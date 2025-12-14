import asyncio
import datetime
from asyncio import Queue
from dataclasses import dataclass, field
import logging
from typing import Literal

from fastapi import status
from fastapi import HTTPException, WebSocket
from fastapi.websockets import WebSocketState

from nevo_framework.llm.dialog_manager import DialogManager

from nevo_framework.config.master_config import get_master_config

CONFIG = get_master_config()


# dictionary to store the session state for each session
_sessions: dict[str, "SessionState"] = {}


@dataclass
class SessionState:
    """This is the state of a user session which is maintained in memory by the API server."""

    # session id
    id: str
    # The dialog manager, which handles the conversation and AI processing, and contains the agent orchestrator.
    dialog_manager: DialogManager
    # Queue used for data received from the frontend from various sources. The queue is processed in the
    # main "dialog loop".
    input_queue: Queue
    # Queue used for data sent to the frontend, such as audio chunks and messages.
    output_queue: Queue
    # timestamp of the users last activity
    last_activity: datetime.datetime = field(default_factory=datetime.datetime.now)
    # indicates whether the session is currently accepting data from the client
    accept_client_data: bool = False
    # the websocket connection
    websocket: WebSocket = None
    # the session is marked for removal on the next periodic cleanup
    kill_session: bool = False


    def set_was_active(self):
        """
        Update the last activity timestamp to the current time.
        """
        self.last_activity = datetime.datetime.now()

    def get_ai_species(self) -> str:
        """
        Get the type of AI (type of orchestrator) that is being used in this session.
        """
        return self.dialog_manager.get_ai_species()


def store_session_state(session_state: SessionState):
    """
    Store the session state in the sessions dictionary.
    If the session ID already exists, raise an HTTPException.
    """
    if session_state.id in _sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session ID {session_state.id} already exists. Cannot create a new session with the same ID.",
        )
    _sessions[session_state.id] = session_state


def get_session_state(session_id: str) -> SessionState | None:
    """
    Helper to retrieve the session state for a given session ID.
    Returns None if the session is not found.
    """
    return _sessions.get(session_id)


async def session_cleanup():
    """
    Check for inactive sessions and close them. This is run periodically in the background.
    This is only necessary for sessions that log in in but never connected to the websocket.
    The websocket connection will time out sessions that do not upload audio frequently enough.
    """
    logging.info("Starting periodic session activity check.")
    while True:
        logging.info("Checking for inactive or disconnected sessions.")
        now = datetime.datetime.now()
        # check for sessions that have been marked for removal
        sessions_to_kill: set[str] = set(
            (session.id, "marked for removal") for session in _sessions.values() if session.kill_session
        )
        # check for sessions that have not been active for a while
        sessions_to_kill.update(
            (session.id, "inactive")
            for session in _sessions.values()
            if (now - session.last_activity).total_seconds() > 60 * CONFIG.timeout_session_activity_minutes
        )
        # check for sessions that have a websocket connection that is not connected
        sessions_to_kill.update(
            (session.id, "websocket not connected")
            for session in _sessions.values()
            if session.websocket and session.websocket.client_state != WebSocketState.CONNECTED
        )
        # remove sessions that are marked for removal
        for session_id, kill_reason in sessions_to_kill:
            # this seems to occur sometimes
            if session_id not in _sessions:
                continue
            if _sessions[session_id].websocket:
                # close the websocket connection if it is still open
                try:
                    await asyncio.wait_for(_sessions[session_id].websocket.close(), timeout=10)
                except Exception as e:
                    pass  # ignore, we are closing the connection anyway
            del _sessions[session_id]
            logging.info(f"Session {session_id} removed, reason: {kill_reason}")
        await asyncio.sleep(CONFIG.session_cleanup_interval_seconds)
