#!/usr/bin/env python3
"""npu_gemm_diag.py — QUE fait le NPU ? (diagnostic des données écrites)

Pour chaque opcode testé : état matériel, statistiques de C, et recherche de la
meilleure correspondance de C dans A ou B (détecte une simple COPIE de DMA au
lieu d'un calcul), plus corrélation avec les références GEMM plausibles.

Aucune conclusion positive : ce script sert à CLASSER l'observation.
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

M, K, N = 64, 256, 128
SZ_A, SZ_B, SZ_C = M * K * 2, K * N * 2, M * N * 2


def pack(x):
    u = x.astype(np.float32).view(np.uint32)
    u = (u + np.uint32(0x8000)) & np.uint32(0xFFFF0000)
    return u.view(np.float32), (u >> np.uint32(16)).astype("<u2").tobytes()


def unpack(raw, shape):
    u = np.frombuffer(raw, dtype="<u2").astype(np.uint32) << np.uint32(16)
    return u.view(np.float32).reshape(shape)


def best_match(cbytes: bytes, needle: bytes) -> dict:
    """Cherche le plus long préfixe de C présent tel quel dans l'entrée."""
    best = {"prefixe_octets_communs": 0, "offset": None}
    head = cbytes[:64]
    start = 0
    while True:
        i = needle.find(head, start)
        if i < 0:
            break
        n = 0
        while n < len(head) and i + n < len(needle) and needle[i + n] == head[n]:
            n += 1
        if n > best["prefixe_octets_communs"]:
            best = {"prefixe_octets_communs": n, "offset": i}
        start = i + 1
    return best


def run_once(pyxrt, ns, opcode, a_bytes, b_bytes, bo_specs, ref_ab, ref_atb):
    kern, groups, instr = ns["kern"], ns["groups"], ns["instr"]
    dev, F = ns["dev"], ns["F"]
    # Garde-fou de dimensionnement AVANT allocation (taille logique M*K*2 / K*N*2 / M*N*2).
    import npu_preflight  # noqa: PLC0415
    npu_preflight.check((SZ_A, SZ_B, SZ_C), ns["insts"], allow_undersized=True, quiet=False,
                        strict_bounds=False)
    bo_instr = pyxrt.bo(dev, len(instr), F(pyxrt.bo.cacheable), groups["instr"])
    bo_instr.write(instr, 0)
    fl = F(pyxrt.bo.cacheable)
    boA = pyxrt.bo(dev, SZ_A, fl, groups["a"])
    boB = pyxrt.bo(dev, SZ_B, fl, groups["b"])
    boC = pyxrt.bo(dev, SZ_C, fl, groups["c"])
    boA.write(a_bytes, 0)
    boB.write(b_bytes, 0)
    boC.write(b"\xcd" * SZ_C, 0)
    for bo in (bo_instr, boA, boB, boC):
        bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
    run = kern(opcode, bo_instr, len(instr) // 4, boA, boB, boC, 0, 0)
    state = run.wait()
    boC.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
    raw = bytes(int(x) & 0xFF for x in boC.read(SZ_C, 0))
    C = unpack(raw, (M, N))

    stats = {
        "state": str(state),
        "nan": int(np.isnan(C).sum()),
        "zeros": int((C == 0).sum()),
        "total": int(C.size),
        "max_abs": float(np.nanmax(np.abs(C))) if not np.all(np.isnan(C)) else None,
        "mean_abs": float(np.nanmean(np.abs(C))) if not np.all(np.isnan(C)) else None,
        "marqueur_restant": int((np.frombuffer(raw, dtype="<u2") == np.uint16(0xCDCD)).sum()),
    }
    for name, needle in (("A", a_bytes), ("B", b_bytes)):
        stats[f"ressemble_{name}"] = best_match(raw, needle)
    def cos(a, b):
        a, b = a.astype(np.float64), b.astype(np.float64)
        if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
            return None
        return round(float(np.sum(a * b)) / (float(np.linalg.norm(a) * np.linalg.norm(b)) + 1e-30), 6)

    stats["cos_A@B"] = cos(ref_ab, C)
    stats["cos_A_mem(KxM).T@B"] = cos(ref_atb, C)
    # stockage transposé : C lue comme (N x M) comparée à (A@B)ᵀ
    stats["cos_(A@B).T_stockage_transpose"] = cos(ref_ab.T, C.reshape(N, M))
    stats["cos_(A@B)_reordonne_NM"] = cos(ref_ab.T.reshape(-1), C.reshape(-1).reshape(M, N).T.reshape(-1))
    stats["c_premiers"] = [None if not np.isfinite(x) else round(float(x), 6) for x in C.reshape(-1)[:6]]
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xclbin", required=True)
    ap.add_argument("--insts", required=True)
    ap.add_argument("--opcodes", default="3,1")
    ap.add_argument("--json", default=None)
    ns = ap.parse_args(argv)

    import pyxrt  # noqa: PLC0415
    with open(ns.insts, "rb") as fh:
        instr = fh.read()

    rng = np.random.default_rng(7)
    A, a_bytes = pack(rng.uniform(-0.5, 0.5, (M, K)).astype(np.float32))
    B, b_bytes = pack(rng.uniform(-0.5, 0.5, (K, N)).astype(np.float32))
    ref_ab = A @ B                                  # A interprété M x K (64x256)
    ref_atb = A.reshape(K, M).T @ B                 # A interprété K x M (256x64) puis transposé

    dev = pyxrt.device(0)
    xclbin = pyxrt.xclbin(ns.xclbin)
    uuid = dev.register_xclbin(xclbin)
    hwctx = pyxrt.hw_context(dev, uuid)
    kern = pyxrt.kernel(hwctx, xclbin.get_kernels()[0].get_name())
    ctx = {"kern": kern, "dev": dev, "F": pyxrt.bo.flags, "instr": instr,
           "insts": ns.insts,
           "groups": {"instr": kern.group_id(1), "a": kern.group_id(3),
                      "b": kern.group_id(4), "c": kern.group_id(5)}}
    print(f"groupes: {ctx['groups']}")

    out = {}
    for op in [int(x) for x in ns.opcodes.split(",")]:
        try:
            out[f"opcode_{op}"] = run_once(pyxrt, ctx, op, a_bytes, b_bytes, None,
                                           ref_ab, ref_atb)
        except BaseException as exc:  # noqa: BLE001
            out[f"opcode_{op}"] = {"exception": f"{type(exc).__name__}: {exc}",
                                   "traceback": traceback.format_exc()[-500:]}
        s = out[f"opcode_{op}"]
        print(f"opcode={op}: {json.dumps(s, ensure_ascii=False)[:400]}")

    doc = {"xclbin": ns.xclbin, "insts": ns.insts, "resultats": out,
           "lecture": "aucun statut PASS ici : ce script CLASSE l'observation"}
    if ns.json:
        with open(ns.json, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
        print(f"preuve JSON: {ns.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
