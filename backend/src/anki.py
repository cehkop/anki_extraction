# src/anki.py

import os
import httpx
import logging
from typing import List
from tenacity import retry, wait_fixed, stop_after_attempt, RetryError
from fastapi import HTTPException

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
        except httpx.RequestError as e:
            logger.error(f"AnkiConnect request failed: {e}")
            return False

    @retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
    async def add_card(self, deck_name: str, front: str, back: str) -> bool:
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
            response = await self.client.post("/", json=payload, timeout=5.0)
            response_json = response.json()
            if response_json.get("error"):
                logger.error(f"Error adding card: {response_json['error']}")
                return False
            logger.info(f"Added card: {front} - {back}")
            return True
        except httpx.RequestError as e:
            logger.error(f"AnkiConnect request failed: {e}")
            raise

    @retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
    async def get_decks(self) -> List[str]:
        payload = {"action": "deckNames", "version": 6}
        try:
            response = await self.client.post("/", json=payload, timeout=5.0)
            response_json = response.json()
            if response_json.get("error"):
                logger.error(f"Error fetching decks: {response_json['error']}")
                return []
            return response_json.get("result", [])
        except httpx.RequestError as e:
            logger.error(f"AnkiConnect request failed: {e}")
            raise