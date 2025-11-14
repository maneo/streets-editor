"""Export services for generating TXT and JSON files."""

import json


def generate_txt_export(streets):
    """
    Generate TXT export with one street per line.

    Args:
        streets: List of Street model objects

    Returns:
        String with street names, one per line
    """
    lines = []
    for street in streets:
        # Use case-sensitive version
        lines.append(street.main_name_cs)

    return "\n".join(lines)


def generate_json_export(streets, city, decade):
    """
    Generate JSON export according to the specified format.

    Args:
        streets: List of Street model objects
        city: City name
        decade: Decade string

    Returns:
        JSON string with dictionary format
    """
    dictionary = {"city": city, "decade": decade, "streets": []}

    for street in streets:
        street_dict = street.to_dict()
        dictionary["streets"].append(street_dict)

    return json.dumps(dictionary, indent=2, ensure_ascii=False)
