import logging
import os
import wave

import openai
import pyaudio
from dotenv import load_dotenv

from nevo_framework.config.audio_config import AudioConfig

load_dotenv()


async def text_to_speech(
    text: str,
    async_openai_client: openai.AsyncOpenAI,
    voice: str = "onyx",
    config: AudioConfig = AudioConfig(),
    pyaudio_stream: pyaudio.Stream | None = None,
    audio_output_path: str = None,
):
    """
    Generate audio from text using OpenAI's text-to-speech API.
    The audio will always be saved to a file. If pyaudio_stream is provided, the audio will be played back in real-time.

    Args:
        text (str): The text to convert to audio.
        async_openai_client (openai.AsyncOpenAI): OpenAI client for making asynchronous requests.
        voice (str): The voice to use for the text-to-speech conversion.
        config (AudioConfig): Configuration for the audio.
        pyaudio_stream (pyaudio.Stream): PyAudio stream to play the audio. If provided, the audio will be played back in real-time.
            Otherwise, the audio will be saved to a file.
        audio_output_path (str): Path to save the audio file. If None, the audio will not be saved to a file.
    """
    received_audio_chunks = []

    async with async_openai_client.with_streaming_response.audio.speech.create(
        model="tts-1", voice=voice, input=text, response_format="wav"
    ) as response:
        async for chunk in response.iter_bytes(1024):
            if pyaudio_stream and pyaudio_stream.is_active():
                pyaudio_stream.write(chunk)
            received_audio_chunks.append(chunk)

    if audio_output_path is not None:
        os.makedirs(os.path.dirname("src/testing/audio_output/"), exist_ok=True)
        save_audio_chunks_as_wav(audio_output_path=audio_output_path, chunks=received_audio_chunks, config=config)


def save_audio_chunks_as_wav(audio_output_path: str, chunks: list, config: AudioConfig):
    """
    Save audio chunks as a WAV file.

    Args:
        audio_output_path (str): Path to save the audio file.
        chunks (list): List of audio chunks to save. This is exepcted to be a list of byte chunks as returned, for example,
            by audio streaming APIs.
        config (AudioConfig): Description of the audio format.
    """
    assert os.path.exists(os.path.dirname(audio_output_path)), f"Output directory does not exist: {audio_output_path}"
    audio_data = b"".join(chunks)
    with wave.open(audio_output_path, "wb") as wav_file:
        wav_file.setnchannels(config.channels)
        wav_file.setsampwidth(config.sample_width)
        wav_file.setframerate(config.sample_rate)
        wav_file.writeframes(audio_data)
        logging.info(f"Saved audio to {audio_output_path}")


async def speech_to_text(input_audio_path: str, async_openai_client: openai.AsyncOpenAI) -> str:
    """
    Transcribe audio from a file using OpenAI's speech-to-text API.

    Args:
        input_audio_path (str): Path to the audio file to transcribe.
        async_openai_client (openai.AsyncOpenAI): OpenAI client for making asynchronous requests.

    Returns:
        str: The transcribed text.
    """
    with open(input_audio_path, "rb") as audio_file:
        transcript = await async_openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text",
            timeout=10.0,
        )
    return transcript
