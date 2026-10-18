#!/usr/bin/env python3
"""npu_gemm_loop.py — débit en boucle chaude du GEMM phase5 validé.

Contrat inchangé (npu_gemm_ref.py / EVID_D_PHASE5_GEOMETRY_2026-08-10.md) :
  design  : phase5_bf16_512x8192x512 (M=512, K=8192, N=512)
  A, B    : BF16 1.0 (0x3F80) sur M*K éléments
  C       : F32, M*N valeurs, attendu = K = 8192.0
  BO      : 16 MiB par buffer

Ce que ce script mesure, et que le test de validation ne mesurait pas :
  - le coût d'UNE soumission répétée trente fois sur les mêmes BO (boucle chaude),
    décomposé en t_soumission (kern) et t_attente (run.wait) ;
  - le coût des synchros hôte (3 x 16 MiB) et de la relecture de C ;
  - le débit obtenu comparé au coût théorique 2·M·K·N et au pic 58,98 TOPS.
Il ne modifie ni les tailles, ni le TXN, ni l'ordre des arguments. Le pré-vol de
dimensionnement refuse l'exécution si les descripteurs adressent au-delà des BO.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import npu_exp as E  # noqa: E402

XCLBIN = "E:/trixdna_test/repos_strixhalo_npu_setup/saved_xclbins/phase5_bf16_512x8192x512.xclbin"
INSTS = "E:/trixdna_test/repos_strixhalo_npu_setup/saved_xclbins/phase5_bf16_512x8192x512_insts.bin"
M, K, N = 512, 8192, 512
BO = 16 * 1024 * 1024
ONEF = 0x3F80
PEAK_TOPS = 58.98          # 2 x 512 MAC x 32 tuiles x 1.8 GHz (claim projet confirmé)


def stats(xs):
    return {"n": len(xs), "min_ms": round(min(xs), 3),
            "median_ms": round(statistics.median(xs), 3),
            "mean_ms": round(statistics.fmean(xs), 3),
            "max_ms": round(max(xs), 3),
            "stdev_ms": round(statistics.stdev(xs), 3) if len(xs) > 1 else 0.0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=30, help="lots chronometrés")
    ap.add_argument("--depth", type=int, default=1,
                    help="soumissions en vol par lot (1 = séquentiel ; >1 = recouvrement)")
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--bo", type=int, default=BO)
    ap.add_argument("--with-sync", action="store_true",
                    help="refait les synchros hote a chaque iteration (cout complet)")
    ap.add_argument("--allow-undersized", action="store_true")
    ap.add_argument("--json", default="evidence/exp_K_gemm_loop.json")
    ns = ap.parse_args()

    import pyxrt  # noqa: PLC0415

    raw_txn = open(INSTS, "rb").read()
    dev, xb, ctx, kern, kb = E.make_ctx(pyxrt, XCLBIN)
    g = [kern.group_id(i) for i in (1, 3, 4, 5)]

    # Conflit de bornes CONNU et accepté (L-X-01) : plancher mesuré > borne décodée.
    pf = E.preflight((ns.bo, ns.bo, ns.bo), INSTS, allow=ns.allow_undersized,
                     strict_bounds=False)
    print(f"noyau={kb.get_name()} args={kb.get_num_args()} groups={g} BO={ns.bo}")

    ones = np.full(ns.bo // 2, ONEF, dtype="<u2").tobytes()
    marker = E.marker_words(ns.bo // 4)

    bi = E.alloc(dev, pyxrt, len(raw_txn), g[0], role="instr")
    bi.write(raw_txn, 0)
    bi.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
    boA = E.alloc(dev, pyxrt, ns.bo, g[1])
    boB = E.alloc(dev, pyxrt, ns.bo, g[2])
    boC = E.alloc(dev, pyxrt, ns.bo, g[3])
    boA.write(ones, 0)
    boB.write(ones, 0)
    boC.write(marker, 0)

    t0 = time.perf_counter()
    for b in (boA, boB, boC):
        b.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
    h2d_ms = round((time.perf_counter() - t0) * 1000, 3)
    print(f"H2D 3 x {ns.bo} o : {h2d_ms} ms")

    doc = {"test": "K_debit_boucle_chaude", "xclbin": XCLBIN, "insts": INSTS,
           "sha_xclbin": E.sha(XCLBIN), "sha_insts": E.sha(INSTS),
           "M": M, "K": K, "N": N, "bo": ns.bo, "preflight": pf,
           "peak_tops_claim": PEAK_TOPS, "with_sync": ns.with_sync,
           "h2d_3bo_ms": h2d_ms, "flops_par_run": 2 * M * K * N,
           "warmup": ns.warmup, "reps": ns.reps, "runs": []}

    def submit_batch():
        """Soumet `depth` exécutions dos à dos, PUIS attend — mesure le recouvrement."""
        t = time.perf_counter()
        runs = [kern(3, bi, len(raw_txn) // 4, boA, boB, boC, 0, 0)
                for _ in range(ns.depth)]
        t_sub = time.perf_counter() - t
        states = [r.wait() for r in runs]
        t_tot = time.perf_counter() - t
        return states, t_sub * 1000, t_tot * 1000

    for i in range(ns.warmup):
        sts, _, tot = submit_batch()
        print(f"warmup{i + 1}: états={[str(s) for s in sts]} {tot:.3f} ms")

    for i in range(1, ns.reps + 1):
        if ns.with_sync:
            for b in (boA, boB, boC):
                b.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
        sts, t_sub, t_tot = submit_batch()
        doc["runs"].append({"rep": i, "depth": ns.depth,
                            "states": [str(s) for s in sts],
                            "submit_batch_ms": round(t_sub, 3),
                            "batch_ms": round(t_tot, 3),
                            "per_run_ms": round(t_tot / ns.depth, 3)})
        if i <= 3 or i % 10 == 0:
            print(f"lot{i} (profondeur {ns.depth}): états={[str(s) for s in sts]} "
                  f"soumission={t_sub:.3f} ms lot={t_tot:.3f} ms "
                  f"par run={t_tot / ns.depth:.3f} ms")

    t0 = time.perf_counter()
    boC.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
    d2h_ms = round((time.perf_counter() - t0) * 1000, 3)
    t0 = time.perf_counter()
    raw = bytes(int(x) & 0xFF for x in boC.read(ns.bo, 0))
    read_ms = round((time.perf_counter() - t0) * 1000, 3)
    c = np.frombuffer(raw[: M * N * 4], dtype="<f4")
    correct = int(np.sum(np.abs(c - float(K)) <= 1.0))

    tot = stats([r["per_run_ms"] for r in doc["runs"]])
    sub = stats([r["submit_batch_ms"] / ns.depth for r in doc["runs"]])
    gflops = 2 * M * K * N / (tot["median_ms"] / 1000) / 1e9
    t_theo_ms = 2 * M * K * N / (PEAK_TOPS * 1e12) * 1000

    doc.update({"D2H_ms": d2h_ms, "read_ms": read_ms,
                "sha256_C": hashlib.sha256(raw).hexdigest(),
                "correct": correct, "attendu": M * N,
                "stats_total": tot, "stats_submit": sub,
                "gflops_median": round(gflops, 3),
                "t_theorique_ms_at_peak": round(t_theo_ms, 4),
                "pct_pic": round(100 * t_theo_ms / tot["median_ms"], 4),
                "tout_correct": correct == M * N,
                "depth": ns.depth,
                "states": sorted({s for r in doc["runs"] for s in r["states"]})})
    print(f"\npar run  : {tot}")
    print(f"soumission seule par run : {sub}")
    print(f"D2H={d2h_ms} ms  read={read_ms} ms  sha256(C)={doc['sha256_C'][:16]}…")
    print(f"numérique : {correct}/{M*N} valeurs = {K}.0 (tout_correct={doc['tout_correct']})")
    print(f"débit médian : {gflops:.2f} GFLOP/s  vs pic {PEAK_TOPS} TOPS "
          f"({doc['pct_pic']:.3f} %) | coût théorique {t_theo_ms*1000:.1f} µs "
          f"vs {tot['median_ms']*1000:.0f} µs mesurés")
    with open(ns.json, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    print(f"JSON: {ns.json}")
    del boA, boB, boC, bi
    return 0 if doc["tout_correct"] else 3


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
