# Test Analyzer 🧪📊  
Análise automatizada de métricas de testes em projetos **Python** — gere relatórios **HTML** ricos (gráficos, tabelas) e/ou **JSON** em um único comando.

> **Por quê?**  
> Entender a saúde dos testes é fundamental para manter a qualidade do código e evitar regressões.  
> O **test-analyzer** coleta estatísticas (cobertura, complexidade, test doubles, flaky tests, etc.), agrega por ano ou por mês e exibe tudo em um painel interativo.

---

## Instalação

```bash
# dentro do diretório do projeto
pip install -e .
# (ou) publicação:
pip install test-analyzer
```

Depois disso, o executável `test-analyzer` ficará disponível no seu PATH.

---

## Uso básico

```text
test-analyzer TARGET [opções]
```

| Parâmetro           | Descrição                                                                                                                                                          | Padrão          |
|---------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------|
| `TARGET`            | Caminho local **ou** URL do repositório no GitHub (HTTPS).                                                                                                          | —               |
| `--token TOKEN`     | Token pessoal do GitHub para aumentar o limite de requisições e acessar repositórios privados.                                                                     | _None_          |
| `-o, --output PATH` | Salva o relatório em **JSON** no caminho indicado.                                                                                                                  | _None_          |
| `-m, --monthly`     | Faz a agregação **mensal** em vez de anual.                                                                                                                         | _anual_         |
| `--branch NAME`     | Branch a ser analisada. Somente relevante para URLs GitHub.                                                                                                         | `main`          |

> **Observação**  
> Para repositórios **locais**, a análise sempre considera o conteúdo que já está clonado em disco; não é preciso (nem possível) indicar `--branch`.

---

## Exemplos de execução

### 1. Analisar um repositório local

```bash
test-analyzer /caminho/para/meu_projeto
# Relatório HTML salvo em ./meu_projeto_test_report.html
```

### 2. Analisar um repositório público no GitHub

```bash
test-analyzer https://github.com/psf/black
```

### 3. Usar agregação **mensal** e analisar uma branch específica

```bash
test-analyzer https://github.com/pandas-dev/pandas --branch stable --m
```

### 4. Salvar também o resultado em JSON

```bash
test-analyzer /caminho/para/meu_projeto -o metrics.json
```

### 5. Autenticar com token do GitHub (repositório privado ou limites maiores de requisições do GitHub)

```bash
export GITHUB_TOKEN=ghp_xxx              # ou defina no shell
test-analyzer https://github.com/minhaorg/meurepo --token $GITHUB_TOKEN
```

---

## Saídas geradas

1. **HTML interativo** — sempre criado; abra no navegador para visualizar gráficos e tabelas.  
2. **JSON** (opcional) — contém o mesmo conjunto de métricas para integrações ou análises personalizadas.