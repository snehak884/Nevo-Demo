from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel


class TextChunkMessage(BaseModel):
    """Server to frontend message to send a text chunk for text based chat."""

    type: Literal["text_chunk"] = "text_chunk"
    content: str


class EndOfDialogStepMessage(BaseModel):
    """
    Server to frontend message to indicate the end of the dialog step. After this message has been sent,
    the server will not send any more dialog (audio or text chunks) until the frontend triggers the next dialog step
    by sending a message (user voice input or web element message) to the server.
    """

    type: Literal["END_OF_DIALOG_STEP"] = "END_OF_DIALOG_STEP"
    server_error: str | None = None


class EndOfResponseMessage(BaseModel):
    """
    Server to frontend message to indicate the end of the response, but not the end of the dialog step
    since a dialog step can contain multiple responses. After this message has been sent, the server
    can still send more dialog (audio or text chunks). Wait for the EndOfDialogStepMessage to know when the
    dialog step is complete and the server will not send any more dialog until the frontend triggers the next step.

    The EndOfResponseMessage can be used to split a long response into multiple parts in the frontend,
    for example in text chat mode.
    """

    type: Literal["end_of_response"] = "end_of_response"


class AiStatusMessage(BaseModel):
    """Server to frontend message to indicate the status of the AI, for debugging purposes."""

    type: Literal["ai_status"] = "ai_status"
    message: str


class TranscriptionCompletedMessage(BaseModel):
    """Server to frontend message to indicate that the transcription is complete."""

    type: Literal["transcription_completed"] = "transcription_completed"
    content: str


# Hard coded end of dialog step
END_OF_DIALOG_STEP_MESSAGE = EndOfDialogStepMessage()


class TextChatResponse(BaseModel):
    """Server to frontend message to send a text response for text based chat."""

    type: Literal["text_chat_response"] = "text_chat_response"
    content: str


############################################################################################################
# Internal messages used within the server.


@dataclass
class AudioUploadReady:
    audio_file_path: str


@dataclass
class WebElementMessage:
    message_type: str
    message_dict: dict[str, Any]


@dataclass
class TranscribedAudio:
    content: str
