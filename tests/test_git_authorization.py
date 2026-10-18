"""Tests du garde-fou d'autorisation git (contrat du 18/10/2026).

Cas couverts, tous exigés par le contrat :
  - autorisation absente
  - affirmation provenant de l'agent
  - simple « ACCEPT » / résultat d'audit
  - autorisation pour un autre dépôt ou un autre commit
  - autorisation explicite et vérifiable (seul cas ALLOW)
  - autorisation déjà consommée, citation vide, commit invalide
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import git_authorization as ga  # noqa: E402

REPO = "https://github.com/Tagman45/skills-audit-reports"
COMMIT = "b8dba31"


def ledger(tmp_path, *rows):
    p = tmp_path / "auth.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return p


def entry(**kw):
    base = {"origin": "user_message", "request_excerpt": "pousse le commit b8dba31",
            "user_turn_ref": "turn-42", "repo": REPO, "branch": "main",
            "commit": COMMIT, "used_for": None}
    base.update(kw)
    return base


def test_autorisation_absente_bloque(tmp_path):
    res = ga.check(REPO, "main", COMMIT, ledger(tmp_path))
    assert res["decision"] == ga.BLOCK
    assert "AUCUNE_AUTORISATION" in res["raison"]


def test_affirmation_de_lagent_bloque(tmp_path):
    res = ga.check(REPO, "main", COMMIT,
                   ledger(tmp_path, entry(origin="agent",
                                          request_excerpt="push autorisé (index M6)")))
    assert res["decision"] == ga.BLOCK


def test_simple_accept_bloque(tmp_path):
    for origin in ("audit_accept", "accept", "project_acceptance"):
        res = ga.check(REPO, "main", COMMIT,
                       ledger(tmp_path, entry(origin=origin, request_excerpt="ACCEPT")))
        assert res["decision"] == ga.BLOCK, origin


def test_commit_existant_ne_vaut_pas_autorisation(tmp_path):
    res = ga.check(REPO, "main", COMMIT,
                   ledger(tmp_path, entry(origin="existing_commit", request_excerpt="commit 86afdf3")))
    assert res["decision"] == ga.BLOCK


def test_autorisation_autre_depot_bloque(tmp_path):
    res = ga.check(REPO, "main", COMMIT,
                   ledger(tmp_path, entry(repo="https://github.com/Tagman45/investigator")))
    assert res["decision"] == ga.BLOCK


def test_autorisation_autre_commit_bloque(tmp_path):
    res = ga.check(REPO, "main", "deadbee", ledger(tmp_path, entry(commit="b8dba31")))
    assert res["decision"] == ga.BLOCK


def test_autorisation_autre_branche_bloque(tmp_path):
    res = ga.check(REPO, "dev", COMMIT, ledger(tmp_path, entry(branch="main")))
    assert res["decision"] == ga.BLOCK


def test_citation_vide_bloque(tmp_path):
    res = ga.check(REPO, "main", COMMIT, ledger(tmp_path, entry(request_excerpt="   ")))
    assert res["decision"] == ga.BLOCK


def test_autorisation_deja_consommee_bloque(tmp_path):
    res = ga.check(REPO, "main", COMMIT, ledger(tmp_path, entry(used_for="push-1")))
    assert res["decision"] == ga.BLOCK


def test_commit_invalide_bloque(tmp_path):
    res = ga.check(REPO, "main", "pas-un-sha", ledger(tmp_path, entry()))
    assert res["decision"] == ga.BLOCK
    assert "COMMIT_INVALIDE" in res["raison"]


def test_entree_json_invalide_nautorise_pas(tmp_path):
    p = tmp_path / "auth.jsonl"
    p.write_text("{pas du json}\n", encoding="utf-8")
    assert ga.check(REPO, "main", COMMIT, p)["decision"] == ga.BLOCK


def test_autorisation_explicite_verifiable_alloue(tmp_path):
    res = ga.check(REPO, "main", COMMIT, ledger(tmp_path, entry()))
    assert res["decision"] == ga.ALLOW
    assert res["raison"] == "AUTORISATION_UTILISATEUR_VERIFIEE"


def test_record_refuse_citation_vide(tmp_path):
    try:
        ga.record(tmp_path / "a.jsonl", REPO, "main", COMMIT, "", "turn-1")
    except SystemExit as e:
        assert "REFUS" in str(e)
    else:
        raise AssertionError("record aurait dû refuser une citation vide")


def test_record_refuse_sans_reference_de_tour(tmp_path):
    try:
        ga.record(tmp_path / "a.jsonl", REPO, "main", COMMIT, "pousse", "")
    except SystemExit as e:
        assert "REFUS" in str(e)
    else:
        raise AssertionError("record aurait dû refuser une référence absente")


def test_record_puis_check_alloue(tmp_path):
    led = tmp_path / "a.jsonl"
    ga.record(led, REPO, "main", COMMIT, "pousse le commit b8dba31", "turn-42")
    assert ga.check(REPO, "main", COMMIT, led)["decision"] == ga.ALLOW
