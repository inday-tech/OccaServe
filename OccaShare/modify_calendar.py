import re

with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Header and Legend
new_header = '''
<!-- Page Header -->
<div class="page-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
    <div class="header-title-group">
        <h1>Service Calendar</h1>
        <p>Manage bookings, preparation, availability, and your business schedule.</p>
    </div>
    <div style="display: flex; gap: 10px;">
        <button onclick="openManualBookingModal()" class="btn-secondary-pro" title="Add a new walk-in booking">
            <i class="fas fa-user-plus"></i> Walk-in Booking
        </button>
        <button onclick="openAddScheduleModal()" class="btn-primary-pro" title="Add Internal Schedule">
            <i class="fas fa-calendar-plus"></i> Add Schedule
        </button>
    </div>
</div>

<!-- Record Type Filters -->
<div class="cal-card cal-legend-bar" style="padding: 10px 15px; margin-bottom: 15px; display: flex; gap: 10px; overflow-x: auto;">
    <button class="filter-btn active" data-filter="all">All</button>
    <button class="filter-btn" data-filter="booking"><span class="pill-dot" style="background:#10b981;"></span> Bookings</button>
    <button class="filter-btn" data-filter="preparation"><span class="pill-dot" style="background:#0ea5e9;"></span> Preparation</button>
    <button class="filter-btn" data-filter="task"><span class="pill-dot" style="background:#8b5cf6;"></span> Tasks</button>
    <button class="filter-btn" data-filter="reminder"><span class="pill-dot" style="background:#f59e0b;"></span> Reminders</button>
    <button class="filter-btn" data-filter="blocked"><span class="pill-dot" style="background:#ef4444;"></span> Blocked</button>
</div>
'''

content = re.sub(r'<!-- Page Header -->[\s\S]*?<!-- Main Content Grid -->', new_header + '\n<!-- Main Content Grid -->', content)

# Replace right sidebar
new_sidebar = '''
        <!-- Right: Sidebar -->
        <div class="cal-sidebar">
            
            <!-- Selected Day Information -->
            <div class="cal-card" id="selectedDayPanel">
                <div class="cal-section-header" style="background: #f8fafc; padding: 1rem; border-bottom: 1px solid #e2e8f0; border-radius: 8px 8px 0 0;">
                    <div style="text-transform: uppercase; font-size: 0.75rem; font-weight: 700; color: #64748b; letter-spacing: 0.05em; margin-bottom: 4px;">Selected Date</div>
                    <h3 id="sidebarSelectedDateStr" style="font-size: 1.25rem; color: #0f172a; margin: 0;">Today</h3>
                </div>
                
                <div class="cal-section-body" style="padding: 0;">
                    <!-- Today's Schedule -->
                    <div style="padding: 1rem; border-bottom: 1px solid #f1f5f9;">
                        <h4 style="font-size: 0.85rem; color: #475569; margin-bottom: 1rem; font-weight: 700;">Day's Schedule</h4>
                        <div id="sidebarDayEvents" style="display: flex; flex-direction: column; gap: 10px; min-height: 100px;">
                            <div class="empty-state" style="padding: 1rem; font-size: 0.85rem;">Select a date to view schedule.</div>
                        </div>
                    </div>
                    
                    <!-- Availability -->
                    <div style="padding: 1rem; background: #fafafa; border-radius: 0 0 8px 8px;">
                        <h4 style="font-size: 0.85rem; color: #475569; margin-bottom: 0.5rem; font-weight: 700;">Availability</h4>
                        <div id="sidebarAvailabilityStatus" style="font-size: 0.9rem; font-weight: 600; color: #10b981; margin-bottom: 1rem;">
                            <i class="fas fa-check-circle"></i> Available
                        </div>
                        <button onclick="document.getElementById('availabilitySettingsModal').style.display='flex'" class="btn-secondary-pro" style="width: 100%; justify-content: center; font-size: 0.8rem; padding: 6px;">Manage Availability & Settings</button>
                    </div>
                </div>
            </div>
            
            <!-- Upcoming Deadlines (Fallback/extra info) -->
            <div class="cal-card">
                <div class="cal-section-header">
                    <i class="fas fa-clock"></i>
                    <h3>Upcoming Bookings</h3>
                </div>
                <div class="cal-tracker-list" style="max-height: 300px; overflow-y: auto;">
                    <!-- Original logic stays here, but simplified -->
                    {% if bookings %}
                        {% for booking in bookings %}
                        <div class="weekly-event-card type-{{ booking.event_type.lower().split(' ')[0] if booking.event_type else 'other' }}"
                            data-id="{{ booking.id }}"
                            data-customer="{{ (booking.user.first_name ~ ' ' ~ booking.user.last_name) if booking.user else (booking.customer_name or 'Walk-in') }}"
                            data-type="{{ booking.event_type or 'Food Order' }}" data-title="{{ booking.event_name or (booking.user.first_name if booking.user else 'Order') }}"
                            data-datetime="{{ booking.event_date.strftime('%A, %B %d, %Y') }} at {{ booking.event_time.strftime('%I:%M %p') if booking.event_time else 'TBD' }}"
                            data-venue="{{ booking.venue_address or 'TBD' }}"
                            data-package="{{ booking.guest_count }} Guests - {{ booking.package.name if booking.package else 'Ala Carte' }}"
                            data-booking-source="{{ booking.booking_source or '' }}"
                            data-is-food-order="{{ 'true' if (booking.venue_address == 'PICKUP' or (not booking.event_type)) else 'false' }}"
                            data-payment-status="{{ booking.payment_status or 'pending' }}"
                            data-booking-status="{{ booking.status or 'pending' }}"
                            data-prep-status="{{ booking.preparation_status or 'not_started' }}"
                            data-prep-date="{{ booking.preparation_date.strftime('%B %d, %Y') if booking.preparation_date else 'TBD' }}"
                            data-total="{{ booking.total_price or booking.total_amount or 0 }}"
                            data-paid="{{ booking.amount_paid or 0 }}"
                            data-email="{{ booking.user.email if booking.user else (booking.customer_email or 'N/A') }}"
                            data-phone="{{ booking.user.phone_number if booking.user else (booking.customer_contact or 'N/A') }}"
                            data-fulfillment="{{ 'Pickup at Caterer' if booking.venue_address == 'PICKUP' else 'Delivery' }}"
                            onclick="openSidebarEventModal(this)">
                            
                            <div class="weekly-event-date">
                                <span>{{ booking.event_date.strftime('%b') }}</span>
                                <span>{{ booking.event_date.strftime('%d') }}</span>
                            </div>
                            <div class="weekly-event-info">
                                <h4>{{ booking.package.name if booking.package else booking.event_type }}</h4>
                                <p>{{ (booking.user.first_name ~ ' ' ~ booking.user.last_name) if booking.user else 'Walk-in' }}</p>
                                <span class="status-badge status-{{ booking.status }}">{{ booking.status|title|replace('_', ' ') }}</span>
                            </div>
                        </div>
                        {% endfor %}
                    {% else %}
                        <div class="empty-state">No upcoming bookings.</div>
                    {% endif %}
                </div>
            </div>
        </div>
'''

content = re.sub(r'<!-- Right: Sidebar -->[\s\S]*?(?=<!-- Calendar Event Details Modal -->)', new_sidebar + '\n', content)

with open('templates/caterer/calendar.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated calendar.html structure")
