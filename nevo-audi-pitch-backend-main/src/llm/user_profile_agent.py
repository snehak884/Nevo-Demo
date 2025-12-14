import logging

import openai

from nevo_framework.llm.agents import VoiceAgent
from llm import data
from nevo_framework.llm.llm_tools import trim_prompt
from nevo_framework.config.master_config import load_json_config
from nevo_framework.helpers.logging_helpers import LogAi


"""
A set of agents and one-off functions to handle the user profile collection and summarization.
The UserProfileVoiceAgent has a conversation with the user to understand their needs and circumstances
for a car purchase. The summarize_user_profile function summarizes the user profile from the dialogue,
which is then used by another set of agents to recommend a car.

A function call is used in the UserProfileVoiceAgent to check whether all required information has been 
collected. If so, the orchestator can switch to the next stage and proceed with the car recommendation.
"""


CONFIG = load_json_config()

class UserProfileVoiceAgent(VoiceAgent):

    def __init__(self):
        system_prompt = trim_prompt(
            f"""You are an expert car salesman named {data.ASSISTANT_NAME}. You approach a customer in a friendly and chatty way, but also proactively.
            In order to recommend the best vehicle you MUST learn the following things about the customer you are talking to:

            * What is the customers first name? This is the first thing you must ask for.
            
            * In what kind of area do they live? Examples are city, suburbs, small town, countryside.
            
            * Do they have a family? If yes, how large is it?
            
            * What will be the main uses for the car? Examples are commuting, running errands, business trips, long road trips.
            
            * What is important about a car for them? For example, speed and performance, safety, comfort, aesthetics, etc.
            
            In your conversation you politely insist on having these questions answered before starting to recommend a vehicle. 
            You are polite and chatty but you work relentlessly to collecting all the information listed above.  As soon as you 
            learned the customer's name you use it frequently to address them. Once you have ALL QUESTIONS answered, you tell 
            the customer that you are ready to recommend a car. But you DO NOT give an actual recommendation.
            
            DO NOT ask more than one question at once. Do not ask for any information not listed above. Do not ask for the
            same thing twice. If the user has already mentioned what is most important to them in a car, don't ask them again!
             
            The first thing you do is introduce yourself and tell the customer that you will ask a few questions to recommend the best car for them. 
            Let them know they can also load info from a previous conversation if they share their email address. Then ask your first question.
            
            If you cannot find the user's details with their email address, then you must tell them and continue gathering information about them.
            """
        )
        all_info_collected_function = {
            "type": "function",
            "function": {
                "name": "customer_profile_collected",
                "description": (
                    "The function is to be called if and only if all information the assistant is required "
                    "to collect has been collected. This is the customers first name, family type, location type, "
                    "main uses of the car, and what is important about a car for them."
                ),
                "parameters": {
                    "type": "object",
                    "required": ["info_collected"],
                    "properties": {
                        "info_collected": {
                            "type": "boolean",
                            "description": "Indicates whether all required information has been collected.",
                        }
                    },
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }

        user_email_address_function = {
            "type": "function",
            "function": {
                "name": "user_email_address_function",
                "description": (
                    """The function is to be called if and only if the user gives their email address
                    # Details
                    - Please ALWAYS let the user know that you are looking up their email address in the database.
                    - If their email address is not found, please inform them and continue gathering information.
                    - If you have called this function with a specific email address before, NEVER call the function with the same email address!

                    """
                ),
                "parameters": {
                    "type": "object",
                    "required": ["email_address"],
                    "properties": {
                        "email_address": {
                            "type": "string",
                            "description": "The email address provided by the user always in the form of some_indentifier@host_name.host_extension.",
                        }
                    },
                    "additionalProperties": False,
                },
            },
        }


        super().__init__(
            name="UserProfileVoiceAgent",
            default_system_message=system_prompt,
            tools=[all_info_collected_function, user_email_address_function],
            async_openai_client=CONFIG.language_model_config.client["audio"],
            model=CONFIG.language_model_config.model_deployment_name["audio"],
            temperature=0.5
        )

    def all_user_info_collected(self) -> bool:
        tool_calls = self.last_ai_response.tool_calls
        if arg_dict := tool_calls.get("customer_profile_collected", None):
            return arg_dict.get("info_collected", False)
        return False
    
    def user_email_given(self) -> str:
        tool_calls = self.last_ai_response.tool_calls
        arg_dict = tool_calls.get("user_email_address_function", {})
        logging.info(f"User email address function with args: {arg_dict}")
        return arg_dict.get("email_address", "")
        

class UserProfileAgentWithRecord(VoiceAgent):
    def __init__(self, customer_profile: str):
        system_prompt = trim_prompt(
            f"""You are an expert car salesman named {data.ASSISTANT_NAME}. You approach a customer in a friendly and chatty 
            way, but also proactively. You must say 'nice to see you again [inert name]. You have just loaded a customer profile from the 
            database. You must very briefly summarise to the customer what you know about them. You then ask them how you can help them. 
            Here is the customer profile:
            
            -----------------
            {customer_profile}
            """
        )

        super().__init__(
            name="UserProfileAgentWithRecord",
            default_system_message=system_prompt,
            async_openai_client=CONFIG.language_model_config.client["audio"],
            model=CONFIG.language_model_config.model_deployment_name["audio"],
            temperature=0.5
        )

async def summarize_user_profile(
    dialog: list[dict[str, str]],
    model: str = CONFIG.language_model_config.model_deployment_name["standard"],
    temperature: float = 0.5,
) -> str:
    """
    One-off function to summarize a user profile from the dialogue had with the User Profile Agent.

    Args:
        dialogue: The dialogue between the user and the User Profile Agent, in the usual 'assistant'... 'user'... form.
        model: The model to use for the summarization.
        temperature: The temperature to use for the summarization.

    Returns:
        The AI summary of the user profile.
    """

    dialog_str = "\n".join([f"{message['role']}: {message['content']}\n" for message in dialog])
    prompt = trim_prompt(
        f"""Below the === delimeter is a dialog between a customer (the 'user') and a car salesman (the 'assistant'). 
            You will create a user profile from the dialog which will later held an expert to recommend a car.
            You focus on customer's circumstance and their needs regarding a car.
            If the user has mentioned any specific features or requirements, make sure to include them. 
            If the user has mentioned their name, make sure to include it in the summary.
            Don't make up any information that is not included in the dialog.
            Only output the summary. Do not include the dialog. Do not make any recommendations.
            ===
            {dialog_str}"""
    )
    try:
        response = await CONFIG.language_model_config.client["text"].chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}], temperature=temperature
        )
        summary = response.choices[0].message.content
        return summary
    except Exception as e:
        logging.error(f"Error in one_shot_summary: {e}")
        # TODO might return the whole dialogue as a fallback here
        raise e


async def summarize_full_dialog(
    dialog: list[dict[str, str]],
    model: str = CONFIG.language_model_config.model_deployment_name["standard"],
    temperature: float = 0.5,
) -> str:
    """
    One-off function to summarize the entire dilague between the user and the AI.

    Args:
        dialogue: The dialogue between the user and the User Profile Agent, in the usual 'assistant'... 'user'... form.
        model: The model to use for the summarization.
        temperature: The temperature to use for the summarization.

    Returns:
        The AI summary of the user profile.
    """

    dialog_str = "\n".join([f"{message['role']}: {message['content']}\n" for message in dialog])
    prompt = trim_prompt(
        f"""Below the === delimiter is a dialog between a customer (the 'user') and a car salesman (the 'assistant'). 
            You will create a summary of the dialog. The summary should be a concise version of the dialog that captures the main 
            points discussed the customer and the salesman. It should cover everything the customer was interested in and
            everything the salesman asked about or offered.
            ===
            {dialog_str}"""
    )
    try:
        response = await CONFIG.language_model_config.client["text"].chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}], temperature=temperature
        )
        summary = response.choices[0].message.content
        return summary
    except Exception as e:
        logging.error(f"Error in summarize_full_dialog: {e}")
        # TODO might return the whole dialogue as a fallback here
        raise e


async def get_user_name(
    dialog: list[dict[str, str]],
    model: str = CONFIG.language_model_config.model_deployment_name["mini"],
    temperature: float = 0.5,
) -> str:
    """
    One-off function to get the user's name from the dialog.

    Args:
        dialogue: The dialogue between the user and the User Profile Agent, in the usual 'assistant'... 'user'... form.
        model: The model to use.
        temperature: The temperature to use.

    Returns:
        The user names.
    """

    dialog_str = "\n".join([f"{message['role']}: {message['content']}\n" for message in dialog])
    prompt = trim_prompt(
        f"""Below the === delimeter is a dialog between a customer (the 'user') and a car salesman (the 'assistant'). 
            From the dialog, extract the user's name. The user's name is likely the first thing the assistant asks for.
            DO NOT return the assistant's name.
            DO NOT return the salesman's name.
            DO NOT return any other information. Only return the user's name.
            ===
            {dialog_str}"""
    )
    try:
        response = await CONFIG.language_model_config.client["text"].chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}], temperature=temperature
        )
        name = response.choices[0].message.content
        return name
    except Exception as e:
        logging.error(f"Error in get_user_name: {e}")
        # TODO might return the whole dialogue as a fallback here
        raise e


TEST_DIALOG = [
    {
        "role": "assistant",
        "content": "Welcome to our car dealership! Would you tell me your name, please?",
    },
    {
        "role": "user",
        "content": "My name is David.",
    },
    {
        "role": "assistant",
        "content": "Nice to meet you, David! Can you tell me where you live, so I can better understand your needs for a vehicle? For example, do you live in the city, suburbs, a small town, or the countryside?",
    },
    {
        "role": "user",
        "content": "I live on the countryside, with my wife and two kids. And we have two dogs.",
    },
    {
        "role": "assistant",
        "content": "Great! How do you plan to use the car? Will it be for daily commutes, running errands, family trips, or something else?",
    },
    {
        "role": "user",
        "content": "The main use for the car will be my daily commute to the city, but I will also be driving the kids to school and soccer practice.",
    },
    {
        "role": "assistant",
        "content": "Got it! Safety is important when it comes to cars. Are there any other specific features or aspects of a car that are important to you? For example, speed and performance, comfort, aesthetics, or something else?",
    },
    {
        "role": "user",
        "content": "Safety is very important to me, but I also like a car to be fast.",
    },
]


async def test_summary():
    """
    Test function for the user profile summarization.
    """
    summary, name = await asyncio.gather(summarize_user_profile(TEST_DIALOG), get_user_name(TEST_DIALOG))

    print("SUMMARY:")
    print(summary)

    print("NAME ONLY:")
    print(name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_summary())
