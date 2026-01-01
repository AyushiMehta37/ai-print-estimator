import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class PricingCalculator:
    BASE_PAPER_COST_PER_SQM = 2.0
    PHOTO_PAPER_PREMIUM_PER_SQM = 1.0
    DIGITAL_SETUP_COST = 300.0
    DIGITAL_COST_PER_PRINT = 1.5
    OFFSET_SETUP_COST = 5000.0
    OFFSET_COST_PER_PRINT = 0.6
    DOUBLE_SIDED_MULTIPLIER = 1.6
    FINISHING_COSTS = {"laminate": 0.8, "cut": 0.5, "fold": 0.3, "none": 0.0}
    RUSH_PREMIUMS = {1: 0.15, 2: 0.10}
    DEFAULT_MARGIN_RATE = 0.20
    PHOTO_PAPER_KEYWORDS = ["photo", "poster", "a3", "a2", "canvas", "premium"]

    def calculate_pricing(self, specs: Dict[str, Any]) -> Dict[str, Any]:
        try:
            quantity = int(specs.get("quantity", 100))
            width_mm = float(specs.get("width_mm", 210.0))
            height_mm = float(specs.get("height_mm", 297.0))
            material_gsm = int(specs.get("material_gsm", 80))
            sides = specs.get("sides", "single").lower()
            finishing = specs.get("finishing", "none").lower()
            print_method = specs.get("print_method", "digital").lower()
            turnaround_days = int(specs.get("turnaround_days", 3))

            area_sqm = (width_mm * height_mm) / 1_000_000
            paper_cost = self._calculate_paper_cost(area_sqm, quantity, material_gsm, specs)
            printing_cost, setup_cost = self._calculate_printing_cost(quantity, print_method, sides)
            finishing_cost = self._calculate_finishing_cost(quantity, finishing)

            subtotal = paper_cost + printing_cost + finishing_cost
            rush_fee = self._calculate_rush_fee(subtotal, turnaround_days)
            subtotal_with_rush = subtotal + rush_fee
            margin = self._calculate_margin(subtotal_with_rush, specs)
            total_price = subtotal_with_rush + margin

            competitors = self._generate_competitors(total_price)
            breakdown = {
                "paper_cost": round(paper_cost, 2),
                "printing_cost": round(printing_cost - setup_cost, 2),
                "setup_cost": round(setup_cost, 2),
                "finishing_cost": round(finishing_cost, 2),
                "rush_fee": round(rush_fee, 2),
                "margin": round(margin, 2),
            }

            return {
                "total_price": round(total_price, 2),
                "breakdown": breakdown,
                "competitors": competitors,
            }
        except Exception as e:
            logger.error(f"Pricing calculation failed: {e}")
            return self._get_fallback_pricing(specs)

    def _calculate_paper_cost(self, area_sqm: float, quantity: int, gsm: int, specs: Dict[str, Any]) -> float:
        gsm_multiplier = gsm / 80.0
        base_cost = area_sqm * quantity * self.BASE_PAPER_COST_PER_SQM * gsm_multiplier
        photo_premium = area_sqm * quantity * self.PHOTO_PAPER_PREMIUM_PER_SQM if self._is_photo_paper_order(specs) else 0.0
        return base_cost + photo_premium

    def _calculate_printing_cost(self, quantity: int, print_method: str, sides: str) -> Tuple[float, float]:
        sides_multiplier = self.DOUBLE_SIDED_MULTIPLIER if sides == "double" else 1.0
        if print_method == "digital":
            setup_cost = self.DIGITAL_SETUP_COST
            variable_cost = quantity * self.DIGITAL_COST_PER_PRINT * sides_multiplier
        else:
            setup_cost = self.OFFSET_SETUP_COST
            variable_cost = quantity * self.OFFSET_COST_PER_PRINT * sides_multiplier
        return setup_cost + variable_cost, setup_cost

    def _calculate_finishing_cost(self, quantity: int, finishing: str) -> float:
        return quantity * self.FINISHING_COSTS.get(finishing.lower(), 0.0)

    def _calculate_rush_fee(self, subtotal: float, turnaround_days: int) -> float:
        return subtotal * self.RUSH_PREMIUMS.get(turnaround_days, 0.0)

    def _calculate_margin(self, subtotal: float, specs: Dict[str, Any]) -> float:
        quantity = specs.get("quantity", 100)
        margin_rate = 0.22 if quantity < 100 else 0.18 if quantity > 1000 else self.DEFAULT_MARGIN_RATE
        return subtotal * margin_rate

    def _is_photo_paper_order(self, specs: Dict[str, Any]) -> bool:
        width, height = specs.get("width_mm", 210), specs.get("height_mm", 297)
        is_large = width >= 297 or height >= 420
        is_heavy = specs.get("material_gsm", 80) >= 200
        spec_text = " ".join(str(v).lower() for v in specs.values() if v)
        has_keywords = any(kw in spec_text for kw in self.PHOTO_PAPER_KEYWORDS)
        return is_large and (is_heavy or has_keywords)

    def _generate_competitors(self, base_price: float) -> List[Dict[str, Any]]:
        return [
            {"name": "PrintMaster Pro", "price": round(base_price * 1.10, 2)},
            {"name": "QuickPrint Solutions", "price": round(base_price * 1.15, 2)},
        ]

    def _get_fallback_pricing(self, specs: Dict[str, Any]) -> Dict[str, Any]:
        quantity = specs.get("quantity", 100)
        fallback_total = quantity * 5.0 + 300.0
        margin = fallback_total * 0.2
        return {
            "total_price": fallback_total + margin,
            "breakdown": {
                "paper_cost": quantity * 2.0,
                "printing_cost": quantity * 2.0,
                "setup_cost": 300.0,
                "finishing_cost": 0.0,
                "rush_fee": 0.0,
                "margin": margin,
            },
            "competitors": [
                {"name": "PrintMaster Pro", "price": round(fallback_total * 1.15, 2)},
                {"name": "QuickPrint Solutions", "price": round(fallback_total * 1.20, 2)},
            ],
        }


pricing_calculator = PricingCalculator()


def calculate_accurate_pricing(specs: Dict[str, Any]) -> Dict[str, Any]:
    return pricing_calculator.calculate_pricing(specs)


def validate_and_compare_pricing(llm_result: Dict[str, Any], specs: Dict[str, Any]) -> Dict[str, Any]:
    try:
        accurate_pricing = calculate_accurate_pricing(specs)
        llm_total = float(llm_result.get("total_price", 0))
        accurate_total = accurate_pricing["total_price"]

        if abs(llm_total - accurate_total) / accurate_total > 0.30:
            logger.warning(f"LLM pricing off: ₹{llm_total} vs ₹{accurate_total}. Using rule-based.")
            accurate_pricing["validation_note"] = f"LLM pricing corrected (was ₹{llm_total})"
            return accurate_pricing
        return llm_result
    except Exception as e:
        logger.error(f"Pricing validation failed: {e}")
        return llm_result
