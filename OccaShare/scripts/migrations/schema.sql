-- Comprehensive Database Schema for OccaServe (PostgreSQL)

-- DROP tables if they exist to allow clean re-initialization
DROP TABLE IF EXISTS inquiries CASCADE;
DROP TABLE IF EXISTS availability CASCADE;
DROP TABLE IF EXISTS promotions CASCADE;
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS caterer_gallery CASCADE;
DROP TABLE IF EXISTS catering_packages CASCADE;
DROP TABLE IF EXISTS caterer_profiles CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. Users Table (Core Authentication)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'customer', -- 'admin', 'caterer', 'customer'
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone_number VARCHAR(20),
    profile_image_url VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- 'active', 'inactive', 'suspended'
    is_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP WITH TIME ZONE,
    facebook_id VARCHAR(255) UNIQUE,
    instagram_id VARCHAR(255) UNIQUE,
    auth_provider VARCHAR(50) DEFAULT 'email', -- 'email', 'facebook', 'instagram'
    is_email_verified BOOLEAN DEFAULT FALSE,
    verification_code VARCHAR(10),
    otp_expires_at TIMESTAMP WITH TIME ZONE,
    reset_token VARCHAR(255) UNIQUE,
    reset_token_expires TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 1b. Identity Verifications
CREATE TABLE identity_verifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    verification_type VARCHAR(50) DEFAULT 'government_id',
    document_url VARCHAR(255) NOT NULL,
    selfie_url VARCHAR(255) NOT NULL,
    ocr_data JSONB, -- Extracted text from ID
    verification_status VARCHAR(50) DEFAULT 'pending', -- pending, verified, rejected
    failure_reason TEXT,
    verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Caterer Profiles (Extended)
CREATE TABLE caterer_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE, -- For SEO friendly URLs e.g., /caterer/gourmet-delight
    description TEXT,
    logo_url VARCHAR(255),
    cover_image_url VARCHAR(255),
    contact_phone VARCHAR(50),
    contact_address TEXT,
    city VARCHAR(100),
    cuisine_types TEXT[], -- Array of strings e.g. ['Italian', 'Vegan']
    event_types TEXT[], -- Array of strings e.g. ['Wedding', 'Corporate']
    rating DECIMAL(3, 2) DEFAULT 0.00,
    review_count INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_caterer UNIQUE (user_id)
);

-- 3. Catering Packages
CREATE TABLE catering_packages (
    id SERIAL PRIMARY KEY,
    caterer_id INTEGER NOT NULL REFERENCES caterer_profiles(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    price_unit VARCHAR(50) DEFAULT 'per_guest', -- 'per_guest', 'fixed_price'
    min_guests INTEGER DEFAULT 10,
    max_guests INTEGER,
    image_url VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Caterer Gallery (Images/Videos)
CREATE TABLE caterer_gallery (
    id SERIAL PRIMARY KEY,
    caterer_id INTEGER NOT NULL REFERENCES caterer_profiles(id) ON DELETE CASCADE,
    media_url VARCHAR(255) NOT NULL,
    media_type VARCHAR(20) DEFAULT 'image', -- 'image', 'video'
    caption VARCHAR(255),
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Bookings
CREATE TABLE bookings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    caterer_id INTEGER NOT NULL REFERENCES caterer_profiles(id) ON DELETE CASCADE,
    package_id INTEGER REFERENCES catering_packages(id) ON DELETE SET NULL,
    event_date DATE NOT NULL,
    event_time TIME,
    guest_count INTEGER,
    total_amount DECIMAL(10, 2),
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'confirmed', 'completed', 'cancelled', 'rejected'
    payment_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'paid', 'deposit_paid'
    ocr_verified BOOLEAN DEFAULT FALSE,
    liveness_verified BOOLEAN DEFAULT FALSE,
    special_requests TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Reviews & Ratings
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    booking_id INTEGER UNIQUE REFERENCES bookings(id) ON DELETE SET NULL, -- One review per booking
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    caterer_id INTEGER NOT NULL REFERENCES caterer_profiles(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Promotions / Discounts
CREATE TABLE promotions (
    id SERIAL PRIMARY KEY,
    caterer_id INTEGER NOT NULL REFERENCES caterer_profiles(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    discount_type VARCHAR(20) DEFAULT 'percentage', -- 'percentage', 'flat_amount'
    discount_value DECIMAL(10, 2) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Availability / Blocked Dates
CREATE TABLE availability (
    id SERIAL PRIMARY KEY,
    caterer_id INTEGER NOT NULL REFERENCES caterer_profiles(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    is_available BOOLEAN DEFAULT FALSE, -- If FALSE, date is blocked
    reason VARCHAR(255), -- 'fully_booked', 'closed', etc.
    UNIQUE(caterer_id, date)
);

-- 9. Inquiries (General or Specific)
CREATE TABLE inquiries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    caterer_id INTEGER REFERENCES caterer_profiles(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'new', -- 'new', 'read', 'replied'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_caterer_profiles_city ON caterer_profiles(city);
CREATE INDEX idx_bookings_date ON bookings(event_date);
CREATE INDEX idx_reviews_caterer ON reviews(caterer_id);

-- Initial Admin Account (Password: admin123)
-- Hash generated using bcrypt
INSERT INTO users (email, password_hash, role, status, first_name, last_name)
VALUES ('admin@occashare.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxwKc.6q.F0wQ2/l.yy2.1.2.3', 'admin', 'active', 'System', 'Admin')
ON CONFLICT (email) DO NOTHING;
