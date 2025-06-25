import os
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Tuple

from git import Repo
from git.objects.blob import Blob
from github import Github

def parse_github_url(url: str):
    """
    Extrai (owner, repo_name) de uma URL GitHub
    """
    trimmed = url.rstrip(".git")
    parts = trimmed.split("github.com/", 1)[-1].split("/")
    if len(parts) < 2:
        raise ValueError(f"URL inválida: {url}")
    return parts[0], parts[1]

def fetch_commits(repo_path: str):
    """
    Retorna lista de commits do repositório local em repo_path
    """
    repo = Repo(repo_path)
    return list(repo.iter_commits())

def fetch_prs_and_issues(github_url: str, token: str = None):
    """
    Busca todas as PRs e Issues (abertas e fechadas) via PyGithub
    """
    client = Github(token) if token else Github()
    owner, repo_name = parse_github_url(github_url)
    repository = client.get_repo(f"{owner}/{repo_name}")
    prs = list(repository.get_pulls(state="all"))
    issues = list(repository.get_issues(state="all"))
    return prs, issues

def count_prs_with_test_changes(prs: List[Any]):
    """
    Conta PRs que modificam ao menos um arquivo de teste.
    """
    total = 0
    for pr in prs:
        for file in pr.get_files():
            if is_test_file(file.filename):
                total += 1
                break
    return total

def is_test_file(path: str):
    """
    Identifica arquivos de teste Python:
      - test_*.py, *_test.py, *_spec.py
      - qualquer .py em diretório tests/
    """
    lower = path.lower()
    if not lower.endswith(".py"):
        return False
    if lower.startswith("tests/") or "/tests/" in lower:
        return True
    if lower.startswith("test_") or lower.endswith(("_test.py", "_spec.py")):
        return True
    return False

def is_prod_file(path: str):
    """
    Identifica arquivos de produção Python (não são testes)
    """
    lower = path.lower()
    return lower.endswith(".py") and not is_test_file(path)

def commit_diff_stats(repo_path: str):
    """
    Para cada commit, conta linhas de produção e teste, além de calcular densidade de testes
    """
    repo = Repo(repo_path)
    stats = []
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
        density = test_lines / code_lines if code_lines else 0.0
        stats.append({
            "date": date,
            "code_lines": code_lines,
            "test_lines": test_lines,
            "test_density": density,
        })
    return stats

def pr_diff_stats(pr_list: List[Any]):
    """
    Para cada PR fechado com merge, conta linhas de produção e teste, além de calcular densidade de testes
    """
    filtered = [
        pr for pr in pr_list
        if pr.closed_at and pr.merge_commit_sha
    ]
    stats = []
    for pr in filtered:
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
        density = test_lines / code_lines if code_lines else 0.0
        stats.append({
            "date": pr.closed_at,
            "code_lines": code_lines,
            "test_lines": test_lines,
            "test_density": density,
        })
    return stats

@lru_cache(maxsize=None)
def count_files_in_tree(tree: Any):
    """
    Conta arquivos de produção e de teste em um snapshot de árvore
    """
    prod_count = 0
    test_count = 0
    for blob in tree.traverse():
        if isinstance(blob, Blob) and blob.path:
            if is_test_file(blob.path):
                test_count += 1
            elif is_prod_file(blob.path):
                prod_count += 1
    return prod_count, test_count

def file_count_stats(repo_path: str):
    """
    Para cada commit, retorna contagem de arquivos de produção e teste.
    """
    repo = Repo(repo_path)
    stats = []
    for commit in repo.iter_commits():
        prod_files, test_files = count_files_in_tree(
            commit.tree
        )
        stats.append({
            "date": datetime.utcfromtimestamp(
                commit.committed_date
            ),
            "prod_files": prod_files,
            "test_files": test_files,
        })
    return stats

def aggregate_stats_monthly(raw_stats: List[Dict[str, Any]]):
    """
    Agrupa métricas por mês, somando valores.
    """
    if not raw_stats:
        return []
    keys = set(raw_stats[0].keys()) - {"date"}
    for item in raw_stats:
        if set(item.keys()) - {"date"} != keys:
            raise ValueError(
                "Chaves inconsistentes em raw_stats"
            )
    aggregated: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {k: 0 for k in keys}
    )
    for item in raw_stats:
        period = item["date"].strftime("%Y-%m")
        for k in keys:
            aggregated[period][k] += item[k]
    return [
        {"period": period, **metrics}
        for period, metrics in sorted(
            aggregated.items()
        )
    ]

def aggregate_stats_yearly(raw_stats: List[Dict[str, Any]]):
    """
    Agrupa métricas por ano, somando valores.
    """
    if not raw_stats:
        return []
    keys = set(raw_stats[0].keys()) - {"date"}
    for item in raw_stats:
        if set(item.keys()) - {"date"} != keys:
            raise ValueError(
                "Chaves inconsistentes em raw_stats"
            )
    aggregated = defaultdict(lambda: {k: 0 for k in keys})
    for item in raw_stats:
        year = item["date"].strftime("%Y")
        for k in keys:
            aggregated[year][k] += item[k]
    return [
        {"period": year, **metrics}
        for year, metrics in sorted(
            aggregated.items()
        )
    ]

def aggregate_snapshots_monthly(raw_stats: List[Dict[str, Any]]):
    """
    Retorna os snapshots agregados mensalmente
    """
    if not raw_stats:
        return []
    items = sorted(raw_stats, key=lambda x: x["date"])
    first = items[0]["date"]
    last = items[-1]["date"]
    periods: List[str] = []
    current = datetime( first.year, first.month, 1 )
    end = datetime( last.year, last.month, 1 )
    while current <= end:
        periods.append(current.strftime("%Y-%m"))
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)
    last_snap = {}
    snapshots = []
    idx = 0
    for period in periods:
        while idx < len(items) and items[idx]["date"].strftime("%Y-%m") == period:
            last_snap[period] = items[idx]
            idx += 1
        snap = last_snap.get(period)
        if snap:
            snapshots.append({
                "period": period,
                "prod_files": snap.get("prod_files", 0),
                "test_files": snap.get("test_files", 0),
            })
        else:
            snapshots.append({
                "period": period,
                "prod_files": 0,
                "test_files": 0,
            })
    return snapshots

def aggregate_snapshots_yearly(raw_stats: List[Dict[str, Any]]):
    """
    Retorna os snapshots agregados anualmente
    """
    if not raw_stats:
        return []
    items = sorted(raw_stats, key=lambda x: x["date"])
    years = [
        str(y)
        for y in range(
            items[0]["date"].year,
            items[-1]["date"].year + 1
        )
    ]
    last_snap = {}
    snapshots = []
    idx = 0
    for year in years:
        while (
            idx < len(items)
            and items[idx]["date"].strftime("%Y") == year
        ):
            last_snap[year] = items[idx]
            idx += 1
        snap = last_snap.get(year)
        if snap:
            snapshots.append({
                "period": year,
                "prod_files": snap.get("prod_files", 0),
                "test_files": snap.get("test_files", 0),
            })
        else:
            snapshots.append({
                "period": year,
                "prod_files": 0,
                "test_files": 0,
            })
    return snapshots
