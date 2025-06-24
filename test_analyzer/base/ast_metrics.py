from __future__ import annotations
import ast
import os
from datetime import datetime
from git import Repo
from .commits import is_test_file
from collections import Counter, defaultdict
from typing import Dict, Iterable, Set

_MOCK_CREATORS: Set[str] = {
    "mock",
    "magicmock",
    "asynctestmock",
    "asynctestmagicmock",
    "asyncmock",
    "autospec",
    "create_autospec",
    "patch",
}
_SPY_CREATORS: Set[str] = {"patch", "patch.object", "spy"}
_FAKE_MARKERS: Iterable[str] = ("fake",)
_STUB_MARKERS: Iterable[str] = ("stub",)
_DUMMY_MARKERS: Iterable[str] = ("dummy", "placeholder", "unused")

def is_unit_test_file(filepath: str) -> bool:
    """Só .py que importam unittest ou pytest."""
    if not filepath.endswith(".py"):
        return False
    try:
        src = open(filepath, encoding="utf-8").read()
        tree = ast.parse(src, filename=filepath)
    except Exception:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in ("unittest", "pytest"):
                    return True
        if isinstance(node, ast.ImportFrom):
            if node.module in ("unittest", "pytest"):
                return True
    return False

def classify_test_types(repo_path: str) -> dict:
    """
    Métrica 3:
    Conta quantos arquivos de teste são unitários, integração, E2E ou unknown.
    """
    frameworks       = {"unittest", "pytest"}
    integration_libs = {"requests", "httpx", "socket", "docker", "psycopg2", "sqlalchemy"}
    e2e_libs         = {"selenium", "playwright"}

    counts = {"unit": 0, "integration": 0, "e2e": 0, "unknown": 0}
    for root, _, files in os.walk(repo_path):
        for fname in files:
            full = os.path.join(root, fname)
            if not fname.endswith(".py") or not is_test_file(full):
                continue

            try:
                src  = open(full, encoding="utf-8").read()
                tree = ast.parse(src, filename=full)
            except Exception:
                continue

            imps = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        imps.add(a.name.split(".")[0])
                if isinstance(node, ast.ImportFrom) and node.module:
                    imps.add(node.module.split(".")[0])

            if frameworks & imps:
                counts["unit"] += 1
            elif integration_libs & imps:
                counts["integration"] += 1
            elif e2e_libs & imps:
                counts["e2e"] += 1
            else:
                counts["unknown"] += 1

    return counts


def count_functions_tested(repo_path: str) -> dict:
    """
    Conta funções em produção e quantas aparecem em testes unitários.
    """
    prod_funcs = set()
    # 1) coleta todas as functions dos .py de produção
    for root, _, files in os.walk(repo_path):
        for fname in files:
            full = os.path.join(root, fname)
            if not fname.endswith(".py") or is_test_file(full):
                continue
            try:
                tree = ast.parse(open(full, encoding="utf-8").read(), filename=full)
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    prod_funcs.add(node.name)

    tested = set()
    # 2) para cada unit test, veja se o nome da função aparece no código-fonte
    for root, _, files in os.walk(repo_path):
        for fname in files:
            full = os.path.join(root, fname)
            if not is_unit_test_file(full):
                continue
            try:
                src = open(full, encoding="utf-8").read()
            except Exception:
                continue
            for fn in prod_funcs:
                if fn in src:
                    tested.add(fn)

    return {
        "total_functions":       len(prod_funcs),
        "tested_functions":      len(tested)
    }


def compute_test_delay(repo_path: str) -> dict:
    """
    Para cada test_<foo>.py, mede delta (em dias) entre o commit que criou foo.py
    e o commit que criou test_foo.py. Retorna média e quantidade de pares.
    """
    repo = Repo(repo_path)
    prod_dates = {}
    test_dates = {}

    # commits em ordem cronológica
    commits = list(repo.iter_commits(rev="HEAD", reverse=True))
    for commit in commits:
        date = datetime.fromtimestamp(commit.committed_date)
        for path in commit.stats.files:
            if path.endswith(".py") and not is_test_file(path):
                prod_dates.setdefault(path, date)
            if is_test_file(path):
                test_dates.setdefault(path, date)

    delays = []
    for tpath, tdate in test_dates.items():
        base = os.path.basename(tpath)
        if base.startswith("test_"):
            prod_name = base[len("test_"):]
        elif base.endswith("_test.py"):
            prod_name = base[:-len("_test.py")] + ".py"
        else:
            continue

        for ppath, pdate in prod_dates.items():
            if os.path.basename(ppath) == prod_name:
                delta = (tdate - pdate).days
                if delta >= 0:
                    delays.append(delta)
                break

    if delays:
        avg = sum(delays) / len(delays)
    else:
        avg = None

    return {
        "avg_delay_days": round(avg, 2) if avg is not None else None,
        "delay_count":    len(delays)
    }


def detect_flaky_tests(repo_path: str) -> dict:
    """
    Métrica 10:
    Conta ocorrências de time.sleep, random.* e datetime.now em arquivos de teste.
    """
    counts = {"time_sleep": 0, "random_usage": 0, "datetime_now": 0}

    for root, _, files in os.walk(repo_path):
        for fname in files:
            full = os.path.join(root, fname)
            if not fname.endswith(".py") or not is_test_file(full):
                continue
            try:
                tree = ast.parse(open(full, encoding="utf-8").read(), filename=full)
            except Exception:
                continue

            for node in ast.walk(tree):
                # time.sleep()
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    v, attr = node.func.value, node.func.attr
                    if isinstance(v, ast.Name) and v.id == "time" and attr == "sleep":
                        counts["time_sleep"] += 1
                    if isinstance(v, ast.Name) and v.id == "random":
                        counts["random_usage"] += 1
                    if isinstance(v, ast.Name) and v.id == "datetime" and attr == "now":
                        counts["datetime_now"] += 1

                # sleep() ou random() direto
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == "sleep":
                        counts["time_sleep"] += 1
                    if node.func.id in ("random", "randint"):
                        counts["random_usage"] += 1

    return counts

def count_test_smells(repo_path: str) -> dict:
    """
    Varre todo o repo procurando arquivos de teste (.py) e conta três smells:
      - empty_tests: não há nenhuma função test_* definida
      - no_assert: não há nenhum assert (ast.Assert ou self.assert*)
      - unused_setup: existe def setUp/teardown mas nunca é chamado
    Retorna um dict: {"empty_tests": X, "no_assert": Y, "unused_setup": Z}
    """
    smells = {"empty_tests": 0, "no_assert": 0, "unused_setup": 0}

    for root, _, files in os.walk(repo_path):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            full = os.path.join(root, fname)
            if not is_test_file(full):
                continue

            try:
                src = open(full, encoding="utf-8").read()
                tree = ast.parse(src, filename=full)
            except (SyntaxError, UnicodeDecodeError):
                continue

            # 1) empty_tests
            funcs = [
                n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name.startswith("test")
            ]
            if not funcs:
                smells["empty_tests"] += 1

            # 2) no_assert
            has_assert = any(
                isinstance(n, ast.Assert)
                or (
                    isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr.startswith("assert")
                )
                for n in ast.walk(tree)
            )
            if not has_assert:
                smells["no_assert"] += 1

            # 3) unused_setup
            setup_names = {"setUp", "tearDown", "setup_method", "teardown_method"}
            defs = [
                n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name in setup_names
            ]
            if defs:
                calls = [
                    n for n in ast.walk(tree)
                    if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name)
                    and n.func.id in setup_names
                ]
                if not calls:
                    smells["unused_setup"] += 1

    return smells

def detect_test_doubles(repo_path: str) -> dict:
    """
    Conta usos de mocks, stubs, fakes, spies e dummies em arquivos de teste.
    """
    counts = {
        "mocks":  0,
        "stubs":  0,
        "fakes":  0,
        "spies":  0,
        "dummies":0
    }

    for root, _, files in os.walk(repo_path):
        for fname in files:
            full = os.path.join(root, fname)
            if not fname.endswith(".py") or not is_test_file(full):
                continue
            try:
                tree = ast.parse(open(full, encoding="utf-8").read(), filename=full)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    fn = node.func
                    name = ""
                    if isinstance(fn, ast.Attribute):
                        name = fn.attr.lower()
                    elif isinstance(fn, ast.Name):
                        name = fn.id.lower()

                    if "mock" in name:
                        counts["mocks"] += 1
                    if "stub" in name:
                        counts["stubs"] += 1
                    if "fake" in name:
                        counts["fakes"] += 1
                    if "spy" in name:
                        counts["spies"] += 1
                    if "dummy" in name:
                        counts["dummies"] += 1

                if isinstance(node, ast.ImportFrom):
                    mod = (node.module or "").lower()
                    if mod == "unittest.mock":
                        counts["mocks"] += len(node.names)
                    if mod == "mock":
                        counts["mocks"] += len(node.names)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        n = alias.name.lower()
                        if n in ("mock", "unittest.mock"):
                            counts["mocks"] += 1

    return counts

def _name(node: ast.AST) -> str:
    """Extrai nome (minúsculo) de um nó que represente função/atributo."""
    if isinstance(node, ast.Name):
        return node.id.lower()
    if isinstance(node, ast.Attribute):
        return node.attr.lower()
    return ""

def _has_constant_return(body: Iterable[ast.stmt]) -> bool:
    """
    Detecta se TODAS as saídas de uma função retornam Literal / Constant.
    Uma definição típica de *stub* em testes.
    """
    for stmt in body:
        if isinstance(stmt, ast.Return):
            if not isinstance(stmt.value, (ast.Constant, ast.NameConstant, ast.Num, ast.Str, ast.Bytes)):
                return False
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # definicao aninhada ignora; continua
            continue
        elif isinstance(stmt, ast.Pass):
            continue
        else:
            # tem lógica "real"
            return False
    return True

def _count_alias_imports(tree: ast.Module) -> Dict[str, str]:
    """
    Mapeia aliases de importações (ex.: 'import unittest.mock as um' → {'um': 'unittest.mock'})
    """
    alias_map: Dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").lower() in {"unittest.mock", "mock"}:
                for alias in node.names:
                    alias_map[alias.asname or alias.name] = alias.name.lower()
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.lower() in {"unittest.mock", "mock"}:
                    alias_map[alias.asname or alias.name] = alias.name.lower()
    return alias_map

def detect_test_doubles(repo_path: str) -> Dict[str, int]:
    """
    Faz _scan_ em todos os arquivos de teste (`*_test.py` ou `test_*.py`) dentro de `repo_path`
    e conta ocorrências de cinco tipos de **test doubles**:

        * mocks: instâncias criadas por `Mock`, `MagicMock`, `patch`, etc.
        * spies: `patch(..., wraps=obj)` ou similares (executa código real, mas registra)
        * stubs: funções/classe cujo nome contém “stub” **e** cujo corpo retorna valor fixo
        * fakes: classes cujo nome contém “fake” **e** com lógica interna (não apenas `pass`)
        * dummies: variáveis/args constantes cujo nome contém “dummy” ou “placeholder”

    A detecção combina análise de AST, aliases de import, nomes e heurísticas estruturais,
    resultando em **confiança alta** para projetos Python comuns.

    Retorna um `dict` com as contagens.
    """
    counters: Counter[str] = Counter()

    for root, _, files in os.walk(repo_path):
        for filename in files:
            if not filename.endswith(".py"):
                continue

            filepath = os.path.join(root, filename)
            if not is_test_file(filepath):
                continue

            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    source = fh.read()
                tree = ast.parse(source, filename=filepath)
            except (UnicodeDecodeError, SyntaxError):
                # ignora arquivo inválido
                continue

            alias_map = _count_alias_imports(tree)

            # Mocks & Spies via ast.Call (Mock(), patch(), etc.)
            for node in ast.walk(tree):
                # Chamadas de função / construtor
                if isinstance(node, ast.Call):
                    callee_name = _name(node.func)

                    # segue aliases (ex.: um.Mock())
                    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                        base = node.func.value.id
                        if base in alias_map and alias_map[base] in {"unittest.mock", "mock"}:
                            # trata como mock independente do nome do método
                            counters["mocks"] += 1
                            continue

                    if callee_name in _MOCK_CREATORS:
                        # spy é patch(..., wraps=obj)
                        if callee_name.startswith("patch"):
                            has_wraps_kw = any(
                                isinstance(kw.arg, str) and kw.arg.lower() == "wraps"
                                for kw in node.keywords
                            )
                            if has_wraps_kw:
                                counters["spies"] += 1
                            else:
                                counters["mocks"] += 1
                        else:
                            counters["mocks"] += 1

                # Atribuições x = Mock()  /  meu_spy = patch(..., wraps=obj)
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                    set_name = _name(node.value.func)

                    if set_name in _MOCK_CREATORS:
                        if set_name.startswith("patch"):
                            kw_wraps = any(
                                isinstance(kw.arg, str) and kw.arg.lower() == "wraps"
                                for kw in node.value.keywords
                            )
                            if kw_wraps:
                                counters["spies"] += 1
                            else:
                                counters["mocks"] += 1
                        else:
                            counters["mocks"] += 1

                    # Detecta variáveis dummy = <constante>
                    if isinstance(node.value, ast.Constant):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and any(
                                marker in target.id.lower() for marker in _DUMMY_MARKERS
                            ):
                                counters["dummies"] += 1
                                
            # Definições de classes e funções (Fake / Stub)
            for node in ast.walk(tree):
                # ---------- Fakes ----------
                if isinstance(node, ast.ClassDef) and any(
                    marker in node.name.lower() for marker in _FAKE_MARKERS
                ):
                    # considera "fake" apenas se houver pelo menos um método **não-pass**
                    has_logic = any(
                        isinstance(child, ast.FunctionDef)
                        and not all(isinstance(x, ast.Pass) for x in child.body)
                        for child in node.body
                    )
                    if has_logic:
                        counters["fakes"] += 1

                # ---------- Stubs ----------
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
                    marker in node.name.lower() for marker in _STUB_MARKERS
                ):
                    if _has_constant_return(node.body):
                        counters["stubs"] += 1

                # ---------- Dummies (argumentos não utilizados) ----------
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for arg in node.args.args:
                        if any(marker in arg.arg.lower() for marker in _DUMMY_MARKERS):
                            counters["dummies"] += 1

    # normaliza valores ausentes
    for key in ("mocks", "spies", "stubs", "fakes", "dummies"):
        counters.setdefault(key, 0)
    return dict(counters)