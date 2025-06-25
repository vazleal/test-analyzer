from __future__ import annotations

import ast
import os
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, Iterable, Set

from git import Repo

from .commits import is_test_file

_MOCK_CREATORS = {
    "mock",
    "magicmock",
    "asynctestmock",
    "asynctestmagicmock",
    "asyncmock",
    "autospec",
    "create_autospec",
    "patch",
}
_SPY_CREATORS = {"patch", "patch.object", "spy"}
_FAKE_MARKERS = ("fake",)
_STUB_MARKERS = ("stub",)
_DUMMY_MARKERS = ("dummy", "placeholder", "unused")

def is_unit_test_file(filepath: str):
    """Somente arquivos .py que importam unittest ou pytest."""
    if not filepath.endswith(".py"):
        return False

    try:
        with open(filepath, encoding="utf-8") as file:
            source = file.read()
        tree = ast.parse(source, filename=filepath)
    except Exception:
        return False

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = (
                node.module
                if isinstance(node, ast.ImportFrom)
                else None
            )
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            
            for name in names:
                if name in ("unittest", "pytest"):
                    return True
                
            if module in ("unittest", "pytest"):
                return True
    return False

def classify_test_types(repo_path: str):
    """
    Métrica 3:
    Conta quantos arquivos de teste são unitários, integração, E2E ou unknown.
    """
    frameworks = {"unittest", "pytest"}
    integration_libs = {"requests", "httpx", "socket", "docker", "psycopg2", "sqlalchemy"}
    e2e_libs = {"selenium", "playwright"}

    counts = {"unit": 0, "integration": 0, "e2e": 0, "unknown": 0}

    for root, _, files in os.walk(repo_path):
        for filename in files:
            filepath = os.path.join(root, filename)
            if not filename.endswith(".py") or not is_test_file(filepath):
                continue

            try:
                with open(filepath, encoding="utf-8") as file:
                    source = file.read()
                tree = ast.parse(source, filename=filepath)
            except Exception:
                continue

            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])

            if frameworks & imports:
                counts["unit"] += 1
            elif integration_libs & imports:
                counts["integration"] += 1
            elif e2e_libs & imports:
                counts["e2e"] += 1
            else:
                counts["unknown"] += 1

    return counts

def count_functions_tested(repo_path: str):
    """
    Conta funções em produção e quantas aparecem em testes unitários.
    """
    prod_functions = set()

    for root, _, files in os.walk(repo_path):
        for filename in files:
            filepath = os.path.join(root, filename)
            if not filename.endswith(".py") or is_test_file(filepath):
                continue
            try:
                with open(filepath, encoding="utf-8") as file:
                    source = file.read()
                tree = ast.parse(source, filename=filepath)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    prod_functions.add(node.name)

    tested_functions = set()

    for root, _, files in os.walk(repo_path):
        for filename in files:
            filepath = os.path.join(root, filename)
            if not is_unit_test_file(filepath):
                continue

            try:
                with open(filepath, encoding="utf-8") as file:
                    source = file.read()
            except Exception:
                continue

            for func_name in prod_functions:
                if func_name in source:
                    tested_functions.add(func_name)

    return {
        "total_functions": len(prod_functions),
        "tested_functions": len(tested_functions),
    }

def compute_test_delay(repo_path: str):
    """
    Para cada test_<foo>.py, mede delta (em dias) entre o commit que criou foo.py
    e o commit que criou test_foo.py. Retorna média e quantidade de pares.
    """
    repo = Repo(repo_path)
    prod_dates: Dict[str, datetime] = {}
    test_dates: Dict[str, datetime] = {}

    commits = list(repo.iter_commits(rev="HEAD", reverse=True))
    for commit in commits:
        commit_date = datetime.fromtimestamp(commit.committed_date)
        for path in commit.stats.files:
            if path.endswith(".py") and not is_test_file(path):
                prod_dates.setdefault(path, commit_date)
            elif is_test_file(path):
                test_dates.setdefault(path, commit_date)

    delays = []
    for test_path, test_date in test_dates.items():
        filename = os.path.basename(test_path)
        if filename.startswith("test_"):
            prod_filename = filename[len("test_"):]
        elif filename.endswith("_test.py"):
            prod_filename = filename[: -len("_test.py")] + ".py"
        else:
            continue

        for prod_path, prod_date in prod_dates.items():
            if os.path.basename(prod_path) == prod_filename:
                delta_days = (test_date - prod_date).days
                if delta_days >= 0:
                    delays.append(delta_days)
                break

    average_delay = round(sum(delays) / len(delays), 2) if delays else None
    return {"avg_delay_days": average_delay, "delay_count": len(delays)}



def detect_flaky_tests(repo_path: str):
    """
    Métrica 10:
    Conta ocorrências de time.sleep, random.* e datetime.now em arquivos de teste.
    """
    counts = {"time_sleep": 0, "random_usage": 0, "datetime_now": 0}

    for root, _, files in os.walk(repo_path):
        for filename in files:
            filepath = os.path.join(root, filename)
            if not filename.endswith(".py") or not is_test_file(filepath):
                continue

            try:
                with open(filepath, encoding="utf-8") as file:
                    source = file.read()
                tree = ast.parse(source, filename=filepath)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    value = node.func.value
                    attr = node.func.attr
                    if isinstance(value, ast.Name) and value.id == "time" and attr == "sleep":
                        counts["time_sleep"] += 1
                    if isinstance(value, ast.Name) and value.id == "random":
                        counts["random_usage"] += 1
                    if isinstance(value, ast.Name) and value.id == "datetime" and attr == "now":
                        counts["datetime_now"] += 1
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == "sleep":
                        counts["time_sleep"] += 1
                    if node.func.id in ("random", "randint"):
                        counts["random_usage"] += 1

    return counts

def count_test_smells(repo_path: str):
    """
    Varre todo o repo procurando arquivos de teste (.py) e conta três smells:
      - empty_tests: sem funções test_* definidas
      - no_assert: sem assert (ast.Assert ou self.assert*)
      - unused_setup: existe setup mas não é chamado
    """
    smells = {"empty_tests": 0, "no_assert": 0, "unused_setup": 0}

    setup_names = {"setUp", "tearDown", "setup_method", "teardown_method"}

    for root, _, files in os.walk(repo_path):
        for filename in files:
            if not filename.endswith(".py"):
                continue
            filepath = os.path.join(root, filename)
            if not is_test_file(filepath):
                continue

            try:
                with open(filepath, encoding="utf-8") as file:
                    source = file.read()
                tree = ast.parse(source, filename=filepath)
            except (SyntaxError, UnicodeDecodeError):
                continue

            func_defs = [
                node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test")
            ]
            if not func_defs:
                smells["empty_tests"] += 1

            has_assert = any(
                isinstance(node, ast.Assert) or
                (
                    isinstance(node, ast.Call) and
                    isinstance(node.func, ast.Attribute) and
                    node.func.attr.startswith("assert")
                )
                for node in ast.walk(tree)
            )
            if not has_assert:
                smells["no_assert"] += 1

            defs = [
                node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name in setup_names
            ]
            if defs:
                calls = [
                    node for node in ast.walk(tree)
                    if (
                        isinstance(node, ast.Call) and
                        isinstance(node.func, ast.Name) and
                        node.func.id in setup_names
                    )
                ]
                if not calls:
                    smells["unused_setup"] += 1

    return smells


def _name(node: ast.AST):
    """Extrai nome (minúsculo) de um nó de função ou atributo."""
    if isinstance(node, ast.Name):
        return node.id.lower()
    if isinstance(node, ast.Attribute):
        return node.attr.lower()
    return ""

def _has_constant_return(body: Iterable[ast.stmt]):
    """
    Retorna True se todas as saídas de uma função retornam Constant.
    """
    for stmt in body:
        if isinstance(stmt, ast.Return):
            if not isinstance(stmt.value, (ast.Constant,)):
                return False
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Pass)):
            continue
        else:
            return False
    return True

def _count_alias_imports(tree: ast.Module):
    """
    Mapeia aliases de importações (ex.: import unittest.mock as um será {'um':'unittest.mock'}).
    """
    alias_map = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.module or "").lower() in {"unittest.mock", "mock"}:
            for alias in node.names:
                alias_map[alias.asname or alias.name] = alias.name.lower()
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.lower() in {"unittest.mock", "mock"}:
                    alias_map[alias.asname or alias.name] = alias.name.lower()
    return alias_map

def detect_test_doubles(repo_path: str):
    """
    Conta usos de mocks, spies, stubs, fakes e dummies em arquivos de teste.
    """
    counters = Counter()
    for root, _, files in os.walk(repo_path):
        for filename in files:
            if not filename.endswith(".py"):
                continue
            filepath = os.path.join(root, filename)
            if not is_test_file(filepath):
                continue

            try:
                with open(filepath, encoding="utf-8") as file:
                    source = file.read()
                tree = ast.parse(source, filename=filepath)
            except (UnicodeDecodeError, SyntaxError):
                continue

            alias_map = _count_alias_imports(tree)

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    callee = node.func
                    name = _name(callee)
                    # mocks and spies
                    if name in _MOCK_CREATORS | _SPY_CREATORS:
                        if name.startswith("patch") and any(
                            isinstance(kw.arg, str) and kw.arg.lower() == "wraps" for kw in node.keywords
                        ):
                            counters["spies"] += 1
                        else:
                            counters["mocks"] += 1
                    # dummy assignments
                    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and any(
                                marker in target.id.lower() for marker in _DUMMY_MARKERS
                            ):
                                counters["dummies"] += 1

                if isinstance(node, ast.ImportFrom):
                    module = (node.module or "").lower()
                    if module in {"unittest.mock", "mock"}:
                        counters["mocks"] += len(node.names)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.lower() in {"mock", "unittest.mock"}:
                            counters["mocks"] += 1

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and any(
                    marker in node.name.lower() for marker in _FAKE_MARKERS
                ):
                    has_logic = any(
                        isinstance(child, ast.FunctionDef) and child.body and not all(isinstance(x, ast.Pass) for x in child.body)
                        for child in node.body
                    )
                    if has_logic:
                        counters["fakes"] += 1

                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
                    marker in node.name.lower() for marker in _STUB_MARKERS
                ):
                    if _has_constant_return(node.body):
                        counters["stubs"] += 1

                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for arg in node.args.args:
                        if any(marker in arg.arg.lower() for marker in _DUMMY_MARKERS):
                            counters["dummies"] += 1

    return {key: counters.get(key, 0) for key in ("mocks", "spies", "stubs", "fakes", "dummies")}