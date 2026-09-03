import re

with open('templates/caterer/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Business Performance to remove ROI and use Completed Events
replacement_bp = '''
        <!-- Business Performance -->
        <div class="dash-card">
            <div class="card-header" style="border-bottom: 1px solid #f1f5f9;">
                <h3 class="card-title">Business Performance</h3>
            </div>
            
            <div class="action-list" style="padding-top: 0; padding-bottom: 1rem;">
                <div class="list-item" style="cursor: default; padding: 0.75rem 1rem;">
                    <div class="list-item-content">
                        <p style="margin-bottom: 2px;">Total Revenue Collected</p>
                        <h4 style="font-size: 1.1rem; color: #0f172a;">?{{ "{:,.2f}".format(total_revenue) }}</h4>
                    </div>
                </div>
                <div class="list-item" style="cursor: default; padding: 0.75rem 1rem;">
                    <div class="list-item-content">
                        <p style="margin-bottom: 2px;">Active Bookings</p>
                        <h4 style="font-size: 1.1rem; color: #0f172a;">{{ active_bookings }} Active</h4>
                    </div>
                </div>
                <div class="list-item" style="cursor: default; padding: 0.75rem 1rem;">
                    <div class="list-item-content">
                        <p style="margin-bottom: 2px;">Completed Events</p>
                        <h4 style="font-size: 1.1rem; color: #10b981;">{{ bookings_chart_data | sum(attribute='completed') }} Completed</h4>
                    </div>
                </div>
            </div>
            
            <div class="card-body" style="padding: 0 1rem 1.5rem 1rem;">
                <h5 style="margin-bottom: 1rem; font-size: 0.8rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Workload Trend (Events)</h5>
                <div class="chart-box" style="height: 220px; width: 100%;">
                    <canvas id="bookingsChart"></canvas>
                </div>
            </div>
        </div>
'''
content = re.sub(
    r'<!-- Business Performance -->[\s\S]*?(?=</div>\s*</div>\s*{% endblock %})',
    replacement_bp.strip() + '\n    ',
    content
)

# 2. Add dots to the Mini Calendar in JS
replacement_js = '''
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
                contentHeight: 300,
                fixedWeekCount: false,
                showNonCurrentDates: false,
                selectable: true,
                events: '/caterer/api/events', // Fetch events so dots can appear
                eventDisplay: 'list-item', // Display as dots
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
                type: 'bar', // Better chart for events workload
                data: {
                    labels: bookingsDataRaw.map(d => d.label),
                    datasets: [
                        {
                            label: 'Completed Events',
                            data: bookingsDataRaw.map(d => d.completed),
                            backgroundColor: '#10b981',
                            borderRadius: 4,
                            barPercentage: 0.6
                        },
                        {
                            label: 'Active/Pending',
                            data: bookingsDataRaw.map(d => d.pending),
                            backgroundColor: '#3b82f6',
                            borderRadius: 4,
                            barPercentage: 0.6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { 
                            display: true,
                            position: 'bottom',
                            labels: {
                                usePointStyle: true,
                                boxWidth: 8
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { stepSize: 1, precision: 0 },
                            grid: { color: '#f1f5f9' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }
    });
'''
content = re.sub(
    r'// Mini Calendar Init[\s\S]*?(?=</script>)',
    replacement_js.strip() + '\n',
    content
)

# 3. Enhance alignment and styles in the template head
style_injection = '''
<style>
    /* Dashboard Grid Adjustments for perfect alignment */
    .dash-grid {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 1.5rem;
        align-items: start;
    }
    .col-main {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }
    .col-side {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }
    .kpi-grid-clean {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
    }
    
    /* Ensure cards take full height where applicable */
    .dash-card {
        height: 100%;
        display: flex;
        flex-direction: column;
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
        overflow: hidden;
    }
    .dash-card .action-list {
        flex: 1;
    }
    
    /* Mini Calendar overrides for Dots */
    #miniCalendar .fc-header-toolbar { padding: 0.75rem; margin-bottom: 0; font-size: 0.9rem; }
    #miniCalendar .fc-toolbar-title { font-size: 1.1rem !important; font-weight: 700; color: #1e293b; }
    #miniCalendar .fc-daygrid-day-number { font-size: 0.8rem; color: #475569; padding: 4px !important; font-weight: 500; }
    #miniCalendar .fc-day-today { background: #f0fdf4 !important; }
    #miniCalendar .fc-day-today .fc-daygrid-day-number { color: #10b981; font-weight: 800; }
    
    /* Style the dots */
    #miniCalendar .fc-daygrid-event-harness { margin-top: 1px; }
    #miniCalendar .fc-event { border: none !important; background: transparent !important; }
    #miniCalendar .fc-list-event-dot { border-color: var(--primary-color); display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin: 0 auto; }
    #miniCalendar .fc-daygrid-day-events { display: flex; flex-wrap: wrap; gap: 2px; justify-content: center; margin-top: 2px; }
    #miniCalendar .fc-daygrid-event { display: block; font-size: 0; padding: 0; }
    #miniCalendar .fc-event-title { display: none; }
    #miniCalendar .fc-event-time { display: none; }
</style>
'''
content = re.sub(
    r'<style>\s*/\*\s*Mini Calendar overrides\s*\*/[\s\S]*?</style>',
    style_injection.strip(),
    content
)

# 4. Remove inline styles that break flex flow (margin-bottom:0, etc)
content = content.replace('style="margin-bottom:0;"', '')
content = content.replace('style="margin-top: 1.5rem;"', '')

with open('templates/caterer/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated index.html UI.")
