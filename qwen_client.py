import json
import logging
import time
from typing import Any, Dict, List, Optional, Union

import requests

from config import config

logger = logging.getLogger(__name__)

REQUIRED_PRODUCT_FIELDS = [
    "cleaned_canonical_name",
    "general_class",
    "ingredient_type",
    "functional_role",
    "physical_form",
    "application_domain",
    "synonyms",
    "short_embedding_text",
    "confidence",
    "taste"
]


class QwenClient:
    """Client for interacting with an Ollama remote model for structured product data."""

    def __init__(self):
        self.base_url = config.OLLAMA_BASE_URL
        self.model = config.OLLAMA_MODEL_NAME
        self.timeout = config.OLLAMA_TIMEOUT_SECONDS

    def get_product_structured_data(
        self,
        original_product_name: str,
        cleaned_product_name: str,
        supplier_name: str,
        supplier_data_text: str,
        allowed_classes: List[str]
    ) -> Dict[str, Any]:
        """Get structured product data from the Ollama model."""
        prompt = self._build_prompt(
            original_product_name,
            cleaned_product_name,
            supplier_name,
            supplier_data_text,
            allowed_classes
        )

        last_error: Optional[Exception] = None
        for attempt in range(1, 4):
            logger.info(f"Ollama request attempt {attempt} for product {original_product_name}")
            try:
                response_text = self._call_api(prompt)
                result = self._parse_and_validate_response(response_text)
                logger.info("Ollama request succeeded")
                return result
            except Exception as exc:
                logger.warning(f"Ollama validation failed on attempt {attempt}: {exc}")
                last_error = exc
                if attempt < 3:
                    time.sleep(1)
                    continue
                logger.error("Ollama request failed after 3 attempts")
                raise last_error

    def get_supplier_summary_json(
        self,
        supplier_name: str,
        supplier_data_text: str
    ) -> Dict[str, Any]:
        """Return supplier summary JSON for storage."""
        supplier_summary = supplier_data_text.strip() or supplier_name
        return {
            "supplier_summary": supplier_summary,
            "supplier_type": supplier_name,
            "confidence": 1.0
        }

    def test_connection(self) -> bool:
        """Test the Ollama server connection."""
        prompt = 'Return JSON: {"status":"ok"}'
        try:
            response_text = self._call_api(prompt)
            if isinstance(response_text, dict):
                data = response_text
            else:
                data = json.loads(response_text.strip())
            return data.get("status") == "ok"
        except Exception:
            logger.exception("Ollama connection test failed")
            return False

    def _build_prompt(
        self,
        original_product_name: str,
        cleaned_product_name: str,
        supplier_name: str,
        supplier_data_text: str,
        allowed_classes: List[str]
    ) -> str:
        classes_str = ", ".join(f'"{cls}"' for cls in allowed_classes)
        return (
            "Analyze the following food ingredient/supplement raw material and return a valid JSON object with only the required fields.\n"
            "Product Information:\n"
            f"- Original Name: {original_product_name}\n"
            f"- Cleaned Name: {cleaned_product_name}\n"
            f"- Supplier: {supplier_name}\n"
            f"- Additional Data: {supplier_data_text}\n\n"
            "Provide JSON with exactly these keys:\n"
            "cleaned_canonical_name, general_class, ingredient_type, functional_role, physical_form, application_domain, synonyms, short_embedding_text, confidence, taste\n"
            f"Use general_class from this list: {classes_str}.\n"
            "synonyms must be an array. confidence must be a number between 0.0 and 1.0.\n"
            "Do not return any extra text or explanation."
        )

    def _call_api(self, prompt: str) -> Union[str, Dict[str, Any]]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        logger.info(f"Sending request to Ollama at {url}")

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            response_data = response.json()
            return self._extract_response_text(response_data)
        except requests.RequestException as exc:
            logger.error(f"Ollama HTTP request failed: {exc}")
            raise
        except ValueError as exc:
            logger.error(f"Failed to parse Ollama JSON response: {exc}")
            raise

    def _extract_response_text(self, response_data: Any) -> Union[str, Dict[str, Any]]:
        if isinstance(response_data, dict):
            if self._has_required_fields(response_data):
                return response_data

            if "output" in response_data:
                return self._normalize_output(response_data["output"])
            if "result" in response_data:
                return self._normalize_output(response_data["result"])
            if "text" in response_data:
                return self._normalize_output(response_data["text"])
            if "response" in response_data:
                return self._normalize_output(response_data["response"])
            if "status" in response_data:
                return response_data
            if "choices" in response_data and isinstance(response_data["choices"], list) and response_data["choices"]:
                first_choice = response_data["choices"][0]
                if isinstance(first_choice, dict):
                    if "message" in first_choice and isinstance(first_choice["message"], dict):
                        return self._normalize_output(first_choice["message"].get("content", ""))
                    return self._normalize_output(first_choice.get("text", ""))

        if isinstance(response_data, str):
            return response_data

        raise ValueError("Ollama response did not include a recognized output field")

    def _normalize_output(self, raw_output: Any) -> str:
        if isinstance(raw_output, list):
            return "".join(str(item) for item in raw_output)
        if raw_output is None:
            return ""
        return str(raw_output)

    def _parse_and_validate_response(self, response: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(response, dict):
            data = response
        else:
            try:
                data = json.loads(response.strip())
            except json.JSONDecodeError as exc:
                logger.error(f"Invalid JSON response from Ollama: {response}")
                raise ValueError(f"Invalid JSON response: {exc}")

        if not self._has_required_fields(data):
            missing = [field for field in REQUIRED_PRODUCT_FIELDS if field not in data]
            raise ValueError(f"Missing required fields: {missing}")

        if not isinstance(data["synonyms"], list):
            data["synonyms"] = [data["synonyms"]] if data["synonyms"] else []

        if not isinstance(data["confidence"], (int, float)):
            raise ValueError("confidence field must be a number")
        if not 0.0 <= data["confidence"] <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        return data

    def _has_required_fields(self, data: Any) -> bool:
        return isinstance(data, dict) and all(field in data for field in REQUIRED_PRODUCT_FIELDS)


# Global client instance
qwen_client = QwenClient()