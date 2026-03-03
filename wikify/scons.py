import logging

from .config import global_config
from .builders.extraction import create_extraction_builder
from .git.registry import get_data_repo_path


def init_wikify() -> None:
    logging.basicConfig(level=global_config.log_level)


__all__ = [
    "create_extraction_builder",
    "get_data_repo_path",
    "init_wikify",
]
