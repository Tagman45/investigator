#!/usr/bin/env python3
"""txn_dump.py — dump intégral d'un TXN MLIR-AIE (format TxnEncoding.h).

But : ÉTABLIR le contrat d'entrée/sortie du design avant toute conclusion.
Affiche, dans l'ordre du programme :
  - BLOCKWRITE (0x1) : tuile (col,row), adresse BD, longueur, buffer_offset
    + les mots BD décodés (valid_bd, next_bd, dimensions, strides) ;
  - DDR_PATCH (0x81) : registre cible, arg_idx, arg_plus, seed du mot visé ;
  - WRITE (0x0) : registre/queue et valeur ;
  - MASKWRITE (0x3), TCT (0x80).

Sortie JSON optionnelle : table normalisée réutilisable par les sondes.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

NAMES = {0x00: "WRITE", 0x01: "BLOCKWRITE", 0x02: "BLOCKSET", 0x03: "MASKWRITE",
         0x04: "MASKPOLL", 0x05: "NOOP", 0x08: "LOADPDI",
         0x80: "TCT", 0x81: "DDR_PATCH", 0x82: "READ_REGS",
         0x83: "RECORD_TIMER", 0x84: "MERGE_SYNC"}


def walk(words):
    hdr = {
        "major": words[0] & 0xFF, "minor": (words[0] >> 8) & 0xFF,
        "devgen": (words[0] >> 16) & 0xFF, "rows": (words[0] >> 24) & 0xFF,
        "cols": words[1] & 0xFF, "memtile_rows": (words[1] >> 8) & 0xFF,
        "numops": words[2], "txnsize": words[3],
    }
    recs, i, n = [], 4, len(words)
    while i < n:
        op = words[i] & 0xFF
        if op == 0x00:
            sz = words[i + 5] if i + 5 < n else 24
        elif op == 0x01:
            sz = words[i + 3] if i + 3 < n else 0
        elif op == 0x03:
            sz = words[i + 6] if i + 6 < n else 28
        elif op >= 0x80:
            sz = words[i + 1] if i + 1 < n else 0
        elif op == 0x05:
            sz = 4
        else:
            sz = 0
        if sz <= 0 or sz % 4 or i + sz // 4 > n:
            recs.append({"op": op, "name": "??", "start": i, "words": words[i:]})
            break
        recs.append({"op": op, "name": NAMES.get(op, f"OP{op:02x}"),
                     "start": i, "words": words[i:i + sz // 4]})
        i += sz // 4
    return hdr, recs, i


def tile_of(addr):
    return (addr >> 25) & 0x7F, (addr >> 20) & 0x1F


def bd_id_of(addr):
    """AIE2 shim BD registers: 0x1D000 + 0x20*bd_id (+0x4 = buffer addr)."""
    return ((addr & 0xFFFF) - 0x1D000) // 0x20, ((addr & 0xFFFF) - 0x1D000) % 0x20


def decode_bd(payload):
    """BD template écrit par npu.write_bd (16 mots)."""
    keys = ["len", "addr", "d0_size", "d0_stride", "d1_size", "d1_stride",
            "d2_size", "d2_stride", "iteration_current", "iteration_size",
            "iteration_stride", "next_bd", "flags", "lock", "pkt", "misc"]
    return dict(zip(keys, payload))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--insts", required=True)
    ap.add_argument("--json", default=None)
    ap.add_argument("--all", action="store_true", help="afficher aussi les WRITE/TCT")
    ns = ap.parse_args(argv)

    raw = open(ns.insts, "rb").read()
    words = list(struct.unpack("<%dI" % (len(raw) // 4), raw[: len(raw) // 4 * 4]))
    hdr, recs, end = walk(words)
    print(f"fichier   : {ns.insts} ({len(raw)} o, {len(words)} mots)")
    print(f"header    : {hdr}")
    print(f"walk      : {'COHERENT' if end == len(words) and len(recs) == hdr['numops'] else 'INCOHERENT'}"
          f"  ({len(recs)} records / numops={hdr['numops']})")

    bds, patches, rows = {}, [], []
    for r in recs:
        w = r["words"]
        if r["op"] == 0x01:
            col, row = tile_of(w[2])
            bid, off = bd_id_of(w[2])
            bd = decode_bd(w[4:20]) if len(w) >= 20 else {}
            bds[(col, row, bid)] = {"reg": w[2], "len": w[4], "buf_off": w[5], **bd}
            rows.append({"op": "BLOCKWRITE", "col": col, "row": row, "bd_id": bid,
                         "reg": w[2], "reg_off": off, "len": w[4], "buf_off": w[5]})
        elif r["op"] == 0x81:
            p = {"op": "DDR_PATCH", "reg": w[6], "arg": w[8], "plus": w[10],
                 "action": w[5], "col": tile_of(w[6])[0], "bd_id": bd_id_of(w[6])[0],
                 "reg_off": bd_id_of(w[6])[1]}
            patches.append(p)
            rows.append(p)
        elif r["op"] == 0x00:
            rows.append({"op": "WRITE", "addr": w[2], "value": w[4],
                         "col": tile_of(w[2])[0], "off": w[2] & 0xFFFFF})
        elif r["op"] == 0x03:
            rows.append({"op": "MASKWRITE", "addr": w[2], "value": w[4],
                         "mask": w[5], "col": tile_of(w[2])[0],
                         "off": w[2] & 0xFFFFF})
        elif r["op"] == 0x80:
            rows.append({"op": "TCT", "target": hex(w[2]), "meta": hex(w[3]),
                         "col": (w[2] >> 16) & 0xFF, "row": (w[2] >> 8) & 0xFF,
                         "dir": w[2] & 0xFF})

    print(f"\nBD écrits : {len(bds)}")
    for (col, row, bid), bd in sorted(bds.items()):
        print(f"  col={col} row={row} bd={bid:2d}  len={bd['len']:7d}  buf_off=0x{bd['buf_off']:08x}"
              f"  addr_reg=0x{bd.get('addr', 0):08x}  next_bd={bd.get('next_bd')}"
              f"  iter={bd.get('iteration_size')}")

    print(f"\nPatches : {len(patches)}")
    print(f"  {'col':>3} {'bd':>3} {'arg':>3} {'arg_plus':>10} {'len BD':>8} {'seed(BD.addr)':>15}")
    for p in sorted(patches, key=lambda x: (x["col"], x["bd_id"])):
        bd = bds.get((p["col"], 0, p["bd_id"]), {})
        print(f"  {p['col']:3d} {p['bd_id']:3d} {p['arg']:3d} 0x{p['plus']:08x} "
              f"{bd.get('len', -1):8d} 0x{bd.get('addr', 0):08x}")

    per_arg = {}
    for p in patches:
        d = per_arg.setdefault(p["arg"], {"n": 0, "min": 1 << 32, "max": 0,
                                         "lens": set(), "plus": []})
        d["n"] += 1
        d["min"] = min(d["min"], p["plus"])
        d["max"] = max(d["max"], p["plus"])
        d["lens"].add(bds.get((p["col"], 0, p["bd_id"]), {}).get("len"))
        d["plus"].append(p["plus"])
    print("\nRésumé par argument (contrat de tailles implicite) :")
    for a, d in sorted(per_arg.items()):
        total = sum(bds.get((p["col"], 0, p["bd_id"]), {}).get("len", 0)
                    for p in patches if p["arg"] == a)
        print(f"  arg{a}: {d['n']} patches  plus 0x{d['min']:x}..0x{d['max']:x} "
              f" lens={sorted(x for x in d['lens'] if x)}  somme_len={total}"
              f"  (plage min exigée = 0x{d['max']:x} + len)")

    if ns.all:
        print("\nSéquence :")
        for i, r in enumerate(rows):
            print(f"  {i:3d} {json.dumps({k: v for k, v in r.items() if k != 'op'}, ensure_ascii=False)} {r['op']}")

    if ns.json:
        doc = {"insts": ns.insts, "header": hdr, "n_records": len(recs),
               "rows": rows,
               "per_arg": {str(a): {"n": d["n"], "plus_min": d["min"], "plus_max": d["max"],
                                    "lens": sorted(x for x in d["lens"] if x)}
                           for a, d in per_arg.items()}}
        with open(ns.json, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
        print(f"\nJSON: {ns.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
