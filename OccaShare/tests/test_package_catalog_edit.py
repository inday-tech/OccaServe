import asyncio
from types import SimpleNamespace

from app.db import models
from app.routers.caterer_dashboard import get_catalogs_inclusions, quick_edit_catalog_item


class CatalogQuery:
    def __init__(self, item):
        self.item = item

    def filter(self, *_criteria):
        return self

    def first(self):
        return self.item


class CatalogDatabase:
    def __init__(self, item):
        self.item = item

    def query(self, _model):
        return CatalogQuery(self.item)

    def commit(self):
        pass

    def refresh(self, _item):
        pass


class InclusionCatalogQuery:
    def __init__(self, model, filters):
        self.model = model
        self.filters = filters

    def filter(self, *criteria):
        self.filters[self.model] = criteria
        return self

    def order_by(self, *_criteria):
        return self

    def all(self):
        return []


class InclusionCatalogDatabase:
    def __init__(self):
        self.filters = {}

    def query(self, model):
        return InclusionCatalogQuery(model, self.filters)


def edit_catalog_item(item_type, item, **values):
    return asyncio.run(quick_edit_catalog_item(
        item_type=item_type,
        item_id=item.id,
        name=values.pop("name", item.name),
        category=values.pop("category", item.category),
        custom_category=values.pop("custom_category", None),
        upgrade_fee=values.pop("upgrade_fee", 0),
        addon_price=values.pop("addon_price", None),
        price=values.pop("price", None),
        unit_type=values.pop("unit_type", None),
        available_qty=values.pop("available_qty", None),
        minimum_hours=values.pop("minimum_hours", None),
        staff_to_pax_ratio=values.pop("staff_to_pax_ratio", None),
        min_staff_required=values.pop("min_staff_required", None),
        status=values.pop("status", "available"),
        description=values.pop("description", item.description),
        image=None,
        db=CatalogDatabase(item),
        user=SimpleNamespace(caterer_profile=SimpleNamespace(id=7)),
    ))


def test_inclusion_catalog_only_returns_items_accepted_by_package_save():
    db = InclusionCatalogDatabase()
    user = SimpleNamespace(caterer_profile=SimpleNamespace(id=7))

    result = asyncio.run(get_catalogs_inclusions(db=db, user=user))

    assert result == {"equipment": [], "menu": [], "service": []}
    assert {criterion.left.key for criterion in db.filters[models.MenuItem]} >= {
        "caterer_id",
        "is_archived",
        "is_hidden",
        "available_for_package",
        "usage_type",
        "status",
    }
    assert {criterion.left.key for criterion in db.filters[models.Service]} >= {
        "caterer_id",
        "is_archived",
        "is_hidden",
        "usage_type",
        "status",
    }
    assert {criterion.left.key for criterion in db.filters[models.Equipment]} >= {
        "caterer_id",
        "is_archived",
        "is_hidden",
        "usage_type",
        "status",
    }


def test_menu_edit_saves_extra_price_availability_and_pricing_unit():
    menu = SimpleNamespace(
        id=11,
        caterer_id=7,
        name="Chicken",
        category="Chicken",
        price=0,
        pricing_unit="per_pax",
        addon_price=20,
        upgrade_fee=0,
        status="available",
        description="",
        image_url=None,
    )

    result = edit_catalog_item(
        "menu",
        menu,
        category="Other",
        custom_category="Vegetarian",
        upgrade_fee=15,
        addon_price=80,
        unit_type="per_tray",
        status="unavailable",
    )

    assert result["item"]["category"] == "Vegetarian"
    assert result["item"]["addon_price"] == 80
    assert result["item"]["upgrade_fee"] == 15
    assert result["item"]["unit_type"] == "per_tray"
    assert result["item"]["status"] == "unavailable"


def test_service_edit_saves_capacity_duration_and_staffing_fields():
    service = SimpleNamespace(
        id=12,
        caterer_id=7,
        name="Waitstaff",
        category="Staffing",
        selling_price=100,
        unit_type="per_event",
        max_available=2,
        minimum_hours=1,
        capacity_type="unit_based",
        staff_to_pax_ratio=0,
        min_staff_required=1,
        status="available",
        description="",
        image_url=None,
    )

    result = edit_catalog_item(
        "service",
        service,
        price="250.00",
        unit_type="per_staff",
        available_qty=8,
        minimum_hours=4,
        staff_to_pax_ratio=20,
        min_staff_required=2,
        status="unavailable",
    )

    assert result["item"]["price"] == 250
    assert result["item"]["unit_type"] == "per_staff"
    assert result["item"]["max_available"] == 8
    assert result["item"]["minimum_hours"] == 4
    assert result["item"]["staff_to_pax_ratio"] == 20
    assert result["item"]["min_staff_required"] == 2
    assert result["item"]["status"] == "unavailable"


def test_service_catalog_allows_an_explicit_zero_price_for_review_required_items():
    service = SimpleNamespace(
        id=14,
        caterer_id=7,
        name="Unpriced service",
        category="Service",
        selling_price=100,
        unit_type="per_event",
        max_available=1,
        minimum_hours=1,
        capacity_type="unit_based",
        staff_to_pax_ratio=0,
        min_staff_required=1,
        status="available",
        description="",
        image_url=None,
    )

    result = edit_catalog_item("service", service, price="0.00")

    assert result["item"]["price"] == 0


def test_equipment_edit_preserves_catalog_addon_default_when_not_editable():
    equipment = SimpleNamespace(
        id=13,
        caterer_id=7,
        name="Round Table",
        category="Tables",
        rental_price=500,
        addon_price=125,
        unit_type="piece",
        available_qty=4,
        status="available",
        description="",
        image_url=None,
    )

    result = edit_catalog_item(
        "equipment",
        equipment,
        category="Furniture",
        price="600.00",
        unit_type="set",
        available_qty=10,
        status="unavailable",
    )

    assert result["item"]["category"] == "Furniture"
    assert result["item"]["rental_price"] == 600
    assert result["item"]["unit_type"] == "set"
    assert result["item"]["available_qty"] == 10
    assert result["item"]["status"] == "unavailable"
    assert equipment.addon_price == 125
