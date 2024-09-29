# app/main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from openai import AsyncOpenAI
import json
import dotenv
import httpx
import requests


app = FastAPI()
    
    
# Set your OpenAI API key (ensure it's securely stored in environment variables)
dotenv.load_dotenv()


proxy_url = os.getenv("OPENAI_PROXY")
if proxy_url is not None:
    http_client = httpx.AsyncClient(proxy=proxy_url)
else:
    http_client = httpx.AsyncClient()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), http_client=http_client)


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
                "fields": {
                    "Лицо": front,
                    "Оборот": back
                },
                "options": {
                    "allowDuplicate": False
                },
                "tags": []
            }
        }
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


# Asynchronous function to process text with OpenAI API
async def process_with_openai(text: str):
    # return [{"Front": "knack for", "Back": "An aptitude for doing something."}]
    prompt = (
        "You are an assistant that extracts useful collocations, phrases, or sentences from the given text. "
        "For each item, provide a pair consisting of the original text and either a definition in English or a translation if it's complex. "
        "Only include items that are useful for language learning. Here are some examples:\n\n"
        "Example 1:\n"
        "Text: 'She has a knack for languages.'\n"
        "Pairs: [{'front': 'knack for', 'back': 'An aptitude for doing something.'}]\n\n"
        "Example 2:\n"
        "Text: 'The enigmatic smile of the Mona Lisa has intrigued people for centuries.'\n"
        "Pairs: [\n"
        "  {'front': 'enigmatic smile', 'back': 'A mysterious or puzzling smile.'},\n"
        "  {'front': 'has intrigued people', 'back': 'Has fascinated or interested people deeply.'}\n"
        "]\n\n"
        "Now, extract pairs from the following text:\n"
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt},
                      {"role": "user", "content": text}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "extract_pairs",
                    "strict": True,
                    "description": "Extract useful collocations and their definitions or translations.",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "Cards": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "Front": {
                                            "type": "string",
                                            "description": "Original text.",
                                        },
                                        "Back": {
                                            "type": "string",
                                            "description": "Definition or translation.",
                                        },
                                    },
                                    "required": [
                                        "Front",
                                        "Back",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                        },
                        "required": ["Cards"],
                        "additionalProperties": False,
                    },
                }
            },
            timeout=10,
            max_tokens=1024*2
        )

        output = response.choices[0].message.content
        if output:
            data = json.loads(output)
            pairs = data.get("Cards", [])
            return pairs
        else:
            raise ValueError("No function_call in response.")

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return []


# API endpoint
@app.post("/process_text")
async def process_text(input_data: TextInput):
    text = input_data.text

    # Step 1: Process text with OpenAI API
    pairs = await process_with_openai(text)

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
