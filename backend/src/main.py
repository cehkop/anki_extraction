# backend/src/main.py

from fastapi import (
    FastAPI,
    HTTPException,
    File,
    UploadFile,
    Form,
    Request,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import os
import dotenv
import logging
from io import BytesIO
from pathlib import Path
import asyncio
from typing import Dict, List, Any, Optional

from src.utils import image_to_base64, read_and_validate_image, process_sound_tags
from src.processing import extract_pairs_from_text, extract_pairs_from_image, change_anki_pairs
from src.anki import AnkiService

dotenv.load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="logs.txt",
    filemode="a",
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Define the Anki-Connect endpoint and default deck name
DEFAULT_DECK_NAME = os.getenv("DEFAULT_DECK_NAME", "test")
ANKI_CONNECT_URL = os.getenv("ANKI_CONNECT_URL", "http://localhost:8765")

# Initialize AnkiService
anki_service = AnkiService(ANKI_CONNECT_URL)
    
# Each card has Front, Back, and an optional Status (holding "OK" or the error message).
class CardModel(BaseModel):
    Front: str = Field(..., description="Front text of the card")
    Back: str = Field(..., description="Back text of the card")
    Status: Optional[str] = Field(None, description="OK if added successfully, or error message")

# The request body for /add_cards
class AddCardsInput(BaseModel):
    deckName: Optional[str] = Field(None, description="Anki deck name")
    pairs: List[CardModel] = Field(..., description="List of cards to add")

# The unified response model for both /process and /add_cards
class CardsResponse(BaseModel):
    cards: List[CardModel] = Field(..., description="List of processed cards with optional status")

class DecksResponse(BaseModel):
    decks: List[str]

class RedCardModel(BaseModel):
    noteId: int = Field(..., description="The note ID in Anki")
    Front: str = Field(..., description="Existing front text")
    Back: str = Field(..., description="Existing back text")

class CardsResponse(BaseModel):
    cards: List[RedCardModel] = Field(...)

class BeforeAfterCard(BaseModel):
    noteId: int
    beforeFront: str
    beforeBack: str
    afterFront: str
    afterBack: str
    Status: str = Field("OK", description="OK or error message")

class BeforeAfterResponse(BaseModel):
    cards: List[BeforeAfterCard]

class FullManualAddCardsInput(BaseModel):
    deckName: str = Field(None)
    pairs: str = Field(...)

# Consolidated endpoint
@app.post("/process", response_model=CardsResponse, status_code=status.HTTP_200_OK)
async def handle_process(
    text: Optional[str] = Form(None),
    files: List[UploadFile] = File([]),
    deckName: Optional[str] = Form(None),
    mode: str = Form("manual"),
) -> CardsResponse:
    """
    Single endpoint for text + images:
      - manual => {"cards":[{Front, Back, Status=None}, ...]}
      - auto   => {"cards":[{Front, Back, Status='OK' or 'Error'}, ...]}
    """
    deckName = deckName or DEFAULT_DECK_NAME

    if mode not in ("manual", "auto"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mode. Use 'auto' or 'manual'."
        )

    all_cards: List[CardModel] = []

    # 1) Extract from text (if provided)
    if text and text.strip():
        logger.info(f"Extracting pairs from text (mode={mode}, deck={deckName}).")
        text_pairs = await extract_pairs_from_text(text)
        # Convert each extracted pair to CardModel (Status=None by default)
        for p in text_pairs:
            all_cards.append(CardModel(Front=p["Front"], Back=p["Back"]))

    # 2) Extract from images (if provided)
    if files:
        logger.info(f"Extracting pairs from {len(files)} images (mode={mode}, deck={deckName}).")

        async def process_image(upload: UploadFile):
            try:
                content = await read_and_validate_image(upload)
                base64_img = image_to_base64(BytesIO(content))
                pairs = await extract_pairs_from_image(base64_img, image_caption=upload.filename)
                # Return list of CardModel
                return [CardModel(Front=p["Front"], Back=p["Back"]) for p in pairs]
            except Exception as e:
                logger.exception(f"Failed to process image {upload.filename}: {e}")
                return []

        image_cards_lists = await asyncio.gather(*(process_image(f) for f in files))
        for cards_list in image_cards_lists:
            all_cards.extend(cards_list)

    if not all_cards:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No cards extracted from text or images."
        )

    # 3) If 'manual', just return them with Status=None
    if mode == "manual":
        return CardsResponse(cards=all_cards)

    # 4) If 'auto', add to Anki & update Status
    for card in all_cards:
        response = await anki_service.add_card(deckName, card.Front, card.Back)
        if not response["success"]:
            card.Status = response.get("error", "Unknown error occurred.")
        else:
            card.Status = "OK"

    return CardsResponse(cards=all_cards)


# Add selected cards to Anki
@app.post("/add_cards", response_model=CardsResponse, status_code=status.HTTP_201_CREATED)
async def add_cards(input_data: AddCardsInput) -> CardsResponse:
    """
    Adds selected cards to Anki. 
    Request body: { "deckName": "...", "pairs": [ {Front, Back}, ... ] }
    Response body: { "cards": [ {Front, Back, Status="OK" or error}, ... ] }
    """
    deckName = input_data.deckName or DEFAULT_DECK_NAME
    pairs = input_data.pairs

    if not pairs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pairs provided."
        )

    results: List[CardModel] = []

    for pair in pairs:
        # We assume pair is already a CardModel from the AddCardsInput
        front = pair.Front
        back = pair.Back

        # Attempt to add
        response = await anki_service.add_card(deckName, front, back)
        if not response["success"]:
            # Save the error message in the Status
            results.append(CardModel(Front=front, Back=back, Status=response.get("error", "Unknown error occurred.")))
        else:
            results.append(CardModel(Front=front, Back=back, Status="OK"))

    return CardsResponse(cards=results)


### 1) GET RED CARDS
@app.get("/get_cards_red", response_model=CardsResponse)
async def get_cards_red(deck_name: str) -> CardsResponse:
    """
    Returns the flagged (red) cards from the given deck
    as a list of {noteId, Front, Back}.
    """
    card_ids = await anki_service.get_cards_red(deck_name)
    if not card_ids:
        return CardsResponse(cards=[])

    cards_info = await anki_service.cards_info(card_ids)
    # Convert to RedCardModel
    red_cards = []
    for card_info in cards_info:
        note_id = card_info.get("note")
        fields = card_info.get("fields", {})
        front_value = fields.get("Лицо", {}).get("value", "")
        back_value = fields.get("Оборот", {}).get("value", "")
        red_cards.append(RedCardModel(
            noteId=note_id,
            Front=front_value,
            Back=back_value
        ))

    return CardsResponse(cards=red_cards)


### 2) UPDATE CARDS RED AUTO
@app.post("/update_cards_red_auto", response_model=BeforeAfterResponse)
async def update_cards_red_auto(deck_name: str) -> BeforeAfterResponse:
    """
    Auto-process red cards:
      - If exactly 1 new card => update the old note in place.
      - If 2 or more => remove the old note + create new notes for all the new cards.
    """
    card_ids = await anki_service.get_cards_red(deck_name)
    cards_info = await anki_service.cards_info(card_ids)
    print(f"cards_info = {cards_info}")

    before_cards = []
    for cinfo in cards_info:
        note_id = cinfo["note"]
        front_value = cinfo["fields"]["Лицо"]["value"]
        back_value = cinfo["fields"]["Оборот"]["value"]
        before_cards.append({
            "noteId": note_id,
            "Front": front_value,
            "Back": back_value
        })

    results = []
    batch_size = 5

    # Process in chunks of `batch_size`
    for i in range(0, len(before_cards), batch_size):
        chunk = before_cards[i : i + batch_size]
        new_cards_chunk = await change_anki_pairs(chunk)
        print(f"new_cards_chunk = {new_cards_chunk}")

        for idx, old_card in enumerate(chunk):
            if idx >= len(new_cards_chunk) or not isinstance(new_cards_chunk[idx], list):
                # If no new data, skip
                note_id = old_card["noteId"]
                old_front = old_card["Front"]
                old_back = old_card["Back"]
                results.append(BeforeAfterCard(
                    noteId=note_id,
                    beforeFront=old_front,
                    beforeBack=old_back,
                    afterFront=old_front,
                    afterBack=old_back,
                    Status="NO_CHANGES"
                ))
                continue

            new_cards = new_cards_chunk[idx]
            note_id = old_card["noteId"]
            old_front = old_card["Front"]
            old_back = old_card["Back"]
            print(f"old_card = {old_card}")
            print(f"new_cards = {new_cards}")

            if len(new_cards) == 0:
                # No changes
                results.append(BeforeAfterCard(
                    noteId=note_id,
                    beforeFront=old_front,
                    beforeBack=old_back,
                    afterFront=old_front,
                    afterBack=old_back,
                    Status="NO_CHANGES"
                ))
                continue

            elif len(new_cards) == 1:
                # Exactly 1 => update in place
                first_new = new_cards[0]
                new_front = first_new.get("Front", old_front)
                new_back = first_new.get("Back", old_back)

                update_resp = await anki_service.update_card(note_id, new_front, new_back)
                if not update_resp["success"]:
                    results.append(BeforeAfterCard(
                        noteId=note_id,
                        beforeFront=old_front,
                        beforeBack=old_back,
                        afterFront=new_front,
                        afterBack=new_back,
                        Status=update_resp["error"]
                    ))
                else:
                    results.append(BeforeAfterCard(
                        noteId=note_id,
                        beforeFront=old_front,
                        beforeBack=old_back,
                        afterFront=new_front,
                        afterBack=new_back,
                        Status="OK"
                    ))

            else:
                # 2 or more => remove old note & add new ones
                del_resp = await anki_service.delete_note(note_id)
                if not del_resp["success"]:
                    # If can't delete, skip
                    results.append(BeforeAfterCard(
                        noteId=note_id,
                        beforeFront=old_front,
                        beforeBack=old_back,
                        afterFront=old_front,
                        afterBack=old_back,
                        Status=f"DELETE_ERROR: {del_resp['error']}"
                    ))
                    continue

                # We removed the old note, so let's record that result
                results.append(BeforeAfterCard(
                    noteId=note_id,
                    beforeFront=old_front,
                    beforeBack=old_back,
                    afterFront="(deleted)",
                    afterBack="(deleted)",
                    Status="DELETED_OLD"
                ))

                # Then add brand-new notes for all new cards
                for c in new_cards:
                    ext_front = c.get("Front", "")
                    ext_back = c.get("Back", "")
                    add_resp = await anki_service.add_card(deck_name, ext_front, ext_back)
                    status = "OK" if add_resp["success"] else add_resp.get("error", "Unknown error")

                    # noteId of the newly added card:
                    new_note_id = add_resp.get("noteId", 0)

                    results.append(BeforeAfterCard(
                        noteId=new_note_id,
                        beforeFront="(new card)",
                        beforeBack="(new card)",
                        afterFront=ext_front,
                        afterBack=ext_back,
                        Status=status
                    ))

    return BeforeAfterResponse(cards=results)


### 3) UPDATE CARDS RED MANUAL
@app.post("/update_cards_red_manual", response_model=BeforeAfterResponse)
async def update_cards_red_manual(deck_name: str) -> BeforeAfterResponse:
    """
    Fetches the red cards, calls `change_anki_pairs`,
    but returns "before" and "after" for manual user selection.
    Does NOT apply changes in Anki.
    """
    card_ids = await anki_service.get_cards_red(deck_name)
    info_list = await anki_service.cards_info(card_ids)

    before_cards = []
    for cinfo in info_list:
        note_id = cinfo.get("note")
        fields = cinfo.get("fields", {})
        front_value = fields.get("Лицо", {}).get("value", "")
        back_value = fields.get("Оборот", {}).get("value", "")
        before_cards.append({
            "noteId": note_id,
            "Front": front_value,
            "Back": back_value
        })

    new_cards = await change_anki_pairs(before_cards)

    results = []
    for old_card, new_card in zip(before_cards, new_cards):
        note_id = old_card["noteId"]
        old_front = old_card["Front"]
        old_back = old_card["Back"]
        new_front = new_card.get("Front", old_front)
        new_back = new_card.get("Back", old_back)
        # We do not call update_card here (manual flow)
        results.append(BeforeAfterCard(
            noteId=note_id,
            beforeFront=old_front,
            beforeBack=old_back,
            afterFront=new_front,
            afterBack=new_back,
            Status="NOT_APPLIED"
        ))

    return BeforeAfterResponse(cards=results)


### 4) FULL MANUAL ADD CARDS
@app.post("/full_manual_add_cards")
async def full_manual_add_cards(input_data: FullManualAddCardsInput):
    """
    Parses raw text pairs and adds them to Anki.
    Request body: { "deckName": "...", "pairs": "Front: X\nBack: Y\nFront: X2\nBack: Y2" }
    Returns { "status": [...], ... } or similar.
    """
    deck_name = input_data.deckName or DEFAULT_DECK_NAME
    raw_pairs = input_data.pairs
    parsed_pairs = []

    try:
        lines = raw_pairs.strip().splitlines()
        for i in range(0, len(lines), 2):
            front_line = lines[i].replace("Front:", "").strip()
            back_line = lines[i+1].replace("Back:", "").strip()
            parsed_pairs.append({"Front": front_line, "Back": back_line})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing pairs: {e}")

    results = []
    for pair in parsed_pairs:
        front = pair["Front"]
        back = pair["Back"]
        add_resp = await anki_service.add_card(deck_name, front, back)
        if not add_resp["success"]:
            results.append(
                {
                    "Status": False,
                    "Front": front,
                    "Back": back,
                    "Error": add_resp["error"],
                }
            )
        else:
            results.append({"Status": True, "Front": front, "Back": back})

    return {"status": results}


# Endpoint to get all decks
@app.get("/get_decks", response_model=DecksResponse)
async def get_decks():
    response = await anki_service.get_decks()
    if not response["success"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.get("error", "Failed to fetch decks."),
        )
    return {"decks": response["decks"]}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:2342"],  # Use the exact frontend origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Explicitly allow OPTIONS
    allow_headers=["Content-Type", "Authorization"],  # Adjust as needed
)

# Event handler to close the httpx.AsyncClient on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    await anki_service.client.aclose()
