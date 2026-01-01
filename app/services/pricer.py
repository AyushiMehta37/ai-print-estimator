import logging
from typing import Any, Dict

from app.core.llm import LLMError, call_llm
from app.core.prompts import PRICER_PROMPT

logger = logging.getLogger(__name__)


async def price_order(specs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Price the print order using LLM with rule-based validation and correction.

    This function attempts to get pricing from the LLM first, then validates
    the mathematical accuracy against rule-based calculations. If the LLM
    result is significantly inaccurate, it falls back to rule-based pricing.

    Args:
        specs: Dictionary of extracted specifications.
    Returns:
        Dictionary with pricing breakdown, total price, and competitors.
    Raises:
        LLMError: If both LLM and rule-based pricing fail.
    """
    try:
        # Import rule-based calculator
        from app.services.pricing_calculator import validate_and_compare_pricing

        # Attempt to get LLM pricing
        try:
            llm_result = await call_llm(
                prompt=PRICER_PROMPT,
                input_data={"specs": specs},
                temperature=0.1,
                max_tokens=512,
            )

            # Parse and validate LLM output
            if "total_price" not in llm_result:
                raise LLMError("Missing total_price in LLM pricing response")
            if "breakdown" not in llm_result:
                llm_result["breakdown"] = {}
            if "competitors" not in llm_result:
                llm_result["competitors"] = []
            llm_result["total_price"] = float(llm_result["total_price"])

            # Validate LLM result against rule-based calculations
            result = validate_and_compare_pricing(llm_result, specs)

            logger.info(
                f"Pricing completed for {specs.get('quantity', 'N/A')} units: ₹{result['total_price']}"
            )
            return result

        except Exception as llm_error:
            logger.warning(
                f"LLM pricing failed: {llm_error}. Falling back to rule-based calculation."
            )

            # Fall back to rule-based pricing
            from app.services.pricing_calculator import calculate_accurate_pricing

            result = calculate_accurate_pricing(specs)
            result["validation_note"] = "LLM unavailable - used rule-based calculation"

            logger.info(f"Rule-based pricing completed: ₹{result['total_price']}")
            return result

    except Exception as e:
        logger.error(f"All pricing methods failed: {e}")
        raise LLMError(f"Pricing failed: {e}")
