"""The master configuration class"""

from typing import Literal, Any
import os
import openai
import logging
from pydantic import BaseModel, Field


class LanguageModelConfig(BaseModel):
    deployment: Literal["OpenAI", "Azure"]
    model_deployment_name: dict[str, str]
    api_version: dict[str, str] = {}
    client: dict[str, Any] = {}


class MasterConfig(BaseModel):
    config_name: str
    language_model_config: LanguageModelConfig
    ai_speaks_first: bool
    orchestrator_class: str
    # llm_call timeout
    llm_call_timeout: float
    # number of seconds to wait for a recording file from the client
    timeout_wait_for_frontend_message: float = 180
    # number of minutes after which a session is considered inactive
    timeout_session_activity_minutes: float = 2
    # number of seconds between session cleanup checks
    session_cleanup_interval_seconds: float = 60
    # if true, the JSON message indicating the end of the stream will contain the full AI response
    send_response_text_in_end_of_stream: bool = False
    # the file directory for saving temporary user recording files:
    recording_file_dir: str = "temp"
    # maximum number of car models to be matched by the keyword search
    max_keyword_matches: int = 2
    # Values for calculating where to place images based on the character length of the bot's message
    voice_timing_coefficient: float = 0.07106299  # 0.06
    voice_timing_offset: float = -1.09183838  # 1.2
    # Whether to remove the context as we enter each new phase
    context_by_phase_cutoff: bool = True
    prompt_repo_path: str | None = "config/prompts.json"
    # The regex to match the CORS origin header. This is set to allow localhost and any port, which is useful for development.
    cors_regex: str = r"^http:\/\/localhost(:[0-9]+)?$"

    debug_flags: list[str] = Field(default_factory=list)

    def has_debug_flag(self, flag: str) -> bool:
        """Check if the debug flag is set"""
        return flag in self.debug_flags


def _load_config_from_json(filepath: str = "config/master_config.json") -> MasterConfig:
    """Load the master configuration from a JSON file."""

    print(
        f"Loading master config from {filepath}"
    )  # this is printed due to logging setup lagging the first config loading

    if not os.path.exists(filepath):
        filepath = "../" + filepath

    assert os.path.exists(filepath), f"Configuration file {filepath} does not exist."

    with open(filepath, "r") as file:
        master_config = MasterConfig.model_validate_json(file.read())
        logging.info(f"Loaded configuration from {filepath}")

    if master_config.language_model_config.deployment == "Azure":
        master_config.language_model_config.client["audio"] = openai.AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("API_BASE"),  # type: ignore
            api_version=master_config.language_model_config.api_version["audio"],
        )

        master_config.language_model_config.client["text"] = openai.AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("API_BASE"),  # type: ignore
            api_version=master_config.language_model_config.api_version["text"],
        )
    elif master_config.language_model_config.deployment == "OpenAI":
        # both of these dictionary entried have the same client; this is for consistency with the above
        master_config.language_model_config.client["audio"] = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        master_config.language_model_config.client["text"] = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    else:
        raise ValueError("Only Azure and OpenAI are supported")

    # NB: This is a workaround for us needing to use OpenAI for STT because Azure has too low of a rate limit
    master_config.language_model_config.client["stt"] = openai.AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    if debug_flags := os.getenv("API_DEBUG"):
        master_config.debug_flags = debug_flags.split(",")

    _config_singleton = master_config
    return _config_singleton


_config_singleton: MasterConfig = _load_config_from_json()


def load_json_config() -> MasterConfig:
    """
    For compatibility with the old codebase, this function is used to return the master config.
    It will not actually reload the config, but rather return the already loaded singleton.
    """
    logging.warning("get_master_config is deprecated. Use get_master_config() instead.")
    return _config_singleton


def get_master_config() -> MasterConfig:
    """
    Get the master configuration singleton.
    """
    return _config_singleton
