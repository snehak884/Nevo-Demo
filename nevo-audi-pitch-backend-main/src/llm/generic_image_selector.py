import logging
import os
import random
from collections import defaultdict
from os import path

from pydantic import BaseModel

from nevo_framework.helpers.logging_helpers import LogAi
from llm import messages as server_messages


class GenericImage(BaseModel):
    car: str
    file_path: str


class ImageBase(BaseModel):
    images: list[GenericImage]


def _create_lookup():
    image_list = "documents/audi_documents/generic_images_169.json"
    with open(image_list) as f:
        mood_base = ImageBase.model_validate_json(f.read())
        lookup = defaultdict(list)
        for image in mood_base.images:
            lookup[image.car].append(image.file_path)
        for key in lookup:
            images = lookup[key]
            lookup[key] = random.sample(images, len(images))
        return lookup
    raise FileNotFoundError(f"Image list not found: {image_list}")


LOOKUP = _create_lookup()


def _pick_generic_image(car: str) -> str | None:
    if images := LOOKUP.get(car):
        return random.choice(images)
    return None


def get_generic_image(car_model: str | None) -> server_messages.ShowImage | None:
    if car_model:
        # find out whether we are already sending a show_image message
        if image_path := _pick_generic_image(car_model):
            logging.info(LogAi(f"Added generic image with path {image_path} for {car_model} to response."))
            return server_messages.ShowImage(image=image_path, layout_hint="full")
        else:
            logging.error(LogAi(f"get_generic_image: No generic image found for {car_model}"))
    else:
        logging.error(LogAi("maybe_add_generic_image: No car model provided."))
    return None


if __name__ == "__main__":
    if True:

        def get_name(file_path):
            return path.splitext(path.basename(file_path))[0]

        new_image_dir = "/Users/blumenthalbarby/Desktop/audi mood 169"
        new_image_files = [f for f in os.listdir(new_image_dir) if f.endswith(".jpeg")]

        with open("documents/audi_documents/generic_images.json") as f:
            mood_base = ImageBase.model_validate_json(f.read())

        print(get_name(mood_base.images[0].file_path))

        new_image_base = ImageBase(images=[])

        for file in new_image_files:
            matching_image = next((i for i in mood_base.images if get_name(i.file_path) == get_name(file)), None)
            if matching_image:
                # print(f"Found matching image for {file}: {matching_image.car}")
                new_image_base.images.append(GenericImage(car=matching_image.car, file_path=f"audi/generic/{file}"))
            else:
                print(f"No matching image found for {file}")

        with open("documents/audi_documents/generic_images_169.json", "w") as f:
            f.write(new_image_base.model_dump_json(indent=2))

    elif False:  # generate the JSON
        frontend_image_dir = "/Users/blumenthalbarby/dev/skoda-sales-bot-frontend/public"
        images = []
        for dirpath, dirnames, filenames in os.walk("/Users/blumenthalbarby/Downloads/mood_images"):
            for file in (f for f in filenames if f.lower().endswith(".jpg")):
                path_components = os.path.split(dirpath)
                car = path_components[-1]
                if not car.startswith("Audi"):
                    car = f"Audi {car}"
                print(path_components[-1])
                print(path.join(dirpath, file))
                mi = GenericImage(car=car, file_path=f"audi/generic/{car}/{file}")
                frontend_path = path.join(frontend_image_dir, mi.file_path)
                assert path.exists(frontend_path), f"File not found: {frontend_path}"
                images.append(mi)

        mood_image_base = ImageBase(images=images)
        with open("documents/audi_documents/generic_images.json", "w") as f:
            f.write(mood_image_base.model_dump_json(indent=2))

    else:
        print(_pick_generic_image("A3"))
        print(_pick_generic_image("A3"))
        print(_pick_generic_image("A3"))
