import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal

import openai
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from nevo_framework.config.configuration import load_collectors_from_json
from analysis.data_collector_benchmark.create_collectors import create_openai_collectors
from testing.simple_agents import FunctionCallingAgent

logging.basicConfig(level=logging.INFO)

TIMEOUT = 60.0
AGENT_COLLECTORS_FILENAME = "agent_collectors.json"

load_dotenv()
openai_async_client = openai.AsyncClient()


class CustomerProfile(BaseModel):
    first_name: str = Field(description="The first name of the customer.")

    family_type: Literal["single without children", "family", "couple without children", "not specified"] = Field(
        "not specified", description="The family situation of the customer."
    )

    location_type: Literal["city", "suburb", "rural", "small town", "not specified"] = Field(
        "not specified", description="The type of location where the customer lives."
    )

    car_use_reason: Literal[
        "commuting for work", "family trips", "business", "weekend trips", "vacation trips", "not specified"
    ] = Field("not specified", description="The main reason for using the car.")

    skoda_vehicle_model: Literal["enyaq", "kodiaq", "octavia", "superb", "not specified"] = Field(
        "not specified", description="The Skoda vehicle model the customer is interested in."
    )

    color_information: Literal[
        "blue", "grey", "red", "silver", "gold", "black", "white", "green", "orange", "beige", "not specified"
    ] = Field("not specified", description="The color the customer likes for the car.")

    viewing_interest: Literal["color", "interior", "wheels", "not specified"] = Field(
        "not specified",
        description="A certain aspect of the car the customer is interested in seeing more details about.",
    )

    driver_assistance_feature: Literal[
        "adaptive cruise control",
        "lane assist",
        "parking assist",
        "blind spot detection",
        "emergency braking",
        "not specified",
    ] = Field("not specified", description="A driver assitance technology the customer is particularly interested in.")

    post_code: str = Field(description="The postal code of the customer.")

    appointment_date: str = Field(description="The date and time of the appointment the user wants to schedule.")

    car_budget: int | None = Field(description="The budget the customer has for the car.")


@dataclass
class CollectorTestCase:
    user_message: str
    first_name: str = None
    family_type: str = None
    location_type: str = None
    car_use_reason: str = None
    skoda_vehicle_model: str = None
    color_information: str = None
    viewing_interest: str = None
    driver_assistance_feature: str = None
    post_code: str = None
    appointment_date: str = None
    car_budget: int = None


@dataclass
class AgentResult:
    model: str
    agent_data: dict
    test_case: CollectorTestCase
    repetition: int
    agent_type: Literal["structured_output", "function_call"]
    time_taken: float

    def evaluate(self):
        logging.debug(f"Agent: {self.model}")
        logging.debug(f"User message: {self.test_case.user_message}")

        expected_items = {key: exp_val for key, exp_val in asdict(self.test_case).items() if key != "user_message"}
        logging.debug(f"Expected values: {expected_items}")
        logging.debug(f"Agent data: {self.agent_data}")
        num_expected = len(expected_items)
        correct_empty = 0
        correct_non_empty = 0
        wrong_expected_empty = 0
        wrong_not_filled = 0
        wrong_different_value = 0
        result = {
            "model": self.model,
            "agent_type": self.agent_type,
            "repetition": self.repetition,
            "user_message": self.test_case.user_message,
            "agent_data": str(sorted(self.agent_data.items())),
            "expected_items": str({k: v for k, v in expected_items.items() if v is not None}),
            "time_taken": self.time_taken,
        }
        for field, expected_value in expected_items.items():
            if field in self.agent_data:
                if isinstance(expected_value, list):
                    raise NotImplementedError("Multiple expected values not implemented")
                else:
                    if expected_value is None:
                        if self.agent_data[field] == "":
                            correct_empty += 1
                            # result[f"field_{field}"] = "correct_empty"
                        else:
                            wrong_expected_empty += 1
                            result[f"field_{field}"] = "wrong_expected_empty"
                    else:  # we expect a value
                        if expected_value == self.agent_data[field]:
                            correct_non_empty += 1
                            result[f"field_{field}"] = "correct_non_empty"
                        elif self.agent_data[field] == "":  # expect sth, got nothing
                            wrong_not_filled += 1
                            result[f"field_{field}"] = "wrong_not_filled"
                        else:
                            wrong_different_value += 1
                            result[f"field_{field}"] = "wrong_different_value"
            else:
                pass
                # raise ValueError(f"Field {field} is missing from agent data. This should not happen.")

        result["num_expected"] = num_expected
        result["num_correct_empty"] = correct_empty
        result["num_correct_non_empty"] = correct_non_empty
        result["num_wrong_expected_empty"] = wrong_expected_empty
        result["num_wrong_not_filled"] = wrong_not_filled
        result["num_wrong_different_value"] = wrong_different_value
        result["perfect"] = correct_empty + correct_non_empty == num_expected
        return result


async def extract_with_structured_output(test_case: CollectorTestCase, model: str, repetition: int) -> AgentResult:

    def map_value(val):
        if (val is None) or (val == "") or (val == "not specified"):
            return ""
        else:
            return val

    sysprompt = """You are given lines of a dialogue between a customer and a car dealer.
The customer is looking for a car. Your task it to fill a customer profile
with information about the customer and their needs and preferences from the dialogue.
If a piece of information cannot be inferred from the dialogue, say "not specified".
"""
    messages = [
        {"role": "system", "content": sysprompt},
        {"role": "user", "content": test_case.user_message},
    ]
    async with parallel_calls_semaphore:
        try:
            print("calling agent: structured output")
            t = datetime.now()
            response = await openai_async_client.beta.chat.completions.parse(
                messages=messages, model=model, response_format=CustomerProfile, timeout=TIMEOUT
            )
            time_in_seconds = (datetime.now() - t).total_seconds()
        except asyncio.TimeoutError as e:
            raise e
        profile = response.choices[0].message.parsed
        assert isinstance(profile, CustomerProfile)
        response_dict = {key: map_value(val) for key, val in profile.model_dump().items()}
        result = AgentResult(
            model=model,
            agent_data=response_dict,
            test_case=test_case,
            repetition=repetition,
            agent_type="structured_output",
            time_taken=time_in_seconds,
        )
        return result


def create_test_cases() -> list[CollectorTestCase]:

    data_collectors = load_collectors_from_json(filename=AGENT_COLLECTORS_FILENAME)

    for profile_key, collector_key in [
        ("color_information", "get_car_color_information"),
        ("skoda_vehicle_model", "get_skoda_model_information"),
        ("location_type", "get_location_information"),
        ("family_type", "get_family_type"),
        ("car_use_reason", "get_car_use_information"),
        ("viewing_interest", "get_viewing_interest"),
        ("driver_assistance_feature", "get_driver_assistance_information"),
    ]:
        values_from_profile = set(CustomerProfile.__annotations__[profile_key].__args__)
        values_from_collector = set(col for col in data_collectors.collectors[collector_key].argument_enum)
        assert values_from_profile == values_from_collector, f"{values_from_profile} != {values_from_collector}"

    NOT_SPECIFIED = "not specified"

    COLORS = [col for col in CustomerProfile.__annotations__["color_information"].__args__ if col != NOT_SPECIFIED]
    print(f"Colors: {COLORS}")
    MODELS = [
        model for model in CustomerProfile.__annotations__["skoda_vehicle_model"].__args__ if model != NOT_SPECIFIED
    ]
    print(f"Models: {MODELS}")
    NAMES = ["John", "Mary", "Alice", "Bob", "Eve", "Charlie", "David", "Anna", "Peter", "Sophie", "Tom", "Laura"]

    PARTNER_SYNONYMS = [
        "partner",
        "wife",
        "husband",
        "girlfriend",
        "boyfriend",
        "better half",
        "spouse",
        "significant other",
        "life partner",
        "better half",
        "other half",
    ]

    LOCATION_TYPE_SYNONYMS = [  # I live in ...
        ("the city", "city"),
        ("a big city", "city"),
        ("the city center", "city"),
        ("downtown", "city"),
        ("a small town", "small town"),
        ("a little town", "small town"),
        ("a village", "rural"),
        ("a small village", "rural"),
        ("the middle of nowhere", "rural"),
        ("the countryside", "rural"),
        ("the woods", "rural"),
        ("a farm", "rural"),
        ("the suburbs", "suburb"),
        ("suburbia", "suburb"),
        ("a city, but in the suburbs", "suburb"),
        ("in the suburbs of a city", "suburb"),
    ]

    test_cases = [
        # mixed
        CollectorTestCase(
            user_message="Hi, I'm John. I'm looking for a family car. We live in the city and I need it for commuting to work.",
            first_name="John",
            family_type="family",
            location_type="city",
            car_use_reason="commuting for work",
        ),
        CollectorTestCase(
            user_message="Hi, I'm John. I'm looking for a car for my family.",
            first_name="John",
            family_type="family",
        ),
        CollectorTestCase(
            user_message="Hi, I'm John. I'm looking for a car for new car for my commute.",
            first_name="John",
            car_use_reason="commuting for work",
        ),
        CollectorTestCase(
            user_message="Hey, I'm Mary! I'm looking for a small city car for my commute.",
            first_name="Mary",
            location_type="city",
            car_use_reason="commuting for work",
        ),
        # # first name
        *[CollectorTestCase(user_message=f"Hi, I'm {name}. I'm looking for a car.", first_name=name) for name in NAMES],
        *[
            CollectorTestCase(user_message=f"My name is {name}. I'm looking for a car.", first_name=name)
            for name in NAMES
        ],
        # family situation - family
        CollectorTestCase(user_message="I'm looking for a car for my family.", family_type="family"),
        CollectorTestCase(user_message="We're a family of four.", family_type="family"),
        CollectorTestCase(user_message="I have two kids.", family_type="family"),
        CollectorTestCase(
            user_message="I need to take the kids to school.", family_type="family", car_use_reason="family trips"
        ),
        CollectorTestCase(
            user_message="I drive my kids to their friends and activities.",
            family_type="family",
            car_use_reason="family trips",
        ),
        CollectorTestCase(
            user_message="I take my son to too school every day.", family_type="family", car_use_reason="family trips"
        ),
        CollectorTestCase(
            user_message="I drive my daughter to her soccer practice.",
            family_type="family",
            car_use_reason="family trips",
        ),
        CollectorTestCase(
            user_message="I take the little ones to kindergarten.", family_type="family", car_use_reason="family trips"
        ),
        CollectorTestCase(user_message="We are four, me, my partner and our two kids.", family_type="family"),
        # famlily situation - single without children
        CollectorTestCase(user_message="It's just me.", family_type="single without children"),
        CollectorTestCase(user_message="I'm single.", family_type="single without children"),
        CollectorTestCase(user_message="I'm a bachelor.", family_type="single without children"),
        CollectorTestCase(user_message="Just me, no kids yet.", family_type="single without children"),
        CollectorTestCase(user_message="I live alone.", family_type="single without children"),
        # family situation - couple without children
        *[
            CollectorTestCase(user_message=f"It's me and my {partner}.", family_type="couple without children")
            for partner in PARTNER_SYNONYMS
        ],
        *[
            CollectorTestCase(
                user_message=f"I'll share the car with my {partner}.", family_type="couple without children"
            )
            for partner in PARTNER_SYNONYMS
        ],
        *[
            CollectorTestCase(
                user_message=f"My {partner} will use the car as well.", family_type="couple without children"
            )
            for partner in PARTNER_SYNONYMS
        ],
        # location type
        *[
            CollectorTestCase(user_message=f"I live in {location}.", location_type=location_type)
            for location, location_type in LOCATION_TYPE_SYNONYMS
        ],
        *[
            CollectorTestCase(user_message=f"We're in {location}.", location_type=location_type)
            for location, location_type in LOCATION_TYPE_SYNONYMS
        ],
        *[
            CollectorTestCase(user_message=f"I just moved to {location}.", location_type=location_type)
            for location, location_type in LOCATION_TYPE_SYNONYMS
        ],
        CollectorTestCase(user_message="I need a small car for the city.", location_type="city"),
        # car use reason - commuting
        CollectorTestCase(user_message="Mostly for commuting.", car_use_reason="commuting for work"),
        CollectorTestCase(user_message="I go to work by car.", car_use_reason="commuting for work"),
        CollectorTestCase(user_message="I drive to the office every day.", car_use_reason="commuting for work"),
        CollectorTestCase(user_message="My wife will use to drive to work.", car_use_reason="commuting for work"),
        # car use reason - business
        CollectorTestCase(user_message="I drive a lot for my job.", car_use_reason="business"),
        CollectorTestCase(
            user_message="I have a business and I need to drive to my clients.", car_use_reason="business"
        ),
        CollectorTestCase(user_message="I drive to see customers all across the country.", car_use_reason="business"),
        # car use reason - family trips
        CollectorTestCase(
            user_message="I need a car for family trips.", car_use_reason="family trips", family_type="family"
        ),
        CollectorTestCase(
            user_message="I drive my kids to school.", car_use_reason="family trips", family_type="family"
        ),
        CollectorTestCase(user_message="I do the groceries by car.", car_use_reason="family trips"),
        CollectorTestCase(
            user_message="I drive my kids around, to sports and classes.",
            car_use_reason="family trips",
            family_type="family",
        ),
        # car use reason - weekend trips
        CollectorTestCase(user_message="We go to countryside on the weekend.", car_use_reason="weekend trips"),
        CollectorTestCase(user_message="I like going to sea on the weekend.", car_use_reason="weekend trips"),
        CollectorTestCase(user_message="We do a lot of weekend trips.", car_use_reason="weekend trips"),
        CollectorTestCase(user_message="We drive out on the weekend.", car_use_reason="weekend trips"),
        CollectorTestCase(user_message="We go on hikes in the mountains on weekends.", car_use_reason="weekend trips"),
        CollectorTestCase(user_message="On weekends, we go skiing.", car_use_reason="weekend trips"),
        # car use reason - vacation trips
        CollectorTestCase(user_message="We go on vacation with the car.", car_use_reason="vacation trips"),
        CollectorTestCase(user_message="We drive to our holiday home in the summer.", car_use_reason="vacation trips"),
        CollectorTestCase(user_message="We travel a lot by car.", car_use_reason="vacation trips"),
        CollectorTestCase(user_message="In the summer, we travel all through Europe.", car_use_reason="vacation trips"),
        CollectorTestCase(
            user_message="I need a car for long drives when we go on vacation.", car_use_reason="vacation trips"
        ),
        # color and model
        *[
            CollectorTestCase(
                user_message=f"Is this available in {color}?", color_information=color, viewing_interest="color"
            )
            for color in COLORS
        ],
        *[
            CollectorTestCase(user_message=f"I want a {color} car.", color_information=color, viewing_interest="color")
            for color in COLORS
        ],
        *[
            CollectorTestCase(
                user_message=f"Show me the {model} in {color}!",
                color_information=color,
                viewing_interest="color",
                skoda_vehicle_model=model,
            )
            for color in COLORS
            for model in MODELS
        ],
        *[
            CollectorTestCase(
                user_message=f"I like the look of the {model}. Does it come in {color}?",
                color_information=color,
                skoda_vehicle_model=model,
                viewing_interest="color",
            )
            for color in COLORS
            for model in MODELS
        ],
        *[
            CollectorTestCase(
                user_message=f"Does the {model} come in {color}?",
                color_information=color,
                viewing_interest="color",
                skoda_vehicle_model=model,
            )
            for color in COLORS
            for model in MODELS
        ],
        *[
            CollectorTestCase(
                user_message=f"The {model} sounds good. Does it come in {color}?",
                color_information=color,
                skoda_vehicle_model=model,
                viewing_interest="color",
            )
            for color in COLORS
            for model in MODELS
        ],
        *[
            CollectorTestCase(user_message=f"I'm interested in the {model}?", skoda_vehicle_model=model)
            for model in MODELS
        ],
        *[
            CollectorTestCase(
                user_message=f"Can you tell me something about the Skoda {model}?", skoda_vehicle_model=model
            )
            for model in MODELS
        ],
        *[
            CollectorTestCase(
                user_message=f"The {model} sounds like a good fit. Can you tell me more?", skoda_vehicle_model=model
            )
            for model in MODELS
        ],
        *[
            CollectorTestCase(user_message=f"Yes, the {model} might be a good choice.", skoda_vehicle_model=model)
            for model in MODELS
        ],
        *[
            CollectorTestCase(
                user_message=f"I heard about the Skoda {model}. Can you tell me more?", skoda_vehicle_model=model
            )
            for model in MODELS
        ],
        *[
            CollectorTestCase(
                user_message=f"My friend drives a {model}. Tell me something about it?", skoda_vehicle_model=model
            )
            for model in MODELS
        ],
        # budget
        CollectorTestCase(user_message="I have a budget of 20000.", car_budget=20000),
        CollectorTestCase(user_message="I can spend around 35 k.", car_budget=35000),
        CollectorTestCase(user_message="I don't want to spend more than 40000.", car_budget=40000),
        CollectorTestCase(user_message="Something around 30 k or less.", car_budget=30000),
        CollectorTestCase(user_message="I've planned like 35 thousand euros.", car_budget=35000),
        CollectorTestCase(user_message="I can't spend more than 40k.", car_budget=40000),
        CollectorTestCase(user_message="Not sure about the budget yet.", car_budget=None),
        # viewing intention
        CollectorTestCase(user_message="What colors are available?", viewing_interest="color"),
        CollectorTestCase(user_message="I want to see the color options.", viewing_interest="color"),
        CollectorTestCase(user_message="What does the interior look like?", viewing_interest="interior"),
        CollectorTestCase(user_message="What does it look like inside?", viewing_interest="interior"),
        CollectorTestCase(user_message="I want to see the interior.", viewing_interest="interior"),
        CollectorTestCase(user_message="Can you show me the interior?", viewing_interest="interior"),
        CollectorTestCase(user_message="Show me the wheels.", viewing_interest="wheels"),
        CollectorTestCase(user_message="Can I see the wheels?", viewing_interest="wheels"),
        # safety and assistance
        CollectorTestCase(
            user_message="I often drive on highways during rush hour, and traffic can speed up and slow down suddenly. Is there a way the car can adjust to those changing speeds smoothly so I'm not constantly braking and accelerating?",
            driver_assistance_feature="adaptive cruise control",
            car_use_reason="commuting for work",
        ),
        CollectorTestCase(
            user_message="Long road trips can be tiring when I have to keep adjusting my speed. Is there anything in this vehicle that helps reduce driver fatigue on the highway?",
            driver_assistance_feature="adaptive cruise control",
        ),
        CollectorTestCase(
            user_message="Sometimes I get stuck behind slow vehicles, and other times traffic opens up. How can this car help me maintain a comfortable distance from the car ahead, without me having to watch the speedometer constantly?",
            driver_assistance_feature="adaptive cruise control",
        ),
        CollectorTestCase(
            user_message="When I'm traveling with my family, I look for features that keep the ride calm and steady. Is there a function that automatically manages speed when traffic conditions change?",
            driver_assistance_feature="adaptive cruise control",
            family_type="family",
            car_use_reason="family trips",
        ),
        CollectorTestCase(
            user_message="On long journeys, I like to briefly rest my feet from the pedals. Does this car offer a system that lets me do that safely under normal driving conditions?",
            driver_assistance_feature="adaptive cruise control",
        ),
        CollectorTestCase(
            user_message="I drive on winding roads or sometimes in congested areas where lanes shift a lot. How does this car help keep me from drifting into another lane accidentally?",
            driver_assistance_feature="lane assist",
        ),
        CollectorTestCase(
            user_message="When I'm tired or driving at night, I worry about not noticing if I'm veering off course. Are there any features that help me stay centered on the road?",
            driver_assistance_feature="lane assist",
        ),
        CollectorTestCase(
            user_message="Highway lines aren't always clearly marked. Is there anything in this car that helps me maintain my lane when markings are faded or difficult to see?",
            driver_assistance_feature="lane assist",
        ),
        CollectorTestCase(
            user_message="On multi-lane highways, I want a bit of extra support to ensure I don't accidentally stray into another lane. Does this vehicle offer something to help with that?",
            driver_assistance_feature="lane assist",
        ),
        CollectorTestCase(
            user_message="Sometimes I lose focus during long drives. Is there a way this car alerts me if I start drifting over the lane lines without signaling?",
            driver_assistance_feature="lane assist",
        ),
        CollectorTestCase(
            user_message="I often have to parallel park in the city, and tight spaces make me nervous. Is there something that makes parking in tricky spots easier?",
            driver_assistance_feature="parking assist",
        ),
        CollectorTestCase(
            user_message="Some cars can help you navigate into a spot when space is limited. How does this one handle crowded parking scenarios or tight garage spaces?",
            driver_assistance_feature="parking assist",
        ),
        CollectorTestCase(
            user_message="I've heard about features that help guide you into a parking spot without too much hassle. Does this model do anything special to assist with parking?",
            driver_assistance_feature="parking assist",
        ),
        CollectorTestCase(
            user_message="I'm always worried about accidentally bumping into curbs or other cars when backing into a space. Does the vehicle provide any guidance or feedback to prevent that?",
            driver_assistance_feature="parking assist",
        ),
        CollectorTestCase(
            user_message="When I'm trying to fit into a small space at a shopping center, I want to avoid stress and damage. Is there a function in this car that offers extra help for parking maneuvers?",
            driver_assistance_feature="parking assist",
        ),
        CollectorTestCase(
            user_message="I find changing lanes stressful, especially on busy roads. Does this car have a way to warn me if another vehicle is in a spot I might not see?",
            driver_assistance_feature="blind spot detection",
        ),
        CollectorTestCase(
            user_message="It's hard to keep track of every angle around the car. Are there any features that help me be aware of vehicles alongside me before I merge?",
            driver_assistance_feature="blind spot detection",
        ),
        CollectorTestCase(
            user_message="When I'm traveling on the highway, sometimes cars sneak up in that area I can't see in my mirrors. Does this model have a way to detect that?",
            driver_assistance_feature="blind spot detection",
        ),
        CollectorTestCase(
            user_message="I want to feel more confident about safety when I switch lanes. What does this car offer to give me a better view of cars that might be just out of sight?",
            driver_assistance_feature="blind spot detection",
        ),
        CollectorTestCase(
            user_message="I've heard of technology that signals you if there's a vehicle next to you before you turn or merge. Does this car provide any alerts like that?",
            driver_assistance_feature="blind spot detection",
        ),
        CollectorTestCase(
            user_message="In unpredictable traffic, I worry about cars stopping suddenly ahead of me. Is there anything that can help prevent or lessen collisions in these situations?",
            driver_assistance_feature="emergency braking",
        ),
        CollectorTestCase(
            user_message="Sometimes I get momentarily distracted by kids in the back seat. Is there a system in place that helps stop the car if something unexpected happens?",
            driver_assistance_feature="emergency braking",
            family_type="family",
        ),
        CollectorTestCase(
            user_message="I value safety features that can intervene if I don't react quickly enough. How does this vehicle help reduce the chances of a rear-end accident?",
            driver_assistance_feature="emergency braking",
        ),
        CollectorTestCase(
            user_message="I drive in areas with pedestrians crossing unpredictably. Is there anything in this car that can detect a hazard and activate the brakes on its own?",
            driver_assistance_feature="emergency braking",
        ),
        CollectorTestCase(
            user_message="When traffic is heavy, it can be easy to miss sudden stops. Does this vehicle have a safety measure that applies the brakes automatically in an emergency?",
            driver_assistance_feature="emergency braking",
        ),
    ]
    return test_cases


parallel_calls_semaphore = asyncio.Semaphore(30)


def validate_test_cases():
    """
    Make sure that the test cases are valid, i.e. that the properties are known to the tools and the values
    match the known values.
    """
    func_call__data_collectors = load_collectors_from_json(filename=AGENT_COLLECTORS_FILENAME)

    fields = dict()
    for collector in func_call__data_collectors.collectors.values():
        fields[collector.argument_name] = collector.argument_enum

    # make sure the properties are consistent between the function calling tool definition and the
    # class used for structured output
    profile = CustomerProfile(first_name="John", post_code="12345", appointment_date="2022-12-24", car_budget=20000)
    assert set(profile.model_dump().keys()) == set(fields.keys())

    test_cases = create_test_cases()
    print(f"Validating {len(test_cases)} test cases")

    for test_case in test_cases:
        for key, value in asdict(test_case).items():
            if key == "user_message":
                continue
            elif (value is not None) and (key not in fields):
                raise ValueError(f"Property {key} is not a known property in the tools, for case {test_case}.")
            elif (value is not None) and (fields[key] is not None) and (value not in fields[key]):
                raise ValueError(
                    f"Value '{value}' is not a known value for property {key} in the tools, for case {test_case}."
                )
            if isinstance(value, list):
                raise ValueError(f"Value '{value}' is a list for property {key} in the tools, for case {test_case}.")


async def call_collector(agent_params: dict, test_case: CollectorTestCase, repetition: int):
    async with parallel_calls_semaphore:
        agent = FunctionCallingAgent(**agent_params)
        print("calling agent: function call")
        t = datetime.now()
        await agent(test_case.user_message, timeout=60.0)
        time_in_seconds = (datetime.now() - t).total_seconds()
        return AgentResult(
            model=agent.model,
            agent_data=agent.get_data(),
            test_case=test_case,
            repetition=repetition,
            agent_type="function_call",
            time_taken=time_in_seconds,
        )


async def run_test(
    num_repetitions: int = 5,
    limit_to_n: int = None,
):
    import random

    TEST_STRUCTURED_OUTPUT = True
    TEST_FUNCTION_CALLING = True

    tools_list = create_openai_collectors()
    agent_params = [
        {
            "tools": tools_list,
            "model": "gpt-4o-mini",
            "time_debug": False,
            "name": "FCA gpt4o-mini",
            "tool_choice": "required",
        },
        {"tools": tools_list, "model": "gpt-4o", "time_debug": False, "name": "FCA gpt4o", "tool_choice": "required"},
    ]

    test_cases = [test for test in create_test_cases()]
    print(f"Created {len(test_cases)} test cases")
    trials = [
        (repetition, params, test_case)
        for repetition in range(num_repetitions)
        for params in agent_params
        for test_case in test_cases
    ]

    if limit_to_n:
        random.shuffle(trials)
        trials = trials[:limit_to_n]
        assert len(trials) == limit_to_n

    tasks = []
    if TEST_STRUCTURED_OUTPUT:
        print(f"Adding structured output tasks...")
        tasks += [
            extract_with_structured_output(test_case=test_case, model=params["model"], repetition=repetition)
            for repetition, params, test_case in trials
        ]
        print(f"Have {len(tasks)} tasks.")
    if TEST_FUNCTION_CALLING:
        print(f"Adding function calling tasks...")
        tasks += [
            call_collector(agent_params=params, test_case=test_case, repetition=repetition)
            for repetition, params, test_case in trials
        ]
        print(f"Have {len(tasks)} tasks.")

    random.shuffle(tasks)

    print(f"Running {len(tasks)} tasks...")

    data_collector_results: list[AgentResult] = await asyncio.gather(*tasks)
    print(f"Collected {len(data_collector_results)} results")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pd.DataFrame(
        [res.evaluate() for res in data_collector_results],
    ).to_csv(f"collector_test_results_{timestamp}.csv", index=False)


if __name__ == "__main__":

    logging.disable(logging.CRITICAL)
    validate_test_cases()
    print("Running test")
    asyncio.run(run_test(num_repetitions=1, limit_to_n=None))
