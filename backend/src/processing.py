import httpx
import json
from openai import AsyncOpenAI
import openai
import os
from typing import List, Dict
from src.prompts import get_extract_text_prompt, get_extract_image_prompt, get_change_pairs_prompt


proxy_url = os.getenv("OPENAI_PROXY")
if proxy_url is not None and proxy_url != "":
    http_client = httpx.AsyncClient(proxy=proxy_url)
else:
    http_client = httpx.AsyncClient()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key is not set in environment variables.")

client = AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)



# Asynchronous function to process text with OpenAI API
async def extract_pairs_from_text(text: str):
    # return [{"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
            # {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."}]
    prompt = get_extract_text_prompt()
    try:
        resp = await client.responses.create(
            model="gpt-4o-mini-2024-07-18",
            instructions=prompt,
            input=json.dumps(text),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "Anki_cards",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "Cards": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "Front": {"type": "string",
                                                    "description": "One sentence with EXACTLY ONE {{c1::...}} around the target, then newline + [short English definition]"},
                                            "Back":  {"type": "string",
                                                    "description": "1–3 short synonyms/near-phrases, comma-separated"}
                                        },
                                        "required": ["Front", "Back"],
                                        "additionalProperties": False
                                    },
                                },
                            },
                        },
                        "required": ["Cards"],
                        "additionalProperties": False,
                    },
                },
            },
            timeout=30,
            max_output_tokens=1024,
        )

        output_str = None
        try:
            output_str = resp.output_text
        except Exception:
            output_str = None

        if not output_str:
            chunks = []
            for item in getattr(resp, "output", []) or []:
                if getattr(item, "type", None) == "message":
                    for c in getattr(item, "content", []) or []:
                        if getattr(c, "type", None) == "output_text" and isinstance(getattr(c, "text", None), str):
                            chunks.append(c.text)
            output_str = "".join(chunks).strip()

        if output_str:
            data = json.loads(output_str)
            pairs_out = data.get("Cards", [])
            return pairs_out
        else:
            raise ValueError("No response.")

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return []
    
    
# Asynchronous function to process image with OpenAI API
async def extract_pairs_from_image(base64_image, image_caption=""):    
    # return [{"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for", "Back": "An aptitude for doing something."}]
    """Send an image and caption to OpenAI for structured processing and return extracted information."""
    try:
        user_content = []
        if image_caption:
            user_content.append({
                "type": "input_text",
                "text": "Image caption: " + image_caption,
            })
        user_content.append({
            "type": "input_image",
            "image_url": f"data:image/jpeg;base64,{base64_image}",
        })

        resp = await client.responses.create(
            model="gpt-4o-mini-2024-07-18",
            instructions=get_extract_image_prompt(),
            input=[{"role": "user", "content": user_content}],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "image_cards_extraction",
                    "strict": True,
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
                                            "description": "One sentence with EXACTLY ONE {{c1::...}} around the target, then newline + [short English definition]",
                                        },
                                        "Back": {
                                            "type": "string",
                                            "description": "1–3 short synonyms/near-phrases, comma-separated",
                                        },
                                    },
                                    "required": ["Front", "Back"],
                                    "additionalProperties": False,
                                },
                            },
                        },
                        "required": ["Cards"],
                        "additionalProperties": False,
                    },
                }
            },
            max_output_tokens=1024,
        )

        output_str = None
        try:
            output_str = resp.output_text
        except Exception:
            output_str = None

        if not output_str:
            chunks = []
            for item in getattr(resp, "output", []) or []:
                if getattr(item, "type", None) == "message":
                    for c in getattr(item, "content", []) or []:
                        if getattr(c, "type", None) == "output_text" and isinstance(getattr(c, "text", None), str):
                            chunks.append(c.text)
            output_str = "".join(chunks).strip()

        if output_str:
            data = json.loads(output_str)
            pairs = data.get("Cards", [])
            return pairs
        else:
            raise ValueError("No response.")

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return []


async def change_anki_pairs(pairs: List[Dict[str, str]]) -> List[List[Dict[str, str]]]:
    """
    Takes a list of input cards, each {Front,Back}, returns a 2D array, e.g.:
      [ 
         [ {Front,Back}, {Front,Back}, ... ],  # for pairs[0]
         [ {Front,Back}, ... ],                # for pairs[1]
         ...
      ]
    The outer list must match the length of `pairs`, with each sub-list having >= 1 items.
    """

    # 0) Debug short-circuit:
    # debug_result = []
    # for _ in pairs:
    #     debug_result.append([
    #         {"Front": "knack for", "Back": "An aptitude for doing something."},
    #         {"Front": "knack for v2", "Back": "Another example."}
    #     ])
    # Uncomment to skip the LLM and return debug data
    # return debug_result

    # 1) get the prompt
    prompt = get_change_pairs_prompt()

    # 2) Create the JSON schema for the structured outputs
    schema = {
        "name": "changing_anki_cards",
       
    }

    # 3) Call the model via Python SDK Responses API
    try:
        resp = await client.responses.create(
            model="gpt-4o-mini-2024-07-18",
            instructions=prompt,
            input=json.dumps(pairs),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "Anki_cards",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "Cards": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "Front": {"type": "string",
                                                    "description": "One sentence with EXACTLY ONE {{c1::...}} around the target, then newline + [short English definition]"},
                                            "Back":  {"type": "string",
                                                    "description": "1–3 short synonyms/near-phrases, comma-separated"}
                                        },
                                        "required": ["Front", "Back"],
                                        "additionalProperties": False
                                    },
                                },
                            },
                        },
                        "required": ["Cards"],
                        "additionalProperties": False,
                    },
                },
            },
            timeout=30,
            max_output_tokens=1024,
        )

        # 4) Extract output text
        output_str = None
        try:
            output_str = resp.output_text
        except Exception:
            output_str = None

        if not output_str:
            print(resp)
            # Fallback: concatenate output_text items
            text_chunks = []
            try:
                for item in getattr(resp, "output", []) or []:
                    if getattr(item, "type", None) == "message":
                        for c in getattr(item, "content", []) or []:
                            if getattr(c, "type", None) == "output_text" and isinstance(getattr(c, "text", None), str):
                                text_chunks.append(c.text)
            except Exception:
                pass
            output_str = "".join(text_chunks).strip()

        if not output_str:
            raise ValueError("No content returned by the model")
        print(output_str)
        data = json.loads(output_str)
        # Expecting object with "Cards": [ [ {Front,Back}, ... ], ... ]
        cards = data.get("Cards", [])
        if len(cards) != len(pairs):
            print(f"WARNING: The model returned {len(cards)} items, expected {len(pairs)}")

        return cards

    except Exception as e:
        print(f"Error in change_anki_pairs: {e}")
        # Return an empty 2D array shape-compatible with input
        return [[] for _ in pairs]
