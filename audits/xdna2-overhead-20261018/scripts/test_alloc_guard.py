#!/usr/bin/env python3
"""test_alloc_guard.py — le garde-fou d'allocation peut-il être contourné ?

Tests NÉGATIFS avec un stub `pyxrt` : aucune exécution NPU, aucun BO réel.
Chaque cas a un résultat attendu explicite ; tout écart = échec (exit 1).

  T1  alloc() de données SANS pré-vol ni périmètre  -> UnscopedAllocationError
  T2  preflight() strict puis arg sous la cible     -> UndersizedBufferError
  T3  preflight(allow=True) puis arg sous la cible  -> allocation autorisée (borne)
  T4  declare_scope("<motif>") sans pré-vol         -> allocation autorisée + motif journalisé
  T5  BO d'instructions (role="instr")              -> jamais soumis au contrat
  T6  preflight() : les cibles correspondent au rapport (arg -> cible)
  T7  declare_scope("court") : refusé (pas de contournement tacite)
  T8  F-1 : design 512, B=5 832 704 (= cible de l'ancien min()) -> REFUS (exit 3)
  T9  empreinte exacte C : 1 048 576 accepté, 1 048 572 refusé (exp_N_footprint)
  T10 design inconnu (sha256 absent de la table) -> PASS_NON_CERTIFIE, pas PASS
  T11 design 512, B = 8 388 608 (plancher NUMÉRIQUE, exp_O) -> accepté, verdict
      PASS_BOUND_CONFLICT_ASSUME (le conflit de bornes est réel et assumé)
  T12 m32k64n128 : plancher de REPRODUCTIBILITÉ seul -> PASS_SOUS_RESERVE, jamais PASS
  T13 [L-X-01] défaut *fail-closed* : plancher mesuré > borne décodée
      -> BoundConflictError (aucun PASS possible sans l'accepter explicitement)
  T14 [L-X-01] CLI : défaut -> exit 4 FAIL_BOUND_CONFLICT ; avec
      --allow-bound-conflict -> exit 0 + verdict PASS_BOUND_CONFLICT_ASSUME
""";
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import npu_exp as E  # noqa: E402

INSTS = "E:/trixdna_test/phase5_atb/phase5_atb_m32k64n128_insts.bin"
INSTS_512 = ("E:/trixdna_test/repos_strixhalo_npu_setup/saved_xclbins/"
             "phase5_bf16_512x8192x512_insts.bin")
SIZES = (1998848, 2097152, 1048576)


class StubBo:
    def __init__(self, dev, size, fl, group):
        self.size, self.group = size, group

    def address(self):
        return 0


def stub_pyxrt():
    """Objet minimal imitant l'API réellement utilisée par npu_exp.alloc :
    `pyxrt.bo.flags(...)`, `pyxrt.bo.cacheable`, `pyxrt.bo.host_only`,
    `pyxrt.bo(dev, size, fl, group)`."""
    class Bo:
        cacheable = "cacheable"
        host_only = "host_only"

        @staticmethod
        def flags(v):
            return v

        def __new__(cls, dev, size, fl, group):
            return StubBo(dev, size, fl, group)

    class P:
        bo = Bo
    return P()


def reset():
    E._PF.update({"insts": None, "targets": {}, "allow": False, "scope": None,
                  "n_data": 0, "vus": []})
    E.REC.pop("perimetres_declares", None)


def main() -> int:
    pyxrt = stub_pyxrt()
    failures = []

    def check(name, ok, detail=""):
        print(f"  {'OK  ' if ok else 'ECHEC'} {name} {detail}")
        if not ok:
            failures.append(name)

    # T1 — aucune couverture
    reset()
    try:
        E.alloc(None, pyxrt, 16384, 3)
        check("T1 refus sans pre-vol", False, "(allocation acceptee)")
    except E.UnscopedAllocationError:
        check("T1 refus sans pre-vol", True)

    # T6 — cibles issues du rapport
    reset()
    # m32k64n128 : conflit de bornes (plancher > borne décodée) → accepté
    # explicitement ; ce cas teste les CIBLES, pas la politique de refus (T13).
    rep = E.preflight(SIZES, INSTS, allow=False, strict_bounds=False)
    targets = {c["arg"]: c["cible"] for c in rep["checks"]}
    check("T6 cibles posees", E._PF["targets"] == targets, f"({targets})")

    # T2 — refus à la source, en strict
    reset()
    E.preflight(SIZES, INSTS, allow=False, strict_bounds=False)
    try:
        E.alloc(None, pyxrt, 1998848, 3)      # arg0 : OK
        E.alloc(None, pyxrt, 2097152, 4)      # arg1 : OK
        E.alloc(None, pyxrt, 262144, 5)       # arg2 : 256 Kio << 1 Mio
        check("T2 refus a la source", False, "(allocation sous-cible acceptee)")
    except Exception as exc:  # noqa: BLE001
        import npu_preflight
        check("T2 refus a la source", isinstance(exc, npu_preflight.UndersizedBufferError),
              f"({type(exc).__name__})")

    # T3 — mode borne : autorisé (expérience qui teste la borne)
    reset()
    E.preflight(SIZES, INSTS, allow=True, strict_bounds=False)
    try:
        E.alloc(None, pyxrt, 1998848, 3)
        E.alloc(None, pyxrt, 2097152, 4)
        E.alloc(None, pyxrt, 262144, 5)
        check("T3 mode borne autorise", True)
    except Exception as exc:  # noqa: BLE001
        check("T3 mode borne autorise", False, f"({type(exc).__name__}: {exc})")

    # T4 — périmètre déclaré
    reset()
    E.declare_scope("test unitaire du garde-fou, aucune soumission")
    try:
        E.alloc(None, pyxrt, 16384, 3)
        ctx = E.REC.get("perimetres_declares") or []
        check("T4 perimetre declare", bool(ctx) and ctx[-1]["raison"].startswith("test unitaire"),
              f"({ctx[-1]['fonction'] if ctx else 'non journalise'})")
    except Exception as exc:  # noqa: BLE001
        check("T4 perimetre declare", False, f"({type(exc).__name__}: {exc})")

    # T5 — BO d'instructions : jamais soumis au contrat
    reset()
    try:
        b = E.alloc(None, pyxrt, 5168, 1, role="instr")
        check("T5 role=instr hors contrat", getattr(b, "size", None) == 5168)
    except Exception as exc:  # noqa: BLE001
        check("T5 role=instr hors contrat", False, f"({type(exc).__name__}: {exc})")

    # T7 — declare_scope sans motif explicite : refusé (pas de contournement tacite)
    reset()
    try:
        E.declare_scope("court")
        check("T7 motif obligatoire", False, "(motif trop court accepte)")
    except ValueError:
        check("T7 motif obligatoire", True)

    # T8 — F-1 : le min() historique affaiblissait le plancher mesuré. B = 5 832 704 o
    # est la cible que produisait min(étendue=5 832 704, plancher=8 388 608) ; cette
    # taille a été MESURÉE fausse (12 288 valeurs, 8 704 NaN, exp_M). Elle doit être
    # refusée, et la cible doit valoir le plancher mesuré, pas l'étendue décodée.
    import npu_preflight
    for name, path, sizes, attendu_cible in (
            ("T8 B=5832704 (defaut F-1)", INSTS_512, (7995392, 5832704, 7995392), 8388608),
            ("T9 C=1048576 (empreinte exacte)", INSTS, (1998848, 2097152, 1048576), 1048576),
            ("T9 C=1048572 (4 o sous l'empreinte)", INSTS, (1998848, 2097152, 1048572), 1048576)):
        reset()
        try:
            rep = E.preflight(sizes, path, allow=False, strict_bounds=False)
            ok = name.startswith("T9 C=1048576")
            cible = {c["arg"]: c["cible"] for c in rep["checks"]}
            check(name, ok and cible.get(1 if "F-1" in name else 2) == attendu_cible,
                  f"(accepte, cibles={cible})")
        except npu_preflight.UndersizedBufferError as exc:
            ok = not name.startswith("T9 C=1048576")
            check(name, ok, f"(refuse: {str(exc)[:60]}...)")

    # T10 — design INCONNU : aucun plancher mesuré => PASS_NON_CERTIFIE, jamais PASS.
    import struct as _s
    import tempfile
    hdr = [0x00060003, 0x00000008, 2, 0]
    bd = [1, 0, 0x1D000, (4 + 8) * 4, 0x4000, 0, 0, 0, 0, 0, 0x0000FFFF, 0x02000000]
    patch = [0x81, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0x2000, 0]
    sync = [3, 16, 0, 0]
    words = hdr + bd + patch + sync
    words[3] = len(words) * 4
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as fh:
        fh.write(_s.pack("<%dI" % len(words), *words))
        synth = fh.name
    reset()
    rep = E.preflight((0x4000,), synth, allow=False, strict_bounds=False)
    check("T10 design inconnu non certifie",
          rep.get("verdict") == "PASS_NON_CERTIFIE" and rep.get("design_certifie") is False,
          f"(verdict={rep.get('verdict')})")
    os.unlink(synth)

    # T11/T12 — nature du plancher : seul un plancher validé NUMÉRIQUEMENT certifie.
    reset()
    # Conflit de bornes sur ce design (plancher 8 388 608 > borne décodée) : accepté
    # EXPLICITEMENT, sinon le pré-vol refuse (T13). Même propriété vérifiée : c'est
    # le plancher NUMÉRIQUE qui certifie, pas le modèle de format.
    rep512 = E.preflight((16777216, 8388608, 16777216), INSTS_512, allow=False,
                         strict_bounds=False)
    check("T11 plancher numerique -> PASS_BOUND_CONFLICT_ASSUME",
          rep512.get("verdict") == "PASS_BOUND_CONFLICT_ASSUME"
          and rep512.get("design_certifie") is True
          and rep512.get("bound_conflict") is True
          and rep512.get("nature_du_plancher") == "NUMERIQUE_ET_REPRODUCTIBLE",
          f"(verdict={rep512.get('verdict')}, certifie={rep512.get('design_certifie')}, "
          f"conflit={rep512.get('bound_conflict')})")
    reset()
    rep32 = E.preflight(SIZES, INSTS, allow=False, strict_bounds=False)
    check("T12 plancher de reproductibilite -> PASS_SOUS_RESERVE",
          rep32.get("verdict") == "PASS_SOUS_RESERVE"
          and rep32.get("nature_du_plancher") == "REPRODUCTIBLE_SEUL"
          and rep32.get("design_certifie") is False,
          f"(verdict={rep32.get('verdict')}, certifie={rep32.get('design_certifie')})")

    # T13 — [L-X-01] fail-closed : le désaccord plancher/borne décodée REFUSE par défaut.
    reset()
    try:
        E.preflight((16777216, 8388608, 16777216), INSTS_512, allow=False)
        check("T13 conflit de bornes refuse par defaut", False,
              "(accepte sans strict_bounds=False)")
    except npu_preflight.BoundConflictError as exc:
        check("T13 conflit de bornes refuse par defaut", True,
              f"(BoundConflictError: {str(exc)[:48]}...)")

    # T14 — CLI : exit 4 par défaut, exit 0 seulement si le conflit est accepté.
    import subprocess
    cli = os.path.join(os.path.dirname(os.path.abspath(__file__)), "npu_preflight.py")
    base = [sys.executable, cli, "--insts", INSTS_512,
            "--sizes", "16777216,8388608,16777216"]
    r_strict = subprocess.run(base, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    r_accept = subprocess.run(base + ["--allow-bound-conflict"], capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
    ok14 = (r_strict.returncode == 4 and "FAIL_BOUND_CONFLICT" in r_strict.stdout
            and r_accept.returncode == 0
            and "PASS_BOUND_CONFLICT_ASSUME" in r_accept.stdout)
    check("T14 CLI exit 4 / --allow-bound-conflict exit 0", ok14,
          f"(strict={r_strict.returncode}, accepte={r_accept.returncode})")

    print(f"\n{len(failures)} echec(s) sur 14 cas" + (f" : {failures}" if failures else ""))
    return 1 if failures else 0


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
