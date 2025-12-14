import logging
from typing import Optional
import datetime

from pydantic import BaseModel, Field

from nevo_framework.llm.agents import VoiceAgent, StructuredOutputAgent
from llm import data
from nevo_framework.llm.llm_tools import trim_prompt
from nevo_framework.config.master_config import load_json_config
from nevo_framework.helpers.logging_helpers import LogAi

"""
Agents for handling test drive scheduling with a customer. The TestDriveVoiceAgent is a voice agent that guides the user
through the process of scheduling a test drive. The TestDriveDetailsTracker is a structured output agent that tracks the
information collected during the conversation. The TestDriveVoiceAgent can switch to a state where it asks the user to
fill out the contact and consent form, demonstrating interaction of AI with a web form.  

The TestDriveVoiceAgent can also switch to the goodbye state where it thanks the user for their interest in Audi cars 
and says goodbye. This state switch is triggered by the orchestrator when the form has been submitted and the user's
contact information and consent have been collected.
"""

CONFIG = load_json_config()

class TestDriveDetails(BaseModel):

    preferred_date: Optional[str] = Field(
        None, 
        description=(
            f"The customer's preferred date for the test drive. Today's date is " 
            f"{datetime.date.today().strftime('%Y-%m-%d')} and the current day of week is {datetime.date.today().strftime('%A')}."
        )
    )
    preferred_time: Optional[str] = Field(
        None, 
        description=(
            "The customer's preferred time of day for the test drive. If and only if the customer does not give a specific time, "
            "but gives instead the term morning, afternoon or evening, then you shouuld assume morning as 10:00, afternoon as 14:00, "
            "and evening as 18:00. "
        )
    )
    zip_code: Optional[str] = Field(None, description="The customer's zip code.")


class TestDriveDetailsTracker(StructuredOutputAgent):

    def __init__(self):
        system_prompt = trim_prompt(
            """You are given lines of a dialogue between a customer (user) and a car dealer (assistant). 
            The dealer has collected information to schedule a test drive with the customer. Your task is to track the information collected.
            """
        )
        super().__init__(
            model=CONFIG.language_model_config.model_deployment_name["mini"],
            response_format=TestDriveDetails,
            openai_async_client=CONFIG.language_model_config.client["text"],
            system_prompt=system_prompt,
        )
        self.dialog = []
        self.last_test_drive_details: TestDriveDetails = TestDriveDetails(
            preferred_date=None, preferred_time=None, zip_code=None
        )

    def append_to_dialog(self, dialog: dict[str, dict[str, str]]):
        if len(dialog) >= 2:
            assert dialog[-2]["role"] == "assistant"
            assert dialog[-1]["role"] == "user"
            self.dialog.append(f"{dialog[-2]['role']}: {dialog[-2]['content']}")
            self.dialog.append(f"{dialog[-1]['role']}: {dialog[-1]['content']}")

    def get_dialog(self) -> str:
        return "\n".join(self.dialog)

    async def extract_test_drive_details(self):
        if self.dialog:
            # only extract if we have collected some dialog
            dialog_str = self.get_dialog()
            logging.info(LogAi(f"Extracting test drive details from dialog: {dialog_str}"))
            self.last_test_drive_details = await self.extract_with_structured_output(dialog_str)

    def details_complete(self) -> bool:
        return all(
            [
                self.last_test_drive_details.preferred_date,
                self.last_test_drive_details.preferred_time,
                self.last_test_drive_details.zip_code,
            ]
        )

    def get_test_drive_details(self) -> Optional[TestDriveDetails]:
        return self.last_test_drive_details


class TestDriveVoiceAgent(VoiceAgent):

    COLLECTING_INFO = "collecting_info"
    CONTACT_AND_CONSENT_FORM = "contact_and_consent_form"
    DATA_COLLECTED_AND_GOODBYE = "data_collected"

    def __init__(self, customer_name: str, car_model: str):
        """
        Creates a voice agent for scheduling a test drive with a customer. The agent guides the user through the process
        of scheduling a test drive, asking for the user's zip code, preferred date and time for the test drive, and contact
        information. The agent can switch to a state where it asks the user to fill out the contact and consent form, and
        to a goodbye state where it thanks the user for their interest in Audi cars and says goodbye.
        
        Args:
        
        customer_name: The name of the customer who is interested in the test drive.
        car_model: The model of the car that the customer is interested in booking a test drive for.
        """
        self.state: str = self.COLLECTING_INFO
        self.contact_email: str = None
        self.contact_phone: str = None
        self.consent_given: bool = False
        self._car_model: str = car_model
        self.zip_code: str = None

        if not self.zip_code:
            zip_code_question = "* What is the customers zip code? Explain that you need this to find the nearest dealership."

        SYSTEM_PROMPT = trim_prompt(
            f"""You are an expert car salesman named {data.ASSISTANT_NAME}. You are facing a customer named {customer_name}. {customer_name} is 
            interested in the {car_model}. You have already spoken to {customer_name} about the {car_model}, and {customer_name}
            has asked all the questions they had about the {car_model}. 
            
            Your task is now to schedule a test drive with {customer_name}. You start the conversation by explaning
            that you would love to book a test drive for them and that you need to collect some information to do so.

            For this, you need to learn the following information from {customer_name}:
            {zip_code_question}
            * When would they like to schedule the test drive? 
            * What time of day would they prefer for the test drive – morning, afternoon, or evening? Do not ask for a specific time. 
            Morning, afternoon, or evening is enough.

            In your conversation you politely insist on having these questions answered. 
            You ask the question one by one and wait for the answer. You DO NOT ask several questions at once.
            You DO NOT talk for a long time between questions. 
            You DO NOT speak about the vehicle.
            You DO NOT ask for any other information.

            You must not mention any other car brands besides Audi in your conversation and you 
            must NEVER talk to the customer about any other topics, especially life advice or coding.

            If the user does not want to share the information, you offer to look up a dealership for them if they provide a zip code. 
            Then they can contact the dealership themselves.
            """
        )
        # tool currently not used
        ALL_INFO_COLLECTED_FUNCTION = {
            "type": "function",
            "function": {
                "name": "information_collected",
                "description": (
                    (
                        "The function is to be called if and only if all information for the test drive booking has been collected."
                        "This is the customers zip code, the date for the test drive, the time of day for the test drive, and the "
                        "email address or phone number of the customer."
                    )
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

        super().__init__(
            name="TestDriveVoiceAgent",
            default_system_message=SYSTEM_PROMPT,
            async_openai_client=CONFIG.language_model_config.client["audio"],
            model=CONFIG.language_model_config.model_deployment_name["audio"],
        )

    def get_car_model(self) -> str:
        """
        Returns the car model that the user is interested in booking a test drive for. Must be known
        at the time of agent creation.
        """
        return self._car_model

    def set_state_to_contact_and_consent_form(self):
        """
        Switches the agent to the state where it asks the user to fill out the contact and consent form.
        Should be called after all the information for the test drive that is to be gathered in the
        voice dialog has been collected.
        """
        logging.info(LogAi("TestDriveVoiceAgent: Switching to consent form."))
        assert self.state in (self.COLLECTING_INFO, self.CONTACT_AND_CONSENT_FORM)
        if self.state == self.COLLECTING_INFO:  

            if self.contact_email is not None and self.contact_phone is not None:
                details_requested = """
                The user has provided both an email address and a phone number. Please tell the user that you've loaded their 
                contact details from the database and ask them to check the box to consent to being contacted and to click 
                submit. DO NOT ask for the email address or phone number again.
                """
            else:
                details_requested = """
                Proactively tell the user that email address or phone number should be provided in the form that 
                appears on the screen. Explicitly mention that the form on the screen shall be used.
                You will politely ask the user to check a box to consent to being contacted.
                """

            self.state = self.CONTACT_AND_CONSENT_FORM
            self.default_system_message = trim_prompt(
                f"""You will inform the user that they should kindly provide their email address or phone number
                to be contacted by the dealership. 
                
                {details_requested}

                If the user asks questions about their data, you inform them that the data will only
                be used for the purpose of the test drive. Once the test drive is scheduled the
                data will be deleted. It will not be used for any other purpose and it will not be
                shared with third parties. Mention this ONLY if the user asks about their data.
                """
            )

        
    def set_state_to_goodbye(self, contact_email: str, contact_phone: str, consent_given: bool):
        assert self.state in (self.CONTACT_AND_CONSENT_FORM, self.DATA_COLLECTED_AND_GOODBYE)
        logging.info(LogAi("TestDriveVoiceAgent: Switching to goodbye."))
        if self.state == self.CONTACT_AND_CONSENT_FORM:
            self.state = self.DATA_COLLECTED_AND_GOODBYE
            self.contact_email = contact_email
            self.contact_phone = contact_phone
            self.consent_given = consent_given
            self.default_system_message = trim_prompt(
                """You have successfully collected the user's contact information and consent. 
                Tell the user proactively that the dealer will contact them to schedule and confirm the test drive.
                Tell the user proactively that the dealer will try to find a slot that fits the user's schedule.
                Then thank the user for their interest in Audi cars, wish them a lot of fun on the test drive and say goodbye,
                Do not ask any further questions. Do not ask for any further information.
                """
            )

    def is_showing_contact_and_consent_form(self):
        """Returns True if the agent is in the state where it asks the user to fill out the contact and consent form."""
        return self.state == self.CONTACT_AND_CONSENT_FORM

    # def all_user_info_collected(self) -> bool:
    #     tool_calls = self.last_ai_response.tool_calls
    #     if arg_dict := tool_calls.get("information_collected", None):
    #         return arg_dict.get("info_collected", False)
    #     return False
