from .analysis import analyze_tests_local
from .base.clone import clone_repo, cleanup_repo
from .base.commits import fetch_commits, fetch_prs_and_issues

def analyze_tests_github(github_url: str, token: str = None) -> dict:
    """
    Analisa repositório remoto no GitHub:
    - clona localmente
    - executa análise local de testes
    - coleta commits, PRs e issues relacionados a 'test'
    """
    path = clone_repo(github_url)
    try:
        local = analyze_tests_local(path)
        commits = fetch_commits(path)
        prs, issues = fetch_prs_and_issues(github_url, token)

        hist = {
            "total_commits": len(commits),
            "test_commits": sum(1 for c in commits if "test" in c.message.lower()),
            "total_prs": len(prs),
            "test_prs": sum(1 for pr in prs if "test" in pr.title.lower()),
            "total_issues": len(issues),
            "test_issues": sum(
                1 for i in issues
                if "test" in (i.title or "").lower() or "test" in (i.body or "").lower()
            ),
        }

        return {**local, **hist}
    finally:
        cleanup_repo(path)
