"""Run with python -I gatecreep/tests/check_evidence.py; never execute fixtures."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
from unittest.mock import patch


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


e, c = load('extract_facts'), load('check_report')
with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
    root = Path(directory)
    source = root / 'tool.py'
    source.write_bytes(b'# coding: latin-1\n# caf\xe9\ndef run():\n    raise ValueError("bad")\n')
    (root / 'README.md').write_text('contract\n')
    facts = e.extract_project(root)
    assert facts['schema_version'] == 3
    assert len(facts['manifest']) == 2
    assert all(item['status'] == 'read' for item in facts['manifest'])
    evidence = {'snapshot_id': facts['snapshot_id'],
                'citations': [{'id': 'c1', 'path': 'tool.py', 'start': 1, 'end': 4}],
                'steps': [{'id': 's1', 'claim': 'reject', 'provenance': 'static-fact', 'evidence': ['c1']},
                          {'id': 's2', 'claim': 'unknown handler', 'provenance': 'inference', 'evidence': []}],
                'links': [{'from': 's1', 'to': 's2', 'provenance': 'inference', 'evidence': []}]}
    report = '[evidence:c1]'
    assert not c.validate_evidence(facts, evidence, root, report)
    for field, value in [('path', '../tool.py'), ('path', str(source)), ('end', 999), ('start', 0)]:
        bad = copy.deepcopy(evidence)
        bad['citations'][0][field] = value
        assert c.validate_evidence(facts, bad, root, report)
    bad = copy.deepcopy(evidence)
    del bad['steps'][0]['provenance']
    assert c.validate_evidence(facts, bad, root, report)
    assert c.validate_evidence({'schema_version': 2}, evidence, root, report)
    original = source.read_bytes()
    source.write_bytes(original + b'# dirty\n')
    assert e.extract_project(root)['snapshot_id'] != facts['snapshot_id']
    assert c.validate_evidence(facts, evidence, root, report)
    source.unlink()
    assert c.validate_evidence(facts, evidence, root, report)
    source.write_bytes(original)
    real_read = Path.read_bytes
    def unreadable(path):
        if path == source:
            raise PermissionError('synthetic read failure')
        return real_read(path)
    with patch.object(Path, 'read_bytes', unreadable):
        broken = e.extract_project(root)
    assert any(item['status'] == 'failed' for item in broken['manifest'])
    with patch.object(Path, 'resolve', autospec=True, side_effect=lambda path: root.parent if path == source else path):
        assert c.validate_evidence(facts, evidence, root, report)
    # CLI preserves report bytes even when source validation fails.
    full_report = '\n'.join('## ' + title + '\n无' for title in c.REQUIRED_SECTIONS) + '\n' + report
    report_path = root / 'report.txt'
    report_path.write_text(full_report, encoding='utf-8')
    facts_path, evidence_path = root / 'facts.json', root / 'evidence.json'
    facts_path.write_text(json.dumps(facts), encoding='utf-8')
    evidence_path.write_text(json.dumps(evidence), encoding='utf-8')
    assert c.main([str(report_path)]) == 0
    assert c.main([str(report_path), '--facts', str(facts_path), '--evidence', str(evidence_path), '--target', str(root)]) == 0
    source.write_bytes(b'changed\n')
    assert c.main([str(report_path), '--facts', str(facts_path), '--evidence', str(evidence_path), '--target', str(root)]) == 1
    assert report_path.read_text(encoding='utf-8') == full_report

fixture = Path(__file__).parent / 'fixtures/tool-recovery'
facts = e.extract_project(fixture)
raises = [gate for gate in facts['gates'] if gate['kind'] == 'raise']
assert any('Explicit authorization' in str(gate) for gate in raises)
assert any('Unexpected fields' in str(gate) for gate in raises)
assert json.loads((fixture / 'calls.json').read_text())['provenance'].startswith('synthetic')
print('evidence checks passed; model semantic evaluation is separate')


