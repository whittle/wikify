import logging
from typing import Any

from SCons.Script import Builder

from .config import global_config
from .builders.extraction import extract_action
from .git.registry import get_data_repo_path


def init_wikify() -> None:
    logging.basicConfig(level=global_config.log_level)


def create_extraction_builder(env: Any) -> Any:
    """Create and return the extraction Builder.

    Args:
        env: SCons environment

    Returns:
        An SCons Builder configured for extraction
    """
    return Builder(
        action=extract_action,
        suffix=".json",
        src_suffix=".txt",
    )


__all__ = [
    "create_extraction_builder",
    "get_data_repo_path",
    "init_wikify",
]
