import random
import string
import re
import math
from typing import Optional

def calculate_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = {}
    for char in text:
        counts[char] = counts.get(char, 0) + 1
    entropy = 0.0
    for char in counts:
        p = counts[char] / len(text)
        entropy -= p * math.log2(p)
    return entropy

def is_gibberish(text: str) -> bool:
    s = re.sub(r'[^a-z]', '', text.lower())
    if not s:
        return False
    vowels = len(re.findall(r'[aeiouy]', s))
    consonants = len(re.findall(r'[bcdfghjklmnpqrstvwxz]', s))
    ratio = consonants / max(vowels, 1)
    # Relaxed ratio to allow consonant-heavy handles/names
    if ratio > 10 or (vowels == 0 and len(s) > 4):
        return True
    if len(s) > 6 and calculate_entropy(s) > 4.5:
        return True
    return False

def is_keyboard_walk(text: str) -> bool:
    walks = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm', '1234567890', 'poiuytrewq', 'lkjhgfdsa', 'mnbvcxz']
    s = text.lower()
    if len(s) < 3:
        return False
    for walk in walks:
        for i in range(len(walk) - 2):
            sub = walk[i:i+3]
            if sub in s:
                return True
    return False

def is_dummy_email(email: str) -> Optional[str]:
    email = email.lower().strip()
    disposable_domains = [
        'mailinator.com', 'guerrillamail.com', 'tempmail.com', '10minutemail.com',
        'dispostable.com', 'getairmail.com', 'yopmail.com', 'trashmail.com',
        'mailnesia.com', 'maildrop.cc', 'mintemail.com', 'teleworm.us'
    ]
    dummy_patterns = ['test', 'dummy', 'asdf', 'qwerty', '123456', 'demo', 'admin', 'user']
    
    if "@" not in email:
        return "Please enter a valid email address (e.g., example@gmail.com)"
    
    local, domain = email.split("@", 1)
    
    # Enforce Gmail for this specific requirement if needed, but the user says "Business Email" 
    # Usually business emails aren't just gmail, but previous turns enforced gmail.
    # I'll keep the gmail check if it's a project-wide rule, but the user didn't specify gmail ONLY here.
    # Wait, the previous turn had: "Only @gmail.com addresses are permitted".
    # I'll stick to gmail but make it more robust.
    if not email.endswith("@gmail.com"):
        return "Only @gmail.com addresses are permitted for platform security"
    
    if domain in disposable_domains:
        return "Disposable email domains are not permitted"
    
    if local in ['123', 'abc', 'aaa', 'qwe', '000']:
        return "Please use a real, professional email prefix"
    
    if any(p == local for p in dummy_patterns) or is_keyboard_walk(local) or is_gibberish(local):
        return "Email appears to be a placeholder or invalid"
        
    if re.search(r"(.)\1\1", local):
        return "Invalid email pattern (repetitive characters detected)"
        
    return None

def is_valid_business_name(name: str) -> Optional[str]:
    if not name or len(name.strip()) < 3:
        return "Business name must be at least 3 characters"
    if len(name) > 100:
        return "Business name is too long (max 100 characters)"
    
    # Accept letters, numbers, spaces, dots, apostrophes, hyphens, commas, and ampersands
    if not re.match(r"^[a-zA-Z0-9\s\.\'\-\,\&]+$", name):
        return "Business name should only contain letters, numbers, spaces, dots, apostrophes, hyphens, commas, and ampersands"

        
    # Must not be purely numeric
    if name.strip().isdigit():
        return "Business name cannot be purely numeric"
        
    # Split by spaces/hyphens to prevent false positives from word concatenation (e.g., "importeds and" -> "dsa")
    words = re.split(r'[\s\-]+', name)
    if any(is_keyboard_walk(w) for w in words) or is_gibberish(name.replace(" ", "")):
        return "Please provide a valid, professional business name"
        
    return None

def is_valid_person_name(name: str) -> Optional[str]:
    if not name or len(name.strip()) < 2:
        return "Name must be at least 2 characters"
        
    # Letters, spaces, and hyphens only
    if not re.match(r"^[a-zA-Z\s\-]+$", name):
        return "Name should not contain numbers or special characters"
        
    # Split by spaces/hyphens to prevent false positives from word concatenation (e.g., "david samuel" -> "dsa")
    words = re.split(r'[\s\-]+', name)
    if any(is_keyboard_walk(w) for w in words) or is_gibberish(name.replace(" ", "").replace("-", "")):
        return "Please provide a real name"
        
    if re.search(r"(.)\1\1", name): # Triple repetitive check
        return "Names cannot contain repetitive characters (e.g., aaa)"
        
    return None

def is_dummy_name(name: str) -> Optional[str]:
    """Legacy wrapper for backward compatibility or complex name checks"""
    return is_valid_person_name(name)

def is_dummy_phone(phone: str) -> Optional[str]:
    if not phone:
        return None
    phone = phone.strip().replace(" ", "")
    if not phone.startswith("09"):
        return "Mobile number must start with 09"
    if len(phone) != 11:
        return "Mobile number must be exactly 11 digits"
    if not phone.isdigit():
        return "Mobile number must contain only digits"
    if re.search(r"(.)\1\1", phone):
        return "Mobile number contains too many repetitive digits (e.g., 111)"
    
    # Check for repetitive patterns like 121212 or 123123
    if re.search(r"(.{2,3})\1\1", phone):
        return "Mobile number contains repetitive patterns (e.g., 121212)"
        
    dummy_nums = ['09123456789', '09111111111', '09000000000', '09999999999']
    if phone in dummy_nums:
        return "Please use a real mobile number"
    return None

def is_dummy_address(addr: str) -> Optional[str]:
    if not addr:
        return "Address is required"
    addr_str = addr.strip()
    if len(addr_str) < 5:
        return "Detailed address required"
    
    if is_gibberish(addr_str.replace(" ", "")):
        return "Please provide a valid address (no gibberish)"
        
    return None

def get_random_string(length=12):
    letters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(letters) for i in range(length))

def get_random_digits(length=6):
    return ''.join(random.choice(string.digits) for i in range(length))

def get_dashboard_url(role: str) -> str:
    """Returns the dashboard URL for a given role."""
    mapping = {
        "admin": "/admin/dashboard",
        "caterer": "/caterer/dashboard",
        "customer": "/customer/dashboard"
    }
    return mapping.get(role, "/")

def validate_file_type_and_size(file_content: bytes, filename: str, max_size_mb: int = 5) -> Optional[str]:
    """Validates file size and extension for security."""
    # Check size
    if len(file_content) > max_size_mb * 1024 * 1024:
        return f"File size exceeds the {max_size_mb}MB limit."
    
    # Check extension
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.pdf'}
    import os
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_extensions:
        return f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed_extensions)}"
    
    return None

def background_geocode(caterer_id: int):
    """Geocodes a caterer's address in the background and saves to DB."""
    try:
        from ..db.database import SessionLocal
        from ..db.models import CatererProfile
        import os
        import requests
        
        db = SessionLocal()
        try:
            caterer = db.query(CatererProfile).filter(CatererProfile.id == caterer_id).first()
            if not caterer:
                return
                
            addr = caterer.address_details or caterer.contact_address or ""
            if not addr:
                return
                
            api_key = os.getenv("GOOGLE_MAPS_API_KEY")
            if not api_key:
                print("[Geocode] No API key found")
                return
                
            resp = requests.get("https://maps.googleapis.com/maps/api/geocode/json", params={
                "address": addr,
                "key": api_key,
                "region": "ph"
            }, timeout=10)
            
            data = resp.json()
            if data.get("status") == "OK" and data.get("results"):
                loc = data["results"][0]["geometry"]["location"]
                caterer.latitude = loc["lat"]
                caterer.longitude = loc["lng"]
                db.commit()
                print(f"[Geocode] Successfully geocoded Caterer {caterer_id} to {loc['lat']}, {loc['lng']}")
            else:
                print(f"[Geocode] Failed to geocode {addr}: {data.get('status')}")
        finally:
            db.close()
    except Exception as e:
        print(f"[Geocode] Exception during geocoding: {e}")
