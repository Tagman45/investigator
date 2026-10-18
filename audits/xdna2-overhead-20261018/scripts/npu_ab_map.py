#!/usr/bin/env python3
"""npu_ab_map.py — quel BO est A et quel BO est B ? (lacune L-X-04)

Le mapping `bo0/bo1/bo2 ↔ A/B/C` n'est PAS prouvé par le design : dans le harnais,
A et B font la même taille (8 MiB) et contiennent la même valeur (BF16 1.0 = 0x3F80),
donc une INVERSION A↔B est numériquement invisible. Ce script lève l'ambiguïté par
le CONTENU, sans rien changer au TXN ni aux tailles.

Principe (C = A·B, A (M,K), B (K,N) bf16, C f32) :
  - tampon 0 = constante 1.0 partout  (valide comme A ou comme B) ;
  - tampon 1 = motif `val(n) = 1 + (n mod 8)` écrit sur la ligne n du layout (N,K)
    row-major de B (K contigu, prouvé par `d1_stride = K·2`).
  - si le noyau lit tampon0 comme A et tampon1 comme B : C[m,n] = K·val(n)
    → C VARIE EN COLONNE ;
  - s'il lit tampon1 comme A : C[m,n] = K·val(m) → C VARIE EN LIGNE.
  Les valeurs 1..8 sont exactes en BF16 (entiers ≤ 256) et K·val tient en f32.

Contrôle : on rejoue avec les tampons échangés (motif en 0, un en 1) — la prédiction
doit s'inverser. Un motif constant (témoin) redonne C = K partout.

Ce script ne modifie aucune taille, aucun TXN, aucun argument. Pré-vol appliqué
(conflit de bornes accepté explicitement, cf. L-X-01).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import npu_exp as E  # noqa: E402

XCLBIN = "E:/trixdna_test/repos_strixhalo_npu_setup/saved_xclbins/phase5_bf16_512x8192x512.xclbin"
INSTS = "E:/trixdna_test/repos_strixhalo_npu_setup/saved_xclbins/phase5_bf16_512x8192x512_insts.bin"
M, K, N = 512, 8192, 512
SZ = 8 * 1024 * 1024          # 8 MiB = K·N·2 = taille logique de A et de B
SZ_C = 16 * 1024 * 1024
ONEF = 0x3F80


def bf16_const(n_elems: int, word: int) -> bytes:
    return np.full(n_elems, word, dtype="<u2").tobytes()


def bf16_pattern_b(n_elems: int) -> bytes:
    """Motif `1 + (n mod 8)` sur la ligne n du layout (N,K) row-major de B."""
    arr = np.empty(n_elems, dtype="<u2")
    for n in range(N):
        val = 1 + (n % 8)
        # BF16 d'un entier exact : troncature des 16 bits hauts du float32.
        word = np.uint16(np.float32(val).view(np.uint32) >> 16)
        arr[n * K:(n + 1) * K] = word
    return arr.tobytes()


def probe(c: np.ndarray) -> dict:
    """C est f32 (M,N) row-major : colonne n => c[0, n], ligne m => c[m, 0]."""
    cm = c.reshape(M, N)
    col = [float(cm[0, n]) for n in range(8)]
    row = [float(cm[m, 0]) for m in range(8)]
    attendu_col = [K * (1 + (n % 8)) for n in range(8)]
    attendu_row = [K * (1 + (m % 8)) for m in range(8)]

    def near(a, b):
        return all(abs(x - y) <= 8.0 for x, y in zip(a, b))

    verdict = ("VARIE_EN_COLONNE" if near(col, attendu_col) else
               "VARIE_EN_LIGNE" if near(row, attendu_row) else
               "CONSTANT" if all(abs(x - float(K)) <= 1.0 for x in col + row) else
               "AUTRE")
    return {"c_0_n": col, "c_m_0": row, "attendu_colonne": attendu_col,
            "attendu_ligne": attendu_row, "verdict": verdict,
            "uniforme_8192": bool(np.all(np.abs(cm - float(K)) <= 1.0))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--json", default="evidence/exp_LX04_ab_map.json")
    ns = ap.parse_args()

    import pyxrt  # noqa: PLC0415
    raw_txn = open(INSTS, "rb").read()
    dev, xb, ctx, kern, kb = E.make_ctx(pyxrt, XCLBIN)
    g = [kern.group_id(i) for i in (1, 3, 4, 5)]
    print(f"noyau={kb.get_name()} args={kb.get_num_args()} groups={g}")

    sizes = (SZ, SZ, SZ_C)
    # Conflit de bornes connu et accepté (L-X-01) : cible = plancher mesuré.
    pf = E.preflight(sizes, INSTS, allow=False, strict_bounds=False)
    bi = E.alloc(dev, pyxrt, len(raw_txn), g[0], role="instr")
    bi.write(raw_txn, 0)
    bi.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
    bo0 = E.alloc(dev, pyxrt, sizes[0], g[1])
    bo1 = E.alloc(dev, pyxrt, sizes[1], g[2])
    boC = E.alloc(dev, pyxrt, sizes[2], g[3])
    print(f"BO0={hex(bo0.address())} BO1={hex(bo1.address())} C={hex(boC.address())}")

    ones = bf16_const(SZ // 2, ONEF)
    pattern = bf16_pattern_b(SZ // 2)
    marker = E.marker_words(SZ_C // 4)

    doc = {"test": "L_X_04_mapping_A_B_par_contenu", "xclbin": XCLBIN, "insts": INSTS,
           "sha_xclbin": E.sha(XCLBIN), "sha_insts": E.sha(INSTS),
           "M": M, "K": K, "N": N, "sizes": sizes, "preflight_verdict": pf.get("verdict"),
           "sha_pattern": hashlib.sha256(pattern).hexdigest(), "runs": []}

    # (nom, contenu bo0, contenu bo1, prédiction si bo0=A ; si bo1=A)
    essais = [
        ("temoin_un_et_un", ones, ones, "CONSTANT", "CONSTANT"),
        ("motif_en_bo1", ones, pattern, "VARIE_EN_COLONNE", "VARIE_EN_LIGNE"),
        ("motif_en_bo0", pattern, ones, "VARIE_EN_LIGNE", "VARIE_EN_COLONNE"),
    ]
    for r in range(1, ns.reps + 1):
        for nom, p0, p1, pred_si_bo0_A, pred_si_bo1_A in essais:
            bo0.write(p0[:sizes[0]], 0)
            bo1.write(p1[:sizes[1]], 0)
            boC.write(marker[:sizes[2]], 0)
            for b in (bo0, bo1, boC):
                b.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
            t0 = time.perf_counter()
            run = kern(3, bi, len(raw_txn) // 4, bo0, bo1, boC, 0, 0)
            state = run.wait()
            tw = round((time.perf_counter() - t0) * 1000, 3)
            boC.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
            raw = bytes(int(x) & 0xFF for x in boC.read(sizes[2], 0))
            c = np.frombuffer(raw[: M * N * 4], dtype="<f4")
            pr = probe(c)
            pr.update({"rep": r, "essai": nom, "state": int(state), "t_ms": tw,
                       "prediction_si_bo0_A": pred_si_bo0_A,
                       "prediction_si_bo1_A": pred_si_bo1_A,
                       "sha256_C": hashlib.sha256(raw[: M * N * 4]).hexdigest()})
            doc["runs"].append(pr)
            print(f"  [{nom}] state={int(state)} t={tw} ms verdict={pr['verdict']} "
                  f"c[0,0:8]={[round(x) for x in pr['c_0_n']]} "
                  f"c[0:8,0]={[round(x) for x in pr['c_m_0']]}")

    # Conclusion : le motif en bo1 doit donner la même signature pour toutes les reps.
    motifs = [r for r in doc["runs"] if r["essai"] == "motif_en_bo1"]
    verdicts = {r["verdict"] for r in motifs}
    doc["conclusion"] = ("bo0=A, bo1=B" if verdicts == {"VARIE_EN_COLONNE"} else
                         "bo1=A, bo0=B" if verdicts == {"VARIE_EN_LIGNE"} else
                         "INDETERMINE")
    sane = all(r["state"] == 4 for r in doc["runs"])
    doc["etats_ok"] = sane
    print(f"\nCONCLUSION: {doc['conclusion']} (états 4 partout: {sane})")

    with open(ns.json, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    print(f"JSON: {ns.json}")
    del bo0, bo1, boC, bi
    return 0 if sane and doc["conclusion"] != "INDETERMINE" else 3


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
