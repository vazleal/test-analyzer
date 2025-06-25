import os

def analyze_tests_local(path: str):
    """
    Analisa um repositório local em Python:
    - conta arquivos de teste (test_*.py)
    - calcula média de linhas por arquivo de teste
    """
    test_files = []
    for root, _, files in os.walk(path):
        for filename in files:
            if filename.startswith("test_") and filename.endswith(".py"):
                test_files.append(os.path.join(root, filename))

    total_files = len(test_files)
    total_lines = 0
    for file_path in test_files:
        try:
            with open(file_path, "r", encoding="utf-8") as file_handler:
                total_lines += sum(1 for _ in file_handler)
        except (OSError, UnicodeDecodeError):
            print(f"Aviso: não foi possível ler {filepath}: {e}")
            continue

    avg_lines = round(total_lines / total_files, 1) if total_files else 0.0

    return {
        "num_test_files": total_files,
        "avg_test_file_lines": avg_lines,
    }
