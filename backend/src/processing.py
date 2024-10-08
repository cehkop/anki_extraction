import httpx
import json
from openai import AsyncOpenAI
import os


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
    # return [{"Front": "knack for", "Back": "An aptitude for doing something."}]
    prompt = (
        "You are a perfect English teacher. Teacher are very helpful. Teacher helps me to learn English. "
        "I use Anki cards to learn English and I need teacher help. My main language is Russian. "
        "My current English level is about B1. Teacher goals is to help me to learn with anki. "
        "I want teacher to help me to learn English like natives, without russian dialects. "
        "For this goal teacher helps me to create anki cards with collocations, phrazes, sentences, etc - everything for effective learning. "
        "Teacher gets as an input text and extracts any cards pairs of words and their translations to help me improve my English and speak like natives. "
        "For each item, teacher provides a pair consisting of the original text and either a definition in English or a translation if it's complex. "
        "Teacher should make cards understandeble for intermediate level. Teacher can also make up sentences for better sensitivity. "
        "Teacher should only include items that are useful for language learning. Here are some examples:\n\n"
        "Example 1:\n"
        "Text: 'She has a knack for languages.'\n"
        "Cards: [{'Front': 'She has a knack for languages', 'Back': 'She is language inclined.'}]\n\n"
        "Example 2:\n"
        "Text: 'The enigmatic smile of the Mona Lisa has intrigued people for centuries.'\n"
        "Cards: [\n"
        "  {'Front': 'enigmatic smile of the Mona Lisa', 'Back': 'A mysterious or puzzling the Mona Lisa smile'},\n"
        "  {'Front': 'this smile has intrigued people', 'Back': 'This smile has interested people deeply.'}\n"
        "]\n\n"
        "Now, extract pairs from the following text:\n"
        ),
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
            raise ValueError("No function_call in response.")

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return []
    
    
# Asynchronous function to process image with OpenAI API
async def extract_pairs_from_image(base64_image, image_caption=""):
    """Send an image and caption to OpenAI for structured processing and return extracted information."""
    try:
        user_content = [
            {
                "type": "text",
                "text": (
                    "You are a perfect English teacher. Teacher are very helpful. Teacher helps me to learn English. "
                    "I use Anki cards to learn English and I need teacher help. My main language is Russian. "
                    "My current English level is about B1. Teacher goals is to help me to learn with anki. "
                    "I want teacher to help me to learn English like natives, without russian dialects. "
                    "For this goal teacher helps me to create anki cards with collocations, phrazes, sentences, etc - everything for effective learning. "
                    "Teacher gets as an input image with text on it and extracts any cards pairs of words and their translations to help me improve my English and speak like natives. "
                    "For each item, teacher provides a pair consisting of the original text and either a definition in English or a translation if it's complex. "
                    "Teacher should make cards understandeble for intermediate level. Teacher can also make up sentences for better sensitivity. "
                    "Teacher should only include items that are useful for language learning. Here are some examples:\n\n"
                    "Example 1:\n"
                    "Text: 'She has a knack for languages.'\n"
                    "Cards: [{'Front': 'She has a knack for languages', 'Back': 'She is language inclined.'}]\n\n"
                    "Example 2:\n"
                    "Text: 'The enigmatic smile of the Mona Lisa has intrigued people for centuries.'\n"
                    "Cards: [\n"
                    "  {'Front': 'enigmatic smile of the Mona Lisa', 'Back': 'A mysterious or puzzling the Mona Lisa smile'},\n"
                    "  {'Front': 'this smile has intrigued people', 'Back': 'This smile has interested people deeply.'}\n"
                    "]\n\n"
                    "Now, extract pairs from the following text:\n"),
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
                    "name": "image_extraction",
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
            raise ValueError("No function_call in response.")

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return []
