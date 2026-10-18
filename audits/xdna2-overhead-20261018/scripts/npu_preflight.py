#!/usr/bin/env python3
"""npu_preflight.py — pré-vol de dimensionnement des BO, AVANT toute allocation.

[MISE À JOUR 18/10/2026 — Phase B : word[6] DÉCODÉ, et un trou du garde-fou corrigé]

**1. `(payload[6] >> 16) × 0x10000` est RÉFUTÉ comme décodage (preuve par les mots).**
Le layout réel de word[6] (source primaire `AIEDmaToNpu.cpp:750-760`, branche shim
AIE2 8 mots) est :

    word[6] = iteration_current[31:26] | iteration_size[25:20] | iteration_stride[19:0]

avec, côté encodeur (`BdLowering.h:168-181`, `AIEXDialect.cpp:66-73`) :
`iteration_size` stocké = taille-1 (« Size is stored biased by -1 »), stride en
granules de 4 o biaisé par -1. L'ancienne formule extrayait les bits 31:16, soit
`(iteration_size << 4) | (iteration_stride >> 16)` : un MÉLANGE de deux champs, pas
un pas. Vérification sur les mots réels du design m32k64n128 :
`w6 = 0x0013ffff` → `iteration_size = 1`, `iteration_stride = 0x3ffff` ;
`0x0013ffff >> 16 = 0x13 = 19 = (1 << 4) | 3`. Le « pas de 0x10000 » n'existe pas
dans le format.

**2. Nouvelle règle : borne décodée du format, et `max()` avec le plancher mesuré.**

    étendue(BD) = arg_plus + iteration_size × (iteration_stride+1) × 4 + buffer_length

C'est une borne BASSE (chaque itération déplace au moins `buffer_length` octets à un
décalage croissant) ; elle n'inclut pas le dispersement d0/d1/d2 (d2_size est
implicite côté matériel) et n'est donc pas certifiée suffisante.
**TROU CORRIGÉ — `min()` était dangereux.** L'ancien code prenait
`cible = min(étendue, plancher)`. Une borne basse décodée ne doit JAMAIS réduire une
borne haute MESURÉE : sur le design 512×8192×512, `min` ramenait la cible de B à
5 832 704 alors que 8 388 608 est le minimum MESURÉ qui passe et que 7 995 392 a
produit 12 288 valeurs fausses + 8 704 NaN (exp_M). Reproduit le 18/10/2026 :
`--sizes 7995392,5832704,7995392` → **exit 0** (accepté) → défaut F-1.
Désormais `cible = max(plancher mesuré, étendue décodée)` : le plancher mesuré ne
peut plus être affaibli par un modèle.

[CORRIGÉ 18/10/2026, Phase B] Ce paragraphe décrivait l'ancienne règle comme « EXACTE
pour A (1 998 848) et pour B (2 097 152) ». Conservé pour l'historique, mais la valeur
n'est une égalité que pour A (mesuré 1 998 848, jamais mis en défaut) ; pour B la
mesure donne un intervalle (1 949 696 ; 1 966 080] et non 2 097 152 : l'ancienne
formule sur-estimait B de ≥ 131 072 o sans que cela soit démontré à l'époque.

[CORRIGÉ 18/10/2026, preuve exp_G_bracket_C.json + exp_G_bracket_C_small.json]
La formule SUR-ESTIME C : elle prédit 1 590 016 o alors que la mesure montre que le
pic d'écriture est exactement 262 144 mots = 1 048 576 o, saturé dès C = 1 MiB
(1 048 064 o perd 128 mots = 512 o). Cause : le pas d'itération n'est pas 0x10000 pour
l'argument 2 (les arg_plus des BD C avancent de 0x100).

[RÉFUTÉ 18/10/2026 — la règle n'est NI dérivée du format NI un majorant sûr]
Deux réfutations, sources primaires à l'appui :

1. **Ce n'est pas une règle de format.** `TxnEncoding.h` (en-tête `header-only` décrit
   comme « the single in-tree source of truth for the instruction format ») encode
   BLOCKWRITE comme `opcode, (col|row<<8), addr, (4+count)*4, payload…` : `payload`
   est le **contenu brut des mots de BD**, et les commentaires de
   `AIEDMATasksToNPU.cpp:591-629` attribuent word[0]=buffer_length,
   word[1]=buffer_offset, word[2]=packet/enable, word[4]=burst_length[31:30] +
   d1_*, word[5]=AXCache[27:24] + d2_*, word[7]=next_bd/use_next_bd/valid_bd/locks.
   Aucun mot ne porte de « pas de 0x10000 » : le `(payload[6] >> 16) * 0x10000` était
   un ajustement empirique, pas un décodage. [CORRIGÉ 18/10/2026, Phase B] Le layout de
   word[6] n'est plus UNKNOWN : `iteration_current[31:26] | iteration_size[25:20] |
   iteration_stride[19:0]` (voir en-tête de ce module et `bd_records()`), champs 6 bits
   biaisés -1 et stride en granules de 4 o.
2. **Ce n'est pas un majorant sûr.** Sur `phase5_bf16_512x8192x512`, B échoue
   numériquement à 7 995 392 o (étendue prédite pour A) : 249 856/262 144 valeurs
   correctes, 12 288 fausses, 8 704 NaN, sha instable — alors que l'étendue prédite
   pour B n'est que de 5 832 704 o. Mesure : 8 388 608 o PASS 2/2 (reproductible) ;
   seul B est en cause (A et C à 16 Mio et B réduit → FAIL ; C réduit seul → PASS).
   Autrement dit la règle peut **laisser passer une configuration qui produit des
   données fausses** : c'est une erreur dans le sens dangereux.

[CORRIGÉ 18/10/2026, Phase B] La conséquence « la cible reste min(étendue, plancher) »
est REMPLACÉE par `max(plancher mesuré, borne décodée)` — voir défaut F-1 ci-dessus :
le `min()` acceptait une taille MESURÉE fausse (5 832 704 o pour B). Le verdict
**PASS_NON_CERTIFIE** pour un design sans plancher mesuré est conservé : jamais un
PASS silencieux. La certification exige un plancher mesuré avec référence numérique
pour ce couple xclbin/insts.

Usage :
    from npu_preflight import check
    check(sizes=[A, B, C], insts=path)          # lève UndersizedBufferError si trop petit
    check(..., allow_undersized=True)           # expériences qui TESTENT la borne

CLI (échec par défaut, code 3 — c'est un GARDE-FOU, pas un rapport) :
    python npu_preflight.py --insts <txn.bin> [--sizes a,b,c] [--json out.json]
    python npu_preflight.py --insts <txn.bin> --sizes a,b,c --allow-undersized   # teste la borne
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys

GRAN = 4        # granularité d'adressage du DMA (octets par granule de stride)
STEP_REFUTE = 0x10000  # ancien « pas » — RÉFUTÉ (voir docstring) : conservé pour trace

# Planchers MESURÉS (18/10/2026), INDEXÉS PAR sha256 du flux d'instructions.
# Un plancher n'est valable que pour le design sur lequel il a été mesuré : l'appliquer
# à un autre xclbin donnerait un faux PASS (ex. le design 512x8192x512 adresse
# 7 995 392 o sur arg0, bien au-delà du plancher de 1 998 848 mesuré ici).
# Design inconnu -> aucune correction : la cible reste l'étendue descripteur.
#   arg0 : exp_D_iso_1998848_2097152 (jamais mis en défaut) + exp_I (étendue = 1 998 848)
#   arg1 : exp_G_bracket_B (1,25 Mio KO / 2 Mio OK)
#   arg2 : exp_G_bracket_C + exp_G_bracket_C_small (1 MiB saturé, 1 048 064 tronqué)
# NATURE du plancher — un plancher de REPRODUCTIBILITÉ n'est PAS un plancher de JUSTESSE.
# [AJOUTÉ 18/10/2026, exp_O] La table ci-dessus provenait, pour m32k64n128, d'un test de
# déterminisme (bracket_B.py : hash identiques + exit 0) — critère explicitement
# insuffisant (« Une sortie reproductible peut être fausse »). Ce design n'a AUCUNE
# référence numérique : `npu_gemm_verify.py` y donne C ≈ 0 et cos = nan (exp. gemm_verify_op3),
# la justesse n'y est donc pas établie. Le design 512×8192×512, lui, a une référence
# numérique verrouillée (262 144 × 8192.0) et sa borne B a été re-mesurée AU CRITÈRE
# NUMÉRIQUE (exp_O) : 8 126 464 / 8 257 536 / 8 323 072 / 8 372 224 o REFUSÉS (8192 / 4096 /
# 2048 / 512 valeurs fausses, NAN 6400/3200/0/0) et 8 388 608 o PASS 2/2 → plancher NUMÉRIQUE.
FLOOR_NATURE = {
    "0a3d03e92849fa5dd43f9f5d595cd10aae7a0846e7c8d4ffb9385138f1b0c958": "REPRODUCTIBLE_SEUL",
    "487fa1ff00444985dd5e992e19dc24049ae7f864fec2fce298f4df45d57d9ecc": "NUMERIQUE_ET_REPRODUCTIBLE",
}

MEASURED_MIN_BY_INSTS = {
    "0a3d03e92849fa5dd43f9f5d595cd10aae7a0846e7c8d4ffb9385138f1b0c958":  # m32k64n128
        {0: 1998848, 1: 2097152, 2: 1048576},
    # phase5_bf16_512x8192x512 — mesuré le 18/10/2026 avec référence numérique
    # (262 144 valeurs = 8192.0, sha stable 2/2) :
    #   arg0 : 7 995 392 sufit ; non bisecté plus bas
    #   arg1 : 7 995 392 ÉCHOUE (12 288 fausses, 8 704 NaN, sha instable) ;
    #          8 388 608 PASSE -> plancher retenu 8 388 608
    #   arg2 : aucun échec observé (7 995 392 et 16 Mio passent) -> pas de plancher
    #          ajouté, la cible reste l'étendue descripteur (conservateur)
    "487fa1ff00444985dd5e992e19dc24049ae7f864fec2fce298f4df45d57d9ecc":  # 512x8192x512
        {0: 7995392, 1: 8388608},
}


class UndersizedBufferError(RuntimeError):
    """Un BO demandé est plus petit que l'étendue adressée par les descripteurs."""


class BoundConflictError(RuntimeError):
    """Plancher MESURÉ > borne DÉCODÉE : les deux bornes sont incompatibles.

    [AJOUTÉ 18/10/2026 — ferme la lacune L-X-01]
    La borne décodée est une borne BASSE du format (elle ignore d0/d1/d2) ; quand un
    plancher mesuré la dépasse, le modèle et la mesure se contredisent. Avant ce
    correctif, le pré-vol prenait `max()` et signalait le désaccord **sans jamais
    refuser** : un design pouvait donc être présenté comme « PASS » alors que le
    décodeur qui justifie la taille était contredit par la mesure.
    Posture désormais *fail-closed* : le pré-vol REFUSE (exit 4) par défaut, et
    l'acceptation du conflit est un acte explicite (`strict_bounds=False` côté API,
    `--allow-bound-conflict` côté CLI), journalisé dans le rapport.
    """


def bd_records(insts_path: str) -> list[tuple[int, int, list[int]]]:
    """[(arg, arg_plus, mots_du_BD)] pour chaque DDR_PATCH du TXN."""
    raw = open(insts_path, "rb").read()
    w = list(struct.unpack("<%dI" % (len(raw) // 4), raw[: len(raw) // 4 * 4]))
    i, n = 4, len(w)
    last = None
    out: list[tuple[int, int, list[int]]] = []
    while i < n:
        op = w[i] & 0xFF
        if op == 1:                      # BLOCKWRITE : nouveau BD
            sz = w[i + 3] // 4
            last = w[i + 4:i + sz]
            i += sz
        elif op == 0x81 and last:        # DDR_PATCH : rattaché au dernier BD
            if w[i + 8] < 8:
                out.append((w[i + 8], w[i + 10], last))
            i += 12
        elif op == 0:
            i += 6
        elif op == 3:
            i += 7
        elif op >= 0x80:
            i += max(w[i + 1] // 4, 1)
        else:
            break
    return out


def txn_extents(insts_path: str) -> dict[int, int]:
    """BORNE BASSE décodée du format, par argument (jamais un majorant sûr).

        étendue = arg_plus + iteration_size × (iteration_stride+1) × 4 + buffer_length

`iteration_size` est le champ 6 bits biaisé -1 (0 = une seule itération) et
`iteration_stride` le pas en granules de 4 o, biaisé -1. La borne ignore le
dispersement d0/d1/d2 : elle est donc strictement inférieure ou égale au besoin
réel — d'où l'obligation de la combiner en `max()` avec un plancher MESURÉ.
"""
    ext: dict[int, int] = {}
    for arg, plus, bd in bd_records(insts_path):
        if len(bd) < 7:
            continue
        length = bd[0]
        iter_size = (bd[6] >> 20) & 0x3F
        iter_stride = (bd[6] & 0xFFFFF) + 1
        need = plus + iter_size * iter_stride * GRAN + length
        ext[arg] = max(ext.get(arg, 0), need)
    return ext


def txn_extents_refute(insts_path: str) -> dict[int, int]:
    """Ancienne formule `arg_plus + (payload[6]>>16)*0x10000 + len` — RÉFUTÉE.

    Conservée uniquement pour que la réfutation reste reproductible : ses valeurs ne
    doivent être utilisées dans AUCUNE décision (voir docstring du module)."""
    ext: dict[int, int] = {}
    for arg, plus, bd in bd_records(insts_path):
        if len(bd) < 7:
            continue
        need = plus + (bd[6] >> 16) * STEP_REFUTE + bd[0]
        ext[arg] = max(ext.get(arg, 0), need)
    return ext


def check(sizes, insts: str, allow_undersized: bool = False, quiet: bool = False,
          strict_bounds: bool = True) -> dict:
    """Vérifie que chaque BO couvre l'étendue de son argument. Refuse sinon.

    sizes : séquence (a, b, c) des tailles demandées, dans l'ordre des args 0,1,2…
    strict_bounds : si True (défaut, *fail-closed*), un désaccord « plancher mesuré
        > borne décodée » lève BoundConflictError ; l'appelant qui accepte
        explicitement ce conflit (design déjà mesuré) passe strict_bounds=False.
    """
    with open(insts, "rb") as fh:
        sha_insts = hashlib.sha256(fh.read()).hexdigest()
    ext = txn_extents(insts)
    floors = MEASURED_MIN_BY_INSTS.get(sha_insts, {})
    nature = FLOOR_NATURE.get(sha_insts, "AUCUN")
    report = {"insts": insts, "sha256_insts": sha_insts,
              "planchers_connus_pour_ce_design": bool(floors),
              "nature_du_plancher": nature if floors else "AUCUN",
              "extents": {str(k): v for k, v in sorted(ext.items())},
              "sizes": list(sizes), "checks": [], "ok": True}
    for arg in sorted(ext):
        if arg >= len(sizes):
            continue
        need, got = ext[arg], sizes[arg]
        floor = floors.get(arg)
        # max(), PAS min() : une borne basse décodée ne doit jamais affaiblir un
        # plancher mesuré (défaut F-1, 18/10/2026 — le min() acceptait 5 832 704 o
        # pour B alors que cette taille a été MESURÉE fausse : 12 288 valeurs + NaN).
        cible = max(need, floor) if floor is not None else need
        ok = got >= cible
        report["checks"].append({"arg": arg, "borne_decodee": need, "alloue": got,
                                 "plancher_mesure": floor, "cible": cible,
                                 "desaccord_descripteur": floor is not None and floor > need,
                                 "marge": got - cible, "ok": ok})
        if not ok:
            report["ok"] = False
    conflicts = [c for c in report["checks"] if c["desaccord_descripteur"]]
    report["bound_conflict"] = bool(conflicts)
    report["strict_bounds"] = strict_bounds
    if conflicts and strict_bounds:
        detail = "; ".join(
            f"arg{c['arg']}: plancher mesure {c['plancher_mesure']} > borne decodee "
            f"{c['borne_decodee']} (ecart {c['plancher_mesure'] - c['borne_decodee']} o)"
            for c in conflicts)
        raise BoundConflictError(
            "PRE-VOL FAIL_BOUND_CONFLICT — les deux bornes sont incompatibles : " + detail +
            ". La borne decodee du format est une borne BASSE (d0/d1/d2 non inclus) : "
            "elle ne peut ni certifier ni reduire le plancher mesure. Relancer avec "
            "strict_bounds=False (API) / --allow-bound-conflict (CLI) pour accepter "
            "explicitement ce conflit — la cible reste max(plancher, borne).")
    if not report["ok"] and not allow_undersized:
        bad = [c for c in report["checks"] if not c["ok"]]
        msg = "; ".join(
            f"arg{c['arg']}: alloué {c['alloue']} < requis {c['cible']} "
            f"({-c['marge']} octets manquants)" for c in bad)
        raise UndersizedBufferError(
            "PRE-VOL REFUSE l'allocation — " + msg +
            " | cible = max(plancher mesuré, borne décodée du format) "
            "(exp_G_bracket_B/C, exp_M, exp_N_footprint). "
            "Utiliser allow_undersized=True uniquement pour TESTER la borne.")
    if not quiet:
        for c in report["checks"]:
            flag = " [plancher mesure > borne decodee]" if c["desaccord_descripteur"] else ""
            print(f"  pre-vol arg{c['arg']}: borne_decodee={c['borne_decodee']} "
                  f"cible={c['cible']} alloue={c['alloue']} marge={c['marge']:+d} "
                  f"{'OK' if c['ok'] else 'INSUFFISANT'}{flag}")
    report["allow_undersized"] = allow_undersized
    report["design_certifie"] = bool(floors) and nature == "NUMERIQUE_ET_REPRODUCTIBLE"
    if report["ok"] and conflicts:
        print("  AVERTISSEMENT: conflit de bornes ACCEPTE explicitement "
              "(plancher mesure > borne decodee) — cible = plancher mesure, "
              "le decodeur de format est mis en defaut (lacune L-X-03).")
    if report["ok"] and floors and not report["design_certifie"]:
        # [AJOUTÉ 18/10/2026, exp_O] Plancher présent mais issu d'un test de
        # DÉTERMINISME uniquement : ni refus (la cible reste >= borne décodée et >= ce
        # plancher) ni certification (le résultat peut être faux de facon reproductible,
        # mesuré sur le design 512).
        report["verdict"] = "PASS_SOUS_RESERVE"
        print("  AVERTISSEMENT: plancher de REPRODUCTIBILITE seulement "
              f"(nature={nature}) — la justesse n'est pas etablie pour ce design "
              "(aucune reference numerique). Le pre-vol ne certifie que la borne basse.")
    elif report["ok"] and not floors:
        # L'étendue des descripteurs n'étant PAS un majorant sûr (réfutation du
        # 18/10/2026 sur le design 512), un design sans plancher mesuré ne peut pas
        # être certifié : on avertit au lieu de laisser croire à une garantie.
        report["verdict"] = "PASS_NON_CERTIFIE"
        print("  AVERTISSEMENT: etendue descripteur NON certifiee (aucun plancher mesure "
              "pour ce sha256 d'insts) — une configuration conforme a cette etendue "
              "peut encore produire des donnees fausses. Mesurer un plancher avec "
              "reference numerique avant de conclure.")
    else:
        report["verdict"] = "PASS" if report["ok"] else (
            "PASS_SOUS_RESERVE" if allow_undersized else "FAIL")
    # Un PASS simple est interdit quand le modèle de format est contredit : le verdict
    # doit porter le conflit (les verdicts déjà non certificatifs sont conservés).
    if report["verdict"] == "PASS" and report["bound_conflict"]:
        report["verdict"] = "PASS_BOUND_CONFLICT_ASSUME"
    return report


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--insts", required=True)
    ap.add_argument("--sizes", default="")
    ap.add_argument("--json", default=None)
    ap.add_argument("--allow-undersized", action="store_true",
                    help="ne pas refuser : uniquement pour une expérience qui TESTE la borne")
    ap.add_argument("--allow-bound-conflict", action="store_true",
                    help="accepter EXPLICITEMENT un plancher mesure > borne decodee "
                         "(sinon FAIL_BOUND_CONFLICT, exit 4)")
    ns = ap.parse_args()
    sizes = [int(x) for x in ns.sizes.split(",")] if ns.sizes else []
    rc = 0
    if sizes:
        try:
            rep = check(sizes, ns.insts, allow_undersized=ns.allow_undersized, quiet=False,
                        strict_bounds=not ns.allow_bound_conflict)
        except BoundConflictError as exc:
            print(f"PRE-VOL: REFUSE — {exc}")
            rc = 4
            rep = {"insts": ns.insts, "extents": {str(k): v for k, v in
                   sorted(txn_extents(ns.insts).items())}, "sizes": sizes, "ok": False,
                   "refused": True, "bound_conflict": True,
                   "verdict": "FAIL_BOUND_CONFLICT"}
        except UndersizedBufferError as exc:
            print(f"PRE-VOL: REFUSE — {exc}")
            rc = 3
            rep = {"insts": ns.insts, "extents": {str(k): v for k, v in
                   sorted(txn_extents(ns.insts).items())}, "sizes": sizes, "ok": False,
                   "refused": True, "verdict": "FAIL"}
    else:
        rep = {"insts": ns.insts, "extents": {str(k): v for k, v in
               sorted(txn_extents(ns.insts).items())}}
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    if ns.json:
        with open(ns.json, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=2, ensure_ascii=False)
        print(f"JSON: {ns.json}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
