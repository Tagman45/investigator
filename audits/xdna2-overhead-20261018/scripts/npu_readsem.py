#!/usr/bin/env python3
"""npu_readsem.py — `bo.read()` lit-il le DEVICE ou le cache hôte ?

Test B (suite). Séquences discriminantes APRÈS complétion :
  t0 : marqueur M1 -> sync TO -> sync FROM -> read        (roundtrip initial)
  t1 : soumission -> wait -> sync FROM -> read            (contenu device ?)
  t2 : write(M2) SANS sync -> read                        (== M2 => read voit le cache hôte)
  t3 : sync FROM -> read                                  (retour au device ?)
  t4 : sync TO -> sync FROM -> read                       (M2 atteint-il le device ?)

Si t2 == M2 et t3 != M2, `read()` sans sync lit le cache hôte : toutes les
lectures post-run doivent alors être interprétées avec prudence.
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import npu_exp as E  # noqa: E402


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    import pyxrt  # noqa: PLC0415
    xclbin = "E:/trixdna_test/phase5_atb/phase5_atb_m32k64n128.xclbin"
    insts = "E:/trixdna_test/phase5_atb/phase5_atb_m32k64n128_insts.bin"
    raw_txn = open(insts, "rb").read()
    dev, xb, ctx, kern, kb = E.make_ctx(pyxrt, xclbin)
    g = [kern.group_id(i) for i in (1, 3, 4, 5)]
    # Garde-fou de dimensionnement AVANT allocation (BO aux tailles du contrat historique).
    E.preflight_historical((E.SZ_A, E.SZ_B, E.SZ_C), insts)
    bi = E.alloc(dev, pyxrt, len(raw_txn), g[0], role="instr")
    bi.write(raw_txn, 0)
    bi.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
    boA = E.alloc(dev, pyxrt, E.SZ_A, g[1])
    boB = E.alloc(dev, pyxrt, E.SZ_B, g[2])
    boC = E.alloc(dev, pyxrt, E.SZ_C, g[3])
    doc = {"test": "B2_semantique_read", "bo2_addr": hex(boC.address()), "etapes": []}

    def rd(tag: str, expect: bytes | None = None):
        got = bytes(int(x) & 0xFF for x in boC.read(E.SZ_C, 0))
        rec = {"etape": tag, "sha256": sha(got)[:16],
               "premiers_mots": [hex(x) for x in struct.unpack("<8I", got[:32])]}
        if expect is not None:
            rec["identique_attendu"] = got == expect
            rec["octets_differents"] = sum(1 for a, b in zip(got, expect) if a != b)
        doc["etapes"].append(rec)
        print(json.dumps(rec, ensure_ascii=False))
        return got

    M1 = E.marker_words(E.SZ_C // 4)
    M2 = struct.pack("<%dI" % (E.SZ_C // 4), *[0xAA55_0000 | (i & 0xFFFF) for i in range(E.SZ_C // 4)])
    boA.write(E._fill(0xDEAD0000, E.SZ_A), 0)
    boB.write(E._fill(0xBEEF0000, E.SZ_B), 0)
    boC.write(M1, 0)
    for bo in (boA, boB, boC):
        bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
    boC.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
    rd("t0_roundtrip_initial", M1)

    run = kern(3, bi, len(raw_txn) // 4, boA, boB, boC, 0, 0)
    doc["state"] = str(run.wait())
    boC.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
    d1 = rd("t1_apres_run_sync_from")
    boC.write(M2, 0)
    d2 = rd("t2_write_sans_sync", M2)
    boC.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
    d3 = rd("t3_sync_from_apres_write")
    boC.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
    boC.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
    d4 = rd("t4_roundtrip_M2", M2)

    doc["decision"] = {
        "read_sans_sync_voit_cache_hote": d2 == M2,
        "t3_revient_au_device": d3 != M2,
        "t4_M2_atteint_le_device": d4 == M2,
        "t1_egal_t3": d1 == d3,
    }
    print(json.dumps(doc["decision"], indent=2))
    with open("evidence/exp_B2_read_semantics.json", "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    print("JSON: evidence/exp_B2_read_semantics.json")
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
