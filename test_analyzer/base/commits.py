from git import Repo
from github import Github

def parse_github_url(url: str):
    """
    Gera (owner, repo_name) a partir de uma URL GitHub.
    Ex: https://github.com/owner/repo.git → ("owner", "repo")
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
