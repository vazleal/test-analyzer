import argparse
import json
from .analysis           import analyze_tests_local
from .github_analysis   import analyze_tests_github
from .html_report       import HtmlReport

def main():
    parser = argparse.ArgumentParser(
        prog="test-analyzer",
        description="Análise de métricas de testes em repositórios Python"
    )
    parser.add_argument("target", help="Diretório local ou URL GitHub")
    parser.add_argument("--token", help="GitHub token (opcional)", default=None)
    parser.add_argument("-o", "--output", help="Salvar relatório JSON em arquivo", default=None)
    parser.add_argument(
        "-m", "--monthly",
        action="store_true",
        help="Agregação mensal (padrão: anual)"
    )
    parser.add_argument(
        "--branch",
        help="Branch a ser analisada (padrão: main)",
        default="main"
    )

    args = parser.parse_args()

    gran = "monthly" if args.monthly else "yearly"

    # 1) executa análise
    if args.target.startswith(("http://", "https://")):
        report = analyze_tests_github(
            args.target,
            token=args.token,
            branch=args.branch,
            granularity=gran
        )
    else:
        # para local, suponha granularidade anual (ou você pode agregar também)
        report = analyze_tests_local(args.target)

    # 2) salva JSON, se desejado
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Relatório JSON salvo em {args.output}")

    # 3) gera sempre o HTML
    html_path = HtmlReport(report).generate()
    print(f"Relatório HTML salvo em {html_path}")