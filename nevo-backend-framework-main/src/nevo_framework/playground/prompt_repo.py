import pydantic

import nevo_framework.playground.datamodel as datamodel

"""
Very simple prompt repository.
It loads and saves prompts from/to a JSON file.
This can be replaced with a database backed solution later.
"""


class PromptRepo:
    def __init__(self):
        self._prompt_directory: datamodel.PromptDirectory = datamodel.PromptDirectory()
        self._prompt_index: dict[tuple[str, str], datamodel.Prompt] = {}

    def _update_index(self):
        """
        Update the index of prompts for fast lookup.
        """
        self._prompt_index = {(prompt.ai_species, prompt.name): prompt for prompt in self._prompt_directory.prompts}

    def get_as_json(self) -> str:
        """
        Get the prompt directory as a JSON string.
        """
        return self._prompt_directory.model_dump_json(indent=2)

    def init_to_default(self):
        """
        Initialize the repository to the default prompts.
        This will overwrite any existing prompts in the repository.
        """
        self._prompt_directory = datamodel.PromptDirectory(
            prompts=[
                datamodel.Prompt(
                    name="default",
                    ai_species="default",
                    prompt="You are a helpful assistant.",
                    description="Default prompt for the repository.",
                ),
                datamodel.Prompt(
                    name="translation",
                    ai_species="default",
                    prompt="You translate whatever I say into the target language. The target language is English. Do not add any other text.",
                    description="Translation prompt.",
                ),
            ]
        )
        self._update_index()

    def load_from_file(self, file_path: str):
        """
        Load the repository from a JSON file.
        """
        try:
            with open(file_path, "r") as file:
                self._prompt_directory = datamodel.PromptDirectory.model_validate_json(file.read())
            self._update_index()
        except pydantic.ValidationError as e:
            raise ValueError(f"Failed to validate prompts: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"File {file_path} not found.")
        except Exception as e:
            raise ValueError(f"Failed to load prompts from file: {e}")

    def save_to_file(self, file_path: str):
        """
        Save the repository to a JSON file.
        This will overwrite the file if it exists.
        """
        try:
            with open(file_path, "w") as file:
                file.write(self._prompt_directory.model_dump_json(indent=2))
        except Exception as e:
            raise ValueError(f"Failed to save prompts to file: {e}")

    def get_prompt(self, ai_species: str, prompt_name: str) -> datamodel.Prompt | None:
        """
        Get a prompt for a model by name.
        """
        return self._prompt_index.get((ai_species, prompt_name), None)

    def update_prompt(self, prompt: datamodel.Prompt):
        """
        Update a prompt in the repository. Fails if the prompt does not exist.
        """
        if existing_prompt := self.get_prompt(prompt.ai_species, prompt.name):
            existing_prompt.prompt = prompt.prompt
            existing_prompt.description = prompt.description
        else:
            raise ValueError(f"Prompt with name {prompt.name} for AI species {prompt.ai_species} does not exist.")

    def get_prompt_list(self, ai_species: str) -> datamodel.PromptList:
        """
        Get a list of all prompt names in the repository for a specific AI species, sorted by name.
        """
        items = [
            datamodel.PromptListItem(name=prompt.name, description=prompt.description)
            for prompt in self._prompt_directory.prompts
            if prompt.ai_species == ai_species
        ]
        return datamodel.PromptList(prompts=sorted(items, key=lambda item: item.name))
