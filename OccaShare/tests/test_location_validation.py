from app.core.location_validation import (
    is_valid_ph_land_coordinates,
    validate_location_details,
)


MANILA = (14.5995, 120.9842)


def validate_caterer(**overrides):
    values = {
        "province": "Metro Manila",
        "municipality": "Manila",
        "barangay": "Ermita",
        "barangay_status": "identified",
        "landmark": "Near the city hall",
        "latitude": MANILA[0],
        "longitude": MANILA[1],
        "location_type": "caterer",
    }
    values.update(overrides)
    return validate_location_details(**values)


def validate_event(**overrides):
    values = {
        "province": "Laguna",
        "municipality": "Cavinti",
        "barangay": "Bukal",
        "barangay_status": "identified",
        "landmark": "BLOC Camp",
        "latitude": MANILA[0],
        "longitude": MANILA[1],
        "location_type": "event",
    }
    values.update(overrides)
    return validate_location_details(**values)


def test_accepts_valid_land_pins_on_main_islands():
    assert is_valid_ph_land_coordinates(*MANILA)
    assert is_valid_ph_land_coordinates(10.3157, 123.8854)


def test_rejects_water_and_out_of_country_pins():
    assert not is_valid_ph_land_coordinates(14.5, 120.9)  # Manila Bay
    assert not is_valid_ph_land_coordinates(13.99, 120.99)  # Taal Lake
    assert not is_valid_ph_land_coordinates(0, 0)


def test_event_accepts_required_venue_details_without_a_registered_street():
    assert validate_event() is None


def test_event_rejects_water_pins_even_with_address_details():
    assert "land-based" in validate_event(latitude=14.5, longitude=120.9)


def test_event_requires_province_city_and_barangay_but_not_landmark():
    assert validate_event(landmark="") is None
    assert "Province" in validate_event(province="")
    assert "City" in validate_event(municipality="")
    assert "Barangay" in validate_event(barangay="")


def test_caterer_requires_province_and_city():
    assert "Province" in validate_caterer(province="")
    assert "City" in validate_caterer(municipality="")


def test_caterer_accepts_exact_street_without_barangay():
    assert validate_caterer(
        barangay="",
        barangay_status="unavailable",
        landmark="",
        street_address="123 Main Street",
    ) is None


def test_caterer_requires_barangay_but_not_nearby_landmark_without_street():
    assert validate_caterer(street_address="", landmark="") is None
    assert validate_caterer(
        street_address="",
        barangay="",
        barangay_status="unavailable",
        landmark="",
    )


def test_caterer_rejects_water_pin_even_with_complete_address():
    assert "land-based" in validate_caterer(latitude=14.5, longitude=120.9)
