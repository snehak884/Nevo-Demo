import argparse
import asyncio
import datetime
import logging
import logging.handlers
import os
import re
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

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
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocketState

import nevo_framework.api.api_helpers as api_helpers
import nevo_framework.api.server_messages as server_messages
from nevo_framework.api.server_messages import AudioUploadReady, WebElementMessage
from nevo_framework.api.sessions import SessionState, get_session_state, session_cleanup, store_session_state
from nevo_framework.config.master_config import get_master_config
from nevo_framework.helpers.logging_helpers import DIALOG_STEP_ENDED, LogAi
from nevo_framework.llm.dialog_manager import DialogManager

QUEUE_TIMEOUT__OUTPUT_DATA = 2 * 60

CONFIG = get_master_config()
parser = argparse.ArgumentParser(description="Start the API server.")


# Define the custom filter
class AILogFilter(logging.Filter):
    def filter(self, record):
        return record.getMessage().startswith("<<<AI>>>")


# hashed password generated using bcrypt
# If HASHED_PASSWORD is not set or invalid, use fixed hash for password "test123" (matches local setup)
# This hash is from LOCAL_SETUP_GUIDE.md - DO NOT regenerate, use this exact hash
FIXED_HASH_FOR_TEST123 = "$2b$12$hJOKAOiDvFGQFmOT6EYO7e2DP5/icdPGqydXRyp5SNeP93eu0LQdi"
hashed_pw = os.getenv("HASHED_PASSWORD")
if not hashed_pw or len(hashed_pw) < 60:
    # Use fixed hash so it's consistent across restarts (matches local setup)
    hashed_pw = FIXED_HASH_FOR_TEST123
    logging.warning("HASHED_PASSWORD not set or invalid. Using fixed hash for password 'test123' (development only)")
stored_hashed_password = hashed_pw.encode("utf-8")


load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):

    api_helpers.setup_ai_logging()

    # Start the session cleanup task
    asyncio.create_task(session_cleanup())
    yield


enable_docs = os.getenv("ENABLE_DOCS", "false").lower() == "true"
app = FastAPI(docs_url="/readme_images" if enable_docs else None, redoc_url=None, lifespan=lifespan)

# Configure CORS if frontend is on a different domain or port
# Use explicit origins when credentials are enabled (required for CORS with credentials)
# When allow_credentials=True, browsers reject wildcard '*' - must use specific origins
allowed_origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:8000",
    "https://nevo-audi-frontend-dev.azurewebsites.net",
    "https://nevo-audi-backend-dev.azurewebsites.net",
]

# Use explicit origins list (required when allow_credentials=True)
# This prevents CORS from returning wildcard '*' which browsers reject with credentials
if allowed_origins:
    logging.info(f"CORS: Using explicit origins: {allowed_origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", "Authorization", "X-Session-ID", "Content-Type"],  # Explicitly allow custom headers
        expose_headers=["*"],  # Expose all headers to frontend
    )
else:
    logging.warning(f"CORS: No explicit origins found, falling back to regex: {CONFIG.cors_regex}")
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=CONFIG.cors_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Mount static files directory for serving images
# This allows the backend to serve images from the frontend's public directory or backend static directory
# Try frontend public folder first (common location), then backend static folder
from pathlib import Path
framework_dir = Path(__file__).resolve().parent.parent.parent.parent
workspace_dir = framework_dir.parent
frontend_static = workspace_dir / "audi-nevo-frontend-main" / "public"
backend_static = workspace_dir / "nevo-audi-pitch-backend-main" / "static"

static_dir = None
if frontend_static.exists():
    static_dir = str(frontend_static)
    logging.info(f"Static files mounted from frontend public folder: {static_dir}")
elif backend_static.exists():
    static_dir = str(backend_static)
    logging.info(f"Static files mounted from backend static folder: {static_dir}")

if static_dir:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    logging.warning(f"Static files directories not found. Frontend: {frontend_static}, Backend: {backend_static}. Images may not be served.")


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    """
    Lightweight health probe used by local checks and monitoring.
    """
    return {"status": "ok"}


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
@app.post("/login/{modality}")
async def login(request: Request, response: Response, password: str = Body(..., embed=True), modality: str = "audio"):
    """
    Login endpoint. Verifies the password and returns a JWT token and session ID.
    Creates the session state for the user.
    """

    logging.info(f"Login attempt with modality: {modality}")

    if not modality in ["audio", "text"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid modality '{modality}'. Supported modalities are 'audio' and 'text'.",
        )

    if bcrypt.checkpw(password.encode("utf-8"), stored_hashed_password):
        expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        token = jwt.encode({"exp": expiration}, api_helpers.JWT_SECRET_KEY, algorithm=api_helpers.ALGORITHM)
        session_id = str(uuid.uuid4())
        # Set JWT and session ID as HTTP-only cookies
        # For cross-origin requests (frontend and backend on different domains), we need:
        # - Secure=True (required when SameSite=None)
        # - SameSite=None (allows cross-origin cookie sending)
        # Check if we're in Azure (HTTPS) or local (HTTP)
        is_azure = "azurewebsites.net" in str(request.url) or os.getenv("ENABLE_SECURE_COOKIES", "false").lower() == "true"
        response.set_cookie(
            key="access_token", 
            value=token, 
            httponly=True, 
            secure=is_azure,  # True for HTTPS (Azure), False for HTTP (local)
            samesite="none" if is_azure else "lax"  # None for cross-origin (Azure), lax for same-origin (local)
        )
        response.set_cookie(
            key="session_id", 
            value=session_id, 
            httponly=True, 
            secure=is_azure,  # True for HTTPS (Azure), False for HTTP (local)
            samesite="none" if is_azure else "lax"  # None for cross-origin (Azure), lax for same-origin (local)
        )
        input_queue = asyncio.Queue()
        output_queue = asyncio.Queue()
        dialog_manager = DialogManager(output_queue=output_queue, chat_modality=modality)
        store_session_state(
            SessionState(
                id=session_id,
                dialog_manager=dialog_manager,
                input_queue=input_queue,
                output_queue=output_queue,
            )
        )
        logging.info(f"Login successful. New session created with ID {session_id}. Modality is {modality}.")
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


@app.websocket("/ws/audio/{session_id}")
async def websocket_audio_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: dict = Depends(api_helpers.get_and_check_token_from_cookies_ws),
):
    """
    Websocket endpoint for streaming audio and other messages to the client.
    """

    if CONFIG.has_debug_flag("user_first"):
        ai_speaks_first = False
    elif CONFIG.has_debug_flag("ai_first"):
        ai_speaks_first = True
    else:
        ai_speaks_first = CONFIG.ai_speaks_first

    session_state = get_session_state(session_id)

    if session_state is None:
        # this could be more elegant, but we need to check if the session is still active
        logging.warning(f"Websocket wanted to conenct but session not found for the given ID: {session_id} Timed out?")
        try:
            await websocket.close()
        except Exception as e:
            pass  # ignore, we are closing the connection anyway
        logging.warning(f"Session not found for the given ID: {session_id}.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session not found for the given ID.")

    try:
        await websocket.accept()
        logging.info(f"WebSocket connection established. Session ID: {session_id}")
        assert session_state.id == session_id, "Session ID must match the session state."
        session_state.websocket = websocket
        
        # Set session_id in orchestrator if it has a set_session_id method (for Shop version)
        try:
            orchestrator = session_state.dialog_manager._agent_orchestrator
            if hasattr(orchestrator, 'set_session_id'):
                orchestrator.set_session_id(session_id)
                logging.info(f"Session ID set in orchestrator: {session_id}")
        except Exception as e:
            logging.debug(f"Could not set session_id in orchestrator (may not be needed): {e}")

        if ai_speaks_first:
            logging.info(LogAi("AI speaks first."))
            await handle_dialog_step(
                websocket=websocket,
                recording_file_path=None,
                web_element_message=None,
                session_state=session_state,
            )

        # only after the client connects to the websocket, we accept data
        session_state.accept_client_data = True

        while True:
            if websocket.client_state != WebSocketState.CONNECTED:
                logging.info(f"Websocket disconnected for session {session_id}")
                break
            logging.info(f"Waiting for recording file for session {session_id}")
            # wait for a message from the frontend, sent to the input queue from one of the endpoints
            frontend_message = await asyncio.wait_for(
                session_state.input_queue.get(), CONFIG.timeout_wait_for_frontend_message
            )
            # do not accept more data while the server is processing
            session_state.accept_client_data = False
            if isinstance(frontend_message, AudioUploadReady):
                logging.info(f"Recording file ready for session {session_id}: {frontend_message.audio_file_path}")
                await handle_dialog_step(
                    websocket=websocket,
                    recording_file_path=frontend_message.audio_file_path,
                    web_element_message=None,
                    session_state=session_state,
                )
                # delete the audio recording file after processing
                try:
                    os.remove(frontend_message.audio_file_path)
                    logging.info(f"Deleted recording file: {frontend_message.audio_file_path}")
                except Exception as e:
                    logging.error(f"Failed to delete recording file {frontend_message.audio_file_path}: {e}")
            elif isinstance(frontend_message, WebElementMessage):
                logging.info(f"Handling web element message for session {session_id}: {frontend_message}")
                await handle_dialog_step(
                    websocket=websocket,
                    recording_file_path=None,
                    web_element_message=frontend_message.message_dict,
                    session_state=session_state,
                )
            else:
                logging.error(f"Unexpected frontend message type: {frontend_message}")
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


async def handle_dialog_step(
    websocket: WebSocket,
    recording_file_path: str | None,
    web_element_message: dict | None,
    session_state: SessionState,
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
                recording_file_path=recording_file_path, web_element_message=web_element_message
            )
        )
        await asyncio.gather(audio_response_task)

    asyncio.create_task(streaming_ai_tasks())
    try:
        # wait for data created by the streaming dialog step chain
        while True:
            data = await asyncio.wait_for(
                session_state.dialog_manager.get_output_queue().get(), timeout=QUEUE_TIMEOUT__OUTPUT_DATA
            )
            # important to keep the session alive when the AI is streaming long answers
            session_state.set_was_active()
            if data == DIALOG_STEP_ENDED:
                # If we are at the end of the dialog step we break out of the loop as we don't have more messages or audio chunks to send.
                logging.info(f"handle_dialog_step: received DIALOG_STEP_ENDED signal for session {session_state.id}")
                await api_helpers.send_pydantic(websocket, server_messages.EndOfDialogStepMessage())
                break
            elif isinstance(data, bytes):
                # if we have audio data, send it to the client
                await websocket.send_bytes(data)
            elif isinstance(data, pydantic.BaseModel):
                # if we have a Pydantic model, which is (hopefully) a web element message -> send it to the client
                await api_helpers.send_pydantic(websocket, data)
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


@app.post("/receive_audio_blob")
async def recieve_audio_blob(
    file: UploadFile = File(...),
    token: dict = Depends(api_helpers.get_and_check_token_from_cookies),
    session_state: SessionState = Depends(api_helpers.get_session_state_from_cookies),
):
    """
    Endpoint for uploading audio files (user's recorded message) to the server.
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
        session_state.input_queue.put_nowait(AudioUploadReady(audio_file_path=recording_file_path))
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


def validate_orchestrator_class():
    """
    Validates the orchestrator class specified in the configuration.
    Raises an exception if the class is not a subclass of AbstractAgentOrchestrator or if instantiation fails.
    """
    from nevo_framework.helpers.instantiation import create_instance_from_string
    from nevo_framework.llm.agent_orchestrator import AbstractAgentOrchestrator

    if CONFIG.orchestrator_class is None:
        raise ValueError("Orchestrator class must be set in the configuration.")
    agent_orchestrator: AbstractAgentOrchestrator = create_instance_from_string(
        CONFIG.orchestrator_class, output_queue=asyncio.Queue(), chat_modality="text"
    )
    if not isinstance(agent_orchestrator, AbstractAgentOrchestrator):
        raise TypeError(
            f"Orchestrator class {CONFIG.orchestrator_class} must be a subclass of AbstractAgentOrchestrator."
        )
    print(f"Orchestrator class {CONFIG.orchestrator_class} validated successfully.")


def main():
    import argparse
    import uvicorn
    
    # Check for PORT first (Azure App Service sets this)
    port = os.getenv("PORT")
    if port is None:
        # Fallback to LOCAL_API_ENDPOINT (for local development)
        local_endpoint = os.getenv("LOCAL_API_ENDPOINT")
        if local_endpoint is None:
            port = 8000
        else:
            port = local_endpoint.split(":")[-1]
            assert port.isdigit(), "Port number must be an integer"
            port = int(port)
    else:
        port = int(port)

    parser = argparse.ArgumentParser(description="Start the API server.")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for the server.")
    parser.add_argument(
        "--debug",
        type=str,
        help=f"Set debug flags, comma separated without spaces.",
    )
    parser.add_argument(
        "--log_chatsteps",
        action="store_true",
        help="Log token use, AI transcript, length of speech, ... to JSON files.",
    )
    parser.add_argument("--store_audio", action="store_true", help="Store AI audio to disk.")
    parser.add_argument(
        "--ai_first", action="store_true", help="AI speaks first in the dialog, regardless of config setting."
    )
    parser.add_argument(
        "--user_first", action="store_true", help="User speaks first in the dialog, regardless of config setting."
    )
    args = parser.parse_args()
    if args.reload:
        print("Uvicorn auto-reload enabled!")
    else:
        print("Uvicorn auto-reload disabled.")

    debug_flags = ""
    if args.debug:
        logging.warning(f"Debug flags set: {args.debug}")
        debug_flags = args.debug
    if args.store_audio:
        debug_flags += ",store_audio"
        logging.warning("Debug flag 'store_audio' set: AI audio will be stored to disk.")
    if args.log_chatsteps:
        debug_flags += ",log_chatsteps"
        logging.warning("Debug flag 'log_chatsteps' set: Details of chat steps will be logged to JSON.")
    if args.ai_first:
        debug_flags += ",ai_first"
        assert not args.user_first, "Cannot set both --ai_first and --user_first flags."
        logging.warning("Debug flag 'ai_first' set: AI will speak first in the dialog, ignoring config setting.")
    if args.user_first:
        debug_flags += ",user_first"
        assert not args.ai_first, "Cannot set both --ai_first and --user_first flags."
        logging.warning("Debug flag 'user_first' set: User will speak first in the dialog, ignoring config setting.")

    os.environ["API_DEBUG"] = debug_flags

    validate_orchestrator_class()

    uvicorn.run(
        "nevo_framework.api.api:app",
        host="0.0.0.0",
        port=port,
        reload=args.reload,
        log_config="config/log-server.ini",
    )


if __name__ == "__main__":
    main()
