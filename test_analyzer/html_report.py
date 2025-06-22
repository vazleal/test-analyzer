import os
import json
from datetime import datetime

class HtmlReport:
    TEMPLATE_NAME = 'template.html'
    TITLE_PLACEHOLDER   = '{{TITLE}}'
    DATE_PLACEHOLDER    = '{{CREATED_DATE}}'
    JSON_PLACEHOLDER    = '{{JSON_DATA}}'

    def __init__(self, report: dict, title: str = None, filename: str = 'report.html'):
        self.report = report
        self.title = title or 'Relatório Test Analyzer'
        self.filename = filename

    def generate(self) -> str:
        # Leitura o template
        base = os.path.dirname(__file__)
        tpl_path = os.path.join(base, self.TEMPLATE_NAME)
        with open(tpl_path, 'r', encoding='utf-8') as f:
            tpl = f.read()

        # Prepara substituições
        now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
        # incorporamos os charts gerados em viz.py sob a chave "charts"
        payload = {
            **self.report,
            "charts": self._build_chart_configs()
        }
        json_data = json.dumps(payload, indent=2, ensure_ascii=False)

        # Substitui no template
        content = tpl.replace(self.TITLE_PLACEHOLDER, self.title)
        content = content.replace(self.DATE_PLACEHOLDER, now)
        content = content.replace(self.JSON_PLACEHOLDER, json_data)

        # Grava o HTML final
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write(content)

        return os.path.abspath(self.filename)

    def _build_chart_configs(self) -> list[dict]:
        """
        Converte os dados do report em configurações compatíveis
        para Chart.js. Reúne commit_stats e pr_stats em duas charts.
        """
        charts = []
        
        # Commit evolution
        if 'commit_stats' in self.report:
            charts.append({
                'title': 'Evolução de Commits',
                'type': 'line',
                'indexAxis': 'x',
                'display_legend': True,
                'labels': [c['date'] for c in self.report['commit_stats']],
                'datasets': [
                  {'label': 'Código', 'data': [c['code_lines'] for c in self.report['commit_stats']]},
                  {'label': 'Testes', 'data': [c['test_lines'] for c in self.report['commit_stats']]}
                ]
            })
            
        # PR evolution
        if 'pr_stats' in self.report:
            charts.append({
                'title': 'Evolução de PRs',
                'type': 'line',
                'indexAxis': 'x',
                'display_legend': True,
                'labels': [p['date'] for p in self.report['pr_stats']],
                'datasets': [
                  {'label': 'Código', 'data': [p['code_lines'] for p in self.report['pr_stats']]},
                  {'label': 'Testes', 'data': [p['test_lines'] for p in self.report['pr_stats']]}
                ]
            })
        
        # Files evolution
        if 'file_stats' in self.report:
            charts.append({
                'title': 'Evolução de Arquivos (Produção vs Testes)',
                'type': 'line',
                'indexAxis': 'x',
                'display_legend': True,
                'labels': [f['date'] for f in self.report['file_stats']],
                'datasets': [
                    {'label': 'Produção', 'data': [f['prod_files'] for f in self.report['file_stats']]},
                    {'label': 'Testes',   'data': [f['test_files'] for f in self.report['file_stats']]}
                ]
            })
        return charts
