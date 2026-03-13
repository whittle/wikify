import logging
from typing import Any

from SCons.Script import Builder

from .builders.aggregation import merge_action, split_action
from .builders.extraction import extract_action
from .config import global_config
from .git.registry import get_data_repo_path


def init_wikify(_: dict) -> None:
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


def create_split_builder(env: Any) -> Any:
    """Create and return the split Builder.

    Args:
        env: SCons environment

    Returns:
        An SCons Builder configured for splitting extractions
    """
    return Builder(
        action=split_action,
    )


def create_merge_builder(env: Any) -> Any:
    """Create and return the merge Builder.

    Args:
        env: SCons environment

    Returns:
        An SCons Builder configured for merging entity data
    """
    return Builder(
        action=merge_action,
        suffix=".json",
    )


__all__ = [
    "create_extraction_builder",
    "create_merge_builder",
    "create_split_builder",
    "get_data_repo_path",
    "init_wikify",
]
