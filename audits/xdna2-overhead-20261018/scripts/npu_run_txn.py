#!/usr/bin/env python3
"""npu_run_txn.py — exécution réelle d'un TXN sur le NPU (Windows, pyxrt).

Chemin exercé : xclbin → register → hw_context → kernel MLIR_AIE → BO(s) →
soumission → attente → lecture du résultat.

Mesures SÉPARÉES (ms) : chargement xclbin, register, hw_context, ouverture noyau,
allocation BO, écriture BO, sync TO_DEVICE, SOUMISSION, attente (exécution),
sync FROM_DEVICE, lecture.

Vérité matérielle : seul `ERT_CMD_STATE_COMPLETED` est un succès ; les données
lues sont comparées à ce qui a été écrit pour détecter si le DMA a réellement
transféré. Aucune conclusion n'est tirée sans ces deux éléments.

Usage :
    python npu_run_txn.py --xclbin <x.xclbin> --insts <i.bin> [--opcode 3]
                          [--sizes 32768,65536,16384] [--json <out.json>]
"""
from __future__ import annotations

import argparse
import json
import sys
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

TIMES: dict[str, float] = {}
NOTES: list[str] = []


def timed(name: str, fn, *a, **kw):
    t0 = time.perf_counter()
    out = fn(*a, **kw)
    TIMES[name] = round((time.perf_counter() - t0) * 1000, 3)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xclbin", required=True)
    ap.add_argument("--insts", required=True)
    ap.add_argument("--opcode", type=int, default=3)
    ap.add_argument("--sizes", default="32768,65536,16384", help="tailles bo0,bo1,bo2")
    ap.add_argument("--json", default=None)
    ap.add_argument("--flags", default="cacheable",
                    help="flags BO : cacheable | host_only (les valeurs XCL brutes 0x98/0x17 sont REFUSÉES par pyxrt/Windows)")
    ns = ap.parse_args(argv)

    import pyxrt  # noqa: PLC0415

    sizes = [int(x) for x in ns.sizes.split(",")]
    with open(ns.insts, "rb") as fh:
        instr = fh.read()

    # Garde-fou de dimensionnement (avant toute allocation) : ce script est une sonde
    # fonctionnelle à BO volontairement minimaux -> mode historique (avertit, ne refuse pas).
    import npu_preflight  # noqa: PLC0415
    npu_preflight.check(sizes, ns.insts, allow_undersized=True, quiet=False)

    print(f"xclbin={ns.xclbin}")
    print(f"insts ={ns.insts} ({len(instr)} o, {(len(instr) + 3) // 4} mots)")
    print(f"opcode={ns.opcode}  tailles BO={sizes}")

    dev = pyxrt.device(0)
    xclbin = timed("load_xclbin", pyxrt.xclbin, ns.xclbin)
    uuid = timed("register_xclbin", dev.register_xclbin, xclbin)
    hwctx = timed("hw_context", pyxrt.hw_context, dev, uuid)
    kb = xclbin.get_kernels()[0]
    kern = timed("kernel_open", pyxrt.kernel, hwctx, kb.get_name())
    gid_instr = kern.group_id(1)
    groups = [kern.group_id(i) for i in range(3, 6)]
    print(f"noyau={kb.get_name()} args={kb.get_num_args()} group(instr)={gid_instr} groups(data)={groups}")

    # pyxrt (Windows) n'accepte QUE les valeurs d'énumération `cacheable`/`host_only` :
    # les valeurs XCL brutes (0x98 EXECBUF, 0x17) lèvent « unsupported buffer type ».
    F = pyxrt.bo.flags
    fl = F(pyxrt.bo.cacheable if ns.flags == "cacheable" else pyxrt.bo.host_only)
    t0 = time.perf_counter()
    bo_instr = pyxrt.bo(dev, len(instr), fl, gid_instr)
    TIMES["bo_instr_alloc"] = round((time.perf_counter() - t0) * 1000, 3)
    print(f"addr bo_instr = 0x{bo_instr.address():x}  ({bo_instr.size()} o)")
    timed("bo_instr_write", bo_instr.write, instr, 0)
    timed("bo_instr_sync_to", bo_instr.sync, pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)

    bois = []
    for i, sz in enumerate(sizes):
        bo = timed(f"bo{i}_alloc", pyxrt.bo, dev, sz, fl, groups[i])
        print(f"addr bo{i} = 0x{bo.address():x}  ({bo.size()} o)")
        pattern = bytes(((i * 17 + j) % 251) for j in range(sz))
        timed(f"bo{i}_write", bo.write, pattern, 0)
        timed(f"bo{i}_sync_to", bo.sync, pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
        bois.append((bo, pattern))

    run = timed("SUBMIT", kern, ns.opcode, bo_instr, len(instr) // 4, *[b for b, _ in bois], 0, 0)
    st_after_submit = str(run.state)
    t0 = time.perf_counter()
    state = run.wait()
    TIMES["WAIT"] = round((time.perf_counter() - t0) * 1000, 3)
    print(f"état après soumission : {st_after_submit}")
    print(f"état après wait       : {state}")

    moved = {}
    for i, (bo, pattern) in enumerate(bois):
        timed(f"bo{i}_sync_from", bo.sync, pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
        data = timed(f"bo{i}_read", bo.read, len(pattern), 0)
        data = bytes(int(x) & 0xFF for x in data)
        same = data[:len(pattern)] == pattern
        diff = sum(1 for a, b in zip(data[:len(pattern)], pattern) if a != b)
        moved[f"bo{i}"] = {"size": len(pattern), "identique_a_l_ecrit": same,
                           "octets_differents": diff,
                           "premiers_octets": list(data[:16])}
        print(f"  bo{i}: {len(pattern)} o — identique={same} — octets différents={diff} — début={list(data[:8])}")

    completed = str(getattr(state, "name", "")) == "ERT_CMD_STATE_COMPLETED"
    any_moved = any(not v["identique_a_l_ecrit"] for v in moved.values())
    if completed and any_moved:
        status = "TESTED_EXECUTION_MOVE_DMA"
    elif completed:
        status = "COMPLETED_SANS_TRANSFERT"
    else:
        status = f"FAILED_ETAT_{state}"

    doc = {"status": status, "xclbin": ns.xclbin, "insts": ns.insts, "opcode": ns.opcode,
           "kernel": kb.get_name(), "args": kb.get_num_args(),
           "group_instr": gid_instr, "groups_data": groups,
           "state_submit": st_after_submit, "state_wait": str(state),
           "bo": moved, "times_ms": TIMES, "notes": NOTES}
    print("-" * 90)
    print(f"STATUT: {status}")
    for k, v in TIMES.items():
        print(f"  {k:20s} {v:9.3f} ms")
    if ns.json:
        with open(ns.json, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
        print(f"preuve JSON: {ns.json}")
    return 0 if status == "TESTED_EXECUTION_MOVE_DMA" else 3


if __name__ == "__main__":
    sys.exit(main())
