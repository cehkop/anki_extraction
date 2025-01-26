import httpx
import json
from openai import AsyncOpenAI
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
    prompt = get_extract_text_prompt()
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "extract_cards",
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
                },
            },
            timeout=10,
            max_tokens=1024 * 2,
        )
        
        output = response.choices[0].message.content
        if output:
            data = json.loads(output)
            pairs = data.get("Cards", [])
            return pairs
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
        user_content = [
            {
                "type": "text",
                "text": get_extract_image_prompt(),
            },
            {"type": "text", "text": "Image caption: " + image_caption},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": "high",
                },
            },
        ]

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_content}],
            response_format={
                "type": "json_schema",
                "json_schema": {
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
                                            "description": "Extracted text.",
                                        },
                                        "Back": {
                                            "type": "string",
                                            "description": "Definition or translation.",
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
                },
            },
            max_tokens=1024,
        )

        output = response.choices[0].message.content
        if output:
            data = json.loads(output)
            pairs = data.get("Cards", [])
            return pairs
        else:
            raise ValueError("No response.")

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return []


# Asynchronous function to process text with OpenAI API
async def change_anki_pairs(pairs: Dict):
    prompt = get_change_pairs_prompt()
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(pairs)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "extract_cards",
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
                },
            },
            timeout=10,
            max_tokens=1024 * 2,
        )
        
        output = response.choices[0].message.content
        if output:
            data = json.loads(output)
            pairs = data.get("Cards", [])
            return pairs
        else:
            raise ValueError("No response.")

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return []