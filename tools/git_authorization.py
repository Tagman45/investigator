#!/usr/bin/env python3
"""git_authorization.py — garde-fou d'autorisation pour toute opération distante.

Règle : un push / release / modification de branche distante exige une
autorisation EXPLICITE, PRÉALABLE et TRACABLE de l'utilisateur, portant sur le
dépôt, la branche et le commit concernés.

Ce module ne peut pas *créer* une autorisation : il ne lit que des entrées dont
`origin == "user_message"` et qui citent la demande utilisateur. Toute autre
origine (agent, audit ACCEPT, commit existant, autre agent) est refusée.

Usage CLI (lecture seule, aucun réseau) :

    python tools/git_authorization.py check --repo <url|path> --branch main \
        --commit <sha> [--ledger <jsonl>]
    python tools/git_authorization.py record --ledger <jsonl> \
        --repo <url|path> --branch main --commit <sha> \
        --request-excerpt "<citation exacte>" --user-turn-ref "<ref>"

`check` sort 0 si ALLOW, 3 si BLOCK (et imprime la raison).
"""
import argparse
import json
import re
import sys
from pathlib import Path

ALLOW = "ALLOW"
BLOCK = "BLOCK"

# Origines autorisées : UNIQUEMENT un message utilisateur.
AUTHORIZED_ORIGINS = {"user_message"}

# Origines explicitement refusées (documentées pour les tests).
FORBIDDEN_ORIGINS = {
    "agent", "agent_assertion", "audit_accept", "accept", "existing_commit",
    "other_agent", "skill_instruction", "project_acceptance",
}

DEFAULT_LEDGER = Path(__file__).resolve().parent.parent / "audits" / "git-authorizations" / "authorizations.jsonl"


def normalize_repo(value: str) -> str:
    """Normalise une URL ou un chemin de dépôt pour comparaison stricte."""
    v = (value or "").strip().lower().rstrip("/")
    v = re.sub(r"^https?://", "", v)
    v = re.sub(r"^git@([^:]+):", r"\1/", v)
    v = v.replace("\\", "/")
    if v.endswith(".git"):
        v = v[:-4]
    return v


def load_ledger(path) -> list:
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            # entrée illisible : ignorée MAIS jamais convertie en autorisation
            rows.append({"__invalid__": line[:200]})
    return rows


def check(repo, branch, commit, ledger=DEFAULT_LEDGER, now=None) -> dict:
    """Retourne {'decision': ALLOW|BLOCK, 'raison': str, 'entree': dict|None}.

    Une autorisation n'est valide que si TOUS les champs concordent :
    origine utilisateur, dépôt, branche, commit, citation non vide.
    """
    if not commit or not re.fullmatch(r"[0-9a-fA-F]{7,40}", str(commit)):
        return {"decision": BLOCK, "raison": "COMMIT_INVALIDE (SHA attendu, 7-40 hex)", "entree": None}
    if not branch:
        return {"decision": BLOCK, "raison": "BRANCHE_MANQUANTE", "entree": None}

    target_repo = normalize_repo(repo)
    rows = load_ledger(ledger)
    if not rows:
        return {"decision": BLOCK, "raison": "AUCUNE_AUTORISATION_TRACEE", "entree": None}

    for row in rows:
        if row.get("__invalid__"):
            continue
        origin = str(row.get("origin", "")).strip().lower()
        if origin in FORBIDDEN_ORIGINS:
            continue
        if origin not in AUTHORIZED_ORIGINS:
            continue
        if normalize_repo(row.get("repo", "")) != target_repo:
            continue
        if str(row.get("branch", "")).strip() != str(branch).strip():
            continue
        authorized_commit = str(row.get("commit", "")).strip().lower()
        if not (str(commit).lower().startswith(authorized_commit)
                or authorized_commit.startswith(str(commit).lower())):
            continue
        if not str(row.get("request_excerpt", "")).strip():
            continue
        if row.get("used_for"):  # une autorisation ne sert qu'une fois
            continue
        return {"decision": ALLOW, "raison": "AUTORISATION_UTILISATEUR_VERIFIEE", "entree": row}

    return {"decision": BLOCK, "raison": "AUCUNE_AUTORISATION_CORRESPONDANTE (dépôt/branche/commit/origine)", "entree": None}


def record(ledger, repo, branch, commit, request_excerpt, user_turn_ref) -> dict:
    """Ajoute une autorisation. Refuse tout ce qui n'est pas une citation utilisateur."""
    if not request_excerpt or not request_excerpt.strip():
        raise SystemExit("REFUS: --request-excerpt vide (aucune demande utilisateur citée)")
    if not user_turn_ref or not user_turn_ref.strip():
        raise SystemExit("REFUS: --user-turn-ref absent (référence traçable requise)")
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", str(commit)):
        raise SystemExit("REFUS: commit invalide")
    p = Path(ledger)
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "origin": "user_message",
        "request_excerpt": request_excerpt.strip(),
        "user_turn_ref": user_turn_ref.strip(),
        "repo": repo,
        "branch": branch,
        "commit": commit,
        "used_for": None,
    }
    with p.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def main(argv=None):
    ap = argparse.ArgumentParser(description="Garde-fou d'autorisation d'opération distante")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check")
    c.add_argument("--repo", required=True)
    c.add_argument("--branch", required=True)
    c.add_argument("--commit", required=True)
    c.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    c.add_argument("--json", action="store_true")

    r = sub.add_parser("record")
    r.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    r.add_argument("--repo", required=True)
    r.add_argument("--branch", required=True)
    r.add_argument("--commit", required=True)
    r.add_argument("--request-excerpt", required=True)
    r.add_argument("--user-turn-ref", required=True)

    a = ap.parse_args(argv)
    if a.cmd == "check":
        res = check(a.repo, a.branch, a.commit, a.ledger)
        if a.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"{res['decision']}: {res['raison']}")
        return 0 if res["decision"] == ALLOW else 3
    entry = record(a.ledger, a.repo, a.branch, a.commit, a.request_excerpt, a.user_turn_ref)
    print(json.dumps(entry, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
