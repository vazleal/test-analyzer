from .analysis import analyze_tests_local
from .base.clone import clone_repo, cleanup_repo
from .base.commits import *
import datetime
from .base.ast_metrics import *

def analyze_tests_github(
    github_url: str,
    token: str = None,
    branch: str = "main",
    granularity: str = "yearly"
) -> dict:
    path = clone_repo(github_url, branch)
    try:
        local_metrics    = analyze_tests_local(path)

        raw_commits      = commit_diff_stats(path)
        raw_file_stats   = file_count_stats(path)
        prs, issues      = fetch_prs_and_issues(github_url, token)
        raw_pr_stats     = pr_diff_stats(prs)
        
        test_smells = count_test_smells(path)
        test_types     = classify_test_types(path)
        func_metrics   = count_functions_tested(path)
        delay_metrics  = compute_test_delay(path)
        flaky_metrics  = detect_flaky_tests(path)
        doubles_metrics = detect_test_doubles(path)
        
        num_prs_with_test_changes = count_prs_with_test_changes(prs)

        # aplica agregação conforme granularidade
        if granularity == "monthly":
            commits         = aggregate_stats_monthly(raw_commits)
            pr_aggregated   = aggregate_stats_monthly(raw_pr_stats)
            file_snapshots  = aggregate_snapshots_monthly(raw_file_stats)
        else:  # yearly
            commits         = aggregate_stats_yearly(raw_commits)
            pr_aggregated   = aggregate_stats_yearly(raw_pr_stats)
            file_snapshots  = aggregate_snapshots_yearly(raw_file_stats)

        # formata saída usando 'date' para compatibilidade com HtmlReport
        commit_stats = [
            {
                "date":        entry["period"],
                "code_lines":  entry.get("code_lines", 0),
                "test_lines":  entry.get("test_lines", 0),
                "test_density": round(
                    entry.get("test_lines", 0)
                    / max(entry.get("code_lines", 1), 1)
                , 4)
            }
            for entry in commits
        ]

        pr_stats = [
            {
                "date":        entry["period"],
                "code_lines":  entry.get("code_lines", 0),
                "test_lines":  entry.get("test_lines", 0),
                "test_density": round(
                    entry.get("test_lines", 0)
                    / max(entry.get("code_lines", 1), 1)
                , 4)
            }
            for entry in pr_aggregated
        ]

        file_stats = [
            {
                "date":        entry["period"],
                "prod_files":  entry.get("prod_files", 0),
                "test_files":  entry.get("test_files", 0)
            }
            for entry in file_snapshots
        ]

        return {
            **local_metrics,
            "test_doubles": doubles_metrics,
            "test_types": test_types,
            "total_prod_functions": func_metrics["total_functions"],
            "tested_functions": func_metrics["tested_functions"],
            "avg_test_delay_days": delay_metrics["avg_delay_days"],
            "test_delay_count": delay_metrics["delay_count"],
            "flaky_tests": flaky_metrics,
            "total_commits": len(commit_stats),
            "total_prs": len(prs),
            "test_smells": test_smells,
            "prs_with_test_changes": num_prs_with_test_changes,
            "total_issues": len(issues),
            "commit_stats": commit_stats,
            "pr_stats": pr_stats,
            "file_stats": file_stats
        }
    finally:
        cleanup_repo(path)