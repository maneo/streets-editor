"""Test script for geocoding service with specific Poznań streets."""

import time

import requests

# Nominatim API configuration
BASE_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "Streets-Editor/1.0 (contact: streets-editor@example.com)"

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
    "-": None,
}


def build_query(street_name, city, prefix=None):
    """Build a geocoding query string."""
    # Nominatim works better with just the street name and city
    # Prefix normalization often causes no results
    query = f"{street_name}, {city}, Poland"
    return query


def geocode_street(street_name, city, prefix=None):
    """Geocode a street address using Nominatim API."""
    query = build_query(street_name, city, prefix)

    print(f"  Query: {query}")

    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }

    headers = {
        "User-Agent": USER_AGENT,
    }

    try:
        response = requests.get(BASE_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        if not data or len(data) == 0:
            return None

        result = data[0]
        latitude = float(result.get("lat"))
        longitude = float(result.get("lon"))

        if latitude is None or longitude is None:
            return None

        return {"latitude": latitude, "longitude": longitude}

    except Exception as e:
        print(f"  Error: {str(e)}")
        return None


# Streets to test
streets_to_test = [
    {"name": "Głogowska", "prefix": "ul.", "city": "Poznań"},
    {"name": "Głogowoska", "prefix": "ul.", "city": "Poznań"},  # Alternative spelling
    {"name": "Wierzbięcice", "prefix": "ul.", "city": "Poznań"},
    {"name": "Poznańska", "prefix": "ul.", "city": "Poznań"},
    {"name": "Dąbrowskiego", "prefix": "ul.", "city": "Poznań"},
]


def test_geocoding():
    """Test geocoding for the specified streets."""
    print("Testing geocoding service for Poznań streets...")
    print("=" * 70)
    print()

    for street in streets_to_test:
        display_name = f"{street['prefix']} {street['name']}"
        print(f"Testing: {display_name}, {street['city']}")

        result = geocode_street(street["name"], street["city"], street["prefix"])

        if result:
            print("  ✅ SUCCESS")
            print(f"  Latitude: {result['latitude']}")
            print(f"  Longitude: {result['longitude']}")
        else:
            print("  ❌ FAILED - No geolocation found")

        print()

        # Rate limiting: 1 second between requests
        time.sleep(1)

    print("=" * 70)
    print("Test complete!")


if __name__ == "__main__":
    test_geocoding()
