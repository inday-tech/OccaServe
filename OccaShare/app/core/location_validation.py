from .utils import is_valid_ph_coordinates


BARANGAY_STATUSES = {"identified", "manual", "unavailable"}


def validate_location_details(
    province,
    municipality,
    barangay,
    barangay_status,
    landmark,
    latitude,
    longitude,
):
    """Return a validation message for a confirmed PH map location, or None."""
    province = (province or "").strip()
    municipality = (municipality or "").strip()
    barangay = (barangay or "").strip()
    landmark = (landmark or "").strip()
    status = (barangay_status or "").strip().lower()

    if not province:
        return "Province is required."
    if not municipality:
        return "City or municipality is required."
    if not is_valid_ph_coordinates(latitude, longitude):
        return "Choose a valid location pin in the Philippines."

    # Older forms only sent the barangay value. Continue accepting those
    # submissions while requiring an explicit status when it is unavailable.
    if not status and barangay:
        status = "identified"
    if status not in BARANGAY_STATUSES:
        return "Confirm the barangay or mark it as unavailable."
    if status == "unavailable":
        if barangay:
            return "Clear the barangay field when marking it unavailable."
        if not landmark:
            return "Enter a venue, street, building, or landmark when the barangay is unavailable."
    elif not barangay:
        return "Enter the barangay or mark it as unavailable."

    return None
