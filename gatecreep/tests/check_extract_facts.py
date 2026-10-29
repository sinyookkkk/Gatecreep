import ast
import importlib.util
import json
import contextlib
import io
import subprocess
import sys
import tempfile
from unittest.mock import patch
from pathlib import Path

spec = importlib.util.spec_from_file_location('extractor', Path(__file__).parents[1] / 'scripts/extract_facts.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)

def check():
    json.dumps(e.literal(ast.parse('{1, "x"}', mode='eval').body), allow_nan=False)
    visitor = e.PythonFacts('sample.py', 'sample')
    visitor.visit(ast.parse('def run(a,b,c):\n    return a < b < c\n'))
    comparisons = [g for g in visitor.gates if g['kind'] == 'limit']
    assert len({g['id'] for g in comparisons}) == 2
    assert comparisons[1]['left'] == 'b'
    facts = dict(capabilities=visitor.capabilities, gates=visitor.gates, flows=visitor.flows, coverage=[])
    e.link_facts(facts)
    assert all(g['mapped_capability_ids'] == ['sample.run'] for g in comparisons)
    for expression in ['[{1, "x"}, (b"a", 2j), {1: "one"}]', '1e999', '...', 'set()']:
        value = e.literal(ast.parse(expression, mode='eval').body)
        assert json.loads(json.dumps(value, allow_nan=False)) == value
    assert e.literal(ast.parse('[1, {"x": True}]', mode='eval').body) == [1, {'x': True}]
    assert e.literal(ast.parse('{1, "x"}', mode='eval').body)['literal_type'] == 'set'
    source = '''
@unknown
class Box:
    @cache
    def _private(self): pass
@tool(name="run")
@require_auth
async def run(a,b,c):
    assert a < b < c, "bounds"
    assert a
    @validate_call()
    def nested(): pass
'''
    visitor = e.PythonFacts('sample.py', 'sample')
    visitor.visit(ast.parse(source))
    decorators = [g for g in visitor.gates if g['kind'] == 'decorator']
    assert len(decorators) == 5
    assert all(g['action'] == 'candidate' and g['gate_semantics'] == 'inferred' for g in decorators)
    assert {g['owner'] for g in decorators} == {'sample.Box', 'sample.Box._private', 'sample.run', 'sample.run.nested'}
    assertions = [g for g in visitor.gates if g['kind'] == 'assert']
    assert [g['message'] for g in assertions] == ["'bounds'", None]
    assert all(g['function'] == 'sample.run' for g in assertions)
    assert next(c for c in visitor.capabilities if c['id'] == 'sample.run')['kind'] == 'agent-tool'
    out, err = io.StringIO(), io.StringIO()
    with patch.object(e, 'extract_project', return_value={'bad': object()}), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            e.main(['.'])
        except SystemExit as exc:
            assert exc.code != 0
        else:
            raise AssertionError('serialization failure must exit')
    assert not out.getvalue() and 'extract_facts:' in err.getvalue()
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        Path(directory, 'sample.py').write_text(source, encoding='utf-8')
        result = subprocess.run([sys.executable, '-I', str(spec.origin), directory], capture_output=True, check=True)
        parsed = json.loads(result.stdout)
        assert all(g['mapped_capability_ids'] == ['sample.run'] for g in parsed['gates'] if g['kind'] == 'assert')
    result = subprocess.run([sys.executable, '-I', str(spec.origin), str(Path(__file__).parents[2])], capture_output=True, check=True)
    parsed = json.loads(result.stdout, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    ids = [g['id'] for g in parsed['gates']]
    assert len(ids) == len(set(ids))

if __name__ == '__main__':
    check()
    print('fact extraction checks passed')

