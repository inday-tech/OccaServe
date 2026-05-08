let currentBookingId = null;
let currentPage = 1;
const ROWS_PER_PAGE = 5;
let filteredRows = [];

// ─── IMMEDIATE GLOBAL EXPOSURE (Fail-safe) ───────────────────────────────────
(function exposeGlobals() {
    window.filterBookings = filterBookings;
    window.filterBySignature = filterBySignature;
    window.toggleActionMenu = toggleActionMenuBookings;
    window.openWalkinModal = openWalkinModal;
    window.closeWalkinModal = closeWalkinModal;
    window.submitWalkinBooking = submitWalkinBooking;
    window.openExpenseTracker = openExpenseTracker;
    window.closeExpenseTracker = closeExpenseTracker;
    window.addExpenseRow = addExpenseRow;
    window.calculateActualExpenses = calculateActualExpenses;
    window.submitExpenses = submitExpenses;
    window.showBookingDetails = showBookingDetails;
    window.switchBookingTab = switchBookingTab;
    window.resetBookingTabs = resetBookingTabs;
    window.bk_closeBookingDetailModal = bk_closeBookingDetailModal;
    window.openContractModal = openContractModal;
    window.closeContractModal = closeContractModal;
    window.printContract = printContract;
    window.toggleDueDateEdit = toggleDueDateEdit;
    window.saveDueDate = saveDueDate;
    window.confirmAcceptBooking = confirmAcceptBooking;
    window.confirmRejectBooking = confirmRejectBooking;
    window.confirmCompleteBooking = confirmCompleteBooking;
    window.updateBookingStage = updateBookingStage;
    window.requestNewProof = requestNewProof;
    window.confirmArchiveBooking = confirmArchiveBooking;
    window.bk_closeModal = bk_closeModal; // New exposure
    window.scrollToActionTable = filterBySignature; // Link Attend Now button
    
    // Operations Checklist
    window.loadBookingTasks = loadBookingTasks;
    window.addNewCustomTask = addNewCustomTask;
    window.toggleTaskStatus = toggleTaskStatus;
    window.deleteTask = deleteTask;

    window.formatCurrency = (val) => {
        if (!val) return '';
        let num = parseFloat(val.toString().replace(/[₱,]/g, ''));
        if (isNaN(num)) return val;
        return '₱' + num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    console.log('[BookingsJS] Global functions exposed to window.');
})();

/* ─── Standardized modal helpers with Fallback ─── */
function bk_openModal(id) {
    if (window.openModal) {
        window.openModal(id);
    } else {
        const el = document.getElementById(id);
        if (el) {
            el.style.display = 'flex';
            setTimeout(() => el.classList.add('active'), 10);
            document.body.style.overflow = 'hidden';
        }
    }
}

function bk_closeModal(id) {
    console.log('[BookingsJS] Closing modal:', id);
    if (window.closeModal) {
        window.closeModal(id);
    } else {
        // Fallback dismissal
        const el = document.getElementById(id);
        if (el) {
            el.classList.remove('active');
            setTimeout(() => { if (!el.classList.contains('active')) el.style.display = 'none'; }, 450);
            if (document.querySelectorAll('.occ-modal-overlay.active').length === 0) {
                document.body.style.overflow = '';
            }
        }
    }
}

/* ─── Safe action menu toggle ─── */
function toggleActionMenuBookings(id, event) {
    if (event) event.stopPropagation();
    var allMenus = document.querySelectorAll('.action-dropdown-menu');
    var target = document.getElementById('actionMenu-' + id);
    allMenus.forEach(function(m) {
        if (m !== target) m.style.display = 'none';
    });
    if (!target) return;
    target.style.display = (target.style.display === 'none' || target.style.display === '') ? 'block' : 'none';
}

document.addEventListener('DOMContentLoaded', function () {
    console.log('[BookingsJS] Initializing components... [v1.8-robust]');

    try {
        // Override toggleActionMenu for this page
        window.toggleActionMenu = toggleActionMenuBookings;

        // 1. Attach view-details listeners
        initDetailListeners();

        // 2. Form Constraints
        const dateInput = document.getElementById('walkin_event_date');
        if (dateInput) {
            const today = new Date().toISOString().split('T')[0];
            dateInput.setAttribute('min', today);
            console.log('[BookingsJS] Set min date for walk-in form:', today);
        }

        // 3. Walk-in Booking Validation
        if (window.ValidationManager) {
            console.log('[BookingsJS] Initializing ValidationManager for walkinBookingForm...');
            new window.ValidationManager('walkinBookingForm', {
                'customer_name': { 
                    noSameParts: true,
                    label: 'Customer Name'
                },
                'customer_email': {
                    custom: (val) => {
                        if (!val) return true;
                        if (!val.toLowerCase().endsWith('@gmail.com')) return 'Only Gmail accounts are supported.';
                        return true;
                    }
                },
                'customer_contact': {
                    phMobile: true,
                    noRepetitive: true,
                    label: 'Contact Number'
                },
                'guest_count': {
                    numericOnly: true,
                    max: 100000,
                    label: 'Number of Guests'
                },
                'total_amount': {
                    numericOnly: true,
                    max: 5000000,
                    autoStop: false,
                    label: 'Total Amount'
                },
                'event_name': { label: 'Event Name' },
                'venue_address': { label: 'Venue' }
            });
            console.log('[BookingsJS] ValidationManager ready.');
            
            // 4. Real-time Button State & Masking
            const walkinForm = document.getElementById('walkinBookingForm');
            const walkinSubmitBtn = document.getElementById('walkinSubmitBtn');
            const amountInput = document.getElementById('bookTotalAmount');

            if (walkinForm && walkinSubmitBtn) {
                // Disable by default
                walkinSubmitBtn.disabled = true;

                walkinForm.addEventListener('input', function() {
                    const isInvalid = walkinForm.querySelectorAll('.is-invalid').length > 0;
                    const allRequiredFilled = Array.from(walkinForm.querySelectorAll('[required]')).every(input => input.value.trim() !== '');
                    walkinSubmitBtn.disabled = isInvalid || !allRequiredFilled;
                });
            }

            if (amountInput) {
                amountInput.addEventListener('focus', function() {
                    const val = this.value.replace(/[₱,]/g, '');
                    this.value = val;
                });

                amountInput.addEventListener('blur', function() {
                    this.value = window.formatCurrency(this.value);
                });
            }
        } else {
            console.warn('[BookingsJS] window.ValidationManager not found! Validation will be limited.');
        }

        initWalkinDetection();
        attachBookingPackageListeners();

        // 4. Pagination
        const allRows = Array.from(document.querySelectorAll('.bookings-list-table tbody tr.booking-row-item'));
        filteredRows = allRows;
        showPage(1);

        // 5. Global Click Listeners (Backups)
        document.addEventListener('click', function(e) {
            // Backup for "X" buttons that might lose their onclick
            if (e.target.closest('.occ-modal-close')) {
                const modal = e.target.closest('.occ-modal-overlay');
                if (modal) {
                    console.log('[BookingsJS] Backup Close triggered for:', modal.id);
                    bk_closeModal(modal.id);
                }
            }
            
            // Close action menus
            if (!e.target.closest('.action-dropdown-container')) {
                document.querySelectorAll('.action-dropdown-menu').forEach(function(m) {
                    m.style.display = 'none';
                });
            }
        });

        // 6. ESC key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                var open = document.querySelector('.occ-modal-overlay.active');
                if (open) bk_closeModal(open.id);
            }
        });

        // 7. Real-time Alerts Polling (Every 45 seconds)
        setInterval(refreshActionAlerts, 45000);

        console.log('[BookingsJS] Manage Bookings JS Ready. [v2.0-english-standard]');
    } catch (err) {
        console.error('[BookingsJS] CRITICAL ERROR DURING INIT:', err);
    }
});

async function refreshActionAlerts() {
    try {
        const res = await fetch('/caterer/api/dashboard-overview');
        if (!res.ok) return;
        
        // Count critical items across the whole table (even hidden ones)
        const allRows = Array.from(document.querySelectorAll('.bookings-list-table tbody tr.booking-row-item'));
        let payAlerts = 0;
        let contractAlerts = 0;
        let urgentAlerts = 0;

        allRows.forEach(row => {
            const rawStatus = row.dataset.status || '';
            const payStatus = row.dataset.paymentStatus || '';
            const isUrgent = row.dataset.isUrgent === 'true';

            if (['proof_submitted', 'balance_proof_submitted'].includes(payStatus)) payAlerts++;
            if (['pending_quotation', 'awaiting_caterer'].includes(rawStatus)) contractAlerts++;
            if (isUrgent && !['completed', 'cancelled'].includes(rawStatus)) urgentAlerts++;
        });

        const total = payAlerts + contractAlerts + urgentAlerts;
        const banner = document.getElementById('alertBanner');
        const countBadge = document.querySelector('.alert-count-badge');
        const detailsSpan = document.getElementById('bannerTaskDetails');

        if (total > 0) {
            if (banner) {
                banner.style.display = 'flex';
                if (countBadge) countBadge.innerText = total + ' Alerts';
                if (detailsSpan) {
                    let parts = [];
                    if (payAlerts > 0) parts.push(`<span style="color: #f59e0b; font-weight: 800;">${payAlerts}</span> payments`);
                    if (contractAlerts > 0) parts.push(`<span style="color: #f59e0b; font-weight: 800;">${contractAlerts}</span> contracts`);
                    if (urgentAlerts > 0) parts.push(`<span style="color: #fb7185; font-weight: 800;">${urgentAlerts}</span> urgent events`);
                    
                    detailsSpan.innerHTML = 'Pending: ' + parts.join(' &bull; ');
                }
            }
        } else if (banner) {
            banner.style.display = 'none';
        }
    } catch (err) { console.error('Alert polling failed:', err); }
}

function initDetailListeners() {
    document.querySelectorAll('.view-details').forEach(function(btn) {
        btn.onclick = function() { showBookingDetails(this); };
    });
}

function initEmailExistenceCheck() {
    const emailInput = document.getElementById('bookCustEmail');
    if (!emailInput) return;

    let timeout = null;
    emailInput.addEventListener('input', function() {
        const email = this.value.trim();
        const feedback = this.parentElement.querySelector('.invalid-feedback');
        
        clearTimeout(timeout);
        if (email.length < 5 || !email.includes('@')) return;

        timeout = setTimeout(async () => {
            try {
                const res = await fetch(`/auth/check-email?email=${encodeURIComponent(email)}`);
                const data = await res.json();
                if (!data.available) {
                    emailInput.classList.add('is-invalid');
                    if (feedback) feedback.innerText = 'This email is already registered in the system.';
                    // If ValidationManager is active, we might need to trigger it
                    emailInput.setCustomValidity('Already registered');
                } else {
                    emailInput.classList.remove('is-invalid');
                    if (feedback) feedback.innerText = '';
                    emailInput.setCustomValidity('');
                }
            } catch (err) { console.error('Email check failed:', err); }
        }, 500);
    });
}

// ─── FILTERING & PAGINATION ──────────────────────────────────────────────────

function filterBookings() {
    const searchInput = document.getElementById('bookingSearchInput').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;
    const allRows = Array.from(document.querySelectorAll('.bookings-list-table tbody tr.booking-row-item'));

    filteredRows = allRows.filter(function(row) {
        const rawStatus = row.dataset.status || '';
        const payStatus = row.dataset.paymentStatus || '';
        const rowText = row.innerText.toLowerCase();
        
        const matchesSearch = rowText.indexOf(searchInput) > -1;
        
        let matchesStatus = false;
        if (statusFilter === '') {
            matchesStatus = true;
        } else if (statusFilter === 'action_required') {
            // Smart Action Required Logic:
            // 1. Needs signature (Draft or To Sign)
            const needsSignature = ['pending_quotation', 'awaiting_caterer'].includes(rawStatus);
            // 2. Has pending payment proof to verify
            const needsPaymentVerify = ['proof_submitted', 'balance_proof_submitted'].includes(payStatus);
            // 3. Urgent upcoming event (detected by backend in dataset)
            const isUrgent = row.dataset.isUrgent === 'true';
            
            matchesStatus = needsSignature || needsPaymentVerify || isUrgent;
        } else {
            matchesStatus = rawStatus === statusFilter;
        }
        
        return matchesSearch && matchesStatus;
    });

    currentPage = 1;
    showPage(1);
}

function showPage(page) {
    const totalPages = Math.ceil(filteredRows.length / ROWS_PER_PAGE) || 1;
    if (page < 1) page = 1;
    if (page > totalPages) page = totalPages;
    currentPage = page;

    const startIdx = (page - 1) * ROWS_PER_PAGE;
    const endIdx = startIdx + ROWS_PER_PAGE;

    document.querySelectorAll('.bookings-list-table tbody tr.booking-row-item').forEach(function(r) { r.style.display = 'none'; });
    filteredRows.slice(startIdx, endIdx).forEach(function(r) { r.style.display = ''; });

    const searchEmpty = document.getElementById('searchEmptyState');
    if (searchEmpty) {
        searchEmpty.style.display = filteredRows.length === 0 ? '' : 'none';
    }

    renderPaginationControls(totalPages);

    var s = document.getElementById('startRange');
    var e = document.getElementById('endRange');
    var t = document.getElementById('totalEntries');
    if (s && e && t) {
        s.innerText = filteredRows.length === 0 ? 0 : startIdx + 1;
        e.innerText = Math.min(endIdx, filteredRows.length);
        t.innerText = filteredRows.length;
    }
}

function renderPaginationControls(totalPages) {
    var pageNumbers = document.getElementById('pageNumbers');
    var prevBtn = document.getElementById('prevPage');
    var nextBtn = document.getElementById('nextPage');
    if (!pageNumbers || !prevBtn || !nextBtn) return;

    pageNumbers.innerHTML = '';
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === totalPages || filteredRows.length === 0;
    prevBtn.onclick = function() { showPage(currentPage - 1); };
    nextBtn.onclick = function() { showPage(currentPage + 1); };

    if (filteredRows.length === 0) return;

    for (var i = 1; i <= totalPages; i++) {
        var btn = document.createElement('button');
        btn.className = 'page-num-btn' + (i === currentPage ? ' active' : '');
        var isActive = i === currentPage;
        btn.style.cssText = 'width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:0.4rem;border:1px solid ' + (isActive ? 'var(--primary-color)' : '#e2e8f0') + ';background:' + (isActive ? 'var(--primary-color)' : 'white') + ';color:' + (isActive ? 'white' : '#475569') + ';font-size:0.85rem;font-weight:700;cursor:pointer;transition:all 0.2s;';
        btn.innerText = i;
        (function(pg) { btn.onclick = function() { showPage(pg); }; })(i);
        pageNumbers.appendChild(btn);
    }
}

function filterBySignature() {
    const si = document.getElementById('bookingSearchInput');
    if (si) si.value = ''; // Clear search to show all actionable items
    
    var sf = document.getElementById('statusFilter');
    if (sf) { 
        sf.value = 'action_required'; 
        filterBookings(); 
    }
    const tc = document.querySelector('.bookings-list-section') || document.querySelector('.b-table-container');
    if (tc) tc.scrollIntoView({ behavior: 'smooth' });
}

// ─── MODAL: NEW BOOKING ──────────────────────────────────────────────────────

function openWalkinModal() {
    bk_openModal('walkinBookingModal');
    var form = document.getElementById('walkinBookingForm');
    if (form) form.dispatchEvent(new Event('input', { bubbles: true }));
}

function closeWalkinModal() {
    bk_closeModal('walkinBookingModal');
    var form = document.getElementById('walkinBookingForm');
    if (form) {
        form.reset();
        form.querySelectorAll('.is-invalid').forEach(function(el) { el.classList.remove('is-invalid'); });
    }
}

async function submitWalkinBooking(e) {
    if (e && e.preventDefault) e.preventDefault();
    const form = document.getElementById('walkinBookingForm');

    // 1. Check for ValidationManager errors
    if (form.querySelectorAll('.is-invalid').length > 0) {
        window.showError('Please fix the errors highlighted in red before submitting.');
        return;
    }

    // 2. HTML5 Check
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const btn = document.getElementById('walkinSubmitBtn');
    const originalContent = btn ? btn.innerHTML : 'Submit';

    // 3. Data Prep
    const formData = new FormData(form);
    const data = {};
    for (let [key, value] of formData.entries()) {
        if (key === 'total_amount') {
            data[key] = parseFloat(value.replace(/[₱,]/g, '')) || 0;
        } else {
            data[key] = value;
        }
    }

    // 4. Guest Capacity Check (Double Check)
    const pkgSelect = document.getElementById('bookPackage');
    if (pkgSelect && pkgSelect.value !== "") {
        const option = pkgSelect.options[pkgSelect.selectedIndex];
        const minGuests = parseInt(option.dataset.min) || 0;
        if (parseInt(data.guest_count) < minGuests) {
            window.showError(`The selected package requires at least ${minGuests} guests.`);
            return;
        }
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
    }

    try {
        const response = await fetch('/caterer/api/bookings/manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        if (response.ok && result.status === 'success') {
            if (window.showToast) window.showToast("Manual booking recorded successfully!", "success");
            closeWalkinModal();
            setTimeout(() => window.location.reload(), 1500);
        } else {
            const errorMsg = result.detail || result.message || "Failed to create booking.";
            window.showError(errorMsg);
        }
    } catch (err) {
        console.error('Error submitting manual booking:', err);
        window.showError("A connection error occurred. Please try again.");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalContent;
        }
    }
}

// ─── MODAL: EXPENSE TRACKER ──────────────────────────────────────────────────

function openExpenseTracker(bookingId, btn) {
    document.getElementById('expenseBookingId').value = bookingId;
    
    // Set Total Budget from data attribute
    var totalAmount = 0;
    if (btn) {
        totalAmount = parseFloat(btn.getAttribute('data-total-amount')) || 0;
        document.getElementById('bookingTotalAmount').value = totalAmount;
    }
    
    var modalTotal = document.getElementById('modalBookingTotal');
    if (modalTotal) modalTotal.innerText = '₱' + totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    bk_openModal('expenseTrackerModal');
    var container = document.getElementById('actualExpenseRows');
    if (!container) return;
    container.innerHTML = '';

    var breakdown = [];
    if (btn) {
        try {
            var breakdownStr = btn.getAttribute('data-breakdown');
            if (breakdownStr) {
                var unescaped = breakdownStr.replace(/&quot;/g, '"');
                breakdown = JSON.parse(unescaped);
                if (typeof breakdown === 'string') breakdown = JSON.parse(breakdown);
            }
        } catch (e) { breakdown = []; }
    }

    if (breakdown && breakdown.length > 0) {
        breakdown.forEach(function(exp) {
            var row = document.createElement('div');
            row.className = 'd-flex gap-2 mb-2 expense-item-row';
            row.innerHTML = '<input type="text" class="form-control form-control-sm exp-name" value="' + exp.name + '" placeholder="Item" style="flex:2;"><input type="number" class="form-control form-control-sm exp-amount" value="' + exp.amount + '" min="0" oninput="calculateActualExpenses()" style="flex:1;"><button type="button" class="btn btn-sm btn-light text-danger" onclick="this.parentElement.remove();calculateActualExpenses()"><i class="fas fa-times"></i></button>';
            container.appendChild(row);
        });
    } else {
        addExpenseRow();
    }
    calculateActualExpenses();
}

function closeExpenseTracker() {
    bk_closeModal('expenseTrackerModal');
    var form = document.getElementById('expenseTrackerForm');
    if (form) form.reset();
}

function addExpenseRow() {
    var container = document.getElementById('actualExpenseRows');
    var row = document.createElement('div');
    row.className = 'd-flex gap-2 mb-2 expense-item-row';
    row.innerHTML = '<input type="text" class="form-control form-control-sm exp-name" placeholder="Item (e.g. Labor)" style="flex:2;"><input type="number" class="form-control form-control-sm exp-amount" placeholder="₱ 0.00" min="0" oninput="calculateActualExpenses()" style="flex:1;"><button type="button" class="btn btn-sm btn-light text-danger" onclick="this.parentElement.remove();calculateActualExpenses()"><i class="fas fa-times"></i></button>';
    container.appendChild(row);
}

function calculateActualExpenses() {
    var totalExpense = 0;
    document.querySelectorAll('#actualExpenseRows .expense-item-row').forEach(function(row) {
        totalExpense += parseFloat(row.querySelector('.exp-amount').value) || 0;
    });
    
    var bookingTotal = parseFloat(document.getElementById('bookingTotalAmount').value) || 0;
    var profit = bookingTotal - totalExpense;
    var roi = totalExpense > 0 ? (profit / totalExpense) * 100 : 0;
    
    // Update Displays
    var display = document.getElementById('totalActualExpenseDisplay');
    if (display) display.innerText = '₱' + totalExpense.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    
    var profitDisplay = document.getElementById('modalEstimateProfit');
    if (profitDisplay) {
        profitDisplay.innerText = '₱' + profit.toLocaleString(undefined, { minimumFractionDigits: 2 });
        profitDisplay.style.color = profit >= 0 ? '#10b981' : '#ef4444';
    }
    
    var roiDisplay = document.getElementById('modalRoiPercent');
    if (roiDisplay) {
        var roiText = roiDisplay.querySelector('span');
        var roiIcon = document.getElementById('roiTrendIcon');
        
        if (roiText) roiText.innerText = Math.round(roi) + '%';
        
        if (roi >= 25) {
            roiDisplay.style.color = '#10b981';
            if (roiIcon) roiIcon.innerHTML = '<i class="fas fa-arrow-up" style="color:#10b981; font-size: 0.8rem;"></i>';
        } else if (roi >= 10) {
            roiDisplay.style.color = '#f59e0b';
            if (roiIcon) roiIcon.innerHTML = '<i class="fas fa-arrow-right" style="color:#f59e0b; font-size: 0.8rem;"></i>';
        } else {
            roiDisplay.style.color = '#ef4444';
            if (roiIcon) roiIcon.innerHTML = '<i class="fas fa-arrow-down" style="color:#ef4444; font-size: 0.8rem;"></i>';
            if (roi < 0) roiDisplay.classList.add('pulse-roi');
            else roiDisplay.classList.remove('pulse-roi');
        }
    }
    
    return totalExpense;
}

async function submitExpenses(e) {
    e.preventDefault();
    var btn = document.getElementById('saveExpenseBtn');
    if (!btn) return;
    btn.disabled = true;
    btn.innerText = 'Saving...';

    var bookingId = document.getElementById('expenseBookingId').value;
    var total = calculateActualExpenses();
    var breakdown = [];
    document.querySelectorAll('#actualExpenseRows .expense-item-row').forEach(function(row) {
        var name = row.querySelector('.exp-name').value;
        var amount = parseFloat(row.querySelector('.exp-amount').value) || 0;
        if (name && amount > 0) breakdown.push({ name: name, amount: amount });
    });

    try {
        var res = await fetch('/caterer/bookings/' + bookingId + '/actual-cost', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ actual_cost: total, actual_cost_breakdown: breakdown })
        });
        if (res.ok) {
            window.showSuccess('Actual expenses saved.');
            closeExpenseTracker();
            setTimeout(function() { window.location.reload(); }, 1500);
        } else {
            window.showError('Failed to save expenses');
        }
    } catch (err) {
        window.showError('Error saving expenses');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save"></i> Save Expenses';
    }
}

// ─── MODAL: BOOKING DETAILS ──────────────────────────────────────────────────

function showBookingDetails(btn) {
    var data = btn.dataset;
    currentBookingId = data.id;

    resetBookingTabs();

    document.getElementById('modalBookingId').innerText = 'Booking #' + data.id;
    
    // Urgent Indicator in Modal Header
    const headerTitle = document.getElementById('modalBookingId');
    if (data.isUrgent === 'true') {
        headerTitle.innerHTML = `Booking #${data.id} <span style="background: #fff1f2; color: #e11d48; font-size: 0.65rem; padding: 2px 8px; border-radius: 50px; margin-left: 8px; border: 1px solid #fecdd3; vertical-align: middle;"><i class="fas fa-clock"></i> URGENT</span>`;
    }

    document.getElementById('modalCustomer').innerText = data.customer;
    document.getElementById('modalEmail').innerText = data.email;
    document.getElementById('modalEventName').innerText = data.eventName;
    document.getElementById('modalEventType').innerText = data.eventType;
    document.getElementById('modalVenue').innerText = data.venue;
    document.getElementById('modalRequests').innerText = data.requests;

    var statusEl = document.getElementById('modalStatus');
    statusEl.innerText = data.status.replace(/_/g, ' ').toUpperCase();
    statusEl.className = 'premium-status-badge';
    var statusMap = {
        'pending': 'ps-badge-pending',
        'pending_quotation': 'ps-badge-draft',
        'awaiting_caterer': 'ps-badge-pending',
        'awaiting_payment': 'ps-badge-payment',
        'confirmed': 'ps-badge-confirmed',
        'preparing': 'ps-badge-preparing',
        'on_the_way': 'ps-badge-transit',
        'in_progress': 'ps-badge-ongoing',
        'completed': 'ps-badge-completed',
        'cancelled': 'ps-badge-cancelled'
    };
    statusEl.classList.add(statusMap[data.status] || 'ps-badge-draft');

    var menuSource = document.getElementById('booking-items-' + data.id);
    var menuTarget = document.getElementById('modalMenuItems');
    var menuSection = document.getElementById('modalMenuSection');
    if (menuSource && menuTarget) {
        menuTarget.innerHTML = menuSource.innerHTML;
        if (menuSection) menuSection.style.display = 'block';
    } else if (menuTarget) {
        menuTarget.innerHTML = '<p style="color:#64748b;font-size:0.9rem;">No menu items selected.</p>';
    }

    var proofUrl = data.proofUrl;
    var balanceProofUrl = data.balanceProofUrl;
    var proofSection = document.getElementById('modalProofSection');
    var proofContainer = document.getElementById('modalProofContainer');
    if (proofSection && proofContainer) {
        proofContainer.innerHTML = '';
        var hasProof = false;
        if (proofUrl) {
            hasProof = true;
            proofContainer.innerHTML += '<a href="' + proofUrl + '" target="_blank" class="modal-proof-item"><img src="' + proofUrl + '" class="modal-proof-img" onerror="this.src=\'/static/images/file-placeholder.png\'"><span class="modal-proof-label">Downpayment Proof</span></a>';
        }
        if (balanceProofUrl) {
            hasProof = true;
            proofContainer.innerHTML += '<a href="' + balanceProofUrl + '" target="_blank" class="modal-proof-item"><img src="' + balanceProofUrl + '" class="modal-proof-img" onerror="this.src=\'/static/images/file-placeholder.png\'"><span class="modal-proof-label">Balance Proof</span></a>';
        }
        proofSection.style.display = hasProof ? 'block' : 'none';
    }

    // RISK ALERT HANDLING
    var riskAlert = document.getElementById('modalRiskAlert');
    var riskMsg = document.getElementById('modalRiskMessage');
    if (riskAlert) {
        // Risk alert UI removed as requested
        riskAlert.style.display = 'none';
    }

    var actionsEl = document.getElementById('bookingModalActions');
    const isVerified = data.isVerified === 'true' || data.isVerified === true;
    const targetUserId = data.targetUserId;

    if (actionsEl) {
        actionsEl.innerHTML = '';
        
        const isPackage = data.isPackage === 'true' || data.isPackage === true;
        
        // --- KYC WARNING BANNER ---
        // Only show for Event Packages. Skip for Ala Carte / Food Orders.
        if (!isVerified && targetUserId && isPackage) {
            actionsEl.innerHTML = `
                <div style="width:100%; margin-bottom: 1rem; background:#fff7ed; border:1px solid #fed7aa; padding:1rem; border-radius:0.75rem; display:flex; align-items:center; gap:0.75rem;">
                    <div style="width:40px; height:40px; background:#ffedd5; color:#f97316; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:1.2rem;">
                        <i class="fas fa-shield-exclamation"></i>
                    </div>
                    <div style="flex:1;">
                        <h4 style="margin:0; font-size:0.85rem; color:#9a3412; font-weight:800;">UNVERIFIED CUSTOMER</h4>
                        <p style="margin:2px 0 0; font-size:0.75rem; color:#c2410c;">Audit their identity before accepting this booking to prevent fraud.</p>
                    </div>
                    <a href="/caterer/compliance/view/${targetUserId}" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#fdba74; color:#9a3412;">
                        <i class="fas fa-search"></i> Audit Now
                    </a>
                </div>
            `;
        }

        const plan = (data.paymentPlan || 'downpayment').toUpperCase();
        
        if (data.status === 'pending') {
            const isPayment = data.paymentStatus === 'proof_submitted';
            const btnLabel = isPayment ? `Verify ${plan} & Accept` : 'Confirm & Accept Booking';
            const btnIcon = isPayment ? 'fa-check-double' : 'fa-check-circle';
            
            actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.confirmAcceptBooking(${data.id}, ${isPayment}, ${isVerified}, ${isPackage})"><i class="fas ${btnIcon}"></i> ${btnLabel}</button>`;
            if (isPayment) actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-reject" onclick="window.requestNewProof(${data.id})" style="background:#64748b;"><i class="fas fa-redo"></i> Request New Proof</button>`;
            actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-reject" onclick="window.confirmRejectBooking(${data.id})"><i class="fas fa-times-circle"></i> Reject Booking</button>`;
            
        } else if (data.status === 'awaiting_caterer') {
            actionsEl.innerHTML = `<a href="/caterer/bookings/${data.id}/sign" class="btn-footer-action btn-status-confirm" style="text-decoration:none;"><i class="fas fa-pen-nib"></i> Sign Contract Now</a><button type="button" class="btn-footer-action btn-status-reject" onclick="window.confirmRejectBooking(${data.id})"><i class="fas fa-times-circle"></i> Reject</button>`;
            
        } else {
            // ─── CONSOLIDATED OPERATIONAL LIFECYCLE ───
            // Both Ala Carte (8 Steps) and Package (6 Steps) share these event milestones
            if (data.status === 'confirmed') {
                if (data.paymentStatus === 'balance_proof_submitted') {
                    actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-confirm pulse-update" onclick="window.confirmAcceptBooking(${data.id}, true)" style="margin-bottom:0.5rem;width:100%;"><i class="fas fa-check-double"></i> Verify Final Balance</button>`;
                }
                actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(${data.id}, 'preparing')" style="background:#5b5a9c;"><i class="fas fa-utensils"></i> Start Preparation</button>`;
            } else if (data.status === 'preparing') {
                if (data.venue === 'PICKUP') {
                    actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'ready_for_pickup\')" style="background:#10b981;"><i class="fas fa-shopping-bag"></i> Mark as Ready for Pickup</button>';
                } else {
                    actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'ready_for_delivery\')" style="background:#10b981;"><i class="fas fa-box"></i> Mark as Ready for Delivery</button>';
                }
            } else if (data.status === 'ready_for_pickup') {
                actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-complete" onclick="window.confirmCompleteBooking(' + data.id + ')"><i class="fas fa-flag-checkered"></i> Mark as Picked Up (Complete)</button>';
            } else if (data.status === 'ready_for_delivery') {
                actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'on_the_way\')" style="background:#0ea5e9;"><i class="fas fa-truck"></i> Out for Delivery</button>';
            } else if (data.status === 'on_the_way') {
                actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'arrived\')" style="background:#6366f1;"><i class="fas fa-map-marker-alt"></i> Arrived at Location</button>';
            } else if (data.status === 'arrived') {
                actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'setup_ongoing\')" style="background:#f97316;"><i class="fas fa-magic"></i> Setup & Serve</button>';
            } else if (data.status === 'setup_ongoing' || data.status === 'in_progress') {
                if (data.paymentStatus === 'paid' || data.amount === "₱0.00" || data.paymentPlan === 'full') {
                    const btnLabel = isPackage ? 'Mark as Done (Step 6)' : 'Mark as Completed';
                    actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-complete" onclick="window.confirmCompleteBooking(' + data.id + ')"><i class="fas fa-flag-checkered"></i> ' + btnLabel + '</button>';
                } else {
                    if (data.paymentStatus === 'balance_proof_submitted') {
                        actionsEl.innerHTML = `<button type="button" class="btn-footer-action btn-status-confirm pulse-update" onclick="window.confirmAcceptBooking(${data.id}, true)" style="margin-bottom:0.5rem;width:100%;"><i class="fas fa-check-double"></i> Verify Final Balance</button>`;
                    }
                    const lockMsg = isPackage ? 'Step 6 Locked: Final Payment Required' : 'Bill Settlement Required to Complete';
                    actionsEl.innerHTML += `<div class="completion-pending-hint" style="background:#fff7ed;color:#c2410c;padding:0.75rem;border-radius:0.75rem;font-size:0.85rem;font-weight:600;display:flex;align-items:center;gap:0.5rem;width:100%;"><i class="fas fa-lock"></i> ${lockMsg}</div>`;
                    if (data.paymentStatus === 'balance_proof_submitted') {
                        actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-reject" onclick="window.requestNewProof(${data.id})" style="margin-top:0.5rem; width:100%;"><i class="fas fa-undo"></i> Request Correct Balance Proof</button>`;
                    }
                }
            } else if (data.status === 'completed' || data.status === 'cancelled') {
                const archiveLabel = isPackage ? 'Archive Package Record' : 'Archive Booking';
                actionsEl.innerHTML = '<button type="button" class="btn-footer-action" style="background:#fef3c7;color:#92400e;border:1px solid #fcd34d;flex:1;" onclick="window.confirmArchiveBooking(' + data.id + ')"><i class="fas fa-archive"></i> ' + archiveLabel + '</button>';
            }
        }
    }

    document.getElementById('modalBookedOn').innerText = data.bookedOn;
    document.getElementById('modalPaymentMethod').innerText = `Method: ${data.paymentMethod} (${(data.paymentPlan || 'downpayment').toUpperCase()})`;
    document.getElementById('modalTotalAmount').innerText = data.amount;
    document.getElementById('modalGuestCount').innerText = data.guestCount + ' Guests';
    // Handle Due Date section display logic
    const dueDateCard = document.querySelector('.due-date-card-premium');
    const modalDueDate = document.getElementById('modalDueDate');
    const badgeContainer = document.getElementById('dueDateBadgeContainer');
    
    if (data.paymentPlan === 'full') {
        if (dueDateCard) dueDateCard.closest('.occ-form-group').style.display = 'none';
    } else {
        if (dueDateCard) dueDateCard.closest('.occ-form-group').style.display = 'block';
        if (!data.balanceDue) {
            modalDueDate.innerHTML = '<span style="color:#ef4444;"><i class="fas fa-exclamation-circle"></i> Needs Deadline</span>';
            if (badgeContainer) badgeContainer.innerHTML = '<span class="due-date-badge missing">Action Required</span>';
        } else {
            // Simple format for display
            const parts = data.balanceDue.split('-');
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const formatted = `${months[parseInt(parts[1])-1]} ${parts[2]}, ${parts[0]}`;
            modalDueDate.innerText = formatted;
            if (badgeContainer) badgeContainer.innerHTML = '<span class="due-date-badge"><i class="fas fa-check-circle"></i> Deadline Set</span>';
        }
    }

    document.getElementById('dueDateDisplaySection').style.display = 'block';
    document.getElementById('dueDateEditSection').style.display = 'none';
    document.getElementById('balanceDueDateInput').value = data.balanceDue || '';
    // Ensure min date is today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('balanceDueDateInput').min = today;

    var pStatusEl = document.getElementById('modalPaymentStatus');
    var pLabels = { 'paid': 'Fully Paid', 'deposit_paid': 'Downpayment Paid', 'proof_submitted': 'Proof Sent', 'balance_proof_submitted': 'Balance Proof Sent', 'pending': 'Payment Pending' };
    if (pStatusEl) {
        pStatusEl.innerText = pLabels[data.paymentStatus] || data.paymentStatus;
        pStatusEl.className = 'premium-status-badge';
        if (data.paymentStatus === 'paid' || data.paymentStatus === 'deposit_paid') pStatusEl.classList.add('ps-badge-confirmed');
        else if (data.paymentStatus === 'proof_submitted' || data.paymentStatus === 'balance_proof_submitted') pStatusEl.classList.add('ps-badge-payment');
        else pStatusEl.classList.add('ps-badge-cancelled');
    }

    // Load Checklist Tasks
    loadBookingTasks(data.id);
    
    // Load History
    loadBookingHistory(data.id);
    
    // Load Notes
    const notesEl = document.getElementById('modalCatererNotes');
    if (notesEl) notesEl.value = btn.dataset.catererNotes || '';
    
    // Update Stepper
    updateBookingStepper(data.status);

    bk_openModal('bookingDetailModal');
}

function bk_closeBookingDetailModal() { bk_closeModal('bookingDetailModal'); }

function switchBookingTab(tabId) {
    document.querySelectorAll('.mtab-pane-pro').forEach(function(p) { p.classList.remove('active'); });
    document.querySelectorAll('.mtab-btn-pro').forEach(function(b) { b.classList.remove('active'); });
    var pane = document.getElementById('btab-' + tabId);
    if (pane) pane.classList.add('active');
    if (event && event.currentTarget) event.currentTarget.classList.add('active');
}

function resetBookingTabs() {
    document.querySelectorAll('.mtab-pane-pro').forEach(function(p) { p.classList.remove('active'); });
    document.querySelectorAll('.mtab-btn-pro').forEach(function(b) { b.classList.remove('active'); });
    var summaryTab = document.getElementById('btab-summary');
    if (summaryTab) summaryTab.classList.add('active');
    var firstBtn = document.querySelector('.mtab-btn-pro');
    if (firstBtn) firstBtn.classList.add('active');
}

// ─── NEW: AUDIT HISTORY ──────────────────────────────────────────────────────

async function loadBookingHistory(bookingId) {
    const container = document.getElementById('modalHistoryTimeline');
    if (!container) return;
    
    try {
        const res = await fetch(`/caterer/api/bookings/${bookingId}/history`);
        const history = await res.json();
        
        if (history && history.length > 0) {
            container.innerHTML = history.map(item => `
                <div class="timeline-item-pro ${item === history[0] ? 'active' : ''}">
                    <div class="timeline-icon-pro">
                        <i class="fas fa-check"></i>
                    </div>
                    <div class="timeline-content-pro">
                        <div class="timeline-meta-pro">
                            <span class="timeline-status-pro">${item.status.replace(/_/g, ' ')}</span>
                            <span class="timeline-date-pro">${item.created_at_formatted}</span>
                        </div>
                        <div class="timeline-note-pro">${item.notes || 'Status changed automatically.'}</div>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div style="text-align:center;padding:2rem;color:#94a3b8;">No history records found.</div>';
        }
    } catch (err) {
        container.innerHTML = '<div style="text-align:center;padding:2rem;color:#ef4444;">Failed to load history audit trail.</div>';
    }
}

// ─── NEW: CATERER NOTES ──────────────────────────────────────────────────────

async function saveCatererNotes() {
    const notes = document.getElementById('modalCatererNotes').value;
    const btn = event.currentTarget;
    const originalText = btn.innerText;
    
    btn.disabled = true;
    btn.innerText = 'Saving...';
    
    try {
        const res = await fetch(`/caterer/api/bookings/${currentBookingId}/notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: notes })
        });
        
        if (res.ok) {
            window.showSuccess('Notes saved successfully.');
            // Update the data attribute on the view button to persist change
            const viewBtn = document.querySelector(`.view-details[data-id="${currentBookingId}"]`);
            if (viewBtn) viewBtn.dataset.catererNotes = notes;
        } else {
            window.showError('Failed to save notes.');
        }
    } catch (err) {
        window.showError('Error connecting to server.');
    } finally {
        btn.disabled = false;
        btn.innerText = originalText;
    }
}

// ─── NEW: STEPPER LOGIC ──────────────────────────────────────────────────────

function updateBookingStepper(status) {
    const steps = ['pending', 'confirmed', 'preparing', 'on_the_way', 'in_progress', 'completed'];
    const currentIdx = steps.indexOf(status);
    
    document.querySelectorAll('.step-pro').forEach((step, idx) => {
        const dot = step.querySelector('.step-dot');
        step.classList.remove('active', 'completed');
        
        if (idx < currentIdx) {
            step.classList.add('completed');
            if (dot) dot.innerHTML = '<i class="fas fa-check"></i>';
        } else if (idx === currentIdx) {
            step.classList.add('active');
            if (dot) dot.innerHTML = idx + 1;
        } else {
            if (dot) dot.innerHTML = idx + 1;
        }
        
        // Handle specific labels for sub-statuses
        if (status === 'awaiting_payment' || status === 'pending_quotation' || status === 'awaiting_caterer') {
            if (idx === 0) {
                step.classList.add('active');
                if (dot) dot.innerHTML = '1';
            }
        }
    });
}

// ─── CONTRACT MODAL ──────────────────────────────────────────────────────────

var currentBookingIdForContract = null;
function openContractModal(bookingId) {
    currentBookingIdForContract = bookingId;
    var body = document.getElementById('contractModalBody');
    if (!body) return;
    body.innerHTML = '<div style="text-align:center;padding:4rem;"><i class="fas fa-circle-notch fa-spin fa-3x" style="color:var(--primary-color);"></i></div>';
    bk_openModal('contractModal');
    fetch('/caterer/api/bookings/' + bookingId + '/contract/content')
        .then(function(r) { return r.text(); })
        .then(function(html) { body.innerHTML = html; })
        .catch(function() { body.innerHTML = '<p style="color:#ef4444;text-align:center;">Failed to load contract.</p>'; });
}

function closeContractModal() { bk_closeModal('contractModal'); }

function printContract(bookingId) {
    var url = '/caterer/bookings/' + bookingId + '/contract';
    var w = window.open(url, '_blank');
    if (w) w.onload = function() { w.print(); };
}

// ─── DUE DATE ────────────────────────────────────────────────────────────────

function toggleDueDateEdit() {
    var display = document.getElementById('dueDateDisplaySection');
    var edit = document.getElementById('dueDateEditSection');
    var btnEdit = document.getElementById('btnEditDueDate');
    if (!display || !edit) return;
    if (display.style.display === 'none') {
        display.style.display = 'block';
        edit.style.display = 'none';
        if (btnEdit) btnEdit.style.display = 'inline-flex';
    } else {
        display.style.display = 'none';
        edit.style.display = 'block';
        if (btnEdit) btnEdit.style.display = 'none';
    }
}

async function saveDueDate() {
    var newDate = document.getElementById('balanceDueDateInput').value;
    if (!newDate) { window.showError('Please select a valid date.'); return; }
    var today = new Date().toISOString().split('T')[0];
    if (newDate < today) { window.showError('Please select a current or future date.'); return; }
    try {
        var response = await fetch('/caterer/api/bookings/' + currentBookingId + '/set-due-date', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ due_date: newDate })
        });
        if (response.ok) {
            // Local UI Update
            const parts = newDate.split('-');
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const formatted = `${months[parseInt(parts[1])-1]} ${parts[2]}, ${parts[0]}`;
            
            document.getElementById('modalDueDate').innerText = formatted;
            const badgeContainer = document.getElementById('dueDateBadgeContainer');
            if (badgeContainer) badgeContainer.innerHTML = '<span class="due-date-badge"><i class="fas fa-check-circle"></i> Deadline Set</span>';
            
            toggleDueDateEdit();
            
            var btn = document.querySelector('.view-details[data-id="' + currentBookingId + '"]');
            if (btn) btn.dataset.balanceDue = newDate;
            
            window.showSuccess('Payment deadline updated and customer has been notified!');
        } else {
            var err = await response.json();
            window.showError(err.detail || 'Failed to update due date.');
        }
    } catch (error) { window.showError('An error occurred.'); }
}

async function runAIScan() {
    const resultsPanel = document.getElementById('aiScanResults');
    const content = document.getElementById('aiScanContent');
    const badge = document.getElementById('aiConfidenceBadge');
    const flags = document.getElementById('aiScanFlags');
    const btn = document.getElementById('aiVerifyBtn');

    if (!resultsPanel || !btn) return;

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Scanning...';
    resultsPanel.style.display = 'block';
    content.innerHTML = '<p class="text-muted italic">Engine processing image pixels and cross-referencing ledger data...</p>';
    badge.innerHTML = '';
    flags.innerHTML = '';

    try {
        const res = await fetch(`/caterer/api/bookings/${currentBookingId}/verify-proof`, { method: 'POST' });
        const result = await res.json();

        if (result.status === 'success') {
            const data = result.data;
            const score = data.confidence;
            const isNonDoc = data.flags.some(f => f.includes('Non-Document'));
            
            // Render Badge with clearer status labels
            let config = { icon: 'fa-shield-alt', color: '#e11d48', label: 'CRITICAL RISK', bg: '#fff1f2' };
            if (score >= 80) config = { icon: 'fa-check-double', color: '#10b981', label: 'LEGIT', bg: '#f0fdf4' };
            else if (score >= 40) config = { icon: 'fa-exclamation-triangle', color: '#f59e0b', label: 'SUSPICIOUS', bg: '#fffbeb' };
            
            badge.innerHTML = `<div class="ai-confidence-indicator" style="background:${config.bg}; color:${config.color};"><i class="fas ${config.icon}"></i> ${config.label} (${score}% Match)</div>`;

            // Premium Grid Layout - Only show if it's a document
            const extr = data.extracted_data;
            if (isNonDoc) {
                content.innerHTML = `
                    <div style="padding:1rem; text-align:center; color:#64748b; font-style:italic;">
                        <i class="fas fa-image-slash fa-2x mb-2 opacity-50"></i><br>
                        Statistical analysis aborted. Image does not contain receipt-like data.
                    </div>
                `;
            } else {
                content.innerHTML = `
                    <div class="ai-stat-grid mt-3">
                        <div class="ai-stat-item"><span class="ai-stat-label">REF NO.</span><span class="ai-stat-value">${extr.reference_no || 'Missing'}</span></div>
                        <div class="ai-stat-item"><span class="ai-stat-label">AMOUNT</span><span class="ai-stat-value">₱${(extr.amount || 0).toLocaleString()}</span></div>
                        <div class="ai-stat-item"><span class="ai-stat-label">DATE</span><span class="ai-stat-value">${extr.date || 'Unknown'}</span></div>
                    </div>
                `;
            }

            // Render Flags in Pilled list
            if (data.flags && data.flags.length > 0) {
                flags.innerHTML = '<div class="ai-flags-container">' + 
                    data.flags.map(f => {
                        const isDanger = f.toLowerCase().includes('fraud') || f.toLowerCase().includes('risk') || f.toLowerCase().includes('mismatch') || f.toLowerCase().includes('invalid');
                        const flagClass = isDanger ? 'ai-flag-danger' : 'ai-flag-warning';
                        const flagIcon = isDanger ? 'fa-exclamation-triangle' : 'fa-flag';
                        return `<div class="ai-flag-item ${flagClass}"><i class="fas ${flagIcon}"></i> ${f}</div>`;
                    }).join('') + 
                    '</div>';
            } else {
                flags.innerHTML = '<div class="ai-flag-item ai-flag-success"><i class="fas fa-check-double"></i> All data points matched perfectly. No fraud detected.</div>';
            }
        } else {
            content.innerHTML = `<div class="ai-flag-item ai-flag-danger"><i class="fas fa-exclamation-circle"></i> ${result.message || 'Verification failed.'}</div>`;
        }
    } catch (err) {
        content.innerHTML = '<div class="ai-flag-item ai-flag-danger"><i class="fas fa-wifi-slash"></i> Service unavailable.</div>';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-microchip me-1"></i> Run AI Scan Again';
        resultsPanel.classList.add('ai-report-panel'); // Switch to new class
    }
}

function confirmAcceptBooking(bookingId, isPayment, isVerified, isPackage) {
    isPayment = isPayment || false;
    isVerified = isVerified === undefined ? true : isVerified; 
    isPackage = isPackage === undefined ? false : isPackage;
    
    // --- KYC GATEKEEPER ---
    // Only enforce for Packages. Ala Carte is exempt.
    if (!isVerified && isPackage) {
        window.showAlert({
            type: 'warning',
            title: 'Customer Not Verified',
            message: 'This customer has not submitted identity verification (KYC). Are you sure you want to accept this booking?<br><br><small style="color:#64748b;">Recommendation: Audit their identity on the Compliance page first to prevent fake bookings.</small>',
            confirmText: 'Accept Anyway',
            cancelText: 'Go to Audit',
            onConfirm: () => {
                proceedWithAcceptance(bookingId, isPayment);
            }
        });
        return;
    }

    proceedWithAcceptance(bookingId, isPayment);
}

async function proceedWithAcceptance(bookingId, isPayment) {
    let confirmMsg = isPayment ? 'Have you received the payment from the customer?' : 'Do you want to accept this booking even without payment proof?';
    let confirmTitle = isPayment ? 'Confirm Payment?' : 'Accept Booking Manually?';
    let confirmBtn = isPayment ? 'Yes, Verify Payment' : 'Yes, Accept Booking';

    window.showConfirm(confirmMsg,
        async function() {
            var url = isPayment ? '/caterer/payments/' + bookingId + '/confirm' : '/caterer/bookings/' + bookingId + '/accept';
            var result = await window.apiAction(url, { method: 'POST' });
            if (result && result.status === 'success') {
                bk_closeBookingDetailModal();
                if (typeof window.refreshDashboardData === 'function') window.refreshDashboardData();
                else window.location.reload();
            }
        },
        confirmTitle, confirmBtn
    );
}

let rejectionBookingId = null;

function confirmRejectBooking(bookingId) {
    rejectionBookingId = bookingId;
    document.getElementById('rejectReasonInput').value = '';
    bk_openModal('rejectReasonModal');
}

async function submitRejectionWithReason() {
    const reason = document.getElementById('rejectReasonInput').value.trim();
    if (!reason) {
        window.showError('Please provide a reason for the rejection.');
        return;
    }
    
    const btn = event.currentTarget;
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Rejecting...';
    
    try {
        const response = await fetch(`/caterer/bookings/${rejectionBookingId}/reject`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason: reason })
        });
        
        const data = await response.json();
        if (response.ok && data.status === 'success') {
            window.showSuccess('Booking rejected and customer notified.');
            bk_closeModal('rejectReasonModal');
            bk_closeModal('bookingDetailModal');
            setTimeout(() => location.reload(), 1500);
        } else {
            window.showError(data.detail || 'Failed to reject booking.');
        }
    } catch (err) {
        window.showError('Error connecting to server.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function confirmCompleteBooking(bookingId) {
    window.showConfirm('Is the event finished and everything settled?',
        async function() {
            const actionBtn = event.target.closest('.btn-footer-action');
            if (actionBtn) {
                const originalHtml = actionBtn.innerHTML;
                actionBtn.disabled = true;
                actionBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            }

            var result = await window.apiAction('/caterer/bookings/' + bookingId + '/update-status', { 
                method: 'POST', 
                body: JSON.stringify({status: 'completed'}) 
            });

            if (result && result.status === 'success') {
                window.showToast('Booking successfully marked as Completed! Great job!', 'success');
                
                if (typeof window.showBookingDetails === 'function') {
                    window.showBookingDetails(bookingId);
                }
                
                const rowBadge = document.querySelector(`#booking-row-${bookingId} .premium-status-badge`);
                if (rowBadge) {
                    rowBadge.innerText = 'Completed';
                    rowBadge.className = 'premium-status-badge ps-badge-completed';
                    const row = document.getElementById(`booking-row-${bookingId}`);
                    if (row) row.dataset.status = 'completed';
                }
            } else if (actionBtn) {
                actionBtn.disabled = false;
                actionBtn.innerHTML = originalHtml;
            }
        },
        'Mark as Completed?', 'Yes, Event Finished'
    );
}

function updateBookingStage(bookingId, status) {
    const labels = {
        'preparing': 'Start cooking and preparation?',
        'ready_for_delivery': 'Is the order packed and ready for delivery?',
        'ready_for_pickup': 'Is the order ready for the customer to pick up?',
        'on_the_way': 'Is the team/rider currently in transit to the location?',
        'arrived': 'Has the order/team arrived at the venue?',
        'setup_ongoing': 'Has the setup and food service started?',
        'in_progress': 'Has the event serving officially started?'
    };
    const titles = {
        'preparing': 'Start Preparation?',
        'ready_for_delivery': 'Mark as Ready?',
        'ready_for_pickup': 'Ready for Pickup?',
        'on_the_way': 'Dispatch Order?',
        'arrived': 'Order Arrived?',
        'setup_ongoing': 'Start Setup?',
        'in_progress': 'Start Event?'
    };

    window.showConfirm(labels[status] || 'Are you sure you want to proceed?',
        async function() {
            // Add Loading State to the button in the modal
            const actionBtn = event.target.closest('.btn-footer-action');
            if (actionBtn) {
                const originalHtml = actionBtn.innerHTML;
                actionBtn.disabled = true;
                actionBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            }

            var result = await window.apiAction('/caterer/bookings/' + bookingId + '/update-status', { 
                method: 'POST', 
                body: JSON.stringify({ status: status }) 
            });

            if (result && result.status === 'success') {
                window.showToast('Status updated successfully and customer notified.', 'success');
                
                // 1. Immediate Modal Refresh
                if (typeof window.showBookingDetails === 'function') {
                    window.showBookingDetails(bookingId);
                }
                // 2. Immediate Table Row Update (Local Sync)
                const rowBadge = document.querySelector(`#booking-row-${bookingId} .premium-status-badge`);
                if (rowBadge) {
                    const statusLabels = {
                        'preparing': 'Preparing',
                        'ready_for_delivery': 'Ready',
                        'on_the_way': 'In Transit',
                        'arrived': 'Arrived',
                        'setup_ongoing': 'Setup',
                        'in_progress': 'Ongoing',
                        'completed': 'Completed'
                    };
                    const statusClasses = {
                        'preparing': 'ps-badge-preparing',
                        'ready_for_delivery': 'ps-badge-ready',
                        'on_the_way': 'ps-badge-transit',
                        'arrived': 'ps-badge-arrived',
                        'setup_ongoing': 'ps-badge-ongoing',
                        'in_progress': 'ps-badge-ongoing',
                        'completed': 'ps-badge-completed'
                    };
                    rowBadge.innerText = statusLabels[status] || status.toUpperCase();
                    rowBadge.className = 'premium-status-badge ' + (statusClasses[status] || '');
                    
                    // Also update row data attribute for filtering
                    const row = document.getElementById(`booking-row-${bookingId}`);
                    if (row) row.dataset.status = status;
                }
            } else {
                // Reset button if error
                if (actionBtn) {
                    actionBtn.disabled = false;
                    actionBtn.innerHTML = originalHtml;
                }
            }
        },
        titles[status] || 'Update Status', 'Yes, Proceed'
    );
}

function requestNewProof(bookingId) {
    var reason = prompt("Why are you rejecting this? (e.g. 'Unreadable image', 'Wrong amount', 'Fake receipt')");
    if (reason === null) return;

    window.showConfirm('Are you sure you want to reject this proof and send a notification to the customer?',
        async function() {
            var result = await window.apiAction('/caterer/bookings/' + bookingId + '/request-new-proof', {
                method: 'POST',
                body: JSON.stringify({ reason: reason })
            });
            if (result && result.status === 'success') {
                window.showToast('Notification sent to customer.', 'success');
                if (typeof window.showBookingDetails === 'function') {
                    window.showBookingDetails(bookingId);
                }
            }
        },
        'Request New Proof?', 'Yes, Notify Customer'
    );
}

function confirmArchiveBooking(bookingId) {
    window.showConfirm('Are you sure you want to archive this booking?',
        async function() { await window.apiAction('/caterer/bookings/' + bookingId + '/archive', { method: 'POST' }); },
        'Archive Booking?', 'Yes, Archive'
    );
}

function togglePackageAccordion(btn) {
    const accordion = btn.closest('.package-accordion');
    if (accordion) {
        accordion.classList.toggle('active');
    }
}

// ─── GLOBAL EXPOSURE ─────────────────────────────────────────────────────────
window.filterBookings = filterBookings;
window.filterBySignature = filterBySignature;
window.toggleActionMenu = toggleActionMenuBookings;
window.openWalkinModal = openWalkinModal;
window.closeWalkinModal = closeWalkinModal;
window.submitWalkinBooking = submitWalkinBooking;
window.openExpenseTracker = openExpenseTracker;
window.closeExpenseTracker = closeExpenseTracker;
window.addExpenseRow = addExpenseRow;
window.calculateActualExpenses = calculateActualExpenses;
window.submitExpenses = submitExpenses;
window.showBookingDetails = showBookingDetails;
window.switchBookingTab = switchBookingTab;
window.resetBookingTabs = resetBookingTabs;
window.bk_closeBookingDetailModal = bk_closeBookingDetailModal;
window.openContractModal = openContractModal;
window.closeContractModal = closeContractModal;
window.printContract = printContract;
window.toggleDueDateEdit = toggleDueDateEdit;
window.saveDueDate = saveDueDate;
window.togglePackageAccordion = togglePackageAccordion;
window.confirmAcceptBooking = confirmAcceptBooking;
window.confirmRejectBooking = confirmRejectBooking;
window.confirmCompleteBooking = confirmCompleteBooking;
window.updateBookingStage = updateBookingStage;
window.requestNewProof = requestNewProof;
window.confirmArchiveBooking = confirmArchiveBooking;

function initWalkinDetection() {
    let timeoutId;
    const nameInput = document.getElementById('bookCustName');
    const emailInput = document.getElementById('bookCustEmail');
    const contactInput = document.getElementById('bookCustContact');
    const badge = document.getElementById('bookUserDetectionBadge');
    
    if (!nameInput || !emailInput || !badge) return;

    function checkUser() {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(async () => {
            const name = nameInput.value.trim();
            const email = emailInput.value.trim();
            
            if (!name && !email) {
                badge.style.display = 'none';
                return;
            }

            try {
                const response = await fetch('/caterer/api/check-customer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email })
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.exists) {
                        badge.style.display = 'flex';
                        badge.style.background = '#eff6ff';
                        badge.style.color = '#3b82f6';
                        badge.innerHTML = `<i class="fas fa-check-circle"></i> <span>Existing User: <b>${data.name}</b></span>`;
                        
                        if (!emailInput.value && data.email) emailInput.value = data.email;
                        if (!contactInput.value && data.contact) contactInput.value = data.contact;
                    } else {
                        badge.style.display = 'flex';
                        badge.style.background = '#f0fdf4';
                        badge.style.color = '#16a34a';
                        badge.innerHTML = `<i class="fas fa-user-plus"></i> <span style="font-weight: 500;">New Customer</span>`;
                    }
                }
            } catch (err) {
                badge.style.display = 'none';
            }
        }, 600);
    }

    nameInput.addEventListener('input', checkUser);
    emailInput.addEventListener('input', checkUser);
}

function attachBookingPackageListeners() {
    const pkgSelect = document.getElementById('bookPackage');
    const guestInput = document.getElementById('bookGuests');
    const amountInput = document.getElementById('bookTotalAmount');
    if (!pkgSelect || !guestInput || !amountInput) return;

    pkgSelect.addEventListener('change', () => {
        const option = pkgSelect.options[pkgSelect.selectedIndex];
        const minGuests = parseInt(option.dataset.min) || 1;
        guestInput.min = minGuests;
        if (!guestInput.value || parseInt(guestInput.value) < minGuests) {
            guestInput.value = minGuests;
        }
        recalculateBookingTotal();
        guestInput.classList.remove('is-invalid');
    });
    
    guestInput.addEventListener('input', () => {
        const option = pkgSelect.options[pkgSelect.selectedIndex];
        const minGuests = parseInt(option.dataset.min) || 1;
        if (pkgSelect.value !== "" && parseInt(guestInput.value) < minGuests) {
            guestInput.classList.add('is-invalid');
            let feedback = guestInput.parentElement.querySelector('.invalid-feedback');
            if (feedback) {
                feedback.innerText = 'Min. guests needed: ' + minGuests;
                feedback.style.display = 'block';
            }
        } else {
            guestInput.classList.remove('is-invalid');
            let feedback = guestInput.parentElement.querySelector('.invalid-feedback');
            if (feedback) feedback.style.display = 'none';
        }
        recalculateBookingTotal();
    });
}

function recalculateBookingTotal() {
    const pkgSelect = document.getElementById('bookPackage');
    const guestInput = document.getElementById('bookGuests');
    const amountInput = document.getElementById('bookTotalAmount');
    
    if (!pkgSelect || !guestInput || !amountInput) return;

    let total = 0;
    const option = pkgSelect.options[pkgSelect.selectedIndex];
    const price = parseFloat(option.dataset.price) || 0;
    const unit = option.dataset.unit || 'fixed';
    
    let guests = parseInt(guestInput.value) || 0;

    if (pkgSelect.value !== "") {
        amountInput.readOnly = true;
        amountInput.style.backgroundColor = '#f8fafc';
        amountInput.style.cursor = 'not-allowed';
        if (unit === 'per_guest') {
            total = price * guests;
        } else {
            total = price;
        }
        amountInput.value = total > 0 ? total.toFixed(2) : '';
        // Force ValidationManager to see the auto amount update
        amountInput.dispatchEvent(new Event('input', { bubbles: true }));
    } else {
        amountInput.readOnly = false;
        amountInput.style.backgroundColor = '';
        amountInput.style.cursor = 'text';
    }
}

/* ─── OPERATIONS CHECKLIST ─── */

async function loadBookingTasks(bookingId) {
    const listContainer = document.getElementById('bookingTasksList');
    const progressText = document.getElementById('checklistProgressText');
    const progressBar = document.getElementById('checklistProgressBar');
    
    if (!listContainer) return;
    listContainer.innerHTML = '<div style="text-align:center;padding:1rem;color:#94a3b8;"><i class="fas fa-circle-notch fa-spin"></i> Loading tasks...</div>';

    try {
        const res = await fetch(`/caterer/api/bookings/${bookingId}/tasks`);
        if (!res.ok) throw new Error('Failed to load tasks');
        
        const tasks = await res.json();
        
        if (tasks.length === 0) {
            listContainer.innerHTML = '<p style="text-align:center;color:#94a3b8;font-size:0.85rem;padding:2rem;">No operational tasks found for this booking.</p>';
            if (progressText) progressText.innerText = '0%';
            if (progressBar) progressBar.style.width = '0%';
            return;
        }

        const completedCount = tasks.filter(t => t.is_completed).length;
        const progress = Math.round((completedCount / tasks.length) * 100);

        if (progressText) progressText.innerText = progress + '%';
        if (progressBar) progressBar.style.width = progress + '%';

        listContainer.innerHTML = tasks.map(task => `
            <div class="task-item-pro ${task.is_completed ? 'completed' : ''}" data-task-id="${task.id}">
                <div class="task-checkbox-pro" onclick="toggleTaskStatus(${task.id})">
                    ${task.is_completed ? '<i class="fas fa-check"></i>' : ''}
                </div>
                <div class="task-title" onclick="toggleTaskStatus(${task.id})">${task.title}</div>
                <div class="btn-delete-task" onclick="deleteTask(${task.id})">
                    <i class="fas fa-trash-alt"></i>
                </div>
            </div>
        `).join('');

    } catch (err) {
        console.error('Error loading tasks:', err);
        listContainer.innerHTML = '<p style="text-align:center;color:#ef4444;font-size:0.85rem;">Failed to load checklist.</p>';
    }
}

async function addNewCustomTask() {
    if (!currentBookingId) return;
    
    const title = prompt("Enter task description (e.g., Finalize flower arrangements):");
    if (!title || title.trim() === "") return;

    try {
        const res = await fetch(`/caterer/api/bookings/${currentBookingId}/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: title.trim() })
        });
        
        if (res.ok) {
            loadBookingTasks(currentBookingId);
        } else {
            window.showError('Failed to add task');
        }
    } catch (err) {
        window.showError('Error adding task');
    }
}

async function toggleTaskStatus(taskId) {
    try {
        const res = await fetch(`/caterer/api/tasks/${taskId}/toggle`, { method: 'POST' });
        if (res.ok) {
            loadBookingTasks(currentBookingId);
        }
    } catch (err) {
        console.error('Error toggling task:', err);
    }
}

async function deleteTask(taskId) {
    if (!confirm('Are you sure you want to remove this task?')) return;

    try {
        const res = await fetch(`/caterer/api/tasks/${taskId}`, { method: 'DELETE' });
        if (res.ok) {
            loadBookingTasks(currentBookingId);
        } else {
            window.showError('Failed to delete task');
        }
    } catch (err) {
        window.showError('Error deleting task');
    }
}
