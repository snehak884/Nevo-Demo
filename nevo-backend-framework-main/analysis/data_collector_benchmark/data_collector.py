from dataclasses import dataclass


@dataclass
class DataCollector:
    """Data class for storing information about a function and its arguments"""

    function_name: str
    function_description: str
    argument_name: str
    argument_data_type: str
    argument_description: str
    argument_enum: list[str] = None
    system_message: str = None
    linked_to_agent: str = None
