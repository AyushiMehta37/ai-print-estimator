import base64
import json
import os
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
USE_OPENAI = bool(OPENAI_API_KEY)
API_KEY = OPENAI_API_KEY if USE_OPENAI else OPENROUTER_API_KEY
BASE_URL = "https://api.openai.com/v1/chat/completions" if USE_OPENAI else "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini" if USE_OPENAI else "anthropic/claude-3.5-sonnet"
MOCK_MODE = os.getenv("MOCK_LLM", "true").lower() == "true"

class LLMError(Exception):
    pass


async def call_llm(prompt: str, input_data: Dict[str, Any], model: Optional[str] = None, temperature: float = 0.1, max_tokens: int = 2000) -> Dict[str, Any]:
    if MOCK_MODE:
        return _mock_llm_response(prompt, input_data)

    if not API_KEY:
        raise LLMError("API key not found")

    formatted_prompt = prompt.format(**input_data)

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    if not USE_OPENAI:
        headers.update({"HTTP-Referer": "http://localhost:8000", "X-Title": "AI-Print-Estimator"})

    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [{"role": "user", "content": formatted_prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"}
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(BASE_URL, headers=headers, json=payload)
        if response.status_code != 200:
            raise LLMError(f"API error {response.status_code}: {response.text}")

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)


def call_llm_sync(
    prompt: str,
    input_data: Dict[str, Any],
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """
    Synchronous version of call_llm for non-async contexts.

    Args:
        Same as call_llm

    Returns:
        Parsed JSON dictionary from LLM response

    Raises:
        LLMError: If API call fails or response is invalid
    """

    # Use mock responses for testing
    if MOCK_MODE:
        return _mock_llm_response(prompt, input_data)

    if not API_KEY:
        api_name = "OPENAI_API_KEY" if USE_OPENAI else "OPENROUTER_API_KEY"
        raise LLMError(f"{api_name} not found in environment variables")

    # Format the prompt with input data
    try:
        formatted_prompt = prompt.format(**input_data)
    except KeyError as e:
        raise LLMError(f"Missing key in input_data for prompt formatting: {e}")

    # Prepare the API request headers
    if USE_OPENAI:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
    else:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": SITE_URL,
            "X-Title": APP_NAME,
        }

    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [{"role": "user", "content": formatted_prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    # Add JSON mode if supported
    if USE_OPENAI:
        payload["response_format"] = {"type": "json_object"}
    else:
        payload["response_format"] = {"type": "json_object"}

    try:
        # Make sync HTTP request
        with httpx.Client(timeout=60.0) as client:
            response = client.post(BASE_URL, headers=headers, json=payload)

            # Check for HTTP errors
            if response.status_code != 200:
                error_detail = response.text
                api_name = "OpenAI" if USE_OPENAI else "OpenRouter"
                raise LLMError(
                    f"{api_name} API error (status {response.status_code}): {error_detail}"
                )

            # Parse response
            response_data = response.json()

            # Extract the assistant's message content
            if "choices" not in response_data or len(response_data["choices"]) == 0:
                api_name = "OpenAI" if USE_OPENAI else "OpenRouter"
                raise LLMError(f"Invalid response structure from {api_name} API")

            content = response_data["choices"][0]["message"]["content"]

            # Parse JSON from content
            try:
                parsed_json = json.loads(content)
                return parsed_json
            except json.JSONDecodeError as e:
                logger.error(
                    "JSON parse failed in call_llm_sync",
                    extra={
                        "json_error": str(e),
                        "raw_content": content,
                        "content_length": len(content) if content else 0,
                    },
                )
                raise LLMError(
                    f"Failed to parse JSON from LLM response: {e}\nContent: {content}"
                )

    except httpx.RequestError as e:
        api_name = "OpenAI" if USE_OPENAI else "OpenRouter"
        raise LLMError(f"Network error calling {api_name} API: {e}")
    except Exception as e:
        raise LLMError(f"Unexpected error in LLM call: {e}")


# Optional: Helper function for streaming responses (if needed later)
async def call_llm_stream(
    prompt: str,
    input_data: Dict[str, Any],
    model: Optional[str] = None,
    temperature: float = 0.1,
):
    """
    Stream LLM response (useful for long outputs or real-time display).
    Not needed for JSON extraction but included for completeness.
    """

    if not API_KEY:
        api_name = "OPENAI_API_KEY" if USE_OPENAI else "OPENROUTER_API_KEY"
        raise LLMError(f"{api_name} not found in environment variables")

    formatted_prompt = prompt.format(**input_data)

    if USE_OPENAI:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
    else:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": SITE_URL,
            "X-Title": APP_NAME,
        }

    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [{"role": "user", "content": formatted_prompt}],
        "temperature": temperature,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST", BASE_URL, headers=headers, json=payload
        ) as response:
            if response.status_code != 200:
                api_name = "OpenAI" if USE_OPENAI else "OpenRouter"
                raise LLMError(f"{api_name} API error: {response.status_code}")

            async for chunk in response.aiter_lines():
                if chunk.startswith("data: "):
                    data = chunk[6:]
                    if data == "[DONE]":
                        break
                    try:
                        parsed = json.loads(data)
                        if "choices" in parsed and len(parsed["choices"]) > 0:
                            delta = parsed["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue


async def call_llm_vision(
    prompt: str,
    images: Optional[List[bytes]] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 4000,
) -> str:
    """
    Call OpenRouter API with a vision model to extract text from images.

    Args:
        prompt: The prompt/instruction for the vision model
        images: List of image bytes (will be converted to base64)
        model: Optional model override (uses vision-capable model if not specified)
        temperature: Controls randomness (0-1, lower is more deterministic)
        max_tokens: Maximum tokens in response

    Returns:
        Extracted text content from images

    Raises:
        LLMError: If API call fails or response is invalid
    """

    # Use mock responses for testing
    if MOCK_MODE:
        return "Mock image analysis: Found text requesting 250 brochures, A4 size, double-sided, 200gsm paper, gloss laminate finishing, full color printing, needed in 4 days."

    if not API_KEY:
        api_name = "OPENAI_API_KEY" if USE_OPENAI else "OPENROUTER_API_KEY"
        raise LLMError(f"{api_name} not found in environment variables")

    if not images:
        raise LLMError("At least one image must be provided")

    # Use a vision-capable model
    if USE_OPENAI:
        vision_model = model or "gpt-4o"  # OpenAI's vision model
    else:
        vision_model = model or "anthropic/claude-3.5-sonnet"  # OpenRouter vision model

    # Build content array
    content = [{"type": "text", "text": prompt}]

    # Convert images to base64 if provided
    if images:
        for img_bytes in images:
            # Detect image format from bytes - ONLY accept valid image formats
            # Reject PDFs and other non-image formats
            if img_bytes.startswith(b"\x89PNG\r\n\x1a\n") or img_bytes.startswith(
                b"\x89PNG"
            ):
                mime_type = "image/png"
            elif img_bytes.startswith(b"\xff\xd8\xff"):
                mime_type = "image/jpeg"
            elif img_bytes.startswith(b"GIF"):
                mime_type = "image/gif"
            elif img_bytes.startswith(b"RIFF") and b"WEBP" in img_bytes[:12]:
                mime_type = "image/webp"
            elif img_bytes.startswith(b"%PDF"):
                # PDF files should NOT be passed to vision API
                raise LLMError(
                    "PDF files cannot be passed to vision API. "
                    "Use extract_text_from_pdf_async() to extract text from PDFs instead."
                )
            else:
                # Unknown format - reject it to avoid API errors
                raise LLMError(
                    f"Invalid image format. Only PNG, JPEG, GIF, and WebP are supported. "
                    f"Received bytes starting with: {img_bytes[:20].hex()}"
                )

            base64_image = base64.b64encode(img_bytes).decode("utf-8")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                }
            )

    # Prepare the API request headers
    if USE_OPENAI:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
    else:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": SITE_URL,
            "X-Title": APP_NAME,
        }

    # Reduce max_tokens if not enough credits
    adjusted_max_tokens = min(max_tokens, 1000)
    payload = {
        "model": vision_model,
        "messages": [{"role": "user", "content": content}],
        "temperature": temperature,
        "max_tokens": adjusted_max_tokens,
    }

    try:
        # Make async HTTP request
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(BASE_URL, headers=headers, json=payload)

            # Check for HTTP errors
            if response.status_code != 200:
                error_detail = response.text
                api_name = "OpenAI" if USE_OPENAI else "OpenRouter"
                raise LLMError(
                    f"{api_name} API error (status {response.status_code}): {error_detail}"
                )

            # Parse response
            response_data = response.json()

            # Extract the assistant's message content
            if "choices" not in response_data or len(response_data["choices"]) == 0:
                api_name = "OpenAI" if USE_OPENAI else "OpenRouter"
                raise LLMError(f"Invalid response structure from {api_name} API")

            content_text = response_data["choices"][0]["message"]["content"]
            return content_text

    except httpx.RequestError as e:
        api_name = "OpenAI" if USE_OPENAI else "OpenRouter"
        raise LLMError(f"Network error calling {api_name} API: {e}")
    except Exception as e:
        raise LLMError(f"Unexpected error in LLM vision call: {e}")


def _mock_llm_response(prompt: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate mock responses for testing without hitting the LLM API.
    All pricing responses are validated for consistency.
    """
    # Check which prompt is being used based on content
    if "extract or estimate print order specifications" in prompt.lower():
        # Extractor prompt - check input type for artwork handling
        input_content = input_data.get("input", "")
        artwork_url = None

        if "Input Type: pdf" in input_content:
            artwork_url = "uploaded_pdf"
        elif "Input Type: image" in input_content:
            artwork_url = "uploaded_image"

        return {
            "quantity": 250,
            "width_mm": 210.0,
            "height_mm": 297.0,
            "material_gsm": 200,
            "sides": "double",
            "finishing": "laminate",
            "print_method": "digital",
            "turnaround_days": 4,
            "artwork_url": artwork_url,
        }
    elif "print pricing ai" in prompt.lower() or "base costs" in prompt.lower():
        # Pricer prompt - check input for specific requirements
        input_content = input_data.get("specs", "")

        # Check if it's A3 photo paper order (like the user's image)
        if any(
            keyword in str(input_content).lower()
            for keyword in ["297", "420", "a3", "photo", "poster"]
        ):
            # More competitive pricing for A3 photo posters
            # Calculate total to match breakdown: 85 + 375 + 300 + 0 + 390 + 550 = 1700
            pricing_response = {
                "total_price": 1700.0,
                "breakdown": {
                    "paper_cost": 85.0,
                    "printing_cost": 375.0,
                    "setup_cost": 300.0,
                    "finishing_cost": 0.0,
                    "rush_fee": 390.0,  # 15% rush premium
                    "margin": 550.0,
                },
                "competitors": [
                    {"name": "PhotoPrint Pro", "price": 3200.0},
                    {"name": "PosterExpress", "price": 2950.0},
                ],
            }
            return pricing_response
        else:
            # Standard pricing for regular orders
            # Calculate total to match breakdown: 195.97 + 675 + 300 + 200 + 0 + 504.28 = 1875.25
            pricing_response = {
                "total_price": 1875.25,
                "breakdown": {
                    "paper_cost": 195.97,
                    "printing_cost": 675.0,
                    "setup_cost": 300.0,
                    "finishing_cost": 200.0,
                    "rush_fee": 0.0,
                    "margin": 504.28,
                },
                "competitors": [
                    {"name": "PrintMaster Pro", "price": 2100.0},
                    {"name": "QuickPrint Solutions", "price": 1750.0},
                ],
            }
            return pricing_response
    elif "validate" in prompt.lower():
        # Validator prompt
        return {"valid": True, "flags": []}
    else:
        # Default response
        return {
            "status": "mock_response",
            "message": "This is a mock response for testing",
        }
