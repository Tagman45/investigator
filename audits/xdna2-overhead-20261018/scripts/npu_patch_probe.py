#!/usr/bin/env python3
"""npu_patch_probe.py — le firmware applique-t-il vraiment arg_plus ?

Test structurel (pas de justesse GEMM) :
1. parse le TXN, extrait pour chaque DDR_PATCH (registre, arg_idx, arg_plus) ;
2. dimensionne chaque BO sur max(arg_plus) + taille du plus grand bloc ecrit ;
3. remplit bo0/bo1 d'un motif connu, bo2 de 0xCD ;
4. soumet opcode=3, attend COMPLETED, relit bo2 ;
5. compare les plages reellement ecrites aux plages attendues (arg_plus arg2).

PASS structurel = ecritures aux offsets patches. Aucune conclusion de justesse.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import time
import traceback

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

CHUNK = {0: 32768, 1: 65536, 2: 16384}  # tailles de bloc observees dans les BD


def parse_txn(path: str):
    raw = open(path, "rb").read()
    w = struct.unpack("<%dI" % (len(raw) // 4), raw)
    i, patches = 4, []
    while i < len(w):
        op = w[i] & 0xFF
        if op == 0x81:
            patches.append({"reg": w[i + 6], "arg": w[i + 8], "plus": w[i + 10]})
            i += 12
        elif op == 0x80:
            i += 4
        elif op == 1:
            i += w[i + 3] // 4
        elif op == 3:
            i += 7
        elif op == 0:
            i += 6
        else:
            break
    return raw, patches


def runs(buf: bytes, marker: bytes) -> list[tuple[int, int]]:
    """Plages contigues qui ne sont plus le marqueur."""
    size = len(marker)
    out, start = [], None
    for off in range(0, len(buf) - size + 1, size):
        changed = buf[off:off + size] != marker
        if changed and start is None:
            start = off
        elif not changed and start is not None:
            out.append((start, off - start))
            start = None
    if start is not None:
        out.append((start, len(buf) - start))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xclbin", required=True)
    ap.add_argument("--insts", required=True)
    ap.add_argument("--opcode", type=int, default=3)
    ap.add_argument("--json", default=None)
    ns = ap.parse_args(argv)

    import pyxrt

    instr, patches = parse_txn(ns.insts)
    maxp = {a: 0 for a in CHUNK}
    for p in patches:
        if p["arg"] in maxp:
            maxp[p["arg"]] = max(maxp[p["arg"]], p["plus"])
    sizes = []
    for a in (0, 1, 2):
        need = maxp[a] + CHUNK[a]
        sizes.append((need + 0xFFF) & ~0xFFF)
    print(f"arg_plus max : {[hex(maxp[a]) for a in (0,1,2)]}")
    print(f"BO dimensionnes : {[hex(s) for s in sizes]} ({sizes} octets)")

    # Garde-fou de dimensionnement : ces BO ne couvrent que arg_plus + un chunk
    # (pas l'étendue complète des descripteurs) -> mode historique explicite.
    import npu_preflight  # noqa: PLC0415
    npu_preflight.check(sizes, ns.insts, allow_undersized=True, quiet=False,
                        strict_bounds=False)

    t = {}
    dev = pyxrt.device(0)
    xclbin = pyxrt.xclbin(ns.xclbin)
    uuid = dev.register_xclbin(xclbin)
    ctx = pyxrt.hw_context(dev, uuid)
    kern = pyxrt.kernel(ctx, xclbin.get_kernels()[0].get_name())
    F = pyxrt.bo.flags

    bo_instr = pyxrt.bo(dev, len(instr), F(pyxrt.bo.cacheable), kern.group_id(1))
    bo_instr.write(instr, 0)
    bo_instr.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)

    bos = []
    for i, sz in enumerate(sizes):
        bo = pyxrt.bo(dev, sz, F(pyxrt.bo.cacheable), kern.group_id(3 + i))
        data = (b"\xcd" * sz) if i == 2 else bytes(((i * 29 + j * 7) % 251) for j in range(sz))
        bo.write(data, 0)
        bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
        bos.append((bo, data, sz))
        print(f"bo{i}: addr=0x{bo.address():x} size={sz}")

    t0 = time.perf_counter()
    run = kern(ns.opcode, bo_instr, len(instr) // 4, *[b for b, _, _ in bos], 0, 0)
    state = run.wait()
    t["wait_ms"] = round((time.perf_counter() - t0) * 1000, 3)
    print(f"etat: {state}  wait={t['wait_ms']} ms")

    bo2 = bos[2][0]
    bo2.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
    out = bytes(int(x) & 0xFF for x in bo2.read(sizes[2], 0))
    got = runs(out, b"\xcd\xcd")

    expect = sorted({p["plus"] for p in patches if p["arg"] == 2})
    got_starts = sorted({s for s, _ in got})
    matched = [s for s in got_starts if s in expect]
    record = {
        "xclbin": ns.xclbin, "insts": ns.insts, "opcode": ns.opcode,
        "state": str(state), "wait_ms": t["wait_ms"],
        "argplus_max": {str(a): maxp[a] for a in maxp},
        "bo_sizes": sizes,
        "patches_arg2_attendus": expect,
        "ecritures_observees": got,
        "offsets_attendus_atteints": matched,
        "verdict": ("PASS_STRUCTUREL" if got_starts and all(s in expect for s in got_starts)
                    else "FAIL_STRUCTUREL" if got_starts else "AUCUNE_ECRITURE"),
    }
    print(f"attendus arg2 : {[hex(x) for x in expect]}")
    print(f"observes      : {[(hex(s), l) for s, l in got][:20]}")
    print(f"VERDICT: {record['verdict']}")
    if ns.json:
        open(ns.json, "w", encoding="utf-8").write(json.dumps(record, indent=2, ensure_ascii=False))
        print(f"preuve JSON: {ns.json}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BaseException as exc:  # noqa: BLE001
        traceback.print_exc()
        print(f"ERREUR: {type(exc).__name__}: {exc}")
        sys.exit(2)
