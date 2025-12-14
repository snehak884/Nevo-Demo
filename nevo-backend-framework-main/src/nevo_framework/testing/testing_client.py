import argparse
import asyncio
import datetime
import logging
import os
from http.cookies import SimpleCookie
from typing import Literal
import time

import aiofiles
import aiohttp
import openai
import pyaudio
import pydantic
import websockets
from dotenv import load_dotenv
from websockets.exceptions import InvalidStatus

import nevo_framework.api.server_messages as server_messages
import nevo_framework.testing.test_helpers as test_helpers
from nevo_framework.config.audio_config import AudioConfig
from nevo_framework.testing.testing_bot import TestingAudioAgent


class HttpError(Exception):
    """Custom exception for HTTP errors."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


load_dotenv()
AUDIO_UPLOAD_TEST_FILE = "src/testing/audio_input/looking-for-a-car.wav"


async_openai_client = openai.AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)


class Client:

    def __init__(
        self,
        base_url: str,
        password: str,
        ai_speaks_first: bool,
        modality: Literal["audio", "text"],
        ai_customer_system_prompt: str | None = None,
        play_audio: bool = False,
        audio_output_path: str = None,
        customer_first_message: str = None,
    ):

        assert modality in ["audio", "text"], "Modality must be either 'audio' or 'text'."
        self.modality = modality

        if ai_customer_system_prompt is None:
            logging.warning("No AI customer system prompt provided. Using a default system prompt.")
            ai_customer_system_prompt = "You are a customer looking to buy an umbrella."

        if not ai_speaks_first and not customer_first_message:
            logging.warning("AI speaks first, but customer_first_message is not provided. Using a default message.")
            customer_first_message = "Does the car help me park?"

        if ai_speaks_first and customer_first_message:
            logging.warning("AI speaks first, but customer_first_message is provided. Ignoring customer_first_message.")

        self.base_url = base_url
        self.password = password

        self.token = None
        self.session_id = None
        self.cookies: SimpleCookie = None

        self.pyaudio = None
        self.pyaudio_stream = None

        self.async_openai_client = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        if audio_output_path is not None:
            self.audio_output_path = audio_output_path
        else:
            self.audio_output_path = "../temp/testing"

        assert os.path.exists(self.audio_output_path), f"Testing output path does not exist: {self.audio_output_path}"

        if modality == "audio" and play_audio:
            audio_config = AudioConfig()
            self.pyaudio = pyaudio.PyAudio()
            # Open an audio stream for PCM data
            self.pyaudio_stream = self.pyaudio.open(
                format=pyaudio.get_format_from_width(audio_config.sample_width),
                channels=audio_config.channels,
                rate=audio_config.sample_rate,
                output=True,
            )
            logging.info("Opened PyAudio stream")

        self.customer_ai = TestingAudioAgent(
            name="Customer",
            voice="shimmer",
            first_message=None if ai_speaks_first else customer_first_message,
            async_openai_client=async_openai_client,
            system_prompt=ai_customer_system_prompt,
            pyaudio_stream=self.pyaudio_stream,
            pre_chatstep_callback=None,
            post_chatstep_callback=None,
        )

        self.log_file = None
        self.log_filename = None

    def pre_chat_step(self, dialog):
        print(f"Pre chat step.")

    def post_chat_step(self, dialog):
        print(f"Post chat step.")

    def log(self, message: str):
        if self.log_file:
            self.log_file.write(message + "\n")
            self.log_file.flush()

    def __del__(self):
        if self.pyaudio is not None or self.pyaudio_stream is not None:
            logging.info("Closing PyAudio stream and terminating PyAudio...")
            if self.pyaudio_stream is not None:
                self.pyaudio_stream.stop_stream()
                self.pyaudio_stream.close()
            if self.pyaudio is not None:
                self.pyaudio.terminate()
        if hasattr(self, "log_file") and self.log_file is not None:
            self.log("Session ended.")
            self.log_file.close()
            self.log_file = None

    async def login(self):
        """
        Authenticate with the API and obtain JWT token
        """
        assert self.modality in ["audio", "text"], "Modality must be either 'audio' or 'text'."
        # Open log file with timestamped filename
        timestamp = time.strftime("%Y%m%d%H%M%S")
        self.log_filename = os.path.join(self.audio_output_path, f"{timestamp}_test_log.txt")
        self.log_file = open(self.log_filename, "w", encoding="utf-8")

        self.log(f"Attempting login at {timestamp}, modality: {self.modality}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/login/{self.modality}", json={"password": self.password}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.session_id = response.cookies.get("session_id").value
                    self.token = response.cookies.get("access_token").value
                    self.cookies = response.cookies
                    self.log(f"Login successful. Token: {self.token}")
                else:
                    self.log(f"Login failed with status {response.status}")
                    raise Exception(f"Login failed with status {response.status}")

    async def upload_audio(self, audio_file_path: str):
        """
        Upload audio file using HTTP POST

        Args:
            audio_file_path (str): Path to the audio file to upload
        """
        async with aiohttp.ClientSession(cookies=self.cookies) as session:
            async with aiofiles.open(audio_file_path, "rb") as f:
                file_data = await f.read()

            data = aiohttp.FormData()
            data.add_field("file", file_data, filename=os.path.basename(audio_file_path), content_type="audio/wav")

            async with session.post(f"{self.base_url}/receive_audio_blob", data=data) as response:
                result = await response.json()
                if response.status == 200:
                    pass
                else:
                    raise HttpError(
                        status_code=response.status,
                        message=f"Upload failed with status {response.status}: {result}",
                    )

    async def _send_text_chat_message(self, text: str):
        async with aiohttp.ClientSession(cookies=self.cookies) as session:
            async with session.post(
                f"{self.base_url}/respond", json={"type": "text_chat_response", "content": text}
            ) as response:
                result = await response.json()
                if response.status == 200:
                    pass
                else:
                    raise HttpError(
                        status_code=response.status,
                        message=f"Sending text chat message failed with status {response.status}: {result}",
                    )

    def _handle_server_message(self, str_data: str) -> tuple[bool, str]:
        """
        Handle non-audio server messages received from the websocket connection.

        Args:
            str_data (str): The string data received from the server. This is expected to be a JSON string.
                The function attempts to parse the string data as different types of server messages.
                If the message is an EndOfDialogStepMessage, it indicates the end of the audio stream.
        Returns:
            tuple[bool, str]: A tuple where the first element is a boolean indicating whether the dialog step has ended,
                and the second element is a string containing a text chunk of the server's chat response, if applicable.
                The text chunk is only returned if client and server are in text chat mode.
        """

        try:
            text_chunk_message = server_messages.TextChunkMessage.model_validate_json(str_data)
            return False, text_chunk_message.content
        except pydantic.ValidationError as e:
            pass

        try:
            eos_message = server_messages.EndOfDialogStepMessage.model_validate_json(str_data)
            return True, None
        except pydantic.ValidationError as e:
            pass

        self.log(f"Received server message: {str_data}")
        return False, None

    async def websocket_loop(self, max_conversation_steps: int | None = None):
        """
        The main loop for the websocket connection. This loop will, repeatedly:
        - Generate audio from the AI customer (saving it to a file and optionally playing it back), using the AudioChatAgent class.
        - Upload the audio to the server.
        - Receive audio from the server and save it to a file, optionally playing it back.
        - Transcribe the audio from the server and feed it back to the AI customer agent, so the dialog can be continued.
        """

        def get_audio_path(step: int, role: str) -> str:
            return os.path.join(
                self.audio_output_path,
                f"{session_timestamp}_{self.session_id}_{step}_{role}.wav",
            )

        url_without_protocol = self.base_url.split("//")[1]
        ws_url = f"ws://{url_without_protocol}/ws/audio/{self.session_id}"
        headers = {"Cookie": f"access_token={self.token}"}
        conversation_step = 0
        last_ai_messsage = None
        session_timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        ai_speaks_first = True

        async with websockets.connect(
            ws_url, additional_headers=headers, ping_interval=None, ping_timeout=None
        ) as websocket:
            while True:
                # skip first user message upload if the AI speaks first
                if not (ai_speaks_first and conversation_step == 0):
                    # generate an audio message from the AI customer
                    if self.modality == "audio":
                        customer_response_wav_file = get_audio_path(conversation_step * 2, "customer")
                        customer_response_text = await self.customer_ai.chat_step(
                            opponent_message=last_ai_messsage, audio_output_path=customer_response_wav_file, modality="audio"
                        )
                        self.log(f"Customer said: '{customer_response_text}'")
                        assert os.path.exists(
                            customer_response_wav_file
                        ), f"Customer audio file not found: {customer_response_wav_file}"
                        # upload the audio file to the server
                        await self.upload_audio(customer_response_wav_file)
                    elif self.modality == "text":
                        customer_response_text = await self.customer_ai.chat_step(
                            opponent_message=last_ai_messsage, audio_output_path=None, modality="text"
                        )
                        self.log(f"Customer said: '{customer_response_text}'")
                        await self._send_text_chat_message(text=customer_response_text)

                # retrieve server data...
                received_audio_chunks = []
                received_text_chunks = []

                while True:
                    try:
                        data = await asyncio.wait_for(websocket.recv(), timeout=60)
                        if isinstance(data, str):
                            # string data is expected to be a server message
                            dialog_step_ended, text_chunk = self._handle_server_message(data)
                            if text_chunk is not None:
                                received_text_chunks.append(text_chunk)
                            if dialog_step_ended:
                                break  # leave the loop if we get the stop signal
                        elif isinstance(data, bytes):
                            # binary data is expected to be audio data
                            received_audio_chunks.append(data)
                            if self.pyaudio_stream is not None:
                                self.pyaudio_stream.write(data)
                        else:
                            raise RuntimeError(f"Invalid data type received: {type(data)}")
                    except websockets.exceptions.ConnectionClosedOK as e:
                        logging.error(f"Connection closed with ConnectionClosedOK: {e}")
                        raise e
                    except websockets.exceptions.ConnectionClosedError as e:
                        logging.error(f"Connection closed with ConnectionClosedError: {e}")
                        raise e
                    except asyncio.TimeoutError as e:
                        logging.error("Timeout waiting for data from server")
                        raise e

                # did we get an audio response from the server?
                if len(received_audio_chunks) > 0:
                    server_audio_path = get_audio_path(conversation_step * 2 + 1, "ai")
                    test_helpers.save_audio_chunks_as_wav(
                        audio_output_path=server_audio_path,
                        chunks=received_audio_chunks,
                        config=AudioConfig(),
                    )
                    assert os.path.exists(server_audio_path), f"Audio file from server not found: {server_audio_path}"

                    last_ai_messsage = await test_helpers.speech_to_text(
                        input_audio_path=server_audio_path, async_openai_client=async_openai_client
                    )
                elif len(received_text_chunks) > 0:  # or did we get a text response from the server?
                    last_ai_messsage = "".join(received_text_chunks)
                else:
                    raise RuntimeError(
                        "No audio or text response received from the server. This should not happen if the server is working correctly."
                    )

                print(f"AI said: '{last_ai_messsage}'")
                logging.info(f"AI said: '{last_ai_messsage}'")

                conversation_step += 1
                if (max_conversation_steps is not None) and (conversation_step >= max_conversation_steps):
                    logging.info("Max conversation steps reached. Ending conversation.")
                    break


def create_client(
    ai_customer_system_prompt: str | None = None,
    play_audio: bool = False,
    ai_speaks_first: bool = True,
    customer_first_message: str = None,
    modality: Literal["audio", "text"] = "audio",
):
    """
    Create a client instance with the given parameters.
    """
    assert modality in ["audio", "text"], "Modality must be either 'audio' or 'text'."
    BASE_URL = os.getenv("LOCAL_API_ENDPOINT")
    PASSWORD = os.getenv("API_PASSWORD")
    client = Client(
        base_url=BASE_URL,
        password=PASSWORD,
        play_audio=play_audio,
        ai_customer_system_prompt=ai_customer_system_prompt,
        ai_speaks_first=ai_speaks_first,
        modality=modality,
        customer_first_message=customer_first_message,
    )
    return client


async def test_upload_without_login():
    """
    Test the API by sending a POST request to /receive_audio_blob without logging in.
    This should fail with a 403 status code."""
    client = create_client(play_audio=False)
    try:
        await client.upload_audio(AUDIO_UPLOAD_TEST_FILE)
    except HttpError as e:
        assert e.status_code == 403, f"Expected status 403, got {e.status_code}"
        logging.info(f"Upload failed as expected: {e}")


async def test_token_and_session_errors():
    """
    Test the API by sending a GET request to /test and messing with the tokens and session_id.
    All manipulations should return 403 status code.
    """
    client = create_client()
    await client.login()

    async def check_for_200():
        # this is the "good" case and should return 200
        async with aiohttp.ClientSession(cookies=client.cookies) as session:
            async with session.get(f"{client.base_url}/test") as response:
                assert response.status == 200, f"Expected status 200, got {response.status}"
                data = await response.json()
                logging.info(f"Test successful. Response: {data}")

    # test the "good" case
    await check_for_200()

    # break the token
    client.cookies["access_token"] = "this-is-a-broken-token"
    async with aiohttp.ClientSession(cookies=client.cookies) as session:
        async with session.get(f"{client.base_url}/test") as response:
            assert response.status == 403, f"Expected status 403, got {response.status}"
            data = await response.json()
            logging.info(f"Test successful. Response: {data}")

    # reset the token
    client.cookies["access_token"] = client.token
    await check_for_200()

    # break the session_id
    client.cookies["session_id"] = "this-is-a-bronken-session-id"
    async with aiohttp.ClientSession(cookies=client.cookies) as session:
        async with session.get(f"{client.base_url}/test") as response:
            assert response.status == 403, f"Expected status 403, got {response.status}"
            data = await response.json()
            logging.info(f"Test successful. Response: {data}")

    # reset the session_id
    client.cookies["session_id"] = client.session_id
    await check_for_200()


async def test_wrong_upload_order():
    """
    Test that uploading without connecting to the websocket fails.
    """
    client = create_client()
    try:
        await client.login()
        await client.upload_audio(AUDIO_UPLOAD_TEST_FILE)
    except HttpError as e:
        assert e.status_code == 412, f"Expected status 412, got {e.status_code}"
        logging.info(f"Upload failed as expected: {e}")


async def test_websocket_connect_without_login():
    """
    Test the websocket connection without logging in.
    """
    client = create_client()
    try:
        await client.websocket_loop()
    except InvalidStatus as e:
        assert e.response.status_code == 500, f"Expected status 500, got {e.response.status_code}"
        logging.info(f"Websocket connection failed as expected without login. Error: {e.response}")


async def test_conversation(
    ai_customer_system_prompt: str, modality: Literal["audio", "text"] = "audio", play_audio: bool = False
):
    """
    Test the conversation with the AI customer agent.
    """
    assert modality in ["audio", "text"], "Modality must be either 'audio' or 'text'."
    if modality == "text" and play_audio:
        logging.warning("Audio playback is not supported in text chat mode. Disabling audio playback.")
        play_audio = False
    client = create_client(
        ai_customer_system_prompt=ai_customer_system_prompt, play_audio=play_audio, modality=modality
    )
    await client.login()
    await client.websocket_loop(max_conversation_steps=8)


async def main(play_audio: bool):
    await test_conversation(play_audio=play_audio)

    await test_upload_without_login()
    await test_wrong_upload_order()
    await test_token_and_session_errors()
    await test_websocket_connect_without_login()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Run the client with optional audio playback.")
    parser.add_argument("--play", action="store_true", help="Enable audio playback", default=False)
    args = parser.parse_args()

    if args.play:
        logging.info("Audio playback enabled")

    asyncio.run(main(play_audio=args.play))
