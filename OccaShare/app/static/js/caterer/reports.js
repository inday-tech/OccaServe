/**
 * Business Reports - Revenue Chart Implementation
 * Uses Chart.js to visualize revenue over time
 */

function initRevenueChart(rawBookings) {
    if (!rawBookings || rawBookings.length === 0) {
        renderEmptyChart();
        return;
    }

    // Aggregate revenue by month
    const revenueByMonth = {};
    rawBookings.forEach(b => {
        if (!revenueByMonth[b.date]) revenueByMonth[b.date] = 0;
        revenueByMonth[b.date] += parseFloat(b.revenue || 0);
    });

    // Ensure we at least have months to show, sort chronologically
    let labels = Object.keys(revenueByMonth).sort();
    let dataRevenue = labels.map(l => revenueByMonth[l]);

    if (labels.length === 0) {
        renderEmptyChart();
        return;
    }

    // Render Chart
    const canvas = document.getElementById('revenueChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(79, 70, 229, 0.4)');
    gradient.addColorStop(1, 'rgba(79, 70, 229, 0.0)');

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Gross Revenue (₱)',
                data: dataRevenue,
                borderColor: '#4f46e5',
                backgroundColor: gradient,
                borderWidth: 3,
                pointBackgroundColor: '#ffffff',
                pointBorderColor: '#4f46e5',
                pointBorderWidth: 2,
                pointRadius: 5,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            let value = context.parsed.y;
                            return '₱' + value.toLocaleString(undefined, { minimumFractionDigits: 2 });
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function (value) {
                            return '₱' + value.toLocaleString();
                        }
                    }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

function renderEmptyChart() {
    const canvas = document.getElementById('revenueChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['No Data Available'],
            datasets: [{
                label: 'Gross Revenue (₱)',
                data: [0],
                borderColor: '#cbd5e1',
                borderDash: [5, 5],
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true },
                x: { grid: { display: false } }
            }
        }
    });
}
