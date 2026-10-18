#!/usr/bin/env python3
"""audit_preflight_order.py — le pré-vol de dimensionnement peut-il être contourné ?

Contrôle STATIQUE (AST, aucune exécution NPU) que, dans chaque script d'allocation :

 1. un appel de pré-vol précède la **première allocation réelle** — dans la même
    fonction s'il y en a une, sinon au niveau module ;
 2. les **allocations indirectes** (appel à une fonction locale qui alloue, y compris
    transitive) sont couvertes par le même ordre ;
 3. les chemins d'**exception** sont identifiés : `allow_undersized=True` littéral
    (opt-out assumé) est distingué d'un opt-out piloté par un drapeau CLI ;
 4. les **alias d'API** (`x = pyxrt.bo`, `getattr(pyxrt, "bo")`) sont signalés comme
    chemins non couverts par l'analyse textuelle.

Le contrôle ne prétend pas prouver l'absence de tout chemin indirect (Python est
dynamique) : il produit la liste des points où l'analyse est INCERTAINE, jamais un
faux PASS. Exit 0 = aucun défaut ; 3 = au moins un défaut ; 2 = erreur d'analyse.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys

ALLOC_ATTRS = {"bo"}                 # pyxrt.bo(...)
ALLOC_FUNCS = {"alloc"}              # npu_exp.alloc / E.alloc
PREFLIGHT_NAMES = {"preflight", "preflight_historical"}
PREFLIGHT_CHECK = "check"            # npu_preflight.check(...)


def _name(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _name(node.func)
    return ""


def _base(node) -> str:
    """Nom de base d'une expression d'appel : E.alloc -> 'E', npu_preflight.check -> 'npu_preflight'."""
    if isinstance(node, ast.Attribute):
        return _name(node.value)
    return ""


def scan_file(path: str) -> dict:
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src, filename=path)
    funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

    def analyse(node_ast, label: str) -> dict:
        """Événements ordonnés (ligne) d'une fonction ou du module."""
        events = {"alloc": [], "preflight": [], "indirect": [], "alias": []}
        for n in ast.walk(node_ast):
            if isinstance(n, ast.Call):
                fn = _name(n.func)
                base = _base(n.func)
                if fn in ALLOC_ATTRS and base in {"pyxrt", "xrt", ""}:
                    events["alloc"].append(n.lineno)
                elif fn in ALLOC_FUNCS:
                    # alloue si c'est notre wrapper (E.alloc / alloc module-level)
                    events["alloc"].append(n.lineno)
                elif fn in PREFLIGHT_NAMES or (fn == PREFLIGHT_CHECK and base == "npu_preflight"):
                    kw = {k.arg: k.value for k in n.keywords}
                    allow = kw.get("allow_undersized")
                    mode = "flag_driven"
                    if isinstance(allow, ast.Constant) and allow.value is True:
                        mode = "opt_out_litteral"
                    elif allow is None:
                        mode = "defaut_refus"
                    events["preflight"].append({"line": n.lineno, "mode": mode})
            elif isinstance(n, ast.Assign):
                # alias : bo = pyxrt.bo   /  alloc = E.alloc
                for t in n.targets:
                    if isinstance(t, ast.Name) and _name(n.value) in ALLOC_ATTRS | ALLOC_FUNCS:
                        events["alias"].append(n.lineno)
            elif isinstance(n, ast.Call) and _name(n.func) == "getattr":
                if any(isinstance(a, ast.Constant) and a.value in ALLOC_ATTRS | ALLOC_FUNCS
                       for a in n.args):
                    events["alias"].append(n.lineno)
        # perimètre déclaré (declare_scope / preflight_historical = borne assumée)
        for n in ast.walk(node_ast):
            if isinstance(n, ast.Call) and _name(n.func) in {"declare_scope",
                                                            "preflight_historical"}:
                events.setdefault("scope", []).append(n.lineno)
            if isinstance(n, ast.Raise):
                nm = _name(n.exc) if n.exc is not None else ""
                if nm in {"UnscopedAllocationError", "UndersizedBufferError"}:
                    events.setdefault("guard_internal", []).append(n.lineno)
        # appels indirects : appel à une fonction locale qui alloue (transitif plus bas)
        calls = set()
        for n in ast.walk(node_ast):
            if isinstance(n, ast.Call) and _name(n.func) in funcs:
                calls.add((_name(n.func), n.lineno))
        return {"events": events, "calls": sorted(calls), "label": label}

    # 1re passe : quelles fonctions allouent (transitivement) ?
    first = {name: analyse(node, name) for name, node in funcs.items()}
    # Le pseudo-niveau module ne doit contenir QUE le code de premier niveau :
    # analyser l'arbre entier dupliquait le corps des fonctions et produisait un
    # faux DEFAUT_ORDRE sur chaque fichier (chaque allocation interne était vue
    # « avant » le pre-vol de module). Mesure du 18/10 : 9 faux defauts.
    module_only = ast.Module(body=[s for s in tree.body
                                   if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))],
                             type_ignores=[])
    first["<module>"] = analyse(module_only, "<module>")
    # Une fonction qui alloue peut se protéger ELLE-MÊME (pre-vol avant son premier
    # déclencheur). Dans ce cas ses appelants n'ont rien à protéger — sinon chaque
    # appel depuis main() serait un faux défaut (mesuré 18/10 : 9 faux positifs).
    def first_line(v, kind):
        xs = [d["line"] if isinstance(d, dict) else d for d in v["events"].get(kind, [])]
        return min(xs) if xs else None

    def self_protected(v) -> bool:
        pf = [d["line"] for d in v["events"]["preflight"]]
        trig = [ln for ln in v["events"]["alloc"]]
        if not pf or not trig:
            return False
        return min(pf) < min(trig)

    def internal_guard(v) -> bool:
        """La fonction refuse elle-même l'allocation (garde-fou dans le wrapper)."""
        return bool(v["events"].get("guard_internal"))

    def scope_before_alloc(v) -> bool:
        """declare_scope() posé avant la première allocation propre : périmètre assumé."""
        scope = v["events"].get("scope", [])
        alloc = v["events"]["alloc"]
        return bool(scope and alloc and min(scope) < min(alloc))

    _memo: dict = {}

    def protected_callee(name) -> bool:
        """Un appelant n'a rien à protéger si le callee se protège (directement ou
        parce que tous ses propres callees allouants le font). Récursif, mémoïsé ;
        un callee inconnu (import externe) est considéré NON accusable."""
        if name in _memo:
            return _memo[name]
        _memo[name] = False  # garde anti-récursion
        v = first.get(name)
        if v is None:
            _memo[name] = True
        elif self_protected(v) or internal_guard(v):
            _memo[name] = True
        elif v["events"]["alloc"] and not scope_before_alloc(v):
            _memo[name] = False
        else:
            _memo[name] = all(protected_callee(c) for c, _ln in v["calls"]
                              if alloc_trans.get(c))
        return _memo[name]

    alloc_direct = {k: bool(v["events"]["alloc"] or v["events"]["alias"])
                    for k, v in first.items()}
    changed = True
    alloc_trans = dict(alloc_direct)
    while changed:  # point fixe des appels transitifs
        changed = False
        for name, v in first.items():
            if alloc_trans.get(name):
                continue
            for callee, _ln in v["calls"]:
                if alloc_trans.get(callee):
                    alloc_trans[name] = True
                    changed = True
                    break

    report = {"file": os.path.basename(path), "functions": [], "defauts": [],
              "incertitudes": []}
    for name, v in first.items():
        ev = v["events"]
        # Déclencheurs RÉELS : allocations propres + appels à un callee qui alloue et
        # NE se protège PAS lui-même (un callee auto-protégé couvre son appelant).
        trigger = [("alloc", ln) for ln in ev["alloc"]]
        trigger += [("indirect", ln) for callee, ln in v["calls"]
                    if alloc_trans.get(callee) and not protected_callee(callee)]
        own_alloc = bool(ev["alloc"])
        alias_only = bool(ev["alias"]) and not own_alloc
        if not trigger and not alias_only:
            continue
        trigger.sort(key=lambda t: t[1])
        pf = sorted(ev["preflight"], key=lambda d: d["line"])
        scope = sorted(ev.get("scope", []))
        first_trigger = trigger[0] if trigger else None
        before = [d for d in pf if first_trigger and d["line"] < first_trigger[1]]
        modes = sorted({d["mode"] for d in pf})
        if alias_only:
            verdict = "ALIAS_SEUL"
        elif not trigger:
            verdict = "PASS_ORDRE"
        elif internal_guard(v):
            verdict = "GARDE_INTERNE"        # le wrapper refuse lui-même

        elif before:
            verdict = "PASS_ORDRE"
        elif scope and (first_trigger is None or min(scope) < first_trigger[1]):
            verdict = "PERIMETRE_DECLARE"      # hors contrat : motif journalisé
        else:
            verdict = "DEFAUT_ORDRE" if pf else "DEFAUT_ABSENT"
        entry = {"unite": name, "premier_declencheur": first_trigger,
                 "pre_vol_lignes": [d["line"] for d in pf], "modes": modes,
                 "perimetre_declare_lignes": scope, "verdict": verdict}
        report["functions"].append(entry)
        if verdict.startswith("DEFAUT"):
            report["defauts"].append(entry)
        elif verdict == "GARDE_INTERNE":
            report["incertitudes"].append(
                {**entry, "note": "garde-fou interne (raise) : chemin couvert par le wrapper"})
        elif verdict == "ALIAS_SEUL":
            report["incertitudes"].append(
                {**entry, "note": "alias seul (aucune allocation propre) — "
                                   "couverture textuelle non garantie"})
        elif verdict == "PERIMETRE_DECLARE":
            report["incertitudes"].append(
                {**entry, "note": "alloue hors contrat des descripteurs (perimetre declare)"})
        elif "opt_out_litteral" in modes:
            report["incertitudes"].append(
                {**entry, "note": "pre-vol en opt-out litteral (mode borne declare)"})
        if ev["alias"]:
            report["incertitudes"].append(
                {"unite": name, "alias_lignes": ev["alias"],
                 "note": "alias d'API d'allocation : couverture textuelle non garantie"})
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--json", default=None)
    ns = ap.parse_args()

    files = sorted(f for f in os.listdir(ns.dir)
                   if f.endswith(".py") and f != "audit_preflight_order.py")
    docs, defects, uncertain, hors_perimetre = [], 0, 0, 0
    for f in files:
        try:
            r = scan_file(os.path.join(ns.dir, f))
        except SyntaxError as exc:
            print(f"  {f:<24} ERREUR D'ANALYSE: {exc}")
            continue
        if not r["functions"] and not r["incertitudes"]:
            continue
        # Les fichiers de test EXERCENT délibérément les refus (appeler alloc sans
        # pré-vol est leur objet) : leurs défauts sont reportés mais comptés à part,
        # jamais ignorés en silence et jamais transformés en PASS.
        r["perimetre"] = "TEST" if f.startswith("test_") else "PRODUCTION"
        docs.append(r)
        if r["perimetre"] == "TEST":
            hors_perimetre += len(r["defauts"])
        else:
            defects += len(r["defauts"])
        uncertain += len(r["incertitudes"])
        tag = "OK" if not r["defauts"] else ("DEFAUT" if r["perimetre"] == "PRODUCTION"
                                             else "DEFAUT_TEST")
        print(f"  {f:<24} {tag:<7} unites={len(r['functions'])} "
              f"defauts={len(r['defauts'])} incertitudes={len(r['incertitudes'])}")
        for e in r["defauts"]:
            print(f"      !! {e['unite']}: declencheur={e['premier_declencheur']} "
                  f"pre_vol={e['pre_vol_lignes']} -> {e['verdict']}")
        for e in r["incertitudes"]:
            print(f"      ?? {e['unite']}: {e.get('note')} "
                  f"lignes={e.get('alias_lignes', e.get('pre_vol_lignes'))}")

    print(f"\nfichiers analyses : {len(docs)}   defauts (production) : {defects}   "
          f"defauts (fichiers de test, attendus) : {hors_perimetre}   incertitudes : {uncertain}")
    out = {"dir": ns.dir, "files": docs, "n_defauts": defects,
           "n_defauts_fichiers_de_test": hors_perimetre, "n_incertitudes": uncertain,
           "verdict": "PASS_ORDRE_GLOBAL" if defects == 0 else "DEFAUT_ORDRE_GLOBAL"}
    print(f"VERDICT: {out['verdict']}")
    if ns.json:
        with open(ns.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, ensure_ascii=False)
        print(f"JSON: {ns.json}")
    return 0 if defects == 0 else 3


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
