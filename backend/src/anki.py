# src/anki.py

import httpx
import logging
from typing import List, Dict, Any
from tenacity import retry, wait_fixed, stop_after_attempt, RetryError, retry_if_exception_type
from httpx import ConnectError

logger = logging.getLogger(__name__)


class AnkiService:
    def __init__(self, base_url: str):
        self.client = httpx.AsyncClient(base_url=base_url)

    async def is_anki_running(self) -> bool:
        try:
            response = await self.client.post(
                "/", json={"action": "version", "version": 6}, timeout=5.0
            )
            return response.status_code == 200
        except httpx.RequestError:
            logger.error("Launch Anki!!!")
            return False

    @retry(
        wait=wait_fixed(2),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(ConnectError),
        reraise=True,
    )
    async def add_card(self, deck_name: str, front: str, back: str) -> Dict[str, Any]:
        if not await self.is_anki_running():
            return {
                "success": False,
                "error": "Anki is not running. Please launch Anki and ensure AnkiConnect is enabled.",
            }
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
                            "deckName": deck_name,
                            "checkChildren": True,
                            "checkAllModels": True,
                        },
                    },
                    "tags": [],
                }
            },
        }
        try:
            response = await self.client.post("/", json=payload, timeout=5.0)
            response.raise_for_status()
            response_json = response.json()
            if response_json.get("error"):
                logger.error(f"Error adding card: {response_json['error']}")
                return {"success": False, "error": response_json["error"]}
            logger.info(f"Added card: {front} - {back}")
            return {"success": True}
        except ConnectError as e:
            logger.error(f"AnkiConnect connection failed: {e}")
            return {"success": False, "error": "Connection to AnkiConnect failed."}
        except httpx.RequestError as e:
            logger.error(f"AnkiConnect request failed: {e}")
            return {"success": False, "error": "Request to AnkiConnect failed."}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"success": False, "error": f"Unexpected error: {e}"}


    @retry(
        wait=wait_fixed(2),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(ConnectError),
        reraise=True,
    )
    async def get_decks(self) -> Dict[str, Any]:
        if not await self.is_anki_running():
            return {
                "success": False,
                "error": "Anki is not running. Please launch Anki and ensure AnkiConnect is enabled.",
            }
        payload = {"action": "deckNames", "version": 6}
        try:
            response = await self.client.post("/", json=payload, timeout=5.0)
            response.raise_for_status()
            response_json = response.json()
            if response_json.get("error"):
                logger.error(f"Error fetching decks: {response_json['error']}")
                return {"success": False, "error": response_json["error"]}
            return {"success": True, "decks": response_json.get("result", [])}
        except ConnectError as e:
            logger.error(f"AnkiConnect connection failed: {e}")
            return {"success": False, "error": "Connection to AnkiConnect failed."}
        except httpx.RequestError as e:
            logger.error(f"AnkiConnect request failed: {e}")
            return {"success": False, "error": "Request to AnkiConnect failed."}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"success": False, "error": f"Unexpected error: {e}"}
    
    @retry(
        wait=wait_fixed(2),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(ConnectError),
        reraise=True,
    )
    async def get_cards_red(self, deck_name: str) -> List[Dict[str, Any]]:
        if not await self.is_anki_running():
            return []
        
        red_cards_ids = await self.get_cards_ids_red(deck_name)
        # print(red_cards_ids)
        red_cards_info = await self.get_cards_by_ids(red_cards_ids)
        # print(red_cards_info)
        
        red_cards_info_main = []
        try:
            for card in red_cards_info:
                if card.get("fields", {}).get("Лицо") and card.get("fields", {}).get("Оборот"):
                    card_info_main = {'Front': card.get("fields").get("Лицо").get("value"), 'Back': card.get("fields").get("Оборот").get("value")}
                    red_cards_info_main.append(card_info_main)
            # print(red_cards_info_main)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        return red_cards_info_main
        
    @retry(
        wait=wait_fixed(2),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(ConnectError),
        reraise=True,
    )
    async def get_cards_by_ids(self, card_ids: List[int]) -> List[Dict[str, Any]]:
        if not await self.is_anki_running():
            return []
        payload = {
            "action": "cardsInfo",
            "version": 6,
            "params": {"cards": card_ids},
        }
        try:
            response = await self.client.post("/", json=payload, timeout=5.0)
            response.raise_for_status()
            response_json = response.json()
            if response_json.get("error"):
                logger.error(f"Error fetching cards: {response_json['error']}")
                return []
            return response_json.get("result", [])
        except ConnectError as e:
            logger.error(f"AnkiConnect connection failed: {e}")
            return []
        except httpx.RequestError as e:
            logger.error(f"AnkiConnect request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []
        
    async def get_cards_ids_red(self, deck_name: str) -> List[int]:
        if not await self.is_anki_running():
            return []
        payload = {
            "action": "findCards",
            "version": 6,
            "params": {"query": f"deck:{deck_name} flag:1"},
        }
        try:
            response = await self.client.post("/", json=payload, timeout=5.0)
            response.raise_for_status()
            response_json = response.json()
            if response_json.get("error"):
                logger.error(f"Error fetching cards: {response_json['error']}")
                return []
            return response_json.get("result", [])
        except ConnectError as e:
            logger.error(f"AnkiConnect connection failed: {e}")
            return []
        except httpx.RequestError as e:
            logger.error(f"AnkiConnect request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []

