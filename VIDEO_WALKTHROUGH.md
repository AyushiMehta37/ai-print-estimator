# AI Print Estimator - Video Walkthrough Guide

## Overview
This guide provides step-by-step instructions for demonstrating the AI Print Estimator system. Follow these steps to showcase all features in approximately 8-10 minutes.

## Demo Script

### 1. Introduction (1 minute)
- Show project structure and key files
- Explain the system architecture (FastAPI + PostgreSQL + n8n + LLM)
- Highlight key features: multi-input support, AI extraction, pricing calculation, validation

### 2. Environment Setup (2 minutes)

#### Start the System
```bash
# Navigate to project directory
cd ai-print-estimator

# Start all services with Docker
docker-compose up -d

# Check services are running
docker ps
```

#### Verify Services
- **API**: http://localhost:8000 (FastAPI)
- **n8n**: http://localhost:5678 (admin/admin123)
- **PostgreSQL**: localhost:5432

### 3. API Testing (3 minutes)

#### Test Text Input
```bash
python test_api.py --text "100 business cards, double-sided, glossy finish"
```

**Expected Output:**
- Order ID created
- Specifications extracted (quantity, size, material, etc.)
- Pricing breakdown with realistic costs
- Validation results

#### Test Multiple Scenarios
```bash
# Large volume offset job
python test_api.py --text "5000 A4 flyers, full color, double-sided"

# Rush order
python test_api.py --text "50 A3 posters, urgent delivery tomorrow"

# Complex order
python test_api.py --text "250 brochures, A4 tri-fold, 200gsm, laminated"
```

### 4. Web Interface Demo (2 minutes)

#### Open Frontend
- Open `frontend.html` in browser
- Show tabbed interface (Text Input / File Upload)

#### Submit Text Order
- Enter: "100 business cards, double-sided, urgent"
- Show real-time processing
- Display results with pricing breakdown

### 5. n8n Workflow Integration (2 minutes)

#### Access n8n Interface
- Open http://localhost:5678
- Login: admin/admin123

#### Import Workflow
- Import `n8n-workflow-config.json`
- Show workflow nodes: Webhook → If → Email/Slack → Wait → MIS Handoff

#### Test Workflow
```bash
# Submit order with n8n webhook
curl -X POST http://localhost:8000/estimate \
  -H "x-n8n-webhook-url: http://host.docker.internal:5678/webhook/order-orchestrator" \
  -H "Content-Type: application/json" \
  -d '{"input": "500 flyers, urgent", "input_type": "text"}'
```

- Show workflow execution in n8n
- Demonstrate conditional logic (valid/invalid orders)

### 6. Database & API Documentation (1 minute)

#### Show API Docs
- Open http://localhost:8000/docs (Swagger UI)
- Demonstrate endpoint testing
- Show OpenAPI specification

#### Database Schema
- Reference `DATABASE_SCHEMA.md`
- Show table relationships
- Explain audit trail functionality

### 7. Advanced Features (1 minute)

#### Competitor Pricing
- Show competitor data in API responses
- Reference `app/services/competitor_scraper.py`

#### Prompt Engineering
- Reference `PROMPT_ENGINEERING.md`
- Explain LLM optimization techniques

### 8. Conclusion (30 seconds)
- Summarize key achievements
- Highlight production readiness
- Show performance metrics from `PROJECT_STATUS.md`

## Key Demo Points to Emphasize

1. **AI Accuracy**: Show how unstructured text becomes structured data
2. **Pricing Realism**: Demonstrate competitive, profitable pricing
3. **Validation Intelligence**: Show smart flagging vs false positives
4. **Workflow Automation**: Illustrate end-to-end order processing
5. **Scalability**: Docker deployment for production use

## Backup Demo (If Docker Fails)

If Docker has issues, demonstrate locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set mock mode
export MOCK_LLM=true

# Start server
uvicorn app.main:app --reload

# Run tests
python test_api.py --text "100 business cards"
```

## Timing Breakdown
- Setup: 2 minutes
- API Testing: 3 minutes
- Web Interface: 2 minutes
- n8n Workflows: 2 minutes
- Documentation: 1 minute
- Conclusion: 30 seconds

**Total: ~10 minutes**

This walkthrough demonstrates a complete, production-ready AI-powered print estimation system with enterprise-grade features and documentation.