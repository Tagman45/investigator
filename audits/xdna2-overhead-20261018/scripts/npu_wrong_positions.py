#!/usr/bin/env python3
"""npu_wrong_positions.py — OÙ sont les valeurs fausses de C quand B est trop petit ?

Hypothèse H1 (dérivée du layout, à réfuter ou valider par ce test) :

    B est (N, K) col-major  → la fin de B = les dernières colonnes de B ;
    un manque de D octets = D/2 éléments bf16 = D/(2K) colonnes de B ;
    chaque colonne manquante rend fausses les M valeurs C[:, j].

    ⇒ valeurs fausses = M × D/(2K) = D × M/(2K)  (ici M=512, K=8192 ⇒ D/32)
    ⇒ les colonnes fautives sont les D/(2K) DERNIÈRES de C.

Rôle de ce script : mesurer la POSITION (indices) des valeurs fausses, pas seulement leur
nombre, puis confronter aux deux prédictions de position possibles :

    P_tail  : la queue contiguë de C   [M*N − fausses, M*N)
    (sinon les indices doivent former M valeurs réparties sur les dernières colonnes)

Usage :
    python npu_wrong_positions.py --bsizes 8388608,8372224,8323072 --reps 2 \
        --json evidence/exp_P_positions_B.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import npu_exp as E  # noqa: E402

XCLBIN = "E:/trixdna_test/repos_strixhalo_npu_setup/saved_xclbins/phase5_bf16_512x8192x512.xclbin"
INSTS = "E:/trixdna_test/repos_strixhalo_npu_setup/saved_xclbins/phase5_bf16_512x8192x512_insts.bin"
M, K, N = 512, 8192, 512
ONEF = 0x3F80
BO_A = BO_C = 16777216


def positions(c: np.ndarray, b_size: int) -> dict:
    """Indices des valeurs fausses + confrontation aux prédictions de position."""
    finite = np.isfinite(c)
    flat = c.reshape(-1)                    # ordre mémoire du BO
    bad = np.nonzero(np.abs(flat - float(K)) > 1.0)[0]
    deficit = M * K * 2 - b_size            # octets manquants dans B
    pred_n = deficit * M // (2 * K)         # = deficit // 32
    if bad.size:
        # contiguïté de la queue ?
        tail_start = flat.size - bad.size
        is_tail = bool(bad.size and bad[0] == tail_start
                       and np.array_equal(bad, np.arange(tail_start, flat.size)))
        # colonnes touchées selon les deux hypothèses de layout de C
        cols_rowmajor = sorted(set((bad % N).tolist()))
        cols_colmajor = sorted(set((bad // M).tolist()))
        rows_colmajor = sorted(set((bad % M).tolist()))
    else:
        is_tail = False
        cols_rowmajor, cols_colmajor, rows_colmajor = [], [], []
    n_deficit_cols = deficit // (2 * K)     # colonnes de B manquantes
    return {
        "b_size": b_size, "deficit_octets": deficit,
        "fausses_mesurees": int(bad.size), "fausses_predites_H1": pred_n,
        "H1_nombre_valide": int(bad.size) == pred_n,
        "queue_contigue": is_tail,
        "queue_contigue_predite_H1": bool(n_deficit_cols > 0),
        "idx_min": int(bad[0]) if bad.size else None,
        "idx_max": int(bad[-1]) if bad.size else None,
        "n_colonnes_B_manquantes": n_deficit_cols,
        "colonnes_touchees_si_C_rowmajor": len(cols_rowmajor),
        "colonnes_touchees_si_C_colmajor": len(cols_colmajor),
        "derniere_colonne_selon_C_rowmajor": cols_rowmajor[-1] if cols_rowmajor else None,
        "derniere_colonne_selon_C_colmajor": cols_colmajor[-1] if cols_colmajor else None,
        "lignes_touchees_si_C_colmajor": len(rows_colmajor),
        "nb_nan": int((~finite).sum()),
        "sha256_C": hashlib.sha256(c.tobytes()).hexdigest(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xclbin", default=XCLBIN)
    ap.add_argument("--insts", default=INSTS)
    ap.add_argument("--opcode", type=int, default=3)
    ap.add_argument("--bsizes", default="8388608,8372224,8323072")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--json", default="evidence/exp_P_positions_B.json")
    ns = ap.parse_args()

    import pyxrt  # noqa: PLC0415
    raw_txn = open(ns.insts, "rb").read()
    dev, xb, ctx, kern, kb = E.make_ctx(pyxrt, ns.xclbin)
    g = [kern.group_id(i) for i in (1, 3, 4, 5)]
    doc = {"test": "P_positions_des_valeurs_fausses", "xclbin": ns.xclbin, "insts": ns.insts,
           "sha_insts": E.sha(ns.insts), "M": M, "K": K, "N": N, "runs": []}
    bi = E.alloc(dev, pyxrt, len(raw_txn), g[0], role="instr")
    bi.write(raw_txn, 0)
    bi.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
    ones = np.full(BO_A // 2, ONEF, dtype="<u2").tobytes()

    for b_size in (int(x) for x in ns.bsizes.split(",")):
        # Le pré-vol est posé AVANT toute allocation de données, et l'ordre A→B→C est
        # respecté dans CHAQUE itération : le garde-fou d'allocation est indexé par
        # ordre d'appel (mesuré le 18/10/2026 — un appel hors ordre lève
        # UnscopedAllocationError, ce qui est le comportement attendu).
        # Conflit de bornes CONNU et accepté (L-X-01) : le but est de TESTER la borne.
        E.preflight((BO_A, b_size, BO_C), ns.insts, allow=True, strict_bounds=False)
        boA = E.alloc(dev, pyxrt, BO_A, g[1])
        boB = E.alloc(dev, pyxrt, b_size, g[2])
        boC = E.alloc(dev, pyxrt, BO_C, g[3])
        for r in range(1, ns.reps + 1):
            boA.write(ones[:BO_A], 0)
            boB.write(ones[:b_size], 0)
            boC.write(E.marker_words(BO_C // 4), 0)
            for b in (boA, boB, boC):
                b.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
            t0 = time.perf_counter()
            run = kern(ns.opcode, bi, len(raw_txn) // 4, boA, boB, boC, 0, 0)
            state = run.wait()
            tw = round((time.perf_counter() - t0) * 1000, 3)
            boC.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
            raw = bytes(int(x) & 0xFF for x in boC.read(M * N * 4, 0))
            c = np.frombuffer(raw, dtype="<f4")
            rec = positions(c, b_size)
            rec.update({"rep": r, "state": str(state), "ms": tw,
                        "preflight_cible": E._PF["targets"].get(1)})
            doc["runs"].append(rec)
            print(f"B={b_size:>9} r{r}: état={state} fausses={rec['fausses_mesurees']} "
                  f"(prédit {rec['fausses_predites_H1']}) queue_contigue={rec['queue_contigue']} "
                  f"idx=[{rec['idx_min']},{rec['idx_max']}] nan={rec['nb_nan']} sha={rec['sha256_C'][:8]}")
        del boA, boB, boC

    ok = [r for r in doc["runs"] if r["H1_nombre_valide"]]
    doc["H1_nombre_valide_partout"] = len(ok) == len(doc["runs"])
    doc["H1_queue_contigue_partout"] = all(r["queue_contigue"] for r in doc["runs"]
                                           if r["fausses_mesurees"])
    print(f"\nH1 (nombre = D×M/(2K)) validée partout : {doc['H1_nombre_valide_partout']}")
    print(f"H1 (queue contiguë de C)              : {doc['H1_queue_contigue_partout']}")
    with open(ns.json, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    print(f"JSON: {ns.json}")
    del bi
    return 0 if doc["H1_nombre_valide_partout"] else 3


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
