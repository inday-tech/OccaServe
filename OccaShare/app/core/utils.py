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
        'dispostable.com', 'getairmail.com', 'yopmail.com', 'trashmail.com'
    ]
    dummy_patterns = ['test', 'dummy', 'asdf', 'qwerty', '123456', 'demo', 'admin', 'user']
    
    if "@" not in email:
        return "Invalid email format"
    
    local, domain = email.split("@", 1)
    
    if not email.endswith("@gmail.com"):
        return "Only Gmail addresses are allowed"
    
    if domain in disposable_domains or local in ['123', 'abc', 'aaa', 'qwe']:
        return "Disposable or placeholder email addresses are not allowed"
    
    if any(p in local for p in dummy_patterns) or is_keyboard_walk(local) or is_gibberish(local):
        return "Please use a real, professional email address"
        
    if re.search(r"(.)\1\1", local):
        return "Invalid email pattern (repetitive characters)"
        
    return None

def is_dummy_name(name: str) -> Optional[str]:
    if not name:
        return None
    name_str = name.lower().strip()
    dummy_names = ['pepito', 'test', 'dummy', 'guest', 'admin', 'user', 'qwerty', 'asdf', 'demo']
    
    if len(name_str) < 3:
        return "Names must be at least 3 characters"
        
    clean_name = name_str.replace(" ", "")
    if any(d in name_str for d in dummy_names) or is_keyboard_walk(clean_name) or is_gibberish(clean_name):
        return "Please use a real, professional name"
        
    if re.search(r"(.)\1\1", name_str):
        return "Names cannot contain repetitive characters"
        
    parts = name_str.split()
    if len(parts) < 2:
        return "Please enter full name (at least 2 words)"
    if len(parts) != len(set(parts)):
        return "Names cannot contain repetitive words (e.g. Pepito Pepito)"
    return None

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
