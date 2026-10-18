#!/usr/bin/env python3
"""skills_preflight.py — pré-vol d'utilisation des skills (lecture seule).

Un skill « obligatoire » doit être : trouvé, LU (hash identique à celui
enregistré), APPLIQUÉ (champ `applied_to` non vide), et ses tests exécutés si la
tâche les exige. Sinon la tâche est BLOCKED — jamais « terminée » par défaut.

Usage :
    python tools/skills_preflight.py --task fix-defects
    python tools/skills_preflight.py --task fix-defects --json

Sortie : exit 0 = OK ; exit 3 = BLOCKED (raisons listées).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_REGISTRY = HERE / "skills_registry.json"
DEFAULT_USAGE = REPO / "audits" / "skills-usage" / "skills_usage.jsonl"

# Emplacements configurés (ordre de recherche). Le premier trouvé gagne.
DEFAULT_ROOTS = [
    Path.home() / ".config" / "opencode" / "skills",
    Path.home() / "Desktop" / "doc-skill-xdna2-work" / "skills" / "local",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"__invalid__": line[:200]})
    return rows


def find_skill(name: str, roots) -> Path | None:
    for root in roots:
        p = Path(root) / name / "SKILL.md"
        if p.is_file():
            return p
    return None


def preflight(task: str, registry=None, usage=None, roots=None,
              git_repo=None, git_branch=None, git_commit=None) -> dict:
    registry = Path(registry or DEFAULT_REGISTRY)
    usage = Path(usage or DEFAULT_USAGE)
    roots = [Path(r) for r in (roots or DEFAULT_ROOTS)]

    if not registry.exists():
        return {"status": "BLOCKED", "task": task,
                "raisons": [{"code": "REGISTRY_ABSENT", "detail": str(registry)}]}

    spec = json.loads(registry.read_text(encoding="utf-8")).get(task)
    if not spec:
        return {"status": "BLOCKED", "task": task,
                "raisons": [{"code": "TASK_INCONNUE", "detail": task}]}

    entries = load_jsonl(usage)
    raisons, detail = [], []
    for skill in spec.get("required_skills", []):
        path = find_skill(skill, roots)
        if path is None:
            raisons.append({"code": "SKILL_UNAVAILABLE", "skill": skill,
                            "detail": "introuvable dans " + ", ".join(str(r) for r in roots)})
            continue
        digest = sha256(path)
        mine = [e for e in entries if e.get("skill") == skill and e.get("task") == task
                and not e.get("__invalid__")]
        if not mine:
            raisons.append({"code": "SKILL_NOT_READ", "skill": skill, "detail": str(path)})
            continue
        if not any(e.get("sha256") == digest for e in mine):
            raisons.append({"code": "SKILL_CHANGED_SINCE_READ", "skill": skill,
                            "detail": f"hash actuel {digest[:12]} absent des lectures enregistrées"})
            continue
        cur = [e for e in mine if e.get("sha256") == digest][-1]
        if not str(cur.get("applied_to") or "").strip():
            raisons.append({"code": "SKILL_READ_NOT_APPLIED", "skill": skill,
                            "detail": "applied_to vide : lu mais non appliqué"})
            continue
        if spec.get("requires_tests") and not (cur.get("tests") or []):
            raisons.append({"code": "TESTS_NOT_EXECUTED", "skill": skill,
                            "detail": "aucun test consigné pour cette lecture"})
            continue
        detail.append({"skill": skill, "path": str(path), "sha256": digest,
                       "applied_to": cur.get("applied_to"), "tests": cur.get("tests", [])})

    # Tâche protégée : l'autorisation git doit être vérifiée, pas supposée.
    if spec.get("requires_git_authorization"):
        if not (git_repo and git_branch and git_commit):
            raisons.append({"code": "GIT_AUTHORIZATION_NOT_CHECKED",
                            "detail": "tâche protégée : fournir --repo/--branch/--commit"})
        else:
            sys.path.insert(0, str(HERE))
            import git_authorization as ga
            res = ga.check(git_repo, git_branch, git_commit)
            if res["decision"] != ga.ALLOW:
                raisons.append({"code": "GIT_AUTHORIZATION_ABSENTE",
                                "detail": res["raison"]})
            else:
                detail.append({"git_authorization": res["raison"]})

    return {"status": "OK" if not raisons else "BLOCKED", "task": task,
            "skills": detail, "raisons": raisons}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--usage", default=str(DEFAULT_USAGE))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--repo")
    ap.add_argument("--branch")
    ap.add_argument("--commit")
    a = ap.parse_args(argv)
    res = preflight(a.task, a.registry, a.usage,
                    git_repo=a.repo, git_branch=a.branch, git_commit=a.commit)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"{res['status']}: {res['task']}")
        for r in res["raisons"]:
            print(f"  - {r['code']} {r.get('skill', '')}: {r['detail']}")
    return 0 if res["status"] == "OK" else 3


if __name__ == "__main__":
    sys.exit(main())
