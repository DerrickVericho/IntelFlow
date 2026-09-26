"""Structural checks for backend function annotations."""

import ast
from collections.abc import Iterator
from pathlib import Path


BACKEND_ROOT = Path(__file__).parents[1]
FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


def _function_nodes(tree: ast.AST) -> Iterator[FunctionNode]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _annotation_violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []

    for function in _function_nodes(tree):
        parameters = [
            *function.args.posonlyargs,
            *function.args.args,
            *function.args.kwonlyargs,
        ]
        if function.args.vararg is not None:
            parameters.append(function.args.vararg)
        if function.args.kwarg is not None:
            parameters.append(function.args.kwarg)

        for parameter in parameters:
            if parameter.arg not in {"self", "cls"} and parameter.annotation is None:
                violations.append(
                    f"{path.relative_to(BACKEND_ROOT)}:{function.lineno} "
                    f"{function.name}() parameter '{parameter.arg}' has no type"
                )

        if function.returns is None:
            violations.append(
                f"{path.relative_to(BACKEND_ROOT)}:{function.lineno} "
                f"{function.name}() has no return type"
            )

    return violations


def test_backend_functions_are_fully_annotated() -> None:
    violations = [
        violation
        for path in BACKEND_ROOT.rglob("*.py")
        for violation in _annotation_violations(path)
    ]

    assert not violations, "\n".join(violations)
