import tempfile
import shutil
from git import Repo

def clone_repo(github_url: str) -> str:
    """
    Clona o repositório GitHub para um diretório temporário
    e retorna o path onde foi clonado.
    """
    tmp_dir = tempfile.mkdtemp()
    Repo.clone_from(github_url, tmp_dir)
    return tmp_dir

def cleanup_repo(path: str):
    """
    Remove o diretório temporário criado para o clone.
    """
    shutil.rmtree(path, ignore_errors=True)
