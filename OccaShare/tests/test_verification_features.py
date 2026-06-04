import pytest
from app.services.verification import verification_service
import numpy as np

def test_parse_passport_mrz():
    # Standard TD3 Passport MRZ format
    mrz_text = (
        "P<PHLRODRIGUEZ<<MARIA<CLARA<<<<<<<<<<<<<<<<<\n"
        "P1234567A8PHL9001015F2512312<<<<<<<<<<<<<<02"
    )
    result = verification_service.parse_passport_mrz(mrz_text)
    assert result is not None
    assert result["passport_number"] == "P1234567A"
    assert result["last_name"] == "RODRIGUEZ"
    assert result["first_name"] == "MARIA"
    assert result["middle_name"] == "CLARA"
    assert result["nationality"] == "PHL"
    assert result["date_of_birth"] == "1990-01-01"
    assert result["sex"] == "FEMALE"
    assert result["expiry_date"] == "2025-12-31"
    assert result["mrz_parsed"] is True

def test_validate_and_autocorrect_fields():
    # 1. PhilSys formatting and digits-to-letters, letters-to-digits swaps
    philid_fields = {
        "id_number": {"value": "44O4-1234-5S78-9O12", "confidence": 80}, # O->0, S->5
        "last_name": {"value": "R0DR1GUEZ", "confidence": 85}, # 0->O, 1->I
        "first_name": {"value": "MAR1A", "confidence": 90}, # 1->I
        "date_of_birth": {"value": "1990/01/01", "confidence": 90},
        "sex": {"value": "M", "confidence": 90},
        "nationality": {"value": "FILIP", "confidence": 90}
    }
    
    corrected = verification_service._validate_and_autocorrect_fields(philid_fields, "PhilSys / PhilID")
    assert corrected["id_number"]["value"] == "4404-1234-5578-9012"
    assert corrected["last_name"]["value"] == "RODRIGUEZ"
    assert corrected["first_name"]["value"] == "MARIA"
    assert corrected["sex"]["value"] == "MALE"
    assert corrected["nationality"]["value"] == "FILIPINO"

    # 2. Driver's License formatting
    dl_fields = {
        "id_number": {"value": "N01-23-456789", "confidence": 80}, # N01->N01, but formatted as N01-23-456789
        "last_name": {"value": "CRUZ", "confidence": 95}
    }
    corrected_dl = verification_service._validate_and_autocorrect_fields(dl_fields, "Driver's License")
    assert corrected_dl["id_number"]["value"] == "N01-23-456789"

    # 3. Passport formatting
    passport_fields = {
        "id_number": {"value": "P1234567O", "confidence": 80},
        "last_name": {"value": "SANT0S", "confidence": 95}
    }
    corrected_pass = verification_service._validate_and_autocorrect_fields(passport_fields, "Passport")
    assert corrected_pass["last_name"]["value"] == "SANTOS"

def test_check_image_quality():
    # Resolution too low check
    small_img = np.zeros((100, 100, 3), dtype=np.uint8)
    res = verification_service.check_image_quality(small_img)
    assert res["valid"] is False
    assert "Resolution too low" in res["reason"]
