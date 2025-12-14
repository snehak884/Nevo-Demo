import abc
import asyncio
import logging
from typing import Any, Literal

from pydantic import BaseModel

import nevo_framework.api.server_messages as server_messages
from nevo_framework.helpers.logging_helpers import LogAi
from nevo_framework.llm.agents import VoiceAgent, VoiceAgentResponse


class AbstractAgentOrchestrator(abc.ABC):

    def __init__(self, output_queue: asyncio.Queue, chat_modality: Literal["text", "audio"] = "audio"):
        """
        The AgentOrchestrator is the main class that manages the interaction between the user and the AI agents.
        It is initialized by the framework.

        Args:
            output_queue (asyncio.Queue): Queue to which the audio output and output messages are written.
        """
        super().__init__()
        assert chat_modality in ["text", "audio"], "Chat modality must be either 'text' or 'audio'."
        assert output_queue is not None, "Output queue must be set."
        self._output_queue: asyncio.Queue = output_queue
        self._status_messages: list[server_messages.AiStatusMessage] = []
        # never ever access this directly, always use the setter to make sure the audio queue is set
        self.___PRIVATE_speaking_bot: VoiceAgent = None
        self._chat_modality: Literal["text", "audio"] = chat_modality
        logging.info(LogAi(f"Agent orchestrator initialized with chat modality: {self._chat_modality}"))

    @property
    def speaking_agent(self):
        return self.___PRIVATE_speaking_bot

    @speaking_agent.setter
    def speaking_agent(self, chatbot: VoiceAgent):
        logging.info(LogAi(f"Switched agent to {chatbot.name}"))
        assert self._output_queue is not None, "Output queue must be set."
        self.___PRIVATE_speaking_bot = chatbot
        self.___PRIVATE_speaking_bot._set_audio_output_queue(self._output_queue)
        self.___PRIVATE_speaking_bot._set_modality(self._chat_modality)
        self.send_status_message(f"Current agent: {chatbot.name}")

    def send_web_element_message(self, message: BaseModel):
        """
        Sends a web element message to the frontend immediately.
        """
        assert self._output_queue is not None, "Output queue must be set."
        if type := getattr(message, "type", None):
            if type != "":
                self._output_queue.put_nowait(message)
                return
        logging.error(LogAi(f"Malformed web element message not sent: {message}"))

    def send_status_message(self, message: str):
        self.send_web_element_message(server_messages.AiStatusMessage(message=message))

    def set_audio_output_queue(self, audio_output_queue: asyncio.Queue):
        self._output_queue = audio_output_queue
        if self.speaking_agent is not None:
            self.speaking_agent._set_audio_output_queue(audio_output_queue)

    def current_chatbot_name(self) -> str:
        """Returns the name of the current chatbot."""
        return self.speaking_agent.name

    @abc.abstractmethod
    async def dialog_step(
        self,
        dialog: list[dict[str, str]],
        web_element_message: dict[str, Any],
    ) -> VoiceAgentResponse:
        """
        This method is called by the framework whenever a voice response by the AI is needed.
        In this method there is usually exactly one call to a voice agent, and its `AudioAgentResponse` is returned.

        * The `dialog` **must** be passed to the voice agent, as it is used to keep track of entire conversation.
        * The `dialog` can be read but should **not be modified** in any way.
        * The framework will take care of sending all web element messages in the returned response.

        Making multiple calls to voice agents in this method is permitted as long as the `dialog` is passed to each call.
        In this case, however, attention should be paid to the web element messages. Only the web element messages returned
        by this function will as part of the `AudioAgentResponse` be sent to the frontend.

        Args:
            dialog: The full conversation dialog so far, including the latest message from the user if the user has spoken.
            web_element_message: A web element message that was sent from the frontend.

        Returns:
            The response from the voice agent.
        """

        raise NotImplementedError
