"""Run with Python; no target code is executed by extraction."""
import ast
import importlib.util
import tempfile
from pathlib import Path


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


e = load('extract_facts')
r = load('check_report')


def parser_check():
    for declaration in ('import argparse\np = argparse.ArgumentParser()',
                        'import argparse as ap\np = ap.ArgumentParser()',
                        'from argparse import ArgumentParser as AP\np = AP()'):
        visitor = e.PythonFacts('sample.py', 'sample')
        visitor.visit(ast.parse(declaration + '''
p.add_argument('path')
p.add_argument('--limit', default=10, choices=[5, 10, 20], required=True, action='append')
subs = p.add_subparsers()
child = subs.add_parser('run')
child.add_argument('--child')
'''))
        commands = [c for c in visitor.capabilities if c['kind'] == 'cli-command']
        assert len(commands) == 2, commands
        root, child = commands
        assert root['id'] != child['id']
        assert root['arguments'][0]['options'] == ['path']
        assert root['arguments'][1] == dict(options=['--limit'], default=10, choices=[5, 10, 20], required=True, action='append')
        assert child['arguments'][0]['options'] == ['--child']
    visitor = e.PythonFacts('sample.py', 'sample')
    visitor.visit(ast.parse('from other import ArgumentParser\np = ArgumentParser()\np.add_argument("x")'))
    assert not visitor.capabilities


def expression_check():
    visitor = e.PythonFacts('sample.py', 'sample')
    visitor.visit(ast.parse('''
def run(q):
    for x in fetch()[:10]:
        pass
    while len(q) > 10:
        break
    raise ValueError('large' if len(q) > 99 else 'small') from cause(len(q) > 2)
'''))
    assert len([g for g in visitor.gates if g['kind'] == 'limit']) == 3
    assert len([g for g in visitor.gates if g['kind'] == 'slice']) == 1
    assert len([g for g in visitor.gates if g['kind'] == 'loop']) == 2
    assert len([g for g in visitor.gates if g['kind'] == 'raise']) == 1
    assert len(visitor.flows) == 6
    facts = dict(capabilities=visitor.capabilities, gates=visitor.gates, flows=visitor.flows, coverage=[])
    e.link_facts(facts)
    assert all(g['mapped_capability_ids'] == ['sample.run'] for g in visitor.gates)
    assert len({g['id'] for g in visitor.gates}) == len(visitor.gates)


def report_check():
    def report(chain, following=''):
        finding = '### [疑似过度门禁] 示例\n' + '\n'.join(
            f'- {field}：' + (chain if field == '因果链' else following)
            for field in r.FINDING_FIELDS)
        return '\n'.join('## ' + title + '\n' + (finding if title == '主要发现' else '无')
                         for title in r.REQUIRED_SECTIONS)
    for chain in ('A → B [静态事实]', 'A\n  → B [模型推断]', '\n  ```text\n  A\n  → B [静态事实]\n  ```'):
        assert not r.validate_report(report(chain)), chain
    for chain in ('A → B', 'A\n  → B'):
        assert any('因果链必须标注' in error for error in r.validate_report(report(chain, '[静态事实]')))
    text = report('A\n  → B') + '\n### [疑似过度门禁] 下一项\n- 因果链：X [静态事实]\n'
    assert any('因果链必须标注' in error for error in r.validate_report(text))


def project_check():
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        target = Path(directory, 'target.py')
        source = b'raise RuntimeError("must not execute")\n'
        target.write_bytes(source)
        before = target.stat().st_mtime_ns
        e.extract_project(Path(directory))
        assert target.read_bytes() == source and target.stat().st_mtime_ns == before
        assert list(Path(directory).iterdir()) == [target]
    facts = e.extract_project(Path(__file__).parents[1] / 'scripts')
    commands = [c for c in facts['capabilities'] if c['kind'] == 'cli-command']
    assert {c['source']['path'] for c in commands} == {'extract_facts.py', 'check_report.py', 'check_discovery.py'}
    assert len(commands) == 3
    assert len({c['id'] for c in facts['capabilities']}) == len(facts['capabilities'])


if __name__ == '__main__':
    for check in (parser_check, expression_check, report_check, project_check):
        try:
            check()
        except AssertionError:
            print(f'{check.__name__}: FAILED')
            raise
    print('audit regression checks passed')
