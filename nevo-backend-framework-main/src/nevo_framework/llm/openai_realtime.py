import asyncio
import base64
import json
import logging
import os
import time

import websockets
import websockets.asyncio.connection as websockets_connection
from starlette import websockets as starlette_websockets

from nevo_framework.api.server_messages import AiStatusMessage, TranscribedAudio, TranscriptionCompletedMessage
from nevo_framework.config.audio_config import AudioConfig
from nevo_framework.llm.agents import save_audio_chunks_as_wav


async def _stream_client_audio(
    websocket_to_transcriber: websockets_connection.Connection,
    websocket_from_client: starlette_websockets.WebSocket,
    save_audio_sample: bool = False,
):
    """
    Stream audio data that arrives at the websocket_from_client to the real-time transcription service
    via the websocket_to_transcriber. Optionally save a sample of the audio data to validate the audio settings.

    Args:
        websocket_to_transcriber: The websocket connection to the OpenAI real-time transcription service.
        websocket_from_client: The websocket connection from the client.
        save_audio_sample: If True, save a sample of the audio data to a WAV file for validation. Saves the data every 20 chunks.
    """
    logging.info("Starting audio streaming to OpenAI server...")

    if save_audio_sample:
        audio_chunks = []

    while True:
        try:
            data = await asyncio.wait_for(websocket_from_client.receive_bytes(), timeout=5 * 60)
            audio_b64 = base64.b64encode(data).decode("utf-8")
            message = {"type": "input_audio_buffer.append", "audio": audio_b64}
            await websocket_to_transcriber.send(json.dumps(message))

            if save_audio_sample:
                audio_chunks.append(data)
                if len(audio_chunks) > 0 and len(audio_chunks) % 20 == 0:
                    # save audio data as WAV to validate it
                    logging.info(f"Received {len(audio_chunks)} audio chunks, saving.")
                    # Save the audio chunks to a PCM16 wave file
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    audio_output_path = f"voice_ai_src/test/audio_output/streamed_audio_{timestamp}_{16000}.wav"
                    save_audio_chunks_as_wav(
                        audio_output_path=audio_output_path,
                        chunks=audio_chunks,
                        config=AudioConfig(sample_rate=16000, channels=1, sample_width=2),
                    )
        except asyncio.CancelledError:
            logging.info("websocket_from_client: Task cancelled.")
            raise
        except asyncio.TimeoutError:
            logging.error("websocket_from_client: Timeout while receiving data.")
            raise
        except websockets.ConnectionClosed:
            logging.error("websocket_from_client: Connection closed.")
            raise
        except Exception as e:
            logging.error(f"Error in _stream_client_audio: {type(e).__name__}, {e}")
            raise


async def _setup_transcriber(websocket_to_transcriber: websockets_connection.Connection) -> bool:
    """
    Set up the transcriber by connecting to the OpenAI real-time transcription service.
    This function handles the connection, session creation, and session configuration.
    """
    data = await websocket_to_transcriber.recv()
    message = json.loads(data)
    # Check if the connection was successful and a session was created
    if message.get("type") == "transcription_session.created":
        session = message.get("session")
        logging.info(f"Connected to real-time transcription service and session created: {session}")

        # Now we can update the session with the desired model and language and other parameters
        session_update = {
            "input_audio_transcription": {"model": "gpt-4o-mini-transcribe", "prompt": "", "language": "en"}
        }
        await websocket_to_transcriber.send(
            json.dumps({"type": "transcription_session.update", "session": session_update})
        )

        # Wait for the session update confirmation
        data = await websocket_to_transcriber.recv()
        message = json.loads(data)
        if message.get("type") == "transcription_session.updated":
            logging.info(f"Transcriber: Session updated successfully: {message}")
            return True
        else:
            logging.error(f"Transcriber: Error updating transcription session: {message}")
            return False
    else:
        logging.error(f"Transcriber: Error creating transcription session: {message}")
        return False


async def realtime_transcription(
    websocket_from_client: starlette_websockets.WebSocket,
    client_input_queue: asyncio.Queue,
    client_output_queue: asyncio.Queue,
):
    """
    Connect to the real-time transcription service.
    """

    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

    url = "wss://api.openai.com/v1/realtime?intent=transcription"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "OpenAI-Beta": "realtime=v1"}

    async with websockets.connect(url, additional_headers=headers) as websocket_to_transcriber:
        # Set up the transcriber
        logging.info("Setting up the transcriber...")
        setup_success = await _setup_transcriber(websocket_to_transcriber)
        if not setup_success:
            logging.error("Failed to set up the transcriber.")
            return

        # Now we launch the audio streaming task that sends audio data to the OpenAI server
        audio_upstream_task = asyncio.create_task(_stream_client_audio(websocket_to_transcriber, websocket_from_client))

        # ... and start receiving messages from the transcriber
        try:
            while True:
                data = await asyncio.wait_for(websocket_to_transcriber.recv(), timeout=5 * 60)
                message = json.loads(data)
                if message["type"] == "conversation.item.input_audio_transcription.delta":
                    # Incremental transcription updates
                    pass
                elif message["type"] == "conversation.item.input_audio_transcription.completed":
                    # Full transcription of a speech segment
                    transcription = message["transcript"]
                    logging.info(f"Transcriber: Transcription completed: {transcription}")
                    client_output_queue.put_nowait(TranscriptionCompletedMessage(content=transcription))
                    client_input_queue.put_nowait(TranscribedAudio(content=transcription))
                    client_output_queue.put_nowait(AiStatusMessage(message=f"User said: {transcription}"))
                elif message["type"] == "input_audio_buffer.speech_started":
                    logging.info("Transcriber: speech_started Detected")
                elif message["type"] == "input_audio_buffer.speech_stopped":
                    logging.info("Transcriber: speech_stopped Detected")
                else:
                    logging.info(f"Transcriber: Unknown message type from transcriber: {message['type']}")
                # Add more event handling for other types as needed
                # (e.g., for `response.audio.delta` if you are expecting audio responses)
        except TimeoutError:
            logging.error("websocket_to_transcriber: Timeout while receiving data.")
            return
        except websockets.ConnectionClosed:
            logging.error("websocket_to_transcriber: Connection closed.")
            return
        finally:
            # Ensure the upstream task is cancelled when done
            audio_upstream_task.cancel()
            await audio_upstream_task
            await websocket_to_transcriber.close()
