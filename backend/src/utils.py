import base64
import os
from io import BytesIO
from fastapi import UploadFile, HTTPException, status 
import re
from typing import List, Dict, Tuple
from src.anki import AnkiService


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


async def apply_auto_changes_for_chunk(
    chunk: List[Dict], 
    new_cards_chunk: List[List[Dict]], 
    deck_name: str,
    anki_service: AnkiService
):
    """
    For each old card in 'chunk', we either:
      - If new_cards == 1 => update old note in place
      - If new_cards >= 2 => delete old note, create brand-new notes
      - If new_cards == 0 => NO_CHANGES
    Returns a list of BeforeAfterCard for each operation.
    """
    results = []
    for idx, old_card in enumerate(chunk):
        note_id = old_card["noteId"]
        old_front = old_card["Front"]
        old_back = old_card["Back"]

        # If the new_cards_chunk array is missing or not a list, skip
        if idx >= len(new_cards_chunk) or not isinstance(new_cards_chunk[idx], list):
            # No new data => skip
            results.append({
                'noteId': note_id,
                'beforeFront': old_front,
                'beforeBack': old_back,
                'afterFront': old_front,
                'afterBack': old_back,
                'Status': "NO_CHANGES"
            })
            continue

        new_cards = new_cards_chunk[idx]

        # Cases:
        if not new_cards:  # empty
            results.append({
                'noteId': note_id,
                'beforeFront': old_front,
                'beforeBack': old_back,
                'afterFront': old_front,
                'afterBack': old_back,
                'Status': "NO_CHANGES"
            })
            continue

        if len(new_cards) == 1:
            # Exactly 1 => update old note in place
            first_new = new_cards[0]
            new_front = first_new.get("Front", old_front)
            new_back = first_new.get("Back", old_back)

            update_resp = await anki_service.update_card(note_id, new_front, new_back)
            if not update_resp["success"]:
                results.append({
                    'noteId': note_id,
                    'beforeFront': old_front,
                    'beforeBack': old_back,
                    'afterFront': new_front,
                    'afterBack': new_back,
                    'Status': update_resp["error"]
                })
            else:
                results.append({
                    'noteId': note_id,
                    'beforeFront': old_front,
                    'beforeBack': old_back,
                    'afterFront': new_front,
                    'afterBack': new_back,
                    'Status': "OK"
                })

        else:
            # 2 or more => delete old note + create brand-new notes
            del_resp = await anki_service.delete_note(note_id)
            if not del_resp["success"]:
                # If can't delete, skip
                results.append({
                    'noteId': note_id,
                    'beforeFront': old_front,
                    'beforeBack': old_back,
                    'afterFront': old_front,
                    'afterBack': old_back,
                    'Status': f"DELETE_ERROR: {del_resp['error']}"
                })
                continue

            # Record that old note was deleted
            
            results.append({
                'noteId': note_id,
                'beforeFront': old_front,
                'beforeBack': old_back,
                'afterFront': "(deleted)",
                'afterBack': "(deleted)",
                'Status': "DELETED_OLD"
            })

            # Create brand-new notes for each new card
            for c in new_cards:
                ext_front = c.get("Front", "")
                ext_back = c.get("Back", "")
                add_resp = await anki_service.add_card(deck_name, ext_front, ext_back)
                status = "OK" if add_resp["success"] else add_resp.get("error", "Unknown error")
                
                results.append({
                    'noteId': add_resp.get("noteId", 0),
                    'beforeFront': "(new card)",
                    'beforeBack': "(new card)",
                    'afterFront': ext_front,
                    'afterBack': ext_back,
                    'Status': status
                })
    results = [card.model_dump() for card in results]
    print(f"results = {results}")
    return results


def apply_manual_changes_for_chunk(chunk, new_cards_chunk):
    """
    Process a batch of changed cards for manual review.
    Does NOT apply changes to Anki.
    Returns the old card with a list of possible new replacements.
    """
    results = []

    for idx, old_card in enumerate(chunk):
        if idx >= len(new_cards_chunk) or not isinstance(new_cards_chunk[idx], list):
            continue  # Skip if no new changes

        new_cards = new_cards_chunk[idx]  # List of new suggestions
        note_id = old_card["noteId"]
        old_front = old_card["Front"]
        old_back = old_card["Back"]

        print(f"old_card = {old_card}")
        print(f"new_cards_chunk[idx] = {new_cards}")

        # Convert new suggestions into structured dictionary format
        new_suggestions = [{"Front": new_card.get("Front", ""), "Back": new_card.get("Back", "")} for new_card in new_cards]

        # Store the original card along with new suggested replacements
        results.append({
            "noteId": note_id,
            "Front": old_front,
            "Back": old_back,
            "New": new_suggestions
        })

    return results
