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
                'customer_name': { label: 'customer name', noSameParts: true },
                'customer_email': { label: 'email address' },
                'customer_contact': { label: 'contact number', numericOnly: true, maxLength: 11 },
                'event_name':    { label: 'event name' },
                'event_type':    { label: 'event type' },
                'event_date':    { label: 'event date' },
                'guest_count':   { numericOnly: true, max: 100000, autoStop: true },
                'total_amount':  { numericOnly: true, max: 10000000, autoStop: true }
            });
            console.log('[BookingsJS] ValidationManager ready.');
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

        console.log('[BookingsJS] Manage Bookings JS Ready.');
    } catch (err) {
        console.error('[BookingsJS] CRITICAL ERROR DURING INIT:', err);
    }
});

function initDetailListeners() {
    document.querySelectorAll('.view-details').forEach(function(btn) {
        btn.onclick = function() { showBookingDetails(this); };
    });
}

// ─── FILTERING & PAGINATION ──────────────────────────────────────────────────

function filterBookings() {
    const searchInput = document.getElementById('bookingSearchInput').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;
    const allRows = Array.from(document.querySelectorAll('.bookings-list-table tbody tr.booking-row-item'));

    filteredRows = allRows.filter(function(row) {
        const rawStatus = row.dataset.status || '';
        const rowText = row.innerText.toLowerCase();
        const matchesSearch = rowText.indexOf(searchInput) > -1;
        const matchesStatus = statusFilter === '' || rawStatus === statusFilter;
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
    var sf = document.getElementById('statusFilter');
    if (sf) { sf.value = 'awaiting_caterer'; filterBookings(); }
    var tc = document.querySelector('.b-table-container');
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
    e.preventDefault();
    const form = e.target;

    // 1. Strict HTML5 Check
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    // 2. Custom validation for guests minimum check
    const guestInput = document.getElementById('bookGuests');
    const pkgSelect = document.getElementById('bookPackage');
    if (pkgSelect && guestInput && pkgSelect.value !== "") {
        const option = pkgSelect.options[pkgSelect.selectedIndex];
        const minGuests = parseInt(option.dataset.min) || 1;
        if (parseInt(guestInput.value) < minGuests) {
            window.showError(`Dapat hindi bababa sa ${minGuests} ang guests para sa package na ito.`);
            guestInput.classList.add('is-invalid');
            return;
        }
    }

    const btn = document.getElementById('walkinSubmitBtn');
    if (!btn) return;
    btn.disabled = true;
    btn.innerText = 'Creating...';

    const formData = new FormData(form);
    const data = {};
    for (let [key, value] of formData.entries()) { data[key] = value; }
    data.guest_count = parseInt(data.guest_count);
    data.total_amount = parseFloat(data.total_amount.replace(/,/g, ''));
    if (!data.package_id) data.package_id = null;
    else data.package_id = parseInt(data.package_id);
    if (!data.event_time) data.event_time = null;
    data.menu_items = [];

    // Additional Validation for Amount
    if (isNaN(data.total_amount) || data.total_amount <= 0) {
        window.showError('Invalid total amount.');
        btn.disabled = false;
        btn.innerText = 'Create Booking';
        return;
    }

    try {
        const res = await fetch('/caterer/api/bookings/manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            window.showSuccess('Booking created successfully!');
            setTimeout(function() { window.location.reload(); }, 1500);
        } else {
            const err = await res.json();
            window.showError(err.detail || 'Failed to create booking.');
        }
    } catch (err) {
        window.showError('An error occurred. Please try again.');
    } finally {
        if(btn) {
            btn.disabled = false;
            btn.innerText = 'Create Booking';
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
    if (actionsEl) {
        actionsEl.innerHTML = '';
        const plan = (data.paymentPlan || 'downpayment').toUpperCase();
        
        const isPackage = data.isPackage === 'true' || data.isPackage === true;
        
        if (data.status === 'pending') {
            const isPayment = data.paymentStatus === 'proof_submitted';
            const btnLabel = isPayment ? `Verify ${plan}` : 'Accept Booking';
            const btnIcon = isPayment ? 'fa-check-double' : 'fa-check-circle';
            
            actionsEl.innerHTML = `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.confirmAcceptBooking(${data.id}, ${isPayment})"><i class="fas ${btnIcon}"></i> ${btnLabel}</button>`;
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
                actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'ready_for_delivery\')" style="background:#10b981;"><i class="fas fa-box"></i> Mark as Ready</button>';
            } else if (data.status === 'ready_for_delivery') {
                actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'on_the_way\')" style="background:#0ea5e9;"><i class="fas fa-truck"></i> Out for Delivery</button>';
            } else if (data.status === 'on_the_way') {
                actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'arrived\')" style="background:#6366f1;"><i class="fas fa-map-marker-alt"></i> Arrived</button>';
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
    const dueDateSection = document.getElementById('dueDateDisplaySection').parentElement;
    const modalDueDate = document.getElementById('modalDueDate');
    
    if (data.paymentPlan === 'full') {
        dueDateSection.style.display = 'none';
    } else {
        dueDateSection.style.display = 'block';
        // Highlight if missing
        if (!data.balanceDue) {
            modalDueDate.innerHTML = '<span style="color:#ef4444; font-weight:700;"><i class="fas fa-exclamation-triangle"></i> ACTION REQUIRED: Set Due Date</span>';
        } else {
            modalDueDate.innerText = data.balanceDue;
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
            document.getElementById('modalDueDate').innerText = newDate;
            toggleDueDateEdit();
            var btn = document.querySelector('.view-details[data-id="' + currentBookingId + '"]');
            if (btn) btn.dataset.balanceDue = newDate;
            window.showSuccess('Due date updated!');
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

function confirmAcceptBooking(bookingId, isPayment) {
    isPayment = isPayment || false;
    
    let confirmMsg = isPayment ? 'Natanggap mo na ba ang bayad mula sa customer?' : 'Nais mo bang tanggapin ang booking na ito kahit wala pang payment proof?';
    let confirmTitle = isPayment ? 'Confirm Payment?' : 'Accept Booking Manually?';
    let confirmBtn = isPayment ? 'Yes, Verify Payment' : 'Yes, Accept Booking';

    window.showConfirm(confirmMsg,
        async function() {
            var url = isPayment ? '/caterer/payments/' + bookingId + '/confirm' : '/caterer/bookings/' + bookingId + '/accept';
            var result = await window.apiAction(url, { method: 'POST' });
            if (result && result.status === 'success') {
                bk_closeBookingDetailModal();
                if (typeof window.refreshDashboardData === 'function') window.refreshDashboardData();
            }
        },
        confirmTitle, confirmBtn
    );
}

function confirmRejectBooking(bookingId) {
    window.showConfirm('Nais mo bang i-REJECT ang booking na ito?',
        async function() { await window.apiAction('/caterer/bookings/' + bookingId + '/reject', { method: 'POST' }); },
        'Reject Booking?', 'Yes, Reject Booking'
    );
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
        'on_the_way': 'Is the team currently in transit to the location?',
        'arrived': 'Has the team arrived at the venue?',
        'setup_ongoing': 'Has the setup and food service started?',
        'in_progress': 'Has the event serving officially started?'
    };
    const titles = {
        'preparing': 'Start Preparation?',
        'ready_for_delivery': 'Mark as Ready?',
        'on_the_way': 'Dispatch Team?',
        'arrived': 'Staff Arrived?',
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
    window.showConfirm('Do you want to archive this booking?',
        async function() { await window.apiAction('/caterer/bookings/' + bookingId + '/archive', { method: 'POST' }); },
        'Archive Booking?', 'Yes, Archive'
    );
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
