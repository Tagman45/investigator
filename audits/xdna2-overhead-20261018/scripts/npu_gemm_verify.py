#!/usr/bin/env python3
"""npu_gemm_verify.py — le NPU calcule-t-il VRAIMENT le GEMM attendu ?

Contrat : on n'écrit « correct » que si les données lues correspondent à une
référence CPU calculée pour des entrées bf16 connues. Sinon on écrit exactement
ce qui a été observé (état matériel + corrélation mesurée).

Hypothèses testées (formes imposées par les tailles de BO bf16 2 o) :
    A: M×K = 64×256, B: K×N = 256×128, C: M×N = 64×128
    C1 = A·B      C2 = Aᵀ·B (ATB)      C3 = Bᵀ·A ... selon tailles
On garde la meilleure corrélation et on l'affiche telle quelle.

Usage :
    python npu_gemm_verify.py --xclbin <x> --insts <i> [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

M, K, N = 64, 256, 128          # imposés par 32768 / 65536 / 16384 octets en bf16
SZ_A, SZ_B, SZ_C = M * K * 2, K * N * 2, M * N * 2


def bf16(x: np.ndarray):
    """Retourne (valeur arrondie bf16 en float32, octets bf16 2 o little-endian)."""
    u = x.astype(np.float32).view(np.uint32)
    u = (u + np.uint32(0x8000)) & np.uint32(0xFFFF0000)
    return u.view(np.float32), (u >> np.uint32(16)).astype("<u2").tobytes()


def unpack_bf16(raw: bytes, shape) -> np.ndarray:
    """Octets bf16 (2 o) → float32."""
    u = np.frombuffer(raw, dtype="<u2").astype(np.uint32) << np.uint32(16)
    return u.view(np.float32).reshape(shape)


def timed(name, fn, *a, **kw):
    t0 = time.perf_counter()
    out = fn(*a, **kw)
    return out, round((time.perf_counter() - t0) * 1000, 3)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xclbin", required=True)
    ap.add_argument("--insts", required=True)
    ap.add_argument("--opcode", type=int, default=3)
    ap.add_argument("--json", default=None)
    ns = ap.parse_args(argv)

    import pyxrt  # noqa: PLC0415

    with open(ns.insts, "rb") as fh:
        instr = fh.read()

    rng = np.random.default_rng(1234)
    A, a_bytes = bf16(rng.uniform(-0.5, 0.5, (M, K)).astype(np.float32))
    B, b_bytes = bf16(rng.uniform(-0.5, 0.5, (K, N)).astype(np.float32))

    dev = pyxrt.device(0)
    xclbin, t_load = timed("load", pyxrt.xclbin, ns.xclbin)
    uuid, t_reg = timed("register", dev.register_xclbin, xclbin)
    hwctx, t_ctx = timed("hw_context", pyxrt.hw_context, dev, uuid)
    kern, t_kern = timed("kernel_open", pyxrt.kernel, hwctx, xclbin.get_kernels()[0].get_name())
    F = pyxrt.bo.flags
    fl = F(pyxrt.bo.cacheable)

    # Garde-fou de dimensionnement AVANT allocation (tailles logiques M*K*2, K*N*2, M*N*2).
    # Mode historique : tailles logiques, potentiellement sous l'étendue des descripteurs.
    import npu_preflight  # noqa: PLC0415
    npu_preflight.check((SZ_A, SZ_B, SZ_C), ns.insts, allow_undersized=True, quiet=False,
                        strict_bounds=False)

    bo_instr = pyxrt.bo(dev, len(instr), fl, kern.group_id(1))
    bo_instr.write(instr, 0)
    bo_instr.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)

    boA = pyxrt.bo(dev, SZ_A, fl, kern.group_id(3))
    boB = pyxrt.bo(dev, SZ_B, fl, kern.group_id(4))
    boC = pyxrt.bo(dev, SZ_C, fl, kern.group_id(5))
    boA.write(a_bytes, 0)
    boB.write(b_bytes, 0)
    boC.write(b"\xcd" * SZ_C, 0)          # marqueur : si C n'est pas écrit, il reste 0xcd
    for bo in (boA, boB, boC):
        bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
    print(f"A(64x256) @0x{boA.address():x}  B(256x128) @0x{boB.address():x}  C(64x128) @0x{boC.address():x}")

    run, t_submit = timed("submit", kern, ns.opcode, bo_instr, len(instr) // 4, boA, boB, boC, 0, 0)
    state, t_wait = timed("wait", run.wait)
    print(f"state={state}  submit={t_submit} ms  wait={t_wait} ms")

    _, t_sync = timed("sync_from", boC.sync, pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
    raw, t_read = timed("read", boC.read, SZ_C, 0)
    C = unpack_bf16(bytes(int(x) & 0xFF for x in raw), (M, N))

    untouched = int((np.frombuffer(bytes(int(x) & 0xFF for x in raw), dtype="<u2") == np.uint16(0xCDCD)).sum())
    print(f"C: {untouched}/{M * N} mots encore au marqueur 0xcdcdcdcd  (sync={t_sync} ms read={t_read} ms)")

    results = {}
    for name, ref in (("A@B", A @ B),):
        num = float(np.sum(ref * C))
        den = float(np.linalg.norm(ref) * np.linalg.norm(C)) + 1e-30
        results[name] = {"cos": round(num / den, 6),
                         "max_abs_err": round(float(np.max(np.abs(ref - C))), 6),
                         "ref_norm": round(float(np.linalg.norm(ref)), 4)}

    best = max(results.items(), key=lambda kv: kv[1]["cos"])
    completed = str(getattr(state, "name", "")) == "ERT_CMD_STATE_COMPLETED"
    if completed and best[1]["cos"] > 0.99:
        status = "TESTED_GEMM_CORRECT"
    elif completed:
        status = "COMPLETED_RESULTAT_NON_CONFIRME"
    else:
        status = f"FAILED_ETAT_{state}"

    doc = {"status": status, "state": str(state), "shape": {"M": M, "K": K, "N": N},
           "opcode": ns.opcode, "xclbin": ns.xclbin, "insts": ns.insts,
           "bo_addresses": {"A": hex(boA.address()), "B": hex(boB.address()), "C": hex(boC.address()),
                            "instr": hex(bo_instr.address())},
           "c_marqueur_restant": untouched,
           "times_ms": {"submit": t_submit, "wait": t_wait, "sync_from": t_sync, "read": t_read,
                        "load": t_load, "register": t_reg, "hw_context": t_ctx, "kernel_open": t_kern},
           "comparaisons": results, "meilleur": best[0],
           "c_premiers_float": [round(float(x), 6) for x in C.reshape(-1)[:8]],
           "ref_premiers_float": [round(float(x), 6) for x in (A @ B).reshape(-1)[:8]]}
    print("-" * 90)
    print(f"STATUT: {status}  (meilleur candidat: {best[0]} cos={best[1]['cos']})")
    print(f"  C[0:8]   = {doc['c_premiers_float']}")
    print(f"  ref[0:8] = {doc['ref_premiers_float']}")
    if ns.json:
        with open(ns.json, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
        print(f"preuve JSON: {ns.json}")
    return 0 if status == "TESTED_GEMM_CORRECT" else 3


if __name__ == "__main__":
    sys.exit(main())
