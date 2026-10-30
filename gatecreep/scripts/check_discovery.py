"""Check four discovery JSON artifacts, source references and optional report."""
import argparse
import importlib.util
import json
import re
from pathlib import Path

spec = importlib.util.spec_from_file_location('discovery_report', Path(__file__).with_name('check_report.py'))
report_checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report_checks)
CATEGORIES = {'documentation', 'configuration', 'dynamic-registration', 'multi-action', 'non-python', 'unmapped-paths'}
OUTCOMES = {'inspected-no-addition', 'discovered', 'not-applicable', 'not-inspected', 'unresolved'}
DETAILS = ('inputs', 'outputs', 'success_criteria', 'preconditions', 'side_effects', 'failure_behavior')


def validate(scan, summary, supplement, final, evidence, target, report=None):
    errors = []
    def require(ok, message):
        if not ok:
            errors.append(message)
    def text(value):
        return isinstance(value, str) and bool(value.strip())
    def records(obj, field):
        value = obj.get(field)
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise ValueError(f'{field}: expected list of objects')
        return value
    def ids(items, label):
        result = set()
        for item in items:
            rid = item.get('id')
            if not text(rid):
                raise ValueError(f'{label}: nonempty string id required')
            require(rid not in result, f'{label}: duplicate id {rid}')
            result.add(rid)
        return result
    def refs(value, allowed, label, nonempty=False):
        require(isinstance(value, list) and all(isinstance(v, str) and v in allowed for v in value)
                and (not nonempty or bool(value)), label + ': missing or unknown references')
    used = set()
    citation_ids = ids(records(evidence, 'citations'), 'citations')
    def citations(item, label, optional=False):
        value = item.get('evidence')
        refs(value, citation_ids, label, not optional)
        if isinstance(value, list):
            used.update(v for v in value if isinstance(v, str))
        if optional and not value:
            require(text(item.get('missing_evidence')), label + ': missing_evidence reason required')
    require(scan.get('schema_version') == 3, 'scan requires schema_version 3')
    for artifact, stage in ((summary, 'features'), (supplement, 'supplement'), (final, 'reconciliation')):
        require(type(artifact.get('discovery_version')) is int and artifact['discovery_version'] == 1, stage + ': unsupported version')
        require(artifact.get('stage') == stage, stage + ': wrong stage')
        require(artifact.get('snapshot_id') == scan.get('snapshot_id'), stage + ': snapshot mismatch')
    candidates = ids(records(scan, 'capabilities'), 'candidates')
    features = records(summary, 'features')
    additions = records(supplement, 'features')
    summary_ids, addition_ids = ids(features, 'summary'), ids(additions, 'supplement')
    require(not summary_ids & addition_ids, 'feature ids reused across stages')
    source_ids = summary_ids | addition_ids
    final_features = records(final, 'features')
    final_ids = ids(final_features, 'final')
    require(not final_ids & source_ids, 'final feature ids must differ from source ids')
    for feature in features + additions + final_features:
        label = feature['id']
        for field in ('name', 'purpose'):
            require(text(feature.get(field)), label + ': ' + field + ' required')
        require(feature.get('status') in {'confirmed', 'inferred', 'unknown'}, label + ': invalid status')
        require(text(feature.get('reason')), label + ': reason required')
        refs(feature.get('candidate_ids'), candidates, label + ' candidates')
        citations(feature, label)
        for field in DETAILS:
            detail = feature.get(field)
            if not isinstance(detail, dict):
                raise ValueError(label + ': missing detail ' + field)
            require(detail.get('status') in {'known', 'unknown', 'not-applicable'} and text(detail.get('reason'))
                    and 'value' in detail, label + ': invalid detail ' + field)
            if detail.get('status') == 'known':
                require(detail.get('value') is not None and detail.get('value') != '', label + ': known value missing')
            else:
                require(detail.get('value') is None, label + ': unknown/inapplicable value must be null')
    for feature in final_features:
        refs(feature.get('source_feature_ids'), source_ids, feature['id'] + ' sources', True)
    inspections = records(supplement, 'inspections')
    inspection_ids = ids(inspections, 'inspections')
    require({i.get('category') for i in inspections} == CATEGORIES, 'all inspection categories required')
    for item in inspections:
        require(item.get('outcome') in OUTCOMES and text(item.get('reason')) and text(item.get('impact')),
                item['id'] + ': invalid inspection')
        citations(item, item['id'], optional=item.get('outcome') in {'not-applicable', 'not-inspected', 'unresolved'})
        refs(item.get('feature_ids'), source_ids, item['id'] + ' features', item.get('outcome') == 'discovered')
    for item in records(supplement, 'corrections'):
        refs(item.get('feature_ids'), summary_ids, 'correction features', True)
        require(text(item.get('reason')), 'correction reason required')
        citations(item, 'correction')
    dispositions = records(final, 'candidate_dispositions')
    disposed = [item.get('candidate_id') for item in dispositions]
    require(all(isinstance(v, str) for v in disposed) and set(disposed) == candidates and len(disposed) == len(candidates),
            'every candidate must have exactly one disposition')
    for item in dispositions:
        require(item.get('classification') in {'public-entry', 'internal', 'test', 'legacy', 'false-positive', 'unresolved'}
                and text(item.get('reason')), 'invalid disposition')
        refs(item.get('feature_ids'), final_ids, 'disposition features', item.get('classification') == 'public-entry')
        citations(item, 'disposition', optional=True)
    for item in records(final, 'transformations'):
        require(item.get('kind') in {'merge', 'split', 'retain'} and text(item.get('reason')), 'invalid transformation')
        refs(item.get('source_ids'), source_ids, 'transformation sources', True)
        refs(item.get('target_ids'), final_ids, 'transformation targets', True)
        citations(item, 'transformation')
    for item in records(final, 'conflicts'):
        require(item.get('status') in {'resolved', 'unresolved'} and text(item.get('reason')) and text(item.get('impact')),
                'invalid conflict')
        citations(item, 'conflict')
        refs(item.get('feature_ids'), final_ids, 'conflict features')
    impacts = records(final, 'scope_impacts')
    expected = {'coverage:' + str(i) for i in range(len(scan.get('coverage', [])))}
    expected.update('inspection:' + i['id'] for i in inspections if i['outcome'] in {'unresolved', 'not-inspected'})
    impact_keys = [item.get('source') for item in impacts]
    require(all(isinstance(v, str) for v in impact_keys) and set(impact_keys) == expected and len(impact_keys) == len(expected),
            'coverage and unfinished inspections require exactly one impact each')
    for item in impacts:
        require(text(item.get('reason')) and text(item.get('impact')), 'scope impact requires reason and impact')
    if report is not None:
        errors.extend(report_checks.validate_report(report))
        mentioned = set(re.findall(r'\[feature:([^\]]+)\]', report))
        require(mentioned == final_ids, 'report must reference all and only final feature ids')
        pending = expected | {'conflict:' + str(i) for i, item in enumerate(final['conflicts']) if item['status'] == 'unresolved'}
        require(pending <= set(re.findall(r'\[scope:([^\]]+)\]', report)), 'report missing unresolved scope references')
    errors.extend(report_checks.validate_evidence(scan, evidence, target, report or '', used))
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('scan', 'summary', 'supplement', 'final', 'evidence', 'target'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args(argv)
    try:
        paths = [getattr(args, name) for name in ('scan', 'summary', 'supplement', 'final', 'evidence')]
        root = args.target.resolve()
        if any(path.resolve().is_relative_to(root) for path in paths + ([args.report] if args.report else [])):
            raise ValueError('analysis artifacts must be outside target')
        data = [json.loads(path.read_text(encoding='utf-8')) for path in paths]
        errors = validate(*data, args.target, args.report.read_text(encoding='utf-8') if args.report else None)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print('invalid discovery input:', exc)
        return 2
    print('Validation scope: structure, associations and source references; semantics/runtime/exhaustive coverage not verified')
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
