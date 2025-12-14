import asyncio
import logging
from typing import Any, Literal

import nevo_framework.llm.llm_tools as llm_tools
from nevo_framework.api.server_messages import TextChatResponse
from nevo_framework.config.master_config import get_master_config
from nevo_framework.helpers.logging_helpers import (
    DIALOG_STEP_ENDED,
    LogAi,
    LogAiDialogStart,
    LogAiUserMessage,
    TimingLogger,
)
from nevo_framework.llm.agent_orchestrator import AbstractAgentOrchestrator

CONFIG = get_master_config()


class DialogManager:
    def __init__(self, output_queue: asyncio.Queue, chat_modality: Literal["text", "audio"]) -> None:
        """Class that creates an AI that can interact with the user based on the llamaindex

        Args:
            force_rebuild (bool, optional): Whether to rebuild the index. Defaults to False.
        """
        logging.info(f"Initializing DialogManager with chat modality: {chat_modality}")
        assert output_queue is not None, "Output queue must be provided"
        assert chat_modality in ["text", "audio"], "Chat modality must be either 'text' or 'audio'."
        # this is the history of the conversation, with everything the user and the AI said
        self._message_hist: list[dict[str, Any]] = []

        if CONFIG.has_debug_flag("recommendation"):
            raise DeprecationWarning("Debug flag 'recommendation' is deprecated.")
            # this depends on audi stuff whihch is not available in the nevo framework
            logging.warning(LogAi("Debug flag 'recommendation' is set, setting the dialog state."))
            self._message_hist = [
                {
                    "role": "assistant",
                    "content": "Thank you for sharing this with me! I'm now ready to help you find the perfect car for you.",
                },
                {"role": "assistant", "content": data.TEST_RECOMMENDATION_TEXT_1},
            ]
        # queue for AI output, both audio packets and messages, all sent to the frontend
        self._output_queue: asyncio.Queue = output_queue
        self._ai_species: str | None = None  # will be set in _set_orchestrator_from_config
        self._set_orchestrator_from_config(chat_modality=chat_modality)
        assert self._agent_orchestrator is not None, "Agent orchestrator must be set after orchestrator configuration."
        assert self._ai_species is not None, "AI species must be set after orchestrator configuration."

    def get_ai_species(self) -> str:
        """Get the type of AI (type of orchestrator) that is being used by this DialogManager."""
        return self._ai_species

    def _set_orchestrator_from_config(self, chat_modality: Literal["text", "audio"]) -> None:
        from nevo_framework.helpers.instantiation import create_instance_from_string

        if CONFIG.orchestrator_class is None:
            raise ValueError("Orchestrator class must be set in the configuration.")
        self._agent_orchestrator: AbstractAgentOrchestrator = create_instance_from_string(
            CONFIG.orchestrator_class, output_queue=self._output_queue, chat_modality=chat_modality
        )
        if not isinstance(self._agent_orchestrator, AbstractAgentOrchestrator):
            raise TypeError(
                f"Orchestrator class {CONFIG.orchestrator_class} must be a subclass of AbstractAgentOrchestrator."
            )
        self._ai_species: str = CONFIG.orchestrator_class
        assert self._output_queue is not None
        logging.info(LogAiDialogStart())

    async def dialog_step(self, recording_file_path: str | None, web_element_message: dict | None) -> None:
        
        if recording_file_path:
            with TimingLogger("generate_response_openai_streaming:transcribe_recording"):
                user_message = await llm_tools.transcribe_recording(recording_file_path)
            logging.info(LogAiUserMessage(user_message))
        elif web_element_message and web_element_message.get("type") == "text_chat_response":
            if user_message := web_element_message.get("content"):
                # If the web element message is a TextChatResponse, we take the users message from it
                # but we do not pass the message itself to the orchestrator, as it is not needed for the dialog step.
                web_element_message = None
                logging.info(LogAiUserMessage(user_message))
            else:
                logging.error(f"Web element message '{web_element_message}' does not contain a user message.")
        else:
            user_message = None

        if user_message:
            self._message_hist.append({"role": "user", "content": user_message})

        assert self._output_queue is not None
        self._agent_orchestrator.set_audio_output_queue(self._output_queue)

        if False:  # debugging
            # log the whole dialog
            dialog_str = "\n".join(
                [
                    f"{message['role']}: '{message['content']}' {message.get('audio', '')}\n"
                    for message in self._message_hist
                ]
            )
            logging.info(LogAi(f"Calling _agent_orchestrator.dialog_step, with the following dialog:\n{dialog_str}"))

        response = await self._agent_orchestrator.dialog_step(
            dialog=self._message_hist, web_element_message=web_element_message
        )

        if response._web_element_messages:
            for message in response._web_element_messages:
                self._output_queue.put_nowait(message)

        self.get_output_queue().put_nowait(DIALOG_STEP_ENDED)

    def get_output_queue(self) -> asyncio.Queue:
        return self._output_queue
