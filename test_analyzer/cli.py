import argparse
import json
from .analysis import analyze_tests_local
from .github_analysis import analyze_tests_github

def main():
    parser = argparse.ArgumentParser(
        prog="test-analyzer",
        description="Analisa métricas de testes em repositórios Python (locais ou GitHub)"
    )
    parser.add_argument(
        "target",
        help="Caminho para repositório local ou URL GitHub (ex: https://github.com/owner/repo)"
    )
    parser.add_argument(
        "--token",
        help="GitHub token (opcional; útil para repositórios privados ou maior rate-limit)",
        default=None
    )
    parser.add_argument(
        "-o", "--output",
        help="Arquivo JSON de saída (stdout se omitido)",
        default=None
    )
    args = parser.parse_args()

    if args.target.startswith(("http://", "https://")):
        report = analyze_tests_github(args.target, args.token)
    else:
        report = analyze_tests_local(args.target)

    dump = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(dump)
        print(f"Relatório salvo em {args.output}")
    else:
        print(dump)
