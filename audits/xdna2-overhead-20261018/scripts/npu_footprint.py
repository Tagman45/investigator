#!/usr/bin/env python3
"""npu_footprint.py — empreinte RÉELLE d'écriture des BO, au mot près (4 octets).

But : mesurer, sans inférence, jusqu'où le NPU écrit dans chaque BO de données,
puis comparer cette empreinte aux grandeurs DÉCODÉES dans les descripteurs du TXN.

Protocole (une seule variable : la taille allouée) :
  - BO remplis d'un marqueur positionnel 0xDEAD0000|i (jamais produit par le GEMM) ;
  - un seul TXN soumis, attente ERT ;
  - relecture intégrale et carte exacte des mots modifiés (min / max / plages).

Ce script ne conclut PAS sur la justesse numérique (c'est npu_gemm_ref.py) ; il
mesure une BORNE PHYSIQUE : le plus grand offset écrit + 4 octets.

Usage :
    python npu_footprint.py --sizes 1998848,2097152,4194304 --json evidence/exp_N_footprint.json
"""
from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import npu_exp as E  # noqa: E402

XCLBIN = "E:/trixdna_test/phase5_atb/phase5_atb_m32k64n128.xclbin"
INSTS = "E:/trixdna_test/phase5_atb/phase5_atb_m32k64n128_insts.bin"


def footprint(raw: bytes) -> dict:
    """Carte des mots écrits : min/max/plages + empreinte exacte."""
    w = E.words_of(raw)
    idx = [i for i, v in enumerate(w) if (v & 0xFFFF0000) != 0xDEAD0000]
    if not idx:
        return {"n_words": len(w), "n_changed": 0, "min_byte": None,
                "max_byte_excl": None, "n_ranges": 0, "ranges_head": []}
    ranges, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1:
            ranges.append([start, prev])
            start = i
        prev = i
    ranges.append([start, prev])
    return {"n_words": len(w), "n_changed": len(idx),
            "min_byte": idx[0] * 4, "max_byte_excl": (idx[-1] + 1) * 4,
            "n_ranges": len(ranges),
            "ranges_head": [[a * 4, (b + 1) * 4] for a, b in ranges[:16]]}


def descriptor_terms(insts: str) -> dict:
    """Grandeurs DÉCODÉES par BD (champs du format, cf. AIEDmaToNpu.cpp).

    Layout shim AIE2P (8 mots) :
      w0 buffer_length | w1 buffer_offset | w2 packet
      w3 d0_size[29:20] d0_stride[19:0]
      w4 burst_length[31:30] d1_size[29:20] d1_stride[19:0]
      w5 AXCache[27:24] d2_stride[19:0]
      w6 iter_current[31:26] iter_size[25:20] iter_stride[19:0]
      w7 next_bd/use_next_bd/valid_bd/locks
    Les strides/size d'itération sont biaisés par -1 (0 => 1 granule/pas).
    """
    import struct
    raw = open(insts, "rb").read()
    w = list(struct.unpack("<%dI" % (len(raw) // 4), raw[: len(raw) // 4 * 4]))
    i, n, last, out = 4, len(w), None, {}
    while i < n:
        op = w[i] & 0xFF
        if op == 1:
            sz = w[i + 3] // 4
            last = w[i + 4:i + sz]
            i += sz
        elif op == 0x81 and last:
            arg, plus = w[i + 8], w[i + 10]
            if arg < 8 and len(last) >= 8:
                bd = last
                rec = {"plus": plus, "len": bd[0],
                       "d0_size_gran": (bd[3] >> 20) & 0x3FF,
                       "d0_stride_gran": bd[3] & 0xFFFFF,
                       "burst_enc": (bd[4] >> 30) & 0x3,
                       "d1_size": (bd[4] >> 20) & 0x3FF,
                       "d1_stride_gran": bd[4] & 0xFFFFF,
                       "axcache": (bd[5] >> 24) & 0xF,
                       "d2_stride_gran": bd[5] & 0xFFFFF,
                       "iter_current": (bd[6] >> 26) & 0x3F,
                       "iter_size": (bd[6] >> 20) & 0x3F,
                       "iter_stride_gran": bd[6] & 0xFFFFF,
                       "valid_bd": (bd[7] >> 25) & 1,
                       "n_words_bd": len(bd)}
                out.setdefault(arg, []).append(rec)
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xclbin", default=XCLBIN)
    ap.add_argument("--insts", default=INSTS)
    ap.add_argument("--opcode", type=int, default=3)
    ap.add_argument("--sizes", default="1998848,2097152,4194304")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--json", default="evidence/exp_N_footprint.json")
    ns = ap.parse_args()
    import pyxrt  # noqa: PLC0415
    sizes = [int(x) for x in ns.sizes.split(",")]
    raw_txn = open(ns.insts, "rb").read()

    dev, xb, ctx, kern, kb = E.make_ctx(pyxrt, ns.xclbin)
    g = [kern.group_id(i) for i in (1, 3, 4, 5)]
    # Conflit de bornes CONNU et accepté (L-X-01) — cible = plancher mesuré.
    pf = E.preflight(tuple(sizes), ns.insts, allow=False, strict_bounds=False)
    print(f"tailles={sizes}  groups={g}  preflight={pf['verdict']}")

    bi = E.alloc(dev, pyxrt, len(raw_txn), g[0], role="instr")
    bi.write(raw_txn, 0)
    bi.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
    bos = [E.alloc(dev, pyxrt, sz, g[1 + i]) for i, sz in enumerate(sizes)]

    # Deux remplissages, une seule variable à la fois :
    #  - ones   : entrées = BF16 1.0 (mêmes entrées que la référence numérique) ;
    #             l'empreinte de C est alors mesurée dans les conditions du GEMM.
    #  - marker : entrées = 0xDEAD0000|i : permet de détecter si le NPU ÉCRIT dans A/B.
    fills = {
        "ones": [b"\x80\x3f" * (sizes[0] // 2), b"\x80\x3f" * (sizes[1] // 2),
                 E.marker_words(sizes[2] // 4)],
        "marker": [E.marker_words(sizes[0] // 4), E.marker_words(sizes[1] // 4),
                   E.marker_words(sizes[2] // 4)],
    }
    doc = {"test": "N_footprint_ecriture", "xclbin": ns.xclbin, "insts": ns.insts,
           "sha_xclbin": E.sha(ns.xclbin), "sha_insts": E.sha(ns.insts),
           "bo_sizes": sizes, "preflight": pf, "runs": [],
           "descripteurs": descriptor_terms(ns.insts)}
    for fill, payloads in fills.items():
        for r in range(1, ns.reps + 1):
            for i, (b, pay) in enumerate(zip(bos, payloads)):
                b.write(pay[:sizes[i]], 0)
            for b in bos:
                b.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
            run = kern(ns.opcode, bi, len(raw_txn) // 4, bos[0], bos[1], bos[2], 0, 0)
            state = run.wait()
            rec = {"fill": fill, "rep": r, "state": str(state), "bo": {}}
            for i, b in enumerate(bos):
                b.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
                raw = bytes(int(x) & 0xFF for x in b.read(sizes[i], 0))
                fp = footprint(raw)
                rec["bo"][f"bo{i}"] = fp
                print(f"  [{fill}] run{r} bo{i} ({sizes[i]} o) : modifiés={fp['n_changed']} "
                      f"min={fp['min_byte']} max_excl={fp['max_byte_excl']} "
                      f"plages={fp['n_ranges']}")
            doc["runs"].append(rec)

    # Consolidation : empreinte de C stable, et A/B jamais écrits ?
    runs = doc["runs"]
    doc["bo2_stable"] = len({json.dumps(r["bo"]["bo2"], sort_keys=True) for r in runs}) == 1
    doc["bo2_borne_sup_octets"] = max(r["bo"]["bo2"]["max_byte_excl"]
                                      for r in runs if r["bo"]["bo2"]["max_byte_excl"])
    doc["bo2_une_seule_plage"] = all(r["bo"]["bo2"]["n_ranges"] <= 1 for r in runs)
    doc["entrees_jamais_ecrites"] = all(
        r["bo"]["bo0"]["n_changed"] == 0 and r["bo"]["bo1"]["n_changed"] == 0
        for r in runs if r["fill"] == "marker")
    print(f"\nC : stable={doc['bo2_stable']} borne_sup={doc['bo2_borne_sup_octets']} o "
          f"plage_unique={doc['bo2_une_seule_plage']}")
    print(f"A/B jamais écrits (remplissage marqueur) : {doc['entrees_jamais_ecrites']}")
    with open(ns.json, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    print(f"JSON: {ns.json}")
    del bos, bi
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
