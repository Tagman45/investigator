#!/usr/bin/env python3
"""aiecc_smoke_evidence.py — preuve MACHINE pour un build smoke `aiecc`.

Portée STRICTE : **compilation AIE uniquement**. Ce script ne prouve ni
l'exécution NPU, ni la latence, ni un débit, ni la validité d'un kernel du
projet. Aucun rapport n'est modifié : il écrit un dossier de preuve neuf.

Ce que produit chaque exécution (dans `runs/<UTC>/`), sans jamais écraser
une preuve existante :

    command.txt     commande exacte rejouable (argv complet, cwd)
    stdout.txt      sortie brute complète du build
    stderr.txt      sortie d'erreur brute complète
    env.txt         aiecc --version, chemin, python, plateforme, date
    min.mlir        design compilé (réutilisable tel quel)
    out.xclbin      ARTEFACT conservé (copie), avec taille + sha256
    xclbin_info.txt `xclbinutil --info` si disponible, sinon raison
    manifest.json   statuts + métadonnées, champ `status` explicite

Statuts écrits dans `status` :
    TESTED        build exit 0 ET artefact valide (magic `xclbin2`) conservé
    NOT TESTED    aiecc absent — rien n'a été exécuté
    UNKNOWN       build lancé mais échec, ou artefact absent/invalide

Sortie CLI : 0 = TESTED ; 2 = NOT TESTED ; 3 = UNKNOWN.

Usage :
    python tools/aiecc_smoke_evidence.py
    python tools/aiecc_smoke_evidence.py --root <dossier_evidence>
    python tools/aiecc_smoke_evidence.py --check-only <run_dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_ROOT = REPO / "audits" / "skills-fix-20261018" / "evidence" / "aiecc_smoke"

MAGIC = b"xclbin2\x00"

MIN_MLIR = "\n".join([
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

SCOPE = "COMPILATION_ONLY_NO_NPU"
REQUIRED_KEYS = (
    "schema", "scope", "status", "argv", "cwd", "exit", "duration_s",
    "aiecc", "env", "artifacts", "outputs", "limits",
)

EXIT_TESTED = 0
EXIT_NOT_TESTED = 2
EXIT_UNKNOWN = 3


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _aiecc_version(exe: str) -> dict:
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        return {"path": exe, "version_exit": r.returncode,
                "version": (r.stdout or "").strip() or (r.stderr or "").strip()}
    except Exception as exc:  # noqa: BLE001 — l'échec doit être enregistré, pas masqué
        return {"path": exe, "version_exit": None, "version": f"ERREUR: {exc}"}


def _xclbin_info(xcl: Path) -> tuple[str, str]:
    util = shutil.which("xclbinutil")
    if not util:
        return "OUTIL_ABSENT: xclbinutil introuvable sur le PATH (aucune sortie)", "NOT TESTED"
    r = subprocess.run([util, "--info", "--input", str(xcl)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    txt = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr else "")
    return txt, f"exit {r.returncode}"


def run(root: Path) -> int:
    exe = shutil.which("aiecc")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = root / "runs" / stamp
    if run_dir.exists():
        print(f"REFUS: {run_dir} existe déjà — aucune preuve écrasée", file=sys.stderr)
        return EXIT_UNKNOWN
    run_dir.mkdir(parents=True)

    env_info = {
        "date_utc": stamp,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
    }
    (run_dir / "min.mlir").write_text(MIN_MLIR, encoding="utf-8")

    if not exe:
        manifest = {
            "schema": 1, "scope": SCOPE, "status": "NOT TESTED",
            "argv": None, "cwd": None, "exit": None, "duration_s": None,
            "aiecc": {"path": None, "version_exit": None, "version": None},
            "env": env_info,
            "artifacts": {"mlir": "min.mlir"},
            "outputs": {},
            "limits": ["aiecc introuvable sur le PATH : aucun build exécuté",
                       "aucune conclusion NPU/latence/débit"],
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                               encoding="utf-8")
        print(f"NOT TESTED — aiecc absent. Preuve: {run_dir}", file=sys.stderr)
        return EXIT_NOT_TESTED

    out_dir = run_dir / "o"
    argv = [exe, "min.mlir", "--xclbin-name=out.xclbin", "--get-xclbin",
            f"--output-dir={out_dir}"]
    (run_dir / "command.txt").write_text(
        "cwd: " + str(run_dir) + "\n" + " ".join(f'"{a}"' if " " in a else a for a in argv) + "\n",
        encoding="utf-8")

    t0 = time.perf_counter()
    r = subprocess.run(argv, cwd=str(run_dir), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    duration = round(time.perf_counter() - t0, 3)

    (run_dir / "stdout.txt").write_text(r.stdout or "", encoding="utf-8")
    (run_dir / "stderr.txt").write_text(r.stderr or "", encoding="utf-8")

    gen = _aiecc_version(exe)
    (run_dir / "env.txt").write_text(
        "\n".join([
            f"date_utc: {stamp}",
            f"python: {env_info['python']}",
            f"platform: {env_info['platform']}",
            f"aiecc: {gen['path']}",
            f"aiecc --version (exit {gen['version_exit']}):",
            str(gen["version"]),
            "",
        ]), encoding="utf-8")

    produced = out_dir / "out.xclbin"
    artifacts: dict = {"mlir": {"path": "min.mlir", "size": (run_dir / "min.mlir").stat().st_size}}
    status = "UNKNOWN"
    note = ""

    if produced.is_file():
        kept = run_dir / "out.xclbin"
        shutil.copyfile(produced, kept)
        head = kept.read_bytes()[:8]
        artifacts["xclbin"] = {
            "path": "out.xclbin",
            "size": kept.stat().st_size,
            "sha256": _sha256(kept),
            "magic": head[:7].decode("ascii", "replace"),
            "magic_ok": head == MAGIC,
        }
        info_txt, info_status = _xclbin_info(kept)
        (run_dir / "xclbin_info.txt").write_text(info_txt, encoding="utf-8")
        artifacts["xclbin_info"] = {"path": "xclbin_info.txt", "status": info_status}
        if r.returncode == 0 and head == MAGIC:
            status = "TESTED"
        else:
            note = f"build exit={r.returncode}, magic_ok={head == MAGIC}"
    else:
        note = "out.xclbin non produit"

    manifest = {
        "schema": 1,
        "scope": SCOPE,
        "status": status,
        "argv": argv,
        "cwd": str(run_dir),
        "exit": r.returncode,
        "duration_s": duration,
        "aiecc": gen,
        "env": env_info,
        "artifacts": artifacts,
        "outputs": {"stdout": "stdout.txt", "stderr": "stderr.txt", "command": "command.txt"},
        "limits": [
            "COMPILATION uniquement : aucune exécution NPU, aucune mesure de latence ou de débit",
            "design smoke trivial (1 tile, runtime_sequence vide) : ne valide aucun kernel du projet",
            "le statut porte sur ce build précis, pas sur l'environnement global",
        ],
    }
    if note:
        manifest["failure_note"] = note

    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8")

    print(f"status={status} exit={r.returncode} duree={duration}s")
    if "xclbin" in artifacts:
        x = artifacts["xclbin"]
        print(f"artefact=out.xclbin size={x['size']} sha256={x['sha256'][:16]}… magic={x['magic']}")
    if note:
        print(f"note: {note}", file=sys.stderr)
    print(f"preuve: {run_dir}")
    return EXIT_TESTED if status == "TESTED" else EXIT_UNKNOWN


def check_only(run_dir: Path) -> int:
    """Valide la structure d'un manifeste existant (aucun build, aucune écriture)."""
    mf = run_dir / "manifest.json"
    if not mf.is_file():
        print(f"REFUS: manifeste absent: {mf}", file=sys.stderr)
        return EXIT_UNKNOWN
    data = json.loads(mf.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        print(f"INVALIDE: clés manquantes {missing}", file=sys.stderr)
        return EXIT_UNKNOWN
    if data["status"] == "TESTED":
        x = data.get("artifacts", {}).get("xclbin") or {}
        kept = run_dir / str(x.get("path", ""))
        if not kept.is_file():
            print(f"INVALIDE: artefact annoncé absent: {kept}", file=sys.stderr)
            return EXIT_UNKNOWN
        if _sha256(kept) != x.get("sha256"):
            print("INVALIDE: sha256 de l'artefact différent du manifeste", file=sys.stderr)
            return EXIT_UNKNOWN
    print(f"OK status={data['status']} scope={data['scope']}")
    return EXIT_TESTED


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Preuve machine d'un build smoke aiecc (compilation seule).")
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                    help="dossier de preuve (défaut: audits/skills-fix-20261018/evidence/aiecc_smoke)")
    ap.add_argument("--check-only", type=Path, metavar="RUN_DIR",
                    help="valider un manifeste existant, sans rien construire ni écrire")
    ns = ap.parse_args(argv)
    if ns.check_only:
        return check_only(ns.check_only)
    return run(ns.root)


if __name__ == "__main__":
    sys.exit(main())
