# AI Print Estimator - Test Examples

This file contains various test prompts you can use to verify the system is working correctly via command line.

## Basic Command Structure

```bash
# Basic text input test
python test_api.py --text "Your test prompt here"

# PDF file test  
python test_api.py --pdf "path/to/file.pdf"

# Image file test
python test_api.py --image "path/to/image.jpg"

# Get existing order details
python test_api.py --order 123
```

## Test Scenarios

### 1. Simple Standard Order
```bash
python test_api.py --text "I need 100 business cards, double-sided, standard paper"
```
**Expected Output:**
- Quantity: 100
- Small format (likely 85x55mm business card size)
- Double-sided printing
- Total price: ~₹300-500
- Valid order (no flags)

### 2. Rush Photo Poster (Previously Problematic)
```bash
python test_api.py --text "Urgent: 50 A3 photo posters, 250gsm glossy paper, need tomorrow"
```
**Expected Output:**
- Quantity: 50
- A3 size (297x420mm)
- 250gsm material
- 1-day turnaround (rush fee applied)
- Total price: ~₹580-650
- Valid order (should NOT have price_anomaly flag)
- Paper cost: ~₹45 (not ₹25)
- Rush fee: ~₹63 (not ₹712)

### 3. Large Volume Offset Job
```bash
python test_api.py --text "5000 A4 flyers, full color, double-sided, standard 150gsm, laminated, 1 week delivery"
```
**Expected Output:**
- Quantity: 5000
- A4 size (210x297mm)
- Print method: offset (efficient for high volume)
- Laminate finishing
- Total price: ~₹15,000-20,000
- Valid order

### 4. Small Rush Order (Edge Case)
```bash
python test_api.py --text "Emergency printing: 25 invitations, A5 size, premium paper, same day delivery"
```
**Expected Output:**
- Quantity: 25
- A5 size
- 1-day rush (15% premium)
- Higher per-unit cost due to small quantity
- Valid order despite high per-unit price

### 5. Problematic Order (Should Be Flagged)
```bash
python test_api.py --text "10000 business cards, need them in 4 hours, offset printing"
```
**Expected Output:**
- Should have validation flags:
  - `rush_conflict` (impossible timeline)
  - `material_mismatch` (offset setup time)

### 6. Missing Information Order
```bash
python test_api.py --text "I need some flyers printed"
```
**Expected Output:**
- System should fill in defaults:
  - Quantity: 100 (default)
  - Size: A4 (default)
  - Material: 80gsm (default)
- May have `low_res_art` flag (no artwork specified)

### 7. Poster with Specific Dimensions
```bash
python test_api.py --text "Need 75 posters printed, size 420x594mm, 200gsm paper, 3 days turnaround"
```
**Expected Output:**
- A2 size (420x594mm)
- Photo paper premium should apply
- No rush fees (3-day turnaround)
- Total price: ~₹800-1200

### 8. Complex Commercial Order
```bash
python test_api.py --text "Corporate brochure order: 2500 pieces, A4 tri-fold, 200gsm coated paper, double-sided CMYK, saddle-stitched binding, 5 business days"
```
**Expected Output:**
- High quantity
- Complex finishing (fold + binding)
- Premium paper
- Professional pricing tier

## What to Look For in Results

### ✅ Good Results Should Show:
1. **Consistent Breakdown**: All cost components sum to total price
2. **Realistic Pricing**: 
   - Business cards: ₹2-8 per piece
   - A4 flyers: ₹3-15 per piece  
   - Photo posters: ₹10-25 per piece
3. **Proper Rush Fees**: 
   - 1 day: 15% of subtotal
   - 2 days: 10% of subtotal
4. **Accurate Paper Costs**: Include GSM multipliers and photo premiums
5. **Validation Notes**: If LLM was corrected, should show "LLM pricing corrected"

### ❌ Red Flags to Watch For:
1. **Math Errors**: Breakdown doesn't sum to total
2. **Extreme Pricing**: Orders off by 3x+ expected price
3. **Wrong Rush Calculations**: Rush fees over ₹200 for small orders
4. **Paper Cost Issues**: ₹25 for heavy paper orders (should be ₹40+)
5. **False Validation Flags**: Premium orders marked as price anomalies

## Quick Verification Commands

### Check System Status
```bash
# Check if server is running
curl http://localhost:8000/

# Quick API test
curl -X POST http://localhost:8000/estimate \
  -H "Content-Type: application/json" \
  -d '{"input": "100 business cards", "input_type": "text"}'
```

### Batch Testing
```bash
# Test multiple scenarios quickly
python test_api.py --text "50 business cards"
python test_api.py --text "100 A4 flyers, glossy"  
python test_api.py --text "25 A3 posters, urgent"
```

## Expected System Behavior

### Before Our Fixes (Problems):
- LLM returns ₹4,740 for ₹580 job (704% error)
- Paper cost: ₹25 (too low)
- Rush fee: ₹712 (way too high)
- Breakdown sum ≠ total price
- Valid premium orders flagged as anomalies

### After Our Fixes (Current):
- LLM errors automatically detected and corrected
- Rule-based calculation provides accurate fallback
- All breakdowns mathematically consistent
- Premium orders validated correctly
- Detailed logging shows when corrections are made

## Troubleshooting

### If You Get Errors:
1. **Server not running**: Start with `uvicorn app.main:app --reload`
2. **API key issues**: Check if MOCK_LLM=true for testing
3. **Connection errors**: Verify localhost:8000 is accessible
4. **Validation errors**: Check the specific flags returned

### If Results Look Wrong:
1. **Compare with expected ranges above**
2. **Check for "validation_note" in response**
3. **Verify breakdown components sum correctly**
4. **Look for reasonable competitor pricing**

## Success Criteria

The system is working correctly if:
- ✅ Pricing accuracy within 10% of expected
- ✅ Mathematical consistency (breakdown = total)
- ✅ Appropriate validation flags only
- ✅ Rush orders handled properly
- ✅ Photo paper premiums applied correctly
- ✅ LLM corrections logged when needed

Run several of these tests to verify your system is performing accurately and consistently!