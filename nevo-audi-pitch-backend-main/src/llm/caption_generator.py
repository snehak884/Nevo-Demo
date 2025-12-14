import logging
from typing import Literal

import markdown
from pydantic import BaseModel, Field

from nevo_framework.config.master_config import load_json_config
from nevo_framework.helpers.logging_helpers import LogAi
from nevo_framework.llm.agents import StructuredOutputAgent, VoiceAgentResponse
from llm.recommendation_and_details import KeywordExtractor
from nevo_framework.llm.llm_tools import trim_prompt

"""
A StructuredOutputAgent that creates very concise summaries of the recommendations to use as captions
for the images of the cars in the frontend. Requires the "long" spoken version of the recommendation as input.
"""

CONFIG = load_json_config()


class RecommendationCaptionDouble(BaseModel):

    car_model_1: Literal["Audi A3", "Audi A6", "Audi Q3", "Audi A1", "Audi Q6"] = Field(
        description="The first recommended car model."
    )
    car_1_summary: str = Field(description="The summary of the recommendation for the first recommended car.")

    car_model_2: Literal["Audi A3", "Audi A6", "Audi Q3", "Audi A1", "Audi Q6"] = Field(
        description="The second recommended car model."
    )
    car_2_summary: str = Field(description="The summary of the recommendation for the second recommended car.")


class RecommendationCaptionSingle(BaseModel):

    car_model: Literal["Audi A3", "Audi A6", "Audi Q3", "Audi A1", "Audi Q6"] = Field(
        description="The recommended car model."
    )
    car_summary: str = Field(description="The summary of the recommendation for the recommended car.")


class RecommendationCaptionAgent(StructuredOutputAgent):

    def __init__(self, num_captions: Literal[1, 2] = 2):

        # Prevents a crash from the
        if num_captions > 2:
            num_captions = 2

        system_prompt = {
            1: trim_prompt(
                """You are given a car recommendation which was given to a customer by a salesman. 
            The salesman recommends one car model and gives reasons for the recommendation. 
            I want you to summarize the recommendation of the car into three short bullet points 
            with short sentences. The summary is highly concise and should fit on a napkin. 
            Use markdown bullet list notation in the summary.
            """
            ),
            2: trim_prompt(
                """You are given a car recommendation which was given to a customer by a salesman. 
            The salesman recommends two different car models and gives reasons for the recommendation. 
            I want you to summarize the recommendation of each car into three short bullet points 
            with short sentences. The summaries are highly concise and should fit on a napkin. 
            Use markdown bullet list notation in the summaries.
            """
            ),
        }

        response_format = {
            1: RecommendationCaptionSingle,
            2: RecommendationCaptionDouble,
        }

        super().__init__(
            model=CONFIG.language_model_config.model_deployment_name["standard"],
            system_prompt=system_prompt[num_captions],
            response_format=response_format[num_captions],
            openai_async_client=CONFIG.language_model_config.client["text"],
        )


def _extend_and_convert(car_model: str, markdown_summary: str) -> str:
    """Add the car model to the summary as a bold title and convert the markdown to HTML."""
    return markdown.markdown(f"**{car_model}**\n\n{markdown_summary}")


async def add_recommendation_captions(
    l2_response: VoiceAgentResponse,
) -> VoiceAgentResponse:
    """
    Creates a short 3 bullet summary why of each of the two cars is recommmended,
    based on the (long) answer given by the recommendation agent.
    The summary is added to the ImageMessage so the frontend can display it under the images.
    """

    keyword_extractor = KeywordExtractor()
    # use the keyword extractor to extract the image names. This should work because this is how we extract the
    # images onto the queue in the first place
    image_msg_with_summaries = keyword_extractor.maybe_create_image_message(bot_response=l2_response.text)

    if keyword_extractor.matches:
        matches = keyword_extractor.matches
        recommendation_caption_agent = RecommendationCaptionAgent(num_captions=len(matches))
    else:
        return l2_response

    # TODO keep this constant or update it frequently?
    recommendation_caption: RecommendationCaptionSingle | RecommendationCaptionDouble = (
        await recommendation_caption_agent.extract_with_structured_output(l2_response.text)
    )

    if recommendation_caption:
        if image_msg_with_summaries is None:
            return l2_response

        if len(matches) == 1:
            caption = _extend_and_convert(recommendation_caption.car_model, recommendation_caption.car_summary)
            image_msg_with_summaries.text = caption
        elif len(matches) == 2:
            caption_1 = _extend_and_convert(recommendation_caption.car_model_1, recommendation_caption.car_1_summary)
            caption_2 = _extend_and_convert(recommendation_caption.car_model_2, recommendation_caption.car_2_summary)

            if keyword_extractor.matches[0] in recommendation_caption.car_model_1:
                image_msg_with_summaries.text = caption_1
                image_msg_with_summaries.text2 = caption_2
            else:
                image_msg_with_summaries.text = caption_2
                image_msg_with_summaries.text2 = caption_1
        logging.info(LogAi(f"Recommendation summary for image captions: {recommendation_caption}"))
        l2_response.add_web_element_message(image_msg_with_summaries)
        return l2_response
    else:
        # if summary extraction failed somehow, just log it and return the response as is
        logging.warning(LogAi(f"Failed to extract recommendation captions from response: {l2_response.text}"))
        return l2_response
