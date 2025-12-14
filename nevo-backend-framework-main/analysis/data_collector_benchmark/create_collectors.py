"""Class for creating collectors for data"""

from analysis.data_collector_benchmark.data_collector import DataCollector
from nevo_framework.config.configuration import load_collectors_from_json

AGENT_COLLECTORS_FILENAME = "agent_collectors.json"


def create_openai_collectors() -> list[list[dict]]:
    """Function which creates the string used for OpenAI function calling

    Returns:
        list[dict]: A list of dictionaries containing the OpenAI function calling syntax for each tool
    """

    # Creating a list of tools from a JSON file
    data_collectors = load_collectors_from_json(filename=AGENT_COLLECTORS_FILENAME)
    tools = [openai_function_syntax(collector) for _, collector in data_collectors.collectors.items()]

    return tools


def openai_function_syntax(collector: DataCollector) -> dict:
    """Function for preparing the syntax for the OpenAI function calling

    Args:
        collector (DataCollector): The data collector object for creating the function syntax

    Returns:
        dict: A dictionary containing the OpenAI function calling syntax
    """

    tool = {
        "type": "function",
        "function": {
            "name": collector.function_name,
            "description": collector.function_description,
            "parameters": {
                "type": "object",
                "properties": {
                    collector.argument_name: {
                        "type": collector.argument_data_type,
                        "description": collector.argument_description,
                    }
                },
                "required": [collector.argument_name],
            },
        },
    }

    if collector.argument_enum is not None:
        tool["function"]["parameters"]["properties"][collector.argument_name]["enum"] = collector.argument_enum

    return tool  # , collector.system_message
