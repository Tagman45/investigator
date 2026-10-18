"""Non-régression des corrections D1-D8 (mission skills-fix-20261018).

Chaque test vise un défaut documenté dans
`audits/skills-contract-20261018/DEFECTS_D1_D8.md`.
Les chemins des skills sont découverts, pas codés en dur dans un seul emplacement.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SKILLS = Path.home() / ".config" / "opencode" / "skills"
AIE2P = SKILLS / "aie2p-hand-asm-debug" / "scripts"
NPU = SKILLS / "npu-offload-pipeline"
ORACLE = SKILLS / "xdna2-evidence-oracle"
PATHEXP = SKILLS / "xdna2-path-explorer"
QWEN36 = SKILLS / "open-qwen36-kernels"
REPO = Path(r"E:/trixdna_test/repos_openflowlm_next")
FIX = Path(__file__).resolve().parent / "fixtures" / "aie2p"
IS_WIN = os.name == "nt"


def run_ps(script, *args, timeout=90):
    return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                           "-File", str(script), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)


# ---------------------------------------------------------------- D1
def test_d1_refs_resolvent_depuis_le_depot():
    if not REPO.is_dir():
        pytest.skip("dépôt OpenFlowLM-Next absent sur cette machine")
    r = subprocess.run([sys.executable, str(NPU / "scripts" / "check_refs.py"),
                        "--base", str(REPO), "--json"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["resolus"] == 5


def test_d1_sans_base_echoue_avec_code_nomme():
    env = {k: v for k, v in os.environ.items() if k != "OFLM_REPO"}
    r = subprocess.run([sys.executable, str(NPU / "scripts" / "check_refs.py"), "--json"],
                       capture_output=True, text=True, encoding="utf-8", env=env,
                       cwd=str(SKILLS))
    assert r.returncode == 3
    assert json.loads(r.stdout)["status"] == "REFERENCE_BASE_NOT_FOUND"


def test_d1_skill_documente_les_modes_installation():
    txt = (NPU / "SKILL.md").read_text(encoding="utf-8")
    assert "REFERENCE_BASE_NOT_FOUND" in txt
    assert "OFLM_REPO" in txt
    assert "check_refs.py" in txt


# ---------------------------------------------------------------- D2 / D7
@pytest.mark.skipif(not IS_WIN, reason="PowerShell requis")
def test_d2_sans_marqueur_ne_dit_jamais_zero():
    r = run_ps(AIE2P / "inspect_kernel.ps1", "-KernelPath", str(FIX / "sans_marqueur.s"), "-Lenient")
    assert r.returncode == 0
    assert "NOT_MEASURED" in r.stdout
    assert "Bundle max :       0" not in r.stdout
    assert "non classifi" in r.stdout


@pytest.mark.skipif(not IS_WIN, reason="PowerShell requis")
def test_d2_avec_marqueur_detecte_sept():
    r = run_ps(AIE2P / "inspect_kernel.ps1", "-KernelPath", str(FIX / "avec_marqueur.s"))
    assert "Bundle max :       7" in r.stdout


@pytest.mark.skipif(not IS_WIN, reason="PowerShell requis")
def test_d2_vide_et_mixte_signales():
    vide = run_ps(AIE2P / "inspect_kernel.ps1", "-KernelPath", str(FIX / "vide.s"), "-Lenient")
    assert "NOT_MEASURED" in vide.stdout
    mixte = run_ps(AIE2P / "inspect_kernel.ps1", "-KernelPath", str(FIX / "mixte.s"), "-Lenient")
    assert "PARTIELLE" in mixte.stdout


@pytest.mark.skipif(not IS_WIN, reason="PowerShell requis")
def test_d2_couverture_incomplete_sort_2_par_defaut():
    r = run_ps(AIE2P / "inspect_kernel.ps1", "-KernelPath", str(FIX / "sans_marqueur.s"))
    assert r.returncode == 2, r.stdout[-200:]
    ok = run_ps(AIE2P / "inspect_kernel.ps1", "-KernelPath", str(FIX / "ok.s"))
    assert ok.returncode == 0
    lenient = run_ps(AIE2P / "inspect_kernel.ps1", "-KernelPath",
                     str(FIX / "sans_marqueur.s"), "-Lenient")
    assert lenient.returncode == 0


@pytest.mark.skipif(not IS_WIN, reason="PowerShell requis")
def test_d2_interface_lenient_sans_pseudo_strict():
    """Fige l'interface RÉELLE : défaut strict, `-Lenient` en opt-out.

    L'audit affirmait une option `-Strict` → exit 2 : elle n'existe pas.
    """
    txt = (AIE2P / "inspect_kernel.ps1").read_text(encoding="utf-8", errors="replace")
    assert "[switch]$Lenient" in txt, "paramètre -Lenient absent : opt-out introuvable"
    assert "Strict" not in txt, "option -Strict annoncée par l'audit mais absente du script"
    r = run_ps(AIE2P / "inspect_kernel.ps1", "-KernelPath",
               str(FIX / "sans_marqueur.s"), "-Strict")
    assert r.returncode == 1, "un paramètre inexistant doit échouer (exit 1), pas produire un verdict"
    assert "Strict" in (r.stderr or "") + (r.stdout or "")


@pytest.mark.skipif(not IS_WIN, reason="PowerShell requis")
def test_d7_mac_comptes_par_occurrence():
    r = run_ps(AIE2P / "inspect_kernel.ps1", "-KernelPath", str(FIX / "sans_marqueur.s"), "-Lenient")
    assert "Nombre de MAC :    4" in r.stdout, r.stdout


# ---------------------------------------------------------------- D3
def test_d3_ancien_nom_supprime_et_doc_corrigee():
    assert not (AIE2P / "validate_kernel.ps1").exists()
    assert (AIE2P / "new_validation_report.ps1").exists()
    txt = (SKILLS / "aie2p-hand-asm-debug" / "SKILL.md").read_text(encoding="utf-8")
    assert "Lancer la validation A/B" not in txt
    assert "GABARIT MANUEL" in txt


@pytest.mark.skipif(not IS_WIN, reason="PowerShell requis")
def test_d3_script_sort_3_et_ne_fabrique_pas_de_resultat(tmp_path):
    a, b = tmp_path / "base.xclbin", tmp_path / "fix.xclbin"
    a.write_bytes(b"BASE")
    b.write_bytes(b"FIX!")
    r = run_ps(AIE2P / "new_validation_report.ps1", "-BaselineXclbin", str(a),
               "-FixXclbin", str(b), "-ModelPath", str(tmp_path / "m.gguf"),
               "-OutputDir", str(tmp_path / "out"))
    assert r.returncode == 3, r.stdout
    rapport = next((tmp_path / "out").glob("rapport_validation_*.md"))
    body = rapport.read_text(encoding="utf-8", errors="replace")
    assert "PASS" in body and "[Paste la sortie qdump" in body  # gabarit, pas résultat
    assert "UNKNOWN" in r.stdout


# ---------------------------------------------------------------- D4
def test_d4_mention_perimee_corrigee():
    txt = (SKILLS / "evidence" / "SKILL.md").read_text(encoding="utf-8")
    assert "existe et répond" in txt
    assert "peut ne pas exister encore → le documenter comme à venir" not in txt
    assert "CORRIGÉ 18/10/2026" in txt


# ---------------------------------------------------------------- D5
def test_d5_preflight_mlir_aie_deux_plateformes():
    """Le préflight ne conclut jamais depuis une seule plateforme."""
    r = subprocess.run([sys.executable, str(QWEN36 / "scripts" / "preflight_mlir_aie.py"), "--json"],
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode in (0, 3, 4), r.stdout
    data = json.loads(r.stdout)
    assert data["status"] in ("PREREQUIS_OK", "PREREQUIS_MANQUANTS", "AUCUNE_PLATEFORME")
    plateformes = {p["plateforme"]: p for p in data["plateformes"]}
    assert set(plateformes) & {"windows", "wsl"}
    if data["status"] == "PREREQUIS_OK":
        assert data["plateforme_utilisable"]
        for nom in data["plateforme_utilisable"]:
            assert plateformes[nom]["manquants"] == []
    else:
        assert any(p.get("manquants") for p in data["plateformes"])


def test_d5_wsl_force_reste_signale_comme_incomplet():
    r = subprocess.run([sys.executable, str(QWEN36 / "scripts" / "preflight_mlir_aie.py"),
                        "--platform", "wsl", "--json"],
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    data = json.loads(r.stdout)
    assert data["status"] in ("PREREQUIS_MANQUANTS", "AUCUNE_PLATEFORME")
    if data["status"] == "PREREQUIS_MANQUANTS":
        assert data["plateformes"][0]["manquants"]


def test_d5_les_trois_skills_noyaux_referencent_le_preflight():
    for name in ("open-qwen36-kernels", "open-phi3-nanbeige-kernels", "open-granite-kernels"):
        txt = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
        assert "preflight_mlir_aie.py" in txt or "Test-Path C:\\Xilinx\\XRT" in txt, name


# ---------------------------------------------------------------- D6
def _load_generator():
    path = ORACLE / "scripts" / "generate_evidence.py"
    spec = importlib.util.spec_from_file_location("generate_evidence", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _validator():
    path = PATHEXP / "scripts" / "validate_cost_model.py"
    spec = importlib.util.spec_from_file_location("validate_cost_model", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_d6_le_cost_model_du_generateur_est_valide():
    model = json.loads(json.dumps(_load_generator().COST_MODEL, default=str))
    assert _validator().validate(model) == []


def test_d6_refuse_unite_invalide_et_valeur_inventee():
    v = _validator()
    model = json.loads(json.dumps(_load_generator().COST_MODEL, default=str))
    model["metrics"]["submit_us"]["unit"] = "furlongs"
    assert any("UNITE_INVALIDE" in r for r in v.validate(model))
    model = json.loads(json.dumps(_load_generator().COST_MODEL, default=str))
    model["metrics"]["wait_us"]["value"] = 12.5
    assert any("VALEUR_SANS_MESURE" in r for r in v.validate(model))
    model["metrics"]["wait_us"]["status"] = "MEASURED"
    assert not any("VALEUR_SANS_MESURE" in r for r in v.validate(model))


def test_d6_champ_manquant_et_valeur_non_numerique():
    v = _validator()
    model = json.loads(json.dumps(_load_generator().COST_MODEL, default=str))
    del model["metrics"]["total_us"]
    assert any("METRICS_MANQUANTS" in r for r in v.validate(model))
    model = json.loads(json.dumps(_load_generator().COST_MODEL, default=str))
    model["metrics"]["compute_us"]["value"] = "beaucoup"
    assert any("VALEUR_NON_NUMERIQUE" in r for r in v.validate(model))


def test_d6_cli_absent_et_invalide(tmp_path):
    r = subprocess.run([sys.executable, str(PATHEXP / "scripts" / "validate_cost_model.py"),
                        str(tmp_path / "nope.json")], capture_output=True, text=True)
    assert r.returncode == 2
    bad = tmp_path / "bad.json"
    bad.write_text("{pas json}", encoding="utf-8")
    r = subprocess.run([sys.executable, str(PATHEXP / "scripts" / "validate_cost_model.py"),
                        str(bad)], capture_output=True, text=True)
    assert r.returncode == 5


# ---------------------------------------------------------------- D8
def test_d8_chaque_script_oracle_est_documente():
    txt = (ORACLE / "SKILL.md").read_text(encoding="utf-8")
    for py in (ORACLE / "scripts").glob("*.py"):
        assert py.name in txt, f"script non documenté : {py.name}"


# ---------------------------------------------------------------- contrat git
def test_contrat_git_enregistre_dans_les_instructions():
    here = Path(__file__).resolve().parent.parent
    candidates = [here / "AGENTS.md", Path.home() / "Desktop" / "doc-skill-xdna2-work" / "AGENTS.md"]
    found = [p for p in candidates if p.is_file() and "AUTORISATION GIT" in p.read_text(encoding="utf-8")]
    assert found, "le contrat d'autorisation git n'est enregistré dans aucun fichier d'instructions chargé"


# ---------------------------------------------------------------- statut unique
@pytest.mark.skipif(not IS_WIN, reason="PowerShell requis")
def test_statut_unique_par_fixture():
    attendus = {"sans_marqueur": "NOT_MEASURED", "mixte": "PARTIAL",
                "avec_marqueur": "BUNDLE_LIMIT_EXCEEDED", "ok": "OK"}
    for nom, statut in attendus.items():
        r = run_ps(AIE2P / "inspect_kernel.ps1", "-KernelPath", str(FIX / f"{nom}.s"), "-Lenient")
        assert f"STATUS: {statut}" in r.stdout, (nom, r.stdout[-300:])


# ---------------------------------------------------------------- D6 exemple
def test_d6_exemple_livre_et_valide():
    exemple = PATHEXP / "examples" / "COST_MODEL.example.json"
    assert exemple.is_file()
    r = subprocess.run([sys.executable, str(PATHEXP / "scripts" / "validate_cost_model.py"),
                        str(exemple)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
    data = json.loads(exemple.read_text(encoding="utf-8"))
    assert all(m["value"] is None for m in data["metrics"].values() if "value" in m)


# ---------------------------------------------------------------- D5 procédure
def test_d5_procedure_reproductible_documentee():
    doc = QWEN36 / "docs" / "setup_mlir_aie_wsl.md"
    txt = doc.read_text(encoding="utf-8")
    assert "xilinx.github.io/mlir-aie" in txt
    assert "env_install.sh" in txt and "env_setup.sh" in txt
    assert "NON EXÉCUTÉE" in txt
    assert "setup_mlir_aie_wsl.md" in (QWEN36 / "SKILL.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------- dette nettoyée
def test_plus_aucune_instruction_vers_le_script_renomme():
    """La mention historique est autorisée (règle : corriger, jamais supprimer),
    mais aucun SKILL.md ne doit pointer le script par son chemin ni annoncer
    qu'il exécute la validation A/B."""
    for sk in SKILLS.iterdir():
        p = sk / "SKILL.md"
        if not p.is_file():
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        assert "scripts/validate_kernel.ps1" not in txt, sk.name
        assert "Lancer la validation A/B" not in txt, sk.name


def test_helper_mort_supprime_dans_les_trois_copies():
    copies = [
        SKILLS / "git-ecosystem-investigator" / "tests" / "test_negative.py",
        Path.home() / "Desktop" / "doc-skill-xdna2-work" / "skills" / "local" / "git-ecosystem-investigator" / "tests" / "test_negative.py",
        Path.home() / "Desktop" / "doc-skill-xdna2-work" / "skills_backup" / "opencode" / "git-ecosystem-investigator" / "tests" / "test_negative.py",
    ]
    for p in copies:
        if p.is_file():
            assert "def run_report" not in p.read_text(encoding="utf-8"), p


# ---------------------------------------------------------------- D6 synchro
def test_d6_metriques_generateur_et_validateur_synchronisees():
    """Détecte la dérive : les clés exigées par le validateur doivent être
    exactement celles produites par le générateur (dans les deux sens)."""
    gen = _load_generator()
    val = _validator()
    from_gen = set(gen.COST_MODEL["metrics"])
    from_val = set(val.REQUIRED_METRIC_KEYS)
    assert from_val - from_gen == set(), f"validateur exige des clés absentes du générateur : {from_val - from_gen}"
    assert from_gen - from_val == set(), f"générateur produit des clés non validées : {from_gen - from_val}"
    assert gen.COST_MODEL["schema_version"] == "1.0"


# ---------------------------------------------------------------- D5 exécution réelle
def test_d5_aiecc_compile_un_design_minimal(tmp_path):
    """Vérifie la chaîne de COMPILATION AIE (pas le NPU).

    Preuve machine conservée par `tools/aiecc_smoke_evidence.py` dans
    `audits/skills-fix-20261018/evidence/aiecc_smoke/runs/<UTC>/` (artefact,
    stdout/stderr, environnement, sha256). Ce test recompile pour prouver que
    la chaîne fonctionne aujourd'hui ; il ne prouve rien sur le NPU.
    """
    aiecc = shutil.which("aiecc")
    if not aiecc:
        pytest.skip("aiecc absent : chaîne AIE non installée")
    mlir = "\n".join([
        "module {",
        "  aie.device(npu1) {",
        "    %tile = aie.tile(0, 2)",
        "    aie.runtime_sequence() {",
        "      aie.end",
        "    }",
        "  }",
        "}",
        "",
    ])
    (tmp_path / "min.mlir").write_text(mlir, encoding="utf-8")
    r = subprocess.run([aiecc, "min.mlir", "--xclbin-name=out.xclbin", "--get-xclbin",
                        f"--output-dir={tmp_path / 'o'}"],
                       cwd=str(tmp_path), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    assert r.returncode == 0, (r.stdout[-800:], r.stderr[-400:])
    xcl = tmp_path / "o" / "out.xclbin"
    assert xcl.is_file(), list(tmp_path.rglob("*"))
    assert xcl.read_bytes()[:8] == b"xclbin2\x00"


# ------------------------------------- D5 preuve machine (aucune revendication NPU)
EVIDENCE = (Path(__file__).resolve().parent.parent / "audits" / "skills-fix-20261018"
            / "evidence" / "aiecc_smoke")
HARNESS = Path(__file__).resolve().parent.parent / "tools" / "aiecc_smoke_evidence.py"


def _latest_run():
    runs = sorted((EVIDENCE / "runs").glob("*/manifest.json"))
    return runs[-1] if runs else None


def test_evidence_aiecc_smoke_est_machine_et_complete():
    """Un manifeste TESTED doit porter commande, exit, sorties, env, artefact."""
    mf = _latest_run()
    if mf is None:
        pytest.skip("aucune preuve machine : lancer tools/aiecc_smoke_evidence.py")
    data = json.loads(mf.read_text(encoding="utf-8"))
    for key in ("scope", "status", "argv", "cwd", "exit", "duration_s",
                "aiecc", "env", "artifacts", "outputs", "limits"):
        assert key in data, key
    assert data["scope"] == "COMPILATION_ONLY_NO_NPU"
    assert data["status"] in {"TESTED", "NOT TESTED", "UNKNOWN"}
    assert any("NPU" in lim for lim in data["limits"])
    assert "PASS" not in json.dumps(data)  # aucun PASS sans exécution matérielle
    if data["status"] == "TESTED":
        run_dir = mf.parent
        assert Path(data["outputs"]["stdout"]).name in os.listdir(run_dir)
        assert Path(data["outputs"]["stderr"]).name in os.listdir(run_dir)
        assert data["aiecc"]["version"], "version d'aiecc non enregistrée"
        assert data["env"]["platform"]
        x = data["artifacts"]["xclbin"]
        kept = run_dir / x["path"]
        assert kept.is_file(), "artefact annoncé mais absent = preuve invalide"
        assert kept.stat().st_size == x["size"]
        assert hashlib.sha256(kept.read_bytes()).hexdigest() == x["sha256"]
        assert x["magic"] == "xclbin2"
        assert data["exit"] == 0


def test_evidence_check_only_refuse_un_artefact_altere(tmp_path):
    """`--check-only` doit sortir 3 si le sha256 ne correspond plus."""
    mf = _latest_run()
    if mf is None:
        pytest.skip("aucune preuve machine à vérifier")
    if json.loads(mf.read_text(encoding="utf-8"))["status"] != "TESTED":
        pytest.skip("dernière preuve non TESTED : rien à altérer")
    dst = tmp_path / "run"
    shutil.copytree(mf.parent, dst)
    xcl = dst / "out.xclbin"
    raw = bytearray(xcl.read_bytes())
    raw[-1] ^= 0xFF
    xcl.write_bytes(bytes(raw))
    spec = importlib.util.spec_from_file_location("aiecc_smoke_evidence", HARNESS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(["--check-only", str(dst)]) == 3
    assert mod.main(["--check-only", str(mf.parent)]) == 0
