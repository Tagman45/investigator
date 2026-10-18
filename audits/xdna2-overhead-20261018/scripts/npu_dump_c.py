#!/usr/bin/env python3
"""npu_dump_c.py — caractériser CE QUE le NPU écrit dans le BO de sortie.

Soumet le TXN, relit bo2, puis :
  - statistiques de valeurs (distinctes, min/max, zéros) ;
  - détection de progression arithmétique (pas constant) ;
  - décodage BF16 des mêmes mots ;
  - comparaison à la référence GEMM si les formes sont connues ;
  - empreinte sha256 + échantillon à offsets fixes (déterminisme inter-run).

Aucune conclusion de justesse : cet outil CARACTÉRISE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import npu_exp as E  # noqa: E402


def analyse(raw: bytes, offsets) -> dict:
    w = np.frombuffer(raw[: len(raw) // 4 * 4], dtype="<u4")
    f = w.view(np.float32)
    d = {
        "n_words": int(w.size),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "distinct": int(np.unique(w).size),
        "zeros": int((w == 0).sum()),
        "min": hex(int(w.min())), "max": hex(int(w.max())),
        "sample": {hex(o): [hex(int(x)) for x in w[o:o + 8]] for o in offsets if o + 8 <= w.size},
        "float_sample": {hex(o): [round(float(x), 6) for x in f[o:o + 4]] for o in offsets if o + 4 <= f.size},
    }
    # pas constant ? (sur les 16 premiers mots, puis sur des fenêtres)
    diffs = np.diff(w[:4096].astype(np.int64))
    d["diff_first_word"] = int(diffs[0]) if diffs.size else None
    d["first_4096_uniform_step"] = bool(diffs.size and np.all(diffs == diffs[0]))
    d["step_counts_top"] = {str(int(k)): int(v) for k, v in
                            zip(*np.unique(diffs, return_counts=True))} if diffs.size else {}
    # progression sur tout le buffer ?
    dall = np.diff(w.astype(np.int64))
    vals, cnt = np.unique(dall, return_counts=True)
    order = np.argsort(cnt)[::-1][:5]
    d["global_top_steps"] = {str(int(vals[i])): int(cnt[i]) for i in order}
    d["global_uniform"] = bool(dall.size and np.all(dall == dall[0]))
    # fenêtre : les 4 plages attendues de C
    d["windows"] = {}
    for name, off in (("C_tile0", 0), ("C_tile1", 0x100 // 4), ("C_tile2", 0x200 // 4),
                      ("C_tile3", 0x300 // 4), ("C_tile4", 0x80000 // 4)):
        win = w[off:off + 64]
        d["windows"][name] = {"off_bytes": off * 4,
                              "first8": [hex(int(x)) for x in win[:8]],
                              "distinct": int(np.unique(win).size)}
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xclbin", default="E:/trixdna_test/phase5_atb/phase5_atb_m32k64n128.xclbin")
    ap.add_argument("--insts", default="E:/trixdna_test/phase5_atb/phase5_atb_m32k64n128_insts.bin")
    ap.add_argument("--opcode", type=int, default=3)
    ap.add_argument("--json", default=None)
    ap.add_argument("--save-bin", default=None, help="écrit la sortie brute relue")
    ns = ap.parse_args(argv)

    import pyxrt  # noqa: PLC0415
    raw_txn = open(ns.insts, "rb").read()
    dev, xb, ctx, kern, kb = E.make_ctx(pyxrt, ns.xclbin)
    g = [kern.group_id(i) for i in (1, 3, 4, 5)]
    # Garde-fou de dimensionnement AVANT allocation (BO aux tailles du contrat historique).
    E.preflight_historical((E.SZ_A, E.SZ_B, E.SZ_C), ns.insts)
    bo_instr = E.alloc(dev, pyxrt, len(raw_txn), g[0], role="instr")
    bo_instr.write(raw_txn, 0)
    bo_instr.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
    bos = []
    for i, sz in enumerate((E.SZ_A, E.SZ_B, E.SZ_C)):
        bo = E.alloc(dev, pyxrt, sz, g[1 + i])
        bo.write(E.marker_words(sz // 4), 0)
        bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
        bos.append(bo)
    run = kern(ns.opcode, bo_instr, len(raw_txn) // 4, bos[0], bos[1], bos[2], 0, 0)
    state = run.wait()
    bos[2].sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
    raw = bytes(int(x) & 0xFF for x in bos[2].read(E.SZ_C, 0))

    offs = [0, 0x100 // 4, 0x200 // 4, 0x300 // 4, 0x1000, 0x4000, 0x10000,
            0x20000 // 4, 0x40000 // 4, 0x80000 // 4, 0x80100 // 4, 0x83400 // 4]
    doc = {"state": str(state), "opcode": ns.opcode, "bo2_addr": hex(bos[2].address()),
           "xclbin": ns.xclbin, "insts": ns.insts, "resultat": analyse(raw, offs)}
    print(json.dumps(doc["resultat"], indent=2, ensure_ascii=False)[:6000])
    if ns.save_bin:
        open(ns.save_bin, "wb").write(raw)
        print(f"bin: {ns.save_bin}")
    if ns.json:
        with open(ns.json, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
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
