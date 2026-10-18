#!/usr/bin/env python3
"""npu_probe.py — sonde pas-à-pas du chemin réel NPU sur Windows.

Objectif : identifier le PREMIER point non validé du chemin
`Windows → pilote → XRT → chargement xclbin → contexte → soumission → NPU`.
Chaque étape est chronométrée et son échec est rapporté tel quel (jamais un
succès supposé). Sortie JSON + texte lisible.

Statuts par étape : OK | FAIL | SKIP
Statut global     : TESTED (toutes étapes OK) | BLOCKED (premier échec) | UNKNOWN

Usage :
    python npu_probe.py --xclbin <fichier.xclbin> [--kernel <nom>] [--json <sortie>]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback

# Console Windows en cp1252 : forcer UTF-8 sinon toute flèche/accent casse la sortie.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — pas bloquant sur les plateformes sans reconfigure
        pass

STEPS: list[dict] = []


def step(name: str, fn, *args, **kwargs):
    """Exécute une étape, mesure sa durée, capture l'échec exact."""
    t0 = time.perf_counter()
    try:
        value = fn(*args, **kwargs)
        dt = time.perf_counter() - t0
        STEPS.append({"step": name, "status": "OK", "duration_ms": round(dt * 1000, 3),
                      "value": _short(value)})
        print(f"[OK]   {name:38s} {dt * 1000:9.3f} ms  {_short(value)}")
        return value
    except BaseException as exc:  # noqa: BLE001 — l'échec doit être enregistré, pas masqué
        dt = time.perf_counter() - t0
        STEPS.append({"step": name, "status": "FAIL", "duration_ms": round(dt * 1000, 3),
                      "error_type": type(exc).__name__, "error": str(exc)[:400],
                      "traceback": traceback.format_exc()[-800:]})
        print(f"[FAIL] {name:38s} {dt * 1000:9.3f} ms  {type(exc).__name__}: {str(exc)[:200]}",
              file=sys.stderr)
        return None


def _short(v) -> str:
    if v is None:
        return "None"
    s = repr(v)
    return s if len(s) < 160 else s[:157] + "…"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xclbin", required=True)
    ap.add_argument("--kernel", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--no-run", action="store_true", help="s'arrêter avant la soumission")
    ns = ap.parse_args(argv)

    import pyxrt  # noqa: PLC0415 — import local : l'absence doit apparaître comme un FAIL

    print(f"pyxrt   : {getattr(pyxrt, '__file__', '?')}")
    print(f"python  : {sys.version.split()[0]}")
    print(f"xclbin  : {ns.xclbin}")
    print(f"kernel  : {ns.kernel}")
    print("-" * 100)

    dev = step("pyxrt.device(0)", pyxrt.device, 0)
    if dev is not None:
        step("device.get_info(name)", dev.get_info, pyxrt.xrt_info_device.name)
        step("device.get_info(bdf)", dev.get_info, pyxrt.xrt_info_device.bdf)

    xclbin = step("pyxrt.xclbin(path)", pyxrt.xclbin, ns.xclbin)
    uuids = None
    if xclbin is not None:
        # pyxrt 2.21.0 Windows expose `get_uuid()` (pas `get_uuids()`) : on essaie les deux.
        for fn_name in ("get_uuid", "get_uuids"):
            fn = getattr(xclbin, fn_name, None)
            if fn is None:
                continue
            got = step(f"xclbin.{fn_name}()", fn)
            if got is not None:
                try:  # pyxrt renvoie soit une liste, soit un objet `pyxrt.uuid`
                    uuids = list(got)
                except TypeError:
                    uuids = [got]
                if uuids:
                    break

    if dev is None or xclbin is None or not uuids:
        _report("BLOCKED", ns)
        return 3

    uuid = uuids[0]
    registered = step("device.register_xclbin(xclbin)", dev.register_xclbin, xclbin)
    hwctx = step("pyxrt.hw_context(dev, uuid)", pyxrt.hw_context, dev, uuid)
    if hwctx is None:
        _report("BLOCKED", ns)
        return 3

    names = []
    objs = []
    for fn_name in ("get_kernels", "get_kernel_names"):
        fn = getattr(xclbin, fn_name, None)
        if fn:
            got = step(f"xclbin.{fn_name}()", fn)
            if got:
                objs = list(got)
                break
    for obj in objs:
        name = getattr(obj, "name", None)
        if name is None and hasattr(obj, "get_name"):
            name = step("kernel_obj.get_name()", obj.get_name)
        if isinstance(name, str):
            names.append(name)
        else:
            names.append(str(obj))
    if objs:
        print(f"       attributs noyau: {[a for a in dir(objs[0]) if not a.startswith('_')]}")

    kname = ns.kernel or (names[0] if names else None)
    if kname is None:
        print("[FAIL] aucun nom de kernel : xclbin AIE-only sans symbole noyau "
              "(sections AIE_PARTITION/IP_LAYOUT seules) — soumettre via ce chemin est impossible",
              file=sys.stderr)
        STEPS.append({"step": "kernel name", "status": "FAIL",
                      "error": "xclbin sans nom de kernel : chemin pyxrt.kernel inapplicable"})
        _report("BLOCKED", ns)
        return 3

    kern = step(f"pyxrt.kernel(hwctx, {kname})", pyxrt.kernel, hwctx, kname)
    if kern is None:
        _report("BLOCKED", ns)
        return 3

    # Signature réelle du kernel : indispensable pour ne pas soumettre « à vide »
    nargs = step("kernel.get_num_args()", kern.get_num_args) if hasattr(kern, "get_num_args") else None
    if nargs is not None:
        for i in range(int(nargs)):
            getter = getattr(kern, "get_arg", None)
            if getter is None:
                break
            arg = step(f"kernel.get_arg({i})", getter, i)
            if arg is not None:
                print(f"       arg[{i}]: name={getattr(arg, 'name', '?')} "
                      f"type={getattr(arg, 'type', '?')} size={getattr(arg, 'size', '?')}")

    if ns.no_run:
        _report("BLOCKED" if any(s["status"] == "FAIL" for s in STEPS) else "TESTED", ns)
        return 0 if not any(s["status"] == "FAIL" for s in STEPS) else 3

    run = step("kernel(...) — soumission", kern)
    state = None
    if run is not None:
        state = step("run.wait() — synchronisation", run.wait)

    # Un `run.wait()` qui répond n'est PAS un succès : seul ERT_CMD_STATE_COMPLETED l'est.
    completed = str(getattr(state, "name", "")) == "ERT_CMD_STATE_COMPLETED"
    if run is None:
        status = "BLOCKED"
    elif completed:
        status = "TESTED"
    else:
        status = "FAILED_AT_EXECUTION"
        STEPS.append({"step": "verdict d'exécution", "status": "FAIL",
                      "error": f"état retourné par le matériel : {state} (attendu ERT_CMD_STATE_COMPLETED)"})
    _report(status, ns)
    return 0 if status == "TESTED" else 3


def _report(status: str, ns) -> None:
    doc = {"status": status, "xclbin": ns.xclbin, "kernel": ns.kernel,
           "steps": STEPS,
           "premier_echec": next((s for s in STEPS if s["status"] == "FAIL"), None)}
    print("-" * 100)
    print(f"STATUS GLOBAL: {status}")
    if doc["premier_echec"]:
        e = doc["premier_echec"]
        print(f"PREMIER BLOCAGE: {e['step']} → {e.get('error_type')}: {e.get('error')}")
    if ns.json:
        with open(ns.json, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
        print(f"preuve JSON: {ns.json}")


if __name__ == "__main__":
    sys.exit(main())
