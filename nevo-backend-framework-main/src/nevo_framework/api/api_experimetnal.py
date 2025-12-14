import argparse
import asyncio
import datetime
import logging
import os
import uuid
from contextlib import asynccontextmanager

import bcrypt  # Use bcrypt for password hashing
import jwt
import pydantic
from dotenv import load_dotenv
from fastapi import (
    Body,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Path,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

import nevo_framework.api.api_helpers as api_helpers
import nevo_framework.api.server_messages as server_messages
import nevo_framework.playground.datamodel as datamodel
import nevo_framework.playground.prompt_repo as prompt_repository
from nevo_framework.api.server_messages import AudioUploadReady, TranscribedAudio, WebElementMessage
from nevo_framework.api.sessions import SessionState, get_session_state, session_cleanup, store_session_state
from nevo_framework.config.master_config import get_master_config
from nevo_framework.helpers.logging_helpers import DIALOG_STEP_ENDED, LogAi, LogTiming, TimingLogger
from nevo_framework.llm import llm_tools
from nevo_framework.llm.dialog_manager_experimental import DialogManager
from nevo_framework.llm.openai_realtime import realtime_transcription

CONFIG = get_master_config()
parser = argparse.ArgumentParser(description="Start the API server.")

QUEUE_TIMEOUT__OUTPUT_DATA = 2 * 60

# hashed password generated using bcrypt
stored_hashed_password = os.getenv("HASHED_PASSWORD").encode("utf-8")


load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # set up the AI logger, which does not work via the logging ini file
    api_helpers.setup_ai_logging()

    # Load the prompt repository from a file and make it available globally in the app state.
    if CONFIG.prompt_repo_path:
        prompt_repo = prompt_repository.PromptRepo()
        try:
            prompt_repo.load_from_file(CONFIG.prompt_repo_path)
            logging.info(f"Prompt repository loaded from {CONFIG.prompt_repo_path}.")
        except Exception as e:
            logging.error(
                f"Failed to load prompt repository from {CONFIG.prompt_repo_path}: {e}. Initializing to default."
            )
            # prompt_repo.init_to_default()
            # prompt_repo.save_to_file(CONFIG.prompt_repo_path)
            prompt_repo = None
        finally:
            app.state.prompt_repo = prompt_repo
    else:
        app.state.prompt_repo = None
        logging.warning("Prompt repository path not set. No prompt repository loaded.")

    # Start the session cleanup task
    asyncio.create_task(session_cleanup())

    # Run the app.
    yield

    if hasattr(app.state, "prompt_repo"):
        if CONFIG.prompt_repo_path is None:
            logging.warning("Prompt repository path not set. Prompt repository not saved.")
            return
        else:
            # Save the prompt repository to a file when the app shuts down
            try:
                if os.path.exists(CONFIG.prompt_repo_path):
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    base, ext = os.path.splitext(CONFIG.prompt_repo_path)
                    backup_path = f"{base}_{timestamp}_backup{ext}"
                    try:
                        os.rename(CONFIG.prompt_repo_path, backup_path)
                        logging.info(f"Backup of prompt repository created at {backup_path}.")
                    except Exception as e:
                        logging.error(f"Failed to create backup of prompt repository: {e}")
                app.state.prompt_repo.save_to_file(CONFIG.prompt_repo_path)
                logging.info(f"Prompt repository saved to {CONFIG.prompt_repo_path}.")
            except Exception as e:
                logging.error(f"Failed to save prompt repository: {e}")


enable_docs = True  # os.getenv("ENABLE_DOCS", "false").lower() == "true"
app = FastAPI(docs_url="/readme_images" if enable_docs else None, redoc_url=None, lifespan=lifespan)

# Configure CORS if frontend is on a different domain or port
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https:\/\/skodabot-react-frontend-[\w\d]+\.francecentral-01\.azurewebsites\.net$|^http:\/\/localhost(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_prompt_repo() -> prompt_repository.PromptRepo:
    """
    Helper to retrieve the prompt repository from the app state.
    """
    if hasattr(app.state, "prompt_repo") and app.state.prompt_repo is not None:
        return app.state.prompt_repo
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prompt repository not available.",
        )


@app.middleware("http")
async def track_session_last_activity(request: Request, call_next):
    """
    This middleware function tracks the last activity time of a session.
    """
    if session_id := request.cookies.get("session_id"):
        if session_state := get_session_state(session_id):
            session_state.set_was_active()
            logging.debug(f"Session activity tracker: Session {session_id} was active at {session_state.last_activity}")
        else:
            logging.warning(f"Session activity tracker: Session not found for session: {session_id}")
    else:
        logging.warning(f"Session ID not found in cookies: {request.cookies}")
    response = await call_next(request)
    return response


@app.post("/login")
async def login(request: Request, response: Response, password: str = Body(..., embed=True)):
    """
    Login endpoint. Verifies the password and returns a JWT token and session ID.
    Creates the session state for the user.
    """
    if bcrypt.checkpw(password.encode("utf-8"), stored_hashed_password):
        expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        token = jwt.encode({"exp": expiration}, api_helpers.JWT_SECRET_KEY, algorithm=api_helpers.ALGORITHM)
        session_id = str(uuid.uuid4())
        # Set JWT and session ID as HTTP-only, secure cookies
        response.set_cookie(key="access_token", value=token, httponly=True, secure=False, samesite="lax")
        response.set_cookie(key="session_id", value=session_id, httponly=True, secure=False, samesite="lax")
        input_queue = asyncio.Queue()
        output_queue = asyncio.Queue()

        # If we have a prompt repository in the app state, pass a reference to it to the dialog manager.
        # This is for AI systems that depend on user editable prompts, which are accessible via the prompt repository.
        prompt_repo = (
            app.state.prompt_repo if (hasattr(app.state, "prompt_repo") and app.state.prompt_repo is not None) else None
        )
        dialog_manager = DialogManager(output_queue=output_queue, prompt_repo=prompt_repo)

        store_session_state(
            SessionState(
                id=session_id,
                dialog_manager=dialog_manager,
                input_queue=input_queue,
                output_queue=output_queue,
            )
        )
        logging.info(f"Login successful. New session created with ID {session_id}")
        return {"message": "Logged in", "token": token, "session_id": session_id}
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")


@app.post("/respond")
async def web_element_respond(
    token: dict = Depends(api_helpers.get_and_check_token_from_cookies),
    session_state: SessionState = Depends(api_helpers.get_session_state_from_cookies),
    payload: dict = Body(...),
):
    if not session_state.accept_client_data:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Client messages not allowed before websocket connection or during processing of a dialog step.",
        )
    if msg_type := payload.get("type"):
        logging.info(f"web_element_respond endpoint received valid payload: {payload}")
        session_state.input_queue.put_nowait(WebElementMessage(message_type=msg_type, message_dict=payload))
        return {"message": "ok"}
    else:
        logging.error("web_element_respond route received payload without 'type' key.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload missing 'type' key.")


@app.websocket("/ws/realtime/{session_id}")
async def websocket_realtime(
    websocket: WebSocket,
    session_id: str,
    token: dict = Depends(api_helpers.get_and_check_token_from_cookies_ws),
):
    session_state = get_session_state(session_id)
    await websocket.accept()
    realtime_transcription_task = asyncio.create_task(
        realtime_transcription(websocket_from_client=websocket, client_input_queue=session_state.input_queue)
    )
    try:
        while True:
            message = await session_state.input_queue.get()
            logging.info(f"Received message from session {session_id}: {message}")
            if isinstance(message, server_messages.AiStatusMessage):
                await api_helpers.send_pydantic(websocket, message)
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected for session {session_id} (WebSocketDisconnect exception)")
    except asyncio.TimeoutError:
        logging.info(f"Timeout while waiting for session {session_id}")
    finally:
        realtime_transcription_task.cancel()
        await realtime_transcription_task


@app.websocket("/ws/audio/{session_id}")
async def websocket_audio_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: dict = Depends(api_helpers.get_and_check_token_from_cookies_ws),
):
    """
    Websocket endpoint for streaming audio and other messages to the client.
    """
    ai_speaks_first = CONFIG.ai_speaks_first
    session_state = get_session_state(session_id)
    assert session_state.id == session_id, "Session ID must match the session state."

    if session_state is None:
        # this could be more elegant, but we need to check if the session is still active
        logging.warning(f"Websocket wanted to connect but session not found for the given ID: {session_id} Timed out?")
        try:
            await websocket.close()
        except Exception as e:
            pass  # ignore, we are closing the connection anyway
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session not found for the given ID.")

    if session_state.websocket is not None:
        logging.warning(f"Websocket already connected for session {session_id}. Closing the old connection.")
        try:
            await session_state.websocket.close()
        except Exception as e:
            pass

    realtime_transcription_task = None

    try:
        await websocket.accept()
        logging.info(f"WebSocket connection established. Session ID: {session_id}")
        session_state.websocket = websocket

        if ai_speaks_first:
            # if AI speaks first, we start with an AI dialog step
            logging.info(LogAi("AI speaks first."))
            await handle_dialog_step(
                websocket=websocket,
                session_state=session_state,
            )

        # only after the client connects to the websocket and the AI has spoke (if applicable) we start accepting client data
        session_state.accept_client_data = True

        if CONFIG.has_debug_flag("realtime"):
            logging.info("Debug flag 'realtime' is set, starting real-time transcription.")
            realtime_transcription_task = asyncio.create_task(
                realtime_transcription(
                    websocket_from_client=websocket,
                    client_input_queue=session_state.input_queue,
                    client_output_queue=session_state.output_queue,
                )
            )

        while True:

            # wait for a message from the frontend, sent to the input queue from one of the endpoints
            logging.info(f"Waiting for input for session {session_id}")
            message_from_client = await asyncio.wait_for(
                session_state.input_queue.get(), CONFIG.timeout_wait_for_frontend_message
            )
            # do not accept more data while the server is processing
            session_state.accept_client_data = False

            # Do we have a recording file?
            if isinstance(message_from_client, AudioUploadReady):
                raise DeprecationWarning("AudioUploadReady is deprecated, use transcribed_user_message instead.")
                logging.info(f"Recording file ready for session {session_id}: {message_from_client.audio_file_path}")
                await handle_dialog_step(
                    websocket=websocket,
                    session_state=session_state,
                    recording_file_path=message_from_client.audio_file_path,
                )
                # delete the audio recording file after processing
                try:
                    os.remove(message_from_client.audio_file_path)
                    logging.info(f"Deleted recording file: {message_from_client.audio_file_path}")
                except Exception as e:
                    logging.error(f"Failed to delete recording file {message_from_client.audio_file_path}: {e}")

            elif isinstance(message_from_client, TranscribedAudio):
                logging.info(f"Handling transcribed audio for session {session_id}: {message_from_client}")
                await handle_dialog_step(
                    websocket=websocket,
                    session_state=session_state,
                    transcribed_user_message=message_from_client.content,
                )

            # Do we have a web element message? (non audio frontend message)
            elif isinstance(message_from_client, WebElementMessage):
                logging.info(f"Handling web element message for session {session_id}: {message_from_client}")
                await handle_dialog_step(
                    websocket=websocket,
                    session_state=session_state,
                    web_element_message=message_from_client.message_dict,
                )
            else:
                logging.error(f"Unexpected frontend message type: {message_from_client}")
            session_state.accept_client_data = True
    except asyncio.TimeoutError:
        logging.info(f"Timeout while waiting for recording file for session {session_id}")
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected for session {session_id} (WebSocketDisconnect exception)")
    finally:
        logging.info(f"Marking session {session_id} for removal.")
        session_state.accept_client_data = False
        # mark the session for removal
        session_state.kill_session = True
        if realtime_transcription_task is not None:
            realtime_transcription_task.cancel()
            await realtime_transcription_task


async def handle_dialog_step(
    websocket: WebSocket,
    session_state: SessionState,
    recording_file_path: str | None = None,
    web_element_message: dict | None = None,
    transcribed_user_message: str | None = None,
):
    """
    Initiate an "audio chat cycle":
    * Transcribe uploaded audio recording, when notfied by the filename of the uploaded audio being available on the queue.
    * Generate a response using the AI.
    * Convert the response to speech and stream it back to the client.
    * Stream any other messages to the client such as show image messages.

    Args:
        websocket (WebSocket): WebSocket connection.
        recording_file_path (str): Path to the uploaded audio recording.
        dialog_manager (AgentOrchestrator): The dialog manager that handles the AI processing.
    """
    assert session_state.dialog_manager is not None

    # this is the task to handle the dialog step
    async def streaming_ai_tasks():
        audio_response_task = asyncio.create_task(
            session_state.dialog_manager.dialog_step(
                recording_file_path=recording_file_path,
                web_element_message=web_element_message,
                transcribed_user_message=transcribed_user_message,
            )
        )
        await asyncio.gather(audio_response_task)

    try:
        ai_task = asyncio.create_task(streaming_ai_tasks())
        sent_audio = False  # this is for timing the first audio chunk
        # wait for data created by the streaming dialog step chain
        while True:
            data = await asyncio.wait_for(
                session_state.dialog_manager.get_output_queue().get(), timeout=QUEUE_TIMEOUT__OUTPUT_DATA
            )
            # important to keep the session alive when the AI is streaming long answers
            session_state.set_was_active()
            if data == DIALOG_STEP_ENDED:
                # If we are at the end of the dialog step we indicate this to the client and break the loop.
                logging.info(f"handle_dialog_step: received DIALOG_STEP_ENDED signal for session {session_state.id}")
                logging.info(LogTiming("api:received_dialog_step_end"))
                await api_helpers.send_pydantic(websocket, server_messages.EndOfDialogStepMessage())
                sent_audio = False
                break
            elif isinstance(data, bytes):
                # if we have audio data, send it to the client
                await websocket.send_bytes(data)
                if not sent_audio:
                    logging.info(LogTiming("api:sent_first_audio_chunk"))
                    sent_audio = True
            elif isinstance(data, pydantic.BaseModel):
                # If we have a Pydantic class we assume its a web element message and we send it to the client right away.
                if hasattr(data, "type"):
                    await api_helpers.send_pydantic(websocket, data)
                else:
                    logging.error(
                        f"streaming_dialogue_step: Message not sent as messages to the client MUST have a 'type' attribute (session: {session_state.id}, invalid message: {data})"
                    )
            else:
                logging.error(
                    f"streaming_dialogue_step: Unexpected data in output stream for session {session_state.id}: {data}"
                )
                raise RuntimeError(f"Unexpected data in output stream: {data}")
    except asyncio.TimeoutError:
        logging.error(
            f"streaming_dialogue_step: TimeoutError on waiting for audio chunks for session {session_state.id}"
        )
        await api_helpers.send_pydantic(
            websocket, server_messages.EndOfDialogStepMessage(server_error="Timeout waiting for audio chunks.")
        )
    finally:
        ai_task.cancel()
        await ai_task


@app.post("/receive_audio_blob")
async def recieve_audio_blob(
    file: UploadFile = File(...),
    token: dict = Depends(api_helpers.get_and_check_token_from_cookies),
    session_state: SessionState = Depends(api_helpers.get_session_state_from_cookies),
):
    """
    Endpoint for uploading audio files with the user's voice.
    """
    if not session_state.accept_client_data:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Audio upload not allowed before websocket connection or during processing of a dialog step.",
        )
    try:
        os.makedirs(CONFIG.recording_file_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        recording_file_path = os.path.join(CONFIG.recording_file_dir, f"audio-input_{session_state.id}_{timestamp}.wav")
        with open(recording_file_path, "wb") as f:
            contents = await file.read()
            f.write(contents)
        logging.info(f"Audio received and saved to {recording_file_path} (session ID: {session_state.id}).")

        with TimingLogger("DialogManager:dialog_step:transcribe"):
            transcribed_user_message = await llm_tools.transcribe_recording(recording_file_path)

        session_state.input_queue.put_nowait(TranscribedAudio(content=transcribed_user_message))
        # session_state.input_queue.put_nowait(AudioUploadReady(audio_file_path=recording_file_path))
        return {"success": True}
    except Exception as e:
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Audio upload failed.")


@app.get("/stop")
async def stop(
    token: dict = Depends(api_helpers.get_and_check_token_from_cookies),
    session_state: SessionState = Depends(api_helpers.get_session_state_from_cookies),
):
    """
    Endpoint to stop the AI and close the session.
    """
    session_state.kill_session = True
    logging.info(f"Session {session_state.id} marked for removal.")
    return {"message": "Session closed."}


@app.get("/test")
async def test(
    token: dict = Depends(api_helpers.get_and_check_token_from_cookies),
    session_state: SessionState = Depends(api_helpers.get_session_state_from_cookies),
):
    """
    Simple endpoint for testing the API.
    """
    return {"message": f"Test successful, token first 3 chars: {token[:3]}, session ID: {session_state.id}"}


def _validate_species(ai_species: str, session_state: SessionState) -> bool:
    """
    Validate the AI species. Raises an HTTPException if the species does not match the session state.
    """
    if session_state.get_ai_species() != ai_species:
        logging.error(
            f"Session species '{session_state.get_ai_species()}' does not match requested species '{ai_species}'."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session species '{session_state.get_ai_species()}' does not match requested species '{ai_species}'.",
        )


@app.get("/playground/{ai_species}/prompt_list")
async def prompt_list(
    ai_species: str,
    prompt_repo: prompt_repository.PromptRepo = Depends(get_prompt_repo),
    token: dict = Depends(api_helpers.get_and_check_token_from_cookies),
    session_state: SessionState = Depends(api_helpers.get_session_state_from_cookies),
) -> datamodel.PromptList:
    """
    Endpoint to list all available prompts for a specific AI species.
    """
    _validate_species(ai_species, session_state)
    return prompt_repo.get_prompt_list(ai_species)


@app.get("/playground/{ai_species}/prompt/{prompt_name}")
async def get_prompt(
    ai_species: str = Path(..., description="The AI species."),
    prompt_name: str = Path(..., description="The name of the prompt to retrieve."),
    prompt_repo: prompt_repository.PromptRepo = Depends(get_prompt_repo),
    token: dict = Depends(api_helpers.get_and_check_token_from_cookies),
    session_state: SessionState = Depends(api_helpers.get_session_state_from_cookies),
):
    """
    Endpoint to get a specific prompt by name, for a specific AI species.
    """
    _validate_species(ai_species, session_state)
    if result := prompt_repo.get_prompt(ai_species, prompt_name):
        return result
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Prompt with name {prompt_name} for AI species {ai_species} not found.",
    )


@app.post("/playground/{ai_species}/prompt/update", status_code=status.HTTP_201_CREATED)
async def update_prompt(
    ai_species: str = Path(..., description="The AI species."),
    prompt: datamodel.Prompt = Body(...),
    prompt_repo: prompt_repository.PromptRepo = Depends(get_prompt_repo),
    token: dict = Depends(api_helpers.get_and_check_token_from_cookies),
    session_state: SessionState = Depends(api_helpers.get_session_state_from_cookies),
):
    """
    Endpoint to update the prompt `prompt_name` for the AI species `ai_species`.
    """
    _validate_species(ai_species, session_state)
    # Here you would set the prompt in the session state or wherever it needs to be stored
    try:
        prompt_repo.update_prompt(prompt)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update prompt: {e}",
        )


@app.post("/playground/{ai_species}/restart")
async def restart(
    ai_species: str,
    prompt_name: str | None,
    token: dict = Depends(api_helpers.get_and_check_token_from_cookies),
    session_state: SessionState = Depends(api_helpers.get_session_state_from_cookies),
):
    """
    Endpoint to restart the AI for the AI species `ai_species`.
    """
    _validate_species(ai_species, session_state)
    session_state.dialog_manager.reset_dialog(prompt_name=prompt_name)
    logging.info(LogAi(f"Session {session_state.id} restarted with prompt '{prompt_name}'"))
    return {"message": "Session restarted."}


@app.get("/playground/download")
async def download_prompt_repo(
    prompt_repo: prompt_repository.PromptRepo = Depends(get_prompt_repo),
    token: dict = Depends(api_helpers.get_and_check_token_from_cookies),
):
    """
    Endpoint to download the entire prompt repository as a JSON file. User must be logged in.
    """
    json_data = prompt_repo.get_as_json()
    return Response(
        content=json_data,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=prompt_repo.json"},
    )


if __name__ == "__main__":
    import argparse

    import uvicorn

    # python -m voice_ai_src.api.api_v2 --reload
    logging.warning("RUNNING API VERSION 3!")

    local_endpoint = os.getenv("LOCAL_API_ENDPOINT")
    if local_endpoint is None:
        port = 8000
    else:
        port = local_endpoint.split(":")[-1]
        assert port.isdigit(), "Port number must be an integer"
        port = int(port)
    logging.info(f"Starting API server on port {port}.")

    DEBUG_FLAGS = ["recommendation", "record"]

    parser = argparse.ArgumentParser(description="Start the API server.")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for the server.")
    parser.add_argument(
        "--debug",
        type=str,
        help=f"Set debug flags, comma separated without spaces. Supported flags: {', '.join(DEBUG_FLAGS)}",
    )
    parser.add_argument(
        "--log_chatsteps",
        action="store_true",
        help="Log token use, AI transcript, length of speech, ... to JSON files.",
    )
    parser.add_argument("--realtime", action="store_true", help="Use real-time transcription for audio input.")
    parser.add_argument("--store_audio", action="store_true", help="Store AI audio to disk.")
    parser.add_argument("--ai", type=str, default="audi")
    args = parser.parse_args()
    if args.reload:
        logging.warning("Uvicorn auto-reload enabled!")
    else:
        logging.info("Uvicorn auto-reload disabled.")

    debug_flags = ""
    if args.debug:
        flags = args.debug.strip().split(",")
        assert all(flag in DEBUG_FLAGS for flag in flags), f"Invalid debug flags: {args.debug}"
        logging.warning(f"Debug flags set: {args.debug}")
        debug_flags = args.debug
    if args.store_audio:
        debug_flags += ",store_audio"
        logging.warning("Debug flag 'store_audio' set: AI audio will be stored to disk.")
    if args.log_chatsteps:
        debug_flags += ",log_chatsteps"
        logging.warning("Debug flag 'log_chatsteps' set: Details of chat steps will be logged to JSON.")
    if args.ai:
        debug_flags += f",ai={args.ai}"
        logging.warning(f"Debug flag 'ai' set: AI type is '{args.ai}'.")
    if args.realtime:
        debug_flags += ",realtime"
        logging.warning("Debug flag 'realtime' set: Real-time transcription will be used.")

    os.environ["API_DEBUG"] = debug_flags

    uvicorn.run(
        "src.api.api_v3:app",
        host="0.0.0.0",
        port=port,
        reload=args.reload,
        log_config="config/log-server.ini",
    )
