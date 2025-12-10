"""Simple test script to check Nominatim API directly."""

import time

import requests

# Test with a simple query first
print("Testing Nominatim API with simple query...")
print("=" * 70)

# Test 1: Simple query without prefix normalization
test_queries = [
    "Głogowska, Poznań, Poland",
    "ulica Głogowska, Poznań, Poland",
    "ul. Głogowska, Poznań, Poland",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

for query in test_queries:
    print(f"\nTesting query: {query}")

    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search", params=params, headers=headers, timeout=15
        )

        print(f"  Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                result = data[0]
                print("  ✅ SUCCESS")
                print(f"  Display Name: {result.get('display_name', 'N/A')}")
                print(f"  Latitude: {result.get('lat', 'N/A')}")
                print(f"  Longitude: {result.get('lon', 'N/A')}")
            else:
                print("  ❌ No results found")
        else:
            print(f"  ❌ Error: {response.status_code}")
            print(f"  Response: {response.text[:200]}")

    except Exception as e:
        print(f"  ❌ Exception: {str(e)}")

    time.sleep(2)  # Be more generous with rate limiting

print("\n" + "=" * 70)
print("Test complete!")
