# src/anki.py

import httpx
import logging
from typing import List, Dict, Any
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

    async def add_card(self, deck_name: str, front: str, back: str) -> Dict[str, Any]:
        """Adds a new note in Anki."""
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
                    "modelName": "Basic",
                    "fields": {"Front": front, "Back": back},
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
        logger.info(payload)
        try:
            response = await self.client.post("/", json=payload, timeout=5.0)
            response.raise_for_status()
            response_json = response.json()
            if response_json.get("error"):
                logger.error(f"Error adding card: {response_json['error']}")
                return {"success": False, "error": response_json["error"]}
            logger.info(f"Added card: {front} - {back}")
            return {"success": True, "noteId": response_json["result"]}
        except Exception as e:
            logger.error(f"Add card error: {e}")
            return {"success": False, "error": str(e)}

    async def update_card(self, note_id: int, front: str, back: str) -> Dict[str, Any]:
        """
        Updates an existing note's fields. 
        This rewrites the old card content in place.
        """
        if not await self.is_anki_running():
            return {
                "success": False,
                "error": "Anki is not running. Please launch Anki and ensure AnkiConnect is enabled.",
            }
        payload = {
            "action": "updateNoteFields",
            "version": 6,
            "params": {
                "note": {
                    "id": note_id,
                    "fields": {
                        "Front": front,
                        "Back": back
                    }
                }
            }
        }
        try:
            response = await self.client.post("/", json=payload, timeout=5.0)
            response.raise_for_status()
            response_json = response.json()
            if response_json.get("error"):
                logger.error(f"Error updating card: {response_json['error']}")
                return {"success": False, "error": response_json["error"]}
            logger.info(f"Updated card noteId={note_id}: {front} - {back}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Update card error: {e}")
            return {"success": False, "error": str(e)}
        
    async def get_cards_red(self, deck_name: str) -> List[int]:
        """
        Returns card IDs that have a red flag in the given deck.
        """
        if not await self.is_anki_running():
            print("Anki is not running")
            return []
        payload = {
            "action": "findNotes",
            "version": 6,
            "params": {"query": f"deck:{deck_name} flag:1"},
        }
        try:
            response = await self.client.post("/", json=payload, timeout=5.0)
            response.raise_for_status()
            response_json = response.json()
            if response_json.get("error"):
                logger.error(f"Error fetching red card IDs: {response_json['error']}")
                return []
            print(f"Got {len(response_json)} red cards")
            return response_json.get("result", [])
        except Exception as e:
            logger.error(f"get_cards_red error: {e}")
            return []

    async def cards_info(self, card_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Utility to retrieve detailed card info for a list of card IDs.
        """
        if not await self.is_anki_running() or not card_ids:
            return []
        payload = {
            "action": "notesInfo",
            "version": 6,
            "params": {"notes": card_ids},
        }
        try:
            resp = await self.client.post("/", json=payload, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                logger.error(f"Error in cardsInfo: {data['error']}")
                return []
            return data.get("result", [])
        except Exception as e:
            logger.error(f"cards_info error: {e}")
            return []
        
    # In src/anki.py

    async def delete_note(self, note_id: int) -> Dict[str, Any]:
        """
        Deletes a single note by its note ID.
        Returns {"success": True} or {"success": False, "error": "..."} 
        """
        if not await self.is_anki_running():
            return {
                "success": False,
                "error": "Anki is not running. Please launch Anki and ensure AnkiConnect is enabled.",
            }
        payload = {
            "action": "deleteNotes",
            "version": 6,
            "params": {
                "notes": [note_id]
            }
        }
        try:
            resp = await self.client.post("/", json=payload, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                return {"success": False, "error": data["error"]}
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

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
        except Exception as e:
            logger.error(f"get_decks error: {e}")
            return {"success": False, "error": str(e)}
        
    async def set_note_cards_flag_yellow(self, note_id: int) -> Dict[str, Any]:
        """
        From the note info, gather all card IDs for this note
        and set their flags to 2 (yellow/orange).
        
        Returns a dict like:
        {
        "success": bool,
        "details": [ 
            { "cardId": 1234, "changed": True/False, "error": "..." }, 
            ...
        ]
        }
        """
        if not await self.is_anki_running():
            return {
                "success": False,
                "error": "Anki is not running. Please launch Anki and ensure AnkiConnect is enabled.",
            }

        # 1) Get the cards for this note using 'notesInfo'
        payload_notes_info = {
            "action": "notesInfo",
            "version": 6,
            "params": {
                "notes": [note_id]
            }
        }
        try:
            resp = await self.client.post("/", json=payload_notes_info, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                return {
                    "success": False,
                    "error": f"Failed to fetch note info: {data['error']}",
                    "details": []
                }
            notes_result = data.get("result", [])
            if not notes_result:
                return {
                    "success": False,
                    "error": f"No note found with note_id={note_id}",
                    "details": []
                }
            # notes_result[0] should be the note data
            cards_list = notes_result[0].get("cards", [])
        except Exception as e:
            return {
                "success": False,
                "error": f"Error calling notesInfo: {e}",
                "details": []
            }

        # 2) For each card, set flags=2 with 'setSpecificValueOfCard'
        results = []
        for card_id in cards_list:
            payload_flag = {
                "action": "setSpecificValueOfCard",
                "version": 6,
                "params": {
                    "card": card_id,
                    "keys": ["flags"],       # We only want to change "flags"
                    "newValues": [2],      # 2 => "orange/yellow"
                    "warning_check": True    # Required for changing these DB values
                }
            }
            try:
                resp_flag = await self.client.post("/", json=payload_flag, timeout=5.0)
                resp_flag.raise_for_status()
                data_flag = resp_flag.json()
                if data_flag.get("error"):
                    results.append({
                        "cardId": card_id,
                        "changed": False,
                        "error": data_flag["error"]
                    })
                else:
                    # data_flag["result"] is typically [true or false] for each item
                    # but we can assume success = all true if no error
                    results.append({
                        "cardId": card_id,
                        "changed": True,
                        "error": None
                    })
            except Exception as e:
                results.append({
                    "cardId": card_id,
                    "changed": False,
                    "error": str(e)
                })

        # If any card changed successfully, success=True
        any_changed = any(r["changed"] for r in results)
        return {
            "success": any_changed,
            "details": results
        }
