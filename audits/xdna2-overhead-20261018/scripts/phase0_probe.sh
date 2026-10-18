#!/usr/bin/env bash
# Phase 0 — sondes d'environnement, codes de sortie distincts, aucun pipe masquant.
# Bloc exécuté verbatim (fourni par l'utilisateur le 18/10/2026).
set +e
echo "=== ENVIRONNEMENT ==="
printf 'cwd='; pwd
printf 'uname='; uname -a
printf 'date='; date -Iseconds

probe() {
  echo
  echo "=== $1 ==="
  shift
  "$@"
  rc=$?
  echo "EXIT=$rc"
}

probe python_version python --version
probe python_py xrt-smi --version
probe xrt_smi_report xrt-smi examine
probe xclbinutil_help xclbinutil --help
probe aiecc_version aiecc --version
probe git_version git --version
probe sha256_version sha256sum --version

echo
echo "=== PYXRT ==="
python -c "import pyxrt; print('pyxrt_file=',pyxrt.__file__); print('pyxrt_import=OK')"
echo "EXIT_PYXRT=$?"

echo
echo "=== PYTHON MODULES ==="
python -m pip show pyxrt
echo "EXIT_PIP_SHOW_PYXRT=$?"

echo
echo "=== REPOSITORY ==="
git -C /c/Users/videl/skills-audit-reports rev-parse --show-toplevel
echo "EXIT_GIT_ROOT=$?"
git -C /c/Users/videl/skills-audit-reports status --short
echo "EXIT_GIT_STATUS=$?"
