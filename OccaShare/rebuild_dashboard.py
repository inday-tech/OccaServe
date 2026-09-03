import re

with open('templates/caterer/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

new_html = '''
{% extends "caterer/layout.html" %}

{% block title %}Operations Dashboard{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', path='/css/caterer/index.css') }}?v=11.0">
<link href="https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.css" rel="stylesheet" />
<style>
    /* Mini Calendar overrides */
    #miniCalendar .fc-header-toolbar { padding: 0.5rem; margin-bottom: 0; font-size: 0.85rem; }
    #miniCalendar .fc-toolbar-title { font-size: 1rem !important; }
    #miniCalendar .fc-daygrid-day-number { font-size: 0.75rem; color: #475569; padding: 2px !important; }
    #miniCalendar .fc-daygrid-day-events { display: none; }
    #miniCalendar .fc-day-today { background: #f0fdf4 !important; }
    #miniCalendar .fc-highlight { background: var(--primary-color) !important; opacity: 0.1; }
    .fc-theme-standard td, .fc-theme-standard th { border-color: #f1f5f9; }
</style>
{% endblock %}

{% block content %}
<!-- Page Header -->
<div class="dash-header">
    <div class="dash-title">
        <h1>Overview</h1>
        <p>Good afternoon, {{ user.first_name }}. Here's what needs your attention today.</p>
    </div>
    <div class="dash-actions">
        <a href="/caterer/calendar" class="btn-secondary-action">
            <i class="fas fa-calendar-plus"></i> Add Schedule
        </a>
        <a href="/caterer/bookings?new=walkin" class="btn-primary-action">
            <i class="fas fa-user-plus"></i> Walk-in Booking
        </a>
    </div>
</div>

<div class="dash-grid">
    <!-- NEW KPI Section -->
    <div class="kpi-grid-clean" style="grid-column: span 12; margin-bottom: 0;">
        <div class="kpi-card-clean">
            <div class="kpi-info">
                <h4>Today's Events</h4>
                <span class="kpi-value">{{ today_events_count }}</span>
                <span class="trend-badge" style="background:#e0f2fe; color:#0369a1;"><i class="fas fa-calendar-day"></i> Today</span>
            </div>
        </div>
        <div class="kpi-card-clean">
            <div class="kpi-info">
                <h4>Upcoming Events</h4>
                <span class="kpi-value">{{ upcoming_events_count }}</span>
                <span class="trend-badge" style="background:#f3e8ff; color:#7e22ce;"><i class="fas fa-calendar-alt"></i> Next 30 days</span>
            </div>
        </div>
        <div class="kpi-card-clean">
            <div class="kpi-info">
                <h4>Outstanding Balance</h4>
                <span class="kpi-value">?{{ "{:,.2f}".format(outstanding_balance) }}</span>
                <span class="trend-badge" style="background:#fef3c7; color:#b45309;"><i class="fas fa-money-bill-wave"></i> {{ outstanding_count }} bookings</span>
            </div>
        </div>
        <div class="kpi-card-clean">
            <div class="kpi-info">
                <h4>Action Required</h4>
                <span class="kpi-value">{{ action_required_count }}</span>
                <span class="trend-badge" style="background:#fee2e2; color:#b91c1c;"><i class="fas fa-exclamation-circle"></i> Needs attention</span>
            </div>
        </div>
    </div>

    <!-- Main Content Left -->
    <div class="col-main">
        
        <!-- Action Center -->
        <div class="dash-card">
            <div class="card-header">
                <h3 class="card-title"><i class="fas fa-bolt" style="color:#eab308; margin-right:6px;"></i> Action Center</h3>
            </div>
            <div class="action-list" style="padding: 0.5rem 0;">
                {% if action_center_items %}
                    {% for item in action_center_items %}
                    <a href="/caterer/bookings" class="list-item" style="border-left: 4px solid {{ '#ef4444' if item.type == 'urgent' else '#f59e0b' }};">
                        <div class="list-item-content">
                            <h4 style="color: {{ '#ef4444' if item.type == 'urgent' else '#b45309' }};">
                                <i class="fas {{ item.icon }}" style="margin-right:6px;"></i> {{ item.title }}
                            </h4>
                            <p>{{ item.desc }}</p>
                        </div>
                        <i class="fas fa-chevron-right" style="color:#cbd5e1; font-size:0.8rem;"></i>
                    </a>
                    {% endfor %}
                {% else %}
                    <div class="empty-state" style="padding: 2rem;">
                        <i class="fas fa-check-circle" style="font-size:2rem; color:#10b981; margin-bottom:1rem;"></i>
                        <br>You're all caught up! No urgent actions required.
                    </div>
                {% endif %}
            </div>
        </div>

        <!-- Schedule & Mini Calendar Wrapper -->
        <div style="display: grid; grid-template-columns: 1.5fr 1fr; gap: 1.5rem; align-items: start;">
            
            <!-- Today's Schedule -->
            <div class="dash-card" style="margin-bottom:0;">
                <div class="card-header">
                    <h3 class="card-title">Today's Schedule</h3>
                </div>
                <div class="action-list" style="padding: 0.5rem 0; min-height: 250px;">
                    {% if today_schedule %}
                        {% for event in today_schedule %}
                        <div class="list-item" style="align-items: flex-start; cursor: default;">
                            <div style="min-width: 65px; text-align: right; margin-right: 1rem; color: #475569; font-weight: 600; font-size: 0.85rem; margin-top: 2px;">
                                {{ event.event_time.strftime('%I:%M %p') if event.event_time else 'TBD' }}
                            </div>
                            <div class="list-item-content">
                                <h4>{{ event.package.name if event.package else event.event_type }}</h4>
                                <p>{{ event.user.first_name ~ ' ' ~ event.user.last_name if event.user else 'Walk-in' }} &bull; {{ event.guest_count }} pax</p>
                            </div>
                        </div>
                        {% endfor %}
                    {% else %}
                        <div class="empty-state" style="padding: 3rem 1rem;">No events scheduled for today.</div>
                    {% endif %}
                </div>
                <div class="card-footer" style="padding: 1rem; border-top: 1px solid #f1f5f9; text-align: center;">
                    <a href="/caterer/calendar" style="color: var(--primary-color); font-weight: 600; font-size: 0.85rem; text-decoration: none;">View Full Calendar <i class="fas fa-arrow-right" style="margin-left:4px;"></i></a>
                </div>
            </div>

            <!-- Mini Calendar -->
            <div class="dash-card" style="margin-bottom:0;">
                <div class="card-body" style="padding: 0.5rem;">
                    <div id="miniCalendar"></div>
                </div>
            </div>
            
        </div>
        
        <!-- Upcoming Deadlines -->
        <div class="dash-card" style="margin-top: 1.5rem;">
            <div class="card-header">
                <h3 class="card-title">Upcoming Workload & Deadlines</h3>
            </div>
            <div class="table-container">
                <table class="bookings-list-table">
                    <thead>
                        <tr>
                            <th>Deadline / Event Date</th>
                            <th>Customer</th>
                            <th>Event Type</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for b in upcoming_events %}
                        <tr class="booking-row-item" onclick="window.location.href='/caterer/bookings'" style="cursor: pointer;">
                            <td data-label="Date">
                                <span style="font-weight: 700; color: #0f172a;">{{ b.event_date.strftime('%b %d, %Y') if b.event_date else 'TBD' }}</span>
                            </td>
                            <td data-label="Customer">
                                <span style="font-weight: 600; color: #334155;">{{ b.user.first_name ~ ' ' ~ b.user.last_name if b.user else 'Walk-in' }}</span>
                            </td>
                            <td data-label="Event Type">{{ b.package.name if b.package else b.event_type }}</td>
                            <td data-label="Status">
                                <span class="premium-status-badge ps-badge-pending">
                                    <i class="fas fa-clock"></i> {{ b.status|title|replace('_', ' ') }}
                                </span>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="4" class="empty-state">No upcoming deadlines within this view.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    <!-- Main Content Right -->
    <div class="col-side">
        
        <!-- Business Performance -->
        <div class="dash-card">
            <div class="card-header" style="border-bottom: 1px solid #f1f5f9;">
                <h3 class="card-title">Business Performance</h3>
            </div>
            
            <div class="action-list" style="padding-top: 0;">
                <div class="list-item" style="cursor: default;">
                    <div class="list-item-content">
                        <p style="margin-bottom: 2px;">Total Revenue Collected</p>
                        <h4 style="font-size: 1.1rem; color: #0f172a;">?{{ "{:,.2f}".format(total_revenue) }}</h4>
                    </div>
                </div>
                <div class="list-item" style="cursor: default;">
                    <div class="list-item-content">
                        <p style="margin-bottom: 2px;">Total Bookings</p>
                        <h4 style="font-size: 1.1rem; color: #0f172a;">{{ active_bookings }} Active</h4>
                    </div>
                </div>
                <div class="list-item" style="cursor: default;">
                    <div class="list-item-content">
                        <p style="margin-bottom: 2px;">Average ROI</p>
                        <h4 style="font-size: 1.1rem; color: #10b981;">{{ roi_percentage }}%</h4>
                    </div>
                </div>
            </div>
            
            <div class="card-body" style="padding-top: 0; padding-bottom: 1.5rem;">
                <h5 style="margin-bottom: 0.75rem; font-size: 0.8rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Booking Activity</h5>
                <div class="chart-box" style="height: 200px;">
                    <canvas id="bookingsChart"></canvas>
                </div>
            </div>
        </div>
        
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.js"></script>
<script>
    const chartDataRaw = {{ chart_data | tojson | safe }};
    const bookingsDataRaw = {{ bookings_chart_data | tojson | safe }};
    
    // Mini Calendar Init
    document.addEventListener('DOMContentLoaded', function() {
        var calendarEl = document.getElementById('miniCalendar');
        if (calendarEl) {
            var calendar = new FullCalendar.Calendar(calendarEl, {
                initialView: 'dayGridMonth',
                headerToolbar: {
                    left: 'title',
                    right: 'prev,next'
                },
                height: 'auto',
                contentHeight: 250,
                fixedWeekCount: false,
                showNonCurrentDates: false,
                selectable: true,
                dateClick: function(info) {
                    window.location.href = '/caterer/calendar?date=' + info.dateStr;
                }
            });
            calendar.render();
        }
        
        // Render Bookings Chart (Workload representation)
        const bCtx = document.getElementById('bookingsChart');
        if (bCtx && bookingsDataRaw && bookingsDataRaw.length > 0) {
            new Chart(bCtx, {
                type: 'bar',
                data: {
                    labels: bookingsDataRaw.map(d => d.label),
                    datasets: [
                        {
                            label: 'Completed',
                            data: bookingsDataRaw.map(d => d.completed),
                            backgroundColor: '#10b981',
                            borderRadius: 4
                        },
                        {
                            label: 'Pending/Active',
                            data: bookingsDataRaw.map(d => d.pending),
                            backgroundColor: '#eab308',
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { stepSize: 1 }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }
    });
</script>
{% endblock %}
'''

with open('templates/caterer/index.html', 'w', encoding='utf-8') as f:
    f.write(new_html)
print("Rebuilt index.html")
