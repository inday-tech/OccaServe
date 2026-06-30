import os

file_path = r"c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

params_to_insert = """    business_hours_open_time: Optional[str] = Form("08:00"),
    business_hours_close_time: Optional[str] = Form("20:00"),
    food_delivery_start: Optional[str] = Form("09:00"),
    food_delivery_end: Optional[str] = Form("19:00"),
    food_lead_time_hours: Optional[int] = Form(24),
    food_allow_same_day: Optional[bool] = Form(False),
    equipment_pickup_start: Optional[str] = Form("08:00"),
    equipment_pickup_end: Optional[str] = Form("18:00"),
    equipment_min_rental: Optional[int] = Form(24),
    equipment_max_rental: Optional[int] = Form(72),
    service_earliest_start: Optional[str] = Form("08:00"),
    service_latest_end: Optional[str] = Form("22:00"),
    service_min_duration: Optional[int] = Form(3),
    service_max_duration: Optional[int] = Form(8),
    package_min_duration: Optional[int] = Form(4),
    package_max_duration: Optional[int] = Form(6),
    package_setup_time: Optional[int] = Form(2),
    package_cleanup_time: Optional[int] = Form(1),
"""

logic_to_insert = """
    # Update Universal Scheduling Rules
    profile.scheduling_rules = {
        "business_hours": {"open_time": business_hours_open_time, "close_time": business_hours_close_time},
        "food_rules": {
            "delivery_available": True, "pickup_available": True, 
            "delivery_start": food_delivery_start, "delivery_end": food_delivery_end, 
            "lead_time_hours": food_lead_time_hours, "allow_same_day": bool(food_allow_same_day)
        },
        "equipment_rules": {
            "pickup_start": equipment_pickup_start, "pickup_end": equipment_pickup_end, 
            "return_start": equipment_pickup_start, "return_end": equipment_pickup_end, 
            "min_rental_hours": equipment_min_rental, "max_rental_hours": equipment_max_rental
        },
        "service_rules": {
            "min_duration_hours": service_min_duration, "max_duration_hours": service_max_duration, 
            "earliest_start": service_earliest_start, "latest_end": service_latest_end
        },
        "package_rules": {
            "min_event_duration": package_min_duration, "max_event_duration": package_max_duration, 
            "setup_time_hours": package_setup_time, "cleanup_time_hours": package_cleanup_time
        }
    }
"""

content = content.replace(params_to_insert + "    user: models.User = Depends(caterer_only)", "user: models.User = Depends(caterer_only)")
content = content.replace("profile = user.caterer_profile" + logic_to_insert, "profile = user.caterer_profile")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Undid patch")
