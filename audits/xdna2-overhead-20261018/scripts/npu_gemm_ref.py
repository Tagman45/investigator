#!/usr/bin/env python3
"""npu_gemm_ref.py — validation NUMÉRIQUE contre une référence documentée.

Référence verrouillée (E:/trixdna_test/docs/EVID_D_PHASE5_GEOMETRY_2026-08-10.md) :
  design  : phase5_bf16_512x8192x512   (M=512, K=8192, N=512)
  A       : BF16 0x3F80 (=1.0) sur M*K = 4 194 304 éléments (8 MB)
  B       : BF16 0x3F80 (=1.0) col-major (N,K) = 4 194 304 éléments (8 MB)
  C       : F32, M*N = 262 144 valeurs
  attendu : C[i][j] = somme_k 1*1 = K = 8192.0  (0x46000000), 0 valeur fausse
  BO      : 16 MB par buffer dans le harnais validé (npu_repro --gemm-check)

Ce script applique ce contrat SANS le modifier, puis vérifie :
  - état ERT, temps,
  - nombre de valeurs = 8192.0 (±1) sur les M*N premières,
  - nombre de valeurs fausses, min/max,
  - sha256 de C et répétition (reproductibilité).
Aucun PASS n'est prononcé si le critère numérique échoue.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import time

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import npu_exp as E  # noqa: E402

XCLBIN = "E:/trixdna_test/repos_strixhalo_npu_setup/saved_xclbins/phase5_bf16_512x8192x512.xclbin"
INSTS = "E:/trixdna_test/repos_strixhalo_npu_setup/saved_xclbins/phase5_bf16_512x8192x512_insts.bin"
M, K, N = 512, 8192, 512
BO = 16 * 1024 * 1024          # taille du harnais validé
ONEF = 0x3F80                  # BF16 1.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--json", default="evidence/exp_H_gemm_ref.json")
    ap.add_argument("--bo", type=int, default=BO)
    ap.add_argument("--bo-map", default="",
                    help="tailles A,B,C explicites (une variable à la fois, ex. "
                         "16777216,7995392,7995392) — prioritaire sur --bo")
    ap.add_argument("--allow-undersized", action="store_true",
                    help="DANGER: n'applique pas le pre-vol de dimensionnement")
    ns = ap.parse_args()

    import pyxrt  # noqa: PLC0415
    raw_txn = open(INSTS, "rb").read()
    dev, xb, ctx, kern, kb = E.make_ctx(pyxrt, XCLBIN)
    g = [kern.group_id(i) for i in (1, 3, 4, 5)]
    print(f"noyau={kb.get_name()} args={kb.get_num_args()} groups={g}")

    # Tailles par argument : permet de faire varier UNE variable (A, B ou C) à la fois.
    sizes = ([int(x) for x in ns.bo_map.split(",")] if ns.bo_map
             else [ns.bo, ns.bo, ns.bo])
    if len(sizes) != 3:
        print(f"--bo-map exige 3 tailles (A,B,C), recu {len(sizes)}")
        return 2
    ns.bo = max(sizes)
    # PRÉ-VOL : refus si les descripteurs adressent au-delà des BO demandés.
    pf = E.preflight(tuple(sizes), INSTS, allow=ns.allow_undersized)
    print(f"tailles BO demandees : A={sizes[0]} B={sizes[1]} C={sizes[2]}")
    bi = E.alloc(dev, pyxrt, len(raw_txn), g[0], role="instr")
    bi.write(raw_txn, 0)
    bi.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
    boA = E.alloc(dev, pyxrt, sizes[0], g[1])
    boB = E.alloc(dev, pyxrt, sizes[1], g[2])
    boC = E.alloc(dev, pyxrt, sizes[2], g[3])
    print(f"BO A={hex(boA.address())} B={hex(boB.address())} C={hex(boC.address())} "
          f"({sizes} o)")

    ones = np.full(max(sizes) // 2, ONEF, dtype="<u2").tobytes()
    marker = E.marker_words(max(sizes) // 4)

    doc = {"test": "H_GEMM_reference_documentee", "xclbin": XCLBIN, "insts": INSTS,
           "sha_xclbin": E.sha(XCLBIN), "sha_insts": E.sha(INSTS),
           "M": M, "K": K, "N": N, "bo": ns.bo, "bo_map": sizes, "attendu": float(K),
           "preflight": pf, "runs": []}

    for r in range(1, ns.reps + 1):
        boA.write(ones[:sizes[0]], 0)
        boB.write(ones[:sizes[1]], 0)
        boC.write(marker[:sizes[2]], 0)
        for b in (boA, boB, boC):
            b.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
        t0 = time.perf_counter()
        run = kern(3, bi, len(raw_txn) // 4, boA, boB, boC, 0, 0)
        state = run.wait()
        tw = round((time.perf_counter() - t0) * 1000, 3)
        boC.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
        raw = bytes(int(x) & 0xFF for x in boC.read(sizes[2], 0))

        c = np.frombuffer(raw[: M * N * 4], dtype="<f4")
        finite = np.isfinite(c)
        correct = int(np.sum(np.abs(c - float(K)) <= 1.0))
        doc["runs"].append({
            "rep": r, "state": str(state), "submit_plus_wait_ms": tw,
            "sha256_C": hashlib.sha256(raw).hexdigest(),
            "n_values": int(c.size), "correct": correct,
            "wrong": int(c.size - correct),
            "nan": int(np.sum(~finite)),
            "min": None if not finite.any() else float(np.nanmin(c[finite])),
            "max": None if not finite.any() else float(np.nanmax(c[finite])),
            "c0_8": [float(x) for x in c[:8]],
            "c0_8_hex": ["0x%08x" % x for x in np.frombuffer(raw[:32], dtype="<u4")],
        })
        rr = doc["runs"][-1]
        print(f"run{r}: état={rr['state']} {tw} ms | valeurs={rr['n_values']} "
              f"correctes={correct} fausses={rr['wrong']} nan={rr['nan']} "
              f"min={rr['min']} max={rr['max']} | C[0:4]={rr['c0_8'][:4]}")

    ok = all(r["correct"] == M * N for r in doc["runs"])
    det = len({r["sha256_C"] for r in doc["runs"]}) == 1
    doc["verdict"] = ("PASS_NUMERIQUE" if ok and det else
                      "FAIL_NUMERIQUE" if ok is False else "INCONCLUSIVE")
    doc["reproductible"] = det
    print(f"\nattendu : {M*N} valeurs = {K}.0 | obtenu : "
          f"{[r['correct'] for r in doc['runs']]}")
    print(f"reproductible: {det}   VERDICT: {doc['verdict']}")
    with open(ns.json, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    print(f"JSON: {ns.json}")
    del boA, boB, boC, bi
    return 0 if doc["verdict"] == "PASS_NUMERIQUE" else 3


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
