"""
Rule-based pricing calculator for print orders.
This module implements accurate mathematical calculations based on the pricing formulas
defined in PRICER_PROMPT, ensuring consistent and reliable pricing without LLM hallucination.
"""

import logging
import math
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class PricingCalculator:
    """
    Rule-based pricing calculator that implements exact mathematical formulas
    for print order pricing, eliminating LLM calculation errors.
    """

    # Base pricing constants (in ₹)
    BASE_PAPER_COST_PER_SQM = 2.0
    PHOTO_PAPER_PREMIUM_PER_SQM = 1.0

    # Digital printing costs
    DIGITAL_SETUP_COST = 300.0
    DIGITAL_COST_PER_PRINT = 1.5
    DIGITAL_EFFICIENCY_THRESHOLD = 1000  # Efficient for < 1000 qty

    # Offset printing costs
    OFFSET_SETUP_COST = 5000.0
    OFFSET_COST_PER_PRINT = 0.6
    OFFSET_EFFICIENCY_THRESHOLD = 500  # Efficient for > 500 qty

    # Double-sided printing multiplier (1.6x due to efficiency, not 2x)
    DOUBLE_SIDED_MULTIPLIER = 1.6

    # Finishing costs per sheet
    FINISHING_COSTS = {"laminate": 0.8, "cut": 0.5, "fold": 0.3, "none": 0.0}

    # Rush job premiums
    RUSH_PREMIUMS = {
        1: 0.15,  # 15% for 1-day rush
        2: 0.10,  # 10% for 2-day rush
    }

    # Margin range (18-22% competitive)
    MIN_MARGIN_RATE = 0.18
    MAX_MARGIN_RATE = 0.22
    DEFAULT_MARGIN_RATE = 0.20

    # Photo paper keywords for premium detection
    PHOTO_PAPER_KEYWORDS = ["photo", "poster", "a3", "a2", "canvas", "premium"]

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def calculate_pricing(self, specs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate accurate pricing based on specifications using rule-based math.

        Args:
            specs: Dictionary containing order specifications

        Returns:
            Dictionary with total_price, breakdown, and competitors
        """
        try:
            # Extract and validate specs
            quantity = int(specs.get("quantity", 100))
            width_mm = float(specs.get("width_mm", 210.0))
            height_mm = float(specs.get("height_mm", 297.0))
            material_gsm = int(specs.get("material_gsm", 80))
            sides = specs.get("sides", "single").lower()
            finishing = specs.get("finishing", "none").lower()
            print_method = specs.get("print_method", "digital").lower()
            turnaround_days = int(specs.get("turnaround_days", 3))

            self.logger.info(
                f"Calculating pricing for {quantity} units, {width_mm}x{height_mm}mm, {material_gsm}gsm"
            )

            # Step 1: Calculate paper area and cost
            area_sqm_per_sheet = (width_mm * height_mm) / 1_000_000  # Convert mm² to m²
            paper_cost = self._calculate_paper_cost(
                area_sqm_per_sheet, quantity, material_gsm, specs
            )

            # Step 2: Calculate printing cost (includes setup)
            printing_cost, setup_cost = self._calculate_printing_cost(
                quantity, print_method, sides
            )

            # Step 3: Calculate finishing cost
            finishing_cost = self._calculate_finishing_cost(quantity, finishing)

            # Step 4: Calculate subtotal before rush and margin
            subtotal = paper_cost + printing_cost + finishing_cost

            # Step 5: Apply rush premium if applicable
            rush_fee = self._calculate_rush_fee(subtotal, turnaround_days)
            subtotal_with_rush = subtotal + rush_fee

            # Step 6: Calculate competitive margin
            margin = self._calculate_margin(subtotal_with_rush, specs)

            # Step 7: Calculate final total
            total_price = subtotal_with_rush + margin

            # Step 8: Generate realistic competitors
            competitors = self._generate_competitors(total_price)

            breakdown = {
                "paper_cost": round(paper_cost, 2),
                "printing_cost": round(
                    printing_cost - setup_cost, 2
                ),  # Variable printing cost only
                "setup_cost": round(setup_cost, 2),
                "finishing_cost": round(finishing_cost, 2),
                "rush_fee": round(rush_fee, 2),
                "margin": round(margin, 2),
            }

            # Verify calculation integrity (allow for small floating point rounding)
            calculated_total = sum(breakdown.values())
            if abs(calculated_total - total_price) > 0.02:
                self.logger.warning(
                    f"Calculation verification failed. Expected: {total_price}, Got: {calculated_total}"
                )

            result = {
                "total_price": round(total_price, 2),
                "breakdown": breakdown,
                "competitors": competitors,
            }

            self.logger.info(f"Calculated total: ₹{total_price:.2f}")
            return result

        except Exception as e:
            self.logger.error(f"Pricing calculation failed: {e}")
            # Return fallback pricing
            return self._get_fallback_pricing(specs)

    def _calculate_paper_cost(
        self,
        area_sqm_per_sheet: float,
        quantity: int,
        material_gsm: int,
        specs: Dict[str, Any],
    ) -> float:
        """Calculate paper cost including GSM and photo premium."""

        # Base cost: area * quantity * base_rate * GSM_multiplier
        gsm_multiplier = material_gsm / 80.0  # Base is 80gsm
        base_paper_cost = (
            area_sqm_per_sheet
            * quantity
            * self.BASE_PAPER_COST_PER_SQM
            * gsm_multiplier
        )

        # Check if photo paper premium applies
        photo_premium = 0.0
        if self._is_photo_paper_order(specs):
            photo_premium = (
                area_sqm_per_sheet * quantity * self.PHOTO_PAPER_PREMIUM_PER_SQM
            )
            self.logger.debug(f"Applied photo paper premium: ₹{photo_premium:.2f}")

        total_paper_cost = base_paper_cost + photo_premium

        self.logger.debug(
            f"Paper: {area_sqm_per_sheet:.5f}m²/sheet × {quantity} × ₹{self.BASE_PAPER_COST_PER_SQM} × {gsm_multiplier:.3f} = ₹{base_paper_cost:.2f}"
        )

        return total_paper_cost

    def _calculate_printing_cost(
        self, quantity: int, print_method: str, sides: str
    ) -> Tuple[float, float]:
        """Calculate printing cost including setup, separated for breakdown."""

        sides_multiplier = self.DOUBLE_SIDED_MULTIPLIER if sides == "double" else 1.0

        if print_method == "digital":
            setup_cost = self.DIGITAL_SETUP_COST
            variable_cost = quantity * self.DIGITAL_COST_PER_PRINT * sides_multiplier
        else:  # offset
            setup_cost = self.OFFSET_SETUP_COST
            variable_cost = quantity * self.OFFSET_COST_PER_PRINT * sides_multiplier

        total_printing_cost = setup_cost + variable_cost

        self.logger.debug(
            f"Printing ({print_method}): ₹{setup_cost} setup + ({quantity} × ₹{self.DIGITAL_COST_PER_PRINT if print_method == 'digital' else self.OFFSET_COST_PER_PRINT} × {sides_multiplier:.1f}) = ₹{total_printing_cost:.2f}"
        )

        return total_printing_cost, setup_cost

    def _calculate_finishing_cost(self, quantity: int, finishing: str) -> float:
        """Calculate finishing cost per specification."""

        finishing_rate = self.FINISHING_COSTS.get(finishing.lower(), 0.0)
        finishing_cost = quantity * finishing_rate

        if finishing_cost > 0:
            self.logger.debug(
                f"Finishing ({finishing}): {quantity} × ₹{finishing_rate} = ₹{finishing_cost:.2f}"
            )

        return finishing_cost

    def _calculate_rush_fee(self, subtotal: float, turnaround_days: int) -> float:
        """Calculate rush fee based on turnaround time."""

        rush_premium_rate = self.RUSH_PREMIUMS.get(turnaround_days, 0.0)
        rush_fee = subtotal * rush_premium_rate

        if rush_fee > 0:
            self.logger.debug(
                f"Rush fee ({turnaround_days} days): ₹{subtotal:.2f} × {rush_premium_rate:.0%} = ₹{rush_fee:.2f}"
            )

        return rush_fee

    def _calculate_margin(
        self, subtotal_with_rush: float, specs: Dict[str, Any]
    ) -> float:
        """Calculate competitive margin based on order characteristics."""

        # Adjust margin rate based on order size and complexity
        quantity = specs.get("quantity", 100)
        margin_rate = self.DEFAULT_MARGIN_RATE

        # Higher margin for small orders (higher handling cost per unit)
        if quantity < 100:
            margin_rate = self.MAX_MARGIN_RATE
        elif quantity > 1000:
            margin_rate = self.MIN_MARGIN_RATE  # More competitive for bulk

        margin = subtotal_with_rush * margin_rate

        self.logger.debug(
            f"Margin ({margin_rate:.0%}): ₹{subtotal_with_rush:.2f} × {margin_rate:.0%} = ₹{margin:.2f}"
        )

        return margin

    def _is_photo_paper_order(self, specs: Dict[str, Any]) -> bool:
        """Determine if photo paper premium should apply."""

        # Check dimensions (A3 and larger typically photo paper)
        width = specs.get("width_mm", 210)
        height = specs.get("height_mm", 297)
        is_large_format = width >= 297 or height >= 420  # A3 or larger

        # Check material (high GSM suggests photo paper)
        gsm = specs.get("material_gsm", 80)
        is_heavy_paper = gsm >= 200

        # Check for photo-related keywords in any spec values
        spec_text = " ".join(str(v).lower() for v in specs.values() if v)
        has_photo_keywords = any(
            keyword in spec_text for keyword in self.PHOTO_PAPER_KEYWORDS
        )

        return is_large_format and (is_heavy_paper or has_photo_keywords)

    def _generate_competitors(self, base_price: float) -> List[Dict[str, Any]]:
        """Generate realistic competitor pricing."""

        # Competitors typically within ±15% of our calculated price
        comp1_price = base_price * (1 + 0.10)  # 10% higher
        comp2_price = base_price * (1 + 0.15)  # 15% higher

        competitors = [
            {"name": "PrintMaster Pro", "price": round(comp1_price, 2)},
            {"name": "QuickPrint Solutions", "price": round(comp2_price, 2)},
        ]

        return competitors

    def _get_fallback_pricing(self, specs: Dict[str, Any]) -> Dict[str, Any]:
        """Return safe fallback pricing if calculation fails."""

        quantity = specs.get("quantity", 100)
        # Simple fallback: ₹5 per unit + ₹300 setup
        fallback_total = (quantity * 5.0) + 300.0
        fallback_margin = fallback_total * 0.2

        return {
            "total_price": fallback_total + fallback_margin,
            "breakdown": {
                "paper_cost": quantity * 2.0,
                "printing_cost": quantity * 2.0,
                "setup_cost": 300.0,
                "finishing_cost": 0.0,
                "rush_fee": 0.0,
                "margin": fallback_margin,
            },
            "competitors": [
                {"name": "PrintMaster Pro", "price": fallback_total * 1.15},
                {"name": "QuickPrint Solutions", "price": fallback_total * 1.20},
            ],
        }


# Singleton instance for easy use
pricing_calculator = PricingCalculator()


def calculate_accurate_pricing(specs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to calculate pricing using the rule-based calculator.

    Args:
        specs: Dictionary containing order specifications

    Returns:
        Dictionary with accurate total_price, breakdown, and competitors
    """
    return pricing_calculator.calculate_pricing(specs)


def validate_and_compare_pricing(
    llm_result: Dict[str, Any], specs: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compare LLM pricing with rule-based calculation and use the most accurate.

    Args:
        llm_result: Pricing result from LLM
        specs: Order specifications

    Returns:
        Corrected pricing with validation notes
    """
    try:
        # Calculate accurate pricing
        accurate_pricing = calculate_accurate_pricing(specs)

        # Compare with LLM result
        llm_total = float(llm_result.get("total_price", 0))
        accurate_total = accurate_pricing["total_price"]

        # If LLM result is significantly different (>30%), use rule-based
        difference_percent = abs(llm_total - accurate_total) / accurate_total

        if difference_percent > 0.30:  # 30% threshold
            logger.warning(
                f"LLM pricing significantly off: ₹{llm_total} vs accurate ₹{accurate_total} "
                f"({difference_percent:.1%} difference). Using rule-based calculation."
            )
            # Add validation note
            accurate_pricing["validation_note"] = (
                f"LLM pricing corrected (was ₹{llm_total})"
            )
            return accurate_pricing
        else:
            # LLM result is reasonable, return as-is
            return llm_result

    except Exception as e:
        logger.error(f"Pricing validation failed: {e}")
        # Fall back to LLM result as-is
        return llm_result
