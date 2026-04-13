from __future__ import annotations

import ast
import re
from typing import Any

from .models import SymbolSummary

IMPORT_RE = re.compile(r"""(?:from|import)\s+["']?([A-Za-z0-9_./-]+)["']?""")
FALLBACK_SYMBOL_PATTERNS = [
    re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*(?:export\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*(?:export\s+)?type\s+([A-Za-z_][A-Za-z0-9_]*)"),
]


def extract_symbols(path: str, text: str, language: str | None) -> tuple[list[SymbolSummary], list[str]]:
    if language == "python":
        return _extract_python_symbols(path, text)
    if language in {"javascript", "jsx", "typescript", "tsx"}:
        extracted = _extract_tree_sitter_symbols(path, text, language)
        if extracted is not None:
            return extracted
    return _extract_fallback_symbols(path, text)


def _extract_python_symbols(path: str, text: str) -> tuple[list[SymbolSummary], list[str]]:
    module = ast.parse(text)
    symbols: list[SymbolSummary] = []
    imports: list[str] = []

    for node in module.body:
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            imports.append(module_name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            signature = f"def {node.name}(...)"
            symbols.append(
                SymbolSummary(
                    name=node.name,
                    kind="function",
                    path=path,
                    signature=signature,
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    docstring=ast.get_docstring(node),
                )
            )
        elif isinstance(node, ast.ClassDef):
            base_names = ", ".join(_ast_name(base) for base in node.bases)
            signature = f"class {node.name}({base_names})" if base_names else f"class {node.name}"
            symbols.append(
                SymbolSummary(
                    name=node.name,
                    kind="class",
                    path=path,
                    signature=signature,
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    docstring=ast.get_docstring(node),
                )
            )
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(
                        SymbolSummary(
                            name=f"{node.name}.{child.name}",
                            kind="method",
                            path=path,
                            signature=f"def {child.name}(...)",
                            start_line=child.lineno,
                            end_line=child.end_lineno or child.lineno,
                            docstring=ast.get_docstring(child),
                        )
                    )
    return symbols, sorted(set(filter(None, imports)))


def _ast_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_ast_name(node.value)}.{node.attr}"
    return ast.unparse(node) if hasattr(ast, "unparse") else "expr"


def _extract_tree_sitter_symbols(path: str, text: str, language: str) -> tuple[list[SymbolSummary], list[str]] | None:
    try:
        import tree_sitter_javascript as ts_javascript
        import tree_sitter_typescript as ts_typescript
        from tree_sitter import Language, Parser
    except ImportError:
        return None

    if language in {"javascript", "jsx"}:
        tree_language = Language(ts_javascript.language())
    elif language == "typescript":
        tree_language = Language(ts_typescript.language_typescript())
    else:
        tree_language = Language(ts_typescript.language_tsx())

    parser = Parser(tree_language)
    source_bytes = text.encode("utf-8")
    root = parser.parse(source_bytes).root_node
    symbols: list[SymbolSummary] = []
    imports: list[str] = []

    for child in _named_children(root):
        child_type = child.type
        if child_type == "import_statement":
            imports.extend(_extract_import_strings(_node_text(child, source_bytes)))
            continue
        if child_type == "export_statement":
            inner_children = _named_children(child)
            for inner in inner_children:
                _collect_tree_sitter_symbol(path, source_bytes, inner, symbols)
                if inner.type == "import_statement":
                    imports.extend(_extract_import_strings(_node_text(inner, source_bytes)))
            continue
        _collect_tree_sitter_symbol(path, source_bytes, child, symbols)

    return symbols, sorted(set(filter(None, imports)))


def _collect_tree_sitter_symbol(
    path: str, source_bytes: bytes, node: Any, symbols: list[SymbolSummary]
) -> None:
    node_type = node.type
    if node_type in {"function_declaration", "generator_function_declaration"}:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = _node_text(name_node, source_bytes)
        symbols.append(
            _make_symbol(path, node, source_bytes, name=name, kind="function")
        )
    elif node_type == "class_declaration":
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = _node_text(name_node, source_bytes)
        symbols.append(_make_symbol(path, node, source_bytes, name=name, kind="class"))
    elif node_type in {"interface_declaration", "type_alias_declaration", "enum_declaration"}:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = _node_text(name_node, source_bytes)
        symbols.append(_make_symbol(path, node, source_bytes, name=name, kind="type"))
    elif node_type in {"lexical_declaration", "variable_declaration"}:
        for declarator in _named_children(node):
            if declarator.type != "variable_declarator":
                continue
            name_node = declarator.child_by_field_name("name")
            if name_node is None:
                continue
            name = _node_text(name_node, source_bytes)
            symbols.append(_make_symbol(path, declarator, source_bytes, name=name, kind="variable"))


def _make_symbol(
    path: str,
    node: Any,
    source_bytes: bytes,
    *,
    name: str,
    kind: str,
) -> SymbolSummary:
    start_row, _ = node.start_point
    end_row, _ = node.end_point
    signature = _node_text(node, source_bytes).splitlines()[0].strip()
    return SymbolSummary(
        name=name,
        kind=kind,
        path=path,
        signature=signature,
        start_line=start_row + 1,
        end_line=end_row + 1,
    )


def _named_children(node: Any) -> list[Any]:
    return [node.named_child(i) for i in range(node.named_child_count)]


def _node_text(node: Any, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8")


def _extract_import_strings(text: str) -> list[str]:
    return re.findall(r"""["']([^"']+)["']""", text)


def _extract_fallback_symbols(path: str, text: str) -> tuple[list[SymbolSummary], list[str]]:
    symbols: list[SymbolSummary] = []
    imports: list[str] = []
    lines = text.splitlines()

    for index, line in enumerate(lines, start=1):
        if "import " in line or "from " in line:
            imports.extend(_extract_import_strings(line))
            import_match = IMPORT_RE.search(line)
            if import_match:
                imports.append(import_match.group(1))
        for pattern in FALLBACK_SYMBOL_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            symbols.append(
                SymbolSummary(
                    name=match.group(1),
                    kind=_kind_for_line(line),
                    path=path,
                    signature=line.strip(),
                    start_line=index,
                    end_line=index,
                )
            )
            break
    return symbols, sorted(set(filter(None, imports)))


def _kind_for_line(line: str) -> str:
    lowered = line.lower()
    if "class " in lowered:
        return "class"
    if "interface " in lowered or "type " in lowered:
        return "type"
    if "const " in lowered or "let " in lowered or "var " in lowered:
        return "variable"
    if "def " in lowered or "function " in lowered:
        return "function"
    return "symbol"
