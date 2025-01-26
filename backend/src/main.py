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

from src.utils import image_to_base64, read_and_validate_image
from src.processing import extract_pairs_from_text, extract_pairs_from_image
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
