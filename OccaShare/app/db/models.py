from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, Date, Time, DECIMAL, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="customer") # 'admin', 'caterer', 'customer'
    first_name = Column(String, nullable=True)
    middle_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    dob = Column(Date, nullable=True)
    phone_number = Column(String, nullable=True)
    address = Column(Text, nullable=True)  # Legacy single-field address (kept for backward compat)
    # Structured Address Fields (PSGC-based)
    province = Column(String, nullable=True)
    city_municipality = Column(String, nullable=True)
    barangay = Column(String, nullable=True)
    street_address = Column(Text, nullable=True)  # House/Unit No., Street, Landmark
    profile_image_url = Column(String, nullable=True)
    status = Column(String, default="active")
    status_reason = Column(Text, nullable=True)
    investigation_notes = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # New Profile Info
    gender = Column(String, nullable=True)
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_relation = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)
    notification_preferences = Column(JSONB, default={
        "email_promos": True,
        "email_bookings": True,
        "sms_bookings": False
    })
    
    # Social Login Fields
    facebook_id = Column(String, unique=True, nullable=True)
    google_id = Column(String, unique=True, nullable=True)
    instagram_id = Column(String, unique=True, nullable=True)
    auth_provider = Column(String, default='email') # 'email', 'facebook', 'google', 'instagram'
    
    # Email Verification
    is_email_verified = Column(Boolean, default=False)
    verification_code = Column(String, nullable=True) # OTP
    otp_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Password Reset Fields
    reset_token = Column(String, unique=True, nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_archived = Column(Boolean, default=False)
    is_kyc_complete = Column(Boolean, default=False)
    kyc_attempts = Column(Integer, default=0)
    must_change_password = Column(Boolean, default=False)

    caterer_profile = relationship("CatererProfile", back_populates="user", uselist=False)
    bookings = relationship("Booking", back_populates="user")
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    inquiries = relationship("Inquiry", back_populates="user", cascade="all, delete-orphan")
    identity_verifications = relationship("IdentityVerification", foreign_keys="[IdentityVerification.user_id]", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    verification_attempts = relationship("VerificationAttempt", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    platform_feedback = relationship("PlatformFeedback", back_populates="user", cascade="all, delete-orphan")
    verification_sessions = relationship("VerificationSession", back_populates="user", cascade="all, delete-orphan")
    
    sent_messages = relationship("ChatMessage", foreign_keys="ChatMessage.sender_id", back_populates="sender")
    received_messages = relationship("ChatMessage", foreign_keys="ChatMessage.receiver_id", back_populates="receiver")

    @property
    def identity_verification(self):
        if self.identity_verifications:
            return sorted(self.identity_verifications, key=lambda x: x.id, reverse=True)[0]
        return None

class CatererProfile(Base):
    __tablename__ = "caterer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    business_name = Column(String, unique=True)
    slug = Column(String, unique=True, nullable=True)
    business_type = Column(String, nullable=True)
    years_of_operation = Column(Integer, default=0)
    description = Column(Text)
    logo_url = Column(String)
    cover_image_url = Column(String)
    contact_phone = Column(String)
    contact_address = Column(Text)
    city = Column(String)
    coverage_area = Column(Text, nullable=True)
    out_of_coverage_action = Column(String, default="reject")
    cuisine_types = Column(ARRAY(String)) # Requires PostgreSQL
    event_types = Column(ARRAY(String)) # Supported events like Wedding, Birthday, etc.
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    profile_views = Column(Integer, default=0)  # Total profile page visits
    payout_method = Column(String, nullable=True) # General field (legacy/fallback)
    payout_account_name = Column(String, nullable=True) # General field (legacy/fallback)
    payout_account_number = Column(String, nullable=True) # General field (legacy/fallback)

    # Expanded Payout Fields
    gcash_number = Column(String, nullable=True)
    gcash_qr_url = Column(String, nullable=True)
    maya_number = Column(String, nullable=True)
    maya_qr_url = Column(String, nullable=True)
    bank_name = Column(String, nullable=True)
    bank_account_name = Column(String, nullable=True)
    bank_account_number = Column(String, nullable=True)
    bank_qr_url = Column(String, nullable=True)
    card_bank = Column(String, nullable=True)
    card_holder_name = Column(String, nullable=True)
    card_number = Column(String, nullable=True)
    cash_instructions = Column(Text, nullable=True)
    verification_status = Column(String, default='Pending') # Pending, Verified, Rejected
    account_status = Column(String, default='Active') # Active, Suspended, Deactivated
    status = Column(String, default='Draft') # Draft, Registered, Identity Verified, Profile Incomplete, Ready For Review, Published
    team_size = Column(Integer, default=1, nullable=True)
    is_verified = Column(Boolean, default=False)
    
    # NEW: Jurisdictional Location (PSGC)
    province_code = Column(String, nullable=True)
    city_code = Column(String, nullable=True)
    brgy_code = Column(String, nullable=True)
    address_details = Column(Text, nullable=True)
    
    # NEW: Refined Registration Fields
    min_pax = Column(Integer, default=0)
    starting_price = Column(Float, default=0.0)
    sample_menu_url = Column(String, nullable=True)
    permit_url = Column(String, nullable=True)
    dti_url = Column(String, nullable=True)
    bir_url = Column(String, nullable=True)
    mayors_permit_url = Column(String, nullable=True)
    permit_expiry_date = Column(Date, nullable=True)
    permit_status = Column(String, default='Pending') # Pending, Verified, Rejected
    gov_id_url = Column(String, nullable=True)
    registration_source = Column(String, default="Website")
    admin_remarks = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # NEW: Brand Customization Fields
    primary_color = Column(String, default="#FF7B54") # OccaServe Orange
    secondary_color = Column(String, default="#2D4059") # Dark Blue/Slate
    accent_color = Column(String, default="#FFB17A") # Soft Orange
    highlight_color = Column(String, default="#FFE5D9") # Light Tint
    font_family = Column(String, default="Inter")
    border_radius = Column(Integer, default=12) # in px
    sidebar_mode = Column(String, default="full") # 'full' (text + icon), 'icons' (icon only)
    show_platform_logo = Column(Boolean, default=True)
    
    # Calendar Capacity Settings
    max_bookings_per_day = Column(Integer, default=1) # How many bookings caterer can handle per day
    auto_block_enabled = Column(Boolean, default=True) # Auto-block dates when capacity reached
    
    # NEW: Advanced Branding
    glass_mode = Column(Boolean, default=False)
    sidebar_color = Column(String, default="#000000")
    header_color = Column(String, default="#FFFFFF")
    dashboard_texture = Column(String, default="none") # 'none', 'dots', 'grid', 'waves', etc.
    sidebar_decoration = Column(String, default="none") # 'none', 'food-doodle', 'steam', 'floating-chef'
    header_decoration = Column(String, default="none") # 'none', 'utensils', 'sparkles'
    
    # NEW: Policy Fields
    terms_and_conditions = Column(Text, nullable=True) # Used for formal Event Service Contracts
    general_terms = Column(Text, nullable=True) # Used for fast-track Food & Equipment orders
    rental_policies = Column(Text, nullable=True) # Used for Equipment Rentals
    cancellation_policy = Column(Text, nullable=True) # Universal cancellation rules
    booking_lead_time = Column(Integer, default=7) # Days in advance
    equipment_turnover_hours = Column(Integer, default=24) # Turnaround time for rentals
    min_pax = Column(Integer, default=20) # Minimum pax for services
    accepted_payment_terms = Column(JSONB, default=[100]) # Flexible array, e.g. [30, 50, 100]
    default_labor_cost = Column(Float, default=0.0)
    default_utility_cost = Column(Float, default=0.0)
    default_transport_cost = Column(Float, default=0.0)
    default_reservation_type = Column(String, default='fixed') # 'fixed' or 'percentage'
    default_reservation_value = Column(Float, default=0.0)
    
    # NEW: Delivery Settings
    delivery_fee_type = Column(String, default="area") # "area", "manual", "disabled"
    base_delivery_fee = Column(Float, default=150.0)
    
    # NEW: Universal Scheduling Rules
    scheduling_rules = Column(JSONB, default={
        "business_hours": {"open_time": "08:00", "close_time": "20:00"},
        "food_rules": {"delivery_available": True, "pickup_available": True, "delivery_start": "09:00", "delivery_end": "19:00", "lead_time_hours": 24, "allow_same_day": False},
        "equipment_rules": {"pickup_start": "08:00", "pickup_end": "18:00", "return_start": "08:00", "return_end": "18:00", "min_rental_hours": 24, "max_rental_hours": 72},
        "service_rules": {"min_duration_hours": 3, "max_duration_hours": 8, "earliest_start": "08:00", "latest_end": "22:00"},
        "package_rules": {"min_event_duration": 4, "max_event_duration": 6, "setup_time_hours": 2, "cleanup_time_hours": 1}
    })
    
    # NEW: Notification Preferences (JSONB for flexibility)
    notification_preferences = Column(JSONB, default={
        "email_new_booking": True,
        "email_payment_confirmed": True,
        "email_weekly_summary": False,
        "push_messages": True,
        "email_review_received": True
    })
    
    # NEW: Account Deactivation
    deactivation_reason = Column(Text, nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    
    # NEW: Caterer Verification Module
    verification_status = Column(String, default="NOT_SUBMITTED") # NOT_SUBMITTED, PENDING_REVIEW, RESUBMISSION_REQUIRED, VERIFIED, REJECTED, EXPIRED
    account_status = Column(String, default="PENDING") # PENDING, ACTIVE, RESTRICTED, SUSPENDED
    
    # NEW: Billing and Commission
    outstanding_balance = Column(Float, default=0.0)
    commission_rate = Column(Float, default=0.05) # 5% default commission
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="caterer_profile")
    packages = relationship("CateringPackage", back_populates="caterer")
    gallery_items = relationship("CatererGallery", back_populates="caterer")
    bookings = relationship("Booking", back_populates="caterer")
    reviews = relationship("Review", back_populates="caterer")
    promotions = relationship("Promotion", back_populates="caterer")
    availability = relationship("Availability", back_populates="caterer")
    inquiries = relationship("Inquiry", back_populates="caterer")
    payouts = relationship("Payout", back_populates="caterer")
    menu_items = relationship("MenuItem", back_populates="caterer", cascade="all, delete-orphan")
    social_posts = relationship("SocialPost", back_populates="caterer", cascade="all, delete-orphan")
    equipment_items = relationship("Equipment", back_populates="caterer", cascade="all, delete-orphan")
    service_items = relationship("Service", back_populates="caterer", cascade="all, delete-orphan")
    business_expenses = relationship("BusinessExpense", back_populates="caterer", cascade="all, delete-orphan")
    portfolios = relationship("Portfolio", back_populates="caterer", cascade="all, delete-orphan")
    delivery_zones = relationship("DeliveryZone", back_populates="caterer", cascade="all, delete-orphan")
    verifications = relationship("CatererVerification", back_populates="caterer", cascade="all, delete-orphan")

class DeliveryZone(Base):
    __tablename__ = "delivery_zones"
    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id", ondelete="CASCADE"))
    province = Column(String, nullable=False)
    city_municipality = Column(String, nullable=False)
    barangay = Column(String, nullable=True) # Optional for more granular pricing
    fee = Column(Float, default=0.0)
    is_manual_quote = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    caterer = relationship("CatererProfile", back_populates="delivery_zones")

class PackageMenu(Base):
    __tablename__ = "package_menus"
    package_id = Column(Integer, ForeignKey("catering_packages.id"), primary_key=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), primary_key=True)

class PackageEquipment(Base):
    __tablename__ = "package_equipment"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="CASCADE"))
    quantity = Column(Integer, default=1)
    equipment = relationship("Equipment", backref="package_links")

class PackageService(Base):
    __tablename__ = "package_services"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"))
    quantity = Column(Integer, default=1)
    service = relationship("Service", backref="package_links")

class PackageMenuAddon(Base):
    __tablename__ = "package_menu_addons"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id", ondelete="CASCADE"))
    price = Column(Float, default=0.0)
    selection_type = Column(String, default="single") # 'single' or 'multiple'
    min_quantity = Column(Integer, default=1)
    max_quantity = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, default=True)

class PackageServiceAddon(Base):
    __tablename__ = "package_service_addons"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"))
    price = Column(Float, default=0.0)
    selection_type = Column(String, default="single") # 'single' or 'manpower'
    min_quantity = Column(Integer, default=1)
    max_quantity = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, default=True)

class PackageEquipmentAddon(Base):
    __tablename__ = "package_equipment_addons"
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("catering_packages.id", ondelete="CASCADE"))
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="CASCADE"))
    price = Column(Float, default=0.0)
    min_quantity = Column(Integer, default=1)
    max_quantity = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, default=True)

class CateringPackage(Base):
    __tablename__ = "catering_packages"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    name = Column(String, index=True)
    description = Column(Text)
    price = Column(Float)
    cost_price = Column(Float, default=0.0)
    cost_breakdown = Column(JSONB, nullable=True)
    price_unit = Column(String, default='per_guest')
    min_guests = Column(Integer, default=10)
    max_guests = Column(Integer, nullable=True)
    image_url = Column(String)
    gallery_images = Column(JSONB, nullable=True) # up to 4 additional images
    service_type = Column(String, default="General") # Wedding, Birthday, Corporate, etc.
    
    # NEW: Rich Pricing & Details
    pricing_mode = Column(String, default='per_pax') # 'per_pax' or 'fixed'
    price_per_head = Column(Float, nullable=True) # Selling Price (Customer Visible)
    internal_cost_per_pax = Column(Float, default=0.0) # Internal Break-even (Hidden)
    base_pax = Column(Integer, default=50) # The pax count used for costing
    
    # Internal Expense Breakdown (Overhead)
    labor_cost = Column(Float, default=0.0)
    utility_cost = Column(Float, default=0.0)
    equipment_cost = Column(Float, default=0.0)
    transportation_cost = Column(Float, default=0.0)
    miscellaneous_cost = Column(Float, default=0.0)
    ingredient_total_cost = Column(Float, default=0.0)
    
    min_contract_amount = Column(Float, nullable=True)
    additional_guest_price = Column(Float, nullable=True)
    service_duration = Column(Integer, default=4) # In hours
    overtime_fee = Column(Float, default=0.0)
    location_coverage = Column(String, nullable=True) # City / Area
    reservation_fee_type = Column(String, default='fixed') # 'fixed' or 'percentage'
    reservation_fee_value = Column(Float, default=0.0)
    booking_lead_time = Column(Integer, default=7) # In days
    
    # Structured Data
    inclusions = Column(JSONB, nullable=True) # Checklist fields
    policies = Column(JSONB, nullable=True) # Cancellation, Payment terms, etc.
    selection_rules = Column(JSONB, nullable=True) # e.g. {"Beef": 1, "Pork": 1}
    
    is_active = Column(Boolean, default=True)
    status = Column(String, default="active") # active, inactive, draft
    is_featured = Column(Boolean, default=False)
    
    # ROI & Markup Management
    markup_type = Column(String, default='percentage') # 'percentage', 'fixed'
    markup_value = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    caterer = relationship("CatererProfile", back_populates="packages")
    menu_items = relationship("MenuItem", secondary="package_menus", back_populates="packages")
    
    equipment_links = relationship("PackageEquipment", cascade="all, delete-orphan", backref="package")
    service_links = relationship("PackageService", cascade="all, delete-orphan", backref="package")
    
    menu_addons = relationship("PackageMenuAddon", cascade="all, delete-orphan", backref="package")
    service_addons = relationship("PackageServiceAddon", cascade="all, delete-orphan", backref="package")
    equipment_addons = relationship("PackageEquipmentAddon", cascade="all, delete-orphan", backref="package")

    bookings = relationship("Booking", back_populates="package")

class MenuItem(Base):
    __tablename__ = "menu_items" # Phase 1 'menus'

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    name = Column(String)
    description = Column(Text, nullable=True)
    category = Column(String) 
    image_url = Column(String, nullable=True)
    
    # Phase 1 Fields
    cost_price = Column(Float, default=0.0) # estimated_cost
    price = Column(Float, nullable=True, default=0.0) # selling_price - nullable for package_only
    pricing_unit = Column(String, default="per_pax") # unit_type
    min_order_qty = Column(Integer, default=1)
    status = Column(String, default="available") # available, unavailable
    
    # New V2.0 Menu & Package Management Fields
    usage_type = Column(String, default="both") # package_only, order_only, both
    available_for_package = Column(Boolean, default=True)
    available_for_order = Column(Boolean, default=True)
    pricing_type = Column(String, default="fixed") # fixed, size_based, weight_based, packed_meal
    
    # Legacy fields
    cost_breakdown = Column(JSONB, nullable=True)
    dietary_tags = Column(ARRAY(String), nullable=True)
    allergen_info = Column(ARRAY(String), nullable=True)
    serving_size = Column(String, nullable=True) 
    serving_style = Column(String, nullable=True) # V3 Single Serving Style
    is_addon = Column(Boolean, default=False)
    addon_price = Column(Float, default=0.0)
    max_stock_quantity = Column(Integer, nullable=True) 
    is_hidden = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_combo = Column(Boolean, default=False)
    max_choices = Column(Integer, default=0)
    combo_options = Column(JSONB, nullable=True)
    
    # Granular Ratings Caching
    average_rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    
    # Premium Swap Upgrade
    upgrade_fee = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    caterer = relationship("CatererProfile", back_populates="menu_items")
    packages = relationship("CateringPackage", secondary="package_menus", back_populates="menu_items")
    
    size_prices = relationship("MenuSizePricing", back_populates="menu_item", cascade="all, delete-orphan")
    weight_prices = relationship("MenuWeightPricing", back_populates="menu_item", cascade="all, delete-orphan")
    variants = relationship("MenuVariant", back_populates="menu_item", cascade="all, delete-orphan", order_by="MenuVariant.display_order")

class MenuVariant(Base):
    __tablename__ = "menu_variants"
    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id", ondelete="CASCADE"))
    variant_name = Column(String)
    measurement = Column(String, nullable=True)
    price = Column(Float, default=0.0)
    serving_capacity = Column(String, nullable=True)
    status = Column(String, default="available") # available, unavailable, hidden
    display_order = Column(Integer, default=0)
    
    menu_item = relationship("MenuItem", back_populates="variants")


class MenuSizePricing(Base):
    __tablename__ = "menu_size_pricing"
    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id", ondelete="CASCADE"))
    size_name = Column(String)
    capacity = Column(String, nullable=True) # e.g. "10-15 Pax"
    price = Column(Float, default=0.0)
    
    menu_item = relationship("MenuItem", back_populates="size_prices")

class MenuWeightPricing(Base):
    __tablename__ = "menu_weight_pricing"
    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id", ondelete="CASCADE"))
    weight_label = Column(String) # e.g. "1kg"
    price = Column(Float, default=0.0)

    menu_item = relationship("MenuItem", back_populates="weight_prices")

class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    name = Column(String)
    equipment_type = Column(String, default="Equipment")
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    
    available_qty = Column(Integer, default=1)
    cost_value = Column(Float, default=0.0)
    rental_price = Column(Float, default=0.0)
    unit_type = Column(String, default="piece")
    status = Column(String, default="available")
    is_hidden = Column(Boolean, default=False)
    
    # Strict Rental Fields
    security_deposit_pct = Column(Float, default=20.0) # Percentage of cost_value
    maintenance_buffer_hours = Column(Integer, default=12) # Gap required before next rental
    requires_kyc = Column(Boolean, default=False) # Forced ID verification for high-value items
    
    is_archived = Column(Boolean, default=False)
    usage_type = Column(String, default="both") # 'package_only', 'order_only', 'both'
    is_addon = Column(Boolean, default=False)
    addon_price = Column(Float, default=0.0)
    
    # Granular Ratings Caching
    average_rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    
    # Metadata for Complex Structured Fields (Inclusions, Specifications, Rules, Extra Fees)
    details_json = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    caterer = relationship("CatererProfile", back_populates="equipment_items")

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    name = Column(String)
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    
    base_duration_hours = Column(Integer, default=3)
    
    cost = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    unit_type = Column(String, default="per_event")
    max_available = Column(Integer, default=1)
    status = Column(String, default="available")
    is_hidden = Column(Boolean, default=False)
    
    is_archived = Column(Boolean, default=False)
    usage_type = Column(String, default="both") # 'package_only', 'order_only', 'both'
    is_addon = Column(Boolean, default=False)
    addon_price = Column(Float, default=0.0)
    
    # Smart Service Capacity Management Fields
    capacity_type = Column(String, default="unit_based") # 'unit_based' or 'staff_based'
    staff_to_pax_ratio = Column(Integer, default=0) # e.g. 1 staff per 25 pax (0 means N/A)
    min_staff_required = Column(Integer, default=1) # Baseline staff requirement for small events
    allow_freelancers = Column(Boolean, default=False) # If true, allows overbooking beyond max_available
    buffer_time_hours = Column(Integer, default=0) # Extra hours needed before/after for setup/travel
    
    # New Service Booking Specific Fields
    requires_agreement = Column(Boolean, default=False) # Contract-Track vs Fast-Track
    downpayment_percentage = Column(Integer, default=50) # Specific to services, overrides caterer default
    minimum_hours = Column(Integer, default=1) # Duration validation
    
    # Granular Ratings Caching
    average_rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    
    # Metadata for Complex Structured Fields (Inclusions, Requirements, Area, Rules)
    details_json = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    caterer = relationship("CatererProfile", back_populates="service_items")


class CatererGallery(Base):
    __tablename__ = "caterer_gallery"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    media_url = Column(String)
    media_type = Column(String, default="image")
    caption = Column(String, nullable=True)
    display_order = Column(Integer, default=0)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    caterer = relationship("CatererProfile", back_populates="gallery_items")

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    customer_name = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    customer_contact = Column(String, nullable=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    package_id = Column(Integer, ForeignKey("catering_packages.id"), nullable=True)
    event_name = Column(String, nullable=True) # e.g. "Garcia Family Wedding"
    event_type = Column(String, nullable=True) # Wedding, Birthday, Corporate, Private Party
    event_date = Column(Date)
    event_time = Column(Time, nullable=True)
    event_end_time = Column(Time, nullable=True)
    venue_address = Column(Text, nullable=True) # Legacy, keeping for backwards compatibility
    
    # --- SECTION A: Event Details ---
    event_address = Column(Text, nullable=True) # The actual venue/location of the event
    
    # --- SECTION B: User Verification Details ---
    id_address = Column(Text, nullable=True) # Residential address from uploaded ID
    current_address = Column(Text, nullable=True) # Editable current address
    verification_status = Column(String, default="pending") # pending, verified, rejected

    guest_count = Column(Integer)
    total_amount = Column(Float)
    actual_cost = Column(Float, default=0.0)
    actual_cost_breakdown = Column(JSONB, nullable=True)
    total_price = Column(Float, nullable=True) # Alias to match user request structure
    reservation_fee = Column(DECIMAL, nullable=True)
    travel_fee = Column(Float, default=0.0)
    travel_fee_status = Column(String, default="confirmed") # "confirmed", "tbd", "pending_quote"
    status = Column(String, default="pending")
    payment_status = Column(String, default="pending") # unpaid, partially_paid, fully_paid, overdue
    payment_method = Column(String, nullable=True) # GCash, Credit Card, etc.
    amount_paid = Column(Float, default=0.0)
    preparation_status = Column(String, default="not_started") # not_started, scheduled, in_preparation, ready, completed
    preparation_date = Column(Date, nullable=True)
    customer_archived = Column(Boolean, default=False)
    payment_reference = Column(String, nullable=True)
    payment_proof_url = Column(String, nullable=True)
    balance_proof_url = Column(String, nullable=True)
    dispatch_proof_url = Column(String, nullable=True)
    paymongo_link_id = Column(String, nullable=True)
    paymongo_link_url = Column(String, nullable=True)
    payout_id = Column(Integer, ForeignKey("payouts.id"), nullable=True)
    ocr_verification = relationship("OCRVerification", back_populates="booking", uselist=False, cascade="all, delete-orphan")
    contract = relationship("BookingContract", back_populates="booking", uselist=False, cascade="all, delete-orphan")

    payment_verification_data = Column(JSONB, nullable=True)
    proof_image_hash = Column(String, nullable=True)
    ocr_verified = Column(Boolean, default=False)
    liveness_verified = Column(Boolean, default=False)
    special_requests = Column(Text)
    caterer_notes = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False)
    booking_source = Column(String, default="OccaServe") # OccaServe, Facebook, Walk-in, Other
    
    # Strict Equipment Rental Lifecycle Fields
    security_deposit_amount = Column(Float, default=0.0)
    security_deposit_status = Column(String, default="unpaid") # unpaid, held, partially_refunded, fully_refunded, forfeited
    damage_deduction_amount = Column(Float, default=0.0)
    missing_items_count = Column(Integer, default=0)
    release_photo_url = Column(String, nullable=True) # Proof of condition on handover
    return_photo_url = Column(String, nullable=True) # Proof of condition on return
    damage_proof_url = Column(String, nullable=True) # Mandatory if deduction > 0
    rental_disputed = Column(Boolean, default=False) # Flagged if customer challenges deductions
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    commission_calculated = Column(Boolean, default=False)
    
    expires_at = Column(DateTime(timezone=True), nullable=True)
    balance_due_date = Column(DateTime(timezone=True), nullable=True) 
    payment_plan = Column(String, default='downpayment') # 'downpayment' or 'full'
    event_location = Column(Text, nullable=True)
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)
    terms_accepted_ip = Column(String, nullable=True)
    is_custom_event = Column(Boolean, default=False)
    transaction_type = Column(String, default="contract_track") # 'fast_track' or 'contract_track'
    document_type = Column(String, nullable=True) # 'invoice', 'service_agreement', 'booking_agreement', 'rental_agreement'
    custom_requirements = Column(JSONB, nullable=True) # E.g. {"theme": "Rustic", "budget": 50000}
    user = relationship("User", back_populates="bookings")
    caterer = relationship("CatererProfile", back_populates="bookings")
    package = relationship("CateringPackage", back_populates="bookings")
    tasks = relationship("BookingTask", back_populates="booking", cascade="all, delete-orphan")
    review = relationship("Review", back_populates="booking", uselist=False, cascade="all, delete-orphan")
    history = relationship("BookingHistory", back_populates="booking", cascade="all, delete-orphan")
    quotation = relationship("Quotation", back_populates="booking", uselist=False, cascade="all, delete-orphan")
    verification_attempts = relationship("VerificationAttempt", back_populates="booking", cascade="all, delete-orphan")
    fraud_flags = relationship("FraudFlag", back_populates="booking", cascade="all, delete-orphan")
    selected_items = relationship("BookingMenuItem", back_populates="booking", cascade="all, delete-orphan")
    payout = relationship("Payout", back_populates="bookings")
    expenses = relationship("BookingExpense", back_populates="booking", cascade="all, delete-orphan")
    messages = relationship("BookingMessage", back_populates="booking", cascade="all, delete-orphan")
    payment_records = relationship("BookingPaymentRecord", back_populates="booking", cascade="all, delete-orphan")

class BookingPaymentRecord(Base):
    __tablename__ = "booking_payment_records"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime(timezone=True), server_default=func.now())
    payment_method = Column(String, nullable=True)
    payment_type = Column(String, nullable=True) # Deposit, Installment, Full
    reference_notes = Column(Text, nullable=True)
    recorded_by = Column(String, nullable=True) # "Caterer" or "System"

    booking = relationship("Booking", back_populates="payment_records")

class BookingMessage(Base):
    __tablename__ = "booking_messages"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text, nullable=True)
    attachment_url = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="messages")
    sender = relationship("User")

class BookingMenuItem(Base):
    __tablename__ = "booking_menu_items"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    is_add_on = Column(Boolean, default=False)
    custom_name = Column(String, nullable=True)
    price = Column(Float) # Price at the time of booking
    quantity = Column(Integer, default=1)
    choices = Column(JSONB, nullable=True) # Array of selected item names/IDs for combos

    booking = relationship("Booking", back_populates="selected_items")
    menu_item = relationship("MenuItem")
    equipment = relationship("Equipment")
    service = relationship("Service")

class BookingHistory(Base):
    __tablename__ = "booking_history"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    status = Column(String) # The status being transitioned TO
    entry_type = Column(String, default="system_change") # "system_change" or "communication"
    communication_channel = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="history")

class BookingContract(Base):
    __tablename__ = "booking_contracts"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True)
    contract_text = Column(Text) # Generated contract content (HTML or Markdown)
    customer_signature = Column(String, nullable=True) # Data URL of signature or name
    customer_signed_at = Column(DateTime(timezone=True), nullable=True)
    caterer_signature = Column(String, nullable=True)
    caterer_signed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="pending") # pending, customer_signed, fully_signed, expired
    expires_at = Column(DateTime(timezone=True), nullable=True) # NEW: Contract Signing Deadline
    contract_history = Column(JSONB, nullable=True) # Array of old contract versions
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="contract")

class OCRVerification(Base):
    __tablename__ = "ocr_verification"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True) # Can be linked to booking or user
    user_id = Column(Integer, ForeignKey("users.id"))
    document_url = Column(String)
    selfie_url = Column(String)
    status = Column(String, default="pending") # pending, verified, failed
    ocr_data = Column(JSONB)
    
    # Extracted Fields
    full_name = Column(String, nullable=True)
    birthdate = Column(Date, nullable=True)
    id_address_extracted = Column(Text, nullable=True)
    
    match_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="ocr_verification")
    user = relationship("User")

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    rating = Column(Integer) # Overall Rating
    food_quality_rating = Column(Integer, nullable=True)
    service_quality_rating = Column(Integer, nullable=True)
    timeliness_rating = Column(Integer, nullable=True)
    
    comment = Column(Text)
    recommend = Column(Boolean, default=False)
    was_punctual = Column(Boolean, default=False)
    is_highlighted = Column(Boolean, default=False)
    caterer_reply = Column(Text, nullable=True) # Response from the caterer
    is_helpful = Column(Boolean, default=False) # Internal flag if caterer found it helpful
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="review")
    user = relationship("User", back_populates="reviews")
    caterer = relationship("CatererProfile", back_populates="reviews")
    item_ratings = relationship("ItemRating", back_populates="review", cascade="all, delete-orphan")

class ItemRating(Base):
    __tablename__ = "item_ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id", ondelete="CASCADE"))
    item_type = Column(String) # 'menu', 'service', 'equipment'
    item_id = Column(Integer) # The ID of the item
    rating = Column(Integer)
    
    review = relationship("Review", back_populates="item_ratings")

class PlatformFeedback(Base):
    __tablename__ = "platform_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    rating = Column(Integer)  # 1–5 stars
    comment = Column(Text)
    attachment_base64 = Column(Text, nullable=True) # Compressed image string
    role = Column(String, nullable=True)  # 'customer' or 'caterer' for context label
    is_highlighted = Column(Boolean, default=False)  # Featured on landing page
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="platform_feedback")

class DisputeReport(Base):
    __tablename__ = "dispute_reports"

    id = Column(Integer, primary_key=True, index=True)
    reference_id = Column(String, unique=True, index=True) # e.g. REP-10293
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    reporter_id = Column(Integer, ForeignKey("users.id"))
    reported_id = Column(Integer, ForeignKey("users.id"))
    reason = Column(String)
    details = Column(Text, nullable=True)
    evidence_url = Column(String, nullable=True)
    status = Column(String, default="pending") # pending, under_investigation, resolved, dismissed
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    booking = relationship("Booking")
    reporter = relationship("User", foreign_keys=[reporter_id])
    reported = relationship("User", foreign_keys=[reported_id])

class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    title = Column(String)
    description = Column(Text)
    discount_type = Column(String, default="percentage")
    discount_value = Column(Float)
    start_date = Column(Date)
    end_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    caterer = relationship("CatererProfile", back_populates="promotions")


class InternalSchedule(Base):
    __tablename__ = "internal_schedules"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    title = Column(String)
    schedule_type = Column(String)
    date = Column(Date)
    time = Column(Time, nullable=True)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    caterer = relationship("CatererProfile")

class Availability(Base):
    __tablename__ = "availability"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    date = Column(Date)
    is_available = Column(Boolean, default=False) # False means blocked
    reason = Column(String, nullable=True)

    caterer = relationship("CatererProfile", back_populates="availability")

class Inquiry(Base):
    __tablename__ = "inquiries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"), nullable=True)
    name = Column(String)
    email = Column(String)
    message = Column(Text)
    status = Column(String, default="new")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="inquiries")
    caterer = relationship("CatererProfile", back_populates="inquiries")

class IdentityVerification(Base):
    __tablename__ = "identity_verifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True) # Added to link verification attempt directly to booking
    verification_type = Column(String, default='government_id')
    document_url = Column(String, nullable=True)
    document_back_url = Column(String, nullable=True)
    
    # ID Details
    id_type = Column(String, nullable=True)
    id_number = Column(String, nullable=True)
    id_expiry_date = Column(Date, nullable=True)
    
    # Selfie & Liveness
    selfie_url = Column(String, nullable=True) # selfie_1
    selfie_2_url = Column(String, nullable=True)
    selfie_3_url = Column(String, nullable=True)
    
    # Granular Statuses (System processing)
    ocr_data = Column(JSONB)
    ocr_status = Column(String, nullable=True) # passed, failed, needs_review
    liveness_status = Column(String, nullable=True) # passed, failed, needs_review
    match_status = Column(String, nullable=True) # passed, failed, needs_review
    
    # Overall Status & Expiry
    verification_status = Column(String, default='PROCESSING') # PROCESSING, VERIFIED, NEEDS_REVIEW, FAILED, EXPIRED, REVERIFICATION_REQUIRED
    failure_reason = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_valid_until = Column(DateTime(timezone=True), nullable=True)
    
    # Manual Review Tracking (Admin)
    review_status = Column(String, nullable=True) # approved, rejected, requested_reverification
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Analytics & Fraud
    is_archived = Column(Boolean, default=False)
    fraud_score = Column(Integer, default=0)
    match_score = Column(Float, default=0.0) # Face match confidence
    face_detected = Column(Boolean, default=False)
    id_detected = Column(Boolean, default=False)
    ip_address = Column(String, nullable=True)
    device_info = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id], back_populates="identity_verifications")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    booking = relationship("Booking")

class CatererVerification(Base):
    __tablename__ = "caterer_verifications"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"), index=True)
    status = Column(String, default="PENDING_REVIEW") # PENDING_REVIEW, RESUBMISSION_REQUIRED, VERIFIED, REJECTED, EXPIRED
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    caterer = relationship("CatererProfile", back_populates="verifications")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    documents = relationship("VerificationDocument", back_populates="verification", cascade="all, delete-orphan")
    results = relationship("VerificationResult", back_populates="verification", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("VerificationAuditLog", back_populates="verification", cascade="all, delete-orphan")


class VerificationDocument(Base):
    __tablename__ = "verification_documents"

    id = Column(Integer, primary_key=True, index=True)
    verification_id = Column(Integer, ForeignKey("caterer_verifications.id"))
    document_type = Column(String) # GOVERNMENT_ID, SELFIE, BUSINESS_PERMIT
    secure_file_path = Column(String) # Path to secure storage, not public URL
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(Date, nullable=True)
    status = Column(String, default="PENDING") # PENDING, VALID, INVALID, EXPIRED

    verification = relationship("CatererVerification", back_populates="documents")


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True)
    verification_id = Column(Integer, ForeignKey("caterer_verifications.id"))
    name_match = Column(Boolean, default=False)
    dob_match = Column(Boolean, default=False)
    id_valid = Column(Boolean, default=False)
    permit_valid = Column(Boolean, default=False)
    selfie_check = Column(Boolean, default=False)
    overall_result = Column(String, nullable=True) # PASS, FLAG, FAIL

    verification = relationship("CatererVerification", back_populates="results")


class VerificationAuditLog(Base):
    __tablename__ = "verification_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    verification_id = Column(Integer, ForeignKey("caterer_verifications.id"))
    admin_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String) # Viewed ID, Approved, Rejected, etc.
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    verification = relationship("CatererVerification", back_populates="audit_logs")
    admin = relationship("User", foreign_keys=[admin_id])

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    message = Column(Text)
    type = Column(String, default="info") # info, success, warning, reminder
    is_read = Column(Boolean, default=False)
    link = Column(String, nullable=True) # URL to navigate to when clicked
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")

class VerificationAttempt(Base):
    __tablename__ = "verification_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    step = Column(String(20), nullable=False) # 'upload', 'ocr', 'liveness', 'match'
    status = Column(String(20), nullable=False) # pending/verified/failed
    details = Column(JSONB) # raw OCR data or error codes
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="verification_attempts")
    booking = relationship("Booking", back_populates="verification_attempts")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True))
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="refresh_tokens")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String)
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    device_info = Column(JSONB, nullable=True)
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="audit_logs")

class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True)
    package_details = Column(JSONB)
    addons = Column(JSONB)
    total_amount = Column(DECIMAL)
    downpayment_percent = Column(Integer) # CHECK (downpayment_percent BETWEEN 30 AND 50) - handle in app logic or custom CheckConstraint
    contract_url = Column(String, nullable=True) # signed PDF
    status = Column(String(20), default='draft') # draft, sent, signed, rejected
    
    # Digital Signatures (Base64 or URL to image)
    caterer_signature = Column(Text, nullable=True)
    customer_signature = Column(Text, nullable=True)
    caterer_signed_at = Column(DateTime(timezone=True), nullable=True)
    customer_signed_at = Column(DateTime(timezone=True), nullable=True)
    customer_approved_at = Column(DateTime(timezone=True), nullable=True) # Pre-acceptance approval step
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    booking = relationship("Booking", back_populates="quotation")

class FraudFlag(Base):
    __tablename__ = "fraud_flags"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    flag_type = Column(String(50)) # 'multiple_ids','high_risk_location'…
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="fraud_flags")

class Payout(Base):
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    amount = Column(Float)
    total_amount = Column(Float, default=0.0)
    payout_reference = Column(String, unique=True, index=True) # e.g. WDR-12345
    status = Column(String, default="pending") # pending, processing, completed
    reference_number = Column(String, nullable=True) # Bank Ref Number
    is_archived = Column(Boolean, default=False)
    notes = Column(Text, nullable=True) # Caterer notes
    admin_notes = Column(Text, nullable=True) # Admin notes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    caterer = relationship("CatererProfile", back_populates="payouts")
    items = relationship("PayoutItem", back_populates="payout", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="payout")

class PayoutItem(Base):
    __tablename__ = "payout_items"

    id = Column(Integer, primary_key=True, index=True)
    payout_id = Column(Integer, ForeignKey("payouts.id"), nullable=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    amount = Column(Float) # Net to Caterer
    commission_amount = Column(Float, default=0.0) # Platform Cut
    payment_reference = Column(String, nullable=True) # Paymongo/External Ref
    status = Column(String, default="pending") # pending, escrowed, ready, released
    release_trigger = Column(String, default="on_completion") # immediate, on_completion
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    payout = relationship("Payout", back_populates="items")
    booking = relationship("Booking")

class WebsiteConfig(Base):
    __tablename__ = "website_config"

    id = Column(Integer, primary_key=True, index=True)
    site_name = Column(String, default="OccaServe")
    support_email = Column(String, default="support@occaserve.com")
    seo_description = Column(Text, default="The premium marketplace for catering services in the Philippines.")
    
    # Branding
    logo_url = Column(String, nullable=True)
    favicon_url = Column(String, nullable=True)
    
    # Hero Slider
    hero_bg_1 = Column(String, nullable=True)
    hero_label_1 = Column(String, default="Wedding Receptions")
    hero_bg_2 = Column(String, nullable=True)
    hero_label_2 = Column(String, default="Corporate Events")
    hero_bg_3 = Column(String, nullable=True)
    hero_label_3 = Column(String, default="Christmas Parties")
    hero_bg_4 = Column(String, nullable=True)
    hero_label_4 = Column(String, default="Birthdays")
    hero_bg_5 = Column(String, nullable=True)
    hero_label_5 = Column(String, default="Private Parties")
    
    # Social Links
    facebook_link = Column(String, nullable=True)
    instagram_link = Column(String, nullable=True)
    twitter_link = Column(String, nullable=True)
    
    # System Constraints
    commission_rate = Column(Float, default=10.0)
    commission_fixed_amount = Column(Float, default=20.0)
    max_file_size_mb = Column(Integer, default=5)
    
    # Admin Payment Details
    admin_gcash_name = Column(String, nullable=True)
    admin_gcash_number = Column(String, nullable=True)
    admin_gcash_qr_url = Column(String, nullable=True)
    
    # Maintenance
    maintenance_mode = Column(Boolean, default=False)
    maintenance_message = Column(Text, default="OccaServe is currently undergoing scheduled maintenance. We'll be back online shortly!")
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=True)
    message_type = Column(String, default="text") # 'text', 'image', 'file'
    file_url = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")

class SocialPost(Base):
    __tablename__ = "social_posts"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    post_type = Column(String, default="general") # general, menu, package, achievement
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    caterer = relationship("CatererProfile", back_populates="social_posts")

class ProfileView(Base):
    """Track unique profile views per user per caterer.
    Each customer account can only count as ONE view per caterer profile.
    """
    __tablename__ = "profile_views"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"), nullable=False)
    viewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    caterer = relationship("CatererProfile")
    viewer = relationship("User")

class BookingTask(Base):
    __tablename__ = "booking_tasks"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    title = Column(String)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="tasks")

class BookingExpense(Base):
    __tablename__ = "booking_expenses"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    category = Column(String) # Ingredients, Labor, Transport, Other
    description = Column(String)
    amount = Column(Float, default=0.0)
    date_incurred = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="expenses")

class BillingInvoice(Base):
    __tablename__ = "billing_invoices"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    billing_period = Column(String) # e.g., "May 2026"
    amount = Column(Float, default=0.0)
    commission_rate = Column(Float, default=0.10)
    status = Column(String, default="pending") # pending, paid
    due_date = Column(Date, nullable=True)
    payment_proof_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    caterer = relationship("CatererProfile", backref="invoices")
    booking = relationship("Booking", backref="invoices")

class BusinessExpense(Base):
    __tablename__ = "business_expenses"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    category = Column("expense_category", String) # Rent, Utilities, Marketing, Payroll, Other
    description = Column(String)
    amount = Column(Float, default=0.0)
    date_incurred = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    caterer = relationship("CatererProfile", back_populates="business_expenses")


class VerificationSession(Base):
    __tablename__ = "verification_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="pending_liveness") # pending_liveness, pending_face_match, pending_compliance_review, verified, rejected
    liveness_score = Column(Float, default=0.0)
    anti_spoof_score = Column(Float, default=0.0)
    face_match_score = Column(Float, default=0.0)
    verification_result = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="verification_sessions")




class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id", ondelete="CASCADE"))
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True) # For Verified Badge
    title = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    highlights = Column(String, nullable=True) # Stored as comma-separated
    location = Column(String, nullable=True)
    event_date = Column(Date, nullable=True)
    visibility = Column(String, default="Public") # Public or Hidden
    is_featured = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    caterer = relationship("CatererProfile", back_populates="portfolios")
    booking = relationship("Booking", backref="portfolio")
    images = relationship("PortfolioImage", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioImage(Base):
    __tablename__ = "portfolio_images"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"))
    image_url = Column(String, nullable=False)
    is_cover = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    portfolio = relationship("Portfolio", back_populates="images")
