import asyncio
import base64
import json
import logging
import os
import time
import wave
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from typing import Any, Awaitable, Callable, Literal

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AsyncOpenAI
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, ChoiceDelta
from openai.types.completion_usage import CompletionUsage
from pydantic import BaseModel

# from llm.stream_watching import SentenceWatcher
import nevo_framework.llm.stream_watching as stream_watching
from nevo_framework.api.server_messages import TextChunkMessage,  EndOfResponseMessage
from nevo_framework.config.master_config import get_master_config
from nevo_framework.config.audio_config import AudioConfig
from nevo_framework.helpers.logging_helpers import LogAi, LogAiAgentResponse
from nevo_framework.llm.llm_tools import TimedWebElementMessage

log_file_path = os.path.join("logging", f"agent_duration_{datetime.now()}.log")


class TokenUse(BaseModel):
    prompt_tokens: int
    prompt_audio_tokens: int
    completion_tokens: int
    completion_audio_tokens: int


class ChatStepMetadata(BaseModel):
    audio_file: str | None
    recording_length: float
    transcription: str
    token_use: TokenUse | None


def save_audio_chunks_as_wav(audio_output_path: str, chunks: list, config: AudioConfig = None):
    """
    Save audio chunks as a WAV file.

    Args:
        audio_output_path (str): Path to save the audio file.
        chunks (list): List of audio chunks to save. This is exepcted to be a list of byte chunks as returned, for example,
            by audio streaming APIs.
        config (AudioConfig): Description of the audio format.
    """
    if config is None:
        config = AudioConfig()

    # assert os.path.exists(os.path.dirname(audio_output_path)), f"Output directory does not exist: {audio_output_path}"
    audio_data = b"".join(chunks)
    with wave.open(audio_output_path, "wb") as wav_file:
        wav_file.setnchannels(config.channels)
        wav_file.setsampwidth(config.sample_width)
        wav_file.setframerate(config.sample_rate)
        wav_file.writeframes(audio_data)
        logging.info(f"Saved audio to {audio_output_path}")


def unindent(string: str) -> str:
    return "\n".join(line.strip() for line in string.split("\n"))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(process)d] %(levelname)s [%(module)s]: %(message)s",
    # handlers=[logging.FileHandler(log_file_path), logging.StreamHandler()],
)


class AgentStreamedResponse(BaseModel):

    response_gen: str


load_dotenv()

CONFIG = get_master_config()


class GeneralAgentAsync:
    """Class for creating an async agent that can predict the intention of a user"""

    def __init__(
        self,
        system_prompt: str,
        agent_name: str = "",
        model: str | None = None,
        async_openai_client: AsyncOpenAI | AsyncAzureOpenAI | None = None,
        time_debug: bool = False,
        message_debug: bool = False,
        timeout: float = CONFIG.llm_call_timeout,
    ):

        self.client : AsyncOpenAI | AsyncAzureOpenAI = async_openai_client
        self.system_prompt = system_prompt
        self.agent_name = agent_name
        self.model = model
        self.agent_response = None
        self.time_debug = time_debug
        self.message_debug = message_debug
        self.timeout = timeout

    async def __call__(self, user_prompt: str, dialog: list[dict[str, str]] | None = None) -> str:
        start_time = time.time()
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model, # type: ignore
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        *(dialog if dialog is not None else []), # type: ignore
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.0,
                ),
                timeout=self.timeout,
            )

            self.agent_response = response.choices[0].message.content
            time_taken = f"Time taken: {(time.time()-start_time):.2f}s for " if self.time_debug else ""
            (
                logging.info(f"{time_taken}Async {self.agent_name} response:\n{self.agent_response}")
                if self.message_debug
                else ""
            )
            return self.agent_response

        except asyncio.TimeoutError:
            logging.error(f"Operation timed out - {self.timeout} seconds for {self.agent_name.replace('_', ' ')}.")
            time_taken = f"Time taken: {(time.time()-start_time):.2f}s for " if self.time_debug else ""
            return ""

        except Exception as e:
            logging.error(f"Exception: {e}")
            return "I'm sorry, but I'm unable to answer that query."


class StructuredOutputAgent:
    """Class for creating an agent that can generate structured output from input"""

    def __init__(
        self,
        model: str,
        system_prompt: str,
        response_format: Any = None,
        timeout: float = CONFIG.llm_call_timeout,
        openai_async_client=None,
    ):
        self.system_prompt = system_prompt
        self.model = model
        self.timeout = timeout
        assert openai_async_client is not None, "OpenAI client must be provided"
        self.openai_async_client = openai_async_client
        self.response_type = response_format

    async def extract_with_structured_output(self, user_message: str, dialog: list[dict[str, str]] | None = None) -> Any:
        messages = [
            {"role": "system", "content": self.system_prompt},
            *(dialog if dialog is not None else []),
            {"role": "user", "content": user_message},
        ]
        try:
            response = await self.openai_async_client.beta.chat.completions.parse(
                messages=messages, model=self.model, response_format=self.response_type, timeout=self.timeout
            )

            output = response.choices[0].message.parsed
            assert isinstance(output, self.response_type)
            return output
        except asyncio.TimeoutError as e:
            logging.error(f"Exception: {e}")
        except Exception as e:
            logging.error(f"Exception: {e}")

        return None


@dataclass
class VoiceAgentResponse:
    """A response from an audio agent."""

    # The name of the agent that generated the response.
    agent_name: str

    # The (transcribed) text of the response. Can only be None if `no_dialog_step` is set to True.
    text: str | None = None

    # any tool calls made by the agent
    tool_calls: dict[str, dict[str, Any]] | None = None

    # Web element messages are Pydantic objects that WILL BE SENT to to the client as JSON to trigger certain actions
    # on the page besides the playback of the audio response, for example, showing images matching the conversation.
    # AI components can set these messages as they see fit.
    # Use the `add_web_element_message` method to add a web element message to the response.
    _web_element_messages: list[BaseModel] = field(default_factory=list)

    def add_web_element_message(self, web_element_message: BaseModel):
        """
        Add a web element message to the response.

        Web element messages are Pydantic objects that will be sent to to the client as JSON to trigger certain actions
        on the page besides the playback of the audio response, for example, showing images matching the conversation.
        AI components can set these messages as they see fit.
        """
        self._web_element_messages.append(web_element_message)

    def with_web_element_message(self, web_element_message: BaseModel) -> "VoiceAgentResponse":
        """
        Adds a web element message to be sent to the client and return the response object.
        This is a convenience method and has the same effect as using `add_web_element_message`.
        """
        self._web_element_messages.append(web_element_message)
        return self


class VoiceAgent:
    """
    A chat agent for voice interaction, making use of the gpt4o-audio-preview model.

    * Works with either audio based chat dialogs with history (expecting the 'audio_id' in the response)
      and with one-off prompts.
    * Supports with tool / function calls.
    * Does NOT keep track of the dialog history. This is the responsibility of the caller. The AudioAgentResponse
      object returned by the chat_step methods contains all relevant information for the caller to manage the dialog.
    * set_audio_output_queue must be called before using the agent.

    """

    def __init__(
        self,
        name: str,
        default_system_message: str | None,
        tools: list[dict] | None = None,
        async_openai_client: AsyncOpenAI | AsyncAzureOpenAI = None,
        audio_output_queue: asyncio.Queue = None,
        max_conversation_length: int = 500,
        voice: str = "ash",
        temperature: float = 0.7,
        model: str = "gpt-4o-audio-preview",
    ):
        """
        Args:
            name (str): The name of the agent.
            default_system_message (str | None): The default system message to use if none is provided in the chat_step methods.
            tools (list[dict] | None): A list of tools to use for function calls. Expects proper OpenAI tool definitions.
            async_openai_client (AsyncOpenAI | None): An async OpenAI client to use for the chat completions.
            audio_output_queue (asyncio.Queue | None): An audio output queue to put audio chunks into.
            max_conversation_length (int): The maximum length of the conversation history to use in the dialog based chat step.
            voice (str): The voice to use for the audio output.
        """
        self.name = name
        self.default_system_message = (
            default_system_message if default_system_message else "You are a helpful assistant."
        )
        self.tools = tools
        self.async_openai_client = async_openai_client
        self.output_queue = audio_output_queue
        self.max_conversation_length = max_conversation_length
        self.last_ai_response = None
        self.voice = voice
        self.temperature = temperature
        self.model = model

        self.store_audio = CONFIG.has_debug_flag("store_audio")
        self.log_chat_steps = CONFIG.has_debug_flag("log_chatsteps")

        assert async_openai_client is not None, "An async OpenAI client must be provided."
        self.async_openai_client = async_openai_client
        self._modality: Literal["text", "audio"] = "audio"  # default to audio modality

    def has_audio_output_queue(self):
        return self.output_queue is not None

    def _set_audio_output_queue(self, audio_output_queue: asyncio.Queue):
        """Dont call this. This is used by the framework to set the audio output queue of the agent."""
        self.output_queue = audio_output_queue

    def _set_modality(self, modality: Literal["text", "audio"]):
        """Dont call this. This is used by the framework to set the modality of the agent."""
        assert modality in ["text", "audio"], "Modality must be either 'text' or 'audio'."
        self._modality = modality

    async def dialog_step(
        self,
        dialog: list[dict[str, str]],
        context_system_message: str | None = None,
        timed_web_element_messages: list[TimedWebElementMessage] | None = None,
        sentence_callback: (
            Callable[[str, list[str], asyncio.Queue], Awaitable[bool]] | None
        ) = None,  # e.g. async def my_callback(sentence: str, sentences: list[str], output_queue: asyncio.Queue) -> BaseModel
        sentence_watcher_terminals: list[str] | None = None,
    ) -> VoiceAgentResponse:
        """
        Executes a chat step with a system message and a dialogue of 'user' and 'assistant' messages.
        The assistant messages need to have the

                "audio": {"id": <audio_id>}

        field set in the 'assistant' parts dialog history. The audio IDs are captured and returned
        in the response (AudioAgentResponse.audio_id).

        Args:
            context_system_message (str | None): The system message to use instead of the default which was
                set by the constructor.
            dialog (list[dict[str, str]]): The dialog between the user and the assistant.
            timed_web_element_messages (list[TimedWebElementMessage] | None): A list of timed web element messages
                to be sent to the client during streaming. TimedWebElementMessage contains the message to be sent
                (any Pydantic object) and a time_delta field that specifies how many seconds after the streaming
                started the message should be sent the earliest. Note that messages will be sent latest at the end
                of the streaming, regardless of the time_delta. This is not a mechanism to enforce a strict timing.
                If the AI generates a long answer, timed messages can be used to send information to the client
                earlier than by adding the messages to the AudioAgentResponse object, which will send strictly after
                streaming. The time_delta can be used to avoid sending them too early, e.g. before the AI has even
                started speaking.

        Returns:
            str: The response from the AI.
        """
        context = [
            {
                "role": "system",
                "content": context_system_message if context_system_message else self.default_system_message,
            },
        ]
        context.extend(dialog[-self.max_conversation_length :])
        # assert messages[-1]["role"] == "user"  # this is no longer true as we allow the AI to start the dialog
        return await self._chat_step(
            messages_for_context=context,
            full_dialog=dialog,
            timed_web_element_messages=timed_web_element_messages,
            sentence_callback=sentence_callback,
            sentence_watcher_terminals=sentence_watcher_terminals,
        )

    async def _chat_step(
        self,
        messages_for_context: list[dict[str, str]],
        full_dialog: list[dict[str, str]],
        timed_web_element_messages: list[TimedWebElementMessage] | None = None,
        sentence_callback: (
            Callable[[str, list[str], asyncio.Queue], Awaitable[bool]] | None
        ) = None,  # e.g. async def my_callback(sentence: str, sentences: list[str], output_queue: asyncio.Queue) -> BaseModel
        sentence_watcher_terminals: list[str] | None = None,
    ) -> VoiceAgentResponse:
        """
        Execute a chat step with voice streaming and (potentially) tool calls.

        Args:
            messages_for_context (list[dict[str, str]]): The messages to use for the context of the AI response,
                in OpenAI API format. Typically, this the latest N messages of of the full `dialog` and a system message.
            full_dialog (list[dict[str, str]]): The full dialog history. This is only used to append the AI response to the
                dialog history in OpenAI API format, so we keep track of the conversation in future steps and other agents.
                This will **never** contain a system message, only user and assistant messages.
            timed_web_element_messages (list[TimedWebElementMessage] | None): A list of timed web element messages
                to be sent to the client during streaming.
            sentence_callback (Callable[[str, list[str], asyncio.Queue], Awaitable[bool]] | None): A callback function for
                capturing what the AI agent is saying and triggering an image to the frontend
            sentence_watcher_terminals (list[str] | None): A list of terminal strings that will be used to split the AI response

        Returns:
            VoiceAgentResponse: The response from the AI
        """
        # TODO currently not guarded against too long input
        logging.info(LogAi(f"AudioChatAgentGPT4VoiceV2 calling {self.model} ({type(self).__name__})."))
        if self._modality == "audio":
            response = await self.async_openai_client.chat.completions.create(
                model=self.model,
                messages=messages_for_context,
                modalities=["text", "audio"],
                audio={"voice": self.voice, "format": "pcm16"},
                stream=True,
                timeout=CONFIG.llm_call_timeout,
                tools=self.tools,
                temperature=self.temperature,
                stream_options={"include_usage": True} if self.log_chat_steps else None,
            )
        else:
            response = await self.async_openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages_for_context,
                stream=True,
                timeout=CONFIG.llm_call_timeout,
                tools=self.tools,
                temperature=self.temperature,
                stream_options={"include_usage": True} if self.log_chat_steps else None,
            )

        full_response_text = StringIO()
        tool_calls_raw = {}
        audio_id = None

        ################################################################
        if sentence_callback:
            text_watch_queue: asyncio.Queue = asyncio.Queue()
            timed_message_queue: asyncio.Queue = asyncio.Queue()
            watcher = stream_watching.SentenceWatcher(
                sentence_callback=sentence_callback,
                input_queue=text_watch_queue,
                output_queue=timed_message_queue,
                terminals=sentence_watcher_terminals,
            )
            stream_watcher_task = asyncio.create_task(watcher.watch_stream())
            timed_message_queue_task = None
        else:
            text_watch_queue = None
            timed_message_queue = None
            stream_watcher_task = None

        # might be useful some time
        bytes_streamed = 0
        seconds_streamed = 0
        chunk_count = 0
        SAMPLE_RATE = 24000.0
        binary_audio_chunks = []  # used if RECORD_AUDIO is True
        token_use: TokenUse | None = None

        if timed_web_element_messages:
            timed_web_element_messages = sorted(timed_web_element_messages, key=lambda x: x.time_delta)
            next_message_iter = iter(timed_web_element_messages)
            next_timed_message = next(next_message_iter, None)
        else:
            next_timed_message = None

        stream_start_time = time.time()

        async for chunk in response:
            if sentence_callback and timed_message_queue_task is None:
                # start the timed message queue task at the arrival of the first chunk to have a precise t0
                timed_message_queue_task = asyncio.create_task(
                    stream_watching.watch_timed_message_queue(
                        timed_message_queue=timed_message_queue, output_queue=self.output_queue
                    )
                )
            # print(f"------------\nchunk: {chunk}\n------------")
            if chunk.choices:  # and chunk.choices[0].delta.content:
                delta: ChoiceDelta = chunk.choices[0].delta
                time_elapsed = time.time() - stream_start_time
                if next_timed_message and time_elapsed >= next_timed_message.time_delta:
                    self.output_queue.put_nowait(next_timed_message.message)
                    next_timed_message = next(next_message_iter, None)
                if hasattr(delta, "audio"):
                    # print(f"Audio chunk: {delta.audio}")
                    chunk_count += 1
                    if self.output_queue:
                        if audio_chunk := delta.audio.get("data", None):
                            audio_bytes = base64.b64decode(audio_chunk)
                            bytes_streamed += len(audio_bytes)
                            seconds_streamed = bytes_streamed / (2.0 * SAMPLE_RATE)
                            self.output_queue.put_nowait(audio_bytes)
                            if self.store_audio:
                                binary_audio_chunks.append(audio_bytes)
                    else:
                        logging.warning(f"VoiceAgent {self.name} does not have an output queue to send audio chunks to!")
                    if text_chunk := delta.audio.get("transcript", None):
                        full_response_text.write(text_chunk)
                        if text_watch_queue:
                            text_watch_queue.put_nowait(text_chunk)
                        if False:  # TESTING!!!!!!!!
                            print(f"Text chunk: {text_chunk}")
                            self.output_queue.put_nowait(TextChunkMessage(type="text_chunk", content=text_chunk))
                    if not audio_id:
                        audio_id = delta.audio.get("id", None)

                    if False:  # package level timing debugging
                        text = delta.audio.get("transcript", None)
                        has_audio = delta.audio.get("data", None) is not None
                        print(f"Chunk: {'*' if has_audio else '.'} '{text}'")
                        if audio_chunk:
                            save_audio_chunks_as_wav(
                                audio_output_path=f"audio_{chunk_count:04d}_{full_response_text.getvalue()}_{seconds_streamed}.wav",
                                chunks=[audio_bytes],
                            )
                elif hasattr(delta, "content") and delta.content:
                    # this is used for pure text chat, which serves as a fallback and less expensive option 
                    # in case we dont want to use audio streaming
                    self.output_queue.put_nowait(TextChunkMessage(type="text_chunk", content=delta.content))
                    full_response_text.write(delta.content)
                    if text_watch_queue:
                        text_watch_queue.put_nowait(delta.content)

                if delta.tool_calls:
                    for call in delta.tool_calls:
                        tool_index = call.index
                        if tool_index not in tool_calls_raw:
                            # Tool call function names and arugments are "streamed", meaning they
                            # are potentially split up between multiple chunks. We need to assemble
                            # them here.
                            # We create a new entry if we have not seen data for the tool index yet.
                            tool_calls_raw[tool_index] = (
                                call.function.name if call.function.name else "",
                                call.function.arguments if call.function.arguments else "",
                            )
                        else:
                            # We append tool name and arguments to existing entry if we know the tool index.
                            name, args = tool_calls_raw[tool_index]
                            tool_calls_raw[tool_index] = (
                                name + call.function.name if call.function.name else name,
                                args + call.function.arguments if call.function.arguments else args,
                            )
            if chunk.usage:
                usage: CompletionUsage = chunk.usage
                token_use = TokenUse(
                    prompt_tokens=usage.prompt_tokens,
                    prompt_audio_tokens=usage.prompt_tokens_details.audio_tokens,
                    completion_tokens=usage.completion_tokens,
                    completion_audio_tokens=usage.completion_tokens_details.audio_tokens,
                )
        # if we still have timed messages to send, send them now
        while next_timed_message:
            self.output_queue.put_nowait(next_timed_message.message)
            next_timed_message = next(next_message_iter, None)

        # indicate the end of the response (which might not be the end of the dialog step)
        self.output_queue.put_nowait(EndOfResponseMessage())

        if text_watch_queue:
            text_watch_queue.put_nowait(stream_watching.SentenceWatcher.END_OF_STREAM)
            if stream_watcher_task:
                await stream_watcher_task
            if timed_message_queue_task:
                await timed_message_queue_task

        tool_calls = {}
        if tool_calls_raw:
            for index, (tool_name, tool_args) in tool_calls_raw.items():
                try:
                    tool_calls[tool_name] = json.loads(tool_args)
                except json.JSONDecodeError as e:
                    logging.error(f"Invalid JSON in tool arguments '{tool_args}' for tool {tool_name}: {e}")

        full_response_str = full_response_text.getvalue()

        if self.store_audio or self.log_chat_steps:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            if self.store_audio:
                # save the audio chunks to a wav file
                audio_output_path = os.path.join(CONFIG.recording_file_dir, f"ai_{timestamp}.wav")
                save_audio_chunks_as_wav(audio_output_path, binary_audio_chunks)
            else:
                audio_output_path = None
            meta = ChatStepMetadata(
                audio_file=audio_output_path,
                recording_length=seconds_streamed,
                transcription=full_response_str,
                token_use=token_use,
            )
            with open(os.path.join(CONFIG.recording_file_dir, f"ai_{timestamp}.json"), "w") as f:
                f.write(meta.model_dump_json(indent=2))

        # append AI response to the dialog such that the AI keeps the context of the conversation
        if audio_id:
            assert len(full_response_str) > 0, "If audio is present, text must be present too."
            full_dialog.append(
                {
                    "role": "assistant",
                    "content": full_response_str,
                    "audio": {"id": audio_id},
                }
            )
        elif len(full_response_str) > 0:
            full_dialog.append(
                {
                    "role": "assistant",
                    "content": full_response_str,
                }
            )
        else:
            logging.error(f" (no text or audio) for voice agent {self.name}.")

        self.last_ai_response = VoiceAgentResponse(
            agent_name=self.name,
            text=full_response_str,
            tool_calls=tool_calls,
        )
        logging.info(LogAiAgentResponse("AudioChatAgentGPT4VoiceV2", full_response_str))
        full_response_text.close()
        return self.last_ai_response
