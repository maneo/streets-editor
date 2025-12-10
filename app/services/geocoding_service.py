"""Geocoding service using Nominatim (OpenStreetMap) API."""

import time

import requests
from flask import current_app


class GeocodingService:
    """Service for geocoding street addresses using Nominatim API."""

    BASE_URL = "https://nominatim.openstreetmap.org/search"
    RATE_LIMIT_DELAY = 1.0  # 1 second between requests (Nominatim requirement)
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # Prefix mapping for Polish street types
    PREFIX_MAP = {
        "ul.": "ulica",
        "pl.": "plac",
        "al.": "aleja",
        "skwer": "skwer",
        "wiadukt": "wiadukt",
        "zaułek": "zaułek",
        "os.": "osiedle",
        "park": "park",
        "rondo": "rondo",
        "tunel": "tunel",
        "most": "most",
        "rynek": "rynek",
        "droga": "droga",
        "-": None,  # No prefix
    }

    def __init__(self):
        """Initialize the geocoding service."""
        self.last_request_time = 0.0

    def _enforce_rate_limit(self):
        """Enforce rate limiting by waiting if necessary."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.RATE_LIMIT_DELAY:
            sleep_time = self.RATE_LIMIT_DELAY - time_since_last_request
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _build_query(self, street_name: str, city: str, prefix: str | None = None) -> str:
        """Build a geocoding query string from street name, city, and prefix."""
        # Nominatim works better with just the street name and city
        # Prefix normalization (ul. -> ulica) often causes no results
        # So we'll use the street name directly with city
        query = f"{street_name}, {city}, Poland"
        return query

    def geocode_street(
        self, street_name: str, city: str, prefix: str | None = None
    ) -> dict[str, float] | None:
        """
        Geocode a street address using Nominatim API.

        Args:
            street_name: The street name (case-sensitive version)
            city: The city name
            prefix: Optional street prefix (e.g., "ul.", "pl.", "al.")

        Returns:
            Dictionary with "latitude" and "longitude" keys, or None if not found
        """
        # Enforce rate limiting
        self._enforce_rate_limit()

        # Build query
        query = self._build_query(street_name, city, prefix)

        try:
            # Make request to Nominatim API
            params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            }

            headers = {
                "User-Agent": self.USER_AGENT,
            }

            response = requests.get(self.BASE_URL, params=params, headers=headers, timeout=15)

            # Handle rate limiting (HTTP 429) and service unavailable (HTTP 503)
            if response.status_code in [429, 503]:
                wait_time = self.RATE_LIMIT_DELAY * 3  # Wait longer for 503
                if hasattr(current_app, "logger"):
                    current_app.logger.warning(
                        f"Rate limited/service unavailable (HTTP {response.status_code}). Waiting {wait_time} seconds..."
                    )
                time.sleep(wait_time)
                # Retry once
                response = requests.get(self.BASE_URL, params=params, headers=headers, timeout=15)

            response.raise_for_status()

            data = response.json()

            if not data or len(data) == 0:
                current_app.logger.debug(f"No geocoding results for query: {query}")
                return None

            # Extract lat/lon from first result
            result = data[0]
            latitude = float(result.get("lat"))
            longitude = float(result.get("lon"))

            if latitude is None or longitude is None:
                current_app.logger.warning(f"Invalid geocoding result for query: {query}")
                return None

            return {"latitude": latitude, "longitude": longitude}

        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Geocoding API error for query '{query}': {str(e)}")
            return None
        except (ValueError, KeyError) as e:
            current_app.logger.error(
                f"Error parsing geocoding response for query '{query}': {str(e)}"
            )
            return None
        except Exception as e:
            current_app.logger.error(
                f"Unexpected error during geocoding for query '{query}': {str(e)}"
            )
            return None
