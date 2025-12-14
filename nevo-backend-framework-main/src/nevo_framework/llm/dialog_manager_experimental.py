import asyncio
import logging
from typing import Any

from nevo_framework.config.master_config import get_master_config
import llm.audi.audi_orchestrator as audi_orchestrator
import nevo_framework.llm.llm_tools as llm_tools
from nevo_framework.config.definitions import *
from llm.audi import data
from nevo_framework.playground.prompt_repo import PromptRepo
from nevo_framework.helpers.logging_helpers import DIALOG_STEP_ENDED, LogAi, LogAiDialogStart, LogAiUserMessage, TimingLogger
from llm.neva import neva_agent_orchestrator
from llm.aiiv import aiiv_agent_orchestrator

CONFIG = get_master_config()


class DialogManager:
    def __init__(
        self, output_queue: asyncio.Queue, prompt_repo: PromptRepo | None = None, **orchestrator_args: dict[str, Any]
    ) -> None:
        """Class that creates an AI that can interact with the user based on the llamaindex

        Args:
            output_queue (asyncio.Queue): Queue for sending messages to the frontend.
            prompt_repo (PromptRepo | None): Repository for prompts. This is what the playground frontend writes to. Not used by all orchestrators.
            orchestrator_args (dict[str, Any]): Arguments for the orchestrator.
        """
        assert output_queue is not None, "Output queue must be provided"
        self._output_queue: asyncio.Queue = output_queue
        # this is the history of the conversation, with everything the user and the AI said
        self._message_hist: list[dict[str, Any]] = []

        if CONFIG.has_debug_flag("recommendation"):
            logging.warning(LogAi("Debug flag 'recommendation' is set, setting the dialog state."))
            self._message_hist = [
                {
                    "role": "assistant",
                    "content": "Thank you for sharing this with me! I'm now ready to help you find the perfect car for you.",
                },
                {"role": "assistant", "content": data.TEST_RECOMMENDATION_TEXT_1},
            ]
        self._prompt_repo: PromptRepo | None = prompt_repo
        self._orchestrator_args: dict[str, Any] = orchestrator_args
        # queue for AI output, both audio packets and messages, all sent to the frontend
        self._ai_species: str | None = None  # will be set in _set_orchestrator_from_config
        self._set_orchestrator_from_config(**(self._orchestrator_args))
        assert self._agent_orchestrator is not None, "Agent orchestrator must be set after orchestrator configuration."
        assert self._ai_species is not None, "AI species must be set after orchestrator configuration."

    def reset_dialog(self, **orchestrator_args: dict[str, Any]) -> None:
        """
        Reset the dialog history.

        Args:
            orchestrator_args (dict[str, Any]): Arguments for the orchestrator.
        """
        logging.info(LogAi(f"Resetting dialog. Orchestrator args: {orchestrator_args}"))
        self._message_hist = []
        self._set_orchestrator_from_config(**orchestrator_args)

    def get_ai_species(self) -> str:
        """Get the type of AI (type of orchestrator) that is being used by this DialogManager."""
        return self._ai_species

    def _set_orchestrator_from_config(self, **orchestrator_args: dict[str, Any]) -> None:
        ai_flag = [flag for flag in CONFIG.debug_flags if flag.startswith("ai=")]
        if len(ai_flag) > 1:
            raise ValueError(f"Multiple AI types specified: {ai_flag}")
        elif len(ai_flag) == 1:
            ai_type = ai_flag[0].split("=")[1]
            logging.info(LogAi(f"AI type: {ai_type}"))
        else:
            ai_type = "audi"
            logging.info(LogAi("No AI type specified, using default: audi"))

        assert self._output_queue is not None
        assert ai_type is not None

        if ai_type == "audi":
            self._agent_orchestrator: audi_orchestrator.AbstractAgentOrchestrator = (
                audi_orchestrator.AudiAgentOrchestrator(output_queue=self._output_queue, **orchestrator_args)
            )
            self._ai_species = "audi"
        elif ai_type == "neva":  # Nevo speaking about himself
            self._agent_orchestrator: neva_agent_orchestrator.NevaAgentOrchestrator = (
                neva_agent_orchestrator.NevaAgentOrchestrator(output_queue=self._output_queue, **orchestrator_args)
            )
            self._ai_species = "neva"
        elif ai_type == "aiiv":  # Experiment for Tomas
            self._agent_orchestrator: audi_orchestrator.AbstractAgentOrchestrator = (
                aiiv_agent_orchestrator.AiivAgentOrchestrator(
                    output_queue=self._output_queue, prompt_repo=self._prompt_repo, **orchestrator_args
                )
            )
            self._ai_species = "aiiv"
        else:
            raise ValueError(f"Unknown AI type: {ai_type}")
        logging.info(LogAiDialogStart())

    async def dialog_step(
        self,
        transcribed_user_message: str | None = None,
        web_element_message: dict | None = None,
        recording_file_path: str | None = None,
    ) -> None:
        with TimingLogger("DialogManager:dialog_step"):

            assert (
                sum(x is not None for x in [transcribed_user_message, web_element_message, recording_file_path]) <= 1
            ), "At most one of transcribed_user_message, web_element_message, or recording_file_path must be provided."

            if recording_file_path:
                raise DeprecationWarning("This should not be used anymore, provide transcribed_user_message instead.")
                with TimingLogger("DialogManager:dialog_step:transcribe"):
                    transcribed_user_message = await llm_tools.transcribe_recording(recording_file_path)
                logging.info(LogAiUserMessage(transcribed_user_message))

            if transcribed_user_message:
                self._message_hist.append({"role": "user", "content": transcribed_user_message})

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
                logging.info(
                    LogAi(f"Calling _agent_orchestrator.dialog_step, with the following dialog:\n{dialog_str}")
                )

            with TimingLogger("dialog_step:_agent_orchestrator"):
                # Call the orchestrator to get the next step in the dialog
                response = await self._agent_orchestrator.dialog_step(
                    dialog=self._message_hist, web_element_message=web_element_message
                )

            if response._web_element_messages:
                for message in response._web_element_messages:
                    self._output_queue.put_nowait(message)

            self.get_output_queue().put_nowait(DIALOG_STEP_ENDED)

    def get_output_queue(self) -> asyncio.Queue:
        return self._output_queue
