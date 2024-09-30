from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
import os
import dotenv
import requests
import shutil
from typing import List

from src.utils import image_to_base64
from src.processing import extract_pairs_from_text, extract_pairs_from_image

app = FastAPI()


# Set your OpenAI API key (ensure it's securely stored in environment variables)
dotenv.load_dotenv()

# Define the Anki-Connect endpoint
ANKI_CONNECT_URL = "http://localhost:8765"

# Pydantic model for input
class TextInput(BaseModel):
    text: str


# Function to add a card to Anki
def add_card_to_anki(deck_name: str, front: str, back: str):
    payload = {
        "action": "addNote",
        "version": 6,
        "params": {
            "note": {
                "deckName": deck_name,
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
async def process_text(input_data: TextInput):
    text = input_data.text

    # Step 1: Process text with OpenAI API
    pairs = await extract_pairs_from_text(text)

    if not pairs:
        raise HTTPException(status_code=400, detail="No pairs extracted.")

    # Step 2: Add pairs to Anki
    deck_name = "test"
    pairs_status = []
    for pair in pairs:
        front = pair.get("Front")
        back = pair.get("Back")
        if front and back:
            status = add_card_to_anki(deck_name, front, back)
            pairs_status.append({"Status": status, "Front": front, "Back": back})
    return {"status": pairs_status}


# Function to process all images in a folder
@app.post("/upload_images")
async def upload_images(files: List[UploadFile] = File(...)):
    images_folder = "uploaded_images"
    os.makedirs(images_folder, exist_ok=True)

    results = []

    for file in files:
        # Validate the uploaded file
        if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
            raise HTTPException(status_code=400, detail=f"Invalid image type: {file.filename}")

        # Limit file size (e.g., 5MB)
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

        if not pairs:
            results.append({
                "Image": file.filename,
                "Status": False,
                "Detail": "No pairs extracted from the image."
            })
            continue

        # Add pairs to Anki
        deck_name = "test"  # Replace with your actual deck name
        pairs_status = []
        for pair in pairs:
            front = pair.get("Front")
            back = pair.get("Back")
            if front and back:
                status = add_card_to_anki(deck_name, front, back)
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

    if not pairs:
        raise HTTPException(status_code=400, detail="No pairs extracted from the image.")

    # Add pairs to Anki
    deck_name = "test"  # Replace with your actual deck name
    pairs_status = []
    for pair in pairs:
        front = pair.get("Front")
        back = pair.get("Back")
        if front and back:
            status = add_card_to_anki(deck_name, front, back)
            pairs_status.append({"Status": status, "Front": front, "Back": back})

    return {"status": pairs_status}