import os

def analyze_tests_local(path: str) -> dict:
    """
    Analisa um repositório local em Python:
    - conta arquivos test_*.py
    - calcula média de linhas por arquivo de teste
    """
    test_files = []
    for root, _, files in os.walk(path):
        for f in files:
            if f.startswith("test_") and f.endswith(".py"):
                test_files.append(os.path.join(root, f))

    total = len(test_files)
    avg_lines = 0
    for tf in test_files:
        with open(tf, 'r', encoding='utf-8') as fp:
            avg_lines += sum(1 for _ in fp)
    avg_lines = round(avg_lines / total, 1) if total else 0

    return {
        "num_test_files": total,
        "avg_test_file_lines": avg_lines,
    }
