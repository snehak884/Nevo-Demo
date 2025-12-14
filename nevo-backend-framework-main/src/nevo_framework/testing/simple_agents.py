import argparse
import asyncio
import base64
import datetime
import json
import logging
import os
import time
from collections import defaultdict
from typing import Literal

import openai
import pandas as pd
import pyaudio
from pydantic import BaseModel

from nevo_framework.config.master_config import get_master_config
from nevo_framework.config.audio_config import AudioConfig
from nevo_framework.testing.test_helpers import text_to_speech

SYSPROMPT_SALESMAN = """You are a salesperson at a car dealership. You are trying to sell a car to a customer.
You are friendly and helpful. You are patient and understanding. You are knowledgeable about the cars you are selling. 
You give short answers and ask questions to keep the conversation going. You really want to learn about your customer's needs.
Specifically, you need to know what they will use the car for, in what kind of area they live, and what their budget is. 
You don't answer with numbered lists or bullet points. You answer like a normal person would in a spoken conversation.
"""
SYSPROMPT_CUSTOMER = """You are a middle aged woman looking for a car to buy. You are interested in a family car. 
You have a budget of $50,000. You have 3 kids and two dogs. You live in the suburbs and you commute to work every day.
Your workplace in the city is 30 miles away. You are looking for a car that is safe, reliable, and fuel efficient.
You don't give the salesman too much information. You wait until you are asked before you provide more details.
"""


class SimpleChatAgent:
    """
    A very simple OpenAI chat agent with a system prompt and a conversation history.
    """

    def __init__(
        self,
        name: str,
        async_openai_client: openai.AsyncOpenAI,
        system_prompt: str,
        model: str = "gpt-4o",
        first_message: str = None,
        temperature: float = 0.8,
    ):
        """
        Initialize the chat agent with a system prompt.

        Args:
            name (str): The name of the chat agent. Used for logging, filenames, etc.
            async_openai_client (openai.AsyncOpenAI): OpenAI client for making asynchronous requests.
            system_prompt (str): The system prompt to use for the conversation. Either this or personality_file must be provided.
            model (str): The OpenAI model to use for the conversation.
            first_message (str): Optionally, the first message in the dialogue can be hard-coded.
        """
        self.name = name
        self.async_openai_client = async_openai_client
        self.model = model
        self.temperature = temperature

        self.first_message = first_message
        self.conversation = [{"role": "system", "content": system_prompt}]

    async def chat_step(self, opponent_message: str = None) -> str:
        """
        Take a step in the chat conversation. Adds opponent_message to the conversation history, if provided
        and calls the OpenAI API to generate a response, which is then added to the conversation history as well.
        `oppenent_message` can be None for the first step in the conversation.

        Args:
            opponent_message (str): The last thing the other person in the conversation said.

        Returns:
            str: The response from the chat agent.
        """
        # if we have a hard-coded first message, and we are in the first step of the conversation, use it
        if self.first_message is not None and len(self.conversation) == 1:
            self.conversation.append({"role": "user", "content": self.first_message})
            return self.first_message

        if opponent_message:
            self.conversation.append({"role": "user", "content": opponent_message})

        print(f"Calling OpenAI...")  # Debugging output
        response = await asyncio.wait_for(
            self.async_openai_client.chat.completions.create(
                model=self.model,
                messages=self.conversation,
                temperature=self.temperature,
                timeout=60.0,
            ),
            timeout=60.0,
        )
        response_content = response.choices[0].message.content
        self.conversation.append({"role": "assistant", "content": response_content})
        return response_content


class AudioChatAgent(SimpleChatAgent):
    """
    A `SimpleChatAgent` that generates audio from the text responses using OpenAI's text-to-speech API.
    Audio can be saved to a file and/or played back in real-time using PyAudio. The agent can also be used
    in pure text mode, where it generates text responses only without audio generation.
    """

    def __init__(
        self,
        name: str,
        async_openai_client: openai.AsyncOpenAI,
        system_prompt: str,
        first_message: str = None,
        model: str = "gpt-4o",
        pyaudio_stream=None,
        voice: str = "onyx",
    ):
        """
        Initialize the audio chat agent with a system prompt and optional personality file.

        Args:
            name (str): The name of the chat agent. Used for logging, filenames, etc.
            async_openai_client (openai.AsyncOpenAI): OpenAI client for making asynchronous requests.
            system_prompt (str): The system prompt to use for the conversation. Either this or personality_file must be provided.
            first_message (str): Optionally, the first message in the dialogue can be hard-coded.
            personality_file (str): Path to a YAML file containing the personality to use for the conversation.
            model (str): The OpenAI model to use for the conversation.
            pyaudio_stream (pyaudio.Stream): PyAudio stream to play the audio. If provided, the audio will be played back in real-time.
            voice (str): The voice to use for the text-to-speech conversion.
        """
        super().__init__(
            name=name,
            async_openai_client=async_openai_client,
            system_prompt=system_prompt,
            first_message=first_message,
            model=model,
        )
        self.pyaudio_stream = pyaudio_stream
        self.voice = voice

    async def chat_step(
        self, opponent_message=None, audio_output_path=None, modality: Literal["audio", "text"] = "audio"
    ):
        """
        Same as `SimpleChatAgent.chat_step`, but generates audio from the text response using OpenAI's text-to-speech API.

        Args:
            opponent_message (str): The last thing the other person in the conversation said.
            audio_output_path (str): Path to save the audio file. If None, the audio will not be saved to a file.
            modality (Literal["audio", "text"]): The modality of the response. If "audio", the response will be generated as audio
                and played back in real-time if a PyAudio stream is provided, as well as saved to a file if `audio_output_path` is provided.
                If "text", the response will be generated as text only and no audio will be generated. This makes it possible to use this
                agent for testing text-only conversations without audio generation.
        """
        assert modality in ["audio", "text"], "Modality must be either 'audio' or 'text'."
        response_content = await super().chat_step(opponent_message)
        if modality == "audio":
            await text_to_speech(
                text=response_content,
                async_openai_client=self.async_openai_client,
                pyaudio_stream=self.pyaudio_stream,
                voice=self.voice,
                audio_output_path=audio_output_path,
            )
        return response_content


class AudioChatAgentGPT4VoiceWithHistory:

    def __init__(
        self,
        name: str,
        async_openai_client: openai.AsyncOpenAI,
        pyauido_stream: pyaudio.Stream | None = None,
        system_prompt: str = None,
        audio_output_queue: asyncio.Queue = None,
    ):
        self.name = name
        self.async_openai_client = async_openai_client
        self.pyaudio_stream = pyauido_stream
        self.audio_output_queue = audio_output_queue
        if system_prompt is None:
            system_prompt = "You are a friendly assistant who provides helpful answers. You formulate your answers like a normal person would in a spoken conversation. You don't use numbered lists or bullet points."
        else:
            system_prompt = system_prompt
        self.conversation = [{"role": "system", "content": system_prompt}]

    def has_audio_output_queue(self):
        return self.audio_output_queue is not None

    def set_audio_output_queue(self, audio_output_queue: asyncio.Queue):
        self.audio_output_queue = audio_output_queue

    async def chat_step(self, opponent_message):
        """Function which takes a prompt and geenrates a voice response.

        Returns:
            float: Time taken to generate a response
        """
        if opponent_message:
            self.conversation.append({"role": "user", "content": opponent_message})

        response = await self.async_openai_client.chat.completions.create(
            model="gpt-4o-audio-preview",
            messages=self.conversation,
            # temperature=0.0, # Does temp=0 cause the infinite loop?
            modalities=["text", "audio"],
            audio={"voice": "sage", "format": "pcm16"},
            stream=True,
            timeout=5.0,
        )

        response_content_text = ""
        audio_id = None
        async for chunk in response:
            delta = chunk.choices[0].delta
            if hasattr(delta, "audio"):
                response_content_text += delta.audio.get("transcript", "")
                audio_chunk = base64.b64decode(delta.audio.get("data", b""))
                if not audio_id:
                    audio_id = delta.audio.get("id", None)
                if self.pyaudio_stream:
                    self.pyaudio_stream.write(audio_chunk)
                if self.audio_output_queue:
                    self.audio_output_queue.put_nowait(audio_chunk)

        assert audio_id is not None, "No audio ID found in response stream."

        self.conversation.append({"role": "assistant", "audio": {"id": audio_id}})
        logging.info(f"Conversation: {self.conversation}")


class AudioChatAgentGPT4Voice:

    def __init__(
        self,
        name: str,
        async_openai_client: openai.AsyncOpenAI,
        pyauido_stream: pyaudio.Stream | None = None,
        system_prompt: str = None,
        audio_output_queue: asyncio.Queue = None,
        max_conversation_length: int = 10,
    ):
        self.name = name
        self.async_openai_client = async_openai_client
        self.pyaudio_stream = pyauido_stream
        self.audio_output_queue = audio_output_queue
        if system_prompt is None:
            system_prompt = "You are a friendly assistant who provides helpful answers. You formulate your answers like a normal person would in a spoken conversation. You don't use numbered lists or bullet points."
        else:
            system_prompt = system_prompt
        self.conversation: list[dict[str, str]] = []
        self.max_conversation_length = max_conversation_length

    def has_audio_output_queue(self):
        return self.audio_output_queue is not None

    def set_audio_output_queue(self, audio_output_queue: asyncio.Queue):
        self.audio_output_queue = audio_output_queue

    async def chat_step(self, user_query: str, rag_input: str, system_message: str = None) -> str:
        """Function which takes a prompt and geenrates a voice response.

        Returns:
            float: Time taken to generate a response
        """
        # TODO limit conversation length to put in the prompt
        self.conversation = self.conversation[-10:]

        pretext = (
            f"Formulate an answer based on the conversation so far. In the converation protocol, you are the 'assistant'. "
            "This is the conversation so far:"
        )
        conversation = "\n".join([f"{msg['role']}: {msg['content'].strip()}" for msg in self.conversation])
        conversation += "\n" + rag_input
        prompt = f"{pretext}\n{conversation}"
        logging.info(f"Prompt: {prompt}")

        if system_message is not None:
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ]
        else:
            messages = [{"role": "user", "content": prompt}]

        response = await self.async_openai_client.chat.completions.create(
            model="gpt-4o-audio-preview",
            messages=messages,
            # temperature=0.0, #  Does temp=0 cause the infinite loop?
            modalities=["text", "audio"],
            audio={"voice": "sage", "format": "pcm16"},
            stream=True,
            timeout=5.0,
        )

        response_content_text = ""
        audio_id = None
        async for chunk in response:
            delta = chunk.choices[0].delta
            if hasattr(delta, "audio"):
                response_content_text += delta.audio.get("transcript", "")
                audio_chunk = base64.b64decode(delta.audio.get("data", b""))
                if not audio_id:
                    audio_id = delta.audio.get("id", None)
                if self.pyaudio_stream:
                    self.pyaudio_stream.write(audio_chunk)
                if self.audio_output_queue:
                    self.audio_output_queue.put_nowait(audio_chunk)

        assert audio_id is not None, "No audio ID found in response stream."

        self.conversation.append({"role": "user", "content": user_query})
        self.conversation.append({"role": "assistant", "content": response_content_text})
        # logging.info(f"Conversation: {self.conversation}")

        return response_content_text


async def test_gpt4o_audio():
    audio_config = AudioConfig()
    pa = pyaudio.PyAudio()
    pyaudio_stream = pa.open(
        format=pyaudio.get_format_from_width(audio_config.sample_width),
        channels=audio_config.channels,
        rate=audio_config.sample_rate,
        output=True,
    )

    agent = AudioChatAgentGPT4VoiceWithHistory(
        name="AudioChatAgentGPT4Voice",
        async_openai_client=openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")),
        pyauido_stream=pyaudio_stream,
    )

    await agent.chat_step("What is the distance between earth and moon?")
    await agent.chat_step("Tell me more!")
    await agent.chat_step("This is fascinating! Can you give a short summary of your answer in German?")

    pyaudio_stream.stop_stream()
    await asyncio.sleep(1)
    pyaudio_stream.close()


async def test_ai_to_ai_chat(with_audio: bool = False, live_audio: bool = False, num_steps: int = 10):
    """
    A simple test of two AI chat agents talking to each other.
    """

    if with_audio and live_audio:
        audio_config = AudioConfig()
        pa = pyaudio.PyAudio()
        pyaudio_stream = pa.open(
            format=pyaudio.get_format_from_width(audio_config.sample_width),
            channels=audio_config.channels,
            rate=audio_config.sample_rate,
            output=True,
        )
    else:
        pyaudio_stream = None

    first_message_customer = "I'm looking for a new car. Can you help me?"

    async_openai_client = openai.AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    if with_audio:
        ai_customer = AudioChatAgent(
            name="customer",
            async_openai_client=async_openai_client,
            system_prompt=SYSPROMPT_CUSTOMER,
            first_message=first_message_customer,
            voice="alloy",
            pyaudio_stream=pyaudio_stream,
        )
        ai_salesman = AudioChatAgent(
            name="salesman",
            async_openai_client=async_openai_client,
            system_prompt=SYSPROMPT_SALESMAN,
            voice="onyx",
            pyaudio_stream=pyaudio_stream,
        )
    else:
        ai_customer = SimpleChatAgent(
            async_openai_client=async_openai_client,
            system_prompt=SYSPROMPT_CUSTOMER,
            first_message=first_message_customer,
        )
        ai_salesman = SimpleChatAgent(async_openai_client=async_openai_client, system_prompt=SYSPROMPT_SALESMAN)

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    salesman_message = None
    for round in range(num_steps):
        if with_audio:
            wav_output_path_salesman = f"src/testing/audio_output/{timestamp}_round_{2 * round}_salesman.wav"
            wav_output_path_customer = f"src/testing/audio_output/{timestamp}_round_{2 * round+1}_customer.wav"
            customer_message = await ai_customer.chat_step(salesman_message, audio_output_path=wav_output_path_customer)
            print(f"CUSTOMER: {customer_message}")
            print()
            salesman_message = await ai_salesman.chat_step(customer_message, audio_output_path=wav_output_path_salesman)
            print(f"SALESMAN: {salesman_message}")
            print()
        else:
            customer_message = await ai_customer.chat_step(salesman_message)
            print(f"CUSTOMER: {customer_message}")
            print()
            salesman_message = await ai_salesman.chat_step(customer_message)
            print(f"SALESMAN: {salesman_message}")
            print()

    if with_audio:
        pyaudio_stream.stop_stream()
        pyaudio_stream.close()
        pa.terminate()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Test AI to AI chat with optional audio playback.")
    parser.add_argument("--play", action="store_true", help="Play audio in real-time using PyAudio.")
    args = parser.parse_args()

    # asyncio.run(test_ai_to_ai_chat(with_audio=args.play, live_audio=True))
    asyncio.run(test_gpt4o_audio())

CONFIG = get_master_config()


class ToolDescription(BaseModel):

    field_name: str
    description: str
    type_name: Literal["string", "int", "float", "bool", "number"]


class FunctionCallingAgent:
    """Class for creating an agent that can call functions"""

    def __init__(
        self,
        tools: list[dict],
        model: str = CONFIG.language_model_config.model_deployment_name["standard"],
        tool_choice: str = "auto",
        time_debug: bool = False,
        name: str = "",
        azure_openai: bool = False,
    ):

        self.client = CONFIG.language_model_config.client["text"]

        self.data = defaultdict(list)
        self.tool_descriptions: list[ToolDescription] = []
        self.model = model
        self.tools = tools
        self.tool_choice = tool_choice
        self.time_debug = time_debug
        self.name = name
        self.duration = None

        self._create_tool_descriptions()

    def _create_tool_descriptions(self):
        for tool in self.tools:

            params = tool["function"]["parameters"]
            var_name = list(tool["function"]["parameters"]["properties"].keys())[0]
            var_type = tool["function"]["parameters"]["properties"][var_name]["type"]

            self.tool_descriptions.append(
                ToolDescription(
                    field_name=params["required"][0],  # Assume only one required field
                    description=tool["function"]["description"],
                    type_name=var_type,
                )
            )

            self.data[var_name] = ""

    async def __call__(self, message: str, timeout: float = CONFIG.llm_call_timeout):
        start_time = time.time()
        """Taken mostly from: https://platform.openai.com/docs/guides/function-calling"""
        logging.info(f"length of messages in collector: {len(message)}") if self.time_debug else ""
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": message}],
                    tools=self.tools,
                    tool_choice=self.tool_choice,
                    temperature=0.0,
                ),
                timeout=timeout,
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            if tool_calls:
                for tool_call in tool_calls:
                    function_args = json.loads(tool_call.function.arguments)
                    (
                        logging.info(f"Function argument in {self.name} collector: {list(function_args.values())[0]}")
                        if self.time_debug
                        else ""
                    )
                    self.data[list(function_args.keys())[0]] = list(function_args.values())[0]

        except asyncio.TimeoutError as e:
            logging.error(
                f"Operation timed out in function call. Time taken: {timeout} seconds for {self.name} collector."
            )

        except Exception as e:
            logging.error(f"Exception: {e}")

        self.duration = round(time.time() - start_time, 2)
        logging.info(f"Time taken: {self.duration} for {self.name} collection tool") if self.time_debug else ""

        return ""

    def get_data_records(self) -> str:
        return pd.DataFrame([{"Field": field, "Collected value(s)": values} for field, values in self.data.items()])

    def get_tool_descriptions(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"Field": desc.field_name, "Description": desc.description, "Type": desc.type_name}
                for desc in self.tool_descriptions
            ]
        )

    def get_data(self) -> dict:
        return self.data
