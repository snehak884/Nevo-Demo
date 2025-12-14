import asyncio
from dataclasses import dataclass
import logging
import os
from typing import Any, TypeVar

import openai
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from nevo_framework.config.master_config import get_master_config


load_dotenv()

CONFIG = get_master_config()


@dataclass
class TimedWebElementMessage:
    """A timed web element message to be sent to the client."""

    # the time in seconds when the message should be sent, after streaming started
    time_delta: float

    # the web element message to be sent - some Pydantic object that will be sent to the client as JSON
    message: BaseModel


async def rewrite_query(dialogue: list[dict[str, str]], dialogue_steps: int = 3, rewrite_prompt: str | None = None) -> str:
    """Rewrite the user query based on the conversation history

    Args:
        dialogue (list[dict[str, str]]): The conversation history
        dialogue_steps (int, optional): The number of dialogue steps to consider. Defaults to 3.

    Returns (str): The rewritten user query
    """

    chat_messages = " ".join([f"{message['role']}: {message['content']}\n" for message in dialogue[-dialogue_steps:]])

    # If the system prompt is not provided, use a default one
    rewrite_prompt = rewrite_prompt or (
        "Rewrite the user's final message from the following conversation so it is maximally clear and specific for a knowledge base search. "
        "Use only information present in the conversation to resolve references or ambiguities. "
        "Preserve the user's intent. "
        "If the final message is already clear and specific, return it unchanged. "
        "Return only the rewritten query, with no preamble or explanation. "
        f"Conversation:\n{chat_messages}"
    ) 

    try:
        rewritten_prompt = await CONFIG.language_model_config.client["text"].chat.completions.create(
            model=CONFIG.language_model_config.model_deployment_name["mini"],
            messages=[{"role": "user", "content": rewrite_prompt}],
            temperature=0.0,
        )

        return rewritten_prompt.choices[0].message.content
    except Exception as e:
        logging.error(f"Error: {e}")
        return dialogue[-1]["content"]


def trim_prompt(prompt: str) -> str:
    """
    Trims the prompt by removing leading and trailing white spaces.
    """
    return "\n".join(line.strip() for line in prompt.split("\n"))


T = TypeVar("T", bound=BaseModel)


def maybe_get(dictionary: dict[str, Any] | None, pydantic_model_t: T, log_failures: bool = False) -> T | None:
    """
    Returns a Pydantic class if the dictionary is not None and of the type `pydantic_model_t`. Else, returns None.
    """
    if dictionary is None:
        return None
    else:
        try:
            message = pydantic_model_t.model_validate(dictionary)
            return message
        except ValidationError:
            if log_failures:
                logging.info(f"Message {dictionary} is not of type {pydantic_model_t}.")
            return None


async def transcribe_recording(recording_file_path: str) -> str:
    """
    Uses and OpenAI model to transcribe a recorded voice audio file.
    Raises a RuntimeError if the recording file is not found.

    Args:
        recording_file_path (str): The path to the audio file to transcribe.

    Returns:
        str: The transcription of the audio file.
    """
    if not os.path.exists(recording_file_path):
        raise RuntimeError(f"Recording file not found: {recording_file_path}")

    with open(recording_file_path, "rb") as audio_file:
        transcript = await CONFIG.language_model_config.client["stt"].audio.transcriptions.create(
            model=CONFIG.language_model_config.model_deployment_name["stt"],
            file=audio_file,
            response_format="text",
            timeout=CONFIG.llm_call_timeout,
            # prompt="If the user mentions an email address, always use the '@' symbol in the address."
        )
        return transcript

    raise RuntimeError("illegal state / no transcript returned")


async def main():
    print("Testing LLM tools")
    logging.basicConfig(level=logging.WARNING)
    chat_messages = [
        {"role": "user", "content": "I'm looking for a black Skoda Enyaq with 4 wheel drive"},
        {"role": "assistant", "content": "Great, would you prefer electric or hybrid?"},
        {"role": "user", "content": "Which one has a longer range?"},
    ]

    corroutines = await asyncio.gather(
        rewrite_query(chat_messages),
        # manual_routing([{"role": "user", "content": "Does it have infotainment?"}], None)
    )
    return corroutines
