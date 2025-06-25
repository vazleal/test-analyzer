import tempfile
import shutil

from git import Repo, GitCommandError

def read_repos_from_txt(filepath: str):
    """
    Lê uma lista de URLs de repositórios de um arquivo de texto
    """
    with open(filepath, encoding="utf-8") as file_handler:
        return [line.strip() for line in file_handler if line.strip()]
    
def get_repo_name_from_url(url: str):
    """
    Extrai o nome do repositório de uma URL GitHub
    """
    name = url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[: -len(".git")]
    return name

def clone_repo(github_url: str, branch: str = "main"):
    """
    Clona um repositório GitHub em um diretório temporário e faz checkout na branch desejada
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        repo = Repo.clone_from(
            github_url,
            tmp_dir,
            multi_options=["--no-single-branch"],
        )
        try:
            repo.git.checkout(branch)
        except GitCommandError:
            # Branch não encontrada: usa a branch padrão do repositório
            pass
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    
    return tmp_dir

def cleanup_repo(path: str):
    """
    Remove o diretório temporário criado para o clone
    """
    shutil.rmtree(path, ignore_errors=True)