/**
 * DIAMOND CRM & RELATIONSHIP INTELLIGENCE (v8.0)
 * Integrated with OccaServe Premium Global Modal System
 */

console.log("[CRM] Intelligence Hub Initializing... v8.0");

// Centralized State
let currentCustomerId = null;
const PSGC_BASE = 'https://psgc.gitlab.io/api';

document.addEventListener('DOMContentLoaded', function() {
    // Attach Input Restrictions for Registration
    attachRegistrationRestrictions();
    // Preload provinces for Registration Modal
    if(document.getElementById('regProv')) {
        window.loadProvinces('regProv');
    }
});

/**
 * Optimized Filtering Logic
 */
window.filterCustomerTable = function() {
    const bridge = document.getElementById('custSearchInput');
    const filterText = bridge ? bridge.value.toLowerCase() : '';
    const statusSelect = document.getElementById('tableFilterStatus');
    const statusFilter = statusSelect ? statusSelect.value : 'All';
    
    const rows = document.querySelectorAll('#customersTable tbody .premium-row');
    
    rows.forEach(row => {
        const text = row.dataset.name || row.innerText.toLowerCase();
        const textMatch = text.includes(filterText);
        
        let statusMatch = true;
        if (statusFilter !== 'All') {
            const badge = row.querySelector('.p-badge');
            const rowStatus = badge ? badge.innerText.trim() : '';
            if (statusFilter === 'VIP Elite' && rowStatus !== 'VIP Elite') statusMatch = false;
            if (statusFilter === 'Standard' && rowStatus !== 'Standard') statusMatch = false;
            if (statusFilter === 'Blacklisted' && rowStatus !== 'Blacklisted') statusMatch = false;
        }
        
        row.style.display = (textMatch && statusMatch) ? '' : 'none';
    });
};

window.filterCustomers = window.filterCustomerTable; // Keep compatibility if called externally

window.exportCustomerCSV = function() {
    const rows = document.querySelectorAll('#customersTable tbody .premium-row');
    if (rows.length === 0) {
        if (window.showError) window.showError("No data to export.");
        return;
    }
    
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Customer ID,Name,Email,Account Tier,Lifetime Spend,Events,Last Engagement\n";
    
    rows.forEach(row => {
        if (row.style.display === 'none') return; // Only export visible
        
        try {
            const idEl = row.querySelector('.customer-id-pill');
            const nameEl = row.querySelector('.cust-name-pro');
            const emailEl = row.querySelector('.cust-email-pro');
            const tierEl = row.querySelector('.p-badge');
            const spendEl = row.querySelector('.spend-value');
            const eventsEl = row.querySelector('.booking-count-badge');
            const lastSeenEl = row.querySelector('.last-seen-pro');

            const id = idEl ? idEl.innerText.replace('#', '').trim() : '';
            const name = nameEl ? nameEl.innerText.trim() : '';
            const email = emailEl ? emailEl.innerText.trim() : '';
            const tier = tierEl ? tierEl.innerText.trim() : 'Standard';
            const spend = spendEl ? spendEl.innerText.replace('₱', '').replace(/,/g, '').trim() : '0.00';
            const events = eventsEl ? eventsEl.innerText.replace(' events', '').trim() : '0';
            const lastSeen = lastSeenEl ? lastSeenEl.innerText.trim() : 'N/A';
            
            const rowData = `"${id}","${name}","${email}","${tier}","${spend}","${events}","${lastSeen}"`;
            csvContent += rowData + "\n";
        } catch(e) {
            console.warn("Failed to export a row due to missing elements.", e);
        }
    });
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "customer_database_export.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

/**
 * Intelligence Hub: Tab Navigation
 */
window.switchIntelTab = function(tabId, btn) {
    // Update Buttons
    const tabs = document.querySelectorAll('.intel-tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    btn.classList.add('active');

    // Update Content
    const contents = document.querySelectorAll('.intel-content');
    contents.forEach(content => content.classList.remove('active'));
    
    const target = document.getElementById(`intel-${tabId}`);
    if (target) target.classList.add('active');
};

/**
 * Fetch & Render Customer Intelligence
 */
window.openCustomerProfile = async function(id) {
    currentCustomerId = id;
    
    // Reset Modal UI
    document.getElementById('profName').innerText = "Loading Hub...";
    document.getElementById('profInitials').innerText = "--";
    document.getElementById('profStatus').innerText = "Analyzing Relationship...";
    document.getElementById('profLTV').innerText = "₱0.00";
    document.getElementById('profEvents').innerText = "0";
    document.getElementById('profEmail').innerText = "--";
    document.getElementById('profPhone').innerText = "--";
    document.getElementById('profNotes').innerText = "Initializing data stream...";
    document.getElementById('profHistory').innerHTML = '<div class="empty-intel-msg"><i class="fas fa-spinner fa-spin"></i><p>Synchronizing history...</p></div>';

    // Switch to Overview Tab by default
    const overviewTab = document.querySelector('.intel-tab[data-tab="overview"]');
    if (overviewTab) window.switchIntelTab('overview', overviewTab);

    // Open Modal
    if (window.openModal) window.openModal('customerProfileModal');

    try {
        const res = await fetch(`/api/customers/${id}/details`);
        if (!res.ok) throw new Error("Intelligence Sync Failed");
        
        const data = await res.json();
        const c = data; // Backend returns the user object directly, not wrapped in 'customer'

        // Render Overview
        document.getElementById('profName').innerText = `${c.first_name} ${c.last_name}`;
        document.getElementById('profInitials').innerText = `${c.first_name[0]}${c.last_name[0]}`;
        document.getElementById('profLTV').innerText = `₱${parseFloat(c.total_spent || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        document.getElementById('profEvents').innerText = c.total_bookings || 0;
        document.getElementById('profEmail').innerText = c.email;
        document.getElementById('profPhone').innerText = c.phone || 'N/A';
        document.getElementById('profNotes').innerText = c.notes || "No operational notes recorded.";
        
        const statusTag = document.getElementById('profStatus');
        const blacklistBtn = document.getElementById('blacklistBtn');

        if (c.status === 'BLACKLISTED') {
            statusTag.innerText = "Blacklisted / High Risk";
            statusTag.style.color = "#ef4444";
            statusTag.style.background = "rgba(239, 68, 68, 0.1)";
            blacklistBtn.innerText = "RESTORE RELATIONSHIP";
            blacklistBtn.classList.add('active');
        } else {
            statusTag.innerText = c.status === 'VIP' ? "VIP Engagement" : "Standard Relationship";
            statusTag.style.color = "#10b981";
            statusTag.style.background = "rgba(16, 185, 129, 0.1)";
            blacklistBtn.innerText = "BLOCK RELATIONSHIP";
            blacklistBtn.classList.remove('active');
        }
        
        // Populate Edit Form
        document.getElementById('editFirstName').value = c.first_name || '';
        document.getElementById('editLastName').value = c.last_name || '';
        document.getElementById('editEmail').value = c.email || '';
        document.getElementById('editPhone').value = c.phone || '';
        document.getElementById('editNotes').value = c.notes !== "No notes added yet." ? c.notes : '';

        // Render History
        const historyContainer = document.getElementById('profHistory');
        if (data.history && data.history.length > 0) {
            historyContainer.innerHTML = data.history.map(item => `
                <div class="history-item-pro">
                    <div class="hist-main">
                        <span class="hist-date">${new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                        <span class="hist-package">${item.package_name}</span>
                    </div>
                    <div class="hist-price">₱${item.amount.toLocaleString()}</div>
                </div>
            `).join('');
        } else {
            historyContainer.innerHTML = '<div class="empty-intel-msg"><i class="fas fa-calendar-minus"></i><p>No historical bookings found for this relationship.</p></div>';
        }

    } catch (err) {
        console.error("[CRM] Sync Error:", err);
        if (window.showError) window.showError("Failed to synchronize intelligence hub.");
    }
};

window.updateCustomerProfile = async function(event) {
    event.preventDefault();
    if (!currentCustomerId) return;

    // Validate edit form before submit
    const firstName = document.getElementById('editFirstName').value.trim();
    const email = document.getElementById('editEmail').value.trim();
    const phone = document.getElementById('editPhone').value.trim();

    if (!firstName) {
        setFieldError('editFirstName', 'First name is required.');
        return;
    }

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        setFieldError('editEmail', 'Please enter a valid email address.');
        return;
    }

    if (phone && (phone.length < 11 || !phone.startsWith('09'))) {
        setFieldError('editPhone', 'Please enter a valid 11-digit PH mobile number starting with 09.');
        return;
    }

    const btn = document.getElementById('btnUpdateCustomer');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    btn.disabled = true;

    try {
        const form = document.getElementById('editCustomerForm');
        const formData = new FormData(form);

        const res = await fetch(`/api/customers/${currentCustomerId}/edit`, {
            method: 'POST',
            body: formData
        });

        const data = await res.json();

        if (data.status === 'success') {
            if (window.showSuccess) window.showSuccess(data.message);
            // Refresh modal data
            await window.openCustomerProfile(currentCustomerId);
            // Optionally reload page to update table after 1.5s
            setTimeout(() => window.location.reload(), 1500);
        } else {
            if (window.showError) window.showError(data.message);
            // Try to set specific field errors if they relate to email/phone
            if (data.message.includes('email')) {
                setFieldError('editEmail', data.message);
            } else if (data.message.includes('phone')) {
                setFieldError('editPhone', data.message);
            }
        }
    } catch (err) {
        console.error("Update Error:", err);
        if (window.showError) window.showError("A system error occurred while updating the profile.");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
};

/**
 * --- VALIDATION LOGIC (CALENDAR PARITY) ---
 */

function setFieldError(fieldId, msg) {
    const field = document.getElementById(fieldId);
    const errorDiv = document.getElementById(`error-${fieldId}`);
    if (field && errorDiv) {
        field.classList.add('is-invalid');
        errorDiv.textContent = msg;
        errorDiv.style.display = 'block';
    }
}

function clearFieldError(fieldId) {
    const field = document.getElementById(fieldId);
    const errorDiv = document.getElementById(`error-${fieldId}`);
    if (field && errorDiv) {
        field.classList.remove('is-invalid');
        errorDiv.style.display = 'none';
    }
}

function validateSmartEmail(val) {
    if (!val) { clearFieldError('regEmail'); return false; }
    // Standard email validation regex
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(val)) {
        setFieldError('regEmail', 'Please enter a valid email address.');
        return false;
    }
    clearFieldError('regEmail');
    return true;
}

function validateSmartName(val) {
    if (!val) { clearFieldError('regName'); return false; }
    const parts = val.trim().split(/\s+/);
    if (parts.length < 2) {
        setFieldError('regName', 'Please provide both First Name and Surname.');
        return false;
    }
    clearFieldError('regName');
    return true;
}

function validateSmartContact(val) {
    if (!val) { clearFieldError('regPhone'); return false; }
    if (val.length < 11 || !val.startsWith('09')) {
        setFieldError('regPhone', 'Please enter a valid 11-digit PH mobile number starting with 09.');
        return false;
    }
    clearFieldError('regPhone');
    return true;
}

function attachRegistrationRestrictions() {
    const phoneInput = document.getElementById('regPhone');
    if (phoneInput) {
        phoneInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '');
            if (this.value.length > 11) this.value = this.value.slice(0, 11);
            validateSmartContact(this.value);
        });
    }

    const firstNameInput = document.getElementById('regFirstName');
    if (firstNameInput) {
        firstNameInput.addEventListener('input', function() {
            validateSmartNamePart(this.value, 'regFirstName', 'First name');
        });
    }
    
    const lastNameInput = document.getElementById('regLastName');
    if (lastNameInput) {
        lastNameInput.addEventListener('input', function() {
            validateSmartNamePart(this.value, 'regLastName', 'Last name');
        });
    }

    const emailInput = document.getElementById('regEmail');
    if (emailInput) {
        emailInput.addEventListener('input', function() {
            validateSmartEmail(this.value, 'regEmail');
        });
    }

    // Attach edit form validation
    attachEditFormValidation();
}

function attachEditFormValidation() {
    const editFirstName = document.getElementById('editFirstName');
    const editLastName = document.getElementById('editLastName');
    const editEmail = document.getElementById('editEmail');
    const editPhone = document.getElementById('editPhone');

    if (editFirstName) {
        editFirstName.addEventListener('input', function() {
            if (this.value.trim()) {
                clearFieldError('editFirstName');
            } else {
                setFieldError('editFirstName', 'First name is required.');
            }
        });
    }

    if (editLastName) {
        editLastName.addEventListener('input', function() {
            validateSmartNamePart(this.value, 'editLastName', 'Last name');
        });
    }

    if (editEmail) {
        editEmail.addEventListener('input', function() {
            validateSmartEmail(this.value, 'editEmail');
        });
    }

    if (editPhone) {
        editPhone.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '');
            if (this.value.length > 11) this.value = this.value.slice(0, 11);
            if (this.value) {
                validateSmartContact(this.value, 'editPhone');
            } else {
                clearFieldError('editPhone');
            }
        });
    }
}

function validateSmartEmail(val, fieldId = 'regEmail') {
    if (!val) { clearFieldError(fieldId); return false; }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(val)) {
        setFieldError(fieldId, 'Please enter a valid email address.');
        return false;
    }
    clearFieldError(fieldId);
    return true;
}

function validateSmartContact(val, fieldId = 'regPhone') {
    if (!val) { clearFieldError(fieldId); return false; }
    if (val.length < 11 || !val.startsWith('09')) {
        setFieldError(fieldId, 'Please enter a valid 11-digit PH mobile number starting with 09.');
        return false;
    }
    clearFieldError(fieldId);
    return true;
}

function validateSmartNamePart(val, fieldId, label) {
    if (!val || !val.trim()) {
        setFieldError(fieldId, `${label} is required.`);
        return false;
    }
    clearFieldError(fieldId);
    return true;
}

/**
 * Action: Register Relationship
 */
window.registerCustomer = async function(e) {
    e.preventDefault();
    const form = e.target;
    const btn = document.getElementById('btnSubmitRegistration');

    // Reset errors
    ['regFirstName', 'regLastName', 'regEmail', 'regPhone', 'regProv', 'regCity', 'regBrgy', 'regLandmark'].forEach(id => clearFieldError(id));

    // Perform validation
    const fName = document.getElementById('regFirstName').value.trim();
    const lName = document.getElementById('regLastName').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const phone = document.getElementById('regPhone').value.trim();
    const prov = document.getElementById('regProv').value;
    const city = document.getElementById('regCity').value;
    const brgy = document.getElementById('regBrgy').value;
    const landmark = document.getElementById('regLandmark').value.trim();
    
    let hasError = false;
    if(!fName) { setFieldError('regFirstName', 'First Name is required.'); hasError = true; }
    if(!lName) { setFieldError('regLastName', 'Last Name is required.'); hasError = true; }
    if(!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setFieldError('regEmail', 'Valid email is required.'); hasError = true; }
    if(phone && (phone.length < 11 || !phone.startsWith('09'))) { setFieldError('regPhone', 'Valid 11-digit mobile number required.'); hasError = true; }
    if(!prov) { setFieldError('regProv', 'Province is required.'); hasError = true; }
    if(!city) { setFieldError('regCity', 'City is required.'); hasError = true; }
    if(!brgy) { setFieldError('regBrgy', 'Barangay is required.'); hasError = true; }
    if(!landmark) { setFieldError('regLandmark', 'Street/Landmark is required.'); hasError = true; }
    
    if (hasError) return;

    // Add loading state
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Establishing...';
    btn.disabled = true;

    const formData = new FormData(form);

    if (window.apiAction) {
        try {
            const res = await window.apiAction('/api/customers/register', {
                method: 'POST',
                body: formData
            }, btn);

            if (res && res.status === 'success') {
                window.closeModal('addCustomerModal');
                if (window.showSuccess) window.showSuccess(res.message || "Relationship established successfully.");
                setTimeout(() => location.reload(), 800);
            } else {
                btn.innerHTML = originalText;
                btn.disabled = false;
                if (res && res.message) {
                    if (window.showError) window.showError(res.message);
                }
            }
        } catch (err) {
            console.error("Registration Error:", err);
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }
};

// --- PSGC Address Functions ---
window.loadProvinces = async function(selectId) {
    const select = document.getElementById(selectId);
    if(!select) return;
    try {
        const res = await fetch(`${PSGC_BASE}/provinces/`);
        const data = await res.json();
        data.sort((a,b) => a.name.localeCompare(b.name));
        select.innerHTML = '<option value="">Select Province</option>';
        data.forEach(p => {
            select.innerHTML += `<option value="${p.name}" data-code="${p.code}">${p.name}</option>`;
        });
        
        // Load NCR
        const resNcr = await fetch(`${PSGC_BASE}/regions/130000000/districts/`);
        const distData = await resNcr.json();
        distData.forEach(d => {
            select.innerHTML += `<option value="${d.name}" data-code="${d.code}">${d.name}</option>`;
        });
    } catch(err) {
        console.error("Failed to load provinces", err);
    }
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
        if(code.startsWith('13')) {
            endpoint = `${PSGC_BASE}/districts/${code}/cities-municipalities/`;
        }
        
        const res = await fetch(endpoint);
        const data = await res.json();
        data.sort((a,b) => a.name.localeCompare(b.name));
        
        citySelect.innerHTML = '<option value="">Select City/Municipality</option>';
        data.forEach(c => {
            citySelect.innerHTML += `<option value="${c.name}" data-code="${c.code}">${c.name}</option>`;
        });
        citySelect.disabled = false;
        clearFieldError('regProv');
    } catch(err) {
        console.error("Failed to load cities", err);
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
    
    const code = selectedOption.dataset.code;
    
    try {
        const res = await fetch(`${PSGC_BASE}/cities-municipalities/${code}/barangays/`);
        const data = await res.json();
        data.sort((a,b) => a.name.localeCompare(b.name));
        
        brgySelect.innerHTML = '<option value="">Select Barangay</option>';
        data.forEach(b => {
            brgySelect.innerHTML += `<option value="${b.name}">${b.name}</option>`;
        });
        brgySelect.disabled = false;
        clearFieldError('regCity');
    } catch(err) {
        console.error("Failed to load barangays", err);
        brgySelect.innerHTML = '<option value="">Error loading</option>';
    }
};

/**
 * Action: Risk Management (Blacklist)
 */
window.toggleBlacklist = async function() {
    if (!currentCustomerId) return;

    const action = document.getElementById('blacklistBtn').classList.contains('active') ? 'restore' : 'block';
    const message = action === 'block' 
        ? "Are you sure you want to block this relationship? They will not be able to book with you again."
        : "Restore relationship with this client?";

    if (window.showConfirm) {
        window.showConfirm(message, async () => {
            // Using the correct endpoint from the router
            const res = await window.apiAction(`/api/customers/${currentCustomerId}/blacklist`, {
                method: 'POST'
            });
            if (res) {
                window.closeModal('customerProfileModal');
                setTimeout(() => location.reload(), 600);
            }
        }, action === 'block' ? 'Warning' : 'Restore');
    }
};

// Global Bridge for Layout Search
window.addEventListener('globalSearch', function(e) {
    const bridge = document.getElementById('custSearchInput');
    if (bridge) {
        bridge.value = e.detail.value;
        window.filterCustomers();
    }
});
