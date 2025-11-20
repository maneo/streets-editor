"""Tests for AI extraction service."""

from unittest.mock import Mock, mock_open, patch

import pytest

from app import create_app
from app.services.ai_extraction import encode_image_to_base64, extract_streets_from_image

# Test constants
TEST_CITY = "Poznań"
TEST_DECADE = "1940-1949"


@pytest.fixture
def app():
    """Create and configure a test app."""
    app = create_app("testing")
    with app.app_context():
        yield app


class TestEncodeImageToBase64:
    """Test base64 encoding function."""

    @patch("builtins.open", new_callable=mock_open, read_data=b"fake image data")
    @patch("base64.b64encode")
    def test_encode_image_to_base64(self, mock_b64encode, mock_file):
        """Test successful base64 encoding."""
        mock_b64encode.return_value = b"encoded_data"
        result = encode_image_to_base64("test.png")
        assert result == "encoded_data"
        mock_file.assert_called_once_with("test.png", "rb")
        mock_b64encode.assert_called_once_with(b"fake image data")

    @patch("builtins.open")
    def test_encode_image_to_base64_file_error(self, mock_file):
        """Test encoding with file error."""
        mock_file.side_effect = OSError("File not found")

        with pytest.raises(OSError):
            encode_image_to_base64("nonexistent.png")


class TestExtractStreetsFromImage:
    """Test AI extraction function."""

    @patch("app.services.ai_extraction.encode_image_to_base64")
    @patch("app.services.ai_extraction.requests.post")
    @patch("app.services.ai_extraction.time.sleep")
    def test_extract_streets_success(self, mock_sleep, mock_post, mock_encode, app):
        """Test successful street extraction."""
        with app.app_context():
            # Setup mocks
            mock_encode.return_value = "base64_data"

            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [
                    {"message": {"content": '[{"prefix": "ul.", "main_name": "Marszałkowska"}]'}}
                ]
            }
            mock_post.return_value = mock_response

            # Test
            result = extract_streets_from_image("test.png", "Poznań", "1940-1949")

            expected = [{"prefix": "ul.", "main_name": "Marszałkowska"}]
            assert result == expected

            # Verify API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]["json"]["model"] == app.config["EXTRACTION_MODEL"]

    @patch("app.services.ai_extraction.encode_image_to_base64")
    @patch("app.services.ai_extraction.requests.post")
    def test_extract_streets_no_api_key(self, mock_post, mock_encode, app):
        """Test extraction without API key."""
        with app.app_context():
            app.config["OPENROUTER_API_KEY"] = ""

            with pytest.raises(ValueError, match="OPENROUTER_API_KEY is not configured"):
                extract_streets_from_image("test.png", "Poznań", "1940-1949")

    @patch("app.services.ai_extraction.encode_image_to_base64")
    @patch("app.services.ai_extraction.requests.post")
    def test_extract_streets_empty_response(self, mock_post, mock_encode, app):
        """Test extraction with empty AI response."""
        with app.app_context():
            mock_encode.return_value = "base64_data"

            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": "[]"  # Empty array
                        }
                    }
                ]
            }
            mock_post.return_value = mock_response

            result = extract_streets_from_image("test.png", "Poznań", "1940-1949")
            assert result == []

    @patch("app.services.ai_extraction.encode_image_to_base64")
    @patch("app.services.ai_extraction.requests.post")
    @patch("app.services.ai_extraction.time.sleep")
    def test_extract_streets_rate_limit_retry(self, mock_sleep, mock_post, mock_encode, app):
        """Test rate limit handling with retry."""
        with app.app_context():
            mock_encode.return_value = "base64_data"

            # First call returns 429, second succeeds
            mock_response_429 = Mock()
            mock_response_429.status_code = 429

            mock_response_success = Mock()
            mock_response_success.json.return_value = {
                "choices": [
                    {"message": {"content": '[{"prefix": "ul.", "main_name": "Test Street"}]'}}
                ]
            }

            mock_post.side_effect = [mock_response_429, mock_response_success]

            result = extract_streets_from_image("test.png", "Poznań", "1940-1949")

            expected = [{"prefix": "ul.", "main_name": "Test Street"}]
            assert result == expected

            # Verify retry happened
            assert mock_post.call_count == 2
            assert mock_sleep.call_count == 1

    @patch("app.services.ai_extraction.encode_image_to_base64")
    @patch("app.services.ai_extraction.requests.post")
    @patch("app.services.ai_extraction.time.sleep")
    def test_extract_streets_rate_limit_exhausted(self, mock_sleep, mock_post, mock_encode, app):
        """Test exhausted rate limit retries."""
        with app.app_context():
            mock_encode.return_value = "base64_data"

            mock_response = Mock()
            mock_response.status_code = 429
            mock_post.return_value = mock_response

            with pytest.raises(Exception, match="Rate limit exceeded"):
                extract_streets_from_image("test.png", "Poznań", "1940-1949")

            # Should retry max_retries + 1 times (3 + 1 = 4)
            assert mock_post.call_count == 4
            assert mock_sleep.call_count == 3

    @patch("app.services.ai_extraction.encode_image_to_base64")
    @patch("app.services.ai_extraction.requests.post")
    def test_extract_streets_invalid_json_response(self, mock_post, mock_encode, app):
        """Test invalid JSON in AI response."""
        with app.app_context():
            mock_encode.return_value = "base64_data"

            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "invalid json {{{"}}]
            }
            mock_post.return_value = mock_response

            with pytest.raises(Exception, match="Failed to parse AI response as JSON"):
                extract_streets_from_image("test.png", "Poznań", "1940-1949")

    @patch("app.services.ai_extraction.encode_image_to_base64")
    @patch("app.services.ai_extraction.requests.post")
    def test_extract_streets_markdown_json_response(self, mock_post, mock_encode, app):
        """Test AI response wrapped in markdown code blocks."""
        with app.app_context():
            mock_encode.return_value = "base64_data"

            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": """```json
[{"prefix": "ul.", "main_name": "Test Street"}]
```"""
                        }
                    }
                ]
            }
            mock_post.return_value = mock_response

            result = extract_streets_from_image("test.png", "Poznań", "1940-1949")
            expected = [{"prefix": "ul.", "main_name": "Test Street"}]
            assert result == expected

    @patch("app.services.ai_extraction.encode_image_to_base64")
    @patch("app.services.ai_extraction.requests.post")
    def test_extract_streets_non_list_response(self, mock_post, mock_encode, app):
        """Test AI response that is not a list."""
        with app.app_context():
            mock_encode.return_value = "base64_data"

            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": '{"not": "a list"}'}}]
            }
            mock_post.return_value = mock_response

            with pytest.raises(Exception, match="Response is not a list"):
                extract_streets_from_image("test.png", "Poznań", "1940-1949")

    @patch("app.services.ai_extraction.encode_image_to_base64")
    @patch("app.services.ai_extraction.requests.post")
    def test_extract_streets_400_error(self, mock_post, mock_encode, app):
        """Test 400 Bad Request error."""
        from requests.exceptions import RequestException

        with app.app_context():
            mock_encode.return_value = "base64_data"

            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Bad request details"

            exception = RequestException("400 Client Error")
            exception.response = mock_response
            mock_post.side_effect = exception

            with pytest.raises(Exception, match="Bad request to AI API"):
                extract_streets_from_image("test.png", "Poznań", "1940-1949")

    @patch("app.services.ai_extraction.encode_image_to_base64")
    @patch("app.services.ai_extraction.requests.post")
    def test_extract_streets_404_error(self, mock_post, mock_encode, app):
        """Test 404 Not Found error."""
        from requests.exceptions import RequestException

        with app.app_context():
            mock_encode.return_value = "base64_data"

            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Model not found"

            exception = RequestException("404 Client Error")
            exception.response = mock_response
            mock_post.side_effect = exception

            with pytest.raises(Exception, match="Model .* not found on OpenRouter"):
                extract_streets_from_image("test.png", "Poznań", "1940-1949")

    @patch("app.services.ai_extraction.encode_image_to_base64")
    @patch("app.services.ai_extraction.requests.post")
    @patch("app.services.ai_extraction.time.sleep")
    def test_extract_streets_network_error_retry(self, mock_sleep, mock_post, mock_encode, app):
        """Test network error handling with retry."""
        from requests.exceptions import RequestException

        with app.app_context():
            mock_encode.return_value = "base64_data"

            # Mock network error followed by success
            mock_success_response = Mock()
            mock_success_response.json.return_value = {
                "choices": [
                    {"message": {"content": '[{"prefix": "ul.", "main_name": "Recovered Street"}]'}}
                ]
            }

            # Network error without response (connection error)
            network_error = RequestException("Network error")

            mock_post.side_effect = [network_error, mock_success_response]

            result = extract_streets_from_image("test.png", "Poznań", "1940-1949")
            expected = [{"prefix": "ul.", "main_name": "Recovered Street"}]
            assert result == expected

            assert mock_post.call_count == 2
            assert mock_sleep.call_count == 1

    @patch("app.services.ai_extraction.encode_image_to_base64")
    @patch("app.services.ai_extraction.requests.post")
    @patch("app.services.ai_extraction.time.sleep")
    def test_extract_streets_network_error_exhausted(self, mock_sleep, mock_post, mock_encode, app):
        """Test exhausted network error retries."""
        from requests.exceptions import RequestException

        with app.app_context():
            mock_encode.return_value = "base64_data"

            mock_post.side_effect = RequestException("Persistent network error")

            with pytest.raises(Exception, match="API request failed after 4 attempts"):
                extract_streets_from_image("test.png", "Poznań", "1940-1949")

            assert mock_post.call_count == 4  # max_retries + 1
            assert mock_sleep.call_count == 3  # max_retries
