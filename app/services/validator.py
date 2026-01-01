from typing import Any, Dict, List

from app.core.llm import LLMError, call_llm
from app.core.prompts import VALIDATOR_PROMPT


async def validate_order(
    specs: Dict[str, Any], pricing: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate print order specifications and pricing for feasibility and issues.

    Args:
        specs: Dictionary of extracted specifications
        pricing: Dictionary of calculated pricing

    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "flags": [string]  # List of issue flags
        }

        Possible flags:
        - "missing_qty": Quantity seems unreasonably low/high
        - "low_res_art": Artwork resolution may be insufficient
        - "invalid_size": Dimensions are non-standard or problematic
        - "rush_conflict": Turnaround time conflicts with quantity/complexity
        - "price_anomaly": Calculated price seems unusual
        - "material_mismatch": Material specs incompatible with print method
        - "finishing_conflict": Finishing option not feasible with specs

    Raises:
        LLMError: If validation fails
    """

    try:
        # Format specs and pricing for the prompt
        specs_str = format_data_for_validation(specs, pricing)

        # Call LLM with the validator prompt
        result = await call_llm(
            prompt=VALIDATOR_PROMPT,
            input_data={"specs": specs_str, "pricing": str(pricing)},
            temperature=0.1,  # Very low temperature for consistent validation
            max_tokens=512,
        )

        # Validate response structure
        if "valid" not in result:
            raise LLMError("Missing 'valid' field in validation response")

        if "flags" not in result:
            result["flags"] = []

        # Ensure correct types
        result["valid"] = bool(result["valid"])

        if not isinstance(result["flags"], list):
            result["flags"] = []

        # Clean flags list (ensure all are strings)
        result["flags"] = [str(flag) for flag in result["flags"]]

        # Additional rule-based validation checks
        additional_flags = perform_rule_based_validation(specs, pricing)

        # Merge LLM flags with rule-based flags (avoid duplicates)
        all_flags = list(set(result["flags"] + additional_flags))
        result["flags"] = all_flags

        # If there are any flags, mark as invalid
        if len(result["flags"]) > 0:
            result["valid"] = False

        return result

    except LLMError as e:
        raise LLMError(f"Order validation failed: {e}")
    except Exception as e:
        raise LLMError(f"Unexpected error during validation: {e}")


def validate_order_sync(
    specs: Dict[str, Any], pricing: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Synchronous version of validate_order for non-async contexts.

    Args:
        Same as validate_order

    Returns:
        Same as validate_order

    Raises:
        LLMError: If validation fails
    """
    from app.core.llm import call_llm_sync

    try:
        specs_str = format_data_for_validation(specs, pricing)

        result = call_llm_sync(
            prompt=VALIDATOR_PROMPT,
            input_data={"specs": specs_str, "pricing": str(pricing)},
            temperature=0.1,
            max_tokens=512,
        )

        if "valid" not in result:
            raise LLMError("Missing 'valid' field in validation response")

        if "flags" not in result:
            result["flags"] = []

        result["valid"] = bool(result["valid"])

        if not isinstance(result["flags"], list):
            result["flags"] = []

        result["flags"] = [str(flag) for flag in result["flags"]]

        additional_flags = perform_rule_based_validation(specs, pricing)
        all_flags = list(set(result["flags"] + additional_flags))
        result["flags"] = all_flags

        if len(result["flags"]) > 0:
            result["valid"] = False

        return result

    except Exception as e:
        raise LLMError(f"Order validation failed: {e}")


def perform_rule_based_validation(
    specs: Dict[str, Any], pricing: Dict[str, Any]
) -> List[str]:
    """
    Perform rule-based validation checks using accurate pricing calculations.
    Uses the same pricing calculator as the pricer service to eliminate false positives.

    Args:
        specs: Specifications dictionary
        pricing: Pricing dictionary

    Returns:
        List of flag strings
    """
    flags = []

    quantity = specs.get("quantity", 0)
    width_mm = specs.get("width_mm", 0)
    height_mm = specs.get("height_mm", 0)
    material_gsm = specs.get("material_gsm", 0)
    print_method = specs.get("print_method", "")
    turnaround_days = specs.get("turnaround_days", 0)
    finishing = specs.get("finishing", "none")
    total_price = pricing.get("total_price", 0)

    # Check 1: Quantity validation
    if quantity <= 0:
        flags.append("missing_qty")
    elif quantity > 50000:
        flags.append("missing_qty")  # Suspiciously high for typical print runs

    # Check 2: Size validation
    if width_mm < 50 or height_mm < 50:
        flags.append("invalid_size")  # Too small
    elif width_mm > 1000 or height_mm > 1500:
        flags.append("invalid_size")  # Too large for most printers

    # Check 3: Material validation
    if material_gsm < 60 or material_gsm > 400:
        flags.append("material_mismatch")

    # Check 4: Rush conflict
    if turnaround_days < 2 and quantity > 5000:
        flags.append("rush_conflict")  # Can't print 5000+ in under 2 days

    if turnaround_days < 1:
        flags.append("rush_conflict")  # Same-day is almost always problematic

    # Check 5: Print method mismatch
    if print_method == "digital" and quantity > 5000:
        flags.append("material_mismatch")  # Digital is inefficient for high volume

    if print_method == "offset" and quantity < 500:
        flags.append("material_mismatch")  # Offset setup cost too high for low qty

    # Check 6: Finishing conflicts
    if finishing == "laminate" and material_gsm < 100:
        flags.append("finishing_conflict")  # Lamination on thin paper is problematic

    # Check 7: Price anomaly detection using accurate pricing calculator
    try:
        from app.services.pricing_calculator import calculate_accurate_pricing

        # Calculate what the price should be using our accurate calculator
        expected_pricing = calculate_accurate_pricing(specs)
        expected_total = expected_pricing["total_price"]

        # Define acceptable deviation range (50% to account for market variations)
        deviation_threshold = 0.50  # 50% deviation allowance
        lower_threshold = expected_total * (1 - deviation_threshold)
        upper_threshold = expected_total * (1 + deviation_threshold)

        # Only flag if price deviates significantly from accurate calculation
        if total_price < lower_threshold:
            flags.append("price_anomaly")  # Suspiciously low pricing
        elif total_price > upper_threshold:
            flags.append("price_anomaly")  # Suspiciously high pricing

        # For very small orders (< 100 qty), be more lenient with pricing
        # Setup costs can make small orders appear expensive
        if quantity < 100 and total_price < expected_total * 3.0:
            flags = [f for f in flags if f != "price_anomaly"]

    except Exception as e:
        # Fallback to basic validation if pricing calculator fails
        area_sqm = (width_mm * height_mm) / 1_000_000
        sides_multiplier = 2 if specs.get("sides") == "double" else 1

        # Very basic fallback estimate
        if print_method == "digital":
            basic_estimate = (quantity * area_sqm * 20 * sides_multiplier) + 300
        else:
            basic_estimate = (quantity * area_sqm * 10 * sides_multiplier) + 5000

        # Only flag extreme deviations in fallback mode
        if total_price < basic_estimate * 0.2 or total_price > basic_estimate * 5.0:
            flags.append("price_anomaly")

    # Check 8: Artwork validation
    artwork_url = specs.get("artwork_url")
    # Only flag if no artwork AND no uploaded file (PDF/image)
    if not artwork_url and quantity >= 250:
        flags.append("low_res_art")  # No artwork for significant order
    # Don't flag if artwork was uploaded (PDF or image)
    elif artwork_url in ["uploaded_pdf", "uploaded_image"]:
        pass  # Artwork provided via upload - no flag needed

    return flags


def format_data_for_validation(specs: Dict[str, Any], pricing: Dict[str, Any]) -> str:
    """
    Format specifications and pricing into readable text for LLM validation prompt.

    Args:
        specs: Specifications dictionary
        pricing: Pricing dictionary

    Returns:
        Formatted string
    """
    formatted = f"""
SPECIFICATIONS:
- Quantity: {specs.get("quantity", "N/A")}
- Dimensions: {specs.get("width_mm", "N/A")}mm x {specs.get("height_mm", "N/A")}mm
- Paper: {specs.get("material_gsm", "N/A")}gsm
- Sides: {specs.get("sides", "N/A")}
- Finishing: {specs.get("finishing", "none")}
- Print Method: {specs.get("print_method", "N/A")}
- Turnaround: {specs.get("turnaround_days", "N/A")} days
- Artwork: {"Provided" if specs.get("artwork_url") else "Not provided"}

PRICING:
- Total Price: Rs. {pricing.get("total_price", "N/A")}
- Paper Cost: Rs. {pricing.get("breakdown", {}).get("paper_cost", "N/A")}
- Printing Cost: Rs. {pricing.get("breakdown", {}).get("printing_cost", "N/A")}
- Setup Cost: Rs. {pricing.get("breakdown", {}).get("setup_cost", "N/A")}
- Finishing Cost: Rs. {pricing.get("breakdown", {}).get("finishing_cost", 0)}
- Rush Fee: Rs. {pricing.get("breakdown", {}).get("rush_fee", 0)}
"""
    return formatted.strip()


# Helper function for generating validation summary
def generate_validation_summary(validation_result: Dict[str, Any]) -> str:
    """
    Generate human-readable validation summary.

    Args:
        validation_result: Result from validate_order

    Returns:
        Human-readable summary string
    """
    if validation_result["valid"]:
        return "✓ Order validation passed. No issues detected."

    flags = validation_result.get("flags", [])

    if not flags:
        return "✓ Order validation passed."

    # Map flags to user-friendly messages
    flag_messages = {
        "missing_qty": "Quantity appears unusual or missing",
        "low_res_art": "Artwork may be low resolution or missing",
        "invalid_size": "Dimensions are non-standard",
        "rush_conflict": "Turnaround time may not be feasible",
        "price_anomaly": "Pricing appears unusual",
        "material_mismatch": "Material specifications may not be compatible",
        "finishing_conflict": "Finishing option may not be feasible",
    }

    issues = []
    for flag in flags:
        message = flag_messages.get(flag, flag)
        issues.append(f"• {message}")

    summary = "✗ Order validation failed. Issues detected:\n" + "\n".join(issues)
    return summary
