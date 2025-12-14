"""
Script which goes through a set of specifications for cars in a folder and converts them to more
prose-like files for RAG
"""
import os
import openai
from dotenv import load_dotenv
from typing import Generator
import argparse
import logging
import time


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
FORMAT = '%(asctime)s - %(message)s'
logging.basicConfig(format=FORMAT)

load_dotenv()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SUMMARY_PROMPT = (
    "Here is some information on a model of car. Could you convert this into a three paragraph document "
    "that does not exclude any important information and would give a potential customer a good understanding "
    "of the ALL of the features of the car. At the beginning of each paragraph you must mention the model "
    "name, engine size and engine type:\n\n {car_overview}"
)


def generate_summary(model: str, car_info: str) -> str:
    """Function which generates a summary of a car model based on its specifications
    
    Args:
        model (str): The model of the car
        car_info (str): The specifications of the car

    Returns:
        str: The summary of the car
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert Skoda marketing and sales representative."
            },
            {
                "role": "user",
                "content": car_info
            }
        ],
        temperature=0.0
    )

    return response.choices[0].message.content

def load_files(folder: str) -> Generator:
    """Function which cycles through each .txt file in the folder variable and returns the contents of the file"""
    for file in os.listdir(folder):
        if file.endswith(".txt"):
            with open(os.path.join(folder, file), "r") as f:
                yield f.read(), file

def main():
    logger.info("Starting conversion of files")
    parser = argparse.ArgumentParser(description="Convert car specifications to prose-like files")
    parser.add_argument("--load_folder", type=str, default = "", help="Folder to search for files to process")
    parser.add_argument("--save_folder", type=str, default = "", help="Folder to search for files to process")
    args = parser.parse_args()

    car_specs = load_files(args.load_folder)

    if not os.path.exists(args.save_folder):
        os.makedirs(args.save_folder)
        logger.info(f"Creating folder {args.save_folder}")

    i = 0

    for spec, filename in car_specs:
        i += 1
        summary = generate_summary("gpt-4o", SUMMARY_PROMPT.format(car_overview=spec))
        sections = summary.split("\n\n")
        for i, section in enumerate(sections):
            save_path = os.path.join(args.save_folder,f"{filename}_part{i}.txt")
            with open(save_path, "w") as f:    
                logger.info(f"Writing section {i} to {save_path}")
                f.write(section)
        
        if i > 2:
            break

if __name__ == "__main__":
    main()