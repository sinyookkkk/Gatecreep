"""Standard-library negative and positive checks; no fixture execution."""
import copy
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

repo = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('discovery', repo / 'gatecreep/scripts/check_discovery.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
folder = repo / 'docs/discovery-example'
data = [json.loads((folder / (name + '.json')).read_text()) for name in
        ('01-scan', '02-features', '03-supplement', '04-reconciliation', 'evidence')]
target = repo / 'gatecreep/tests/fixtures/discovery'
data[0]['root'] = str(target)
report = (folder / 'report.md').read_text(encoding='utf-8')
assert not d.validate(*data, target, report)


def reject(change):
    altered = copy.deepcopy(data)
    change(altered)
    assert d.validate(*altered, target, report), 'invalid artifact accepted'


reject(lambda a: a[1].update(discovery_version=99))
reject(lambda a: a[2].update(snapshot_id='wrong'))
reject(lambda a: a[3]['features'][0].update(candidate_ids=['unknown']))
reject(lambda a: a[3]['features'][0].update(source_feature_ids=['unknown']))
reject(lambda a: a[3]['features'][0].update(evidence=[]))
reject(lambda a: a[1]['features'].append(copy.deepcopy(a[1]['features'][0])))
reject(lambda a: a[3]['candidate_dispositions'].pop())
reject(lambda a: a[3]['candidate_dispositions'].append(copy.deepcopy(a[3]['candidate_dispositions'][0])))
reject(lambda a: a[3]['candidate_dispositions'][1].update(feature_ids=[]))
reject(lambda a: a[3].update(scope_impacts=[]))
reject(lambda a: a[2].update(inspections=[]))
reject(lambda a: a[4]['citations'][0].update(end=999))
reject(lambda a: a[4]['citations'][0].update(path='../outside.py'))
reject(lambda a: a[3]['transformations'][0].update(target_ids=['unknown']))
reject(lambda a: a[3]['features'][0]['inputs'].update(status='guessed'))
assert d.validate(*data, target, report + '\n[feature:missing]')
assert d.validate(*data, target, report.replace('[scope:conflict:0]', ''))
real_read = Path.read_bytes
with patch.object(Path, 'read_bytes', lambda path: b'changed' if path.name == 'tool.py' else real_read(path)):
    assert d.validate(*data, target, report)
args = sum(([f'--{key}', str(folder / (name + '.json'))] for key, name in
            zip(('scan', 'summary', 'supplement', 'final', 'evidence'),
                ('01-scan', '02-features', '03-supplement', '04-reconciliation', 'evidence'))), [])
args += ['--target', str(target)]
with patch.object(Path, 'read_text', return_value='{broken'):
    assert d.main(args) == 2
print('discovery checks passed; semantic review remains separate')
