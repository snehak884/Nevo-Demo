import asyncio
import logging
import re
from typing import Any, Literal

from nevo_framework.config.master_config import load_json_config
from nevo_framework.helpers.logging_helpers import LogAi
from nevo_framework.llm.agent_orchestrator import AbstractAgentOrchestrator
from nevo_framework.llm.agents import TimedWebElementMessage, VoiceAgentResponse
from nevo_framework.llm.llm_tools import maybe_get, trim_prompt

import llm.data as data
import llm.messages as server_messages
from llm import generic_image_selector
from llm import image_intent as image_intent
from llm import recommendation_and_details as recommendation
from llm import test_drive_agent as test_drive
from llm import user_profile_agent as user_profile
from llm.caption_generator import add_recommendation_captions
from llm.recommendation_and_details import ConversationRoutes, RecommendationsWithImages, UserModelChoice
from salesforce_connector.salesforce_connector import SalesforceConnector


def _message_list_for_generic_image(model: str, time_delta: float = 2) -> list[TimedWebElementMessage]:
    """
    Returns a message with a generic image for the given car model.
    """
    if generic_image := generic_image_selector.get_generic_image(model):
        return [TimedWebElementMessage(time_delta, generic_image)]
    else:
        return None


class AudiAgentOrchestrator(AbstractAgentOrchestrator):
    """
    Manages the "big picture" state of the conversation and the transitions between the different AI agents.
    Calls level 1 agents if desired. Switches between level 2 agents or sets context dependenpt (system) prompts.
    """

    def __init__(self, output_queue: asyncio.Queue, chat_modality: Literal["text", "audio"]):
        super().__init__(output_queue, chat_modality)
        self.user_profile: str = None
        self.customer_name: str = None
        self.first_time_showing_car: bool = True

        # we start with the UserProfileVoiceAgent to get the user profile in a conversation
        self.speaking_agent = user_profile.UserProfileVoiceAgent()
        # we create this here as it loads RAG data and we don't want to do this on every call
        self.car_detail_agent = recommendation.CarDetailAgent()
        self.safety_feature_agent = recommendation.SafetyFeatureAgent()

        self.recommendations: RecommendationsWithImages = None
        self.model_selector = recommendation.UserModelChoiceSelector()
        self.router = recommendation.ConversationRouter()
        self.car_walkaround_tracker = image_intent.CarModelWalkaroundTracker()
        
        # Initialize Salesforce connector only if credentials are available
        import os
        if (os.getenv("SALESFORCE_SANDBOX_USERNAME") and 
            os.getenv("SALESFORCE_SANDBOX_PASSWORD") and 
            os.getenv("SALESFORCE_SANDBOX_TOKEN")):
            try:
                self.salesforce_connector = SalesforceConnector(table_name="SalesAgentRecord__c")
                logging.info("Salesforce connector initialized successfully")
            except Exception as e:
                logging.warning(f"Failed to initialize Salesforce connector: {e}. Continuing without Salesforce.")
                self.salesforce_connector = None
        else:
            logging.info("Salesforce credentials not found. Running without Salesforce integration.")
            self.salesforce_connector = None

        self.test_drive_tracker = test_drive.TestDriveDetailsTracker()
        self.keyword_extractor = recommendation.KeywordExtractor()
        self.tour_keyword_extractor = recommendation.TourKeywordExtractor(
            keywords=[
                "left",
                "right",
                "front",
                "rear",
                "back",
                "trunk",
                "boot",
                "dashboard",
            ]
        )

        self.config = load_json_config()
        self.selected_image = None

        self.debug_start_on_stage = None
        if self.config.has_debug_flag("recommendation"):
            self.debug_start_on_stage = "recommendation"
            logging.warning(
                LogAi("Debug flag 'recommendation' is set, setting up the orchestration for a recommendation.")
            )
            self.recommendations = RecommendationsWithImages(
                recommended_cars=["Audi A3", "Audi Q3"],
                reason_for_recommendations="The Audi A3 is a compact luxury sedan that is perfect for city driving. The Audi Q3 is a subcompact luxury SUV that is perfect for families.",
                image_message=server_messages.ShowImage(
                    image="audi/car_views/A3/Walkaround_A3_front_left_square.jpg",
                    image2="audi/car_views/Q3/Walkaround_Q3_front_left_square.jpg",
                ),
            )
            self.customer_name = data.TEST_USER_NAME
            self.user_profile = data.TEST_USER_PROFILE
            self.speaking_agent = recommendation.CarRecommendationAgent(
                user_profile=data.TEST_USER_PROFILE,
            )

    async def chat_step__user_profile_state(self, dialog: list[dict[str, str]]) -> VoiceAgentResponse:
        assert isinstance(self.speaking_agent, user_profile.UserProfileVoiceAgent)

        response = await self.speaking_agent.dialog_step(dialog=dialog)

        # check if we have collected all user info and switch to the next agent if so
        if self.speaking_agent.all_user_info_collected():
            (profile, name) = await asyncio.gather(
                user_profile.summarize_user_profile(dialog), user_profile.get_user_name(dialog)
            )
            self.user_profile = profile
            self.customer_name = name
            # we switch to the recommendation agent...
            self.speaking_agent = recommendation.CarRecommendationAgent(user_profile=self.user_profile)
            logging.info(
                LogAi(
                    trim_prompt(
                        f"""User profile collected. Switching to recommendation mode; AI speaks next.
                        Profile summary: '{profile}'.
                        Customer name: {name}"""
                    )
                )
            )
            # ... and let it speak immediately
            response = await self.speaking_agent.dialog_step(
                dialog=dialog,
                sentence_callback=self.keyword_extractor.sentence_callback,
                sentence_watcher_terminals=[". ", ".\n"],
            )  # llm_call=self.keyword_extractor)
            response = await add_recommendation_captions(response)
            # respond with AI speaking next, so we go into the recommendation branch

            if self.config.context_by_phase_cutoff:
                # Just include the recommendation as we move to the next phase
                dialog = dialog[-1:]
                # del dialog[:-1]
                logging.info(f"Length of updated dialog for conversation phase shift: {len(dialog)}")

        return response

    async def handle_walkaround_click(
        self, walkaround_message: server_messages.CarWalkaroundResponse, dialog: list[dict[str, str]]
    ) -> VoiceAgentResponse:

        view_to_ask_about = None

        logging.info(LogAi(f"Running through web interaction on walkaround images."))
        if current_model := re.search(r"Q\d|A\d", walkaround_message.current_image)[0]:
            # If the image it gets is the open boot or the dashboard, it returns the rear or front instead
            new_image = self.car_walkaround_tracker.rotate_image(
                direction=walkaround_message.clicked,
                current_image=walkaround_message.current_image,
                model=current_model,
            )
            new_image = f"audi/car_views/{new_image}"

            # trigger the AI to ask about another view it has to offer
            if "front.jpeg" in new_image:
                view_to_ask_about = "dashboard"
            elif "rear.jpeg" in new_image:
                view_to_ask_about = "open trunk"

            # send image message immediately to avoid delay
            self.send_web_element_message(server_messages.ShowImage(image=new_image, layout_hint="walkaround"))

        # do we have an image we want the AI to comment on?
        if view_to_ask_about:
            self.speaking_agent = image_intent.ImageCommentaryAgent(
                current_model=current_model,
                view=view_to_ask_about,
                current_image=walkaround_message.current_image,
            )
            response = await self.speaking_agent.dialog_step(dialog=dialog)
            return response
        else:
            # nothing to comment on: send empty response
            return VoiceAgentResponse(agent_name="no agent")

    async def chat_step__recommender_and_details_state(
        self, dialog: list[dict[str, str]], web_element_message: dict[str, Any] | None
    ) -> VoiceAgentResponse:
        assert self.user_profile is not None, "Missing user profile!"

        # handle the frontend message indicating that the user click the "next / previous" image button when looking at a car model
        if walkaround_message := maybe_get(web_element_message, server_messages.CarWalkaroundResponse):
            return await self.handle_walkaround_click(walkaround_message, dialog)

        # If its not the first time, we perform dynamic routing to decide what to do next.
        async_routings = asyncio.gather(
            self.router.extract_output(dialog=dialog),
            self.model_selector.extract_output(dialog=dialog),
            self.safety_feature_agent.rag_lookup(dialog=dialog),
        )

        route_and_model: tuple[ConversationRoutes, UserModelChoice, None] = await async_routings
        routing, model_choice, _ = route_and_model

        assert routing is not None, "Missing routing!"
        logging.info(LogAi(f"Recommender / detail - route: {routing}, user speaking about model: {model_choice}"))
        self.send_status_message(f"Routing: {routing}, model: {model_choice}")
        # self.current_car_model = model_choice.user_selected_model

        if routing.conversation_topic == "car_model_comparison":
            # We are back to comparing car models, and we compute a new recommendation as the user
            # has told us more about their preferences.
            self.speaking_agent = recommendation.CarRecommendationAgent(user_profile=self.user_profile)
            l2_response = await self.speaking_agent.dialog_step(
                dialog=dialog,
                sentence_callback=self.keyword_extractor.sentence_callback,
                sentence_watcher_terminals=[". ", ".\n"],
            )  # llm_call=self.keyword_extractor)
            l2_response = await add_recommendation_captions(l2_response)

        elif routing.conversation_topic == "car_model_details":
            # We are talking about a specific car model and its details.
            self.speaking_agent = self.car_detail_agent

            timed_messages = _message_list_for_generic_image(model_choice.user_selected_model)

            await self.speaking_agent.rag_lookup(dialog=dialog, car_model=model_choice.user_selected_model)
            l2_response = await self.speaking_agent.dialog_step(
                dialog=dialog, timed_web_element_messages=timed_messages
            )

        elif routing.conversation_topic == "test_drive":
            # We are talking about a test drive.
            timed_messages = _message_list_for_generic_image(model_choice.user_selected_model)

            self.speaking_agent = test_drive.TestDriveVoiceAgent(
                customer_name=self.customer_name, car_model=model_choice.user_selected_model
            )
            l2_response = await self.speaking_agent.dialog_step(
                dialog=dialog, timed_web_element_messages=timed_messages
            )

            # Cutoff the conversation history as we move to the next phase; just keep the last step
            if self.config.context_by_phase_cutoff:
                dialog = dialog[-1:]
                # del dialog[:-1]
                logging.info(f"Length of updated dialog for conversation phase shift: {len(dialog)}")

        elif routing.conversation_topic == "image_intent":
            uses_web_interface = False
            # The user wants us to show them something.
            if image_rotation_message := maybe_get(web_element_message, server_messages.CarWalkaroundResponse):
                self.selected_image: str = self.car_walkaround_tracker.rotate_image(
                    direction=image_rotation_message.clicked,
                    current_image=image_rotation_message.current_image,
                    model=model_choice.user_selected_model,
                )

                dialog.append(
                    {
                        "role": "user",
                        "content": f"Show me the {self.selected_image.replace('Walkaround_', '').replace('.jpeg', '')}",
                    }
                )

                uses_web_interface = True

            else:
                # Here we selected the image from a list using an LLM based on what the user has asked
                self.selected_image = await image_intent.ImageLookupAgent().image_lookup(
                    dialog=dialog,
                    car_model=model_choice.user_selected_model,
                )

            self.speaking_agent = image_intent.ImageIntentAgent(
                image_name=self.selected_image,
                uses_web_interface=uses_web_interface,
            )

            image_path = f"audi/car_views/{self.selected_image}"
            logging.info(LogAi(f"Showing image: {image_path}"))

            # If we show the car for the first time, we ask the user if they want to see a walkaround
            # If it's not the first time, we should have removed this question from the system prompt
            if self.first_time_showing_car:
                self.speaking_agent.update_system_prompt("\nYou MUST also ask if they would like a tour of the car!")
                self.first_time_showing_car = False

            l2_response = await self.speaking_agent.dialog_step(
                dialog=dialog,
                timed_web_element_messages=[
                    TimedWebElementMessage(0.01, server_messages.ShowImage(image=image_path, layout_hint="walkaround"))
                ],
            )

            self.speaking_agent.reset_system_prompt()

        elif routing.conversation_topic == "driver_assistance_features":
            # We are talking about driver assistant features
            self.speaking_agent = self.safety_feature_agent
            stream_watcher = recommendation.ImageFromResponse(
                rag_information=self.safety_feature_agent.rag_information,
                selected_rag_docs=self.safety_feature_agent.selected_rag_docs,
            )
            l2_response = await self.safety_feature_agent.dialog_step(
                dialog=dialog,
                sentence_callback=stream_watcher.sentence_callback,
            )

        elif routing.conversation_topic == "tour_of_car":
            l2_response = await self.chat_step__car_tour_state(
                dialog=dialog,
                model_choice=model_choice.user_selected_model,
            )

        return l2_response

    async def chat_step__test_drive_state(
        self,
        dialog: list[dict[str, str]],
        web_elment_message: dict[str, Any] | None,
    ) -> VoiceAgentResponse:
        assert isinstance(self.speaking_agent, test_drive.TestDriveVoiceAgent)
        tracker = self.test_drive_tracker

        if self.speaking_agent.state == test_drive.TestDriveVoiceAgent.COLLECTING_INFO:
            # In this phase we collect information about the test drive from the user in
            # a voice dialog, for example the zip code, date and time.
            tracker.append_to_dialog(dialog)
            await tracker.extract_test_drive_details()

            if tracker.details_complete():
                # If we have those details, we switch to the contact and consent form state.
                # The form is used for data that is awkward to collect in a voice dialog, such
                # as email and phone number. It also contains consent confirmation.
                self.speaking_agent.set_state_to_contact_and_consent_form()
                # responding with changed state!
                response = await self.speaking_agent.dialog_step(dialog=dialog)
                # enrich the response using web element message to trigger the form display in the frontend
                return response.with_web_element_message(
                    server_messages.ShowForm(
                        zip_code=tracker.get_test_drive_details().zip_code,
                        preferred_date=tracker.get_test_drive_details().preferred_date,
                        preferred_time=tracker.get_test_drive_details().preferred_time,
                        car_model=self.speaking_agent.get_car_model(),
                    )
                )
            else:
                timed_messages = _message_list_for_generic_image(self.speaking_agent.get_car_model(), time_delta=1)
                return await self.speaking_agent.dialog_step(dialog=dialog, timed_web_element_messages=timed_messages)

        elif self.speaking_agent.state == test_drive.TestDriveVoiceAgent.CONTACT_AND_CONSENT_FORM:
            # do we have a "submit" click from the frontend?
            if contact_and_consent_response := maybe_get(web_elment_message, server_messages.ContactAndConsentResponse):
                logging.info(LogAi(f"Got contact and consent response: {contact_and_consent_response}"))
                self.speaking_agent.set_state_to_goodbye(
                    contact_email=contact_and_consent_response.email,
                    contact_phone=contact_and_consent_response.phone_number,
                    consent_given=contact_and_consent_response.contact_consent,
                )

                timed_messages = _message_list_for_generic_image(self.speaking_agent.get_car_model(), time_delta=1)
                return await self.speaking_agent.dialog_step(dialog=dialog, timed_web_element_messages=timed_messages)
            else:
                # we keep the dialog tracker running as this allows the user to change information like the date
                # while the form is already on the screen
                tracker.append_to_dialog(dialog)
                await tracker.extract_test_drive_details()
                response = await self.speaking_agent.dialog_step(dialog=dialog)
                return response.with_web_element_message(
                    server_messages.ShowForm(
                        zip_code=tracker.get_test_drive_details().zip_code,
                        preferred_date=tracker.get_test_drive_details().preferred_date,
                        preferred_time=tracker.get_test_drive_details().preferred_time,
                        car_model=self.speaking_agent.get_car_model(),
                    )
                )

        elif self.speaking_agent.state == test_drive.TestDriveVoiceAgent.DATA_COLLECTED_AND_GOODBYE:
            return await self.speaking_agent.dialog_step(dialog=dialog)

        raise RuntimeError("Invalid state.")

    async def handle_backoffice_data_request(
        self, message: server_messages.RequestBackofficeData, dialog: list[dict[str, str]]
    ) -> VoiceAgentResponse:

        NOT_COLLECTED = "Not collected"
        if isinstance(self.speaking_agent, test_drive.TestDriveVoiceAgent):
            email = self.speaking_agent.contact_email if self.speaking_agent.contact_email else NOT_COLLECTED
            phone = self.speaking_agent.contact_phone if self.speaking_agent.contact_phone else NOT_COLLECTED
            car_model = self.speaking_agent.get_car_model()
        else:
            email = NOT_COLLECTED
            phone = NOT_COLLECTED
            car_model = NOT_COLLECTED

        date = self.test_drive_tracker.last_test_drive_details.preferred_date
        date = date if date else NOT_COLLECTED

        time = self.test_drive_tracker.last_test_drive_details.preferred_time
        time = time if time else NOT_COLLECTED

        name = self.customer_name
        name = name if name else NOT_COLLECTED

        profile = self.user_profile
        profile = profile if profile else NOT_COLLECTED

        if not car_model and self.recommendations:
            car_model = f"{self.recommendations.recommended_cars[0]} or {self.recommendations.recommended_cars[1]}"

        summary = await user_profile.summarize_user_profile(dialog)

        return VoiceAgentResponse(agent_name="no agent").with_web_element_message(
            server_messages.BackofficeDataMessage(
                name=name,
                car=car_model,
                date=date,
                time=time,
                profile_summary=profile,
                conversation_summary=summary,
            )
        )

    async def chat_step__car_tour_state(
        self,
        dialog: dict[str, str],
        model_choice: str,
    ) -> Any:

        self.tour_keyword_extractor.car_model = model_choice.replace("Audi ", "")

        self.speaking_agent = image_intent.CarTourAgent(model_name=model_choice, user_profile=self.user_profile)
        _ = await self.speaking_agent.dialog_step(
            dialog=dialog,
            sentence_callback=self.tour_keyword_extractor.sentence_callback,
        )

        self.tour_keyword_extractor.reset()

        return VoiceAgentResponse(agent_name="no agent")

    async def dialog_step(
        self, dialog: list[dict[str, str]], web_element_message: dict[str, Any] | None
    ) -> VoiceAgentResponse:
        """
        Call to execute a chat step with the current level 2 chatbot. This function handles things like
        dynamic prompts, running level 1 agents and injecting information from other agents to steer the current agent.
        It should not, however, change the current agent.

        Args:
            dialog: The full conversation dialog so far, including the latest message from the user
                if input was handed over to the user. This includes all messages from the user and all AI agents.
            web_element_message: The message from the frontend, if any.
        Returns:
            The response from the level 2 chatbot.
        """
        if message := maybe_get(web_element_message, server_messages.RequestBackofficeData):
            return await self.handle_backoffice_data_request(message, dialog)

        if isinstance(self.speaking_agent, user_profile.UserProfileVoiceAgent):
            response = await self.chat_step__user_profile_state(dialog=dialog)

        elif isinstance(
            self.speaking_agent,
            (
                recommendation.CarRecommendationAgent,
                recommendation.CarDetailAgent,
                recommendation.SafetyFeatureAgent,
                image_intent.ImageIntentAgent,
                image_intent.ImageCommentaryAgent,
                image_intent.CarTourAgent,
            ),
        ):
            response = await self.chat_step__recommender_and_details_state(
                dialog=dialog, web_element_message=web_element_message
            )

        elif isinstance(self.speaking_agent, test_drive.TestDriveVoiceAgent):
            response = await self.chat_step__test_drive_state(dialog=dialog, web_elment_message=web_element_message)
            if self.speaking_agent.state == "data_collected":
                # Once we've set the state to goodbye, we can write to Salesforce / the CRM system
                # Question: Should this little write be in a separate function/method? It doesn't look
                # # like a further abstraction would be useful, but it looks messy here
                if self.salesforce_connector is not None:
                    try:
                        salesforce_insert = self.salesforce_connector.write_user_details(
                            new_record={
                                "name__c": self.customer_name,
                                "email__c": self.speaking_agent.contact_email,
                                "phone_number__c": self.speaking_agent.contact_phone,
                                "car_model__c": self.speaking_agent.get_car_model(),
                                "preferred_date__c": self.test_drive_tracker.last_test_drive_details.preferred_date,
                                "preferred_time__c": self.test_drive_tracker.last_test_drive_details.preferred_time,
                                "zip_code__c": self.test_drive_tracker.last_test_drive_details.zip_code,
                                "user_profile__c": self.user_profile,
                                "consent_given__c": self.speaking_agent.consent_given,
                                "conversation_summary__c": await user_profile.summarize_user_profile(dialog),
                            }
                        )
                        logging.info(LogAi(f"Salesforce insert result: {salesforce_insert}"))
                    except Exception as e:
                        logging.warning(LogAi(f"Failed to write to Salesforce: {e}"))
                else:
                    logging.info(LogAi("Salesforce connector not available. Skipping Salesforce write."))
        else:
            # keep this here to make sure we don't forget to handle all cases
            raise RuntimeError("Invalid state.")

        return response
