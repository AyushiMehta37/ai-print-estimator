# AI Print Estimator

An intelligent print order estimation system that uses AI to extract specifications from unstructured input (text, PDF, images) and provides accurate pricing estimates.

## Features

- **Multi-input Support**: Text, PDF uploads, and image uploads
- **AI-Powered Extraction**: Automatically extracts print specifications from any input format
- **Realistic Pricing**: Competitive pricing with appropriate setup costs and margins
- **Smart Validation**: Conservative validation to minimize false positives
- **Artwork Detection**: Recognizes uploaded files as artwork to prevent false flags
- **Database Integration**: Stores orders, estimates, and audit trails
- **API-First Design**: RESTful API with comprehensive endpoints

## Recent Fixes Applied

All major logical issues have been resolved:

- **Eliminated false 'missing_qty' flags** for valid quantities (e.g., 250 pieces)
- **Reduced pricing by 77.8%** with realistic setup costs (₹300 vs ₹5,000 for digital)
- **Fixed artwork detection** for PDF and image uploads
- **Improved validation logic** with conservative flagging approach
- **Added mock mode** for testing without API credits

See `FIXES_SUMMARY.md` for detailed technical information.

## Prerequisites

- Python 3.8+
- OpenRouter API key (for production)
- PostgreSQL (optional, SQLite used by default)

## Installation

1. **Clone and setup:**
   ```bash
   cd ai-print-estimator
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   # Copy and edit .env file
   # Set your OpenRouter API key for production
   # Use MOCK_LLM=true for testing without API costs
   ```

3. **Initialize database:**
   ```bash
   python -c "from app.database import create_tables; create_tables()"
   ```

## Usage

### Start the Server

```bash
# Activate virtual environment
venv\Scripts\activate

# Start server
python -m uvicorn app.main:app --reload --port 8000
```

### Test with Different Input Types

```bash
# Text input
python test_api.py --text "250 brochures, A4, double-sided, 200gsm, laminate"

# PDF upload
python test_api.py --pdf "path/to/your/file.pdf"

# Image upload
python test_api.py --image "path/to/your/image.jpg"

# Get order details
python test_api.py --order 1
```

### Expected Results (Fixed System)

For "250 brochures, A4, double-sided, 200gsm, laminate":

```json
{
  "order_id": 1,
  "specs": {
    "quantity": 250,
    "width_mm": 210.0,
    "height_mm": 297.0,
    "material_gsm": 200,
    "sides": "double",
    "finishing": "laminate",
    "artwork_url": null
  },
  "pricing": {
    "total_price": 1875.25,
    "breakdown": {
      "setup_cost": 300.0,
      "paper_cost": 195.97,
      "printing_cost": 675.0,
      "finishing_cost": 200.0,
      "margin": 504.28
    }
  },
  "validation": {
    "valid": false,
    "flags": ["low_res_art"]
  }
}
```

## API Endpoints

- `POST /estimate` - Submit text for estimation
- `POST /estimate/upload` - Upload PDF/image for estimation
- `GET /orders/{order_id}` - Retrieve order details
- `POST /orders/{order_id}/status` - Update order status
- `GET /` - Health check

## Pricing Model

### Digital Printing
- Setup cost: ₹300
- Per print: ₹1.5 + material costs
- Efficient for quantities < 1000

### Offset Printing
- Setup cost: ₹5000
- Per print: ₹0.6 + material costs
- Efficient for quantities > 500

### Additional Costs
- Double-sided: 1.6x print cost
- Laminate finishing: ₹0.8 per sheet
- Rush jobs (<3 days): 30% premium
- Standard margin: 20-25%

## Validation Rules

Conservative validation approach to minimize false positives:

- **missing_qty**: Only if quantity ≤ 0 or > 50,000
- **low_res_art**: Only if no artwork for orders ≥ 250 pieces
- **price_anomaly**: Only if pricing is clearly unrealistic
- **material_mismatch**: Only if print method doesn't suit quantity

## Project Structure

```
ai-print-estimator/
├── app/
│   ├── api/           # API routes and endpoints
│   ├── core/          # LLM integration and prompts
│   ├── database/      # Database models and operations
│   ├── schemas/       # API schemas
│   └── services/      # Business logic (extractor, pricer, validator, scraper)
├── tests/             # Test files
├── alembic/           # Database migrations
├── test_api.py        # Main testing script
├── frontend.html      # Simple web interface
├── API_DOCUMENTATION.md    # Complete API documentation
├── DATABASE_SCHEMA.md      # Database schema documentation
├── PROMPT_ENGINEERING.md   # AI prompt optimization guide
├── FIXES_SUMMARY.md   # Detailed fix documentation
└── requirements.txt   # Dependencies
```

## Web Interface

A simple HTML frontend is included for easy order submission:

```bash
# Open in browser
start frontend.html
```

Features:
- Text input for order descriptions
- File upload for PDFs and images
- Real-time pricing estimates
- Responsive design

## Documentation

### API Documentation
- **Swagger UI**: `http://localhost:8000/docs` (when server running)
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`
- **Detailed Docs**: See `API_DOCUMENTATION.md`

### Database Schema
Complete database documentation available in `DATABASE_SCHEMA.md`

### AI Prompt Engineering
Learn about the AI optimization techniques in `PROMPT_ENGINEERING.md`

## Testing

### Production Mode (with API)
```bash
# Set in .env file
MOCK_LLM=false
OPENROUTER_API_KEY=your_actual_key

python test_api.py --text "your order text"
```

### Mock Mode (no API costs)
```bash
# Set in .env file
MOCK_LLM=true

python test_api.py --text "your order text"
```

## Performance Improvements

| Metric | Before | After | Improvement |
|--------|--------|--------|-------------|
| Total Price (250 brochures) | ₹8,450 | ₹1,875 | 77.8% reduction |
| Setup Cost (digital) | ₹5,000 | ₹300 | 94% reduction |
| False Validation Flags | 2-3 | 0-1 | 67-100% reduction |
| Per Unit Cost | ₹33.80 | ₹7.50 | 78% reduction |

## Contributing

1. Follow existing code structure
2. Add tests for new features
3. Update documentation
4. Ensure all validation tests pass

## License

[Add your license information here]

## Support

For issues or questions:
1. Check `FIXES_SUMMARY.md` for detailed technical information
2. Run tests with mock mode to verify functionality
3. Review API endpoint documentation above

## Success Metrics

Your system now provides:
- Competitive pricing for small digital runs
- Realistic setup costs across all print methods
- Accurate per-unit calculations
- Professional profit margins
- Smart input processing (text, PDF, images)
- Minimal false validation flags