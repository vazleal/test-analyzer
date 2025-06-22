from .analysis import analyze_tests_local
from .base.clone import clone_repo, cleanup_repo
from .base.commits import *

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

def analyze_tests_github(
    github_url: str,
    token: str = None,
    branch: str = "main",
    granularity: str = "yearly"
) -> dict:
    path = clone_repo(github_url, branch)
    try:
        local_metrics = analyze_tests_local(path)

        raw_commits = commit_diff_stats(path)
        raw_files   = file_count_stats(path)
        prs, issues = fetch_prs_and_issues(github_url, token)
        raw_pr_stats = pr_diff_stats(prs)

        # aplica agregação conforme granularidade
        if granularity == "monthly":
            commits = aggregate_stats_monthly(raw_commits)
            pr_stats = aggregate_stats_monthly(raw_pr_stats)
            file_stats = aggregate_stats_monthly(raw_files)
        else:  # yearly
            commits = aggregate_stats_yearly(raw_commits)
            pr_stats = aggregate_stats_yearly(raw_pr_stats)
            file_stats = aggregate_stats_yearly(raw_files)

        commit_stats = [
            {"date": c["date"].isoformat(),
             "code_lines": c["code_lines"],
             "test_lines": c["test_lines"]}
            for c in commits
        ]
        pr_stats = [
            {"date": p["date"].isoformat(),
             "code_lines": p["code_lines"],
             "test_lines": p["test_lines"]}
            for p in pr_stats
        ]
        file_stats = [
            {"date": f["date"].isoformat(), "prod_files": f["prod_files"], "test_files": f["test_files"]}
            for f in file_stats
        ]

        return {
            **local_metrics,
            "total_commits": len(commit_stats),
            "total_prs":     len(prs),
            "total_issues":  len(issues),
            "commit_stats":  commit_stats,
            "pr_stats":      pr_stats,
            "file_stats":    file_stats
        }
    finally:
        cleanup_repo(path)