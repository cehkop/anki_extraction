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
from src.anki import AnkiService

# Initialize AnkiService
ANKI_CONNECT_URL = os.getenv("ANKI_CONNECT_URL", "http://localhost:8765")
anki_service = AnkiService(ANKI_CONNECT_URL)

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
    input_data: InputData,
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
                anki_status = await anki_service.add_card(deckName, front, back)
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

            # Process the image with OpenAI API
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
                    try:
                        anki_status = await anki_service.add_card(deckName, front, back)
                        pairs_status.append({
                            "Status": anki_status,
                            "Front": front,
                            "Back": back,
                        })
                    except Exception as e:
                        logger.error(
                            f"Failed to add card for Front: {front}, Back: {back}. Error: {e}"
                        )
                        pairs_status.append({
                            "Status": False,
                            "Front": front,
                            "Back": back,
                        })

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

    # Return results in the same format as the original implementation
    return {"results": results}


# Endpoint to upload an image and process it
@app.post(
    "/upload_image",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    file: UploadFile = File(...),
    deckName: str = Form(DEFAULT_DECK_NAME),
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
                anki_status = await anki_service.add_card(deckName, front, back)
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
async def get_decks():
    response = await anki_service.get_decks()
    if not response["success"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.get("error", "Failed to fetch decks."),
        )
    return {"decks": response["decks"]}


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
            logger.exception(f"Failed to process image {filename}, error: {str(e)}")
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


@app.on_event("shutdown")
async def shutdown_event():
    await anki_service.client.aclose()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:2342"],  # Use the exact frontend origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Explicitly allow OPTIONS
    allow_headers=["Content-Type", "Authorization"],  # Adjust as needed
)
