-- Migration script to add new fields to caterer_profiles table for OccaShare
-- Refined Caterer Registration Update

ALTER TABLE caterer_profiles 
ADD COLUMN IF NOT EXISTS min_pax INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS starting_price DOUBLE PRECISION DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS city VARCHAR(255),
ADD COLUMN IF NOT EXISTS sample_menu_url VARCHAR(255),
ADD COLUMN IF NOT EXISTS permit_url VARCHAR(255),
ADD COLUMN IF NOT EXISTS gov_id_url VARCHAR(255);

-- Optional: If city was missing from contact_address, we might want to populate it 
-- but since these are new fields, they will start empty for existing caterers.

COMMENT ON COLUMN caterer_profiles.min_pax IS 'Minimum number of guests the caterer can service';
COMMENT ON COLUMN caterer_profiles.starting_price IS 'Starting price of the caterer services in PHP';
COMMENT ON COLUMN caterer_profiles.city IS 'City or specific location of the business';
COMMENT ON COLUMN caterer_profiles.sample_menu_url IS 'Path to the uploaded sample menu or package PDF/Image';
COMMENT ON COLUMN caterer_profiles.permit_url IS 'Path to the uploaded business permit';
COMMENT ON COLUMN caterer_profiles.gov_id_url IS 'Path to the uploaded government ID of the owner';
