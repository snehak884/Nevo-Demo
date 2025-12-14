import logging
import os

import jwt
import pydantic
from fastapi import HTTPException, Request, WebSocket, status

from nevo_framework.api.sessions import SessionState, get_session_state

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"


async def get_and_check_token_from_cookies_ws(websocket: WebSocket):
    # Try to get token from cookies first (same-origin)
    token = websocket.cookies.get("access_token")
    
    # If not in cookies, try query parameter (cross-origin WebSocket)
    if not token:
        query_params = dict(websocket.query_params)
        token = query_params.get("token")
    
    if not token:
        logging.warning("get_and_check_token_from_cookies_ws: WebSocket token missing from both cookies and query params")
        logging.debug(f"WebSocket cookies: {websocket.cookies}")
        logging.debug(f"WebSocket query params: {dict(websocket.query_params)}")
        await websocket.close(code=1008)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token missing")
    await verify_jwt_token(token)
    return token


async def get_and_check_token_from_cookies(request: Request) -> str:
    logging.info(f"Request cookies: {request.cookies}, getting token.")  # Changed to INFO for debugging
    token = request.cookies.get("access_token")
    if not token:
        # Also check Authorization header as fallback for cross-origin requests
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            logging.info(f"Token found in Authorization header instead of cookies")
        else:
            logging.error(f"Token missing from both cookies and Authorization header. Cookies: {request.cookies}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token missing")
    await verify_jwt_token(token)
    return token


async def get_session_id_from_cookies(request: Request) -> str:
    logging.info(f"Request cookies: {request.cookies}, getting session id.")  # Changed to INFO for debugging
    session_id = request.cookies.get("session_id")
    if not session_id:
        # Fallback: check X-Session-ID header for cross-origin requests
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            logging.info(f"Session ID found in X-Session-ID header instead of cookies")
        else:
            logging.error(f"Session ID missing from both cookies and X-Session-ID header. Cookies: {request.cookies}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session ID missing")
    return session_id


async def get_session_state_from_cookies(request: Request) -> SessionState:
    logging.info(f"Request cookies: {request.cookies}, getting session id.")  # Changed to INFO for debugging
    session_id = request.cookies.get("session_id")
    if not session_id:
        # Fallback: check X-Session-ID header for cross-origin requests
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            logging.info(f"Session ID found in X-Session-ID header instead of cookies")
        else:
            logging.error(f"Session ID missing from both cookies and X-Session-ID header. Cookies: {request.cookies}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session ID missing")
    if session := get_session_state(session_id):
        return session
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session not found for the given ID.")


async def verify_jwt_token(token: str) -> dict:
    try:
        logging.debug(f"Verifying JWT token: {token}")
        # Decode and validate the JWT token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logging.warning("verify_jwt_token: Token has expired")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token has expired")
    except jwt.InvalidTokenError:
        logging.warning("verify_jwt_token: Invalid token")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")


async def send_pydantic(websocket: WebSocket, message: pydantic.BaseModel):
    """
    Helper function to send a Pydantic model as JSON to a WebSocket.
    """
    await websocket.send_text(message.model_dump_json())


def setup_ai_logging():
    """
    Programmatically set up a logger that filters for AI messages and logs to a file.
    This does not seem to work in the logging ini file.
    """

    # Define the custom filter
    class AILogFilter(logging.Filter):
        def filter(self, record):
            return record.getMessage().startswith("<<<AI>>>")

    # Programmatically set up a logger that filters for AI messages and logs to a file.
    # This does not seem to work in the logging ini file.
    ai_log_handler = logging.handlers.RotatingFileHandler("ai.log", maxBytes=5 * 1024 * 1024, backupCount=3)
    ai_log_handler.setLevel(logging.INFO)
    ai_log_handler.setFormatter(
        logging.Formatter(
            "SERVER [%(asctime)s] [%(thread)d] [%(name)s %(module)s.%(funcName)s] %(levelname)s - %(message)s"
        )
    )
    ai_log_handler.addFilter(AILogFilter())
    logging.getLogger().addHandler(ai_log_handler)
