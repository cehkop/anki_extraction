# backend/src/main.py

from fastapi import (
    FastAPI,
    HTTPException,
    File,
    UploadFile,
    Form,
    status,
    Body,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
import dotenv
import logging
from io import BytesIO
import sys
import asyncio
from typing import Dict, List, Any, Optional

from src.utils import (
    image_to_base64, 
    read_and_validate_image, 
    apply_auto_changes_for_chunk, 
    apply_manual_changes_for_chunk,
    remove_sound_tags,
    )
from src.processing import extract_pairs_from_text, extract_pairs_from_image, change_anki_pairs
from src.anki import AnkiService

dotenv.load_dotenv()

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="logs.txt",
    filemode="a",
)
logger = logging.getLogger(__name__)
logger.addHandler(handler)

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

class DeckRequest(BaseModel):
    deck_name: str

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

class RedCardsResponse(BaseModel):
    cards: List[RedCardModel] = Field(...)

class BeforeAfterCard(BaseModel):
    noteId: int
    beforeFront: str
    beforeBack: str
    afterFront: str
    afterBack: str
    Status: str

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
    
    logger.info(f"All extracted cards: {all_cards}")
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
        return RedCardsResponse(cards=[])

    cards_info = await anki_service.cards_info(card_ids)
    # Convert to RedCardModel (Front/Back only)
    red_cards = []
    for card_info in cards_info:
        note_id = card_info.get("noteId")
        fields = card_info.get("fields", {})
        front_value = fields.get("Front", {}).get("value", "")
        back_value = fields.get("Back", {}).get("value", "")
        red_cards.append(RedCardModel(
            noteId=note_id,
            Front=front_value,
            Back=back_value
        ))
    logger.info(red_cards)
    return RedCardsResponse(cards=red_cards)


### 2) UPDATE CARDS RED AUTO
@app.post("/update_cards_red_auto", response_model=BeforeAfterResponse)
async def update_cards_red_auto(deck_name: str) -> BeforeAfterResponse:
    card_ids = await anki_service.get_cards_red(deck_name)
    # logger.info(f"card_ids = {card_ids}")
    cards_info = await anki_service.cards_info(card_ids)
    # logger.info(f"cards_info = {cards_info}")

    before_cards = []
    for cinfo in cards_info:
        note_id = cinfo.get("noteId")
        fields = cinfo.get("fields", {})
        front_value = fields.get("Front", {}).get("value", "")
        back_value = fields.get("Back", {}).get("value", "")
        before_cards.append({
            "noteId": note_id,
            "Front": front_value,
            "Back": back_value
        })

    results = []
    batch_size = 5
    # 1) chunk the cards and call change_anki_pairs in chunks
    for i in range(0, len(before_cards), batch_size):
        chunk = before_cards[i : i + batch_size]

        # call change_anki_pairs on this chunk
        new_cards_chunk = await change_anki_pairs(chunk)
        logger.info(f"Lenght of chunk {len(cards_info)} lenght of new_cards_chunk {len(new_cards_chunk)}")
        if len(new_cards_chunk) != len(chunk):
            logger.info(f"Warning: Expected {len(chunk)} new cards, but got {len(new_cards_chunk)}")
            continue
        logger.info(f"chunk = {chunk}")
        logger.info(f"new_cards_chunk = {new_cards_chunk}")

        # 2) apply the auto logic in a separate helper
        batch_results = await apply_auto_changes_for_chunk(
            chunk=chunk,
            new_cards_chunk=new_cards_chunk,
            deck_name=deck_name,
            anki_service=anki_service
        )
        results.extend(batch_results)
    logger.info(results)
    return BeforeAfterResponse(cards=results)


### 3) UPDATE CARDS RED MANUAL
@app.get("/update_cards_red_manual_get")
async def update_cards_red_manual_get(
    deck_name: str = Query(...),
    cards_num: int = Query(3),
):
    """
    Fetches up to `cards_num` red cards from the specified deck.
    This is a GET endpoint; parameters come in as query params:
      e.g. /update_cards_red_manual_get?deck_name=test&cards_num=10
    """
    card_ids = await anki_service.get_cards_red(deck_name)
    card_ids = card_ids[:cards_num]
    logger.info(f"Fetching red cards from the deck: {deck_name}")
    logger.info(f"card_ids: {card_ids}")
    cards_info = await anki_service.cards_info(card_ids)
    before_cards = []
    for cinfo in cards_info:
        try:
            logger.info(cinfo.__getitem__("noteId"), cinfo.__getitem__("fields"))
        except Exception as e:
            logger.error(cinfo, e)
        if not cinfo:
            continue
        
        note_id = cinfo.get("noteId")
        fields = cinfo.get("fields", {})
        front_value = fields.get("Front", {}).get("value", "")
        front_value, _ = remove_sound_tags(front_value)
        back_value = fields.get("Back", {}).get("value", "")
        back_value, _ = remove_sound_tags(back_value)
        before_cards.append({
            "noteId": note_id,
            "Front": front_value,
            "Back": back_value
        })

    results = []
    batch_size = 3
    # 1) chunk the cards and call change_anki_pairs in chunks
    for i in range(0, len(before_cards), batch_size):
        chunk = before_cards[i : i + batch_size]

        # call change_anki_pairs on this chunk
        new_cards_chunk = await change_anki_pairs(chunk)
        logger.info(f"Length of chunk {len(chunk)}, length of new_cards_chunk {len(new_cards_chunk)}")
        if len(new_cards_chunk) != len(chunk):
            logger.info(f"Warning: Expected {len(chunk)} new cards, but got {len(new_cards_chunk)}")
            logger.info(chunk)
            logger.info(new_cards_chunk)
            continue
        logger.info(f"chunk = {chunk}")
        logger.info(f"new_cards_chunk = {new_cards_chunk}")

        # 2) apply manual logic
        batch_results = apply_manual_changes_for_chunk(
            chunk=chunk,
            new_cards_chunk=new_cards_chunk
        )
        results.extend(batch_results)
    
    return results


@app.post("/update_cards_red_manual_adding")
async def update_cards_red_manual_adding(
    deckName: str = Body(...),
    data: List[Dict[str, Any]] = Body(...)
):
    """
    New logic:
      - If all are 'no' => do nothing
      - If exactly 1 'yes' => update old note
      - If more than 1 'yes' => 
          update old note with the first selected suggestion
          add new notes for the rest of selected suggestions
    """
    results = []
    logger.info("Red cards manual update")
    logger.info(f"data = \n{data}\n",'--------------','\n\n')
    for item in data:
        note_id = item["noteId"]
        old_front = item["oldFront"]
        old_back = item["oldBack"]
        suggestions = item.get("newSuggestions", [])

        # Filter for suggestions with selected = True
        selected_sugs = [s for s in suggestions if s.get("selected")]

        # Case 1: No selected suggestions => do nothing
        if not selected_sugs:
            logger.info("No selected suggestions - skipping update")
            logger.info(item)
            logger.info('---------------------------------------------------')
            results.append({
                "noteId": note_id,
                "action": "SKIP",
                "reason": "No suggestions selected"
            })
            continue

        # Case 2: Exactly 1 => update old note
        if len(selected_sugs) == 1:
            logger.info("Only one is selected - updating the old note")
            logger.info(item)
            logger.info('---------------------------------------------------')
            chosen = selected_sugs[0]
            new_front = chosen["Front"]
            new_back = chosen["Back"]
            update_resp = await anki_service.update_card(note_id, new_front, new_back)
            if not update_resp["success"]:
                status = update_resp["error"]
            else:
                status = "OK"
                
            cards_flag_yellow = await anki_service.set_note_cards_flag_yellow(note_id)
            logger.info('Change cards flag result\n'
                f'{cards_flag_yellow}\n\n')
            
            results.append({
                "noteId": note_id,
                "beforeFront": old_front,
                "beforeBack": old_back,
                "afterFront": new_front,
                "afterBack": new_back,
                "action": "UPDATE",
                "status": status,
            })

        # Case 3: 2 or more selected => 
        #    update old note with the FIRST selected
        #    then add new notes for the rest
        else:
            # 3a) Update the old note with the first suggestion
            logger.info("More than one is selected - updating the old note with the first selected suggestion")
            logger.info(item)
            logger.info('---------------------------------------------------')
            first = selected_sugs[0]
            first_front = first["Front"]
            first_back = first["Back"]
            update_resp = await anki_service.update_card(note_id, first_front, first_back)
            if not update_resp["success"]:
                # If we can't update, skip the rest
                results.append({
                    "noteId": note_id,
                    "beforeFront": old_front,
                    "beforeBack": old_back,
                    "attemptedFront": first_front,
                    "attemptedBack": first_back,
                    "action": "UPDATE_ERROR",
                    "error": update_resp["error"]
                })
                continue
            
            # Set yellow flag
            cards_flag_yellow = await anki_service.set_note_cards_flag_yellow(note_id)
            logger.info('Change cards flag result\n'
                f'{cards_flag_yellow}\n\n')
            results.append({
                "noteId": note_id,
                "beforeFront": old_front,
                "beforeBack": old_back,
                "afterFront": first_front,
                "afterBack": first_back,
                "action": "UPDATED_OLD",
                "status": "OK"
            })

            # 3b) For each additional selected, add a brand-new note
            for extra in selected_sugs[1:]:
                ext_front = extra["Front"]
                ext_back = extra["Back"]
                add_resp = await anki_service.add_card(deckName, ext_front, ext_back)
                # add_resp = {'error': 'test', 'success': False}
                if not add_resp["success"]:
                    results.append({
                        "noteId": 0,
                        "action": "ADD_ERROR",
                        "front": ext_front,
                        "back": ext_back,
                        "error": add_resp["error"]
                    })
                else:
                    results.append({
                        "noteId": add_resp["noteId"],
                        "action": "ADD_NEW",
                        "front": ext_front,
                        "back": ext_back,
                        "status": "OK"
                    })
                cards_flag_yellow = await anki_service.set_note_cards_flag_yellow(note_id)
                logger.info('Change cards flag result\n'
                    f'{cards_flag_yellow}\n\n')
                
    logger.info(f"{'------------'}\n{results}\n{'-----------'}\n\n")
    return {"status": "DONE", "results": results}


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
    allow_origins=[
        "http://localhost:2342",
        "http://127.0.0.1:2342",
    ],  # Use the exact frontend origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Explicitly allow OPTIONS
    allow_headers=["Content-Type", "Authorization"],  # Adjust as needed
)

# Event handler to close the httpx.AsyncClient on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    await anki_service.client.aclose()
