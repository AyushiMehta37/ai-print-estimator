# AI Print Estimator Database Schema

## Overview

The system uses PostgreSQL for production and SQLite for development. The schema consists of three main tables with relationships for order management, pricing estimates, and audit trails.

## Tables

### 1. orders

Main table storing order information and processing status.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique order identifier |
| input_type | VARCHAR(20) | NOT NULL | Input format: text, email, pdf, image |
| raw_input | TEXT | NOT NULL | Original input content |
| extracted_specs | JSON | NULL | AI-extracted specifications |
| validation_flags | JSON | NULL | Validation results and flags |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | Order status |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- Index on `status` for status filtering

**Relationships:**
- One-to-many with `estimates` table
- One-to-many with `audits` table

### 2. estimates

Stores pricing estimates with versioning support.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique estimate identifier |
| order_id | INTEGER | NOT NULL, FOREIGN KEY → orders.id | Reference to order |
| pricing | JSON | NOT NULL | Complete pricing breakdown |
| total_price | FLOAT | NOT NULL | Total calculated price |
| version | INTEGER | NOT NULL, DEFAULT 1 | Estimate version number |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY on `order_id`
- Index on `order_id` for order lookup
- Index on `(order_id, version)` for latest estimate queries

### 3. audits

Audit trail for all order actions and changes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique audit entry identifier |
| order_id | INTEGER | NOT NULL, FOREIGN KEY → orders.id | Reference to order |
| action | VARCHAR(50) | NOT NULL | Action performed |
| actor | VARCHAR(100) | NOT NULL | Who performed the action |
| notes | TEXT | NULL | Additional details |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Action timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY on `order_id`
- Index on `order_id` for audit history queries

## Relationships Diagram

```
orders (1) ──── (many) estimates
    │
    └─── (many) audits
```

## Common Actions

### Create New Order
```sql
INSERT INTO orders (input_type, raw_input, status)
VALUES ('text', '100 business cards', 'pending');
```

### Add Estimate
```sql
INSERT INTO estimates (order_id, pricing, total_price, version)
VALUES (1, '{"total_price": 300.0, "breakdown": {...}}', 300.0, 1);
```

### Update Order Status
```sql
UPDATE orders SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = 1;
INSERT INTO audits (order_id, action, actor, notes) VALUES (1, 'status_changed_to_approved', 'csr@test.local', 'Approved by customer service');
```

### Get Order with Latest Estimate
```sql
SELECT o.*, e.pricing, e.total_price
FROM orders o
LEFT JOIN estimates e ON o.id = e.order_id
WHERE o.id = 1
AND e.version = (SELECT MAX(version) FROM estimates WHERE order_id = 1);
```

## Data Types

### JSON Fields

#### extracted_specs
```json
{
  "quantity": 100,
  "width_mm": 85.0,
  "height_mm": 55.0,
  "material_gsm": 300,
  "sides": "double",
  "finishing": "laminate",
  "artwork_url": null
}
```

#### validation_flags
```json
{
  "valid": true,
  "flags": []
}
```

#### pricing (in estimates table)
```json
{
  "total_price": 450.25,
  "breakdown": {
    "setup_cost": 300.0,
    "paper_cost": 25.0,
    "printing_cost": 75.0,
    "finishing_cost": 20.0,
    "margin": 30.25
  }
}
```

## Migration Strategy

The project uses Alembic for database migrations. To create and apply migrations:

```bash
# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migration
alembic upgrade head
```

## Environment Configuration

### Development (SQLite)
```bash
DATABASE_URL=sqlite:///./print_estimator.db
```

### Production (PostgreSQL)
```bash
DATABASE_URL=postgresql://username:password@localhost:5432/print_estimator
```

## Backup Strategy

- **Development:** SQLite file backup
- **Production:** PostgreSQL pg_dump daily backups

## Performance Considerations

- Indexes on frequently queried columns (`order_id`, `status`)
- JSON fields for flexible schema evolution
- Connection pooling in production
- Read replicas for high-traffic scenarios