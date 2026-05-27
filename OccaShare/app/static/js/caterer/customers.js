/**
 * PREMIUM CRM ENGINE v10.0
 * Fully inherits global UI context and dynamic functionality.
 */

const PSGC_BASE = 'https://psgc.gitlab.io/api';
let currentCustomerId = null;
let validationDebounceTimer = null;

document.addEventListener('DOMContentLoaded', function() {
    attachSmartRealtimeValidation();
    if(document.getElementById('regProv')) {
        window.loadProvinces('regProv');
    }
});

// Hook into Global Search from Layout
window.addEventListener('globalSearch', function(e) {
    const query = e.detail.value.toLowerCase();
    window.filterCustomerTable(query);
});

// Action Menu Toggler
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
    const filterText = (typeof searchQuery === 'string') ? searchQuery : (document.getElementById('globalSearchInput') ? document.getElementById('globalSearchInput').value.toLowerCase() : '');
    
    const statusSelect = document.getElementById('tableFilterStatus');
    const statusFilter = statusSelect ? statusSelect.value : 'All';
    
    const rows = document.querySelectorAll('#customersTableBody .table-row-pro');
    let visibleCount = 0;
    
    rows.forEach(row => {
        const textMatchName = (row.dataset.name || "").includes(filterText);
        const textMatchEmail = (row.dataset.email || "").includes(filterText);
        const textMatch = filterText === '' || textMatchName || textMatchEmail;
        
        let statusMatch = true;
        if (statusFilter !== 'All') {
            const badge = row.querySelector('.badge-pro');
            const rowStatus = badge ? badge.innerText.trim() : '';
            if (statusFilter === 'VIP Elite' && rowStatus !== 'VIP Elite') statusMatch = false;
            if (statusFilter === 'Standard' && rowStatus !== 'Standard') statusMatch = false;
            if (statusFilter === 'Blacklisted' && rowStatus !== 'Blacklisted') statusMatch = false;
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
            emptyState.querySelector('h4').innerText = "No Client Records Found";
            emptyState.querySelector('p').innerText = "Your client database is empty. Add a new customer to start building intelligence.";
            const btn = emptyState.querySelector('button');
            if(btn) btn.style.display = '';
        } else {
            emptyState.style.display = 'none';
        }
    }
};

window.exportCustomerCSV = function(format = 'csv') {
    const rows = document.querySelectorAll('#customersTableBody .table-row-pro');
    if (rows.length === 0) {
        if (window.showError) window.showError("No data to export.");
        return;
    }
    
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Client ID,First Name,Last Name,Email,Account Tier,Lifetime Spend,Events,Last Active\n";
    
    rows.forEach(row => {
        if (row.style.display === 'none') return;
        try {
            const cells = row.querySelectorAll('td');
            const id = cells[0].innerText.replace('#', '').trim();
            const fullName = row.querySelector('.name-text').innerText.trim();
            const names = fullName.split(' ');
            const firstName = names[0];
            const lastName = names.slice(1).join(' ');
            const email = row.querySelector('.email-text').innerText.trim();
            const tier = cells[2].innerText.trim();
            const spend = cells[3].innerText.replace('₱', '').replace(/,/g, '').trim();
            const events = cells[4].innerText.replace('events', '').trim();
            const lastSeen = cells[5].innerText.trim();
            
            csvContent += `"${id}","${firstName}","${lastName}","${email}","${tier}","${spend}","${events}","${lastSeen}"\n`;
        } catch(e) {}
    });
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", format === 'excel' ? "customer_database.xls" : "customer_database.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    window.toggleActionMenu('export');
};

window.exportCustomerPDF = function() {
    window.toggleActionMenu('export');
    const rows = document.querySelectorAll('#customersTableBody .table-row-pro');
    if (rows.length === 0) {
        if (window.showError) window.showError("No data to export.");
        return;
    }

    let printHtml = `
    <html><head><title>Customer Database Report</title>
    <style>
        body { font-family: 'Poppins', sans-serif; padding: 2rem; color: #0f172a; }
        h2 { border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; margin-bottom: 1.5rem; }
        table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        th, td { border: 1px solid #e2e8f0; padding: 0.75rem; text-align: left; }
        th { background: #f8fafc; font-weight: 800; text-transform: uppercase; color: #64748b; }
        tr:nth-child(even) { background: #fcfcfd; }
    </style></head><body>
    <h2>OccaServe Caterer - Customer Database Report</h2>
    <table><thead><tr>
        <th>ID</th><th>Name</th><th>Email</th><th>Tier</th><th>LTV (Spend)</th><th>Events</th>
    </tr></thead><tbody>`;

    rows.forEach(row => {
        if (row.style.display === 'none') return;
        try {
            const cells = row.querySelectorAll('td');
            const id = cells[0].innerText.replace('#', '').trim();
            const fullName = row.querySelector('.name-text').innerText.trim();
            const email = row.querySelector('.email-text').innerText.trim();
            const tier = cells[2].innerText.trim();
            const spend = cells[3].innerText.trim();
            const events = cells[4].innerText.trim();
            printHtml += `<tr><td>${id}</td><td>${fullName}</td><td>${email}</td><td>${tier}</td><td>${spend}</td><td>${events}</td></tr>`;
        } catch(e) {}
    });

    printHtml += `</tbody></table></body></html>`;
    const printWindow = window.open('', '_blank');
    printWindow.document.write(printHtml);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => { printWindow.print(); }, 500);
};

window.switchIntelTab = function(tabId, btn) {
    const tabs = document.querySelectorAll('.tab-btn-pro');
    tabs.forEach(tab => tab.classList.remove('active'));
    btn.classList.add('active');

    const contents = document.querySelectorAll('.intel-content');
    contents.forEach(content => content.style.display = 'none');
    
    const target = document.getElementById(`intel-${tabId}`);
    if (target) target.style.display = 'block';
};

window.openCustomerProfile = async function(id) {
    currentCustomerId = id;
    
    document.getElementById('profName').innerHTML = `<i class="fas fa-user-circle"></i> Analyzing...`;
    document.getElementById('profStatus').innerText = "Connecting to intelligence stream...";
    
    const overviewTab = document.querySelector('.tab-btn-pro[data-tab="overview"]');
    if (overviewTab) window.switchIntelTab('overview', overviewTab);

    if (window.openModal) window.openModal('customerProfileModal');

    try {
        const res = await fetch(`/caterer/api/customers/${id}/details`);
        if (!res.ok) throw new Error("Intelligence Sync Failed");
        const c = await res.json();
        if (c.status === "error") throw new Error(c.message);

        document.getElementById('profName').innerHTML = `<i class="fas fa-user-circle"></i> ${c.first_name} ${c.last_name}`;
        
        let mName = c.middle_name ? ` ${c.middle_name} ` : ' ';
        const fullNameEl = document.getElementById('profFullName');
        if (fullNameEl) fullNameEl.innerText = `${c.first_name}${mName}${c.last_name}`;
        
        const addrEl = document.getElementById('profAddress');
        if (addrEl) addrEl.innerText = c.address || 'Location not provided';

        document.getElementById('profLTV').innerText = `₱${parseFloat(c.total_spent || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        document.getElementById('profEvents').innerText = c.total_bookings || 0;
        document.getElementById('profEmail').innerText = c.email;
        document.getElementById('profPhone').innerText = c.phone || 'N/A';
        document.getElementById('profNotes').innerText = c.notes || "No operational notes recorded.";
        
        const statusTag = document.getElementById('profStatus');
        const blacklistBtn = document.getElementById('blacklistBtn');

        if (c.status === 'BLACKLISTED') {
            statusTag.innerText = "Status: Blacklisted / High Risk";
            statusTag.style.color = "#fca5a5";
            blacklistBtn.innerText = "Restore Account";
            blacklistBtn.className = "btn-primary bg-success border-none";
        } else {
            statusTag.innerText = c.status === 'VIP' ? "Status: VIP Elite Client" : "Status: Standard Client";
            statusTag.style.color = "#93c5fd";
            blacklistBtn.innerText = "Execute Block";
            blacklistBtn.className = "btn-primary bg-danger border-none";
        }
        
        const blacklistReasonField = document.getElementById('blacklistReason');
        if (blacklistReasonField) blacklistReasonField.value = '';

        document.getElementById('editNotes').value = (c.notes && c.notes !== "No notes added yet.") ? c.notes : '';

        const historyContainer = document.getElementById('profHistory');
        if (c.history && c.history.length > 0) {
            historyContainer.innerHTML = c.history.map(item => `
                <div style="padding: 15px; border-left: 2px solid #e2e8f0; margin-left: 10px; position: relative;">
                    <div style="position: absolute; left: -6px; top: 20px; width: 10px; height: 10px; border-radius: 50%; background: var(--primary-color);"></div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 0.75rem; font-weight: 600; color: #64748b;">${new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                            <div style="font-weight: 600; font-size: 1rem; color: #0f172a; margin-top: 2px;">${item.package_name}</div>
                        </div>
                        <div style="font-weight: 700; color: var(--primary-color);">₱${item.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
                    </div>
                </div>
            `).join('');
        } else {
            historyContainer.innerHTML = '<div style="text-align:center; padding: 2rem; color: #64748b;"><i class="fas fa-receipt" style="font-size:2rem; margin-bottom:1rem; opacity: 0.5;"></i><p>No historical ledger data.</p></div>';
        }

    } catch (err) {
        console.error("Sync Error:", err);
        if (window.showError) window.showError(err.message || "Failed to synchronize intelligence hub.");
        window.closeModal('customerProfileModal');
    }
};

/* --- Real-Time Async Validation --- */
function setFieldStatus(fieldId, status, msg = '') {
    const field = document.getElementById(fieldId);
    const errorDiv = document.getElementById(`error-${fieldId}`);
    if (!field || !errorDiv) return;

    if (status === 'error') {
        field.classList.add('is-invalid');
        field.classList.remove('is-valid');
        errorDiv.textContent = msg;
        errorDiv.style.display = 'block';
    } else if (status === 'success') {
        field.classList.add('is-valid');
        field.classList.remove('is-invalid');
        errorDiv.style.display = 'none';
    } else {
        field.classList.remove('is-invalid', 'is-valid');
        errorDiv.style.display = 'none';
    }
}

async function validateAgainstDatabase(field, value, excludeId = null) {
    if (!value) return true;
    try {
        const payload = {};
        payload[field] = value;
        if (excludeId) payload['exclude_id'] = excludeId;

        const res = await fetch('/caterer/api/customers/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        if (data.status === 'error') {
            let inputId = field === 'email' ? 'regEmail' : 'regPhone';
            if (excludeId) inputId = field === 'email' ? 'editEmail' : 'editPhone';
            
            if (field === 'identity') {
                setFieldStatus('regFirstName', 'error', data.message);
                setFieldStatus('regLastName', 'error', data.message);
                if (document.getElementById('regMiddleName')) {
                    setFieldStatus('regMiddleName', 'error', data.message);
                }
            } else {
                setFieldStatus(inputId, 'error', data.message);
            }
            return false;
        }
        return true;
    } catch (e) {
        return true; 
    }
}

function attachSmartRealtimeValidation() {
    const handleTextRegex = (e, fieldId, label) => {
        const val = e.target.value;
        if (!val.trim()) { setFieldStatus(fieldId, 'error', `${label} is required.`); return false; }
        if (!/^[A-Za-zñÑáéíóúÁÉÍÓÚ\s\-\']+$/.test(val)) {
            setFieldStatus(fieldId, 'error', `Numbers/Symbols not allowed.`);
            return false;
        }
        setFieldStatus(fieldId, 'success');
        return true;
    };

    ['regFirstName', 'regMiddleName', 'regLastName'].forEach(id => {
        const el = document.getElementById(id);
        if(el) {
            el.addEventListener('input', (e) => {
                const isRequired = id !== 'regMiddleName';
                const label = id.replace('reg', '').replace('Name', ' Name');
                
                if (isRequired && !handleTextRegex(e, id, label)) return;
                else if (!isRequired && e.target.value.trim() && !handleTextRegex(e, id, label)) return;
                else if (!isRequired) setFieldStatus(id, 'default');
                
                clearTimeout(validationDebounceTimer);
                validationDebounceTimer = setTimeout(() => {
                    const fn = document.getElementById('regFirstName')?.value.trim();
                    const ln = document.getElementById('regLastName')?.value.trim();
                    const mn = document.getElementById('regMiddleName')?.value.trim() || "";
                    
                    if (fn && ln) {
                        fetch('/caterer/api/customers/validate', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ first_name: fn, last_name: ln, middle_name: mn })
                        }).then(res => res.json()).then(data => {
                            if (data.status === 'error' && data.field === 'identity') {
                                setFieldStatus('regFirstName', 'error', data.message);
                                setFieldStatus('regLastName', 'error', data.message);
                                if (document.getElementById('regMiddleName')) {
                                    setFieldStatus('regMiddleName', 'error', data.message);
                                }
                            } else {
                                setFieldStatus('regFirstName', 'success');
                                setFieldStatus('regLastName', 'success');
                                if (document.getElementById('regMiddleName') && mn) {
                                    setFieldStatus('regMiddleName', 'success');
                                }
                            }
                        }).catch(console.error);
                    }
                }, 800);
            });
        }
    });

    ['regPhone', 'editPhone'].forEach(id => {
        const el = document.getElementById(id);
        if(el) {
            el.addEventListener('input', (e) => {
                e.target.value = e.target.value.replace(/[^0-9]/g, '').slice(0, 11);
                const val = e.target.value;
                
                if (val.length > 0 && (val.length !== 11 || !val.startsWith('09'))) {
                    setFieldStatus(id, 'error', 'Must be exactly 11 digits starting with 09.');
                } else if (val.length === 11) {
                    setFieldStatus(id, 'success');
                    clearTimeout(validationDebounceTimer);
                    validationDebounceTimer = setTimeout(() => {
                        const exId = id.includes('edit') ? currentCustomerId : null;
                        validateAgainstDatabase('phone', val, exId);
                    }, 500);
                } else {
                    setFieldStatus(id, 'default');
                }
            });
        }
    });

    ['regEmail', 'editEmail'].forEach(id => {
        const el = document.getElementById(id);
        if(el) {
            el.addEventListener('input', (e) => {
                const val = e.target.value;
                if (!val) { setFieldStatus(id, 'default'); return; }
                if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) {
                    setFieldStatus(id, 'error', 'Invalid email format.');
                } else {
                    setFieldStatus(id, 'success');
                    clearTimeout(validationDebounceTimer);
                    validationDebounceTimer = setTimeout(() => {
                        const exId = id.includes('edit') ? currentCustomerId : null;
                        validateAgainstDatabase('email', val, exId);
                    }, 500);
                }
            });
        }
    });
}

function checkFormErrors(formId) {
    const form = document.getElementById(formId);
    const errors = form.querySelectorAll('.form-control.is-invalid');
    return errors.length > 0;
}

function dynamicallyUpdateCustomerRow(c) {
    const tableBody = document.getElementById('customersTableBody');
    const existingRow = document.getElementById(`row-cust-${c.id}`);
    
    let badgeHtml = '';
    if (c.status === 'BLACKLISTED') badgeHtml = '<span class="badge-pro badge-danger">Blacklisted</span>';
    else if (c.total_bookings > 5 || c.status === 'VIP') badgeHtml = '<span class="badge-pro badge-warning">VIP Elite</span>';
    else badgeHtml = '<span class="badge-pro badge-secondary">Standard</span>';

    const fnInitial = c.first_name ? c.first_name[0].toUpperCase() : '?';
    const lnInitial = c.last_name ? c.last_name[0].toUpperCase() : '';

    const rowContent = `
        <td>
            <span class="badge-subtle">#${String(c.id).padStart(3, '0')}</span>
        </td>
        <td>
            <div class="identity-flex">
                <div class="avatar-circle-pro">${fnInitial}${lnInitial}</div>
                <div class="identity-text">
                    <div class="name-text">${c.first_name} ${c.last_name}</div>
                    <div class="email-text">${c.email}</div>
                </div>
            </div>
        </td>
        <td>${badgeHtml}</td>
        <td>
            <div class="amount-text">₱${parseFloat(c.total_spent || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
        </td>
        <td>
            <span class="badge-pro bg-primary-light" style="color: var(--primary-color);">${c.total_bookings || 0} events</span>
        </td>
        <td>
            <div class="date-text">
                ${c.history && c.history.length > 0 ? new Date(c.history[0].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'No data'}
            </div>
        </td>
        <td class="text-right">
            <div class="action-dropdown-container">
                <button class="btn-icon-dots" onclick="window.toggleActionMenu('cust${c.id}')">
                    <i class="fas fa-ellipsis-v"></i>
                </button>
                <div class="action-dropdown-menu" id="actionMenu-cust${c.id}">
                    <button onclick="window.openCustomerProfile(${c.id})"><i class="fas fa-id-card text-primary"></i> View Profile</button>
                    <button onclick="window.quickEditCustomer(${c.id})"><i class="fas fa-pen text-warning"></i> Quick Edit</button>
                    <div class="dropdown-divider"></div>
                    <button onclick="window.quickToggleBlacklist(${c.id}, '${c.status}')">
                        <i class="fas ${c.status === 'BLACKLISTED' ? 'fa-check text-success' : 'fa-ban text-danger'}"></i> 
                        ${c.status === 'BLACKLISTED' ? 'Restore Account' : 'Block Account'}
                    </button>
                </div>
            </div>
        </td>
    `;

    if (existingRow) {
        existingRow.innerHTML = rowContent;
        existingRow.dataset.name = `${c.first_name} ${c.last_name}`.toLowerCase();
        existingRow.dataset.email = c.email.toLowerCase();
        existingRow.style.transition = "background 0.5s";
        existingRow.style.backgroundColor = 'rgba(var(--primary-color-rgb), 0.1)';
        setTimeout(() => existingRow.style.backgroundColor = '', 1000);
    } else {
        const tr = document.createElement('tr');
        tr.className = 'table-row-pro';
        tr.id = `row-cust-${c.id}`;
        tr.dataset.name = `${c.first_name} ${c.last_name}`.toLowerCase();
        tr.dataset.email = c.email.toLowerCase();
        tr.innerHTML = rowContent;
        tableBody.prepend(tr);
        
        const emptyState = document.getElementById('emptyStateRow');
        if(emptyState) emptyState.style.display = 'none';

        const totalEl = document.getElementById('statTotalClients');
        if(totalEl) totalEl.innerText = parseInt(totalEl.innerText) + 1;
        const growthEl = document.getElementById('statGrowthClients');
        if(growthEl) growthEl.innerText = parseInt(growthEl.innerText) + 1;
    }
}

window.quickEditCustomer = async function(id) {
    await window.openCustomerProfile(id);
    const editTab = document.querySelector('.tab-btn-pro[data-tab="edit"]');
    if(editTab) window.switchIntelTab('edit', editTab);
}

window.quickToggleBlacklist = function(id, currentStatus) {
    currentCustomerId = id;
    window.toggleBlacklist(currentStatus === 'BLACKLISTED');
}

window.updateCustomerProfile = async function(event) {
    event.preventDefault();
    if (!currentCustomerId) return;

    const btn = document.getElementById('btnUpdateCustomer');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Committing...';
    btn.disabled = true;

    try {
        const form = document.getElementById('editCustomerForm');
        const formData = new FormData(form);

        const res = await fetch(`/caterer/api/customers/${currentCustomerId}/edit`, {
            method: 'POST',
            body: formData
        });

        const data = await res.json();

        if (data.status === 'success') {
            if (window.showSuccess) window.showSuccess(data.message);
            await window.openCustomerProfile(currentCustomerId);
            const updatedDetailsRes = await fetch(`/caterer/api/customers/${currentCustomerId}/details`);
            if (updatedDetailsRes.ok) {
                const updatedDetails = await updatedDetailsRes.json();
                dynamicallyUpdateCustomerRow(updatedDetails);
            }
        } else {
            if (window.showError) window.showError(data.message);
        }
    } catch (err) {
        if (window.showError) window.showError("A system error occurred.");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
};

window.registerCustomer = async function(e) {
    e.preventDefault();
    if (checkFormErrors('addCustomerForm')) {
        if (window.showError) window.showError("Please resolve the validation errors before registering.");
        return;
    }

    const form = e.target;
    const btn = document.getElementById('btnSubmitRegistration');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    btn.disabled = true;

    const formData = new FormData(form);

    try {
        const res = await fetch('/caterer/api/customers/register', {
            method: 'POST',
            body: formData
        });
        
        const data = await res.json();

        if (data.status === 'success' && data.customer_id) {
            window.closeModal('addCustomerModal');
            if (window.showSuccess) window.showSuccess(data.message);
            
            const newCustomerRes = await fetch(`/caterer/api/customers/${data.customer_id}/details`);
            if (newCustomerRes.ok) {
                const newCustomer = await newCustomerRes.json();
                dynamicallyUpdateCustomerRow(newCustomer);
            }
            form.reset();
            form.querySelectorAll('.form-control').forEach(el => el.classList.remove('is-valid', 'is-invalid'));
            ['regProv', 'regCity', 'regBrgy'].forEach(id => {
                const el = document.getElementById(id);
                if(el && el.options) el.selectedIndex = 0;
            });
            document.getElementById('regCity').disabled = true;
            document.getElementById('regBrgy').disabled = true;
        } else {
            if (window.showError) window.showError(data.message);
        }
    } catch (err) {
        if (window.showError) window.showError("System error during registration.");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
};

window.toggleBlacklist = async function(isCurrentlyBlocked = false) {
    if (!currentCustomerId) return;
    
    const btn = document.getElementById('blacklistBtn');
    if (btn && btn.classList.contains('bg-success')) isCurrentlyBlocked = true;

    const reasonField = document.getElementById('blacklistReason');
    const reason = reasonField ? reasonField.value.trim() : "";

    if (!isCurrentlyBlocked && !reason) {
        if (window.showError) window.showError("Please provide a reason for restricting this account.");
        if (reasonField) reasonField.focus();
        return;
    }

    const action = isCurrentlyBlocked ? 'Restore' : 'Block';
    const message = isCurrentlyBlocked 
        ? "Restore relationship with this client?" 
        : "Are you sure you want to block this relationship? They will not be able to book with you again.";

    if (window.showConfirm) {
        window.showConfirm(message, async () => {
            try {
                const res = await fetch(`/caterer/api/customers/${currentCustomerId}/blacklist`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ reason: reason })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    if(window.showSuccess) window.showSuccess(data.message);
                    
                    const modal = document.getElementById('customerProfileModal');
                    if (modal && modal.classList.contains('active')) {
                        await window.openCustomerProfile(currentCustomerId);
                    }
                    
                    const updatedDetailsRes = await fetch(`/caterer/api/customers/${currentCustomerId}/details`);
                    if (updatedDetailsRes.ok) {
                        const updatedDetails = await updatedDetailsRes.json();
                        dynamicallyUpdateCustomerRow(updatedDetails);
                        window.filterCustomerTable();
                    }
                } else {
                    if(window.showError) window.showError(data.message);
                }
            } catch(e) {
                if(window.showError) window.showError("System error processing request.");
            }
        }, action === 'Block' ? 'Warning' : 'Restore');
    }
};

window.loadProvinces = async function(selectId) {
    const select = document.getElementById(selectId);
    if(!select) return;
    try {
        const res = await fetch(`${PSGC_BASE}/provinces/`);
        const data = await res.json();
        data.sort((a,b) => a.name.localeCompare(b.name));
        select.innerHTML = '<option value="">Select Province</option>';
        data.forEach(p => select.innerHTML += `<option value="${p.name}" data-code="${p.code}">${p.name}</option>`);
        
        const resNcr = await fetch(`${PSGC_BASE}/regions/130000000/districts/`);
        const distData = await resNcr.json();
        distData.forEach(d => select.innerHTML += `<option value="${d.name}" data-code="${d.code}">${d.name}</option>`);
    } catch(err) {}
};

window.loadCities = async function(provName, citySelectId) {
    const citySelect = document.getElementById(citySelectId);
    const brgySelect = document.getElementById('regBrgy');
    if(!citySelect) return;
    
    citySelect.innerHTML = '<option value="">Loading...</option>';
    citySelect.disabled = true;
    if(brgySelect) {
        brgySelect.innerHTML = '<option value="">Select Barangay</option>';
        brgySelect.disabled = true;
    }
    
    const provSelect = document.getElementById('regProv');
    const selectedOption = provSelect.options[provSelect.selectedIndex];
    if(!selectedOption || !selectedOption.dataset.code) {
        citySelect.innerHTML = '<option value="">Select City/Municipality</option>';
        return;
    }
    
    const code = selectedOption.dataset.code;
    try {
        let endpoint = `${PSGC_BASE}/provinces/${code}/cities-municipalities/`;
        if(code.startsWith('13')) endpoint = `${PSGC_BASE}/districts/${code}/cities-municipalities/`;
        
        const res = await fetch(endpoint);
        const data = await res.json();
        data.sort((a,b) => a.name.localeCompare(b.name));
        
        citySelect.innerHTML = '<option value="">Select City/Municipality</option>';
        data.forEach(c => citySelect.innerHTML += `<option value="${c.name}" data-code="${c.code}">${c.name}</option>`);
        citySelect.disabled = false;
        setFieldStatus('regProv', 'success');
    } catch(err) {
        citySelect.innerHTML = '<option value="">Error loading</option>';
    }
};

window.loadBarangays = async function(cityName, brgySelectId) {
    const brgySelect = document.getElementById(brgySelectId);
    if(!brgySelect) return;
    
    brgySelect.innerHTML = '<option value="">Loading...</option>';
    brgySelect.disabled = true;
    
    const citySelect = document.getElementById('regCity');
    const selectedOption = citySelect.options[citySelect.selectedIndex];
    if(!selectedOption || !selectedOption.dataset.code) {
        brgySelect.innerHTML = '<option value="">Select Barangay</option>';
        return;
    }
    
    try {
        const res = await fetch(`${PSGC_BASE}/cities-municipalities/${selectedOption.dataset.code}/barangays/`);
        const data = await res.json();
        data.sort((a,b) => a.name.localeCompare(b.name));
        
        brgySelect.innerHTML = '<option value="">Select Barangay</option>';
        data.forEach(b => brgySelect.innerHTML += `<option value="${b.name}">${b.name}</option>`);
        brgySelect.disabled = false;
        setFieldStatus('regCity', 'success');
    } catch(err) {
        brgySelect.innerHTML = '<option value="">Error loading</option>';
    }
};
