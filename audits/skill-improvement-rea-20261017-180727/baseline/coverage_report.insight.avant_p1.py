#!/usr/bin/env python3
"""coverage_report.py — mesure d'entrée du rapport de couverture.

CORRECTIF 17/10/2026 (mission REA skill-improvement-rea-20261017-180727, règle P0 :
l'absence de preuve n'est ni une réfutation ni un crash) :
- --ledger / --collection / --queue pointant un fichier ABSENT -> statut UNKNOWN
  explicite + entrée 'absents' (exit 0), au lieu de FileNotFoundError (exit 1).
- JSON invalide -> raison tracée dans findings ('INVALID_JSON'), pas de crash.
Le contrat de sortie (coverage-report.md, bloc ```json```) est inchangé.
"""
import argparse, json
from pathlib import Path

def load(path):
    """Retourne (rows, erreur). erreur=None si OK, sinon
    {'raison': 'FILE_ABSENT'|'INVALID_JSON'|'READ_ERROR', 'detail': str}."""
    p = Path(path)
    if not p.exists():
        return None, {'raison': 'FILE_ABSENT', 'detail': str(p)}
    try:
        if p.suffix == '.jsonl':
            return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()], None
        obj = json.loads(p.read_text(encoding='utf-8'))
        return (obj if isinstance(obj, list) else [obj]), None
    except json.JSONDecodeError as e:
        return None, {'raison': 'INVALID_JSON', 'detail': str(e)[:200]}
    except (OSError, UnicodeDecodeError) as e:
        return None, {'raison': 'READ_ERROR', 'detail': str(e)[:200]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ledger'); ap.add_argument('--collection', action='append', default=[])
    ap.add_argument('--queue'); ap.add_argument('--out'); args = ap.parse_args()
    report = {'status': 'MEASURED', 'inputs': {}, 'findings': []}
    statut, raison = 'MEASURED', None
    if args.ledger:
        rows, err = load(args.ledger)
        if err:
            statut = 'UNKNOWN'
            report['inputs']['absents'] = [{'fichier':args.ledger, **err}]
            report['findings'].append({'note':"preuve absente ou illisible: statut UNKNOWN appliqué, PAS une réfutation"})
        else:
            report['inputs']['ledger_rows'] = len(rows)
            report['inputs']['unique_destinations'] = len({r.get('canonical_url') or r.get('url') for r in rows})
            report['inputs']['unresolved_rows'] = sum(1 for r in rows if r.get('status') in {'INACCESSIBLE','FETCH_FAILED','NOT_YET_INSPECTED','RATE_LIMITED'})
    report['inputs']['collections'] = []
    for c in args.collection:
        obj, err = load(c)
        if err:
            statut = 'UNKNOWN' if statut == 'MEASURED' else statut
            report['inputs'].setdefault('absents', []).append({'fichier': c, **err})
            continue
        report['inputs']['collections'].append({'file': c, 'records': len(obj)})
        for r in obj:
            if isinstance(r, dict) and r.get('error'):
                report['findings'].append({'file': c, 'error': r['error']})
    if args.queue:
        q, err = load(args.queue)
        if err:
            report['inputs'].setdefault('absents', []).append({'fichier': args.queue, **err})
        else:
            report['inputs']['queue_remaining'] = len(q)
    report['status'] = statut
    report['findings'].append({'note': 'Absence de résultat ne prouve pas l’absence; vérifier pagination, permissions et profondeur.'})
    text = '# Coverage report\n\n```json\n' + json.dumps(report, ensure_ascii=False, indent=2) + '\n```\n'
    if args.out:
        Path(args.out).write_text(text, encoding='utf-8')
    else:
        print(text)

if __name__ == '__main__':
    main()
