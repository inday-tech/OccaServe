import re

file_path = "c:\\OccaServe\\OccaShare\\templates\\caterer\\profile_edit.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

new_html = """
            <!-- Section: Booking & Availability -->
            <div class="settings-section" id="section-availability">
                <div class="section-header-compact">
                    <h3><i class="fas fa-clock"></i> Universal Scheduling & Availability</h3>
                    <p>Set specific schedules and durations for different transaction types.</p>
                </div>

                {% set rules = profile.scheduling_rules or {} %}
                {% set bh = rules.get('business_hours', {'open_time': '08:00', 'close_time': '20:00'}) %}
                {% set fr = rules.get('food_rules', {'delivery_available': true, 'pickup_available': true, 'delivery_start': '09:00', 'delivery_end': '19:00', 'lead_time_hours': 24, 'allow_same_day': false}) %}
                {% set er = rules.get('equipment_rules', {'pickup_start': '08:00', 'pickup_end': '18:00', 'return_start': '08:00', 'return_end': '18:00', 'min_rental_hours': 24, 'max_rental_hours': 72}) %}
                {% set sr = rules.get('service_rules', {'min_duration_hours': 3, 'max_duration_hours': 8, 'earliest_start': '08:00', 'latest_end': '22:00'}) %}
                {% set pr = rules.get('package_rules', {'min_event_duration': 4, 'max_event_duration': 6, 'setup_time_hours': 2, 'cleanup_time_hours': 1}) %}

                <!-- 1. Business Operating Hours -->
                <div class="settings-card-minimal" style="margin-top: 1.5rem; padding: 1.5rem; border: 1px solid #e2e8f0; border-radius: 8px;">
                    <h4 style="margin-top:0; color: #1e293b;"><i class="fas fa-store"></i> General Business Hours</h4>
                    <p class="field-hint">When does your business generally operate and accept communications?</p>
                    <div class="form-row-two-col" style="margin-top: 1rem;">
                        <div class="form-group">
                            <label>Opening Time</label>
                            <input type="time" name="business_hours_open_time" value="{{ bh.open_time }}">
                        </div>
                        <div class="form-group">
                            <label>Closing Time</label>
                            <input type="time" name="business_hours_close_time" value="{{ bh.close_time }}">
                        </div>
                    </div>
                </div>

                <!-- 2. Food Order Scheduling -->
                <div class="settings-card-minimal" style="margin-top: 1.5rem; padding: 1.5rem; border: 1px solid #e2e8f0; border-radius: 8px;">
                    <h4 style="margin-top:0; color: #1e293b;"><i class="fas fa-utensils"></i> Food Order Scheduling</h4>
                    <div class="form-row-two-col" style="margin-top: 1rem;">
                        <div class="form-group">
                            <label>Delivery Start Time</label>
                            <input type="time" name="food_delivery_start" value="{{ fr.delivery_start }}">
                        </div>
                        <div class="form-group">
                            <label>Delivery End Time</label>
                            <input type="time" name="food_delivery_end" value="{{ fr.delivery_end }}">
                        </div>
                    </div>
                    <div class="form-row-two-col">
                        <div class="form-group">
                            <label>Preparation Lead Time (Hours)</label>
                            <input type="number" name="food_lead_time_hours" value="{{ fr.lead_time_hours }}" min="0">
                        </div>
                        <div class="form-group" style="display:flex; align-items:flex-end;">
                            <label class="toggle-switch" style="margin-bottom: 10px;">
                                <input type="checkbox" name="food_allow_same_day" {% if fr.allow_same_day %}checked{% endif %}>
                                <span class="toggle-slider"></span>
                                <span style="margin-left: 50px; font-weight: 600;">Allow Same-Day Orders</span>
                            </label>
                        </div>
                    </div>
                </div>

                <!-- 3. Equipment Rental Scheduling -->
                <div class="settings-card-minimal" style="margin-top: 1.5rem; padding: 1.5rem; border: 1px solid #e2e8f0; border-radius: 8px;">
                    <h4 style="margin-top:0; color: #1e293b;"><i class="fas fa-box-open"></i> Equipment Rental Scheduling</h4>
                    <div class="form-row-two-col" style="margin-top: 1rem;">
                        <div class="form-group">
                            <label>Allowed Pickup Start</label>
                            <input type="time" name="equipment_pickup_start" value="{{ er.pickup_start }}">
                        </div>
                        <div class="form-group">
                            <label>Allowed Pickup End</label>
                            <input type="time" name="equipment_pickup_end" value="{{ er.pickup_end }}">
                        </div>
                    </div>
                    <div class="form-row-two-col">
                        <div class="form-group">
                            <label>Min Rental Duration (Hours)</label>
                            <input type="number" name="equipment_min_rental" value="{{ er.min_rental_hours }}" min="1">
                        </div>
                        <div class="form-group">
                            <label>Max Rental Duration (Hours)</label>
                            <input type="number" name="equipment_max_rental" value="{{ er.max_rental_hours }}" min="1">
                        </div>
                    </div>
                </div>

                <!-- 4. Service Booking Scheduling -->
                <div class="settings-card-minimal" style="margin-top: 1.5rem; padding: 1.5rem; border: 1px solid #e2e8f0; border-radius: 8px;">
                    <h4 style="margin-top:0; color: #1e293b;"><i class="fas fa-user-tie"></i> Service Staff Scheduling</h4>
                    <div class="form-row-two-col" style="margin-top: 1rem;">
                        <div class="form-group">
                            <label>Earliest Service Start</label>
                            <input type="time" name="service_earliest_start" value="{{ sr.earliest_start }}">
                        </div>
                        <div class="form-group">
                            <label>Latest Service End</label>
                            <input type="time" name="service_latest_end" value="{{ sr.latest_end }}">
                        </div>
                    </div>
                    <div class="form-row-two-col">
                        <div class="form-group">
                            <label>Min Duration (Hours)</label>
                            <input type="number" name="service_min_duration" value="{{ sr.min_duration_hours }}" min="1">
                        </div>
                        <div class="form-group">
                            <label>Max Duration (Hours)</label>
                            <input type="number" name="service_max_duration" value="{{ sr.max_duration_hours }}" min="1">
                        </div>
                    </div>
                </div>

                <!-- 5. Package Booking Scheduling -->
                <div class="settings-card-minimal" style="margin-top: 1.5rem; padding: 1.5rem; border: 1px solid #e2e8f0; border-radius: 8px;">
                    <h4 style="margin-top:0; color: #1e293b;"><i class="fas fa-gift"></i> Package Event Scheduling</h4>
                    <div class="form-row-two-col" style="margin-top: 1rem;">
                        <div class="form-group">
                            <label>Min Event Duration (Hours)</label>
                            <input type="number" name="package_min_duration" value="{{ pr.min_event_duration }}" min="1">
                        </div>
                        <div class="form-group">
                            <label>Max Event Duration (Hours)</label>
                            <input type="number" name="package_max_duration" value="{{ pr.max_event_duration }}" min="1">
                        </div>
                    </div>
                    <div class="form-row-two-col">
                        <div class="form-group">
                            <label>Setup Time Needed (Hours Before)</label>
                            <input type="number" name="package_setup_time" value="{{ pr.setup_time_hours }}" min="0">
                        </div>
                        <div class="form-group">
                            <label>Cleanup Time Needed (Hours After)</label>
                            <input type="number" name="package_cleanup_time" value="{{ pr.cleanup_time_hours }}" min="0">
                        </div>
                    </div>
                </div>

            </div>
            <!-- End Section: Booking & Availability -->
"""

if "<!-- Section: Booking & Availability -->" not in content:
    content = content.replace("<!-- End Section: Booking Policies -->", "<!-- End Section: Booking Policies -->\n" + new_html)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Success")
else:
    print("Already added")
