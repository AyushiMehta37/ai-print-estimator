# AI Print Estimator API Documentation

## Overview

The AI Print Estimator provides RESTful API endpoints for processing print orders from various input formats, extracting specifications using AI, calculating pricing, and managing order workflows.

**Base URL:** `http://localhost:8000` (development) / `https://your-domain.com` (production)

**Authentication:** None required (add API keys for production)

## Endpoints

### 1. POST /estimate

Process text input for print order estimation.

**Request:**
```json
{
  "input": "250 brochures, A4, double-sided, 200gsm, laminate",
  "input_type": "text"
}
```

**Response:**
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

**Status Codes:**
- 200: Success
- 422: Validation error
- 500: Internal server error

### 2. POST /estimate/upload

Upload and process PDF or image files for estimation.

**Request:** Multipart form data
- `file`: PDF or image file
- `input_type`: "pdf" or "image"

**Response:** Same as `/estimate`

**Supported File Types:**
- PDF: `.pdf`
- Images: `.jpg`, `.jpeg`, `.png`, `.gif`

**File Size Limit:** 10MB per file

### 3. GET /orders/{order_id}

Retrieve complete order details including estimates and audit trail.

**Response:**
```json
{
  "order_id": 1,
  "status": "pending",
  "specs": {...},
  "validation": {...},
  "estimate": {...},
  "audit": [
    {
      "action": "order_created",
      "actor": "system",
      "created_at": "2024-01-01T10:00:00",
      "notes": "Order created via API"
    }
  ]
}
```

### 4. POST /orders/{order_id}/status

Update order status (used by n8n workflows).

**Request:**
```json
{
  "status": "approved"
}
```

**Valid Statuses:**
- `pending`
- `review`
- `approved`
- `rejected`
- `processing`
- `completed`

## Data Models

### EstimateRequest
```typescript
{
  input: string;        // The order text/description
  input_type: string;   // "text" | "pdf" | "image"
}
```

### EstimateResponse
```typescript
{
  order_id: number;
  specs: {
    quantity?: number;
    width_mm?: number;
    height_mm?: number;
    material_gsm?: number;
    sides?: "single" | "double";
    finishing?: string;
    artwork_url?: string;
  };
  pricing: {
    total_price: number;
    breakdown: {
      setup_cost: number;
      paper_cost: number;
      printing_cost: number;
      finishing_cost: number;
      margin: number;
    };
  };
  validation: {
    valid: boolean;
    flags: string[];
  };
}
```

## n8n Integration

### Webhook Headers
Include `x-n8n-webhook-url` header to enable n8n workflow triggers.

### Workflow Events
- `estimate_created`: Fired after successful estimation
- `estimate_uploaded`: Fired after file upload processing
- `order_status_updated`: Fired after status changes

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": "Description of the error"
}
```

Common errors:
- Invalid input format
- File processing failures
- Database connection issues
- LLM API failures

## Rate Limiting

- 100 requests per minute per IP
- File uploads: 10 per minute

## Testing

Use the provided `test_api.py` script for endpoint testing:

```bash
# Text input
python test_api.py --text "100 business cards"

# File upload
python test_api.py --pdf "sample.pdf"
```

## OpenAPI Specification

Access the complete OpenAPI 3.0 specification at:
- Swagger UI: `http://localhost:8000/docs`
- JSON: `http://localhost:8000/openapi.json`

## Production Deployment

1. Set environment variables:
   ```bash
   export OPENROUTER_API_KEY=your_key
   export DATABASE_URL=postgresql://user:pass@host/db
   ```

2. Deploy with Docker:
   ```bash
   docker-compose up -d
   ```

3. Access API at configured domain/port