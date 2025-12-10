"""File upload validation and handling."""

import os

from flask import current_app
from PIL import Image
from werkzeug.utils import secure_filename


def allowed_file(filename):
    """Check if file extension is allowed."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )


def allowed_csv_file(filename):
    """Check if CSV extension is allowed."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_CSV_EXTENSIONS"]
    )


def allowed_json_file(filename):
    """Check if JSON extension is allowed."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_JSON_EXTENSIONS"]
    )


def validate_file(file):
    """
    Validate uploaded file.
    Returns error message if invalid, None if valid.
    """
    if not file:
        return "No file provided."

    if file.filename == "":
        return "No file selected."

    if not allowed_file(file.filename):
        return "Invalid file type. Only JPG and PNG files are allowed."

    # Check file size (Flask MAX_CONTENT_LENGTH handles this, but double-check)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)  # Reset file pointer

    max_size = current_app.config["MAX_CONTENT_LENGTH"]
    if size > max_size:
        return f"File size exceeds maximum limit of {max_size / (1024 * 1024):.0f} MB."

    # Validate that it's actually an image
    try:
        img = Image.open(file)
        img.verify()
        file.seek(0)  # Reset after verification
    except Exception:
        return "Invalid image file."

    return None


def validate_csv_file(file):
    """
    Validate uploaded CSV file.
    Returns error message if invalid, None if valid.
    """
    if not file:
        return "No file provided."

    if file.filename == "":
        return "No file selected."

    if not allowed_csv_file(file.filename):
        return "Invalid file type. Only CSV files are allowed."

    # Check file size (reuse MAX_CONTENT_LENGTH)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)

    max_size = current_app.config["MAX_CONTENT_LENGTH"]
    if size > max_size:
        return f"File size exceeds maximum limit of {max_size / (1024 * 1024):.0f} MB."

    return None


def validate_json_file(file):
    """
    Validate uploaded JSON file.
    Returns error message if invalid, None if valid.
    """
    if not file:
        return "No file provided."

    if file.filename == "":
        return "No file selected."

    if not allowed_json_file(file.filename):
        return "Invalid file type. Only JSON files are allowed."

    # Check file size (reuse MAX_CONTENT_LENGTH)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)

    max_size = current_app.config["MAX_CONTENT_LENGTH"]
    if size > max_size:
        return f"File size exceeds maximum limit of {max_size / (1024 * 1024):.0f} MB."

    # Basic JSON validation
    try:
        import json

        content = file.read()
        json.loads(content)
        file.seek(0)  # Reset after validation
    except json.JSONDecodeError as e:
        return f"Invalid JSON format: {str(e)}"
    except Exception as e:
        return f"Error reading JSON file: {str(e)}"

    return None


def save_upload(file, user_id):
    """
    Save uploaded file temporarily.
    Returns filepath.
    """
    filename = secure_filename(file.filename)
    # Add user_id to avoid conflicts
    unique_filename = f"{user_id}_{filename}"

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, unique_filename)
    file.save(filepath)

    return filepath
