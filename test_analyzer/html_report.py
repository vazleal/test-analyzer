import os
import json
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

class HtmlReport:
    TEMPLATE_NAME = 'template.html'
    TITLE_PLACEHOLDER = '{{TITLE}}'
    DATE_PLACEHOLDER = '{{CREATED_DATE}}'
    JSON_PLACEHOLDER = '{{JSON_DATA}}'

    def __init__(self, report: dict, title: str = None, filename: str = 'report.html'):
        self.report = report
        self.title = title or 'Relatório Test Analyzer'
        self.filename = filename

    def generate(self):
        base = os.path.dirname(__file__)
        tpl_path = os.path.join(base, self.TEMPLATE_NAME)
        with open(tpl_path, 'r', encoding='utf-8') as f:
            tpl = f.read()

        datetime_now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")

        payload = {
            **self.report,
            "charts": self._build_chart_configs()
        }
        json_data = json.dumps(payload, indent=2, ensure_ascii=False)

        content = tpl.replace(self.TITLE_PLACEHOLDER, self.title)
        content = content.replace(self.DATE_PLACEHOLDER, datetime_now)
        content = content.replace(self.JSON_PLACEHOLDER, json_data)

        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write(content)

        return os.path.abspath(self.filename)

    def _build_chart_configs(self):
        charts = []
        
        if 'commit_stats' in self.report:
            charts.append({
                'title': 'Evolução de Commits (LOC)',
                'type': 'line',
                'indexAxis': 'x',
                'display_legend': True,
                'labels': [c['date'] for c in self.report['commit_stats']],
                'datasets': [
                  {'label': 'Código', 'data': [c['code_lines'] for c in self.report['commit_stats']]},
                  {'label': 'Testes', 'data': [c['test_lines'] for c in self.report['commit_stats']]}
                ]
            })
            
        if 'pr_stats' in self.report:
            charts.append({
                'title': 'Evolução de PRs (LOC)',
                'type': 'line',
                'indexAxis': 'x',
                'display_legend': True,
                'labels': [p['date'] for p in self.report['pr_stats']],
                'datasets': [
                  {'label': 'Código', 'data': [p['code_lines'] for p in self.report['pr_stats']]},
                  {'label': 'Testes', 'data': [p['test_lines'] for p in self.report['pr_stats']]}
                ]
            })
            
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
            
        charts.append({
            "title": "Densidade de Teste por Commit",
            "type": "line",
            "labels": [c["date"] for c in self.report["commit_stats"]],
            "datasets": [
                {
                    "label": "Densidade de Teste",
                    "data": [c["test_density"] for c in self.report["commit_stats"]],
                    "fill": False
                }
            ]
        })

        charts.append({
            "title": "Densidade de Teste por PR",
            "type": "line",
            "labels": [p["date"] for p in self.report["pr_stats"]],
            "datasets": [
                {
                    "label": "Densidade de Teste",
                    "data": [p["test_density"] for p in self.report["pr_stats"]],
                    "fill": False
                }
            ]
        })
        
        charts.append({
            "title": "Smells de Teste (AST)",
            "type": "bar",
            "labels": [
                "Testes vazios", 
                "Testes sem assert", 
                "Setup/TearDown não usado"
            ],
            "datasets": [
                {
                    "label": "Quantidade de ocorrências",
                    "data": [
                        self.report["test_smells"]["empty_tests"],
                        self.report["test_smells"]["no_assert"],
                        self.report["test_smells"]["unused_setup"]
                    ],
                    "fill":  False
                }
            ]
        })
        
        charts.append({
            "title": "Distribuição de Tipos de Testes",
            "type": "bar",
            "labels": list(self.report["test_types"].keys()),
            "datasets": [{
                "label": "Arquivos de teste",
                "data": list(self.report["test_types"].values()),
                "fill": False
            }]
        })
        
        charts.append({
            "title": "Funções Produção Testadas vs Não Testadas",
            "type": "bar",
            "labels": ["Testadas", "Não testadas"],
            "datasets": [{
                "label": "Quantidade de funções",
                "data": [
                    self.report["tested_functions"],
                    self.report["total_prod_functions"] - self.report["tested_functions"]
                ],
                "fill": False
            }]
        })
        
        charts.append({
            "title": "Tempo Médio até o Primeiro Teste (dias)",
            "type": "bar",
            "labels": ["Média delay"],
            "datasets": [{
                "label": "Dias",
                "data":  [self.report["avg_test_delay_days"] or 0],
                "fill": False
            }]
        })

        charts.append({
            "title": "Testes Flaky Detectados",
            "type": "bar",
            "labels": [
                "Chamadas a time.sleep()",
                "Uso de random",
                "Uso de datetime.now()"
            ],
            "datasets": [{
                "label": "Número de ocorrências",
                "data": [
                    self.report["flaky_tests"]["time_sleep"],
                    self.report["flaky_tests"]["random_usage"],
                    self.report["flaky_tests"]["datetime_now"]
                ],
                "fill": False
            }]
        })
        
        charts.append({
            "title": "Uso de Test Doubles",
            "type": "bar",
            "labels": [
                "Mocks",
                "Stubs",
                "Fakes",
                "Spies",
                "Dummies"
            ],
            "datasets": [{
                "label": "Ocorrências",
                "data": [
                    self.report["test_doubles"]["mocks"],
                    self.report["test_doubles"]["stubs"],
                    self.report["test_doubles"]["fakes"],
                    self.report["test_doubles"]["spies"],
                    self.report["test_doubles"]["dummies"],
                ],
                "fill": False
            }]
        })
        
        return charts
