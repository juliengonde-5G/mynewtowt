import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Date, func
)
from sqlalchemy.orm import relationship
from app.database import Base

# Token validity: 90 days from creation
TOKEN_VALIDITY_DAYS = 90


def generate_token():
    return uuid.uuid4().hex[:24]


def default_token_expiry():
    return datetime.now(timezone.utc) + timedelta(days=TOKEN_VALIDITY_DAYS)


class PackingList(Base):
    __tablename__ = "packing_lists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(32), unique=True, nullable=False, default=generate_token, index=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True, default=default_token_expiry)

    # Status: draft, submitted, locked
    status = Column(String(20), default="draft")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_by = Column(String(100), nullable=True)

    order = relationship("Order", backref="packing_list_ref")
    batches = relationship("PackingListBatch", back_populates="packing_list", cascade="all, delete-orphan",
                           order_by="PackingListBatch.id")

    @property
    def is_locked(self):
        return self.status == "locked"

    @property
    def batch_count(self):
        return len(self.batches) if self.batches else 0

    @property
    def completion_pct(self):
        if not self.batches:
            return 0
        required_fields = [
            'customer_name',
            'shipper_name', 'shipper_address', 'shipper_postal', 'shipper_city', 'shipper_country',
            'notify_name', 'notify_address', 'notify_postal', 'notify_city', 'notify_country',
            'consignee_name', 'consignee_address', 'consignee_postal', 'consignee_city', 'consignee_country',
            'type_of_goods', 'pallet_quantity',
            'length_cm', 'width_cm', 'height_cm', 'weight_kg',
        ]
        total = len(self.batches) * len(required_fields)
        filled = 0
        for b in self.batches:
            for f in required_fields:
                val = getattr(b, f, None)
                if val is not None and str(val).strip():
                    filled += 1
        return round((filled / total) * 100) if total > 0 else 0


class PackingListBatch(Base):
    __tablename__ = "packing_list_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    packing_list_id = Column(Integer, ForeignKey("packing_lists.id", ondelete="CASCADE"), nullable=False)
    batch_number = Column(Integer, default=1)

    # === TOWT fields (pre-filled) ===
    voyage_id = Column(String(50), nullable=True)       # leg_code
    vessel = Column(String(100), nullable=True)
    loading_date = Column(Date, nullable=True)
    pol_code = Column(String(10), nullable=True)
    pod_code = Column(String(10), nullable=True)
    pol_name = Column(String(200), nullable=True)
    pod_name = Column(String(200), nullable=True)
    booking_confirmation = Column(String(50), nullable=True)  # order reference
    freight_rate = Column(Float, nullable=True)
    bill_of_lading_id = Column(String(50), nullable=True)
    wh_references_sku = Column(String(200), nullable=True)
    additional_references = Column(String(200), nullable=True)
    ams_hbl_id = Column(String(50), nullable=True)
    isf_date = Column(Date, nullable=True)
    stackable = Column(String(10), nullable=True)
    hold = Column(String(50), nullable=True)
    un_number = Column(String(50), nullable=True)

    # === Client fields (yellow - to be filled by client) ===
    customer_name = Column(String(200), nullable=True)
    freight_forwarder = Column(String(200), nullable=True)
    code_transitaire = Column(String(100), nullable=True)

    # Shipper (structured)
    shipper_name = Column(String(200), nullable=True)
    shipper_address = Column(Text, nullable=True)
    shipper_postal = Column(String(20), nullable=True)
    shipper_city = Column(String(100), nullable=True)
    shipper_country = Column(String(100), nullable=True)

    po_number = Column(String(100), nullable=True)
    customer_batch_id = Column(String(100), nullable=True)

    # Notify (structured)
    notify_name = Column(String(200), nullable=True)
    notify_address = Column(Text, nullable=True)
    notify_postal = Column(String(20), nullable=True)
    notify_city = Column(String(100), nullable=True)
    notify_country = Column(String(100), nullable=True)

    # Consignee (structured)
    consignee_name = Column(String(200), nullable=True)
    consignee_address = Column(Text, nullable=True)
    consignee_postal = Column(String(20), nullable=True)
    consignee_city = Column(String(100), nullable=True)
    consignee_country = Column(String(100), nullable=True)

    pallet_type = Column(String(50), nullable=True)      # EPAL, USPAL, etc.
    type_of_goods = Column(String(200), nullable=True)
    description_of_goods = Column(Text, nullable=True)    # Full description for BL
    bio_products = Column(String(10), nullable=True)      # Yes/No
    cases_quantity = Column(Integer, nullable=True)
    units_per_case = Column(Integer, nullable=True)
    imo_product_class = Column(String(100), nullable=True)
    pallet_quantity = Column(Integer, nullable=True)       # palettes per batch
    length_cm = Column(Float, nullable=True)
    width_cm = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    cargo_value_usd = Column(Float, nullable=True)

    # === Computed by system ===
    surface_m2 = Column(Float, nullable=True)
    volume_m3 = Column(Float, nullable=True)
    density = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    packing_list = relationship("PackingList", back_populates="batches")

    def compute_dimensions(self):
        if self.length_cm and self.width_cm:
            self.surface_m2 = round(self.length_cm * self.width_cm / 10000, 4)
        if self.length_cm and self.width_cm and self.height_cm:
            self.volume_m3 = round(self.length_cm * self.width_cm * self.height_cm / 1000000, 4)
        if self.weight_kg and self.surface_m2 and self.surface_m2 > 0:
            self.density = round((self.weight_kg / 1000) / self.surface_m2, 3)


class PackingListAudit(Base):
    __tablename__ = "packing_list_audit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    packing_list_id = Column(Integer, ForeignKey("packing_lists.id", ondelete="CASCADE"), nullable=False)
    batch_id = Column(Integer, nullable=True)  # null = packing list level change
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_by = Column(String(200), nullable=False)  # user name or "Client"
    changed_at = Column(DateTime(timezone=True), server_default=func.now())

    packing_list = relationship("PackingList", backref="audit_logs")


class PackingListDocument(Base):
    """Document uploaded by client on the packing list portal."""
    __tablename__ = "packing_list_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    packing_list_id = Column(Integer, ForeignKey("packing_lists.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(300), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    uploaded_by = Column(String(100), nullable=False, default="Client")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    packing_list = relationship("PackingList", backref="documents")
