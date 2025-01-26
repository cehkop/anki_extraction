import base64
import os
from io import BytesIO
from fastapi import UploadFile, HTTPException, status
import aiofiles
import re
from typing import List, Dict, Tuple


# Function to convert an image file to base64 format
def image_to_base64(image):
    """
    Convert an image file or binary stream to a Base64 encoded string.
    :param image: File path (str) or BytesIO object
    :return: Base64 encoded string
    """
    if isinstance(image, (str, bytes, os.PathLike)):
        # If image is a file path
        with open(image, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    elif isinstance(image, BytesIO):
        # If image is a binary stream
        return base64.b64encode(image.read()).decode("utf-8")
    else:
        raise TypeError("Expected a file path or BytesIO object.")
    
    
async def read_and_validate_image(file: UploadFile) -> bytes:
    # Validate the image content-type
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg", "image/webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Invalid image type: {file.filename}"
        )

    # Read the file content asynchronously
    content = await file.read()

    # Check file size (limit to 5MB)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large: {file.filename}",
        )
    return content


def process_sound_tags(cards: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Process cards to handle sound tags.
    
    Args:
        cards (List[Dict[str, str]]): List of cards with 'Front' and 'Back' fields.
    
    Returns:
        Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        - Updated cards with `[sound:...]` tags removed from 'Front' and 'Back'.
        - A separate list of stored sound tags with their associated text.
    """
    updated_cards = []
    sound_tags = []
    
    print("Processing sound tags...")

    for card in cards:
        print("Processing card:", card)
        updated_card = {}
        front_text, front_sounds = remove_sound_tags(card.get("Front", ""))
        back_text, back_sounds = remove_sound_tags(card.get("Back", ""))

        updated_card["Front"] = front_text
        updated_card["Back"] = back_text
        updated_cards.append(updated_card)

        # Store sound tags separately with their associated text
        if front_sounds:
            sound_tags.append({"Field": "Front", "Text": card["Front"], "Sounds": front_sounds})
        if back_sounds:
            sound_tags.append({"Field": "Back", "Text": card["Back"], "Sounds": back_sounds})

    return updated_cards


def remove_sound_tags(text: str) -> Tuple[str, List[str]]:
    """
    Remove `[sound:...]` tags from the input text and return the cleaned text and extracted sounds.
    
    Args:
        text (str): Input text potentially containing `[sound:...]` tags.
    
    Returns:
        Tuple[str, List[str]]:
        - Cleaned text without `[sound:...]` tags.
        - List of extracted sound tags.
    """
    sound_pattern = re.compile(r"\[sound:[^\]]+\]")
    sounds = sound_pattern.findall(text)  # Extract all `[sound:...]` tags
    cleaned_text = sound_pattern.sub("", text).strip()  # Remove tags and clean up
    return cleaned_text, sounds
