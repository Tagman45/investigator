#!/usr/bin/env python3
"""Auto-commit + push des depots dedies (mission du 17/10/2026).

REGLE UTILISATEUR (17/10/2026, verrouillee) :
  - repos_openflowlm_next (fork OpenFlowLM-Next) : INTERDIT de push / modif distante.
  - skills git-ecosystem-investigator : rapport + code dans Tagman45/investigator.
  - resultats de recherche XDNA2 : Tagman45/doc-skill-xdna2.
Les deux seuls depot gerés ici :
  - C:/Users/videl/skills-audit-reports  -> origin https://github.com/Tagman45/investigator
  - C:/Users/videl/Desktop/doc-skill-xdna2-work -> origin https://github.com/Tagman45/doc-skill-xdna2

Le cycle : add -A -> commit horodate si changement -> push si avance sur origin/main.
Echecs : consignés dans le log sans casser la boucle. Intervalle par defaut 60 s.
"""
import subprocess, time, datetime, sys, os
from pathlib import Path

REPOS = [
    Path(r"C:/Users/videl/skills-audit-reports"),
    Path(r"C:/Users/videl/Desktop/doc-skill-xdna2-work"),
]
FORBIDDEN_HINTS = ("repos_openflowlm_next",)

LOG = Path(r"C:/Users/videl/skills-audit-reports/tools/auto_commit.log")


def run(repo: Path, *args, timeout=90):
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def log_line(s: str):
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{stamp} {s}\n")
    if "-v" in sys.argv:
        print(f"{stamp} {s}")


def sync_one(repo: Path) -> str:
    name = repo.name
    for h in FORBIDDEN_HINTS:
        if h in str(repo).lower():
            return f"[{name}] REFUSE: repo interdit par la regle utilisateur ({h})"
    r_status = run(repo, "status", "--porcelain")
    if r_status.returncode != 0:
        return f"[{name}] FAIL status: {r_status.stderr.strip()[:120]}"
    r_add = run(repo, "add", "-A")
    if r_add.returncode != 0:
        return f"[{name}] FAIL add: {r_add.stderr.strip()[:120]}"
    r_staged = run(repo, "diff", "--cached", "--name-only")
    n_staged = len([l for l in r_staged.stdout.splitlines() if l.strip()])
    if n_staged == 0:
        return f"[{name}] rien a committer", False
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    r_commit = run(repo, "commit", "-m", f"auto-commit {stamp}: {n_staged} fichier(s) - regle 17/10 (rapports->investigator, recherche->doc-skill-xdna2, fork interdit)")
    if r_commit.returncode != 0:
        return f"[{name}] FAIL commit: {r_commit.stderr.strip()[:160]}"
    ahead = run(repo, "rev-list", "--count", "origin/main..HEAD")
    n_ahead = int(ahead.stdout.strip() or "0") if ahead.returncode == 0 else 0
    if n_ahead == 0:
        return f"[{name}] commit {n_staged} fichier(s) OK, rien a pousser"
    r_push = run(repo, "push", "origin", "main", timeout=300)
    if r_push.returncode != 0:
        return f"[{name}] commit OK mais PUSH ECHOUE: {r_push.stderr.strip()[:180]}"
    return f"[{name}] commit {n_staged} + push {n_ahead} commit(s) OK"


def main_loop(interval: int = 60):
    log_line(f"=== auto_commit_push demarré (interval {interval}s; repos {[r.name for r in REPOS]}; fork interdit) ===")
    while True:
        for repo in REPOS:
            try:
                log_line(sync_one(repo))
            except subprocess.TimeoutExpired:
                log_line(f"[{repo.name}] TIMEOUT operation git")
            except Exception as e:
                log_line(f"[{repo.name}] ERREUR: {type(e).__name__}: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    interval = 60
    for a in sys.argv[1:]:
        if a.startswith("--interval="):
            interval = int(a.split("=", 1)[1])
    main_loop(interval)
