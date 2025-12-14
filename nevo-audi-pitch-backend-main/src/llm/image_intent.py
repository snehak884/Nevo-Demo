import asyncio
import logging
from typing import Literal, Optional

from pydantic import BaseModel, Field

import llm.messages as server_messages
from nevo_framework.config.master_config import load_json_config
from nevo_framework.helpers.logging_helpers import LogAi
from nevo_framework.llm.agents import GeneralAgentAsync, StructuredOutputAgent, VoiceAgent
from nevo_framework.llm.llm_tools import trim_prompt

CONFIG = load_json_config()

WALKAROUND_IMAGE_FILES = {
    "A3": [
        "Walkaround_A3_rear_left.jpeg",
        "Walkaround_A3_trunk_open.jpeg",
        "Walkaround_A3_dashboard.jpeg",
        "Walkaround_A3_side_left.jpeg",
        "Walkaround_A3_rear_right.jpeg",
        "Walkaround_A3_front_right.jpeg",
        "Walkaround_A3_front_left.jpeg",
        "Walkaround_A3_front_left_square.jpeg",
        "Walkaround_A3_rear.jpeg",
        "Walkaround_A3_side_right.jpeg",
        "Walkaround_A3_front.jpeg",
    ],
    "Q6": [
        "Walkaround_Q6_front_left.jpeg",
        "Walkaround_Q6_dashboard.jpeg",
        "Walkaround_Q6_side_left.jpeg",
        "Walkaround_Q6_rear_left.jpeg",
        "Walkaround_Q6_front_right.jpeg",
        "Walkaround_Q6_side_right.jpeg",
        "Walkaround_Q6_trunk_open.jpeg",
        "Walkaround_Q6_rear.jpeg",
        "Walkaround_Q6_front.jpeg",
        "Walkaround_Q6_front_left_square.jpeg",
        "Walkaround_Q6_rear_right.jpeg",
    ],
    "A6": [
        "Walkaround_A6_rear_right.jpeg",
        "Walkaround_A6_front.jpeg",
        "Walkaround_A6_front_left_square.jpeg",
        "Walkaround_A6_rear.jpeg",
        "Walkaround_A6_front_right.jpeg",
        "Walkaround_A6_trunk_open.jpeg",
        "Walkaround_A6_side_left.jpeg",
        "Walkaround_A6_side_right.jpeg",
        "Walkaround_A6_dashboard.jpeg",
        "Walkaround_A6_rear_left.jpeg",
        "Walkaround_A6_front_left.jpeg",
    ],
    "A1": [
        "Walkaround_A1_rear.jpeg",
        "Walkaround_A1_rear_right.jpeg",
        "Walkaround_A1_front_right.jpeg",
        "Walkaround_A1_front.jpeg",
        "Walkaround_A1_trunk_open.jpeg",
        "Walkaround_A1_dashboard.jpeg",
        "Walkaround_A1_side_left.jpeg",
        "Walkaround_A1_side_right.jpeg",
        "Walkaround_A1_front_left_square.jpeg",
        "Walkaround_A1_rear_left.jpeg",
        "Walkaround_A1_front_left.jpeg",
    ],
    "Q3": [
        "Walkaround_Q3_front_left_square.jpeg",
        "Walkaround_Q3_front.jpeg",
        "Walkaround_Q3_side_right.jpeg",
        "Walkaround_Q3_rear.jpeg",
        "Walkaround_Q3_front_left.jpeg",
        "Walkaround_Q3_rear_right.jpeg",
        "Walkaround_Q3_rear_left.jpeg",
        "Walkaround_Q3_front_right.jpeg",
        "Walkaround_Q3_side_left.jpeg",
        "Walkaround_Q3_trunk_open.jpeg",
        "Walkaround_Q3_dashboard.jpeg",
    ],
}


class ImageCommentaryAgent(VoiceAgent):

    def __init__(self, current_model: str, view: str, current_image: str):
        sys_prompt = trim_prompt(
            f"""Your role is to show images. You will ignore the entire context and all pevious steps in the conversation. 
                    You are currently showing the image {current_image}.
                    You will ONLY ask the user if they would like to see the {view} of the {current_model}."""
        )
        super().__init__(
            name="ImageCommentaryAgent",
            default_system_message=sys_prompt,
            temperature=0.7,
            async_openai_client=CONFIG.language_model_config.client["audio"],
            model=CONFIG.language_model_config.model_deployment_name["audio"],
        )

    # def _chat_step(
    #     self,
    #     messages_for_context: list[str],
    #     full_dialog: list[str],
    #     timed_web_element_messages: list[str],
    #     llm_call: Callable,
    # ):
    #     system_prompt_only_context = [
    #         {"role": "system", "content": self.default_system_message},
    #     ]
    #     return super()._chat_step(
    #         messages_for_context=system_prompt_only_context,
    #         full_dialog=full_dialog,
    #         timed_web_element_messages=timed_web_element_messages,
    #         llm_call=llm_call,
    #     )


class CarModelWalkaroundTracker:
    def __init__(self):
        self.current_position = 0
        self.ordered_images = {}
        self.models = ["A3", "A6", "Q3", "A1", "Q6"]

        image_templates = [
            "Walkaround_{model}_front.jpeg",
            "Walkaround_{model}_front_right.jpeg",
            "Walkaround_{model}_side_right.jpeg",
            "Walkaround_{model}_rear_right.jpeg",
            "Walkaround_{model}_rear.jpeg",
            # 'Walkaround_{model}_trunk_open.jpeg',
            "Walkaround_{model}_rear_left.jpeg",
            "Walkaround_{model}_side_left.jpeg",
            "Walkaround_{model}_front_left.jpeg",
            # 'Walkaround_{model}_dashboard.jpeg',
        ]

        for model in self.models:
            self.ordered_images[model] = [image.format(model=model) for image in image_templates]

        self.max_idx = len(image_templates) - 1

    def rotate_image(self, direction: Literal["left", "right"], model: str, current_image: str = None):
        model = model.replace("Audi ", "")
        if current_image:
            if "trunk_open" in current_image:
                target_image = f"Walkaround_{model}_rear.jpeg"
            elif "dashboard" in current_image:
                target_image = f"Walkaround_{model}_front.jpeg"
            else:
                target_image = current_image.split("/")[-1]

            self.current_position = self.ordered_images[model].index(target_image)
        else:
            self.current_position = -1

        if direction == "left":
            self.current_position -= 1
            if self.current_position < 0:
                self.current_position = self.max_idx
        elif direction == "right":
            self.current_position += 1
            if self.current_position > self.max_idx:
                self.current_position = 0

        return self.ordered_images[model][self.current_position]


class WalkAroundTourAgent:
    def __init__(self, starting_image: str, model: str, pause_between_steps: float, pause_been_stages: float):
        self.walkaround_tracker = CarModelWalkaroundTracker()
        self.current_image = self.starting_image = starting_image
        self.is_last_step = False
        self.pause_between_steps = pause_between_steps
        self.pause_between_stages = pause_been_stages
        self.model = model

    async def do_tour(self):
        if not self.is_last_step:
            self.current_image = self.walkaround_tracker.rotate_image(
                direction="left", model=self.model, current_image=self.current_image
            )

            if self.current_image == self.starting_image:
                self.is_last_step = True

            await asyncio.sleep(self.pause_between_steps)
            return self.current_image

        return None


class ImageViewingIntent(BaseModel):

    model_of_interest: Literal["Audi A3", "Audi A6", "Audi Q3", "Audi A1", "Audi Q6"] = Field(
        description="The car model the user is interested in or asking questions about."
    )

    asked_for_image: Optional[bool] = Field(
        None,
        description=(
            "Whether the user has explicitly asked the assistant to show them a view of the car or a part of the car."
        ),
    )

    viewing_interest: Optional[Literal["exterior", "interior", "side", "front", "back", "trunk", "dashboard"]] = Field(
        None, description="The view of the car or the part of the car the customer has explicitly asked to be shown."
    )

    # color_of_interest: Optional[Literal["red", "blue", "black", "white", "silver", "grey", "green", "yellow"]] = Field(
    #     None, description="The color of the car the customer has explicitly asked to be shown."
    # )


class ImageIntentTracker(StructuredOutputAgent):

    def __init__(self):
        sys_prompt = trim_prompt(
            """You are given lines of a dialogue between the user and the assistant.
            Your task is to determine if the customer has explicitly asked be be shown a view of the car of a part of a car.
            If the customer has asked to be shown something, you will determine the following from the dialog:
            * What is the model of the car the customer is interested in?
            * Which view or which part of the car does the customer want to be shown?
            In a longer dialog, or if the user speaks about several cars or several things to view, 
            focus on the recent lines of the dialog to determine the customer's intent.
            """
        )
        super().__init__(
            model=CONFIG.language_model_config.model_deployment_name["mini"],
            response_format=ImageViewingIntent,
            openai_async_client=CONFIG.language_model_config.client["text"],
            system_prompt=sys_prompt,
        )
        self.dialog = []

    def _append_to_dialog(self, dialog: dict[str, dict[str, str]]):
        assert len(dialog) >= 2
        self.dialog.append(f"{dialog[-2]['role']}: {dialog[-2]['content']}")
        self.dialog.append(f"{dialog[-1]['role']}: {dialog[-1]['content']}")

    def _get_dialog(self, dialog: dict[str, dict[str, str]]) -> str:
        self._append_to_dialog(dialog)
        return "\n".join(self.dialog)

    async def extract_output(self, dialog: dict[str, dict[str, str]]) -> ImageViewingIntent:
        dialog = self._get_dialog(dialog)

        logging.info(LogAi(f"Extracting image viewing intent details from dialog: {dialog}"))
        output = await self.extract_with_structured_output(dialog)
        return output


class ImageLookupAgent:
    """
    Class that looks up an image using keywords extracted from the dialog.
    """

    def __init__(self):
        self.previous_image = None
        self.selection_agent = GeneralAgentAsync(
            system_prompt="",
            model=CONFIG.language_model_config.model_deployment_name["mini"],
            async_openai_client=CONFIG.language_model_config.client["text"],
            timeout=CONFIG.llm_call_timeout,
        )

    async def image_lookup(self, dialog: dict[str, str], car_model: str = "Audi A6"):

        chosen_model = car_model.replace("Audi ", "")

        prompt = trim_prompt(
            f"""Below you see a list of images. Based on the user's request, I want you to choose an image that best suits
            the user's request. If the user has looked at a previous image, keep this in mind in your selection if, for example, they
            ask for a change in angle. 

            IMAGES: {WALKAROUND_IMAGE_FILES.get(chosen_model, "No images found for the selected model.")}

            PREVIOUS_IMAGE: {self.previous_image}

            PREVIOUS_ASSISTANT_MESSAGE: {dialog[-2]['content']}
            USER_REQUEST: {dialog[-1]['content']}

            Please return ONLY the name of the image the user is likely to be interested in.
            """
        )

        self.selection_agent.system_prompt = (
            "Your role is to select an image given an assistant message and user request."
        )

        selected_image = await self.selection_agent(user_prompt=prompt)
        self.previous_image = selected_image
        return selected_image


class ImageIntentAgent(VoiceAgent):

    def __init__(self, image_name: str, uses_web_interface: bool = False):

        if uses_web_interface:
            sys_prompt = trim_prompt(
                f"""
                You only have images of the following models in your database: Audi A1, Audi A3, Audi A6, Audi Q3, Audi Q6.

                You are showing this image to a customer of a car they are interested in - {image_name}. You must ONLY say
                to them 'here is the ...' referring to the angle. DO NOT mention the model (e.g. A1, A3). 
                DO NOT say anything else! DO NOT ask if they want any more information about the car! 
                Never mention the exact name of the image file.
                """
            )

        else:
            sys_prompt = trim_prompt(
                f"""You are a professional, friendly car salesman for Audi. You have deep technical expertise, 
                but also empathy for the needs of your customers. You address your customer with their first name, 
                if you know it. You formulate concisely and a bit chatty. You formulate your answer like people 
                speak face to face, and not how they write. You do not use bullet lists or numbered lists in your answers.

                You only have images of the following models in your database: Audi A1, Audi A3, Audi A6, Audi Q3, Audi Q6.

                You are showing this image to a customer of a car they are interested in - {image_name}. You must only say
                to them 'here is the ...' and ask if they would like to see another image or to know more about the car.
                Never mention the exact name of the image file.
                """
            )

        self.original_system_prompt = sys_prompt

        super().__init__(
            name="ImageIntentAgent",
            default_system_message=sys_prompt,
            temperature=1.0,
            async_openai_client=CONFIG.language_model_config.client["audio"],
            model=CONFIG.language_model_config.model_deployment_name["audio"],
        )

    def update_system_prompt(self, additional_text: str):
        self.default_system_message += additional_text

    def reset_system_prompt(self):
        if self.default_system_message != self.original_system_prompt:
            self.default_system_message = self.original_system_prompt


class CarTourAgent(VoiceAgent):

    def __init__(self, model_name: str, user_profile: str):

        sys_prompt = trim_prompt(
            f"""You are giving the customer a tour of the Audi {model_name}. You are going around the car in 
            the following order front, right side, rear, trunk, left side. You will say ONLY the following:
            Here is the front of the {model_name}, here is the right side, here is the rear here is the trunk, here is the left side
            and here is the dashboard. DO NOT compare the left side to the right side!!!
            You can slightly adjust how you describe each view to suit the user's profile shown here: 
            user's profile: {user_profile}.
            But you must be concise! You will ask the customer if they would like to see a specific angle of the car.
            """
        )

        self.original_system_prompt = sys_prompt

        super().__init__(
            name="CarTourAgent",
            default_system_message=sys_prompt,
            temperature=1.0,
            async_openai_client=CONFIG.language_model_config.client["audio"],
            model=CONFIG.language_model_config.model_deployment_name["audio"],
        )


async def test():

    user_lines = [
        "Can you show me the trunk?",
        "Lets see the interior.",
        "Lets look at the back.",
        "Let's see the dashboard.",
        "What does it look like from the side?",
        "What does it look like from the back?",
        "Show me the dashboard.",
        "Can you show me the interior?",
        "What does it look like inside?",
        "Show me a front view!",
        "Whats the dashboard like?",
        "What does the interior look like?",
        "Can you show me the exterior?",
        "What does it look like from the front?",
        "Show me a side view.",
        "Can you show me the backseat?",
        "What engines are available?",
        "What is the size of the trunk?",
        "Whats the top speed?",
        "How many seats does it have?",
        "Is there a hybrid version?",
    ]

    def gen_dialog():
        base_dialog = [
            {"role": "assistant", "content": "Hello, how can I help you today?"},
            {"role": "user", "content": "I'm interested in the Audi A6."},
            {"role": "assistant", "content": "Great choice! What would you like to know about the Audi A6?"},
            {"role": "user", "content": "Is it a good car for families?"},
            {
                "role": "assistant",
                "content": "Yes, it's a great family car. It has plenty of space and safety features.",
            },
            {"role": "user", "content": "Does it have iso-fix points?"},
            {"role": "assistant", "content": "Yes, the car has iso-fix points for child seats."},
        ]
        for line in user_lines:
            yield base_dialog + [{"role": "user", "content": line}]

    for dialog in gen_dialog():
        selected_image = await ImageLookupAgent().image_lookup(dialog=dialog, car_model="Audi A6")
        level2_chatbot = ImageIntentAgent(image_name=selected_image)
        l2_response = await level2_chatbot.dialog_step(dialog=dialog)

        image_path = f"audi/car_views/{selected_image}"
        message = server_messages.ShowImage(image=image_path)
        l2_response.add_web_element_message(message)
        print(l2_response)


if __name__ == "__main__":
    asyncio.run(test())
