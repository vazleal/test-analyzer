from git import Repo
from github import Github
import datetime
import os

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
    """Determin a partir do nome se é arquivo de teste."""
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