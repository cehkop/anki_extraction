# backend/src/main.py

from fastapi import (
    FastAPI,
    HTTPException,
    File,
    UploadFile,
    Form,
    Depends,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import os
import dotenv
import httpx
from typing import List, Dict, Any
import logging
from io import BytesIO
from pathlib import Path
import asyncio

from src.utils import image_to_base64, read_and_validate_image
from src.processing import extract_pairs_from_text, extract_pairs_from_image
from src.anki import get_anki_client, add_card_to_anki, get_decks_from_anki

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

dotenv.load_dotenv()

# Define the Anki-Connect endpoint and default deck name
DEFAULT_DECK_NAME = os.getenv("DEFAULT_DECK_NAME", "test")

# Pydantic models
class InputData(BaseModel):
    text: str = Field(..., description="Text to process")
    deckName: str = Field(..., description="Anki deck name")

    @validator("deckName")
    def deck_name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("deckName cannot be empty")
        return v


class ExtractTextInput(BaseModel):
    text: str


class AddCardsInput(BaseModel):
    deckName: str
    pairs: List[Dict[str, Any]]


class CardStatus(BaseModel):
    Status: bool
    Front: str
    Back: str


class DecksResponse(BaseModel):
    decks: List[str]


# API endpoint to process text
@app.post(
    "/process_text",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
async def process_text(
    input_data: InputData, anki_client: httpx.AsyncClient = Depends(get_anki_client)
):
    text = input_data.text
    deckName = input_data.deckName or DEFAULT_DECK_NAME

    logger.info("Processing text. Deck name: %s", deckName)
    logger.info("Text: %s", text)

    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No text provided."
        )

    # Await the asynchronous extract_pairs_from_text
    pairs = await extract_pairs_from_text(text)

    if not pairs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No pairs extracted."
        )

    # Add pairs to Anki
    pairs_status = []
    for pair in pairs:
        front = pair.get("Front")
        back = pair.get("Back")
        if front and back:
            try:
                anki_status = await add_card_to_anki(anki_client, deckName, front, back)
                pairs_status.append({"Status": anki_status, "Front": front, "Back": back})
            except Exception as e:
                logging.error(f"Error adding card for Front: {front}, Back: {back}. {str(e)}")
                pairs_status.append({"Status": False, "Front": front, "Back": back})

    return {"status": pairs_status}


# Endpoint to process multiple images
@app.post(
    "/process_images",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
async def process_images(
    files: List[UploadFile] = File(...),
    deckName: str = Form(...),
    anki_client: httpx.AsyncClient = Depends(get_anki_client),
):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded."
        )

    deckName = deckName or DEFAULT_DECK_NAME

    logger.info("Processing images...")
    logger.info("Deck name: %s", deckName)

    async def process_single_image(file: UploadFile):
        filename = Path(file.filename).name
        try:
            content = await read_and_validate_image(file)
            base64_image = image_to_base64(BytesIO(content))

            # Await the asynchronous extract_pairs_from_image
            pairs = await extract_pairs_from_image(base64_image, image_caption=filename)
            logger.info("Pairs extracted from %s: %s", filename, pairs)

            if not pairs:
                return {
                    "Image": filename,
                    "Status": False,
                    "Detail": "No pairs extracted from the image.",
                }

            # Add pairs to Anki
            pairs_status = []
            for pair in pairs:
                front = pair.get("Front")
                back = pair.get("Back")
                if front and back:
                    anki_status = await add_card_to_anki(anki_client, deckName, front, back)
                    pairs_status.append(CardStatus(Status=anki_status, Front=front, Back=back)
                    )

            return {
                "Image": filename,
                "Status": True,
                "Pairs": pairs_status,
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

    return {"pairs": results}


# Endpoint to upload an image and process it
@app.post(
    "/upload_image",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    file: UploadFile = File(...),
    deckName: str = Form(DEFAULT_DECK_NAME),
    anki_client: httpx.AsyncClient = Depends(get_anki_client),
):
    filename = Path(file.filename).name

    try:
        content = await read_and_validate_image(file)
        base64_image = image_to_base64(BytesIO(content))

        # Assuming extract_pairs_from_image is synchronous
        pairs = await asyncio.to_thread(
            extract_pairs_from_image, base64_image, image_caption=filename
        )
        logger.info("Pairs extracted from %s: %s", filename, pairs)

        if not pairs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pairs extracted from the image.",
            )

        # Add pairs to Anki
        pairs_status = []
        for pair in pairs:
            front = pair.get("Front")
            back = pair.get("Back")
            if front and back:
                anki_status = await add_card_to_anki(anki_client, deckName, front, back)
                pairs_status.append(CardStatus(Status=anki_status, Front=front, Back=back))

        return {"status": pairs_status}
    except Exception as e:
        logger.exception(f"Failed to process image {filename}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image: {str(e)}",
        )


# Endpoint to get all decks
@app.get("/get_decks", response_model=DecksResponse)
async def get_decks(anki_client: httpx.AsyncClient = Depends(get_anki_client)):
    decks = await get_decks_from_anki(anki_client)
    if decks is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch decks from Anki.",
        )
    return {"decks": decks}


# Extract pairs from text
@app.post(
    "/extract_text",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def extract_text(input_data: ExtractTextInput):
    text = input_data.text
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No text provided."
        )

    # Await the asynchronous function
    pairs = await extract_pairs_from_text(text)
    logger.info("Pairs extracted: %s", pairs)
    
    if not pairs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No pairs extracted."
        )
    
    return {"pairs": pairs}


# Add selected cards to Anki
@app.post(
    "/add_cards",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
async def add_cards(
    input_data: AddCardsInput, anki_client: httpx.AsyncClient = Depends(get_anki_client)
):    
    deckName = input_data.deckName or DEFAULT_DECK_NAME
    pairs = input_data.pairs

    if not pairs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No pairs provided."
        )

    pairs_status = []
    for pair in pairs:
        front = pair.get("Front")
        back = pair.get("Back")
        if front and back:
            try:
                anki_status = await add_card_to_anki(anki_client, deckName, front, back)
                pairs_status.append({
                    "Status": anki_status,
                    "Front": front,
                    "Back": back,
                })
            except Exception as e:
                logging.error(f"Error adding card for Front: {front}, Back: {back}. {str(e)}")
                pairs_status.append({
                    "Status": False,
                    "Front": front,
                    "Back": back,
                })

    # If no cards were successfully processed, return a detailed error
    if not pairs_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid cards could be added.",
        )

    return {"status": pairs_status}



# Extract pairs from images
@app.post(
    "/extract_images",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def extract_images(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded."
        )

    logger.info("Count of files: %s", len(files))

    all_pairs = []

    async def extract_pairs_from_single_image(file: UploadFile):
        filename = file.filename
        try:
            content = await read_and_validate_image(file)
            binary_stream = BytesIO(content)  # Convert content to BytesIO
            base64_image = image_to_base64(binary_stream)  # Pass binary stream

            # Await the asynchronous extract_pairs_from_image
            pairs = await extract_pairs_from_image(base64_image, image_caption=filename)
            logger.info("Pairs extracted from %s: %s", filename, pairs)

            return [
                {
                    "Status": True,
                    "Front": pair.get("Front"),
                    "Back": pair.get("Back"),
                }
                for pair in pairs
            ] if pairs else []
        except Exception as e:
            logger.exception(f"Failed to process image {filename}")
            return []

    # Process images in parallel
    results = await asyncio.gather(
        *(extract_pairs_from_single_image(file) for file in files)
    )

    # Flatten list of pairs from all images
    for image_pairs in results:
        all_pairs.extend(image_pairs)

    if not all_pairs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pairs extracted from images.",
        )

    return {"pairs": all_pairs}


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:2342"],  # Use the exact frontend origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Explicitly allow OPTIONS
    allow_headers=["Content-Type", "Authorization"],  # Adjust as needed
)
