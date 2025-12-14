from typing import Literal

from pydantic import BaseModel


class BackofficeDataMessage(BaseModel):
    """Server to backend message to send backoffice data."""

    type: Literal["backoffice_data"] = "backoffice_data"
    name: str
    car: str
    date: str
    time: str
    profile_summary: str | None
    conversation_summary: str | None


class ShowImage(BaseModel):
    """Server-to-frontend-message to show images.

    Attributes:
        image: The path to the image to be shown.
        image2: The path to a second image to be shown. Optional.
        text: Text to be shown below the first image.
        text2: Text to be shown below the second image. Optional.
        layout_hint: Indicates how the images should be displayed.

    Layout hints:
        - "full": Show the image maximally extended.
        - "compare": Show the image(s) side by side. Images are side by side auomatically
          if two images are provided. If "compare" is set, also a single image is shown
          in the side by side layout, leaving the other side empty.
    """

    type: Literal["show_image"] = "show_image"
    image: str
    image2: str | None = None
    text: str | None = None
    text2: str | None = None
    layout_hint: Literal["full", "compare", "walkaround"] | None = None


class ShowForm(BaseModel):
    """Server to frontend message to show a form."""

    type: Literal["show_form"] = "show_form"
    zip_code: str
    preferred_date: str
    preferred_time: str
    car_model: str
    email: str | None = None
    phone_number: str | None = None
    image: str | None = None  # image of the car model to be shown to make the form nicer


class ContactAndConsentResponse(BaseModel):
    """Client to server message to indicate the user's contact information and consent."""

    type: Literal["contact_and_consent_response"] = "contact_and_consent_response"
    phone_number: str | None
    email: str | None
    contact_consent: bool


class CarWalkaroundResponse(BaseModel):
    """Client to server message to indicate the user's response to the car walkaround."""

    type: Literal["car_walkaround_response"] = "car_walkaround_response"
    current_image: str
    clicked: Literal["left", "right"]


class RequestBackofficeData(BaseModel):
    type: Literal["request_backoffice_data"] = "request_backoffice_data"


class BackofficeMessage(BaseModel):
    type: Literal["backoffice_data"] = "backoffice_data"
    name: str
    car: str
    date: str
    time: str
    profile_summary: str | None
    conversation_summary: str | None
