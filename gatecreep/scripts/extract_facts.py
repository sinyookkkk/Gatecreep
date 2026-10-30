"""Extract read-only, non-judgmental gate audit facts from a project."""

from __future__ import annotations

import argparse
import ast
import json
import hashlib
import io
import math
import os
import stat
import sys
import tempfile
import tokenize
from pathlib import Path


SCHEMA_VERSION = 3
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".uv-cache"}
DOCUMENT_KINDS = {
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
}


def source_ref(path: str, node: ast.AST) -> dict:
    return {
        "path": path,
        "line": getattr(node, "lineno", 1),
        "column": getattr(node, "col_offset", 0),
    }


def module_name(path: Path) -> str:
    parts = list(path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def function_inputs(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict]:
    args = node.args
    positional = args.posonlyargs + args.args
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    inputs = [
        {
            "name": arg.arg,
            "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
            "default": ast.unparse(default) if default else None,
        }
        for arg, default in zip(positional, defaults)
    ]
    inputs.extend(
        {
            "name": arg.arg,
            "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
            "default": ast.unparse(default) if default else None,
        }
        for arg, default in zip(args.kwonlyargs, args.kw_defaults)
    )
    for arg, kind in ((args.vararg, "args"), (args.kwarg, "kwargs")):
        if arg:
            inputs.append({
                "name": arg.arg,
                "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
                "default": None,
                "kind": kind,
            })
    return inputs


def call_name(node: ast.Call) -> str:
    return ast.unparse(node.func)


def json_literal(value, expression=None):
    if isinstance(value, list):
        return [json_literal(item, expression) for item in value]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {key: json_literal(item, expression) for key, item in value.items()}
    if isinstance(value, (set, frozenset, tuple)):
        items = [json_literal(item, expression) for item in value]
        if isinstance(value, (set, frozenset)):
            items.sort(key=lambda item: json.dumps(item, sort_keys=True, allow_nan=False))
        return {"literal_type": type(value).__name__, "expression": expression, "items": items}
    if isinstance(value, dict):
        return {"literal_type": "dict", "expression": expression, "items": [
            [json_literal(key, expression), json_literal(item, expression)] for key, item in value.items()
        ]}
    if isinstance(value, (bytes, complex)) or value is Ellipsis or (
        isinstance(value, float) and not math.isfinite(value)
    ):
        return {"literal_type": type(value).__name__, "expression": expression, "representation": repr(value)}
    return value


def literal(node: ast.AST | None):
    if node is None:
        return None
    try:
        return json_literal(ast.literal_eval(node), ast.unparse(node))
    except (ValueError, TypeError):
        return ast.unparse(node)


class PythonFacts(ast.NodeVisitor):
    def __init__(self, path: str, module: str):
        self.path = path
        self.module = module
        self.capabilities = []
        self.coverage = []
        self.gates = []
        self.flows = []
        self.imports = {}
        # ponytail: literal names cover direct assignments only; mutation needs dataflow analysis.
        self.literal_values = {}
        self.command_vars = {}
        self.command_calls = {}
        self.conditions = []
        self.function_tail = None
        self.current_class = None
        self.current_function = None
        self.current_returns = None

    def add_gate(self, node: ast.AST, kind: str, action: str, **details):
        condition = self.conditions[-1] if self.conditions else None
        gate = {
            "fact_type": "gate",
            "id": f"{self.path}:{getattr(node, 'lineno', 1)}:{getattr(node, 'col_offset', 0)}:{kind}",
            "kind": kind,
            "action": action,
            "status": "confirmed",
            "source": source_ref(self.path, node),
            "function": self.current_function,
            "condition": condition["expression"] if condition else None,
            "has_alternative": condition["has_alternative"] if condition else False,
        }
        gate.update(details)
        self.gates.append(gate)

    def visit_ClassDef(self, node: ast.ClassDef):
        previous = self.current_class
        self.current_class = f"{previous}.{node.name}" if previous else node.name
        owner = f"{self.current_function or self.module}.{self.current_class}"
        self._decorators(node, owner, None)
        for statement in node.body:
            self.visit(statement)
        self.current_class = previous

    def _decorators(self, node, owner, function):
        for decorator in node.decorator_list:
            self.add_gate(decorator, "decorator", "candidate", owner=owner,
                          function=function, expression=ast.unparse(decorator),
                          gate_semantics="inferred")

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._function(node)

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        parent = self.current_function
        prefix = parent or self.current_class
        qualname = f"{prefix}.{node.name}" if prefix else node.name
        function_id = f"{self.module}.{qualname}" if self.module and not parent else qualname
        tool_decorators = []
        mcp_role = None
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            name = ast.unparse(target).rsplit(".", 1)[-1]
            if isinstance(target, ast.Attribute) and name in {"call_tool", "list_tools"}:
                mcp_role = "dispatcher" if name == "call_tool" else "listing"
            elif name == "tool" or name.endswith("_tool"):
                tool_decorators.append(decorator)
        cap = None
        if parent is None and (not node.name.startswith("_") or node.name == "main" or tool_decorators or mcp_role):
            cap = {
                "fact_type": "capability",
                "id": function_id,
                "kind": "agent-tool" if tool_decorators else "python-function",
                "name": node.name,
                "status": "confirmed" if tool_decorators else "candidate",
                "source": source_ref(self.path, node),
                "inputs": function_inputs(node),
                "returns": [],
            }
            self.capabilities.append(cap)
            if mcp_role:
                cap["mcp_role"] = mcp_role
                cap["mcp_role_status"] = "inferred"
        for decorator in tool_decorators:
            if isinstance(decorator, ast.Call):
                name_arg = next((kw.value for kw in decorator.keywords if kw.arg == "name"), None)
                if name_arg is not None and not isinstance(name_arg, ast.Constant):
                    self.coverage.append({
                        "fact_type": "coverage",
                        "kind": "dynamic-agent-name",
                        "status": "confirmed",
                        "source": source_ref(self.path, decorator),
                        "message": "tool name is computed at runtime",
                    })
        previous_returns = self.current_returns
        previous_tail = self.function_tail
        self.current_function = function_id
        self._decorators(node, function_id, function_id)
        self.current_returns = []
        previous_literals = self.literal_values
        self.literal_values = self.literal_values.copy()
        self.function_tail = node.body[-1] if node.body else None
        for statement in node.body:
            self.visit(statement)
        if cap is not None:
            cap["returns"] = self.current_returns
        self.current_function = parent
        self.current_returns = previous_returns
        self.function_tail = previous_tail
        self.literal_values = previous_literals

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base = alias.name.split(".", 1)[0]
            self.imports[alias.asname or base] = alias.name if alias.asname else base

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.level:
            package = self.module.split(".")[:-1]
            keep = len(package) - (node.level - 1)
            base = ".".join(package[:keep] + ([node.module] if node.module else []))
        else:
            base = node.module or ""
        for alias in node.names:
            if alias.name != "*":
                self.imports[alias.asname or alias.name] = f"{base}.{alias.name}" if base else alias.name

    def visit_Assign(self, node: ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                try:
                    self.literal_values[target.id] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    self.literal_values.pop(target.id, None)
        if (
            self.current_function is None
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, (int, float))
            and not isinstance(node.value.value, bool)
        ):
            self.add_gate(node, "numeric-constant", "assignment", value=literal(node.value),
                          configuration="literal", expression=ast.unparse(node))
        self.generic_visit(node)
        if isinstance(node.value, ast.Call) and len(node.targets) == 1:
            target = node.targets[0]
            command = self.command_calls.get(id(node.value))
            if command is not None and isinstance(target, ast.Name):
                self.command_vars[target.id] = command

    def visit_Call(self, node: ast.Call):
        name = call_name(node)
        self.flows.append({
            "fact_type": "flow",
            "caller": self.current_function or self.module,
            "callee": name,
            "resolved": None,
            "status": "inferred",
            "source": source_ref(self.path, node),
            "_module": self.module,
            "_class": self.current_class,
            "_imports": self.imports,
        })
        operation = name.rsplit(".", 1)[-1]
        receiver = node.func.value.id if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) else None
        base, _, attribute = name.partition(".")
        resolved_name = self.imports.get(base, base) + (f".{attribute}" if attribute else "")
        if base in self.imports and resolved_name == "mcp.types.Tool":
            keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg}
            values = {}
            for field in ("name", "description", "inputSchema"):
                value_node = keywords.get(field)
                try:
                    value = self.literal_values[value_node.id] if isinstance(value_node, ast.Name) else ast.literal_eval(value_node)
                    if not isinstance(value, dict if field == "inputSchema" else str):
                        raise ValueError("unexpected declaration type")
                    values[field] = json_literal(value, ast.unparse(value_node))
                except (KeyError, ValueError, TypeError):
                    if field != "description" or value_node is not None:
                        self.coverage.append({
                            "fact_type": "coverage",
                            "kind": {"name": "dynamic-agent-name", "inputSchema": "unresolved-tool-schema",
                                     "description": "unresolved-tool-description"}[field],
                            "status": "confirmed", "source": source_ref(self.path, node),
                            "message": f"MCP Tool {field} is not a supported literal",
                        })
            if "name" in values:
                capability_id = f"{self.module}.mcp:{node.lineno}:{node.col_offset}"
                self.capabilities.append({
                    "fact_type": "capability", "id": capability_id,
                    "kind": "agent-tool", "name": values["name"], "status": "confirmed",
                    "source": source_ref(self.path, node), "declaration_kind": "mcp-tool",
                    "description": values.get("description"), "input_schema": values.get("inputSchema"),
                    "implementation_status": "unknown",
                })
                self.coverage.append({
                    "fact_type": "coverage", "kind": "unresolved-tool-implementation", "status": "confirmed",
                    "source": source_ref(self.path, node), "capability_id": capability_id,
                    "message": "MCP declaration has no confirmed per-tool implementation mapping",
                })
        elif resolved_name == "argparse.ArgumentParser":
            command = {
                "fact_type": "capability",
                "id": f"{self.module}.cli.root:{node.lineno}:{node.col_offset}",
                "kind": "cli-command",
                "name": self.module,
                "status": "confirmed",
                "source": source_ref(self.path, node),
                "arguments": [],
            }
            self.capabilities.append(command)
            self.command_calls[id(node)] = command
        elif operation == "add_parser":
            command_name = literal(node.args[0]) if node.args else None
            if isinstance(command_name, str):
                command = {
                    "fact_type": "capability",
                    "id": f"{self.module}.cli.{command_name}",
                    "kind": "cli-command",
                    "name": command_name,
                    "status": "confirmed",
                    "source": source_ref(self.path, node),
                    "arguments": [],
                }
                self.capabilities.append(command)
                self.command_calls[id(node)] = command
            else:
                self.coverage.append({
                    "fact_type": "coverage",
                    "kind": "dynamic-cli-command",
                    "status": "confirmed",
                    "source": source_ref(self.path, node),
                    "message": "command name is computed at runtime",
                })
        elif operation == "add_argument" and receiver in self.command_vars:
            keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg}
            self.command_vars[receiver]["arguments"].append({
                "options": [literal(arg) for arg in node.args],
                "required": literal(keywords.get("required")) or False,
                "default": literal(keywords.get("default")),
                "choices": literal(keywords.get("choices")),
                "action": literal(keywords.get("action")),
            })
        elif operation == "set_defaults" and receiver in self.command_vars:
            handler = next((kw.value for kw in node.keywords if kw.arg == "func"), None)
            if handler is not None:
                handler_name = ast.unparse(handler)
                self.command_vars[receiver]["implementation"] = (
                    f"{self.module}.{handler_name}" if self.module else handler_name
                )
        elif operation == "register_tool" or operation.endswith("_register_tool"):
            if node.args and isinstance(node.args[0], (ast.Name, ast.Attribute)):
                handler = ast.unparse(node.args[0])
                self.capabilities.append({
                    "fact_type": "capability",
                    "id": f"{self.module}.tool.{handler}",
                    "kind": "agent-tool",
                    "name": handler.rsplit(".", 1)[-1],
                    "status": "confirmed",
                    "source": source_ref(self.path, node),
                    "implementation": f"{self.module}.{handler}" if self.module else handler,
                })
            else:
                self.coverage.append({
                    "fact_type": "coverage",
                    "kind": "dynamic-agent-registration",
                    "status": "confirmed",
                    "source": source_ref(self.path, node),
                    "message": "tool implementation is computed at runtime",
                })
        if name in {"sys.exit", "exit", "quit", "SystemExit"} or operation == "error":
            self.add_gate(node, "exit", "terminate", expression=name)
        for keyword in node.keywords:
            if keyword.arg and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, (int, float)):
                self.add_gate(keyword.value, "resource-argument", "configure",
                              name=keyword.arg, value=literal(keyword.value), configuration="literal")
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        self.add_gate(node, "condition", "branch", expression=ast.unparse(node.test),
                      alternative_present=bool(node.orelse))
        self.visit(node.test)
        self.conditions.append({"expression": ast.unparse(node.test), "has_alternative": bool(node.orelse)})
        for statement in node.body:
            self.visit(statement)
        self.conditions.pop()
        for statement in node.orelse:
            self.visit(statement)

    def visit_Compare(self, node: ast.Compare):
        left = node.left
        for index, (operator, comparator) in enumerate(zip(node.ops, node.comparators)):
            configuration = (
                "literal" if isinstance(comparator, ast.Constant)
                else "named" if isinstance(comparator, ast.Name)
                else "configured" if isinstance(comparator, ast.Attribute)
                else "computed"
            )
            self.add_gate(node, "limit", "compare", operator=type(operator).__name__,
                          left=ast.unparse(left), right=ast.unparse(comparator),
                          value=literal(comparator), configuration=configuration)
            if len(node.ops) > 1:
                self.gates[-1]["id"] += f":{index}"
            left = comparator
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert):
        self.add_gate(node, "assert", "reject", expression=ast.unparse(node.test),
                      message=ast.unparse(node.msg) if node.msg else None)
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise):
        self.add_gate(node, "raise", "reject",
                      exception=ast.unparse(node.exc) if node.exc else None)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        self.add_gate(node, "exception-handler", "handle",
                      exception=ast.unparse(node.type) if node.type else None)
        for statement in node.body:
            self.visit(statement)

    def visit_Continue(self, node: ast.Continue):
        self.add_gate(node, "skip", "skip-item")

    def visit_Break(self, node: ast.Break):
        self.add_gate(node, "stop", "stop-loop")

    def visit_For(self, node: ast.For):
        self.add_gate(node, "loop", "iterate", expression=ast.unparse(node.iter))
        self.visit(node.iter)
        for statement in node.body + node.orelse:
            self.visit(statement)

    def visit_While(self, node: ast.While):
        self.add_gate(node, "loop", "repeat", expression=ast.unparse(node.test))
        self.visit(node.test)
        for statement in node.body + node.orelse:
            self.visit(statement)

    def visit_Subscript(self, node: ast.Subscript):
        if isinstance(node.slice, ast.Slice) and (node.slice.upper or node.slice.lower):
            self.add_gate(node, "slice", "truncate-candidate", expression=ast.unparse(node))
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        self.add_gate(node, "return", "return", early=node is not self.function_tail,
                      value=ast.unparse(node.value) if node.value else None)
        if self.current_returns is not None:
            self.current_returns.append({
                "value": ast.unparse(node.value) if node.value else None,
                "line": node.lineno,
            })
        if node.value:
            self.visit(node.value)


def parse_python(path: Path, relative: Path, data: bytes | None = None) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    try:
        data = path.read_bytes() if data is None else data
        encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
        tree = ast.parse(data.decode(encoding), filename=str(path))
    except (SyntaxError, UnicodeError) as exc:
        return [], [], [], [{
            "fact_type": "coverage",
            "kind": "parse-error",
            "status": "confirmed",
            "source": {
                "path": relative.as_posix(),
                "line": getattr(exc, "lineno", 1),
                "column": max((getattr(exc, "offset", 1) or 1) - 1, 0),
            },
            "message": str(exc),
        }]
    extractor = PythonFacts(relative.as_posix(), module_name(relative))
    extractor.visit(tree)
    role = "test" if (
        {"test", "tests"} & set(relative.parts[:-1])
        or relative.name.startswith("test_") or relative.name.endswith("_test.py")
    ) else "unknown"
    for fact in extractor.capabilities + extractor.gates + extractor.flows:
        fact["source_role"] = role
    return extractor.capabilities, extractor.gates, extractor.flows, extractor.coverage


def link_facts(facts: dict) -> None:
    function_ids = {
        cap["id"] for cap in facts["capabilities"]
        if cap["kind"] in {"python-function", "agent-tool"}
    }
    for flow in facts["flows"]:
        name = flow["callee"]
        module = flow.pop("_module")
        class_name = flow.pop("_class")
        imports = flow.pop("_imports")
        candidates = []
        if "." not in name:
            candidates.append(f"{module}.{name}" if module else name)
            if name in imports:
                candidates.append(imports[name])
        else:
            base, attribute = name.rsplit(".", 1)
            if base in {"self", "cls"} and class_name:
                candidates.append(f"{module}.{class_name}.{attribute}")
            if base in imports:
                candidates.append(f"{imports[base]}.{attribute}")
        resolved = next((candidate for candidate in candidates if candidate in function_ids), None)
        flow["resolved"] = resolved
        flow["status"] = "confirmed" if resolved else "inferred"

    gates_by_function = {}
    for gate in facts["gates"]:
        gate["mapped_capability_ids"] = []
        if gate["function"]:
            gates_by_function.setdefault(gate["function"], []).append(gate["id"])
    gate_by_id = {gate["id"]: gate for gate in facts["gates"]}
    calls = {}
    for flow in facts["flows"]:
        if flow["status"] == "confirmed":
            calls.setdefault(flow["caller"], []).append(flow["resolved"])

    for cap in facts["capabilities"]:
        start = cap.get("implementation", cap["id"])
        direct = list(gates_by_function.get(cap["id"], []))
        cap["direct_gate_ids"] = direct
        cap["reachable_gate_ids"] = []
        queue = [start]
        visited = set()
        while queue:
            caller = queue.pop()
            if caller in visited:
                continue
            visited.add(caller)
            for gate_id in gates_by_function.get(caller, []):
                if gate_id not in cap["reachable_gate_ids"]:
                    cap["reachable_gate_ids"].append(gate_id)
            queue.extend(calls.get(caller, []))
        for gate_id in cap["reachable_gate_ids"]:
            gate_by_id[gate_id]["mapped_capability_ids"].append(cap["id"])

    for gate in facts["gates"]:
        if not gate["mapped_capability_ids"] and gate["kind"] != "numeric-constant":
            facts["coverage"].append({
                "fact_type": "coverage",
                "kind": "unmapped-gate",
                "status": "confirmed",
                "source": gate["source"],
                "gate_id": gate["id"],
                "message": "gate is not mapped to a discovered public capability",
            })


def extract_project(root: Path) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"project directory does not exist: {root}")
    # ponytail: facts and links still fit in RAM; larger scans need disk-backed fact/link storage.
    facts = {
        "schema_version": SCHEMA_VERSION,
        "root": str(root),
        "manifest": [],
        "capabilities": [],
        "gates": [],
        "flows": [],
        "documents": [],
        "coverage": [],
    }
    def gap(path, kind, message):
        facts["manifest"].append({"path": Path(path).relative_to(root).as_posix(), "status": "failed" if kind.startswith("unreadable") else "skipped", "reason": message})
        facts["coverage"].append({
            "fact_type": "coverage", "kind": kind, "status": "confirmed",
            "source": source_ref(Path(path).relative_to(root).as_posix(), ast.Pass()),
            "message": message,
        })

    def walk_error(exc):
        gap(exc.filename or root, "unreadable-directory", str(exc))

    for directory, dirs, files in os.walk(root, topdown=True, onerror=walk_error, followlinks=False):
        parent = Path(directory)
        retained = []
        for name in sorted(dirs):
            path = parent / name
            try:
                attributes = path.lstat()
                linked = stat.S_ISLNK(attributes.st_mode) or bool(
                    getattr(attributes, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
                )
                reason = None
                if linked:
                    reason = "directory link"
                elif name in SKIP_DIRS:
                    reason = "excluded directory name"
                elif (path / "pyvenv.cfg").is_file():
                    reason = "virtual environment marker: pyvenv.cfg"
                if reason:
                    gap(path, "excluded-directory", reason)
                else:
                    retained.append(name)
            except OSError as exc:
                gap(path, "unreadable-directory", str(exc))
        dirs[:] = retained
        for name in sorted(files):
            path = parent / name
            relative = path.relative_to(root)
            try:
                if not path.resolve().is_relative_to(root):
                    gap(path, "excluded-file", "file link resolves outside target")
                    continue
                if path.suffix not in DOCUMENT_KINDS and path.suffix != ".py":
                    facts["manifest"].append({"path": relative.as_posix(), "status": "skipped", "reason": "unsupported file type"})
                    continue
                data = path.read_bytes()
                entry = {"path": relative.as_posix(), "status": "read", "sha256": hashlib.sha256(data).hexdigest(), "line_count": len(data.splitlines())}
                facts["manifest"].append(entry)
                if path.suffix in DOCUMENT_KINDS:
                    facts["documents"].append({
                        "fact_type": "document", "path": relative.as_posix(),
                        "kind": DOCUMENT_KINDS[path.suffix],
                    })
                elif path.suffix == ".py":
                    capabilities, gates, flows, coverage = parse_python(path, relative, data)
                    if coverage:
                        entry["status"] = "parse-error"
                    facts["capabilities"].extend(capabilities)
                    facts["gates"].extend(gates)
                    facts["flows"].extend(flows)
                    facts["coverage"].extend(coverage)
            except OSError as exc:
                gap(path, "unreadable-file", str(exc))
    facts["manifest"].sort(key=lambda item: item["path"])
    facts["snapshot_id"] = hashlib.sha256(json.dumps(facts["manifest"], sort_keys=True, ensure_ascii=True).encode()).hexdigest()
    link_facts(facts)
    return facts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    args = parser.parse_args(argv)
    phase = "extraction"
    try:
        facts = extract_project(args.project)
        phase = "serialization"
        staging_dir = Path(tempfile.gettempdir()).resolve()
        if staging_dir.is_relative_to(args.project.resolve()):
            raise ValueError("temporary directory must be outside target project")
        with tempfile.TemporaryFile(mode="w+", encoding="ascii", dir=staging_dir) as staged:
            json.dump(facts, staged, ensure_ascii=True, indent=2, allow_nan=False)
            staged.write("\n")
            staged.seek(0)
            phase = "output"
            while chunk := staged.read(65536):
                sys.stdout.write(chunk)
            sys.stdout.flush()
    except (OSError, UnicodeError, ValueError, TypeError, MemoryError) as exc:
        message = str(exc).encode("ascii", errors="backslashreplace").decode("ascii").replace("\n", " ").replace("\r", " ")
        parser.exit(2, f"extract_facts: {phase}: {type(exc).__name__}: {message}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
