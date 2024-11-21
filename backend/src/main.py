# backend/src/main.py

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import dotenv
import requests
import shutil
from typing import List
import logging

from src.utils import image_to_base64
from src.processing import extract_pairs_from_text, extract_pairs_from_image

logging.basicConfig(level=logging.INFO, 
                    format="%(asctime)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    filename="logs.txt",
                    filemode="a"
                    )

app = FastAPI()

dotenv.load_dotenv()

# Define the Anki-Connect endpoint
ANKI_CONNECT_URL = os.getenv("ANKI_CONNECT_URL", "http://localhost:8765")

# Pydantic model for input
class Input_Data(BaseModel):
    text: str
    deckName: str 
    
    
class ExtractTextInput(BaseModel):
    text: str

class AddCardsInput(BaseModel):
    deckName: str
    pairs: List[dict]


# Function to add a card to Anki
def add_card_to_anki(deckName: str, front: str, back: str):
    payload = {
        "action": "addNote",
        "version": 6,
        "params": {
            "note": {
                "deckName": deckName,
                "modelName": "Основная (с обратной карточкой)",
                "fields": {"Лицо": front, "Оборот": back},
                "options": {
                    "allowDuplicate": False,
                    "duplicateScopeOptions": {
                        "checkChildren": True,
                        "checkAllModels": True,
                    },
                },
                "tags": [],
            }
        },
    }
    try:
        response = requests.post(ANKI_CONNECT_URL, json=payload).json()
    except requests.exceptions.RequestException as e:
        print(f"Seems like Anki or AnkiConnect is not running: {e}")
        return False

    if response.get("error"):
        print(f"Error adding card: {response['error']}")
        return False
    else:
        print(f"Added card: {front} - {back}")
    return True


# API endpoint
@app.post("/process_text")
async def process_text(input_data: Input_Data):
    text = input_data.text
    deckName = input_data.deckName
    if not deckName:
        deckName = "test"

    logging.info("Processing text. Deck name: %s", deckName)
    logging.info("Text: %s", text)

    if not text:
        raise HTTPException(status_code=400, detail="No text provided.")
    
    # Step 1: Process text with OpenAI API
    pairs = await extract_pairs_from_text(text)

    if not pairs:
        raise HTTPException(status_code=400, detail="No pairs extracted.")

    # Step 2: Add pairs to Anki
    pairs_status = []
    for pair in pairs:
        front = pair.get("Front")
        back = pair.get("Back")
        if front and back:
            status = add_card_to_anki(deckName, front, back)
            pairs_status.append({"Status": status, "Front": front, "Back": back})
    return {"status": pairs_status}


# Function to process all images in a folder
@app.post("/process_images")
async def process_images(files: List[UploadFile] = File(...),
                         deckName: str = Form(...)):
    images_folder = "uploaded_images"
    os.makedirs(images_folder, exist_ok=True)

    logging.info("Processing images...")
    logging.info("Deck name: %s", deckName)

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    results = []

    for file in files:
        # Validate the uploaded file
        if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
            raise HTTPException(status_code=400, detail=f"Invalid image type: {file.filename}")

        # Limit file size 5MB
        file_size = await file.read()
        if len(file_size) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File too large: {file.filename}")
        # Reset the file pointer after reading
        await file.seek(0)

        # Save the uploaded image
        file_path = os.path.join(images_folder, file.filename)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save image {file.filename}: {e}")

        # Convert the image to base64
        base64_image = image_to_base64(file_path)

        # Process the image with OpenAI API
        pairs = await extract_pairs_from_image(base64_image, image_caption=file.filename)
        logging.info("Pairs extracted: %s", pairs)
        if not pairs:
            results.append({
                "Image": file.filename,
                "Status": False,
                "Detail": "No pairs extracted from the image."
            })
            continue

        # Add pairs to Anki
        if not deckName:
            deckName = "test"  # Replace with your actual deck name
        pairs_status = []
        for pair in pairs:
            front = pair.get("Front")
            back = pair.get("Back")
            if front and back:
                status = add_card_to_anki(deckName, front, back)
                pairs_status.append({
                    "Status": status,
                    "Front": front,
                    "Back": back
                })
        results.append({
            "Image": file.filename,
            "Status": True,
            "Pairs": pairs_status
        })

    return {"results": results}


# Endpoint to upload an image and process it
@app.post("/upload_image")
async def upload_image(file: UploadFile = File(...)):
    # Define the folder to save images
    images_folder = "uploaded_images"
    os.makedirs(images_folder, exist_ok=True)

    # Save the uploaded image to the folder
    file_path = os.path.join(images_folder, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {e}")

    # Convert the image to base64
    base64_image = image_to_base64(file_path)

    # Process the image with OpenAI API
    pairs = await extract_pairs_from_image(base64_image, image_caption=file.filename)
    logging.info("Pairs extracted: %s", pairs)

    if not pairs:
        raise HTTPException(status_code=400, detail="No pairs extracted from the image.")

    # Add pairs to Anki
    deckName = "test"  # Replace with your actual deck name
    pairs_status = []
    for pair in pairs:
        front = pair.get("Front")
        back = pair.get("Back")
        if front and back:
            status = add_card_to_anki(deckName, front, back)
            pairs_status.append({"Status": status, "Front": front, "Back": back})

    return {"status": pairs_status}


# Function to get decks from Anki
def get_decks_from_anki():
    payload = {
        "action": "deckNames",
        "version": 6
    }
    try:
        response = requests.post(ANKI_CONNECT_URL, json=payload).json()
        if response.get("error"):
            return None
        return response.get("result", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching decks: {e}")
        return None


# Endpoint to get all decks
@app.get("/get_decks")
async def get_decks():
    decks = get_decks_from_anki()
    if decks is None:
        raise HTTPException(status_code=500, detail="Failed to fetch decks from Anki.")
    return {"decks": decks}


# Extract pairs from text
@app.post("/extract_text")
async def extract_text(input_data: ExtractTextInput):
    text = input_data.text
    if not text:
        raise HTTPException(status_code=400, detail="No text provided.")
    pairs = await extract_pairs_from_text(text)
    logging.info("Pairs extracted: %s", pairs)
    if not pairs:
        raise HTTPException(status_code=400, detail="No pairs extracted.")
    return {"pairs": pairs}


# Add selected cards to Anki
@app.post("/add_cards")
async def add_cards(input_data: AddCardsInput):
    deckName = input_data.deckName
    pairs = input_data.pairs
    if not deckName:
        deckName = "test"
    if not pairs:
        raise HTTPException(status_code=400, detail="No pairs provided.")
    pairs_status = []
    for pair in pairs:
        front = pair.get("Front")
        back = pair.get("Back")
        if front and back:
            status = add_card_to_anki(deckName, front, back)
            pairs_status.append({"Status": status, "Front": front, "Back": back})
    return {"status": pairs_status}


# Extract pairs from images
@app.post("/extract_images")
async def extract_images(files: List[UploadFile] = File(...)):
    images_folder = "uploaded_images"
    os.makedirs(images_folder, exist_ok=True)

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    all_pairs = []
    logging.info("Count of files: %s", len(files))
    for file in files:
        # Validate and save the uploaded image
        if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
            raise HTTPException(status_code=400, detail=f"Invalid image type: {file.filename}")
        file_path = os.path.join(images_folder, file.filename)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save image {file.filename}: {e}")

        # Convert the image to base64
        base64_image = image_to_base64(file_path)

        # Extract pairs from the image
        pairs = await extract_pairs_from_image(base64_image, image_caption=file.filename)
        logging.info("Pairs extracted: %s", pairs)
        if pairs:
            all_pairs.extend(pairs)

    if not all_pairs:
        raise HTTPException(status_code=400, detail="No pairs extracted from images.")

    return {"pairs": all_pairs}


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)