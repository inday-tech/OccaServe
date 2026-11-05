from app.core.location_validation import validate_location_details


LATITUDE = 14.5995
LONGITUDE = 120.9842


def validate(**overrides):
    values = {
        "province": "Metro Manila",
        "municipality": "Manila",
        "barangay": "Ermita",
        "barangay_status": "identified",
        "landmark": "",
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
    }
    values.update(overrides)
    return validate_location_details(**values)


def test_accepts_identified_barangay():
    assert validate() is None


def test_accepts_manual_barangay():
    assert validate(barangay="Ermita", barangay_status="manual") is None


def test_requires_landmark_when_barangay_unavailable():
    assert "landmark" in validate(
        barangay="",
        barangay_status="unavailable",
        landmark="",
    )
    assert validate(
        barangay="",
        barangay_status="unavailable",
        landmark="Seaside Pavilion",
    ) is None


def test_rejects_unconfirmed_missing_barangay():
    assert "Confirm the barangay" in validate(barangay="", barangay_status="")


def test_rejects_inconsistent_barangay_status():
    assert "Clear the barangay" in validate(
        barangay="Ermita",
        barangay_status="unavailable",
        landmark="Seaside Pavilion",
    )
    assert "Enter the barangay" in validate(barangay="", barangay_status="manual")


def test_requires_province_city_and_philippines_pin():
    assert "Province" in validate(province="")
    assert "City" in validate(municipality="")
    assert "location pin" in validate(latitude=0, longitude=0)


def test_legacy_form_with_barangay_remains_valid():
    assert validate(barangay_status="") is None
