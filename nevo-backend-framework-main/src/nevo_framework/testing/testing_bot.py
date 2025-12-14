from nevo_framework.testing.simple_agents import AudioChatAgent
from typing import Callable, Literal


class TestingAudioAgent(AudioChatAgent):
    def __init__(
        self,
        name: str,
        async_openai_client,
        system_prompt: str,
        first_message: str = None,
        model: str = "gpt-4o",
        pyaudio_stream=None,
        voice: str = "onyx",
        pre_chatstep_callback: Callable[[list[dict[str, str]]], None] = None,
        post_chatstep_callback: Callable[[list[dict[str, str]]], None] = None,
    ):
        super().__init__(
            name=name,
            async_openai_client=async_openai_client,
            system_prompt=system_prompt,
            first_message=first_message,
            model=model,
            pyaudio_stream=pyaudio_stream,
            voice=voice,
        )
        self.pre_chatstep_callback = pre_chatstep_callback
        self.post_chatstep_callback = post_chatstep_callback

    async def chat_step(
        self, opponent_message=None, audio_output_path=None, modality: Literal["audio", "text"] = "audio"
    ):
        if self.pre_chatstep_callback:
            self.pre_chatstep_callback(self.conversation)
        response = await super().chat_step(
            opponent_message=opponent_message, audio_output_path=audio_output_path, modality=modality
        )
        if self.post_chatstep_callback:
            self.post_chatstep_callback(self.conversation)
        return response
