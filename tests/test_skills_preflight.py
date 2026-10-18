"""Tests du pré-vol d'utilisation des skills (contrat du 18/10/2026)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import skills_preflight as sp  # noqa: E402


def make_skill(root: Path, name: str, body: str = "# skill\n") -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    p = d / "SKILL.md"
    p.write_text(body, encoding="utf-8")
    return p


def write_registry(tmp_path, skills, requires_tests=True):
    p = tmp_path / "registry.json"
    p.write_text(json.dumps({"t": {"required_skills": skills,
                                   "requires_tests": requires_tests}}), encoding="utf-8")
    return p


def write_usage(tmp_path, rows):
    p = tmp_path / "usage.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return p


def test_skill_absent_bloque(tmp_path):
    roots = [tmp_path / "skills"]
    reg = write_registry(tmp_path, ["fantome"])
    res = sp.preflight("t", reg, tmp_path / "usage.jsonl", roots)
    assert res["status"] == "BLOCKED"
    assert res["raisons"][0]["code"] == "SKILL_UNAVAILABLE"


def test_reference_cassee_racine_inexistante_bloque(tmp_path):
    roots = [tmp_path / "racine_qui_nexiste_pas"]
    reg = write_registry(tmp_path, ["evidence"])
    res = sp.preflight("t", reg, tmp_path / "usage.jsonl", roots)
    assert res["raisons"][0]["code"] == "SKILL_UNAVAILABLE"


def test_skill_lu_mais_non_applique_bloque(tmp_path):
    root = tmp_path / "skills"
    p = make_skill(root, "evidence")
    reg = write_registry(tmp_path, ["evidence"])
    usage = write_usage(tmp_path, [{"task": "t", "skill": "evidence", "sha256": sp.sha256(p),
                                    "applied_to": "", "tests": ["test_x"]}])
    res = sp.preflight("t", reg, usage, [root])
    assert res["status"] == "BLOCKED"
    assert res["raisons"][0]["code"] == "SKILL_READ_NOT_APPLIED"


def test_test_non_execute_bloque(tmp_path):
    root = tmp_path / "skills"
    p = make_skill(root, "evidence")
    reg = write_registry(tmp_path, ["evidence"])
    usage = write_usage(tmp_path, [{"task": "t", "skill": "evidence", "sha256": sp.sha256(p),
                                    "applied_to": "D4", "tests": []}])
    res = sp.preflight("t", reg, usage, [root])
    assert res["raisons"][0]["code"] == "TESTS_NOT_EXECUTED"


def test_skill_non_lu_bloque(tmp_path):
    root = tmp_path / "skills"
    make_skill(root, "evidence")
    reg = write_registry(tmp_path, ["evidence"])
    res = sp.preflight("t", reg, tmp_path / "usage.jsonl", [root])
    assert res["raisons"][0]["code"] == "SKILL_NOT_READ"


def test_skill_modifie_depuis_la_lecture_bloque(tmp_path):
    root = tmp_path / "skills"
    p = make_skill(root, "evidence")
    old = sp.sha256(p)
    p.write_text("# skill modifié après lecture\n", encoding="utf-8")
    reg = write_registry(tmp_path, ["evidence"])
    usage = write_usage(tmp_path, [{"task": "t", "skill": "evidence", "sha256": old,
                                    "applied_to": "D4", "tests": ["test_doc"]}])
    res = sp.preflight("t", reg, usage, [root])
    assert res["raisons"][0]["code"] == "SKILL_CHANGED_SINCE_READ"


def test_registre_absent_bloque(tmp_path):
    res = sp.preflight("t", tmp_path / "absent.json", tmp_path / "u.jsonl", [tmp_path])
    assert res["raisons"][0]["code"] == "REGISTRY_ABSENT"


def test_cas_complet_ok(tmp_path):
    root = tmp_path / "skills"
    p = make_skill(root, "evidence")
    reg = write_registry(tmp_path, ["evidence"])
    usage = write_usage(tmp_path, [{"task": "t", "skill": "evidence", "sha256": sp.sha256(p),
                                    "applied_to": "D4 (mention périmée)", "tests": ["test_doc"]}])
    res = sp.preflight("t", reg, usage, [root])
    assert res["status"] == "OK", res
    assert res["skills"][0]["skill"] == "evidence"


def test_tache_protegee_sans_verification_git_bloque(tmp_path):
    root = tmp_path / "skills"
    p = make_skill(root, "evidence")
    reg = tmp_path / "registry.json"
    reg.write_text(json.dumps({"t": {"required_skills": ["evidence"], "requires_tests": False,
                                     "requires_git_authorization": True}}), encoding="utf-8")
    usage = write_usage(tmp_path, [{"task": "t", "skill": "evidence", "sha256": sp.sha256(p),
                                    "applied_to": "test", "tests": []}])
    res = sp.preflight("t", reg, usage, [root])
    assert any(r["code"] == "GIT_AUTHORIZATION_NOT_CHECKED" for r in res["raisons"])


def test_tache_protegee_avec_autorisation_absente_bloque(tmp_path):
    root = tmp_path / "skills"
    p = make_skill(root, "evidence")
    reg = tmp_path / "registry.json"
    reg.write_text(json.dumps({"t": {"required_skills": ["evidence"], "requires_tests": False,
                                     "requires_git_authorization": True}}), encoding="utf-8")
    usage = write_usage(tmp_path, [{"task": "t", "skill": "evidence", "sha256": sp.sha256(p),
                                    "applied_to": "test", "tests": []}])
    res = sp.preflight("t", reg, usage, [root], git_repo="https://github.com/a/b",
                       git_branch="main", git_commit="b8dba31")
    assert any(r["code"] == "GIT_AUTHORIZATION_ABSENTE" for r in res["raisons"])
