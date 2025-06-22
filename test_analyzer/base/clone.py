# test_analyzer/_gitevo_base/clone.py

import tempfile
import shutil
from git import Repo, GitCommandError

def read_repos_from_txt(filepath):
    with open(filepath, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]
    
def get_repo_name_from_url(url: str) -> str:
    """
    Extrai o nome do repositório da URL.
    Ex: https://github.com/org/repo.git -> repo
    """
    name = url.rstrip('/').split('/')[-1]
    if name.endswith('.git'):
        name = name[:-4]
    return name

def clone_repo(github_url: str, branch: str = "main") -> str:
    """
    Clona o repositório GitHub em um diretório temporário e faz checkout na branch desejada.
    Se a branch não existir, cai silenciosamente na branch padrão.
    Retorna o path do diretório clonado.
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        # Clona sem checkout de submódulos, para ser mais rápido
        repo = Repo.clone_from(
            github_url,
            tmp_dir,
            multi_options=["--no-single-branch"],  # garante histórico completo
        )
        # tenta trocar de branch
        try:
            repo.git.checkout(branch)
        except GitCommandError:
            # branch não existe: não falha, fica na default (geralmente 'main' ou 'master')
            pass
    except Exception:
        # em caso de erro geral, limpa e propaga
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    return tmp_dir

def cleanup_repo(path: str):
    """
    Remove o diretório temporário criado para o clone.
    """
    shutil.rmtree(path, ignore_errors=True)