from git import Repo
from github import Github
from git.objects.blob import Blob
import datetime
import os
from collections import defaultdict

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
    count = 0
    for pr in prs:
        for f in pr.get_files():
            if f.filename.startswith("test_") and f.filename.endswith(".py"):
                count += 1
                break
    return count

def is_test_file(path: str) -> bool:
    """Determina a partir do nome se é arquivo de teste."""
    name = os.path.basename(path)
    return name.startswith("test_") or "/tests/" in path.replace("\\", "/")

def commit_diff_stats(path: str):
    """
    Retorna uma lista de dicts com:
    - date (datetime)
    - code_lines (int): total de linhas inseridas+deletadas em arquivos de código
    - test_lines (int): total de linhas inseridas+deletadas em arquivos de teste
    """
    repo = Repo(path)
    stats = []
    # iterar na ordem cronológica
    for commit in reversed(list(repo.iter_commits())):
        dt = datetime.datetime.fromtimestamp(commit.committed_date)
        files = commit.stats.files  # {filename: {insertions, deletions, lines}}
        code = sum(v['insertions'] + v['deletions']
                   for f, v in files.items() if not is_test_file(f))
        test = sum(v['insertions'] + v['deletions']
                   for f, v in files.items() if is_test_file(f))
        stats.append({"date": dt, "code_lines": code, "test_lines": test})
    return stats

def file_count_stats(path: str):
    """
    Para cada commit (cronológico), conta:
      - prod_files: arquivos .py que NÃO são de teste
      - test_files: arquivos .py que SÃO de teste
    """
    repo = Repo(path)
    stats = []
    for commit in reversed(list(repo.iter_commits())):
        dt = datetime.datetime.fromtimestamp(commit.committed_date)
        prod = 0
        test = 0
        # percorre todo o tree do commit sem fazer checkout
        for blob in commit.tree.traverse():
            if not isinstance(blob, Blob):
                continue
            if not blob.path.endswith(".py"):
                continue
            if is_test_file(blob.path):
                test += 1
            else:
                prod += 1
        stats.append({"date": dt, "prod_files": prod, "test_files": test})
    return stats

def aggregate_stats_monthly(stats: list[dict]) -> list[dict]:
    """
    Agrupa por mês, somando code_lines/test_lines ou prod_files/test_files,
    conforme as chaves presentes em cada item.
    """
    if not stats:
        return []

    # detecta quais chaves usar
    first = stats[0]
    key_main = 'code_lines' if 'code_lines' in first else 'prod_files'
    key_test = 'test_lines' if 'test_lines' in first else 'test_files'

    groups: dict[datetime.datetime, dict] = {}
    for item in stats:
        month = item["date"].replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        grp = groups.setdefault(month, {
            "date": month,
            key_main: 0,
            key_test: 0
        })
        grp[key_main] += item.get(key_main, 0)
        grp[key_test] += item.get(key_test, 0)

    # retorna lista ordenada pelos meses
    return [groups[m] for m in sorted(groups)]

def aggregate_stats_yearly(stats: list[dict]) -> list[dict]:
    """
    Agrupa a lista de stats por ano, somando code_lines/test_lines
    ou prod_files/test_files, de acordo com as chaves presentes.
    """
    if not stats:
        return []

    first = stats[0]
    key_main = 'code_lines' if 'code_lines' in first else 'prod_files'
    key_test = 'test_lines' if 'test_lines' in first else 'test_files'

    groups: dict[datetime.datetime, dict] = {}
    for item in stats:
        year = item["date"].replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        grp = groups.setdefault(year, {
            "date": year,
            key_main: 0,
            key_test: 0
        })
        grp[key_main] += item.get(key_main, 0)
        grp[key_test] += item.get(key_test, 0)

    # retorna lista ordenada pelos anos
    return [groups[y] for y in sorted(groups)]

def aggregate_snapshots_monthly(stats):
    """
    Recebe uma lista de dicts com 'date', 'prod_files', 'test_files'.
    Retorna uma lista com o último snapshot de cada mês.
    """
    monthly = defaultdict(list)
    for s in stats:
        key = (s["date"].year, s["date"].month)
        monthly[key].append(s)
    result = []
    for key, items in monthly.items():
        # pega o último snapshot do mês
        last = max(items, key=lambda x: x["date"])
        result.append(last)
    # ordena por data
    result.sort(key=lambda x: x["date"])
    return result

def aggregate_snapshots_yearly(stats):
    """
    Recebe uma lista de dicts com 'date', 'prod_files', 'test_files'.
    Retorna uma lista com o último snapshot de cada ano.
    """
    yearly = defaultdict(list)
    for s in stats:
        key = s["date"].year
        yearly[key].append(s)
    result = []
    for key, items in yearly.items():
        # pega o último snapshot do ano
        last = max(items, key=lambda x: x["date"])
        result.append(last)
    # ordena por data
    result.sort(key=lambda x: x["date"])
    return result