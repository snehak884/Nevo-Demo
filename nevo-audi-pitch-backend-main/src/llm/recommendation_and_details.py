import asyncio
import logging
import os
import re
from typing import Literal

from pydantic import BaseModel, Field

import llm.data as data
import llm.messages as server_messages
from nevo_framework.config.master_config import load_json_config
from nevo_framework.helpers.logging_helpers import LogAi
from nevo_framework.llm.agents import GeneralAgentAsync, StructuredOutputAgent, VoiceAgent
from llm.constants import (
    AUDI_MODEL_DATA_FILE,
    AUDI_MODEL_VECTOR_INDEX_PATH,
    SAFETY_FEATURE_VECTOR_INDEX_PATH,
    SAFETY_FEATURES_DATA_FILE,
)
from nevo_framework.llm.llm_tools import TimedWebElementMessage, rewrite_query, trim_prompt
from vectordb.vectordb_audi import EmbeddingComputer, VectorDB

CONFIG = load_json_config()


class RecommendationsWithImages(BaseModel):

    recommended_cars: list[Literal["Audi A3", "Audi A6", "Audi Q3", "Audi A1", "Audi Q6"]]
    reason_for_recommendations: str
    image_message: server_messages.ShowImage


class UserModelChoice(BaseModel):

    user_selected_model: Literal["Audi A3", "Audi A6", "Audi Q3", "Audi A1", "Audi Q6"] = Field(
        description=(
            "The model of Audi that the user is currently interested in, talking or requesting more information about. "
            "If several models are discussed, you must choose the model that the user and the salesman have been "
            "discussing about most recently in the dialog."
        )
    )


class UserModelChoiceSelector(StructuredOutputAgent):

    def __init__(self, steps_back: int = 20):
        system_prompt = trim_prompt(
            """You are a helpful assistant, tasked with analyzing a dialog between a car salesman and a customer
            and extrating information from it."""
        )
        self.steps_back = steps_back
        # gpt-4o-mini does not get references like "can I see the trunk of the other car you mentioned?"
        super().__init__(
            model=CONFIG.language_model_config.model_deployment_name["standard"],
            response_format=UserModelChoice,
            openai_async_client=CONFIG.language_model_config.client["text"],
            system_prompt=system_prompt,
        )

    def _get_dialog(self, dialog: list[str, dict[str, str]]) -> str:
        # we dont track our own dialog. just taking the last n messages from the "big one"
        start = max(0, len(dialog) - self.steps_back)
        role_map = {"assistant": "Salesman", "user": "Customer"}
        return "\n".join(
            [f"{role_map[dialog[i]['role']]}: {dialog[i]['content'].strip()}" for i in range(start, len(dialog))]
        )

    async def extract_output(self, dialog: list[str, dict[str, str]]):
        dialog_context = self._get_dialog(dialog)
        prompt = trim_prompt(
            f"""Below you are given part of a dialog between a car salesman and a customer.
            The user is talking or asking about features relating to a specific model of Audi. 
            Your task is to determine which car model the user is currently interested in
            or asking about, taking into account the context of the dialog. If the discuss several models, 
            you must choose the model that the user user and the salesman have been discussing about most recently
            in the dialog. 

            DIALOG:

            {dialog_context}
            """
        )
        output = await self.extract_with_structured_output(prompt)
        return output


class ConversationRoutes(BaseModel):

    conversation_topic: Literal[
        "car_model_comparison",
        "car_model_details",
        "test_drive",
        "image_intent",
        "driver_assistance_features",
        "tour_of_car",
    ] = Field(
        description=(
            """The intent of the user in the current situation of the conversation.

            * "car_model_details" - The customer wants more detailed information about a single specific car model.

            * "image_intent" - The customer wants to see an image of a car or part thereof. Examples of typical phrases are 
                "can you show me...?" or "can I see...?", or "show me...", or "what does X look like?", or "can we look at...".

            * "test_drive" - The customer expresses interest in booking a test drive.

            * "car_model_comparison" - The customer is interested in comparing different car models, or they ask to change something
                about the current recommendation because it does not fit their needs yet or they ask you to make a recommendation.

            * "driver_assistance_features" - The customer is interested specifically in safety assist features, like drive assist, park assist and
            safety assist. This is NOT the correct choice for other features like infotainment, speed and interior etc.

            * "tour_of_car" - the customer is interested in having a visual tour of the car; this is NOT the right choice if they want to 
            see a specific part of the car, like the trunk or the dashboard.
            """
        ),
        default="car_model_comparison",
    )


class ConversationRouter(StructuredOutputAgent):

    def __init__(self):
        system_prompt = trim_prompt(
            """You are given lines of a dialogue between a customer (USER) and a car dealer (ASSISTANT). 
            Your goal is to determine whether the user is interested in comparing two models of cars, whether they want
            more detailed information about a single car, whether they specifically want to see an image of the car or 
            part there of, whether they want a tour of the car or whether they are interested in a test drive.
            """
        )
        system_prompt = trim_prompt(
            """You are given lines of a dialogue between a customer (USER) and a car dealer (ASSISTANT). 
            Your goal is to determine the intent of the customer in the current situation of the conversation.
            There are six options:

            * The customer wants more detailed information about a single specific car model.

            * The customer wants to see an image of a car or part thereof. Typical phrases are "can you show me...?"
              or "can I see...?", or "show me...", or "what does X look like?", or "can we look at...".

            * The customer expresses interest in booking a test drive.

            * The customer is interested in comparing different car models, or they ask to change something about the
              current recommendation because it does not fit their needs yet.

            * The customer wants to know more about the driver assistance features of the car, like drive assist, park assist and 
            safety assist.

            * The customer would like a tour of the car
            """
        )
        self.dialog = []

        super().__init__(
            model=CONFIG.language_model_config.model_deployment_name["mini"],
            response_format=ConversationRoutes,
            openai_async_client=CONFIG.language_model_config.client["text"],
            system_prompt=system_prompt,
        )

    def _append_to_dialog(self, dialog: dict[str, dict[str, str]]):
        if len(dialog) >= 2:
            self.dialog.append(f"{dialog[-2]['role']}: {dialog[-2]['content']}")
            self.dialog.append(f"{dialog[-1]['role']}: {dialog[-1]['content']}")

    def _get_dialog(self, dialog: dict[str, dict[str, str]]) -> str:
        self._append_to_dialog(dialog)
        return "\n".join(self.dialog)

    async def extract_output(self, dialog: dict[str, dict[str, str]]):
        dialog = self._get_dialog(dialog)
        output = await self.extract_with_structured_output(dialog)
        return output


class CarRecommendationAgent(VoiceAgent):
    def __init__(self, user_profile: str):

        SYS_PROMPT = trim_prompt(
            f"""You are a professional, friendly car salesman. You have deep technical expertise, 
            but also empathy for the needs of your customers. You address your customer with their first name, 
            if you know it. You formulate concisely and a bit chatty. You formulate your answer like people 
            speak face to face, and not how they write. You do not use bullet lists or numbered lists in your answers.
            
            Below under CUSTOMER PROFILE you find a profile of a customer who is interested in buying a car. 
            You MUST ALWAYS choose EXACTLY TWO of these models and you must recommend and compare for the customer. 
            Please give a short explanation why you recommend these two models for this specific customer, addressing the
            customer's needs from the profile. You may anticipate other needs the customer might have based on the profile, 
            and highlight why the cars you recommend are a great fit.

            You address the customer directly as if you were speaking with him or her.

            After giving the recommendation, you engage in a conversation with the customer.
            If the customer has questions about a vehicle, you answer them. 
            If the customer tells you more about their needs or preferences, you take that into account in your conversation 
            and adjust your recommendation if necessary. Only adjust your recommendation if you really think
            it is necessary based on the new information you get from the customer.

            CUSTOMER PROFILE

            {user_profile}
            
            CAR BRIEFINGS

            {data.get_car_briefings_without_differentiators()}

            PLEASE BE AS CONCISE AS POSSIBLE. You MUST start your first sentence by mentioning the names of the two models you 
            will compare and recommend! You MUST ALWAYS DISCUSS TWO MODELS and mention both of these in your first sentence. You must
            only have conversations relating to the Audi models A3, A6, Q3, A1, and Q6. You must not mention any other car models in your
            conversation and you must NEVER talk to the customer about any other topics, especially life advice or coding.
            """
        )

        super().__init__(
            name="CarRecommendationAgent",
            default_system_message=SYS_PROMPT,
            async_openai_client=CONFIG.language_model_config.client["audio"],
            model=CONFIG.language_model_config.model_deployment_name["audio"],
        )


class CarDetailAgent(VoiceAgent):

    def __init__(self):
        if os.path.exists(AUDI_MODEL_VECTOR_INDEX_PATH):
            self.vectordb = VectorDB.load_from_disk(AUDI_MODEL_VECTOR_INDEX_PATH)
        else:
            embedding_computer = EmbeddingComputer(model="text-embedding-3-small")
            self.vectordb = VectorDB(AUDI_MODEL_DATA_FILE, embedding_computer=embedding_computer)
            self.vectordb.store_to_disk(AUDI_MODEL_VECTOR_INDEX_PATH)

        super().__init__(
            name="CarDetailAgent",
            default_system_message=None,
            async_openai_client=CONFIG.language_model_config.client["audio"],
            model=CONFIG.language_model_config.model_deployment_name["audio"],
        )

    async def rag_lookup(self, dialog: list[dict[str, str]], car_model: str = "Audi A6"):
        rewritten_query = await rewrite_query(dialog)
        results = self.vectordb.search_with_query(rewritten_query, car_model=car_model)
        rag_information = ""
        for doc, _ in results:
            rag_information += doc.response + "\n\n"

        SYS_PROMPT = trim_prompt(
            f"""You are a professional, friendly car salesman for Audi. You have deep technical expertise, 
            but also empathy for the needs of your customers. You address your customer with their first name, 
            if you know it. You formulate concisely and a bit chatty. You formulate your answer like people 
            speak face to face, and not how they write. You do not use bullet lists or numbered lists in your answers.

            Below you are presented with information on a specific model. Please use this information and ONLY this information
            to answer the user's query. If the relevant information isn't given here to answer the user's query DO NOT make
            anything up - tell the user that you don't have the information to answer these question.

            You must not mention any other car brands besides Audi in your conversation and you 
            must NEVER talk to the customer about any other topics, especially life advice or coding.

            Please make your answer to the user's query as concise as possible using at most two sentences. NEVER use bullet points
            in your answer.

            INFORMATION:

            {rag_information}
            """
        )

        self.default_system_message = SYS_PROMPT


class SafetyFeatureAgent(VoiceAgent):

    def __init__(self):
        self.dialog = []
        self.selected_rag_docs = []
        self.rag_information = ""

        if os.path.exists(SAFETY_FEATURE_VECTOR_INDEX_PATH):
            self.vectordb = VectorDB.load_from_disk(SAFETY_FEATURE_VECTOR_INDEX_PATH)
        else:
            embedding_computer = EmbeddingComputer(model="text-embedding-3-small")
            self.vectordb = VectorDB(SAFETY_FEATURES_DATA_FILE, embedding_computer=embedding_computer)
            self.vectordb.store_to_disk(SAFETY_FEATURE_VECTOR_INDEX_PATH)

        super().__init__(
            name="SafetyFeatureAgent",
            default_system_message=None,
            async_openai_client=CONFIG.language_model_config.client["audio"],
            model=CONFIG.language_model_config.model_deployment_name["audio"],
        )

    async def rag_lookup(self, dialog: list[dict[str, str]]):

        rag_information = ""
        retrieved_documents = []

        rewritten_query = await rewrite_query(dialog)
        results = self.vectordb.search_with_query(rewritten_query)

        for i, (doc, _) in enumerate(results):
            rag_information += f"{i} - " + doc.response + "\n\n"
            retrieved_documents.append(doc)

        self.selected_rag_docs = retrieved_documents
        self.rag_information = rag_information

        SYS_PROMPT = trim_prompt(
            f"""You are a professional, friendly car salesman for Audi. You have deep technical expertise, 
            but also empathy for the needs of your customers. You address your customer with their first name, 
            if you know it. You formulate concisely and a bit chatty. You formulate your answer like people 
            speak face to face, and not how they write. You do not use bullet lists or numbered lists in your answers.

            Below you are presented with information regarding general safety features of Audi vehicles. 
            Please use this information and ONLY this information to answer the user's query. If the relevant 
            information isn't given here to answer the user's query DO NOT make anything up - tell the user 
            that you don't have the information to answer these question.

            You must not mention any other car brands besides Audi in your conversation and 
            you must NEVER talk to the customer about any other topics, especially life advice or coding.

            Please make your answer to the user's query as concise as possible using AT MOST two sentences. NEVER use bullet points
            in your answer. 

            INFORMATION:

            {rag_information}

            Only choose ONE safety feature to talk about at a time.
            """
        )

        self.default_system_message = SYS_PROMPT

    def _append_to_dialog(self, dialog: dict[str, dict[str, str]]):
        if len(dialog) >= 2:
            self.dialog.append(f"{dialog[-2]['role']}: {dialog[-2]['content']}")
            self.dialog.append(f"{dialog[-1]['role']}: {dialog[-1]['content']}")
        # Limit the length of the dialog to the last 6 messages
        if len(self.dialog) > 6:
            self.dialog = self.dialog[-6:]

    def _get_dialog(self, dialog: dict[str, dict[str, str]]) -> str:
        self._append_to_dialog(dialog)
        return "\n".join(self.dialog)


class ImageFromResponse:
    def __init__(self, rag_information: str, selected_rag_docs: list):
        self.rag_information = rag_information
        self.selected_rag_docs = selected_rag_docs

    async def sentence_callback(self, sentence: str, sentences: list[str], output_queue: asyncio.Queue) -> bool:
        system_prompt = trim_prompt(
            """Based on the list of descriptions below, indicated by DESCRIPTIONS and the response of the Assistant indicated by 
            ASSISTANT, you must select the index of the safety feature that best matches the ASSISTANT response. You must return the
            ONLY index of this description as an integer! Please return -1 if none of the descriptions are suitable matches for 
            the assistant's response.
            """
        )

        user_prompt = trim_prompt(
            f"""
            DESCRIPTIONS:
            {self.rag_information}

            ASSISTANT:
            {sentence}
            """
        )

        image_selection_agent = GeneralAgentAsync(
            system_prompt=system_prompt,
            model=CONFIG.language_model_config.model_deployment_name["mini"],
            async_openai_client=CONFIG.language_model_config.client["text"],
        )
        response = await image_selection_agent(user_prompt=user_prompt)

        if isinstance(response, str) and response.lstrip("-").isdigit():
            response = int(response)
            if response >= 0:
                logging.info(LogAi(f"IDX: {response}; SELECTED IMAGE: {self.selected_rag_docs[response].images[0]}"))
                output_queue.put_nowait(
                    server_messages.ShowImage(
                        image="audi/safety_features/" + self.selected_rag_docs[response].images[0]
                    )
                )
                return False
            else:
                logging.info(LogAi(f"IDX: {response}; Returning none"))
                return True

    async def extract_data(self, bot_response: str) -> server_messages.ShowImage:
        raise DeprecationWarning()
        system_prompt = trim_prompt(
            """Based on the list of descriptions below, indicated by DESCRIPTIONS and the response of the Assistant indicated by 
            ASSISTANT, you must select the index of the safety feature that best matches the ASSISTANT response. You must return the
            ONLY index of this description as an integer! Please return -1 if none of the descriptions are suitable matches for 
            the assistant's response.
            """
        )

        user_prompt = trim_prompt(
            f"""
            DESCRIPTIONS:
            {self.rag_information}

            ASSISTANT:
            {bot_response}
            """
        )

        image_selection_agent = GeneralAgentAsync(
            system_prompt=system_prompt,
            model=CONFIG.language_model_config.model_deployment_name["mini"],
            async_openai_client=CONFIG.language_model_config.client["text"],
        )
        response = await image_selection_agent(user_prompt=user_prompt)

        if isinstance(response, str) and response.lstrip("-").isdigit():
            response = int(response)
            if response >= 0:
                print(f"IDX: {response}; SELECTED IMAGE: {self.selected_rag_docs[response].images[0]}")
                return [
                    server_messages.ShowImage(
                        image="audi/safety_features/" + self.selected_rag_docs[response].images[0]
                    )
                ]
            else:
                print(f"IDX: {response}; Returning none")
                return None


class KeywordExtractor:
    def __init__(
        self,
        pattern: str = r"\b(A1|A3|A6|Q3|Q6|a1|a3|a6|q3|q6)\b",
        base_image_path: str = "audi/car_views/Walkaround_{model}_front_left_square.jpeg",
    ):
        """
        Args:
            pattern (str): The regex pattern to match keywords in the bot response.
            base_image_path (str): The base path (format) for the images
        """
        self.images_paths = []
        self.matches: list[str] = []
        self.pattern = re.compile(pattern)
        self.base_image_path = base_image_path

    async def sentence_callback(
        self,
        sentence: str,
        sentences: list[str],
        output_queue: asyncio.Queue,
    ) -> bool:
        """
        Calls self.maybe_create_image_message, but this method is for use with the stream watching system.
        """
        if image_message := self.maybe_create_image_message(sentence):
            output_queue.put_nowait(image_message)
            return False
        else:
            return True

    def maybe_create_image_message(self, bot_response: str) -> server_messages.ShowImage | None:
        """
        Creates a ShowImage message for the car comparison view if the bot response contains keywords that matches the pattern.

        Args:
            bot_response (str): a phrase from the LLM that has been pre-split based on a set of splitting characters (e.g. ',', '.'...)
        """
        self.matches = list(set(self.pattern.findall(bot_response)))
        if self.matches:
            # Prevents the keyword matcher from matching more cars than a set number
            if len(self.matches) > CONFIG.max_keyword_matches:
                self.matches = self.matches[: CONFIG.max_keyword_matches]

            image_paths = [self.base_image_path.format(model=match) for match in self.matches]
            return server_messages.ShowImage(
                image=image_paths[0],
                image2=image_paths[1] if len(image_paths) > 1 else None,
                layout_hint="compare",
            )
        else:
            return None


class TourKeywordExtractor:
    def __init__(
        self,
        keywords: list[str] = None,
        base_image_path: str = "audi/car_views/Walkaround_{model}",
    ):
        """
        Args:
            keywords list[str]: Keywords to look up for adding images to the queue
            base_image_path (str): The base path (format) for the images
            time_coefficient (float): The coefficient to calculate the time delta based on the length of the bot response.
            time_offset (float): The offset to add to the time delta.
        """

        self.images_paths = []
        self.keywords: list[str] = keywords
        self.base_image_path = base_image_path
        # Coefficients from timing analysis of characters -> length of talking
        self.time_coefficient = CONFIG.voice_timing_coefficient
        self.time_offset = CONFIG.voice_timing_offset
        self.car_model = None

    async def sentence_callback(
        self,
        sentence: str,
        sentences: list[str],
        output_queue: asyncio.Queue,
    ) -> bool:
        """
        Calls self.maybe_create_image_message, but this method is for use with the stream watching system.
          Args:
            sentence (str): a phrase from the LLM that has been pre-split based on a set of splitting characters (e.g. ',', '.'...)
            sentences (list[str]): The entirety of the bot's response so far; used here to calculate the time delta
            output_queue (asyncio.Queue): The queue to put the image message into

        Returns:
            True - this is because this callback continues to examine the input queue, even if it has already found a match;
            i.e. it can add multiple images to the output queue

        """
        if image_messages := self.maybe_create_image_message(bot_response=sentence, bot_responses=sentences):
            for message in image_messages:
                output_queue.put_nowait(message)

        return True

    def maybe_create_image_message(
        self, bot_response: str, bot_responses: list[str]
    ) -> list[TimedWebElementMessage] | None:
        """
        Creates a ShowImage message for the car comparison view if the bot response contains keywords that matches the pattern.

        Args:
            bot_response (str): a phrase from the LLM that has been pre-split based on a set of splitting characters (e.g. ',', '.'...)
            bot_responses (list[str]): The entirety of the bot's response so far; used here to calculate the time delta

        Returns:
            list[TimedWebElementMessage]: A list of ShowImage messages with time deltas for each image; allows for adding
            multiple images to the queue at once, but with time delays that enable them to be displayed sequentially.
        """
        # TODO: These lookups should probably be in a constants file
        # Primary images to look up based on the keyword
        image_lookup = {
            "front": self.base_image_path + "_front.jpeg",
            "back": self.base_image_path + "_rear.jpeg",
            "rear": self.base_image_path + "_rear.jpeg",
            "trunk": self.base_image_path + "_trunk_open.jpeg",
            "left": self.base_image_path + "_side_left.jpeg",
            "right": self.base_image_path + "_side_right.jpeg",
            "dashboard": self.base_image_path + "_dashboard.jpeg",
        }

        keywords = set(self.keywords.copy())
        prefix = None
        matched_keyword = None
        for keyword in keywords:
            location = bot_response.find(keyword)
            if location != -1:
                prefix = bot_response[:location]
                matched_keyword = keyword
                # remove "used" keyword from the set as sometimes it will say " from front to back" or so, and it will show the front again
                keywords.remove(keyword)
                break
        if prefix:
            # Is bot_response part of bot_responses? YES! I verified.
            # Using "".join() and not " ".join() since whitespace and separtors are no longer removed from the strings
            num_characters = len("".join(bot_responses[:-1])) + len(prefix)
            time_delta = num_characters * self.time_coefficient + self.time_offset
            return [
                TimedWebElementMessage(
                    time_delta=time_delta,
                    message=server_messages.ShowImage(
                        image=image_lookup[matched_keyword].format(model=self.car_model), layout_hint="walkaround"
                    ),
                )
            ]
        else:
            return None

    def reset(self):
        self.matches = []
        self.car_model = None
