from typing import Dict, Any
from sqlalchemy.orm import Session
from app.services.extractor import extract_specs
from app.services.pricer import price_order
from app.services.validator import validate_order
from app.database import create_order, update_order_specs, create_estimate

class EstimationError(Exception):
    pass

async def estimate_pipeline(input_text: str, input_type: str, db: Session) -> Dict[str, Any]:
    """
    Orchestrates the estimation pipeline:
        1. Extract specs from unstructured input
        2. Price the order with LLM
        3. Validate order specs + pricing
        4. Write to DB (order, specs, estimate, validation)
    Returns: dict for API response
    Throws EstimationError on failure.
    """
    try:
        # 1. Create DB order record (raw_input, status=pending)
        order = create_order(db, input_type=input_type, raw_input=input_text)

        # 2. Extract specs
        specs = await extract_specs(input_text, input_type)

        # 3. Price the order
        pricing = await price_order(specs)

        # 4. Validate order
        validation = await validate_order(specs, pricing)

        # 5. Update order with specs & validation results
        update_order_specs(db, order.id, specs, validation)

        # 6. Save estimate
        estimate = create_estimate(db, order.id, pricing, pricing.get("total_price", 0.0))

        # Prepare output
        return {
            "order_id": order.id,
            "specs": specs,
            "pricing": pricing,
            "validation": validation
        }
    except Exception as e:
        db.rollback()
        raise EstimationError(f"Estimation pipeline failed: {e}")
