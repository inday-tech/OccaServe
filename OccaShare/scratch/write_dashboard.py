import os

html_content = """{% extends "caterer/layout.html" %}

{% block title %}Operations Dashboard{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', path='/css/caterer/index.css') }}?v=7.0">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
<style>
    :root {
        --chart-profit: #10b981;
        --chart-expenses: #ef4444;
        --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    .dashboard-grid {
        display: grid;
        grid-template-columns: repeat(12, 1fr);
        gap: 20px;
        margin-top: 20px;
    }
    
    .card {
        background: white;
        border-radius: 12px;
        box-shadow: var(--card-shadow);
        padding: 20px;
        border: 1px solid #e2e8f0;
    }
    
    .card-title {
        font-size: 1rem;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Summary Cards */
    .summary-section { grid-column: span 12; display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
    .stat-card {
        background: white; border-radius: 12px; padding: 20px;
        border: 1px solid #e2e8f0; border-left: 4px solid var(--primary-color);
        display: flex; flex-direction: column; gap: 8px;
    }
    .stat-title { font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-value { font-size: 1.8rem; font-weight: 700; color: #0f172a; }
    .stat-desc { font-size: 0.8rem; color: #94a3b8; }
    
    /* Quick Actions */
    .quick-actions { grid-column: span 12; display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px; }
    .action-btn { 
        padding: 10px 16px; background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 8px; color: #334155; font-weight: 600; cursor: pointer;
        display: flex; align-items: center; gap: 8px; white-space: nowrap; transition: 0.2s;
    }
    .action-btn:hover { background: var(--primary-color); color: white; border-color: var(--primary-color); }
    
    /* Main Layout */
    .col-left { grid-column: span 8; display: flex; flex-direction: column; gap: 20px; }
    .col-right { grid-column: span 4; display: flex; flex-direction: column; gap: 20px; }
    
    /* Pending Actions */
    .action-item {
        display: flex; justify-content: space-between; align-items: center;
        padding: 12px 15px; background: #f8fafc; border-radius: 8px; margin-bottom: 10px; cursor: pointer; transition: 0.2s;
    }
    .action-item:hover { background: #f1f5f9; transform: translateX(5px); }
    .action-badge { 
        background: #ef4444; color: white; font-size: 0.75rem; font-weight: 700;
        padding: 2px 8px; border-radius: 20px;
    }
    
    /* Operations Tracker */
    .checklist-item {
        display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px dashed #e2e8f0;
    }
    .checklist-item input[type="checkbox"] { width: 18px; height: 18px; accent-color: var(--primary-color); cursor: pointer; }
    
    /* Today's Schedule */
    .schedule-item {
        display: flex; gap: 15px; padding: 15px 0; border-bottom: 1px solid #e2e8f0;
    }
    .schedule-time { font-weight: 700; color: var(--primary-color); width: 80px; flex-shrink: 0; }
    .schedule-details h4 { margin: 0 0 5px 0; font-size: 1rem; color: #0f172a; }
    .schedule-details p { margin: 0; font-size: 0.85rem; color: #64748b; }
    
    @media (max-width: 1024px) {
        .summary-section { grid-template-columns: repeat(2, 1fr); }
        .col-left, .col-right { grid-column: span 12; }
    }
    @media (max-width: 640px) {
        .summary-section { grid-template-columns: 1fr; }
    }
</style>
{% endblock %}

{% block content %}
<div class="page-header" style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
    <div>
        <h1>Operations Dashboard</h1>
        <p style="color: #64748b;">Welcome back, {{ user.first_name }}! Here's what needs your attention today.</p>
    </div>
</div>

<!-- SECTION 12: Quick Actions -->
<div class="quick-actions">
    <button class="action-btn" onclick="window.location.href='/caterer/bookings?new=walkin'"><i class="fas fa-plus"></i> Walk-in Booking</button>
    <button class="action-btn" onclick="window.location.href='/caterer/packages'"><i class="fas fa-box-open"></i> Add Package</button>
    <button class="action-btn" onclick="window.location.href='/caterer/profile'"><i class="fas fa-user"></i> Profile Settings</button>
</div>

<div class="dashboard-grid">
    <!-- SECTION 1: Business Summary Cards -->
    <div class="summary-section">
        <div class="stat-card">
            <span class="stat-title">Gross Revenue</span>
            <span class="stat-value">₱{{ "{:,.2f}".format(total_revenue) }}</span>
            <span class="stat-desc">Collected Payments</span>
        </div>
        <div class="stat-card" style="border-left-color: #10b981;">
            <span class="stat-title">Net Profit</span>
            <span class="stat-value">₱{{ "{:,.2f}".format(net_profit) }}</span>
            <span class="stat-desc">After Expenses</span>
        </div>
        <div class="stat-card" style="border-left-color: #f59e0b;">
            <span class="stat-title">Active Bookings</span>
            <span class="stat-value">{{ active_bookings }}</span>
            <span class="stat-desc">Currently Managed</span>
        </div>
        <div class="stat-card" style="border-left-color: #8b5cf6;">
            <span class="stat-title">Upcoming Events</span>
            <span class="stat-value">{{ upcoming_events_count }}</span>
            <span class="stat-desc">Next 7 Days</span>
        </div>
    </div>

    <!-- LEFT COLUMN -->
    <div class="col-left">
        <!-- SECTION 2: Pending Actions -->
        <div class="card">
            <h3 class="card-title"><i class="fas fa-exclamation-circle" style="color: #ef4444;"></i> Pending Actions</h3>
            {% if pending_actions.total > 0 %}
                {% if pending_actions.approvals > 0 %}
                <div class="action-item" onclick="window.location.href='/caterer/bookings'">
                    <div><i class="fas fa-file-signature" style="color: #f59e0b; width: 20px;"></i> Booking Approvals</div>
                    <span class="action-badge" style="background: #f59e0b;">{{ pending_actions.approvals }}</span>
                </div>
                {% endif %}
                {% if pending_actions.payments > 0 %}
                <div class="action-item" onclick="window.location.href='/caterer/bookings'">
                    <div><i class="fas fa-money-bill-wave" style="color: #10b981; width: 20px;"></i> Payment Verifications</div>
                    <span class="action-badge" style="background: #10b981;">{{ pending_actions.payments }}</span>
                </div>
                {% endif %}
                {% if pending_actions.identity > 0 %}
                <div class="action-item" onclick="window.location.href='/caterer/bookings'">
                    <div><i class="fas fa-id-card" style="color: #3b82f6; width: 20px;"></i> Identity Verification</div>
                    <span class="action-badge" style="background: #3b82f6;">{{ pending_actions.identity }}</span>
                </div>
                {% endif %}
                {% if pending_actions.contracts > 0 %}
                <div class="action-item" onclick="window.location.href='/caterer/bookings'">
                    <div><i class="fas fa-file-contract" style="color: #8b5cf6; width: 20px;"></i> Contracts Awaiting Signature</div>
                    <span class="action-badge" style="background: #8b5cf6;">{{ pending_actions.contracts }}</span>
                </div>
                {% endif %}
                {% if pending_actions.messages > 0 %}
                <div class="action-item" onclick="window.location.href='/caterer/chat'">
                    <div><i class="fas fa-comment-dots" style="color: #64748b; width: 20px;"></i> New Customer Messages</div>
                    <span class="action-badge" style="background: #64748b;">{{ pending_actions.messages }}</span>
                </div>
                {% endif %}
            {% else %}
                <p style="color: #64748b; font-size: 0.9rem;">You're all caught up! No pending actions.</p>
            {% endif %}
        </div>

        <!-- SECTION 7 & 8: Charts -->
        <div class="card">
            <h3 class="card-title"><i class="fas fa-chart-line"></i> Performance Trends</h3>
            <div style="display: flex; gap: 20px; height: 300px;">
                <div style="flex: 1;"><canvas id="revenueChart"></canvas></div>
                <div style="flex: 1;"><canvas id="bookingsChart"></canvas></div>
            </div>
        </div>
        
        <!-- SECTION 6: Recent Bookings -->
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 class="card-title" style="margin:0;"><i class="fas fa-history"></i> Recent Bookings</h3>
                <a href="/caterer/bookings" style="font-size: 0.85rem; color: var(--primary-color); text-decoration: none; font-weight: 600;">View All</a>
            </div>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
                    <thead>
                        <tr style="border-bottom: 1px solid #e2e8f0; color: #64748b; text-align: left;">
                            <th style="padding: 10px 5px;">Customer Name</th>
                            <th style="padding: 10px 5px;">Booking Type</th>
                            <th style="padding: 10px 5px;">Event Date</th>
                            <th style="padding: 10px 5px;">Status</th>
                            <th style="padding: 10px 5px;">Total Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for b in recent_orders %}
                        <tr style="border-bottom: 1px solid #f1f5f9;">
                            <td style="padding: 12px 5px; font-weight: 600; color: #0f172a;">{{ b.user.first_name ~ ' ' ~ b.user.last_name if b.user else 'Walk-in Customer' }}</td>
                            <td style="padding: 12px 5px;">{{ b.package.name if b.package else b.event_type }}</td>
                            <td style="padding: 12px 5px;">{{ b.event_date.strftime('%B %d, %Y') if b.event_date else 'TBD' }}</td>
                            <td style="padding: 12px 5px;">
                                <span style="background: #e2e8f0; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem;">{{ b.status|title|replace('_', ' ') }}</span>
                            </td>
                            <td style="padding: 12px 5px; font-weight: 600;">₱{{ "{:,.2f}".format(b.total_amount or 0) }}</td>
                        </tr>
                        {% else %}
                        <tr><td colspan="5" style="text-align: center; padding: 20px; color: #94a3b8;">No recent bookings.</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- SECTION 9 & 10: Top Packages & Customers -->
        <div style="display: flex; gap: 20px;">
            <div class="card" style="flex: 1;">
                <h3 class="card-title"><i class="fas fa-star" style="color: #f59e0b;"></i> Top Packages</h3>
                {% for pkg in popular_packages %}
                <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f1f5f9;">
                    <div>
                        <div style="font-weight: 600; font-size: 0.9rem;">{{ pkg.name }}</div>
                        <div style="font-size: 0.8rem; color: #64748b;">{{ pkg.orders }} Bookings</div>
                    </div>
                </div>
                {% else %}
                <p style="color: #64748b; font-size: 0.85rem;">Not enough data yet.</p>
                {% endfor %}
            </div>
            
            <div class="card" style="flex: 1;">
                <h3 class="card-title"><i class="fas fa-users" style="color: var(--primary-color);"></i> Top Customers</h3>
                {% for cust in top_spenders %}
                <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f1f5f9;">
                    <div>
                        <div style="font-weight: 600; font-size: 0.9rem;">{{ cust.name }}</div>
                        <div style="font-size: 0.8rem; color: #64748b;">{{ cust.orders }} Bookings</div>
                    </div>
                    <div style="font-weight: 600; font-size: 0.9rem; color: var(--primary-color);">₱{{ "{:,.0f}".format(cust.spent) }}</div>
                </div>
                {% else %}
                <p style="color: #64748b; font-size: 0.85rem;">Not enough data yet.</p>
                {% endfor %}
            </div>
        </div>
    </div>

    <!-- RIGHT COLUMN -->
    <div class="col-right">
        <!-- SECTION 3: Today's Schedule -->
        <div class="card">
            <h3 class="card-title"><i class="fas fa-calendar-day" style="color: var(--primary-color);"></i> Today's Schedule</h3>
            <div class="schedule-list">
                {% for b in today_schedule %}
                <div class="schedule-item">
                    <div class="schedule-time">{{ b.event_time.strftime('%I:%M %p') if b.event_time else 'TBD' }}</div>
                    <div class="schedule-details">
                        <h4>{{ b.event_type }}</h4>
                        <p>{{ b.user.first_name ~ ' ' ~ b.user.last_name if b.user else 'Walk-in' }}</p>
                        <p><i class="fas fa-map-marker-alt"></i> {{ b.venue_address or 'No venue specified' }}</p>
                    </div>
                </div>
                {% else %}
                <p style="color: #64748b; font-size: 0.9rem; text-align: center; padding: 20px 0;">No events scheduled today.</p>
                {% endfor %}
            </div>
        </div>

        <!-- SECTION 4: Operations Tracker -->
        <div class="card">
            <h3 class="card-title"><i class="fas fa-tasks" style="color: #8b5cf6;"></i> Operations Tracker</h3>
            {% if upcoming_events|length > 0 %}
                {% set b = upcoming_events[0] %}
                <div style="margin-bottom: 10px; font-weight: 600; color: #0f172a;">{{ b.event_type }} ({{ b.event_date.strftime('%b %d') if b.event_date else '' }})</div>
                <div class="checklist-item"><input type="checkbox" {% if b.payment_status == 'paid' %}checked{% endif %} disabled> <span>Verify Payment</span></div>
                <div class="checklist-item"><input type="checkbox" {% if b.user and b.user.is_verified %}checked{% endif %} disabled> <span>Verify Customer Identity</span></div>
                <div class="checklist-item"><input type="checkbox" disabled> <span>Confirm Menu</span></div>
                <div class="checklist-item"><input type="checkbox" disabled> <span>Confirm Guest Count</span></div>
                <div class="checklist-item"><input type="checkbox" disabled> <span>Prepare Equipment</span></div>
                <div class="checklist-item"><input type="checkbox" disabled> <span>Assign Staff</span></div>
                <div class="checklist-item"><input type="checkbox" disabled> <span>Confirm Delivery Time</span></div>
                <div class="checklist-item"><input type="checkbox" {% if b.status == 'completed' %}checked{% endif %} disabled> <span>Event Completed</span></div>
                <a href="/caterer/bookings" style="display: block; margin-top: 15px; font-size: 0.85rem; color: var(--primary-color); text-align: center; text-decoration: none; font-weight: 600;">Manage Active Bookings</a>
            {% else %}
                <p style="color: #64748b; font-size: 0.9rem;">No active operations tracking needed right now.</p>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
    document.addEventListener("DOMContentLoaded", function() {
        const chartDataRaw = {{ chart_data | tojson | safe }};
        const bookingsChartRaw = {{ bookings_chart_data | tojson | safe }};
        
        const labels = chartDataRaw.map(d => d.label);
        const revenue = chartDataRaw.map(d => d.revenue);
        
        // Revenue Trend Chart
        new Chart(document.getElementById('revenueChart').getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Gross Revenue (₱)',
                    data: revenue,
                    borderColor: 'var(--primary-color)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { borderDash: [5, 5] } },
                    x: { grid: { display: false } }
                }
            }
        });

        // Booking Trend Chart
        const completedBookings = bookingsChartRaw.map(d => d.completed);
        const pendingBookings = bookingsChartRaw.map(d => d.pending);
        
        new Chart(document.getElementById('bookingsChart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Completed',
                        data: completedBookings,
                        backgroundColor: '#10b981',
                        borderRadius: 4
                    },
                    {
                        label: 'Pending',
                        data: pendingBookings,
                        backgroundColor: '#f59e0b',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top', labels: { boxWidth: 10 } } },
                scales: {
                    y: { beginAtZero: true, stacked: true },
                    x: { stacked: true, grid: { display: false } }
                }
            }
        });
        
        // Auto-refresh pending counts every 60 seconds (simulated)
        setTimeout(() => { location.reload(); }, 60000);
    });
</script>
{% endblock %}
"""

with open(r'c:\OccaServe\OccaShare\templates\caterer\index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Dashboard rewritten successfully!")
