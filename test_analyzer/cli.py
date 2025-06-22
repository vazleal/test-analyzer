import argparse
import json
from .analysis import analyze_tests_local
from .github_analysis import analyze_tests_github
from .viz import plot_commit_evolution, plot_pr_evolution

def main():
    parser = argparse.ArgumentParser(
        prog="test-analyzer",
        description="Analisa métricas de testes em repositórios Python (locais ou GitHub)"
    )
    parser.add_argument(
        "target",
        help="Diretório local ou URL GitHub (ex: https://github.com/owner/repo)"
    )
    parser.add_argument(
        "--token",
        help="GitHub token (opcional; útil para repositórios privados ou rate-limit)",
        default=None
    )
    parser.add_argument(
        "-o", "--output",
        help="Salvar relatório JSON em arquivo (stdout sempre impresso)",
        default=None
    )
    args = parser.parse_args()

    # executa análise local ou remota
    if args.target.startswith(("http://", "https://")):
        report = analyze_tests_github(args.target, args.token)
    else:
        report = analyze_tests_local(args.target)

    # serializa para JSON
    dump = json.dumps(report, indent=2, ensure_ascii=False)
    print(dump)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(dump)
        print(f"\nRelatório salvo em {args.output}")

    if "commit_stats" in report and "pr_stats" in report:
        plot_commit_evolution(report["commit_stats"])
        plot_pr_evolution(report["pr_stats"])