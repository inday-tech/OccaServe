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
    address = Column(Text, nullable=True)
    profile_image_url = Column(String, nullable=True)
    status = Column(String, default="active")
    status_reason = Column(Text, nullable=True)
    investigation_notes = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
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
    identity_verification = relationship("IdentityVerification", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    verification_attempts = relationship("VerificationAttempt", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    platform_feedback = relationship("PlatformFeedback", back_populates="user", cascade="all, delete-orphan")
    
    sent_messages = relationship("ChatMessage", foreign_keys="ChatMessage.sender_id", back_populates="sender")
    received_messages = relationship("ChatMessage", foreign_keys="ChatMessage.receiver_id", back_populates="receiver")

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
    gov_id_url = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # NEW: Brand Customization Fields
    primary_color = Column(String, default="#2D3748") # Deep Blue/Gray
    secondary_color = Column(String, default="#4A5568") # Gray
    accent_color = Column(String, default="#48BB78") # Green
    highlight_color = Column(String, default="#48BB78") # New: Extra branding color
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
    booking_policy = Column(Text, nullable=True)
    payment_policy = Column(Text, nullable=True)
    cancellation_policy = Column(Text, nullable=True)
    
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
    ingredients = relationship("Ingredient", back_populates="caterer", cascade="all, delete-orphan")
    business_expenses = relationship("BusinessExpense", back_populates="caterer", cascade="all, delete-orphan")

class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    name = Column(String, index=True)
    unit = Column(String) # kg, g, pieces, ml, etc.
    unit_price = Column(Float, default=0.0)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    caterer = relationship("CatererProfile", back_populates="ingredients")
    menu_item_ingredients = relationship("MenuItemIngredient", back_populates="ingredient")

class MenuItemIngredient(Base):
    __tablename__ = "menu_item_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    quantity = Column(Float) # Quantity in the specified unit

    menu_item = relationship("MenuItem", back_populates="ingredients")
    ingredient = relationship("Ingredient", back_populates="menu_item_ingredients")

class PackageItem(Base):
    __tablename__ = "package_items"
    package_id = Column(Integer, ForeignKey("catering_packages.id"), primary_key=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), primary_key=True)

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
    service_type = Column(String, default="General") # Wedding, Birthday, Corporate, etc.
    
    # NEW: Rich Pricing & Details
    price_per_head = Column(Float, nullable=True) # Selling Price (Customer Visible)
    internal_cost_per_pax = Column(Float, default=0.0) # Internal Break-even (Hidden)
    base_pax = Column(Integer, default=50) # The pax count used for costing
    
    # Internal Expense Breakdown
    labor_cost = Column(Float, default=0.0)
    utility_cost = Column(Float, default=0.0)
    equipment_cost = Column(Float, default=0.0)
    ingredient_total_cost = Column(Float, default=0.0)
    
    min_contract_amount = Column(Float, nullable=True)
    additional_guest_price = Column(Float, nullable=True)
    service_duration = Column(Integer, default=4) # In hours
    overtime_fee = Column(Float, default=0.0)
    location_coverage = Column(String, nullable=True) # City / Area
    reservation_fee = Column(Float, default=0.0)
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
    menu_items = relationship("MenuItem", secondary="package_items", back_populates="packages")

    bookings = relationship("Booking", back_populates="package")

class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    caterer_id = Column(Integer, ForeignKey("caterer_profiles.id"))
    name = Column(String)
    description = Column(Text, nullable=True)
    category = Column(String) # Starter, Soup, Salad, Main Dish (Beef), etc.
    price = Column(Float, default=0.0)
    cost_price = Column(Float, default=0.0)
    cost_breakdown = Column(JSONB, nullable=True)
    
    # Dietary & Allergen Info
    dietary_tags = Column(ARRAY(String), nullable=True) # Vegetarian, Vegan, Halal
    allergen_info = Column(ARRAY(String), nullable=True) # Nuts, Dairy, Seafood
    
    serving_size = Column(String, nullable=True) # "Good for 1", "Good for 10-15"
    pricing_unit = Column(String, default="per_serving") # "per_tray", "per_bilao", "per_pax", "per_hour", "per_item"
    is_addon = Column(Boolean, default=False)
    addon_price = Column(Float, default=0.0)
    image_url = Column(String, nullable=True)
    is_hidden = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    
    # Combo / Platter Properties
    is_combo = Column(Boolean, default=False)
    max_choices = Column(Integer, default=0)
    combo_options = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    caterer = relationship("CatererProfile", back_populates="menu_items")
    packages = relationship("CateringPackage", secondary="package_items", back_populates="menu_items")
    ingredients = relationship("MenuItemIngredient", back_populates="menu_item", cascade="all, delete-orphan")


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
    status = Column(String, default="pending")
    payment_status = Column(String, default="pending") # pending, paid, deposit_paid
    payment_method = Column(String, nullable=True) # GCash, Credit Card, etc.
    payment_reference = Column(String, nullable=True)
    payment_proof_url = Column(String, nullable=True)
    balance_proof_url = Column(String, nullable=True)
    dispatch_proof_url = Column(String, nullable=True)
    paymongo_link_id = Column(String, nullable=True)
    paymongo_link_url = Column(String, nullable=True)
    payout_id = Column(Integer, ForeignKey("payouts.id"), nullable=True)
    ocr_verification = relationship("OCRVerification", back_populates="booking", uselist=False, cascade="all, delete-orphan")

    payment_verification_data = Column(JSONB, nullable=True)
    proof_image_hash = Column(String, nullable=True)
    ocr_verified = Column(Boolean, default=False)
    liveness_verified = Column(Boolean, default=False)
    special_requests = Column(Text)
    caterer_notes = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False)
    booking_source = Column(String, default="OccaServe") # OccaServe, Facebook, Walk-in, Other
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    commission_calculated = Column(Boolean, default=False)
    
    expires_at = Column(DateTime(timezone=True), nullable=True)
    balance_due_date = Column(DateTime(timezone=True), nullable=True) 
    payment_plan = Column(String, default='downpayment') # 'downpayment' or 'full'
    event_location = Column(Text, nullable=True) 

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

class BookingMenuItem(Base):
    __tablename__ = "booking_menu_items"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))
    is_add_on = Column(Boolean, default=False)
    price = Column(Float) # Price at the time of booking
    quantity = Column(Integer, default=1)
    choices = Column(JSONB, nullable=True) # Array of selected item names/IDs for combos

    booking = relationship("Booking", back_populates="selected_items")
    menu_item = relationship("MenuItem")

class BookingHistory(Base):
    __tablename__ = "booking_history"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    status = Column(String) # The status being transitioned TO
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="history")

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
    rating = Column(Integer)
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

class PlatformFeedback(Base):
    __tablename__ = "platform_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    rating = Column(Integer)  # 1–5 stars
    comment = Column(Text)
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
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    verification_type = Column(String, default='government_id')
    document_url = Column(String, nullable=True)
    id_number = Column(String, nullable=True)
    selfie_url = Column(String, nullable=True) # selfie_1
    selfie_2_url = Column(String, nullable=True)
    selfie_3_url = Column(String, nullable=True)
    ocr_data = Column(JSONB)
    verification_status = Column(String, default='pending') # pending, processing, approved, rejected, manual_review, blocked
    failure_reason = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False)
    fraud_score = Column(Integer, default=0)
    match_score = Column(Float, default=0.0) # Face match confidence
    face_detected = Column(Boolean, default=False)
    id_detected = Column(Boolean, default=False)
    ip_address = Column(String, nullable=True)
    device_info = Column(JSONB, nullable=True)
    liveness_status = Column(String, nullable=True) # passed, failed
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="identity_verification")

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
    site_name = Column(String, default="OccaShare")
    support_email = Column(String, default="support@occashare.com")
    seo_description = Column(Text, default="The premium marketplace for catering services in the Philippines.")
    
    # Branding
    logo_url = Column(String, nullable=True)
    favicon_url = Column(String, nullable=True)
    
    # Social Links
    facebook_link = Column(String, nullable=True)
    instagram_link = Column(String, nullable=True)
    twitter_link = Column(String, nullable=True)
    
    # System Constraints
    commission_rate = Column(Float, default=10.0)
    commission_fixed_amount = Column(Float, default=20.0)
    max_file_size_mb = Column(Integer, default=5)
    
    # Maintenance
    maintenance_mode = Column(Boolean, default=False)
    maintenance_message = Column(Text, default="OccaShare is currently undergoing scheduled maintenance. We'll be back online shortly!")
    
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
    billing_period = Column(String) # e.g., "May 2026"
    amount = Column(Float, default=0.0)
    status = Column(String, default="pending") # pending, paid
    due_date = Column(Date, nullable=True)
    payment_proof_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    caterer = relationship("CatererProfile", backref="invoices")

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

