"""Small regression checks for scan boundaries, output and MCP declarations."""
import ast
import contextlib
import importlib.util
import io
import json
import os
import stat
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('extractor', Path(__file__).parents[1] / 'scripts/extract_facts.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


def output_check():
    data = {'text': '\ud800中文', 'many': list(range(30000))}
    class StrictOutput(io.StringIO):
        def write(self, value):
            value.encode('utf-8')
            assert len(value) <= 65536, 'output must use bounded chunks'
            return super().write(value)
    out = StrictOutput()
    with patch.object(e, 'extract_project', return_value=data), contextlib.redirect_stdout(out):
        assert e.main([str(Path(__file__).parent / 'unused-target')]) == 0
    assert json.loads(out.getvalue()) == data
    for failure in (OSError('disk'), UnicodeError('encoding'), MemoryError()):
        for stage in ('extract', 'write', 'flush'):
            class FailingOutput(io.StringIO):
                def write(self, value):
                    if stage == 'write':
                        raise failure
                    return super().write(value)
                def flush(self):
                    if stage == 'flush':
                        raise failure
            out, err = FailingOutput(), io.StringIO()
            with patch.object(e, 'extract_project', side_effect=failure if stage == 'extract' else None,
                              return_value={}), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    e.main([str(Path(__file__).parent / 'unused-target')])
                except SystemExit as exc:
                    assert exc.code == 2
                else:
                    raise AssertionError('failure must exit 2')
            assert 'extract_facts:' in err.getvalue() and 'Traceback' not in err.getvalue()
    out, err = io.StringIO(), io.StringIO()
    with patch.object(e, 'extract_project', return_value={'valid': [1, 2], 'bad': object()}), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            e.main([str(Path(__file__).parent / 'unused-target')])
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError('invalid object must fail')
    assert not out.getvalue()


def scan_check():
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        root = Path(directory)
        files = {
            'server.py': 'raise RuntimeError("never execute")\ndef run(k): return "\\ud800" <= k <= "\\udbff"\n',
            'tests/test_server.py': 'def test_ok(): assert 2 > 1\n',
            'test/helper.py': 'def helper(): return 1\n',
            'test_root.py': 'def test_root(): return 1\n',
            'root_test.py': 'def test_root(): return 1\n',
            '.venv_source/ok.py': 'def ok(): return 1\n',
            '.venv_seedream/pyvenv.cfg': 'home = python\n',
        }
        for excluded in ('.uv-cache', '.venv', 'node_modules', '__pycache__', '.git', 'venv', '.venv_seedream'):
            files[f'{excluded}/nested/vendor.py'] = 'def vendor(): assert False\n'
        for name, source in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding='utf-8')
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
        facts = e.extract_project(root)
        assert not any(c['name'] == 'vendor' for c in facts['capabilities'])
        excluded = [c for c in facts['coverage'] if c['kind'] == 'excluded-directory']
        assert len(excluded) == 7, excluded
        assert all(c['message'] for c in excluded)
        for collection in ('capabilities', 'gates', 'flows'):
            assert facts[collection]
            for fact in facts[collection]:
                path = fact['source']['path']
                assert fact['source_role'] == ('unknown' if path in ('server.py', '.venv_source/ok.py') else 'test')
        result = subprocess.run([sys.executable, '-B', str(spec.origin), directory], capture_output=True, check=True)
        repeat = subprocess.run([sys.executable, '-B', str(spec.origin), directory], capture_output=True, check=True)
        assert result.stdout == repeat.stdout
        assert json.loads(result.stdout) == facts
        assert any(g.get('value') == '\udbff' for g in facts['gates'])
        for collection in ('capabilities', 'gates'):
            ids = [fact['id'] for fact in facts[collection]]
            assert len(ids) == len(set(ids))
        assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()} == before


def mcp_check():
    for imports, constructor in (('from mcp import types', 'types.Tool'),
                                 ('import mcp.types', 'mcp.types.Tool'),
                                 ('import mcp', 'mcp.types.Tool'),
                                 ('import mcp.types as mt', 'mt.Tool'),
                                 ('from mcp.types import Tool as T', 'T')):
        visitor = e.PythonFacts('server.py', 'server')
        visitor.visit(ast.parse(imports + f'''
SCHEMA = {{'type': 'object', 'properties': {{'x': {{'type': 'integer'}}}}}}
@server.list_tools()
async def list_tools():
    return [{constructor}(name='draw', description='画图', inputSchema=SCHEMA),
            {constructor}(name='erase', description='erase', inputSchema={{'type': 'object'}}),
            {constructor}(name=compute(), inputSchema=dynamic_schema())]
@server.call_tool()
async def call_tool(name, arguments):
    if name == 'draw': return draw(arguments)
@tool
def ordinary(): return 1
'''))
        facts = dict(capabilities=visitor.capabilities, gates=visitor.gates, flows=visitor.flows, coverage=visitor.coverage)
        e.link_facts(facts)
        tools = [c for c in facts['capabilities'] if c['kind'] == 'agent-tool']
        assert {c['name'] for c in tools} == {'draw', 'erase', 'ordinary'}, tools
        draw = next(c for c in tools if c['name'] == 'draw')
        assert draw['description'] == '画图' and draw['input_schema']['properties']['x']['type'] == 'integer'
        assert not draw['reachable_gate_ids'] and not draw['direct_gate_ids']
        assert {c['mcp_role'] for c in facts['capabilities'] if 'mcp_role' in c} == {'listing', 'dispatcher'}
        assert len([c for c in facts['coverage'] if c['kind'] == 'unresolved-tool-implementation']) == 2
        assert any(c['kind'] == 'dynamic-agent-name' for c in facts['coverage'])
        assert any(c['kind'] == 'unresolved-tool-schema' for c in facts['coverage'])
        assert len({c['id'] for c in facts['capabilities']}) == len(facts['capabilities'])
    visitor = e.PythonFacts('other.py', 'other')
    visitor.visit(ast.parse('from other import Tool\nx = Tool(name="fake", inputSchema={})'))
    assert not visitor.capabilities


def boundary_check():
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        root = Path(directory)
        (root / '.uv-cache/nested').mkdir(parents=True)
        (root / '.uv-cache/nested/bad.py').write_text('def hidden(): pass', encoding='utf-8')
        (root / 'linked').mkdir()
        original_scandir, original_lstat = os.scandir, Path.lstat
        visited = []
        def scandir(path):
            visited.append(Path(path))
            assert '.uv-cache' not in Path(path).parts
            assert 'linked' not in Path(path).parts
            return original_scandir(path)
        def lstat(path, *args, **kwargs):
            if path == root / 'linked':
                return SimpleNamespace(st_mode=0o120777, st_file_attributes=0)
            return original_lstat(path, *args, **kwargs)
        with patch.object(e.os, 'scandir', side_effect=scandir), patch.object(Path, 'lstat', lstat):
            facts = e.extract_project(root)
        assert visited == [root]
        assert len([c for c in facts['coverage'] if c['kind'] == 'excluded-directory']) == 2
        def junction_lstat(path, *args, **kwargs):
            if path == root / 'linked':
                return SimpleNamespace(st_mode=0o040777, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
            return original_lstat(path, *args, **kwargs)
        if hasattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT'):
            with patch.object(e.os, 'scandir', side_effect=scandir), patch.object(Path, 'lstat', junction_lstat):
                facts = e.extract_project(root)
            assert any(c['message'] == 'directory link' for c in facts['coverage'])
        def walk(path, **kwargs):
            kwargs['onerror'](PermissionError(13, 'denied', str(root / 'blocked')))
            return iter(())
        with patch.object(e.os, 'walk', side_effect=walk):
            facts = e.extract_project(root)
        assert facts['coverage'][0]['kind'] == 'unreadable-directory'
        assert facts['coverage'][0]['source']['path'] == 'blocked'
        # Exercise real links when this platform permits creating them.
        try:
            (root / 'outside.py').symlink_to(Path(spec.origin).resolve())
        except OSError:
            print('file symlink creation unavailable; testing resolved-path exclusion')
            (root / 'outside.py').write_text('def outside(): pass', encoding='utf-8')
            resolve = Path.resolve
            def redirected(path, *args, **kwargs):
                return Path(spec.origin).absolute() if path == root / 'outside.py' else resolve(path, *args, **kwargs)
            with patch.object(Path, 'resolve', redirected):
                facts = e.extract_project(root)
        else:
            facts = e.extract_project(root)
        assert any(c['kind'] == 'excluded-file' and c['source']['path'] == 'outside.py' for c in facts['coverage'])


def staging_check():
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        target = Path(directory, 'target')
        target.mkdir()
        opened = []
        real_tempfile = tempfile.TemporaryFile
        def tracked(*args, **kwargs):
            assert not Path(kwargs['dir']).resolve().is_relative_to(target.resolve())
            handle = real_tempfile(*args, **kwargs)
            opened.append(handle)
            return handle
        with patch.object(e.tempfile, 'TemporaryFile', side_effect=tracked), \
                patch.object(e.tempfile, 'gettempdir', return_value=directory), \
                patch.object(e, 'extract_project', return_value={'ok': True}), contextlib.redirect_stdout(io.StringIO()):
            assert e.main([str(target)]) == 0
        assert opened and all(handle.closed for handle in opened)
        assert list(target.iterdir()) == []
        assert list(Path(directory).iterdir()) == [target]
        for failure in (OSError('staging disk failure'), MemoryError()):
            out, err = io.StringIO(), io.StringIO()
            with patch.object(e.tempfile, 'TemporaryFile', side_effect=tracked), \
                    patch.object(e.tempfile, 'gettempdir', return_value=directory), \
                    patch.object(e, 'extract_project', return_value={}), \
                    patch.object(e.json, 'dump', side_effect=failure), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    e.main([str(target)])
                except SystemExit as exc:
                    assert exc.code == 2
                else:
                    raise AssertionError('staging failure must exit 2')
            assert not out.getvalue() and 'serialization' in err.getvalue()
            assert all(handle.closed for handle in opened)
            assert list(Path(directory).iterdir()) == [target]
        with patch.object(e.tempfile, 'TemporaryFile', side_effect=OSError('cannot create staging file')), \
                patch.object(e, 'extract_project', return_value={}), contextlib.redirect_stderr(io.StringIO()):
            try:
                e.main([str(target)])
            except SystemExit as exc:
                assert exc.code == 2
            else:
                raise AssertionError('temporary creation failure must exit 2')
        with patch.object(e.tempfile, 'gettempdir', return_value=str(target)), \
                patch.object(e, 'extract_project', return_value={}), contextlib.redirect_stderr(io.StringIO()):
            try:
                e.main([str(target)])
            except SystemExit as exc:
                assert exc.code == 2
            else:
                raise AssertionError('must reject temp storage inside target')


if __name__ == '__main__':
    for check in (output_check, scan_check, mcp_check, boundary_check, staging_check):
        check()
    print('scan reliability checks passed')
