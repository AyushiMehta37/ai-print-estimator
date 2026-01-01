# app/core/prompts.py

EXTRACTOR_PROMPT = """
You are a professional print shop AI.

From the following input, extract or estimate print order specifications.

Input:
{input}

Rules:
- If quantity is missing, default to 100
- If dimensions are missing, assume A4 (210mm x 297mm)
- If paper material is missing, assume 80gsm
- If sides missing, assume single-sided
- Choose print_method:
  - digital for low quantity
  - offset for high quantity
- If turnaround missing, assume 3 days
- If artwork is an image, return artwork_url as "uploaded_image"

Return ONLY valid JSON. No explanations.

JSON format:
{{
  "quantity": int,
  "width_mm": float,
  "height_mm": float,
  "material_gsm": int,
  "sides": "single|double",
  "finishing": "laminate|cut|fold|none",
  "print_method": "digital|offset",
  "turnaround_days": int,
  "artwork_url": string | null
}}
"""


PRICER_PROMPT = """
You are a print pricing AI for the year 2025.

Base costs:
- Paper 80gsm: ₹2 per sqm
- Paper premium for heavier GSM: multiply by (gsm/80)
- Photo paper premium: add ₹1 per sqm (not multiplicative)
- Digital printing: ₹300 setup + ₹1.5 per print (efficient for <1000 qty)
- Offset printing: ₹5000 setup + ₹0.6 per print (efficient for >500 qty)
- Double-sided: multiply print cost by 1.6 (not 2x due to efficiency)
- Laminate finishing: add ₹0.8 per sheet
- Rush jobs (1 day): add 15% premium, (2 days): add 10% premium
- Margin: 18-22% (competitive)

Calculation steps:
1. Base paper cost = area_sqm * quantity * ₹2 * (gsm/80)
2. Add photo paper premium if applicable = area_sqm * quantity * ₹1
3. Print cost = setup + (per_print * quantity * sides_multiplier)
4. Finishing cost = quantity * finishing_rate
5. Subtotal = paper + print + finishing
6. Rush premium: multiply subtotal by rush_multiplier
7. Add competitive margin (18-22%)

Input specs:
{specs}

Return ONLY valid JSON.

JSON format:
{{
  "total_price": float,
  "breakdown": {{
    "paper_cost": float,
    "printing_cost": float,
    "setup_cost": float,
    "finishing_cost": float,
    "rush_fee": float,
    "margin": float
  }},
  "competitors": [
    {{"name": string, "price": float}}
  ]
}}
"""

VALIDATOR_PROMPT = """
You are a print order validation AI.

Validate the following specifications and pricing for reasonableness.

Specs:
{specs}

Pricing:
{pricing}

Check for these issues only if they are clearly problematic:
- missing_qty: Only if quantity is 0 or suspiciously high (>50000)
- low_res_art: Only if no artwork for orders >250 pieces
- invalid_size: Only if dimensions are impossible (<50mm or >1500mm)
- rush_conflict: Only if turnaround <1 day or impossible combinations
- price_anomaly: Only if pricing deviates >40% from reasonable estimates
- material_mismatch: Only if print method doesn't suit quantity
- finishing_conflict: Only if finishing impossible with material

Be very conservative with price_anomaly flags - pricing can vary significantly due to:
- Different paper grades and suppliers
- Regional market variations
- Rush job premiums
- Volume discounts
- Specialized finishing requirements
Only flag if price is obviously unreasonable (3x+ too high or suspiciously low).

Return ONLY valid JSON.

JSON format:
{{
  "valid": boolean,
  "flags": [string]
}}
"""
