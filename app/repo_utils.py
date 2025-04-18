import os
import shutil
import tempfile
from git import Repo as GitRepo, GitCommandError
from logging_config import get_logger

logger = get_logger("repo_utils")

import os
import shutil
import tempfile
from git import Repo as GitRepo, GitCommandError
from logging_config import get_logger

logger = get_logger("repo_utils")

def get_repo_path(repo_url: str = None, local_path: str = None) -> str:
    """
    Determines the local path to the repository.
    - If local_path is provided and valid, it is returned.
    - Otherwise, the repo is cloned from repo_url into a temp dir.

    Returns:
        str: Path to the local repository
    Raises:
        ValueError: If neither a valid URL nor path is provided
    """
    if local_path:
        abs_path = os.path.abspath(local_path)
        if os.path.isdir(abs_path):
            if os.path.isdir(os.path.join(abs_path, ".git")):
                logger.info(f"Using existing local Git repo: {abs_path}")
            else:
                logger.warning(f"Local path exists but is not a Git repo: {abs_path}")
            return abs_path
        else:
            logger.error(f"Provided local path does not exist: {abs_path}")
            raise ValueError(f"Local path not found: {abs_path}")

    elif repo_url:
        try:
            logger.info(f"Cloning repo from {repo_url}")
            temp_dir = tempfile.mkdtemp(prefix="mcp_repo_")
            GitRepo.clone_from(repo_url, temp_dir)
            logger.info(f"Repository cloned to {temp_dir}")
            return temp_dir
        except GitCommandError as e:
            logger.error(f"Git clone failed: {e}")
            raise

    else:
        logger.warning("No repo_url or local_path provided.")
        raise ValueError("Must provide either a valid repo_url or local_path.")

