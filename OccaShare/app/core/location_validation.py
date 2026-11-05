import json
import math
from functools import lru_cache
from pathlib import Path

from .utils import is_valid_ph_coordinates


BARANGAY_STATUSES = {"identified", "manual", "unavailable"}
LOCATION_BOUNDARIES_PATH = Path(__file__).parent.parent / "static" / "data" / "ph_location_boundaries.json"
RIVER_BUFFER_METERS = 30


@lru_cache(maxsize=1)
def _location_boundaries():
    with LOCATION_BOUNDARIES_PATH.open(encoding="utf-8") as boundary_file:
        return json.load(boundary_file)


def _ring_contains(longitude, latitude, ring):
    inside = False
    for index, (x1, y1, *_) in enumerate(ring):
        x2, y2, *_ = ring[(index + 1) % len(ring)]
        cross = (longitude - x1) * (y2 - y1) - (latitude - y1) * (x2 - x1)
        if (
            abs(cross) <= 1e-10
            and min(x1, x2) - 1e-10 <= longitude <= max(x1, x2) + 1e-10
            and min(y1, y2) - 1e-10 <= latitude <= max(y1, y2) + 1e-10
        ):
            return True
        if (y1 > latitude) != (y2 > latitude):
            crossing_longitude = (x2 - x1) * (latitude - y1) / (y2 - y1) + x1
            if longitude < crossing_longitude:
                inside = not inside
    return inside


def _polygon_contains(longitude, latitude, rings):
    return bool(rings) and _ring_contains(longitude, latitude, rings[0]) and not any(
        _ring_contains(longitude, latitude, hole) for hole in rings[1:]
    )


def _geometry_contains(geometry, longitude, latitude):
    geometry_type = geometry["type"]
    coordinates = geometry["coordinates"]
    if geometry_type == "Polygon":
        return _polygon_contains(longitude, latitude, coordinates)
    if geometry_type == "MultiPolygon":
        return any(_polygon_contains(longitude, latitude, polygon) for polygon in coordinates)
    if geometry_type == "GeometryCollection":
        return any(_geometry_contains(item, longitude, latitude) for item in geometry["geometries"])
    return False


def _point_near_line(longitude, latitude, line, buffer_meters):
    meters_per_degree = 111_320
    longitude_scale = math.cos(math.radians(latitude))
    point_x = longitude * longitude_scale * meters_per_degree
    point_y = latitude * meters_per_degree
    for index in range(len(line) - 1):
        x1 = line[index][0] * longitude_scale * meters_per_degree
        y1 = line[index][1] * meters_per_degree
        x2 = line[index + 1][0] * longitude_scale * meters_per_degree
        y2 = line[index + 1][1] * meters_per_degree
        dx = x2 - x1
        dy = y2 - y1
        segment_length_squared = dx * dx + dy * dy
        if segment_length_squared == 0:
            distance_squared = (point_x - x1) ** 2 + (point_y - y1) ** 2
        else:
            projection = max(0, min(1, ((point_x - x1) * dx + (point_y - y1) * dy) / segment_length_squared))
            nearest_x = x1 + projection * dx
            nearest_y = y1 + projection * dy
            distance_squared = (point_x - nearest_x) ** 2 + (point_y - nearest_y) ** 2
        if distance_squared <= buffer_meters * buffer_meters:
            return True
    return False


def _geometry_near_line(geometry, longitude, latitude, buffer_meters):
    geometry_type = geometry["type"]
    coordinates = geometry["coordinates"]
    if geometry_type == "LineString":
        return _point_near_line(longitude, latitude, coordinates, buffer_meters)
    if geometry_type == "MultiLineString":
        return any(
            _point_near_line(longitude, latitude, line, buffer_meters)
            for line in coordinates
        )
    if geometry_type == "GeometryCollection":
        return any(
            _geometry_near_line(item, longitude, latitude, buffer_meters)
            for item in geometry["geometries"]
        )
    return False


def is_valid_ph_land_coordinates(latitude, longitude):
    """Return whether coordinates are on mapped Philippine land rather than mapped water."""
    if not is_valid_ph_coordinates(latitude, longitude):
        return False
    lat = float(latitude)
    lng = float(longitude)
    boundaries = _location_boundaries()
    if not any(
        _geometry_contains(geometry, lng, lat)
        for geometry in boundaries["land"]
    ):
        return False
    if any(
        _geometry_contains(geometry, lng, lat)
        for geometry in boundaries["water_polygons"]
    ):
        return False
    return not any(
        _geometry_near_line(geometry, lng, lat, RIVER_BUFFER_METERS)
        for geometry in boundaries["river_lines"]
    )


def validate_location_details(
    province,
    municipality,
    barangay,
    barangay_status,
    landmark,
    latitude,
    longitude,
    *,
    location_type="event",
    street_address="",
    nearby_landmark="",
):
    """Validate shared map coordinates with distinct caterer and event address rules."""
    province = (province or "").strip()
    municipality = (municipality or "").strip()
    barangay = (barangay or "").strip()
    landmark = (landmark or "").strip()
    status = (barangay_status or "").strip().lower()
    street_address = (street_address or "").strip()
    nearby_landmark = (nearby_landmark or "").strip()

    if location_type not in {"caterer", "event"}:
        raise ValueError("location_type must be 'caterer' or 'event'.")
    if not is_valid_ph_land_coordinates(latitude, longitude):
        return "Choose a valid land-based location pin in the Philippines, not a body of water."
    if location_type == "event":
        return None

    if not province:
        return "Province is required for the business address."
    if not municipality:
        return "City or municipality is required for the business address."

    if status and status not in BARANGAY_STATUSES:
        return "Confirm the barangay or clear its status."
    if status == "unavailable" and barangay:
        return "Clear the barangay field when marking it unavailable."
    if status in {"identified", "manual"} and not barangay:
        return "Enter the barangay or mark it as unavailable."
    if street_address:
        return None
    if not barangay or status == "unavailable":
        return "Enter an exact street address, or provide a barangay and nearby landmark."
    if not nearby_landmark and not landmark:
        return "Enter a nearby landmark when no exact street address is available."

    return None
