from dataclasses import dataclass
from typing import Optional
import logging
import os
import sys


LOG_LEVEL_ENV_VAR = "WIKIFY_LOG_LEVEL"
LLM_FILE_LOGGING_ENV_VAR = "WIKIFY_LLM_FILE_LOGGING"

LOG_LEVELS: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
DEFAULT_LOG_LEVEL_LABEL: str = "WARNING"


@dataclass
class Config:
    """Configuration for wikify"""

    log_level: int
    llm_file_logging: bool
    model: str
    max_tokens: int

    def __init__(
        self,
        llm_file_logging: Optional[bool] = None,
        log_level: Optional[int] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
    ):
        self.log_level = log_level or self.log_level_default()
        self.llm_file_logging = llm_file_logging or self.llm_file_logging_default(
            self.log_level
        )
        self.model = model or "claude-sonnet-4-5-20250929"
        self.max_tokens = max_tokens or 16384

    def log_level_default(self) -> int:
        log_level_label = os.getenv(LOG_LEVEL_ENV_VAR, DEFAULT_LOG_LEVEL_LABEL)
        if log_level_label in LOG_LEVELS:
            return LOG_LEVELS[log_level_label]
        else:
            sys.exit(
                f'Unrecognized log level in {LOG_LEVEL_ENV_VAR}: "{log_level_label}"'
            )

    def llm_file_logging_default(self, log_level: int) -> bool:
        explicit_config = os.getenv(LLM_FILE_LOGGING_ENV_VAR, None)
        if explicit_config is None:
            # Without explicit instruction, guess based on log_level
            return log_level < logging.WARNING
        else:
            match explicit_config.lower():
                case "true", "t", "1":
                    return True
                case "false", "f", "0":
                    return False
                case _:
                    sys.exit(
                        f'Unrecognized bool value for {LLM_FILE_LOGGING_ENV_VAR}: "{explicit_config}"'
                    )


global_config: Config = Config()
