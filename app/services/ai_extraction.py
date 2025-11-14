"""AI-powered street extraction using OpenRouter and Gemini."""

import base64
import json

import requests
from flask import current_app


def encode_image_to_base64(filepath):
    """Encode image file to base64 string."""
    with open(filepath, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def extract_streets_from_image(filepath, city, decade):
    """
    Extract street names from historical city map using Gemini via OpenRouter.

    Args:
        filepath: Path to the uploaded image
        city: City name
        decade: Decade (e.g., "1940-1949")

    Returns:
        List of dictionaries with street data:
        [
            {
                "prefix": "ul.",
                "main_name": "Głogowska"
            },
            ...
        ]
    """
    api_key = current_app.config["OPENROUTER_API_KEY"]
    base_url = current_app.config["OPENROUTER_BASE_URL"]
    model = current_app.config["GEMINI_MODEL"]

    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    # Encode image
    base64_image = encode_image_to_base64(filepath)

    # Determine image mime type
    mime_type = "image/png" if filepath.lower().endswith(".png") else "image/jpeg"

    # Create prompt for street extraction
    prompt = f"""You are analyzing a historical city map of {city} from the decade {decade}.

Your task is to extract ALL street names visible on this map and return them in a structured JSON format.

Instructions:
1. Look for street names on the map (they may be written in various directions)
2. For each street, identify:
   - The street prefix (ul., pl., al., or - if no prefix)
   - The main street name (preserve the original case as it appears on the map)
3. Return ONLY a valid JSON array with this exact structure:
[
  {{"prefix": "ul.", "main_name": "Example Street Name"}},
  {{"prefix": "pl.", "main_name": "Another Street"}}
]

Important:
- Return ONLY the JSON array, no additional text or explanation
- If you cannot find any street names, return an empty array: []
- Preserve the original capitalization from the map
- Common Polish prefixes: ul. (ulica/street), pl. (plac/square), al. (aleja/avenue)
- If there's no prefix, use "-"
"""

    # Make API request to OpenRouter
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                    },
                ],
            }
        ],
    }

    try:
        response = requests.post(base_url, headers=headers, json=payload, timeout=300)
        response.raise_for_status()

        result = response.json()

        # Extract the response text
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]

            # Parse JSON from response
            # Sometimes the model might wrap JSON in markdown code blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            streets = json.loads(content)

            # Validate structure
            if not isinstance(streets, list):
                raise ValueError("Response is not a list.")

            return streets
        else:
            raise ValueError("No response from AI model.")

    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}") from e
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse AI response as JSON: {str(e)}") from e
    except Exception as e:
        raise Exception(f"Extraction failed: {str(e)}") from e
