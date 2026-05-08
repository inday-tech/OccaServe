/**
 * DIAMOND CRM & RELATIONSHIP INTELLIGENCE (v4.0)
 * Integrated with OccaServe Premium Global Modal System
 */

console.log("[CRM] Intelligence Hub Initializing...");

// Centralized State
let currentCustomerId = null;

document.addEventListener('DOMContentLoaded', function() {
    // Attach Input Restrictions for Registration
    attachRegistrationRestrictions();
});

/**
 * Optimized Filtering Logic
 */
window.filterCustomers = function() {
    const bridge = document.getElementById('custSearchInput');
    if (!bridge) return;
    const filter = bridge.value.toLowerCase();
    const rows = document.querySelectorAll('#customersTable tbody .premium-row');
    let visibleCount = 0;

    rows.forEach(row => {
        const text = row.dataset.name || row.innerText.toLowerCase();
        const match = text.includes(filter);
        row.style.display = match ? '' : 'none';
        if (match) visibleCount++;
    });
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
        const res = await fetch(`/caterer/api/customers/${id}/details`);
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
    if (!val.toLowerCase().endsWith('@gmail.com')) {
        setFieldError('regEmail', 'Only @gmail.com addresses are permitted.');
        return false;
    }
    clearFieldError('regEmail');
    return true;
}

function validateSmartName(val) {
    if (!val) { clearFieldError('regName'); return false; }
    const parts = val.trim().split(/\s+/);
    if (parts.length < 3) {
        setFieldError('regName', 'Format: First Name, Middle Initial, and Surname.');
        return false;
    }
    clearFieldError('regName');
    return true;
}

function validateSmartContact(val) {
    if (!val) { clearFieldError('regPhone'); return false; }
    if (val.length < 11) {
        setFieldError('regPhone', 'Incomplete number (11 digits required).');
        return false;
    }
    if (/(\d)\1{7,}/.test(val)) {
        setFieldError('regPhone', 'Invalid pattern: Repetitive numbers detected.');
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

    const nameInput = document.getElementById('regName');
    if (nameInput) {
        nameInput.addEventListener('input', function() {
            validateSmartName(this.value);
        });
    }

    const emailInput = document.getElementById('regEmail');
    if (emailInput) {
        emailInput.addEventListener('input', function() {
            validateSmartEmail(this.value);
        });
    }
}

/**
 * Action: Register Relationship
 */
window.registerCustomer = async function(e) {
    e.preventDefault();
    const form = e.target;
    const btn = document.getElementById('btnSubmitRegistration');
    
    // Reset errors
    ['regName', 'regEmail', 'regPhone'].forEach(id => clearFieldError(id));
    const errorDrawer = document.getElementById('addCustomerError');
    if (errorDrawer) errorDrawer.style.display = 'none';

    // Perform validation
    const isNameValid = validateSmartName(document.getElementById('regName').value);
    const isEmailValid = validateSmartEmail(document.getElementById('regEmail').value);
    const isContactValid = validateSmartContact(document.getElementById('regPhone').value);

    if (!isNameValid || !isEmailValid || !isContactValid) {
        if (errorDrawer) errorDrawer.style.display = 'flex';
        return;
    }

    const formData = new FormData(form);

    if (window.apiAction) {
        const res = await window.apiAction('/caterer/api/customers/register', {
            method: 'POST',
            body: formData
        }, btn);

        if (res) {
            window.closeModal('addCustomerModal');
            if (window.showSuccess) window.showSuccess("Relationship established successfully.");
            setTimeout(() => location.reload(), 800);
        }
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
            const res = await window.apiAction(`/caterer/api/customers/${currentCustomerId}/blacklist`, {
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
