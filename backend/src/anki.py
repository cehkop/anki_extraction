import os
import httpx
import logging

logger = logging.getLogger(__name__)

ANKI_CONNECT_URL = os.getenv("ANKI_CONNECT_URL", "http://localhost:8765")

# Dependency injection for Anki client
async def get_anki_client():
    async with httpx.AsyncClient() as client:
        yield client


# Function to add a card to Anki
async def add_card_to_anki(
    client: httpx.AsyncClient, deckName: str, front: str, back: str
) -> bool:
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
        response = await client.post(ANKI_CONNECT_URL, json=payload, timeout=5.0)
        response_json = response.json()
    except httpx.RequestError as e:
        logger.error(f"AnkiConnect request failed: {e}")
        return False

    if response_json.get("error"):
        logger.error(f"Error adding card: {response_json['error']}")
        return False
    else:
        logger.info(f"Added card: {front} - {back}")
        return True
    
    
# Function to get decks from Anki
async def get_decks_from_anki(client: httpx.AsyncClient):
    payload = {"action": "deckNames", "version": 6}
    try:
        response = await client.post(ANKI_CONNECT_URL, json=payload, timeout=5.0)
        response_json = response.json()
        if response_json.get("error"):
            logger.error(f"Error fetching decks: {response_json['error']}")
            return None
        return response_json.get("result", [])
    except httpx.RequestError as e:
        logger.error(f"Error fetching decks: {e}")
        return None
