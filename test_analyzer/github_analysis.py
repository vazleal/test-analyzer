from .analysis import analyze_tests_local
from .base.clone import clone_repo, cleanup_repo
from .base.commits import (
    fetch_prs_and_issues,
    commit_diff_stats,
    is_test_file
)

def pr_diff_stats(pr_list):
    """
    Para cada PR em `pr_list`, retorna um dict com:
      - date: datetime (merged_at ou created_at)
      - code_lines: somatório de adições+deleções em arquivos de código
      - test_lines: somatório de adições+deleções em arquivos de teste
    """
    stats = []
    for pr in pr_list:
        dt = pr.merged_at or pr.created_at
        code = 0
        test = 0
        for f in pr.get_files():
            changes = f.additions + f.deletions
            if is_test_file(f.filename):
                test += changes
            else:
                code += changes
        stats.append({
            "date": dt,
            "code_lines": code,
            "test_lines": test,
        })
    return stats

def analyze_tests_github(github_url: str, token: str = None) -> dict:
    """
    Executa:
      1. clone do repo
      2. análise local de testes
      3. coleta de stats de commits e PRs
      4. cleanup
    Retorna um dicionário contendo:
      - métricas locais
      - total_commits, total_prs, total_issues
      - commit_stats (lista de dicts com date/code_lines/test_lines)
      - pr_stats (idem para PRs)
    """
    path = clone_repo(github_url)
    try:
        local_metrics = analyze_tests_local(path)
        commits_stats = commit_diff_stats(path)
        prs, issues = fetch_prs_and_issues(github_url, token)
        pr_stats = pr_diff_stats(prs)

        return {
            **local_metrics,
            "total_commits": len(commits_stats),
            "total_prs": len(prs),
            "total_issues": len(issues),
            "commit_stats": [
                {
                    "date": c["date"].isoformat(),
                    "code_lines": c["code_lines"],
                    "test_lines": c["test_lines"]
                } for c in commits_stats
            ],
            "pr_stats": [
                {
                    "date": p["date"].isoformat(),
                    "code_lines": p["code_lines"],
                    "test_lines": p["test_lines"]
                } for p in pr_stats
            ]
        }
    finally:
        cleanup_repo(path)