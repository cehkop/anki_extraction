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
from typing import Dict, List, Any

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

# Pydantic models
class TextInput(BaseModel):
    text: str = Field(..., description="Text to process")
    deckName: str = Field(None, description="Anki deck name")
    mode: str = Field('auto', description="Mode of operation: 'auto' or 'manual'")

    @validator("mode")
    def validate_mode(cls, v):
        if v not in ('auto', 'manual'):
            raise ValueError("Mode must be 'auto' or 'manual'")
        return v

class CardStatus(BaseModel):
    Status: bool = False
    Front: str
    Back: str
    Error: str = None
    
class CardBase(BaseModel):
    Front: str
    Back: str
    
class AddCardsInput(BaseModel):
    deckName: str
    pairs: List[Dict[str, Any]]
    
class AddCardsInputParseText(BaseModel):
    deckName: str
    pairs: str

class DecksResponse(BaseModel):
    decks: List[str]
    
class GetCardsResponse(BaseModel):
    cards: List[CardStatus]

# Consolidated text endpoint
@app.post(
    "/text",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def handle_text(
    input_data: TextInput,
):
    text = input_data.text
    deckName = input_data.deckName or DEFAULT_DECK_NAME
    mode = input_data.mode

    logger.info(f"Handling text in mode '{mode}'. Deck name: {deckName}")
    logger.info("Text: %s", text)

    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No text provided."
        )

    # Extract pairs from text
    pairs = await extract_pairs_from_text(text)

    if not pairs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No pairs extracted."
        )

    if mode == 'manual':
        # Return the extracted pairs without adding to Anki
        return {"pairs": pairs}

    elif mode == 'auto':
        # Add pairs to Anki
        results = []
        for pair in pairs:
            front = pair.get("Front")
            back = pair.get("Back")
            if front and back:
                response = await anki_service.add_card(deckName, front, back)
                if not response["success"]:
                    results.append(
                        {
                            "Status": False,
                            "Front": front,
                            "Back": back,
                            "Error": response.get("error", "Unknown error occurred."),
                        }
                    )
                else:
                    results.append({"Status": True, "Front": front, "Back": back})
        return {"status": results}

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mode. Use 'auto' or 'manual'."
        )

# Consolidated images endpoint
@app.post(
    "/images",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def handle_images(
    request: Request,
    files: List[UploadFile] = File(...),
    deckName: str = Form(None),
    mode: str = Form('manual'),
):
    deckName = deckName or DEFAULT_DECK_NAME

    if mode not in ('auto', 'manual'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mode. Use 'auto' or 'manual'."
        )

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded."
        )

    logger.info(f"Handling images in mode '{mode}'. Deck name: {deckName}")

    async def process_single_image(file: UploadFile):
        filename = Path(file.filename).name
        try:
            content = await read_and_validate_image(file)
            base64_image = image_to_base64(BytesIO(content))

            # Process the image
            pairs = await extract_pairs_from_image(base64_image, image_caption=filename)
            logger.info("Pairs extracted from %s: %s", filename, pairs)

            if not pairs:
                return {
                    "Image": filename,
                    "Status": False,
                    "Detail": "No pairs extracted from the image.",
                }

            if mode == 'manual':
                # Return the extracted pairs without adding to Anki
                return {
                    "Image": filename,
                    "Status": True,
                    "Pairs": pairs,
                }

            elif mode == 'auto':
                # Add pairs to Anki
                pairs_status = []
                for pair in pairs:
                    front = pair.get("Front")
                    back = pair.get("Back")
                    if front and back:
                        response = await anki_service.add_card(deckName, front, back)
                        if not response["success"]:
                            pairs_status.append({
                                "Status": False,
                                "Front": front,
                                "Back": back,
                                "Error": response.get("error", "Unknown error occurred."),
                            })
                        else:
                            pairs_status.append({"Status": True, "Front": front, "Back": back})

                return {
                    "Image": filename,
                    "Status": True,
                    "Pairs": pairs_status,
                }

            else:
                # Should not reach here due to earlier validation
                return {
                    "Image": filename,
                    "Status": False,
                    "Detail": "Invalid mode.",
                }

        except Exception as e:
            logger.exception(f"Failed to process image {filename}")
            return {
                "Image": filename,
                "Status": False,
                "Detail": f"Failed to process image: {str(e)}",
            }

    # Process images in parallel
    results = await asyncio.gather(*(process_single_image(file) for file in files))

    return {"results": results}


# Add selected cards to Anki
@app.post(
    "/add_cards",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
async def add_cards(input_data: AddCardsInput):
    deckName = input_data.deckName or DEFAULT_DECK_NAME
    pairs = input_data.pairs

    if not pairs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No pairs provided."
        )

    results = []
    for pair in pairs:
        front = pair.get("Front")
        back = pair.get("Back")
        if front and back:
            response = await anki_service.add_card(deckName, front, back)
            if not response["success"]:
                results.append(
                    {
                        "Status": False,
                        "Front": front,
                        "Back": back,
                        "Error": response.get("error", "Unknown error occurred."),
                    }
                )
            else:
                results.append({"Status": True, "Front": front, "Back": back})

    return {"status": results}


@app.get("/get_cards_red", response_model=List[CardBase])
async def get_cards_red(deck_name: str):
    red_cards_list = await anki_service.get_cards_red(deck_name)
    return process_sound_tags(red_cards_list)


@app.get("/update_cards_red_auto", response_model=GetCardsResponse)
async def update_cards_red_auto(deck_name: str):
    """
    Automatically updates all red cards in a specified Anki deck.

    Args:
        deck_name (str): The name of the Anki deck to update.

    Returns:
        GetCardsResponse: A list of status updates for each processed card.
    """
    # Example: Fetching red cards (replace with actual logic)
    red_cards = await get_cards_red(deck_name)
    print(f'red cards: {red_cards}')
    batch_size = 10
    results = []

    for i in range(0, len(red_cards), batch_size):
        batch = red_cards[i:i + batch_size]
        print(f'batch: {batch}')
        batch_processed = await change_anki_pairs(batch)
        print(f'batch processed: {batch_processed}')
        for pair in batch_processed:
            front = pair.get("Front")
            back = pair.get("Back")
            if front and back:
                response = await anki_service.add_card(deck_name, front, back)
                if not response["success"]:
                    results.append(
                        {
                            "Status": False,
                            "Front": front,
                            "Back": back,
                            "Error": response.get("error", "Unknown error occurred."),
                        }
                    )
                else:
                    results.append({"Status": True, "Front": front, "Back": back})
    print(f'cards: {results}')
    return {"cards": results}


@app.get("/update_cards_red_manual", response_model=GetCardsResponse)
async def update_cards_red_manual(input_data: AddCardsInput):
    """
    Manually updates specified red cards in batches.

    Args:
        input_data (AddCardsInput): Input containing the deck name and card pairs.

    Returns:
        GetCardsResponse: A list of status updates for each processed card.
    """
    deckName = input_data.deckName or DEFAULT_DECK_NAME
    pairs = input_data.pairs
    batch_size = 10
    results = []

    for i in range(0, len(pairs), batch_size):
        batch = pairs[i:i + batch_size]
        for pair in batch:
            front = pair.get("Front")
            back = pair.get("Back")
            if front and back:
                response = await anki_service.add_card(deckName, front, back)
                if not response["success"]:
                    results.append(
                        {
                            "Status": False,
                            "Front": front,
                            "Back": back,
                            "Error": response.get("error", "Unknown error occurred."),
                        }
                    )
                else:
                    results.append({"Status": True, "Front": front, "Back": back})

    return {"status": results}


@app.post("/full_manual_add_cards")
async def full_manual_add_cards(input_data: AddCardsInputParseText):
    """
    Parses raw text pairs and adds them to Anki.

    Args:
        input_data (AddCardsInputParseText): Raw text pairs to parse and process.

    Returns:
        GetCardsResponse: A list of status updates for each processed card.
    """
    deckName = input_data.deckName or DEFAULT_DECK_NAME
    raw_pairs = input_data.pairs
    parsed_pairs = []

    # Parse raw pairs into structured dictionary
    try:
        lines = raw_pairs.splitlines()
        for i in range(0, len(lines), 2):
            front = lines[i].replace("Front:", "").strip()
            back = lines[i + 1].replace("Back:", "").strip()
            parsed_pairs.append({"Front": front, "Back": back})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing pairs: {e}")

    # Process pairs
    results = []
    for pair in parsed_pairs:
        front = pair.get("Front")
        back = pair.get("Back")
        if front and back:
            response = await anki_service.add_card(deckName, front, back)
            if not response["success"]:
                results.append(
                    {
                        "Status": False,
                        "Front": front,
                        "Back": back,
                        "Error": response.get("error", "Unknown error occurred."),
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
