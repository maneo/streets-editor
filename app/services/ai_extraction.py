"""AI-powered street extraction using OpenRouter and Gemini."""

import base64
import json
import time

import requests
from flask import current_app


def encode_image_to_base64(filepath):
    """Encode image file to base64 string."""
    with open(filepath, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def extract_streets_from_image(filepath, city, decade):
    """
    Extract street names from historical city map using Gemini via OpenRouter.
    Note: Set models via EXTRACTION_MODEL environment variable.
    Recommended models: google/gemini-pro, openai/gpt-4o-mini, openai/gpt-4o

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
    model = current_app.config["EXTRACTION_MODEL"]

    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    current_app.logger.info(f"Using AI model: {model} for city: {city}, decade: {decade}")

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

    # Make API request to OpenRouter with retry logic
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

    # Retry logic for rate limiting
    max_retries = 3
    base_delay = 2  # seconds

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(base_url, headers=headers, json=payload, timeout=300)

            # Handle rate limiting specifically
            if response.status_code == 429:
                if attempt == max_retries:
                    raise Exception(
                        "Rate limit exceeded. Please try again later or consider upgrading to a paid plan."
                    ) from None

                # Exponential backoff: 2, 4, 8 seconds
                delay = base_delay * (2**attempt)
                current_app.logger.warning(
                    f"Rate limit hit (429). Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries + 1})"
                )
                time.sleep(delay)
                continue

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
            # Check for 400 Bad Request errors - don't retry these
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 400:
                current_app.logger.error(f"Bad request details - Model: {model}, URL: {base_url}")
                current_app.logger.error(
                    f"Response content: {e.response.text if hasattr(e.response, 'text') else 'No response text'}"
                )
                raise Exception(
                    f"Bad request to AI API. Model '{model}' may be invalid or request format incorrect. Check OpenRouter API docs for available models."
                ) from e

            # Check for rate limiting (429) - retry with backoff
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 429:
                if attempt == max_retries:
                    raise Exception(
                        "Rate limit exceeded. Please try again later or consider upgrading to a paid plan."
                    ) from None
                delay = base_delay * (2**attempt)
                current_app.logger.warning(
                    f"Rate limit hit (429). Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries + 1})"
                )
                time.sleep(delay)
                continue

            # Check for 404 Not Found errors - don't retry these
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 404:
                current_app.logger.error(f"Not found error - Model: {model}, URL: {base_url}")
                current_app.logger.error(
                    f"Response content: {e.response.text if hasattr(e.response, 'text') else 'No response text'}"
                )
                raise Exception(
                    f"Model '{model}' not found on OpenRouter. Check if the model name is correct and available."
                ) from e

            if attempt == max_retries:
                raise Exception(
                    f"API request failed after {max_retries + 1} attempts: {str(e)}"
                ) from e
            # For other request errors (network issues, 5xx errors), retry with backoff
            delay = base_delay * (2**attempt)
            current_app.logger.warning(
                f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. Retrying in {delay} seconds..."
            )
            time.sleep(delay)
            continue
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse AI response as JSON: {str(e)}") from e
        except Exception as e:
            raise Exception(f"Extraction failed: {str(e)}") from e
