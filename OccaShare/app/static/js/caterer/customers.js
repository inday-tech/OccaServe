/**
 * SECURE CUSTOMER DIRECTORY ENGINE
 * Lightweight, privacy-focused overview and export controller.
 * Detailed customer contact information remains exclusively accessible 
 * in Booking Details -> Customer Tab -> View Customer Details.
 */

document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const searchParam = urlParams.get('search');
    const globalSearchInput = document.getElementById('globalSearchInput');
    if (searchParam) {
        if (globalSearchInput) globalSearchInput.value = searchParam;
        window.filterCustomerTable(searchParam);
    }
});

// Hook into Global Search from Layout
window.addEventListener('globalSearch', function(e) {
    const query = (e.detail?.value || '').toLowerCase();
    window.filterCustomerTable(query);
});

// Action Menu Toggler (for Export Data dropdown)
window.toggleActionMenu = function(id) {
    const menus = document.querySelectorAll('.action-dropdown-menu');
    menus.forEach(menu => {
        if (menu.id !== `actionMenu-${id}`) menu.classList.remove('menu-open');
    });
    const targetMenu = document.getElementById(`actionMenu-${id}`);
    if (targetMenu) {
        targetMenu.classList.toggle('menu-open');
    }
};

// Close menus when clicking outside
document.addEventListener('click', function(e) {
    if (!e.target.closest('.action-dropdown-container')) {
        document.querySelectorAll('.action-dropdown-menu').forEach(m => m.classList.remove('menu-open'));
    }
});

window.filterCustomerTable = function(searchQuery = null) {
    const filterText = (typeof searchQuery === 'string') 
        ? searchQuery.toLowerCase() 
        : (document.getElementById('globalSearchInput') ? document.getElementById('globalSearchInput').value.toLowerCase() : '');
    
    const statusSelect = document.getElementById('tableFilterStatus');
    const statusFilter = statusSelect ? statusSelect.value : 'All';
    
    const rows = document.querySelectorAll('#customersTableBody .premium-row');
    let visibleCount = 0;
    
    rows.forEach(row => {
        const textContent = row.textContent.toLowerCase();
        const textMatch = filterText === '' || textContent.includes(filterText);
        
        let statusMatch = true;
        if (statusFilter !== 'All') {
            const badge = row.querySelector('.premium-status-badge');
            const rowStatus = badge ? badge.innerText.trim() : '';
            if (statusFilter === 'VIP Elite' && !rowStatus.includes('VIP')) statusMatch = false;
            if (statusFilter === 'Standard' && !rowStatus.includes('Standard')) statusMatch = false;
            if (statusFilter === 'Blacklisted' && !rowStatus.includes('Blacklisted')) statusMatch = false;
            if (statusFilter === 'New Client' && !rowStatus.includes('New Client')) statusMatch = false;
        }
        
        if (textMatch && statusMatch) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });

    const emptyState = document.getElementById('emptyStateRow');
    if (emptyState) {
        if (visibleCount === 0 && rows.length > 0) {
            emptyState.style.display = '';
            emptyState.querySelector('h4').innerText = "No Matches Found";
            emptyState.querySelector('p').innerText = "Try adjusting your search or filters.";
            const btn = emptyState.querySelector('button');
            if(btn) btn.style.display = 'none';
        } else if (rows.length === 0) {
            emptyState.style.display = '';
            emptyState.querySelector('h4').innerText = "No Customer Records Found";
            emptyState.querySelector('p').innerText = "Customers will automatically appear here once they book an event with you.";
            const btn = emptyState.querySelector('button');
            if(btn) btn.style.display = 'none';
        } else {
            emptyState.style.display = 'none';
        }
    }
};

window.exportCustomerCSV = function(format = 'csv') {
    const rows = document.querySelectorAll('#customersTableBody .premium-row');
    if (rows.length === 0) {
        if (window.showError) window.showError("No data to export.");
        return;
    }
    
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Client ID,Status,Total Spent,Bookings,Last Active\n";
    
    rows.forEach(row => {
        if (row.style.display === 'none') return;
        try {
            const cells = row.querySelectorAll('td');
            const id = cells[0].innerText.trim();
            const status = cells[1].innerText.trim();
            const spend = cells[2].innerText.replace('₱', '').replace(/,/g, '').trim();
            const bookings = cells[3].innerText.replace('events', '').replace('event', '').trim();
            const lastSeen = cells[4].innerText.trim();
            
            csvContent += `"${id}","${status}","₱${spend}","${bookings} events","${lastSeen}"\n`;
        } catch(e) {}
    });
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", format === 'excel' ? "customer_directory_summary.xls" : "customer_directory_summary.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    window.toggleActionMenu('export');
};

window.exportCustomerPDF = function() {
    window.toggleActionMenu('export');
    const rows = document.querySelectorAll('#customersTableBody .premium-row');
    if (rows.length === 0) {
        if (window.showError) window.showError("No data to export.");
        return;
    }

    let printHtml = `
    <html><head><title>Customer Directory Summary Report</title>
    <style>
        body { font-family: 'Poppins', sans-serif; padding: 2rem; color: #0f172a; }
        h2 { border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; margin-bottom: 1.5rem; }
        table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        th, td { border: 1px solid #e2e8f0; padding: 0.75rem; text-align: left; }
        th { background: #f8fafc; font-weight: 800; text-transform: uppercase; color: #64748b; }
        tr:nth-child(even) { background: #fcfcfd; }
    </style></head><body>
    <h2>OccaServe Caterer - Customer Directory Summary Report</h2>
    <table><thead><tr>
        <th>Client ID</th><th>Status</th><th>Total Spent</th><th>Bookings</th><th>Last Active</th>
    </tr></thead><tbody>`;

    rows.forEach(row => {
        if (row.style.display === 'none') return;
        try {
            const cells = row.querySelectorAll('td');
            const id = cells[0].innerText.trim();
            const status = cells[1].innerText.trim();
            const spend = cells[2].innerText.trim();
            const bookings = cells[3].innerText.trim();
            const lastActive = cells[4].innerText.trim();
            printHtml += `<tr><td>${id}</td><td>${status}</td><td>${spend}</td><td>${bookings}</td><td>${lastActive}</td></tr>`;
        } catch(e) {}
    });

    printHtml += `</tbody></table></body></html>`;
    const printWindow = window.open('', '_blank');
    printWindow.document.write(printHtml);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => { printWindow.print(); }, 500);
};
