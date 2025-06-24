from git import Repo
from github import Github
from git.objects.blob import Blob
from datetime import datetime
import os
from collections import defaultdict
from functools import lru_cache
from typing import List, Dict, Any

def parse_github_url(url: str):
    """
    Gera (owner, repo_name) a partir de uma URL GitHub.
    Ex: https://github.com/owner/repo.git -> ("owner", "repo")
    """
    trimmed = url.rstrip(".git")
    parts = trimmed.split("github.com/")[-1].split("/")
    if len(parts) < 2:
        raise ValueError(f"URL inválida: {url}")
    return parts[0], parts[1]

def fetch_commits(path: str):
    """
    Retorna lista de commits do repositório local apontado por `path`.
    """
    repo = Repo(path)
    return list(repo.iter_commits())

def fetch_prs_and_issues(github_url: str, token: str = None):
    """
    Busca todas as PRs e Issues (abertas e fechadas) via API do PyGithub.
    """
    gh = Github(token) if token else Github()
    owner, repo_name = parse_github_url(github_url)
    repository = gh.get_repo(f"{owner}/{repo_name}")
    prs = list(repository.get_pulls(state="all"))
    issues = list(repository.get_issues(state="all"))
    return prs, issues

def count_prs_with_test_changes(prs):
    """
    Conta PRs que modificam ao menos um arquivo de teste.
    Usa is_test_file para identificar consistentemente.
    """
    count = 0
    for pr in prs:
        for f in pr.get_files():
            if is_test_file(f.filename):
                count += 1
                break
    return count

def is_test_file(path):
    """
    Identifica arquivos de teste Python com padrões comuns:
    - Nomes iniciados por test_ (test_*.py)
    - Nomes terminados em _test.py ou _spec.py
    - Qualquer arquivo .py dentro de diretório tests/
    Retorna True apenas para arquivos Python de teste.
    """
    lower = path.lower()
    if not lower.endswith('.py'):
        return False

    # padrão de diretório tests/
    if lower.startswith('tests/') or '/tests/' in lower:
        return True

    # Python conventions
    if lower.startswith('test_') or lower.endswith(('_test.py', '_spec.py')):
        return True

    return False

def is_prod_file(path):
    """
    Identifica arquivos de produção Python: apenas arquivos .py que não são testes.
    """
    lower = path.lower()
    return lower.endswith('.py') and not is_test_file(path)

def commit_diff_stats(repo_path: str) -> List[Dict[str, Any]]:
    """
    Para cada commit, conta linhas de código de produção e de teste
    e calcula a densidade de testes (test_density).
    """
    repo = Repo(repo_path)
    stats: List[Dict[str, Any]] = []

    for commit in repo.iter_commits():
        date = datetime.utcfromtimestamp(commit.committed_date)
        files = commit.stats.files

        code_lines = sum(
            info["insertions"] + info["deletions"]
            for path, info in files.items()
            if is_prod_file(path)
        )
        test_lines = sum(
            info["insertions"] + info["deletions"]
            for path, info in files.items()
            if is_test_file(path)
        )

        test_density = (test_lines / code_lines) if code_lines else 0.0

        stats.append({
            "date":         date,
            "code_lines":   code_lines,
            "test_lines":   test_lines,
            "test_density": test_density
        })

    return stats

def pr_diff_stats(pr_list: List[Any]) -> List[Dict[str, Any]]:
    """
    Para cada PR, conta linhas de código de produção e de teste
    e calcula a densidade de testes (test_density).
    """
    
    pr_list = [pr for pr in pr_list if pr.closed_at and pr.merge_commit_sha is not None]
    
    stats: List[Dict[str, Any]] = []

    for pr in pr_list:
        files = pr.get_files()

        code_lines = sum(
            f.additions + f.deletions
            for f in files
            if is_prod_file(f.filename)
        )
        test_lines = sum(
            f.additions + f.deletions
            for f in files
            if is_test_file(f.filename)
        )

        test_density = (test_lines / code_lines) if code_lines else 0.0

        stats.append({
            "date":         pr.closed_at,
            "code_lines":   code_lines,
            "test_lines":   test_lines,
            "test_density": test_density
        })

    return stats

@lru_cache(maxsize=None)
def count_files_in_tree(tree):
    """
    Conta recursivamente arquivos de produção e de teste no snapshot.
    Retorna tupla (prod_files, test_files).
    Só arquivos Python são contabilizados.
    """
    prod = 0
    test = 0
    for blob in tree.traverse():
        if blob.type == "blob" and blob.path:
            if is_test_file(blob.path):
                test += 1
            elif is_prod_file(blob.path):
                prod += 1
    return prod, test

def file_count_stats(repo_path):
    """
    Para cada commit, conta arquivos de produção e de teste no snapshot final.
    Usa cache para evitar múltiplas travessias da mesma árvore.
    """
    repo = Repo(repo_path)
    stats = []
    for commit in repo.iter_commits():
        prod_files, test_files = count_files_in_tree(commit.tree)
        stats.append({
            'date': datetime.utcfromtimestamp(commit.committed_date),
            'prod_files': prod_files,
            'test_files': test_files,
        })
    return stats

def aggregate_stats_monthly(raw_stats):
    """
    Agrupa métricas por mês, somando valores. Garante consistência de chaves.
    """
    if not raw_stats:
        return []
    # Validar chaves
    expected = set(raw_stats[0].keys()) - {'date'}
    for item in raw_stats:
        if set(item.keys()) - {'date'} != expected:
            raise ValueError("Inconsistent metric keys in raw_stats")
    # Agregação
    agg = defaultdict(lambda: {k: 0 for k in expected})
    for item in raw_stats:
        period = item['date'].strftime("%Y-%m")
        for k in expected:
            agg[period][k] += item[k]
    return [
        {'period': period, **metrics}
        for period, metrics in sorted(agg.items())
    ]

def aggregate_stats_yearly(raw_stats):
    """
    Agrupa métricas por ano, somando valores. Garante consistência de chaves.
    """
    if not raw_stats:
        return []
    expected = set(raw_stats[0].keys()) - {'date'}
    for item in raw_stats:
        if set(item.keys()) - {'date'} != expected:
            raise ValueError("Inconsistent metric keys in raw_stats")
    agg = defaultdict(lambda: {k: 0 for k in expected})
    for item in raw_stats:
        period = item['date'].strftime("%Y")
        for k in expected:
            agg[period][k] += item[k]
    return [
        {'period': period, **metrics}
        for period, metrics in sorted(agg.items())
    ]

def aggregate_snapshots_monthly(raw_stats):
    """
    Retorna o snapshot final de arquivos por mês, incluindo meses sem commits.
    """
    if not raw_stats:
        return []
    # Ordena por data
    items = sorted(raw_stats, key=lambda x: x['date'])
    first_date = items[0]['date']
    last_date = items[-1]['date']
    # Gera períodos mensais completos
    periods = []
    cur = datetime(first_date.year, first_date.month, 1)
    end = datetime(last_date.year, last_date.month, 1)
    while cur <= end:
        periods.append(cur.strftime("%Y-%m"))
        if cur.month == 12:
            cur = datetime(cur.year + 1, 1, 1)
        else:
            cur = datetime(cur.year, cur.month + 1, 1)
    # Monta snapshots
    last_snapshot = {}
    snapshots = []
    idx = 0
    for period in periods:
        # Avança até o último item daquele mês
        while idx < len(items) and items[idx]['date'].strftime("%Y-%m") == period:
            last_snapshot[period] = items[idx]
            idx += 1
        snap = last_snapshot.get(period)
        if snap:
            snapshots.append({
                'period': period,
                'prod_files': snap.get('prod_files', 0),
                'test_files': snap.get('test_files', 0),
            })
        else:
            snapshots.append({
                'period': period,
                'prod_files': 0,
                'test_files': 0,
            })
    return snapshots

def aggregate_snapshots_yearly(raw_stats):
    """
    Retorna o snapshot final de arquivos por ano, incluindo anos sem commits.
    """
    if not raw_stats:
        return []
    items = sorted(raw_stats, key=lambda x: x['date'])
    first_date = items[0]['date']
    last_date = items[-1]['date']
    periods = [str(y) for y in range(first_date.year, last_date.year + 1)]
    last_snapshot = {}
    idx = 0
    snapshots = []
    for period in periods:
        while idx < len(items) and items[idx]['date'].strftime("%Y") == period:
            last_snapshot[period] = items[idx]
            idx += 1
        snap = last_snapshot.get(period)
        if snap:
            snapshots.append({
                'period': period,
                'prod_files': snap.get('prod_files', 0),
                'test_files': snap.get('test_files', 0),
            })
        else:
            snapshots.append({
                'period': period,
                'prod_files': 0,
                'test_files': 0,
            })
    return snapshots