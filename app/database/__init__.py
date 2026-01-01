import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./print_estimator.db")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=not DATABASE_URL.startswith("sqlite")
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============================================================================
# Database Models
# ============================================================================


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    input_type = Column(String(20), nullable=False)
    raw_input = Column(Text, nullable=False)
    extracted_specs = Column(JSON, nullable=True)
    validation_flags = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    estimates = relationship("Estimate", back_populates="order", cascade="all, delete-orphan")
    audits = relationship("Audit", back_populates="order", cascade="all, delete-orphan")


class Estimate(Base):
    __tablename__ = "estimates"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    pricing = Column(JSON, nullable=False)
    total_price = Column(Float, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    order = relationship("Order", back_populates="estimates")


class Audit(Base):
    __tablename__ = "audits"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    actor = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    order = relationship("Order", back_populates="audits")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


def create_order(db: Session, input_type: str, raw_input: str) -> Order:
    order = Order(input_type=input_type, raw_input=raw_input, status="pending")
    db.add(order)
    db.commit()
    db.refresh(order)
    create_audit(db, order.id, "order_created", "system", "Order created via API")
    return order


def update_order_specs(db: Session, order_id: int, specs: dict, validation: dict):
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        order.extracted_specs = specs
        order.validation_flags = validation
        order.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
    return order


def create_estimate(db: Session, order_id: int, pricing: dict, total_price: float) -> Estimate:
    existing_count = db.query(Estimate).filter(Estimate.order_id == order_id).count()
    version = existing_count + 1
    estimate = Estimate(order_id=order_id, pricing=pricing, total_price=total_price, version=version)
    db.add(estimate)
    db.commit()
    db.refresh(estimate)
    create_audit(db, order_id, "estimate_created", "system", f"Estimate v{version} created: ₹{total_price}")
    return estimate


def update_order_status(db: Session, order_id: int, new_status: str, actor: str = "system", notes: str = None):
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
        audit_notes = notes or f"Status changed from {old_status} to {new_status}"
        create_audit(db, order_id, f"status_changed_to_{new_status}", actor, audit_notes)
    return order


def create_audit(db: Session, order_id: int, action: str, actor: str, notes: str = None) -> Audit:
    audit = Audit(order_id=order_id, action=action, actor=actor, notes=notes)
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


def get_order_with_relations(db: Session, order_id: int) -> Optional[Order]:
    return db.query(Order).filter(Order.id == order_id).first()


def get_latest_estimate(db: Session, order_id: int) -> Optional[Estimate]:
    return db.query(Estimate).filter(Estimate.order_id == order_id).order_by(Estimate.version.desc()).first()


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
