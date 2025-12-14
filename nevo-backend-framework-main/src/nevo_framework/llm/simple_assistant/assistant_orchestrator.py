import asyncio
from typing import Any

from nevo_framework.config.master_config import get_master_config
from nevo_framework.llm.agent_orchestrator import AbstractAgentOrchestrator
from nevo_framework.llm.agents import VoiceAgent, VoiceAgentResponse
from nevo_framework.llm.llm_tools import trim_prompt

CONFIG = get_master_config()


class AssistantOrchestrator(AbstractAgentOrchestrator):

    def __init__(self, output_queue: asyncio.Queue):
        super().__init__(output_queue)

        sysprompt = trim_prompt(
            """You are a friendly virtual assistant designed for voice interaction. Adopt a natural, conversational but professional tone, like you're speaking directly to someone. Mimic spoken language patterns. Use contractions and keep your sentences relatively short. Avoid using typical 'written' language, and instead, focus on how you would speak in a casual conversation. Do not use bullet points or numbered lists. Do not use markdown. You speak with a decidedly British accent."""
        )
        self.speaking_agent = VoiceAgent(
            name="AIIV",
            default_system_message=sysprompt,
            async_openai_client=CONFIG.language_model_config.client["audio"],
        )

    async def dialog_step(
        self,
        dialog: list[dict[str, str]],
        web_element_message: dict[str, Any],
    ) -> VoiceAgentResponse:
        response = await self.speaking_agent.dialog_step(dialog=dialog)
        return response
