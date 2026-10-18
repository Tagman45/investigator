#!/usr/bin/env python3
"""npu_exp.py — expériences contrôlées sur le NPU Windows (pyxrt), une variable à la fois.

Sous-commandes :
  api         : introspecte pyxrt.bo (map/read/write/sync disponibles)
  visibility  : test B — le marqueur écrit par l'hôte est-il relu depuis le DEVICE ?
                (roundtrip write -> sync TO -> sync FROM -> read, SANS soumission)
  map         : test D — soumet le TXN et rend la CARTE EXACTE des mots modifiés
                (marqueur positionnel 0xDEAD0000|i, plages de mots, pas d'octets)
  patch0      : test C — variante « arg_plus = 0 » (une seule variable : le champ
                arg_plus des 40 DDR_PATCH ; les seeds BD ne sont PAS touchés)
  patchsent   : test C — variante « arg_plus = SENTINELLE » (déplace les écritures
                si et seulement si le firmware applique réellement arg_plus)
  teardown    : test E — isole le SIGSEGV de fin de process (taille/nombre de BO,
                ordre de destruction)

Chaque exécution écrit un JSON + un log ; aucun PASS sans comparaison.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import time
import traceback

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

REC = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "python": sys.version.split()[0],
       "argv": sys.argv, "cwd": os.getcwd(),
       "pid": os.getpid()}

# Tailles issues de txn_struct.json (contrat implicite du TXN, PAS d'un manifeste)
SZ_A, SZ_B, SZ_C = 1998848, 851968, 544768
CHUNKS = (32768, 65536, 16384)


def sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def words_of(raw: bytes) -> list[int]:
    return list(struct.unpack("<%dI" % (len(raw) // 4), raw[: len(raw) // 4 * 4]))


def marker_words(n_words: int) -> bytes:
    """Marqueur positionnel : le mot i vaut 0xDEAD0000|i (i < 65536)."""
    return struct.pack("<%dI" % n_words, *[0xDEAD0000 | (i & 0xFFFF) for i in range(n_words)])


def preflight(sizes, insts: str, allow: bool = False,
              strict_bounds: bool = True) -> dict:
    """PRÉ-VOL obligatoire avant toute allocation de BO.

    Refuse (UndersizedBufferError) si un BO est plus petit que l'étendue adressée
    par les descripteurs du TXN. `allow=True` réservé aux expériences qui TESTENT
    la borne de taille. `strict_bounds=True` (défaut, *fail-closed*) refuse
    (BoundConflictError) quand le plancher MESURÉ dépasse la borne DÉCODÉE : un
    appelant qui accepte explicitement ce conflit (design déjà mesuré) passe
    `strict_bounds=False`, et le verdict devient `PASS_BOUND_CONFLICT_ASSUME`.
    Retourne le rapport pour l'archiver dans le JSON.
    """
    import npu_preflight  # noqa: PLC0415
    try:
        rep = npu_preflight.check(sizes, insts, allow_undersized=allow, quiet=False,
                                  strict_bounds=strict_bounds)
    except npu_preflight.BoundConflictError as exc:
        # l'exception porte déjà le préfixe « PRE-VOL FAIL_BOUND_CONFLICT » : ne pas
        # le dupliquer (même défaut cosmétique que l'undersize, corrigé le 18/10/2026).
        print(str(exc))
        raise
    except npu_preflight.UndersizedBufferError as exc:
        # Le message de l'exception commence déjà par « PRE-VOL REFUSE l'allocation » :
        # ne pas le préfixer deux fois (cosmétique, constaté le 18/10/2026).
        print(f"PRE-VOL: REFUSE — {exc}")
        raise
    REC.setdefault("preflight", []).append(rep)
    _PF.update({"insts": insts, "allow": allow, "scope": None, "n_data": 0,
                "vus": [],
                "targets": {c["arg"]: c["cible"] for c in rep.get("checks", [])}})
    return rep


def preflight_historical(sizes, insts: str) -> dict:
    """Pré-vol en mode « expérience de borne » : avertit, mais ne refuse pas.

    Réservé aux scripts dont les tailles de BO sont volontairement minimales ou
    historiques (sonde fonctionnelle, test de borne, rejeu d'une preuve antérieure).
    """
    print("PRE-VOL: MODE HISTORIQUE — tailles possiblement sous l'etendue descripteur")
    # Mode historique = expérience de borne assumée : le conflit de bornes est accepté
    # explicitement (strict_bounds=False), jamais silencieusement.
    return preflight(sizes, insts, allow=True, strict_bounds=False)


# --- Contexte de pré-vol : protéger le CHEMIN d'allocation lui-même --------------
# Un pré-vol appelé « quelque part » ne suffit pas : si le wrapper d'allocation reste
# muet, tout nouveau script qui appelle alloc() directement contourne le garde-fou.
# Défaut mesuré le 18/10/2026 par scripts/audit_preflight_order.py (occurrences
# npu_exp.py:170, :203, :345, :418). D'où : tout BO de DONNÉES exige un contexte de
# pré-vol posé AU PRÉALABLE, ou un périmètre explicitement déclaré.
_PF = {"insts": None, "targets": {}, "allow": False, "scope": None,
       "n_data": 0, "vus": []}


class UnscopedAllocationError(RuntimeError):
    """BO de données demandé sans pré-vol et sans périmètre déclaré."""


def declare_scope(reason: str) -> None:
    """Déclare explicitement un bloc qui alloue HORS du contrat des descripteurs.

    Réservé aux sondes qui ne soumettent rien (introspection d'API, aller-retour
    hôte/device) ou qui testent le cycle de vie des BO. Le motif est journalisé dans
    le JSON de run (`perimetres_declares`) : jamais un contournement tacite.
    """
    if not reason or len(reason) < 8:
        raise ValueError("declare_scope exige un motif explicite (>= 8 caracteres)")
    _PF.update({"insts": None, "targets": {}, "allow": False, "scope": reason,
                "n_data": 0, "vus": []})
    REC.setdefault("perimetres_declares", []).append(
        {"raison": reason, "fonction": sys._getframe(1).f_code.co_name})


def changed_word_ranges(buf: bytes) -> dict:
    """Indices de mots dont la valeur n'est plus 0xDEADxxxx, condensés en plages."""
    w = words_of(buf)
    ranges, start = [], None
    for i, v in enumerate(w):
        bad = (v & 0xFFFF0000) != 0xDEAD0000
        if bad and start is None:
            start = i
        elif not bad and start is not None:
            ranges.append([start, i - 1])
            start = None
    if start is not None:
        ranges.append([start, len(w) - 1])
    total = sum(e - s + 1 for s, e in ranges)
    return {"n_words": len(w), "n_changed": total, "ranges": ranges[:64],
            "n_ranges": len(ranges)}


def load_txn(path: str) -> tuple[bytes, list[int]]:
    raw = open(path, "rb").read()
    return raw, words_of(raw)


def patch_offsets(words: list[int]) -> list[tuple[int, int, int, int]]:
    """[(index du record, arg, plus_actuel, index de arg_plus dans words)]"""
    out, i, n = [], 4, len(words)
    while i < n:
        op = words[i] & 0xFF
        if op == 0x81 and i + 12 <= n:
            out.append((i, words[i + 8], words[i + 10], i + 10))
            i += 12
        elif op == 0x01:
            sz = words[i + 3]
            i += max(sz // 4, 1)
        elif op == 0x00:
            i += 6
        elif op == 0x03:
            i += 7
        elif op >= 0x80:
            sz = words[i + 1]
            i += max(sz // 4, 1)
        else:
            break
    return out


DDR_AIE_OFFSET = 0x80000000


def rewrite_patches(raw: bytes, mode: str, sentinel: int = 0x1000) -> tuple[bytes, list]:
    words = words_of(raw)
    offs = patch_offsets(words)
    applied = []
    for _rec, arg, old, idx in offs:
        if mode == "zero":
            new = 0
        elif mode == "sentinel":
            new = sentinel
        elif mode == "fold":
            # une seule variable : arg_plus += ouverture DDR de l'espace AIE
            new = (old + DDR_AIE_OFFSET) & 0xFFFFFFFF
        else:
            new = old
        words[idx] = new
        applied.append({"arg": arg, "old": old, "new": new})
    return struct.pack("<%dI" % len(words), *words), applied


def make_ctx(pyxrt, xclbin_path: str):
    dev = pyxrt.device(0)
    xb = pyxrt.xclbin(xclbin_path)
    uuid = dev.register_xclbin(xb)
    ctx = pyxrt.hw_context(dev, uuid)
    kb = xb.get_kernels()[0]
    kern = pyxrt.kernel(ctx, kb.get_name())
    return dev, xb, ctx, kern, kb


def alloc(dev, pyxrt, size, group, cacheable=True, role="data"):
    """Alloue un BO en refusant les chemins non couverts.

    role="instr" : flux d'instructions — dimensionné par le fichier lui-même, donc
                   hors contrat des descripteurs (aucune cible de pré-vol).
    role="data"  : BO de données — exige un pré-vol antérieur (ou un périmètre
                   déclaré) et refuse un dépassement de cible en mode strict.
    """
    # Le contrôle est posé AVANT tout appel à pyxrt : un test négatif a montré que
    # placer ce bloc après `pyxrt.bo.flags` laissait passer l'appel (AttributeError
    # au lieu du refus attendu) — mesure 18/10/2026.
    if role != "instr":
        if _PF["insts"] is None and _PF["scope"] is None:
            raise UnscopedAllocationError(
                "BO de donnees demande sans pre-vol ni perimetre declare : appeler "
                "preflight((A,B,C), insts) avant, ou declare_scope('<motif>') si le "
                "bloc n'entre pas dans le contrat des descripteurs.")
        idx = _PF["n_data"]
        cible = _PF["targets"].get(idx)
        if cible is not None and size < cible and not _PF["allow"]:
            import npu_preflight  # noqa: PLC0415
            raise npu_preflight.UndersizedBufferError(
                f"allocation refusee a la source : arg{idx} alloue {size} < cible {cible} "
                f"({cible - size} octets manquants)")
        _PF["n_data"] = idx + 1
        _PF["vus"].append({"arg": idx, "size": size, "group": group,
                           "cible": cible, "perimetre": _PF["scope"]})
        REC["allocations_verifiees"] = _PF["vus"]
    F = pyxrt.bo.flags
    fl = F(pyxrt.bo.cacheable if cacheable else pyxrt.bo.host_only)
    return pyxrt.bo(dev, size, fl, group)


def dump(name: str, doc: dict) -> None:
    doc["_rec"] = REC
    if name:
        with open(name, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
        print(f"JSON: {name}")


# --------------------------------------------------------------------------- #
def cmd_api(pyxrt, ns):
    bo = pyxrt.bo
    doc = {"bo_attrs": [a for a in dir(bo) if not a.startswith("_")],
           "flags": [a for a in dir(bo.flags) if not a.startswith("_")]}
    print(json.dumps(doc, indent=2))
    dump(ns.json, doc)
    return 0


def cmd_visibility(pyxrt, ns):
    """Test B : cohérence mémoire, sans aucune soumission NPU."""
    # Aucune soumission => le contrat des descripteurs ne s'applique pas : périmètre
    # déclaré explicitement (et journalisé), au lieu d'un pré-vol détourné.
    declare_scope("aller-retour hote/device sans soumission NPU")
    doc = {"test": "B_visibilite_memoire", "soumission": "AUCUNE", "cases": []}
    dev, xb, ctx, kern, kb = make_ctx(pyxrt, ns.xclbin)
    # group_id(0) ou 0 en dur => SIGSEGV dans XRT (index de banque invalide).
    # On utilise le groupe réellement déclaré par le noyau pour l'argument 3.
    g = kern.group_id(3)
    doc["group_id_arg3"] = g
    for size in [int(x) for x in ns.sizes.split(",")]:
        for cacheable in (True, False):
            case = {"size": size, "flags": "cacheable" if cacheable else "host_only"}
            try:
                bo = alloc(dev, pyxrt, size, g, cacheable)
                nw = size // 4
                payload = marker_words(nw)
                case["addr"] = hex(bo.address())
                bo.write(payload, 0)
                bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
                bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
                got = bytes(int(x) & 0xFF for x in bo.read(size, 0))
                same = got == payload
                first = struct.unpack("<8I", got[:32])
                case.update({"roundtrip_identique": same,
                             "octets_differents": sum(1 for a, b in zip(got, payload) if a != b),
                             "premiers_mots": [hex(x) for x in first],
                             "attendu": [hex(x) for x in struct.unpack("<8I", payload[:32])]})
                # 2e roundtrip : le résultat est-il stable ?
                bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
                bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
                got2 = bytes(int(x) & 0xFF for x in bo.read(size, 0))
                case["roundtrip2_identique"] = got2 == payload
                case["roundtrip1_egal_2"] = got2 == got
                del bo
            except BaseException as exc:  # noqa: BLE001
                case["exception"] = f"{type(exc).__name__}: {exc}"
            print(json.dumps(case, ensure_ascii=False))
            doc["cases"].append(case)
    ok = [c for c in doc["cases"] if c.get("roundtrip_identique")]
    doc["verdict"] = ("PASS_VISIBILITE" if len(ok) == len(doc["cases"])
                      else "FAIL_VISIBILITE" if doc["cases"] else "NOT_TESTED")
    print(f"VERDICT: {doc['verdict']}  ({len(ok)}/{len(doc['cases'])} roundtrips identiques)")
    dump(ns.json, doc)
    return 0


def _run_variant(pyxrt, ns, instr_bytes: bytes, label: str, patch_edits=None):
    """Alloue les BO aux tailles du contrat, remplit d'un marqueur positionnel,
    soumet, relit bo0/bo1/bo2 et rend la carte des mots modifiés."""
    a_size = getattr(ns, "asize", 0) or SZ_A
    b_size = getattr(ns, "bsize", 0) or SZ_B
    c_size = getattr(ns, "csize", 0) or SZ_C
    sizes = (a_size, b_size, c_size)
    # Expérience sur un design déjà mesuré : conflit de bornes accepté explicitement.
    rep = preflight(sizes, ns.insts, allow=getattr(ns, "allow_undersized", False),
                    strict_bounds=False)
    doc = {"label": label, "opcode": ns.opcode, "bo_sizes": list(sizes),
           "preflight": rep,
           "xclbin": ns.xclbin, "insts": ns.insts, "sha_insts_sha256": sha(ns.insts)}
    edits = patch_edits or []
    doc["patch_edits"] = {"n": len(edits), "distinct_old": sorted({e["old"] for e in edits})[:12],
                          "new": sorted({e["new"] for e in edits})}
    t = {}
    dev, xb, ctx, kern, kb = make_ctx(pyxrt, ns.xclbin)
    groups = [kern.group_id(i) for i in (1, 3, 4, 5)]
    doc["groups"] = groups
    t0 = time.perf_counter()
    bo_instr = alloc(dev, pyxrt, len(instr_bytes), groups[0], role="instr")
    bo_instr.write(instr_bytes, 0)
    bo_instr.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
    bos, payloads = [], []
    for i, sz in enumerate(sizes):
        bo = alloc(dev, pyxrt, sz, groups[1 + i])
        pay = marker_words(sz // 4)
        bo.write(pay, 0)
        bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
        bos.append(bo)
        payloads.append(pay)
        doc[f"bo{i}_addr"] = hex(bo.address())
        doc[f"bo{i}_size"] = sz

    # Contrôle préalable : le marqueur est-il visible sans soumission ?
    pre = {}
    for i, bo in enumerate(bos):
        bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
        got = bytes(int(x) & 0xFF for x in bo.read(sizes[i], 0))
        pre[f"bo{i}"] = got == payloads[i]
    doc["pre_roundtrip_identique"] = pre

    t0 = time.perf_counter()
    run = kern(ns.opcode, bo_instr, len(instr_bytes) // 4, bos[0], bos[1], bos[2], 0, 0)
    ts = round((time.perf_counter() - t0) * 1000, 3)
    state = run.wait()
    tw = round((time.perf_counter() - t0) * 1000, 3)
    doc["state"] = str(state)
    doc["submit_ms_approx"] = ts
    doc["submit_plus_wait_ms"] = tw

    out = {}
    for i, bo in enumerate(bos):
        bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
        raw = bytes(int(x) & 0xFF for x in bo.read(sizes[i], 0))
        info = changed_word_ranges(raw)
        info["sha256"] = hashlib.sha256(raw).hexdigest()
        info["premiers_mots"] = [hex(x) for x in struct.unpack("<8I", raw[:32])]
        info["premiers_mots_attendu"] = [hex(x) for x in struct.unpack("<8I", payloads[i][:32])]
        out[f"bo{i}"] = info
        print(f"  bo{i}: {info['n_words']} mots, {info['n_changed']} modifiés, "
              f"{info['n_ranges']} plages -> {info['ranges'][:6]}")
    doc["changes"] = out
    # Contrôle 2 : les BO d'entrée sont-ils intacts ?
    doc["entrees_intactes"] = {"bo0": out["bo0"]["n_changed"] == 0,
                               "bo1": out["bo1"]["n_changed"] == 0}
    # Écritures attendues sur C d'après le TXN
    doc["attendu_C_offsets"] = [0, 0x100, 0x200, 0x300, 0x80000, 0x80100, 0x80200, 0x80300]
    dump(ns.json, doc)
    for bo in bos + [bo_instr]:
        del bo
    return doc


def cmd_map(pyxrt, ns):
    raw, _ = load_txn(ns.insts)
    doc = _run_variant(pyxrt, ns, raw, "baseline_TXN_original")
    c = doc["changes"]["bo2"]
    exp = [o // 4 for o in doc["attendu_C_offsets"]]
    hits = [r for r in c["ranges"] if any(r[0] <= e <= r[1] for e in exp)]
    print(f"plages attendues (mots) : {exp}")
    print(f"plages observées        : {c['ranges'][:12]}")
    print(f"plages attendues couvertes : {len(hits)}/{len(exp)}")
    return 0


def cmd_patch(pyxrt, ns, mode: str):
    raw, words = load_txn(ns.insts)
    new_raw, edits = rewrite_patches(raw, mode, ns.sentinel)
    label = f"variante_arg_plus_{mode}" + (f"_0x{ns.sentinel:x}" if mode == "sentinel" else "")
    print(f"variante: {label} — {len(edits)} patches modifiés (seule variable : arg_plus)")
    _run_variant(pyxrt, ns, new_raw, label, edits)
    return 0


def _fill(tag: int, size: int) -> bytes:
    return struct.pack("<%dI" % (size // 4), *[tag | (i & 0xFFFF) for i in range(size // 4)])


def cmd_sensitivity(pyxrt, ns):
    """Test A/D : C dépend-il des entrées ? et le résultat est-il déterministe ?

    3 soumissions : (A1,B1) ; (A1,B1) bis ; (A2,B1).
    - run1 == run2  -> déterministe
    - run3 == run1  -> C INDÉPENDANT de A (le chemin de données ne lit pas A)
    - run3 != run1  -> C dépend de A
    """
    raw_txn = open(ns.insts, "rb").read()
    dev, xb, ctx, kern, kb = make_ctx(pyxrt, ns.xclbin)
    g = [kern.group_id(i) for i in (1, 3, 4, 5)]
    sa = getattr(ns, "asize", 0) or SZ_A
    sb = getattr(ns, "bsize", 0) or SZ_B
    sc = getattr(ns, "csize", 0) or SZ_C
    # Le pre-vol est pose AVANT la premiere allocation (y compris le BO d'instructions),
    # conformement a l'exigence P3 : refus avant toute allocation reelle.
    rep = preflight((sa, sb, sc), ns.insts, allow=getattr(ns, "allow_undersized", False))
    bo_instr = alloc(dev, pyxrt, len(raw_txn), g[0], role="instr")
    bo_instr.write(raw_txn, 0)
    bo_instr.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
    boA = alloc(dev, pyxrt, sa, g[1])
    boB = alloc(dev, pyxrt, sb, g[2])
    boC = alloc(dev, pyxrt, sc, g[3])
    doc = {"test": "A_sensibilite_entree", "sizes": [sa, sb, sc], "preflight": rep,
           "bo_addr": {"A": hex(boA.address()), "B": hex(boB.address()),
                       "C": hex(boC.address())}, "runs": []}
    A1 = _fill(0xDEAD0000, sa)
    A2 = _fill(0xCAFE0000, sa)
    B1 = _fill(0xBEEF0000, sb)

    def run(tag, a_bytes, b_bytes):
        boA.write(a_bytes, 0)
        boB.write(b_bytes, 0)
        boC.write(_fill(0xCDCD0000, sc), 0)
        for bo in (boA, boB, boC):
            bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)
        run_ = kern(ns.opcode, bo_instr, len(raw_txn) // 4, boA, boB, boC, 0, 0)
        st = run_.wait()
        boC.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)
        raw = bytes(int(x) & 0xFF for x in boC.read(sc, 0))
        h = hashlib.sha256(raw).hexdigest()
        ch = changed_word_ranges(raw)
        rec = {"tag": tag, "state": str(st), "sha256_C": h,
               "C_premiers_mots": [hex(x) for x in struct.unpack("<8I", raw[:32])],
               "C_modele_change": ch["n_changed"], "C_plages": ch["ranges"][:4]}
        print(json.dumps(rec, ensure_ascii=False))
        doc["runs"].append(rec)
        return raw

    r1 = run("A1_B1", A1, B1)
    r2 = run("A1_B1_bis", A1, B1)
    r3 = run("A2_B1", A2, B1)
    d12 = sum(1 for a, b in zip(r1, r2) if a != b)
    d13 = sum(1 for a, b in zip(r1, r3) if a != b)
    doc["decision"] = {
        "run1_vs_run2_octets_differents": d12,
        "run1_vs_run3_octets_differents": d13,
        "deterministe": d12 == 0,
        "C_depend_de_A": d13 > 0,
    }
    print(f"deterministe={d12 == 0} (diff={d12})   C_depend_de_A={d13 > 0} (diff={d13})")
    dump(ns.json, doc)
    return 0


def cmd_teardown(pyxrt, ns):
    """Test E : où meurt le process ? (code de sortie observé par l'appelant)"""
    dev, xb, ctx, kern, kb = make_ctx(pyxrt, ns.xclbin)
    g = kern.group_id(3)
    # Test du CYCLE DE VIE des BO (taille/nombre/ordre de destruction), sans soumission :
    # hors contrat des descripteurs, périmètre déclaré et journalisé.
    declare_scope("test du cycle de vie des BO, sans soumission")
    doc = {"test": "E_teardown", "cas": ns.case, "ops": []}
    def step(name, fn):
        try:
            v = fn()
            doc["ops"].append({"step": name, "ok": True,
                               "value": getattr(v, "address", lambda: None)() if not isinstance(v, (int, str, bool, type(None))) else v})
            print(f"  ok   {name} -> {v}")
            return v
        except BaseException as exc:  # noqa: BLE001
            doc["ops"].append({"step": name, "ok": False,
                               "exception": f"{type(exc).__name__}: {exc}"})
            print(f"  FAIL {name}: {type(exc).__name__}: {exc}")
            return None

    if ns.case == "bo_group0":
        # reproduit le crash observé : groupe de banque 0 en dur
        step("alloc_group0", lambda: alloc(dev, pyxrt, 16384, 0))
    SIZES = {"ctx_bo16k": [16384], "ctx_bo16k_del": [16384],
             "ctx_bo544k": [544768], "ctx_bo544k_del": [544768],
             "ctx_bo3": [SZ_A, SZ_B, SZ_C], "ctx_bo3_del": [SZ_A, SZ_B, SZ_C]}
    if ns.case in SIZES:
        sizes = SIZES[ns.case]
        bois = []
        for sz in sizes:
            bois.append(step(f"alloc_{sz}", lambda sz=sz: alloc(dev, pyxrt, sz, g)))
        for b, sz in zip(bois, sizes):
            step("write", lambda b=b, sz=sz: b.write(marker_words(sz // 4), 0) or True)
            step("sync_to", lambda b=b: b.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE) or True)
            step("sync_from", lambda b=b: b.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE) or True)
        if ns.case.endswith("_del"):
            for b in bois:
                del b
            bois.clear()
            doc["bos_detruits"] = True
    doc["fin_normale"] = True
    print("fin du corps Python — le code de sortie du process révèle le crash éventuel")
    dump(ns.json, doc)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["api", "visibility", "map", "sensitivity", "patch0",
                                    "patchsent", "patchfold", "teardown"])
    ap.add_argument("--xclbin", default="E:/trixdna_test/phase5_atb/phase5_atb_m32k64n128.xclbin")
    ap.add_argument("--insts", default="E:/trixdna_test/phase5_atb/phase5_atb_m32k64n128_insts.bin")
    ap.add_argument("--opcode", type=int, default=3)
    ap.add_argument("--sizes", default="16384,544768")
    ap.add_argument("--sentinel", type=lambda s: int(s, 0), default=0x1000)
    ap.add_argument("--case", default="ctx")
    ap.add_argument("--asize", type=int, default=0, help="taille du BO A (defaut 1998848)")
    ap.add_argument("--bsize", type=int, default=0, help="taille du BO B (defaut 851968)")
    ap.add_argument("--csize", type=int, default=0, help="taille du BO C (defaut 544768)")
    ap.add_argument("--allow-undersized", action="store_true",
                    help="DANGER: n'applique pas le pre-vol de dimensionnement (borne a tester)")
    ap.add_argument("--json", default=None)
    ns = ap.parse_args(argv)
    import pyxrt  # noqa: PLC0415

    REC["pyxrt"] = getattr(pyxrt, "__file__", "?")
    REC["xclbin_sha256"] = sha(ns.xclbin)
    REC["insts_sha256"] = sha(ns.insts)
    if ns.cmd == "api":
        return cmd_api(pyxrt, ns)
    if ns.cmd == "visibility":
        return cmd_visibility(pyxrt, ns)
    if ns.cmd == "map":
        return cmd_map(pyxrt, ns)
    if ns.cmd == "sensitivity":
        return cmd_sensitivity(pyxrt, ns)
    if ns.cmd == "patch0":
        return cmd_patch(pyxrt, ns, "zero")
    if ns.cmd == "patchsent":
        return cmd_patch(pyxrt, ns, "sentinel")
    if ns.cmd == "patchfold":
        return cmd_patch(pyxrt, ns, "fold")
    if ns.cmd == "teardown":
        return cmd_teardown(pyxrt, ns)
    return 2


if __name__ == "__main__":
    try:
        rc = main()
        print(f"EXIT_CORPS={rc}")
        sys.exit(rc)
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001
        traceback.print_exc()
        print(f"ERREUR: {type(exc).__name__}: {exc}")
        sys.exit(2)
