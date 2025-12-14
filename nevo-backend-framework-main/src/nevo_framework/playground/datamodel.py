from pydantic import BaseModel
from pydantic import Field

"""
This module contains the data models used in the API.
"""


class Prompt(BaseModel):
    """
    A prompt for an AI agent used by an AI model.
    """
    name: str = Field(..., description="The name of the prompt. This is a unique identifier for the prompt.")
    ai_species: str = Field(..., description="The AI 'species' (i.e. the multiagent) that uses this prompt.")
    prompt: str = Field(..., description="The actual prompt text.")
    description: str | None = Field(None, description="A description of the prompt.")


class PromptListItem(BaseModel):
    """
    An item in a list of available prompt names, with optional description.
    """
    name: str = Field(..., description="The name of the prompt.")
    description: str | None = Field(None, description="A description of the prompt.")


class PromptList(BaseModel):
    """
    A list of available prompts for a specific AI species.
    """
    prompts: list[PromptListItem] = Field(default_factory=list, description="A list of available prompts.")


class PromptDirectory(BaseModel):
    prompts: list[Prompt] = Field(default_factory=list)
