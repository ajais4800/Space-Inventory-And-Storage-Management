from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON, Date
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sism.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Models ────────────────────────────────────────────────────────────────────

class PerishableItem(Base):
    __tablename__ = "perishable_items"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    unit = Column(String, default="kg")
    reorder_point_kg = Column(Float, default=100.0)
    lead_days = Column(Integer, default=2)
    storage_temp_min_c = Column(Float, default=0.0)
    storage_temp_max_c = Column(Float, default=15.0)
    shelf_life_days = Column(Integer, default=7)
    ripeness_curve = Column(String, default="sigmoid")
    ripeness_peak_day = Column(Integer, default=3)
    zone = Column(String, default="ambient")
    varieties = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    batches = relationship("InventoryBatch", back_populates="item")
    order_items = relationship("OrderItem", back_populates="item")
    procurement_recs = relationship("ProcurementRecommendation", back_populates="item")


class StorageContainer(Base):
    __tablename__ = "storage_containers"
    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    zone_type = Column(String, nullable=False)  # ambient, refrigerated, cold_chain, freezer
    capacity_kg = Column(Float, nullable=False)
    current_load_kg = Column(Float, default=0.0)
    rows = Column(Integer, default=4)
    cols = Column(Integer, default=4)
    depths = Column(Integer, default=3)
    temp_c = Column(Float, default=15.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    batches = relationship("InventoryBatch", back_populates="container")
    placements = relationship("StoragePlacement", back_populates="container")


class InventoryBatch(Base):
    __tablename__ = "inventory_batches"
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String, unique=True, index=True, nullable=False)
    item_id = Column(Integer, ForeignKey("perishable_items.id"), nullable=False)
    container_id = Column(Integer, ForeignKey("storage_containers.id"), nullable=True)
    quantity_kg = Column(Float, nullable=False)
    variety = Column(String, nullable=True)
    received_date = Column(Date, nullable=False)
    expected_ripeness_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    storage_temp_actual_c = Column(Float, nullable=True)
    # 3D spatial positioning
    position_index = Column(Integer, default=0)  # 0=front(exit), higher=deeper
    row = Column(Integer, default=0)
    col = Column(Integer, default=0)
    depth = Column(Integer, default=0)
    status = Column(String, default="in_stock")  # in_stock, reserved, delivered, expired, wasted
    ripeness_score = Column(Float, default=0.0)   # 0=unripe, 1=perfect, 2=overripe
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    item = relationship("PerishableItem", back_populates="batches")
    container = relationship("StorageContainer", back_populates="batches")
    placements = relationship("StoragePlacement", back_populates="batch")


class StoragePlacement(Base):
    __tablename__ = "storage_placements"
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("inventory_batches.id"), nullable=False)
    container_id = Column(Integer, ForeignKey("storage_containers.id"), nullable=False)
    position_index = Column(Integer, nullable=False)
    row = Column(Integer, nullable=False)
    col = Column(Integer, nullable=False)
    depth = Column(Integer, nullable=False)
    conflict_flag = Column(Boolean, default=False)
    conflict_reason = Column(Text, nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    is_current = Column(Boolean, default=True)

    batch = relationship("InventoryBatch", back_populates="placements")
    container = relationship("StorageContainer", back_populates="placements")


class DeliveryOrder(Base):
    __tablename__ = "delivery_orders"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True, nullable=False)
    client_name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    delivery_date = Column(Date, nullable=False)
    status = Column(String, default="pending")  # pending, confirmed, fulfilled, cancelled
    priority = Column(String, default="normal")  # low, normal, high, urgent
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order_items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("delivery_orders.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("perishable_items.id"), nullable=False)
    quantity_kg = Column(Float, nullable=False)
    fulfilled_kg = Column(Float, default=0.0)
    unit_price = Column(Float, default=0.0)

    order = relationship("DeliveryOrder", back_populates="order_items")
    item = relationship("PerishableItem", back_populates="order_items")


class ProcurementRecommendation(Base):
    __tablename__ = "procurement_recommendations"
    id = Column(Integer, primary_key=True, index=True)
    rec_id = Column(String, unique=True, index=True, nullable=False)
    item_id = Column(Integer, ForeignKey("perishable_items.id"), nullable=False)
    recommended_qty_kg = Column(Float, nullable=False)
    order_by_date = Column(Date, nullable=False)
    expected_delivery_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    ai_generated = Column(Boolean, default=True)
    status = Column(String, default="pending")  # pending, approved, rejected, ordered
    priority = Column(String, default="normal")
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    item = relationship("PerishableItem", back_populates="procurement_recs")


class AIInsight(Base):
    __tablename__ = "ai_insights"
    id = Column(Integer, primary_key=True, index=True)
    insight_id = Column(String, unique=True, index=True, nullable=False)
    insight_type = Column(String, nullable=False)  # expiry_alert, stock_low, placement_conflict, demand_gap
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String, default="info")  # info, warning, critical
    entity_type = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    action = Column(String, nullable=False)  # CREATE, UPDATE, DELETE, OPTIMIZE, AI_RECOMMEND
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    performed_by = Column(String, default="system")
    timestamp = Column(DateTime, default=datetime.utcnow)


def create_tables():
    Base.metadata.create_all(bind=engine)
