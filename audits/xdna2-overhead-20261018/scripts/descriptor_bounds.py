#!/usr/bin/env python3
"""descriptor_bounds.py — chaque offset/stride/longueur tient-il dans son buffer ?

[RÉFUTÉ 18/10/2026, Phase B — modèle CONSERVÉ comme diagnostic, plus utilisé en décision]
Le modèle ci-dessous n'est PAS un décodage du format : son terme `payload[6] >> 16`
extrait les bits 31:16 de word[6], c'est-à-dire `(iteration_size << 4) |
(iteration_stride >> 16)` — un mélange de deux champs. Le layout réel est
`iteration_current[31:26] | iteration_size[25:20] | iteration_stride[19:0]`
(`AIEDmaToNpu.cpp:750-760`, `BdLowering.h`, `AIEXDialect.cpp:66-73`). Preuve par les
mots : `0x0013ffff >> 16 = 19 = (1 << 4) | 3`. La décision de dimensionnement a été
déplacée dans `npu_preflight.py` (borne basse décodée, combinée en `max()` avec les
planchers MESURÉS). Voir `RAPPORT_GARDE_FOU_BORNE_C_DEBIT_2026-10-18.md` §7.

Ancien modèle de champ (dérivé du décodeur TXN de `gemm.dll`, présenté comme **validé**) :

  payload[0] = buffer_length (octets par pas)
  payload[1] = buffer_offset (adresse BD, remplacée par DDR_PATCH)
  payload[2] = 0
  payload[3] = d0 (taille/stride)
  payload[4] = d1 (taille/stride)
  payload[5] = d2 (taille/stride)
  payload[6] = itération : (n_iter << 16) | (stride en unités de 0x10000)
  payload[7] = flags / next_bd

Étendue maximale adressée par une BD :
      extent = arg_plus + (payload[6] >> 16) * 0x10000 + buffer_length

Le modèle n'est PAS supposé : il est confronté aux seuils **mesurés**
(exp_G_bracket_B.json : 1,25 Mio insuffisant, 2 Mio suffisant) et aux tailles
qui ont produit un résultat reproductible.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

STEP = 0x10000

# Tailles mesurées comme suffisantes / insuffisantes (exp_G_bracket_B, D5, D4)
MEASURED = {
    0: {"suffisant": 1998848, "insuffisant": None,
        "source": "exp_D_iso_1998848_2097152 (déterministe) — A jamais mis en défaut"},
    # [AFFINÉ 18/10/2026] la valeur 2 Mio était un majorant prouvé, jamais resserré.
    # Bissection à 8 répétitions : 1 949 696 o échoue (3 hash distincts/8),
    # 1 966 080 o passe 8/8 hash unique. La cible du garde-fou reste 2 097 152
    # (sûr) ; le minimum mesuré est 1 966 080.
    1: {"suffisant": 1966080, "insuffisant": 1949696,
        "source": "exp_G_bracket_B_fine1..4 + _reps8a..d (bisection, 8 répétitions par point)",
        "garde_fou_conserve": 2097152,
        "ancienne_valeur": {"suffisant": 2097152, "insuffisant": 1310720,
                            "source": "exp_G_bracket_B (1,25 Mio KO / 2 Mio OK, 3 répétitions)"}},
    # [CORRIGÉ 18/10/2026] l'ancienne valeur (2 Mio suffisant) ne bornait rien de fin :
    # la mesure montre que C sature à 1 MiB exactement, et que le modèle descripteur
    # SUR-ESTIME C (1 590 016) car son pas d'itération n'est pas 0x10000.
    2: {"suffisant": 1048576, "insuffisant": 1048064,
        "source": "exp_G_bracket_C + exp_G_bracket_C_small (1 MiB saturé : "
                  "262 144 mots écrits ; 1 048 064 o perd 128 mots)",
        "ancienne_valeur": {"suffisant": 2097152, "insuffisant": 544768,
                            "source": "exp_D_map_baseline (KO) / exp_D_bigBO_run1-2 (OK)"}},
}


def parse(path: str):
    raw = open(path, "rb").read()
    w = list(struct.unpack("<%dI" % (len(raw) // 4), raw[: len(raw) // 4 * 4]))
    i, n, bds = 4, len(w), []
    while i < n:
        op = w[i] & 0xFF
        if op == 1:
            sz = w[i + 3] // 4
            bds.append({"reg": w[i + 2], "p": w[i + 4:i + sz]})
            i += sz
        elif op == 0x81:
            bds[-1].setdefault("patches", []).append(
                {"arg": w[i + 8], "plus": w[i + 10]})
            i += 12
        elif op == 0:
            i += 6
        elif op == 3:
            i += 7
        elif op >= 0x80:
            i += max(w[i + 1] // 4, 1)
        else:
            break
    return bds


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--insts", default="E:/trixdna_test/phase5_atb/phase5_atb_m32k64n128_insts.bin")
    ap.add_argument("--json", default="evidence/exp_I_descriptor_bounds.json")
    ns = ap.parse_args()

    bds = parse(ns.insts)
    rows = []
    for bd in bds:
        p = bd["p"]
        for pt in bd.get("patches", []):
            length = p[0]
            it = p[6] >> 16
            extent = pt["plus"] + it * STEP + length
            rows.append({"col": (bd["reg"] >> 25) & 0x7F, "arg": pt["arg"],
                         "plus": pt["plus"], "len": length, "iters": it,
                         "w10": p[6], "extent": extent})

    print(f"BD analysées : {len(rows)}   (source {ns.insts})")
    print(f"{'arg':>3} {'n':>3} {'plus_max':>10} {'iters':>6} {'len':>8} "
          f"{'étendue requise':>16} {'mesuré suffisant':>17} {'verdict':>9}")
    out = {}
    for arg in sorted({r["arg"] for r in rows}):
        sel = [r for r in rows if r["arg"] == arg]
        need = max(r["extent"] for r in sel)
        iters = sorted({r["iters"] for r in sel})
        plus_max = max(r["plus"] for r in sel)
        m = MEASURED.get(arg, {})
        # Sémantique : l'étendue prédite est comparée au MINIMUM MESURÉ, pas l'inverse.
        #   minimum mesuré == prédiction -> EXACT
        #   minimum mesuré <  prédiction -> MAJORANT (la formule surestime : sûr mais pas fin)
        #   minimum mesuré >  prédiction -> SOUS-ESTIMATION (dangereux : un BO conforme
        #                                   à la prédiction serait en réalité trop petit)
        if m.get("suffisant") is None:
            verdict = "INCONCLUSIVE"
        elif m["suffisant"] == need:
            verdict = "EXACT"
        elif m["suffisant"] < need:
            verdict = "MAJORANT"
        else:
            verdict = "SOUS-ESTIMATION"
        out[str(arg)] = {"n": len(sel), "plus_max": plus_max, "iters": iters,
                         "len": sorted({r["len"] for r in sel}),
                         "extent_requis": need, "mesure": m, "verdict": verdict,
                         "marge_suffisant": (m.get("suffisant") - need) if m.get("suffisant") else None}
        print(f"{arg:3d} {len(sel):3d} 0x{plus_max:08x} {str(iters):>6} "
              f"{sorted({r['len'] for r in sel})} {need:>10} (0x{need:x}) "
              f"{m.get('suffisant')} {verdict:>9}")

    print("\n[RÉFUTÉ 18/10/2026] Ce modèle N'EST PAS un décodage : `payload[6]>>16` mélange")
    print("`iteration_size` et `iteration_stride`. Sortie conservée comme diagnostic et")
    print("traçabilité de la réfutation — voir npu_preflight.py pour la règle utilisée.")
    print("Lecture d'époque : l'étendue requise était calculée depuis les descripteurs, PAS")
    print("depuis la réussite du kernel.")
    print("B : prédit 2 097 152 o ; mesuré (8 répétitions/point) 1 949 696 KO,")
    print("    1 966 080 OK -> majorant de 131 072 o.")
    with open(ns.json, "w", encoding="utf-8") as fh:
        json.dump({"insts": ns.insts, "modele": "plus + (w10>>16)*0x10000 + len",
                   "args": out, "bds": rows}, fh, indent=2, ensure_ascii=False)
    print(f"JSON: {ns.json}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"ERREUR: {type(exc).__name__}: {exc}")
        sys.exit(2)
