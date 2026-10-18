#!/usr/bin/env python3
"""bracket_B.py — borner la taille minimale d'un buffer (une variable : --vary).

--vary B (défaut) : fait varier B ; --vary C : fait varier C (borne prédite 1 590 016).
Chaque exécution est un **sous-processus** distinct : le code de sortie est capturé
réellement (un SIGSEGV ne peut donc pas masquer les runs suivants), et le crash de
teardown est détecté séparément du verdict numérique (test E).

Ces scripts TESTENT la borne : ils passent --allow-undersized au pré-vol de
npu_exp.py, sinon celui-ci refuserait — à raison — les tailles sous-dimensionnées.

Pour chaque taille : N répétitions → hash sha256 de C, état ERT, exit.
  déterministe  = tous les hash identiques ET tous les exit == 0
Ce script ne conclut PAS sur la justesse : il borne une exigence de taille.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(HERE, "evidence")


def one(size: int, rep: int, asize: int, bsize: int, csize: int, tag: str) -> dict:
    out = os.path.join(EV, f"exp_G_{tag}{size}_r{rep}.json")
    cmd = [sys.executable, "-u", os.path.join(HERE, "scripts", "npu_exp.py"), "map",
           "--asize", str(asize), "--bsize", str(bsize), "--csize", str(csize),
           "--allow-undersized", "--json", out]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE, timeout=600)
    rec = {"size": size, "rep": rep, "exit": p.returncode, "json": os.path.basename(out)}
    try:
        d = json.load(open(out, encoding="utf-8"))
        rec["state"] = d.get("state")
        rec["sha256_C"] = (d.get("changes", {}).get("bo2") or {}).get("sha256")
        rec["n_changed"] = (d.get("changes", {}).get("bo2") or {}).get("n_changed")
        rec["bo_addr"] = {"A": d.get("bo0_addr"), "B": d.get("bo1_addr"), "C": d.get("bo2_addr")}
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["stderr_tail"] = (p.stderr or "")[-300:]
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vary", choices=["A", "B", "C"], default="B")
    ap.add_argument("--sizes", default="1048576,1048592,1101056,1310720,2097152")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--asize", type=int, default=1998848)
    ap.add_argument("--bsize", type=int, default=2097152)
    ap.add_argument("--csize", type=int, default=2097152)
    ap.add_argument("--json", default="")
    ns = ap.parse_args()
    sizes = [int(x) for x in ns.sizes.split(",")]
    tag = ns.vary
    default_json = ("exp_G_bracket_B.json" if tag == "B"
                    else f"exp_G_bracket_{tag}.json")
    ns.json = ns.json or os.path.join(EV, default_json)

    results, summary = [], []
    for size in sizes:
        sz = {"A": ns.asize, "B": ns.bsize, "C": ns.csize}
        sz[ns.vary] = size
        recs = [one(size, r, sz["A"], sz["B"], sz["C"], tag)
                for r in range(1, ns.reps + 1)]
        results += recs
        shas = [r.get("sha256_C") for r in recs]
        exits = [r["exit"] for r in recs]
        states = {r.get("state") for r in recs}
        det = (len(set(shas)) == 1 and None not in shas and all(e == 0 for e in exits))
        row = {"taille_variable": size, "A": sz["A"], "B": sz["B"], "C": sz["C"],
               "exits": exits, "sha256_C": shas,
               "states": sorted(str(s) for s in states),
               "deterministe": det,
               "n_distinct_hash": len(set(shas))}
        summary.append(row)
        print(f"{ns.vary}={size:>9} ({size/1048576:.4f} Mio)  exit={exits}  "
              f"hash distincts={row['n_distinct_hash']}  déterministe={det}  "
              f"état={row['states']}", flush=True)

    first_ok = next((s["taille_variable"] for s in summary
                     if s["deterministe"]), None)
    doc = {"test": f"G_borne_{ns.vary}", "vary": ns.vary,
           "A": ns.asize, "B": ns.bsize, "C": ns.csize, "reps": ns.reps,
           "sizes": sizes, "premier_reproductible": first_ok,
           "summary": summary, "runs": results}
    with open(ns.json, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    ok = [s["taille_variable"] for s in summary if s["deterministe"]]
    ko = [s["taille_variable"] for s in summary if not s["deterministe"]]
    print(f"\nplus petite taille reproductible : {min(ok) if ok else 'aucune'}")
    print(f"tailles non reproductibles        : {ko}")
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
