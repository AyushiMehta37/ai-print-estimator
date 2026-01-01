import asyncio
import io
from typing import Any, Dict

from app.core.llm import LLMError, call_llm, call_llm_vision
from app.core.prompts import EXTRACTOR_PROMPT


async def extract_specs(input_text: str, input_type: str) -> Dict[str, Any]:
    """
    Extract print order specifications from unstructured input using LLM.

    Args:
        input_text: The raw input content (text, email body, PDF text, or image description)
        input_type: Type of input - "text", "pdf", "email", or "image"

    Returns:
        Dictionary with extracted specifications:
        {
            "quantity": int,
            "width_mm": float,
            "height_mm": float,
            "material_gsm": int,
            "sides": "single|double",
            "finishing": "laminate|cut|fold|none",
            "print_method": "digital|offset",
            "turnaround_days": int,
            "artwork_url": string | null
        }

    Raises:
        LLMError: If extraction fails
    """

    # Prepare input context based on type
    input_context = f"Input Type: {input_type}\n\n{input_text}"

    # Add specific instructions based on input type
    if input_type == "image":
        input_context += "\n\nNote: This is an uploaded image. Extract dimensions and specs from the visual content."
    elif input_type == "pdf":
        input_context += "\n\nNote: This is extracted text from a PDF document. Look for specifications throughout the document."
    elif input_type == "email":
        input_context += "\n\nNote: This is an email body. Extract relevant print specifications from the message."

    try:
        # Call LLM with the extractor prompt
        result = await call_llm(
            prompt=EXTRACTOR_PROMPT,
            input_data={"input": input_context},
            temperature=0.1,  # Low temperature for consistency
            max_tokens=512,
        )

        # Validate required fields are present
        required_fields = [
            "quantity",
            "width_mm",
            "height_mm",
            "material_gsm",
            "sides",
            "finishing",
            "print_method",
            "turnaround_days",
        ]

        for field in required_fields:
            if field not in result:
                raise LLMError(f"Missing required field in extraction: {field}")

        # Type validation and cleanup
        result["quantity"] = int(result["quantity"])
        result["width_mm"] = float(result["width_mm"])
        result["height_mm"] = float(result["height_mm"])
        result["material_gsm"] = int(result["material_gsm"])
        result["turnaround_days"] = int(result["turnaround_days"])

        # Validate enum fields
        if result["sides"] not in ["single", "double"]:
            result["sides"] = "single"  # Default fallback

        if result["finishing"] not in ["laminate", "cut", "fold", "none"]:
            result["finishing"] = "none"  # Default fallback

        if result["print_method"] not in ["digital", "offset"]:
            # Auto-select based on quantity
            result["print_method"] = "offset" if result["quantity"] > 500 else "digital"

        # Handle artwork_url
        if "artwork_url" not in result:
            result["artwork_url"] = None

        # If input was an image or PDF, mark it as uploaded artwork
        if input_type == "image":
            result["artwork_url"] = "uploaded_image"
        elif input_type == "pdf":
            result["artwork_url"] = "uploaded_pdf"

        return result

    except LLMError as e:
        raise LLMError(f"Spec extraction failed: {e}")
    except (ValueError, TypeError) as e:
        raise LLMError(f"Invalid data type in extracted specs: {e}")
    except Exception as e:
        raise LLMError(f"Unexpected error during extraction: {e}")


def extract_specs_sync(input_text: str, input_type: str) -> Dict[str, Any]:
    """
    Synchronous version of extract_specs for non-async contexts.

    Args:
        Same as extract_specs

    Returns:
        Same as extract_specs

    Raises:
        LLMError: If extraction fails
    """
    from app.core.llm import call_llm_sync

    input_context = f"Input Type: {input_type}\n\n{input_text}"

    if input_type == "image":
        input_context += "\n\nNote: This is an uploaded image. Extract dimensions and specs from the visual content."
    elif input_type == "pdf":
        input_context += "\n\nNote: This is extracted text from a PDF document."
    elif input_type == "email":
        input_context += "\n\nNote: This is an email body."

    try:
        result = call_llm_sync(
            prompt=EXTRACTOR_PROMPT,
            input_data={"input": input_context},
            temperature=0.1,
            max_tokens=512,
        )

        # Same validation as async version
        required_fields = [
            "quantity",
            "width_mm",
            "height_mm",
            "material_gsm",
            "sides",
            "finishing",
            "print_method",
            "turnaround_days",
        ]

        for field in required_fields:
            if field not in result:
                raise LLMError(f"Missing required field: {field}")

        result["quantity"] = int(result["quantity"])
        result["width_mm"] = float(result["width_mm"])
        result["height_mm"] = float(result["height_mm"])
        result["material_gsm"] = int(result["material_gsm"])
        result["turnaround_days"] = int(result["turnaround_days"])

        if result["sides"] not in ["single", "double"]:
            result["sides"] = "single"

        if result["finishing"] not in ["laminate", "cut", "fold", "none"]:
            result["finishing"] = "none"

        if result["print_method"] not in ["digital", "offset"]:
            result["print_method"] = "offset" if result["quantity"] > 500 else "digital"

        if "artwork_url" not in result:
            result["artwork_url"] = None

        if input_type == "image":
            result["artwork_url"] = "uploaded_image"
        elif input_type == "pdf":
            result["artwork_url"] = "uploaded_pdf"

        return result

    except Exception as e:
        raise LLMError(f"Spec extraction failed: {e}")


# Helper function for handling PDF input
async def extract_text_from_pdf_async(pdf_content: bytes) -> str:
    """
    Extract text from PDF bytes using PyMuPDF text extraction.

    Note: PDFs should be extracted as text directly, NOT using vision API.
    Vision API is only for actual image files (PNG/JPEG/WebP/GIF).

    Args:
        pdf_content: Raw PDF file bytes

    Returns:
        Extracted text content from all PDF pages
    """
    try:
        # Use PyMuPDF to extract text directly from PDF
        # This is the correct approach - PDFs should NOT use vision API
        try:
            import fitz  # PyMuPDF

            pdf_doc = fitz.open(stream=pdf_content, filetype="pdf")
            all_text = []

            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                # Extract text from page
                page_text = page.get_text()
                if page_text.strip():  # Only add non-empty pages
                    all_text.append(page_text)

            pdf_doc.close()

            if not all_text:
                raise LLMError("No text content found in PDF")

            # Combine all extracted text with page breaks
            combined_text = "\n\n--- Page Break ---\n\n".join(all_text)
            return combined_text

        except ImportError:
            raise LLMError(
                "PDF processing requires PyMuPDF. "
                "Please install it with: pip install -r requirements.txt"
            )

    except LLMError:
        raise
    except Exception as e:
        raise LLMError(f"Failed to extract text from PDF: {str(e)}")


# Synchronous wrapper for backward compatibility
def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extract text from PDF bytes using PyMuPDF (synchronous wrapper).

    Args:
        pdf_content: Raw PDF file bytes

    Returns:
        Extracted text content from all PDF pages
    """
    try:
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(extract_text_from_pdf_async(pdf_content))
        finally:
            loop.close()
    except RuntimeError:
        # If there's already an event loop running, use it
        return asyncio.run(extract_text_from_pdf_async(pdf_content))


# Helper function for handling image input
async def describe_image_async(image_content: bytes) -> str:
    """
    Get description of image using vision model.
    Uses OpenRouter's vision models to extract text and analyze image content.

    Args:
        image_content: Raw image file bytes (PNG, JPEG, WebP, or GIF)

    Returns:
        Description or extracted text from image
    """
    try:
        # Use vision API to extract text and analyze image
        prompt = """Extract all text content and relevant information from this image.
        If this is a print order document, extract specifications like:
        - Quantity
        - Dimensions (width x height)
        - Material type and GSM
        - Print method
        - Finishing options
        - Any other relevant print specifications

        Return the extracted information in a clear, structured format."""

        # call_llm_vision only accepts image formats (PNG/JPEG/WebP/GIF)
        # This function should only be called with actual image files
        description = await call_llm_vision(
            prompt=prompt, images=[image_content], max_tokens=2000
        )

        return description

    except LLMError:
        raise
    except Exception as e:
        raise LLMError(f"Failed to analyze image: {str(e)}")


# Synchronous wrapper for backward compatibility
def describe_image(image_content: bytes) -> str:
    """
    Get description of image using vision model (synchronous wrapper).

    Args:
        image_content: Raw image file bytes

    Returns:
        Description or extracted text from image
    """
    try:
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(describe_image_async(image_content))
        finally:
            loop.close()
    except RuntimeError:
        # If there's already an event loop running, use it
        return asyncio.run(describe_image_async(image_content))
