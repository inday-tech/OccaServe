from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date, time

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    role: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Registration Schemas ---
class UserRegisterCustomer(UserBase):
    full_name: str
    mobile_number: str
    password: str
    confirm_password: str

class UserRegisterCaterer(UserBase):
    full_name: str
    mobile_number: str
    password: str
    confirm_password: str
    business_name: str
    business_type: str
    years_of_operation: int
    business_description: str
    coverage_area: str
    payout_method: str
    payout_account_name: str
    payout_account_number: str

# --- Caterer Profile Schemas ---
class CatererProfileBase(BaseModel):
    business_name: str
    description: Optional[str] = None
    contact_phone: Optional[str] = None
    logo_url: Optional[str] = None

class CatererProfileCreate(CatererProfileBase):
    pass

class CatererProfileResponse(CatererProfileBase):
    id: int
    user_id: int
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Catering Package Schemas ---
class CateringPackageBase(BaseModel):
    name: str
    description: str
    price: float
    image_url: Optional[str] = None

class CateringPackageCreate(CateringPackageBase):
    pass

class CateringPackage(CateringPackageBase):
    id: int
    caterer_id: int
    is_active: bool
    
    class Config:
        from_attributes = True

# --- Inquiry Schemas ---
class InquiryCreate(BaseModel):
    name: str
    email: str
    message: str
    caterer_id: Optional[int] = None

# --- Admin Schemas ---
class CatererCreateRequest(BaseModel):
    email: EmailStr
    business_name: str
    contact_phone: Optional[str] = None
    description: Optional[str] = None

    access_token: str
    token_type: str

# --- Booking Schemas ---
class BookingBase(BaseModel):
    event_date: date
    event_time: Optional[time] = None
    guest_count: int
    special_requests: Optional[str] = None

class BookingCreate(BookingBase):
    caterer_id: int

class Booking(BookingBase):
    id: int
    user_id: int
    caterer_id: int
    status: str
    
    class Config:
        from_attributes = True

# --- Social Post Schemas ---
class SocialPostResponse(BaseModel):
    id: int
    caterer_id: int
    content: str
    image_url: Optional[str] = None
    post_type: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Chat Schemas ---
class ChatMessageBase(BaseModel):
    content: Optional[str] = None
    message_type: str = "text"
    file_url: Optional[str] = None
    file_name: Optional[str] = None

class ChatMessageCreate(ChatMessageBase):
    receiver_id: int

class ChatMessageResponse(ChatMessageBase):
    id: int
    sender_id: int
    receiver_id: int
    is_read: bool
    is_edited: bool
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Caterer Post Schemas ---
class CatererPostBase(BaseModel):
    content: str
    post_type: str = "general"
    image_url: Optional[str] = None
    is_public: bool = True

class CatererPostCreate(CatererPostBase):
    pass

class CatererPostResponse(CatererPostBase):
    id: int
    caterer_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
