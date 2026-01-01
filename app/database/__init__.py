import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./print_estimator.db",  # SQLite fallback for development
)

# Create SQLAlchemy engine
if DATABASE_URL.startswith("sqlite"):
    # SQLite configuration
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL query logging during development
        connect_args={
            "check_same_thread": False
        },  # Allow SQLite to be used across threads
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using them
        echo=False,  # Set to True for SQL query logging during development
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


# ============================================================================
# Database Models
# ============================================================================


class Order(Base):
    """
    Main order table - stores raw input and extracted specifications
    """

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    # Input tracking
    input_type = Column(String(20), nullable=False)  # text, email, pdf, image
    raw_input = Column(Text, nullable=False)  # Original input content

    # Extracted data (JSON columns)
    extracted_specs = Column(JSON, nullable=True)  # From extractor LLM
    validation_flags = Column(JSON, nullable=True)  # From validator LLM

    # Order status tracking
    status = Column(
        String(20), nullable=False, default="pending"
    )  # pending, review, approved, rejected, processing, completed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    estimates = relationship(
        "Estimate", back_populates="order", cascade="all, delete-orphan"
    )
    audits = relationship("Audit", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.id}, status={self.status}, type={self.input_type})>"


class Estimate(Base):
    """
    Pricing estimates table - supports multiple versions per order
    """

    __tablename__ = "estimates"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)

    # Pricing data
    pricing = Column(JSON, nullable=False)  # Full pricing breakdown from pricer LLM
    total_price = Column(Float, nullable=False)  # Quick access to total

    # Versioning (if order is re-estimated)
    version = Column(Integer, nullable=False, default=1)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="estimates")

    def __repr__(self):
        return f"<Estimate(id={self.id}, order_id={self.order_id}, total={self.total_price}, v{self.version})>"


class Audit(Base):
    """
    Audit trail table - tracks all actions on orders
    """

    __tablename__ = "audits"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)

    # Action tracking
    action = Column(
        String(50), nullable=False
    )  # created, validated, approved, rejected, etc.
    actor = Column(String(100), nullable=False)  # system, csr@test.local, api, etc.
    notes = Column(Text, nullable=True)  # Additional details

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="audits")

    def __repr__(self):
        return f"<Audit(id={self.id}, order_id={self.order_id}, action={self.action})>"


# ============================================================================
# Database Dependency for FastAPI
# ============================================================================


def get_db():
    """
    FastAPI dependency to get database session.

    Usage in routes:
        @router.get("/orders/{order_id}")
        def get_order(order_id: int, db: Session = Depends(get_db)):
            order = db.query(Order).filter(Order.id == order_id).first()
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Database Initialization
# ============================================================================


def create_tables():
    """
    Create all tables in the database.
    Run this once during initial setup or in migrations.
    """
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")


def drop_tables():
    """
    Drop all tables (use with caution, only for development).
    """
    Base.metadata.drop_all(bind=engine)
    print("✓ Database tables dropped")


# ============================================================================
# Helper Functions for Common Operations
# ============================================================================


def create_order(db: Session, input_type: str, raw_input: str) -> Order:
    """Create a new order"""
    order = Order(input_type=input_type, raw_input=raw_input, status="pending")
    db.add(order)
    db.commit()
    db.refresh(order)

    # Create initial audit entry
    create_audit(db, order.id, "order_created", "system", "Order created via API")

    return order


def update_order_specs(db: Session, order_id: int, specs: dict, validation: dict):
    """Update order with extracted specs and validation results"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        order.extracted_specs = specs
        order.validation_flags = validation
        order.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
    return order


def create_estimate(
    db: Session, order_id: int, pricing: dict, total_price: float
) -> Estimate:
    """Create a pricing estimate for an order"""
    # Get the next version number
    existing_estimates = (
        db.query(Estimate).filter(Estimate.order_id == order_id).count()
    )
    version = existing_estimates + 1

    estimate = Estimate(
        order_id=order_id, pricing=pricing, total_price=total_price, version=version
    )
    db.add(estimate)
    db.commit()
    db.refresh(estimate)

    # Create audit entry
    create_audit(
        db,
        order_id,
        "estimate_created",
        "system",
        f"Estimate v{version} created: ₹{total_price}",
    )

    return estimate


def update_order_status(
    db: Session,
    order_id: int,
    new_status: str,
    actor: str = "system",
    notes: str = None,
):
    """Update order status and create audit trail"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(order)

        # Create audit entry
        audit_notes = notes or f"Status changed from {old_status} to {new_status}"
        create_audit(
            db, order_id, f"status_changed_to_{new_status}", actor, audit_notes
        )

    return order


def create_audit(
    db: Session, order_id: int, action: str, actor: str, notes: str = None
) -> Audit:
    """Create an audit log entry"""
    audit = Audit(order_id=order_id, action=action, actor=actor, notes=notes)
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


def get_order_with_relations(db: Session, order_id: int) -> Optional[Order]:
    """Get order with all estimates and audit logs"""
    return db.query(Order).filter(Order.id == order_id).first()


def get_latest_estimate(db: Session, order_id: int) -> Optional[Estimate]:
    """Get the most recent estimate for an order"""
    return (
        db.query(Estimate)
        .filter(Estimate.order_id == order_id)
        .order_by(Estimate.version.desc())
        .first()
    )


# ============================================================================
# Initialization Script (run this once)
# ============================================================================

if __name__ == "__main__":
    """
    Run this file directly to initialize the database:
    python -m app.database
    """
    print("Initializing database...")
    create_tables()
    print("Database setup complete!")
