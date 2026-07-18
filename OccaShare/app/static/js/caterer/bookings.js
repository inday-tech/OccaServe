let currentBookingId = null;
let currentEventDate = null;
let currentPage = 1;
const ROWS_PER_PAGE = 5;
let filteredRows = [];

// ─── UTILS ───────────────────────────────────────────────────────────────────
if (typeof window.showError === 'undefined') {
    window.showError = function(msg) {
        if (typeof Swal !== 'undefined') {
            const Toast = Swal.mixin({
                toast: true,
                position: 'bottom-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
            Toast.fire({ icon: 'error', title: msg });
        } else if (window.showToast) {
            window.showToast(msg, 'error');
        } else {
            alert(msg);
        }
    };
}

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
    
    window.refreshBookingsTable = async function() {
        try {
            const res = await fetch(window.location.href);
            const text = await res.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(text, 'text/html');
            const newTbody = doc.querySelector('.bookings-list-table tbody');
            if (newTbody) {
                document.querySelector('.bookings-list-table tbody').innerHTML = newTbody.innerHTML;
                const allRows = Array.from(document.querySelectorAll('.bookings-list-table tbody tr.booking-row-item'));
                filteredRows = allRows;
                initDetailListeners();
                filterBookings();
            }
            if (typeof refreshActionAlerts === 'function') refreshActionAlerts();
        } catch(e) {
            console.error('Failed to refresh bookings table', e);
            setTimeout(() => window.location.reload(), 1500); // Fallback
        }
    };
    
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
        initWalkinLocation();

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

            const isEarlyStage = ['draft', 'pending', 'awaiting_caterer', 'awaiting_payment', 'pending_payment'].includes(rawStatus);
            if (payStatus === 'balance_proof_submitted' || (payStatus === 'proof_submitted' && isEarlyStage)) payAlerts++;
            if (['awaiting_caterer'].includes(rawStatus)) contractAlerts++;
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
        const rowText = row.textContent.toLowerCase();
        
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
    
    // Minimum 2 Days Lead Time Enforcement
    var dateInput = document.getElementById('walkin_event_date');
    if (dateInput) {
        var today = new Date();
        today.setDate(today.getDate() + 2); // At least 2 days from today
        dateInput.min = today.toISOString().split('T')[0];
    }
    
    // Bind Real-Time Validation Triggers
    if (form) {
        // Auto-fill min pax when package changes
        var pkgSelect = document.getElementById('bookPackage');
        var guestInput = document.getElementById('bookGuests');
        if (pkgSelect && guestInput) {
            pkgSelect.addEventListener('change', function() {
                if (this.value) {
                    var option = this.options[this.selectedIndex];
                    var minGuests = option.getAttribute('data-min') || 1;
                    guestInput.value = minGuests;
                    guestInput.min = minGuests;
                    
                    // Trigger input event to clear any existing errors
                    guestInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
            });
        }

        form.querySelectorAll('.real-time-val').forEach(input => {
            // Clear error dynamically as user types
            input.addEventListener('input', function() {
                this.style.borderColor = '#cbd5e1';
                var feedback = this.parentElement.querySelector('.invalid-feedback');
                if (feedback) feedback.innerText = '';
                
                // Extra Name Validation Logic (John John John checker)
                if (this.name === 'first_name' || this.name === 'last_name' || this.name === 'middle_name') {
                    var fn = document.getElementById('bookCustFirstName').value.toLowerCase().trim();
                    var ln = document.getElementById('bookCustLastName').value.toLowerCase().trim();
                    var mn = document.getElementById('bookCustMiddleName').value.toLowerCase().trim();
                    
                    if (fn && ln && fn === ln) {
                        this.style.borderColor = '#ef4444';
                        if (feedback) feedback.innerText = 'First name and Last name cannot be identical.';
                    } else if (fn && mn && fn === mn) {
                        this.style.borderColor = '#ef4444';
                        if (feedback) feedback.innerText = 'First name and Middle name cannot be identical.';
                    }
                }
            });

            // Show error immediately if field is left empty on blur
            input.addEventListener('blur', function() {
                if (this.hasAttribute('required') && !this.value.trim()) {
                    this.style.borderColor = '#ef4444';
                    var feedback = this.parentElement.querySelector('.invalid-feedback');
                    if (feedback) feedback.innerText = 'This field is required.';
                }
            });
        });
    }
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
    let hasError = false;

    // Real-time custom required check
    form.querySelectorAll('.real-time-val[required]').forEach(input => {
        if (!input.value.trim()) {
            input.style.borderColor = '#ef4444';
            let feedback = input.parentElement.querySelector('.invalid-feedback');
            if (feedback) feedback.innerText = 'This field is required.';
            hasError = true;
        }
    });

    // Check custom JS errors from real-time events
    form.querySelectorAll('.invalid-feedback').forEach(feedback => {
        if (feedback.innerText.trim() !== '') hasError = true;
    });

    if (hasError) {
        window.showError('Please complete all required fields correctly before submitting.');
        return;
    }

    // HTML5 Fallback
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
        } else if (key === 'city') {
            data['municipality'] = value;
        } else if (key === 'venue_address') {
            data['landmark'] = value;
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
            if (window.refreshBookingsTable) window.refreshBookingsTable();
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
    // Populate expense form
    document.getElementById('expenseBookingId').value = bookingId;
    
    // Set Total Budget from data attribute
    var totalAmount = 0;
    if (btn) {
        totalAmount = parseFloat(btn.getAttribute('data-total-amount')) || 0;
        document.getElementById('bookingTotalAmount').value = totalAmount;
    }
    
    var modalTotal = document.getElementById('modalBookingTotal');
    if (modalTotal) modalTotal.innerText = '₱' + totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    // Open the booking detail modal by triggering the view details button (to populate everything)
    if (btn) {
        var dropdownMenu = btn.closest('.action-dropdown-menu');
        if (dropdownMenu) {
            var viewBtn = dropdownMenu.querySelector('.view-details');
            if (viewBtn) {
                showBookingDetails(viewBtn);
            }
        }
    }
    
    // Switch to expenses tab
    var expTabBtn = document.querySelector('.mtab-btn-pro[onclick*="expenses"]');
    if (expTabBtn) switchBookingTab('expenses', expTabBtn);
    
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
            row.className = 'd-flex gap-2 mb-2 expense-item-row align-items-center';
            row.style.background = '#fff';
            row.style.padding = '0.5rem';
            row.style.borderRadius = '0.5rem';
            row.style.border = '1px solid #f1f5f9';
            row.style.boxShadow = '0 1px 2px rgba(0,0,0,0.02)';
            row.innerHTML = '<input type="text" class="form-control form-control-sm exp-name" value="' + exp.name + '" placeholder="Item" style="flex:2; border:none; background:transparent; font-weight:600; color:#334155;"><input type="number" class="form-control form-control-sm exp-amount" value="' + exp.amount + '" min="0" oninput="calculateActualExpenses()" style="flex:1; border:none; background:transparent; font-weight:700; color:#0f172a; text-align:right;"><button type="button" class="btn btn-sm text-danger" onclick="this.parentElement.remove();calculateActualExpenses()" style="background:transparent; border:none;"><i class="fas fa-times"></i></button>';
            container.appendChild(row);
        });
    } else {
        addExpenseRow();
    }
    calculateActualExpenses();
}

function closeExpenseTracker() {
    // Now it's just closing the booking detail modal
    bk_closeModal('bookingDetailModal');
    var form = document.getElementById('expenseTrackerForm');
    if (form) form.reset();
}

function addExpenseRow() {
    var container = document.getElementById('actualExpenseRows');
    var row = document.createElement('tr');
    row.className = 'expense-item-row';
    row.style.borderBottom = '1px solid #f1f5f9';
    row.innerHTML = `
        <td style="padding: 0.5rem 1rem;">
            <input type="text" class="form-control form-control-sm exp-name" placeholder="Item (e.g. Labor)" style="width: 100%; border: none; background: transparent; font-weight: 600; color: #334155; padding: 0.25rem 0; box-shadow: none;">
        </td>
        <td style="padding: 0.5rem 1rem;">
            <input type="text" class="form-control form-control-sm exp-amount js-format-comma" placeholder="0.00" oninput="if(window.applyCommaFormatting) window.applyCommaFormatting(this); calculateActualExpenses()" style="width: 100%; border: none; background: transparent; font-weight: 700; color: #0f172a; text-align: right; padding: 0.25rem 0; box-shadow: none;">
        </td>
        <td style="padding: 0.5rem; text-align: center;">
            <button type="button" class="btn btn-sm text-danger" onclick="this.closest('tr').remove(); calculateActualExpenses()" style="background: transparent; border: none; padding: 0.25rem 0.5rem;">
                <i class="fas fa-times"></i>
            </button>
        </td>
    `;
    container.appendChild(row);
}

function calculateActualExpenses() {
    var totalExpense = 0;
    document.querySelectorAll('#actualExpenseRows .expense-item-row').forEach(function(row) {
        var rawVal = row.querySelector('.exp-amount').value || '0';
        totalExpense += parseFloat(rawVal.replace(/,/g, '')) || 0;
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
    var hasError = false;
    
    document.querySelectorAll('#actualExpenseRows .expense-item-row').forEach(function(row) {
        var nameInput = row.querySelector('.exp-name');
        var name = nameInput.value.trim();
        var amountInput = row.querySelector('.exp-amount');
        var rawAmount = amountInput.value || '0';
        var amount = parseFloat(rawAmount.replace(/,/g, ''));

        if (!name) {
            nameInput.style.border = '1px solid #ef4444';
            hasError = true;
        } else {
            nameInput.style.border = 'none';
        }
        
        if (isNaN(amount) || amount < 0) {
            amountInput.style.border = '1px solid #ef4444';
            hasError = true;
        } else {
            amountInput.style.border = 'none';
        }

        if (name && !isNaN(amount) && amount >= 0) {
            breakdown.push({ name: name, amount: amount });
        }
    });

    if (hasError) {
        window.showToast("Please provide a valid item name and a positive amount.", "error");
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save me-1"></i> Save Expenses';
        return;
    }

    try {
        var res = await fetch('/caterer/bookings/' + bookingId + '/actual-cost', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ actual_cost: total, actual_cost_breakdown: breakdown })
        });
        if (res.ok) {
            window.showSuccess('Actual expenses saved.');
            // Re-render expense rows to reflect saved state or keep them as is
            if (window.refreshBookingsTable) window.refreshBookingsTable();
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
    currentEventDate = data.eventDate;
    
    // Format the date and time properly
    let edate = new Date(data.eventDate);
    let formattedDate = edate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    let formattedTime = data.eventTime || 'TBA';
    let fullDateTime = formattedDate + ' at ' + formattedTime;
    
    // --- POPULATE VERIFICATION TAB ---
    const vCustName = document.getElementById('vCustomerName'); if(vCustName) vCustName.innerText = data.customer || 'N/A';
    const vCustEmail = document.getElementById('vCustomerEmail'); if(vCustEmail) vCustEmail.innerText = data.email || 'N/A';
    const vCustContact = document.getElementById('vCustomerContact'); if(vCustContact) vCustContact.innerText = data.contact || 'N/A';
    const vCustAddress = document.getElementById('vCustomerAddress'); if(vCustAddress) vCustAddress.innerText = data.venue || 'N/A';
    
    const vBookType = document.getElementById('vBookingType'); if(vBookType) vBookType.innerText = data.specificName || data.eventType || 'N/A';
    const vEventDateEl = document.getElementById('vEventDate'); if(vEventDateEl) vEventDateEl.innerText = fullDateTime;
    const vVenue = document.getElementById('vVenue'); if(vVenue) vVenue.innerText = data.venue || 'N/A';
    const vGuestCount = document.getElementById('vGuestCount'); if(vGuestCount) vGuestCount.innerText = data.guestCount || 'N/A';
    
    const vAmountPaid = document.getElementById('vAmountPaid'); if(vAmountPaid) vAmountPaid.innerText = data.amount || '0.00';
    const vRefNumber = document.getElementById('vRefNumber'); if(vRefNumber) vRefNumber.innerText = data.paymentRef || 'N/A';
    const vPaymentStatus = document.getElementById('vPaymentStatus'); 
    if(vPaymentStatus) {
        let pStatus = data.paymentStatus || 'pending';
        let pColor = '#d97706'; let pBg = '#fef3c7';
        if (pStatus === 'paid' || pStatus === 'fully_paid') { pColor = '#16a34a'; pBg = '#dcfce3'; }
        vPaymentStatus.innerHTML = `<span class="badge" style="background: ${pBg}; color: ${pColor};">${pStatus.replace('_', ' ').toUpperCase()}</span>`;
    }
    // ---------------------------------

    const isFoodOrder = data.isFoodOrder === 'true' || data.isFoodOrder === true;
    let titlePrefix = isFoodOrder ? 'Food Order #' : (data.status === 'pending_review' ? 'Inquiry Details #' : 'Booking #');
    document.getElementById('modalBookingId').innerText = titlePrefix + data.id;
    
    // Urgent Indicator in Modal Header
    const headerTitle = document.getElementById('modalBookingId');
    if (data.isUrgent === 'true') {
        headerTitle.innerHTML = `${titlePrefix}${data.id} <span style="background: #fff1f2; color: #e11d48; font-size: 0.65rem; padding: 2px 8px; border-radius: 50px; margin-left: 8px; border: 1px solid #fecdd3; vertical-align: middle;"><i class="fas fa-clock"></i> URGENT</span>`;
    }

    document.getElementById('modalCustomer').innerText = data.customer;
    document.getElementById('modalEmail').innerText = data.email;
    const labelEl = document.getElementById('modalEventDetailsLabel');
    if (labelEl) {
        labelEl.innerText = isFoodOrder ? 'Order Details' : 'Event Details';
    }
    document.getElementById('modalEventName').innerText = data.specificName || data.eventName;
    document.getElementById('modalEventType').innerHTML = `<i class="fas fa-tag" style="margin-right: 4px;"></i>${data.eventType}`;
    document.getElementById('modalVenue').innerText = data.venue;
    document.getElementById('modalRequests').innerText = data.requests;

    var statusEl = document.getElementById('modalStatus');
    statusEl.innerText = data.displayStatus || data.status.replace(/_/g, ' ').toUpperCase();
    statusEl.className = 'badge-status';
    var statusMap = {
        'pending': 'badge-pending',
        'pending_quotation': 'badge-draft',
        'pending_payment': 'badge-payment',
        'awaiting_caterer': 'badge-awaiting_caterer',
        'awaiting_payment': 'badge-payment',
        'confirmed': 'badge-confirmed',
        'preparing': 'badge-preparing',
        'on_the_way': 'badge-active',
        'ready_for_delivery': 'badge-active',
        'ready_for_pickup': 'badge-active',
        'arrived': 'badge-active',
        'in_progress': 'badge-in_progress',
        'setup_ongoing': 'badge-in_progress',
        'completed': 'badge-completed',
        'cancelled': 'badge-cancelled'
    };
    statusEl.classList.add(data.displayBadge || statusMap[data.status] || 'badge-draft');

    var menuSource = document.getElementById('booking-items-' + data.id);
    var menuTarget = document.getElementById('modalMenuItems');
    var menuSection = document.getElementById('modalMenuSection');
    var menuDetailsBlock = document.getElementById('modalMenuDetailsBlock');
    
    let hasMenuData = data.hasMenu === 'true';
    if (hasMenuData && menuSource && menuSource.innerHTML.trim() !== '') {
        if (menuTarget) menuTarget.innerHTML = menuSource.innerHTML;
        if (menuSection) menuSection.style.display = 'block';
        if (menuDetailsBlock) menuDetailsBlock.style.display = 'block';
    } else {
        if (menuTarget) menuTarget.innerHTML = '<p style="color:#64748b;font-size:0.9rem;">No menu items or inclusions available.</p>';
        if (menuSection) menuSection.style.display = 'block';
        if (menuDetailsBlock) menuDetailsBlock.style.display = 'none';
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
            proofContainer.innerHTML += `<div style="display:flex;flex-direction:column;align-items:center;gap:8px;">
                <a href="${proofUrl}" target="_blank" style="display:flex;flex-direction:column;align-items:center;gap:8px;text-decoration:none;">
                    <img src="${proofUrl}" class="modal-proof-img" style="max-width:160px;max-height:160px;border-radius:8px;border:1px solid #e2e8f0;object-fit:cover;"
                        onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
                    <div style="display:none;width:120px;height:120px;background:#f1f5f9;border-radius:8px;border:1px dashed #cbd5e1;align-items:center;justify-content:center;flex-direction:column;gap:6px;">
                        <i class='fas fa-file-image' style='font-size:2rem;color:#94a3b8;'></i>
                        <span style='font-size:0.65rem;color:#94a3b8;font-weight:700;'>View File</span>
                    </div>
                    <span class="modal-proof-label">Downpayment Proof</span>
                </a>
            </div>`;
        }
        if (balanceProofUrl) {
            hasProof = true;
            proofContainer.innerHTML += `<div style="display:flex;flex-direction:column;align-items:center;gap:8px;">
                <a href="${balanceProofUrl}" target="_blank" style="display:flex;flex-direction:column;align-items:center;gap:8px;text-decoration:none;">
                    <img src="${balanceProofUrl}" class="modal-proof-img" style="max-width:160px;max-height:160px;border-radius:8px;border:1px solid #e2e8f0;object-fit:cover;"
                        onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
                    <div style="display:none;width:120px;height:120px;background:#f1f5f9;border-radius:8px;border:1px dashed #cbd5e1;align-items:center;justify-content:center;flex-direction:column;gap:6px;">
                        <i class='fas fa-file-image' style='font-size:2rem;color:#94a3b8;'></i>
                        <span style='font-size:0.65rem;color:#94a3b8;font-weight:700;'>View File</span>
                    </div>
                    <span class="modal-proof-label">Balance Proof</span>
                </a>
            </div>`;
        }
        proofSection.style.display = hasProof ? 'block' : 'none';
    }

    // RISK ALERT HANDLING
    var riskAlert = document.getElementById('modalRiskAlert');
    if (riskAlert) {
        if (['pending', 'pending_quotation', 'awaiting_payment', 'awaiting_caterer'].includes(data.status) && (data.isUrgent === 'true' || data.isUrgent === true)) {
            riskAlert.style.display = 'block';
            riskAlert.innerHTML = '<i class="fas fa-clock"></i> URGENT';
        } else {
            riskAlert.style.display = 'none';
        }
    }

    var actionsEl = document.getElementById('bookingModalActionsTop') || document.getElementById('bookingModalActions');
    const isVerified = data.isVerified === 'true' || data.isVerified === true;
    const targetUserId = data.targetUserId;
    const isPackage = data.isPackage === 'true' || data.isPackage === true;

    const isRental = data.eventType === 'Equipment Rental';

    if (actionsEl) {
        actionsEl.style.display = 'flex';
        actionsEl.innerHTML = '';
        
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
            const isCashOrCOD = data.paymentMethod === 'CASH' || data.paymentMethod === 'COD';
            const isPayment = data.paymentStatus === 'proof_submitted';
            let btnLabel = isPayment ? `Verify ${plan} & Accept` : 'Confirm & Accept Booking';
            let rejectLabel = 'Reject Booking';
            if (isFoodOrder) {
                btnLabel = isPayment ? `Verify Payment & Accept Order` : 'Confirm & Accept Order';
                rejectLabel = 'Reject Order';
            }
            const btnIcon = isPayment ? 'fa-check-double' : 'fa-check-circle';
            
            if (isPayment || isCashOrCOD) {
                actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.confirmAcceptBooking(${data.id}, ${isPayment}, ${isVerified}, ${isPackage})"><i class="fas ${btnIcon}"></i> ${btnLabel}</button>`;
                if (isPayment) {
                    actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-reject" onclick="window.requestNewProof(${data.id})" style="background:#64748b;"><i class="fas fa-redo"></i> Request New Proof</button>`;
                }
            } else if (data.paymentStatus === 'reupload_requested') {
                actionsEl.innerHTML += `<div style="padding: 0.5rem 1rem; color: #9f1239; background: #ffe4e6; border: 1px solid #fecdd3; border-radius: var(--border-radius, 8px); font-size: 0.85rem; font-weight: 600; flex: 1; display: flex; align-items: center; gap: 0.5rem;"><i class="fas fa-exclamation-triangle"></i> Re-upload Requested. Waiting for customer.</div>`;
            } else {
                actionsEl.innerHTML += `<div style="padding: 0.5rem 1rem; color: #b45309; background: #fffbeb; border: 1px solid #fde68a; border-radius: var(--border-radius, 8px); font-size: 0.85rem; font-weight: 600; flex: 1; display: flex; align-items: center; gap: 0.5rem;"><i class="fas fa-clock"></i> Awaiting Payment Proof from Customer</div>`;
            }
            actionsEl.innerHTML += `<div style="flex-basis: 100%; height: 0; margin: 0;"></div><button type="button" class="btn-footer-action btn-status-reject" onclick="window.confirmRejectBooking(${data.id})" style="width: 100%; margin-top: 0.25rem;"><i class="fas fa-times-circle"></i> ${rejectLabel}</button>`;
            
        } else if (data.status === 'awaiting_caterer') {
            actionsEl.innerHTML = `<a href="/caterer/bookings/${data.id}/sign" class="btn-footer-action btn-status-confirm" style="text-decoration:none; flex: 1;"><i class="fas fa-pen-nib"></i> Sign Contract Now</a><div style="flex-basis: 100%; height: 0; margin: 0;"></div><button type="button" class="btn-footer-action btn-status-reject" onclick="window.confirmRejectBooking(${data.id})" style="width: 100%; margin-top: 0.25rem;"><i class="fas fa-times-circle"></i> Reject</button>`;
            
        } else {
            // ─── CONSOLIDATED OPERATIONAL LIFECYCLE ───
            // Both Ala Carte (8 Steps) and Package (6 Steps) share these event milestones
            if (data.status === 'confirmed') {
                if (data.paymentStatus === 'balance_proof_submitted') {
                    actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-confirm pulse-update" onclick="window.confirmAcceptBooking(${data.id}, true)" style="margin-bottom:0.5rem;width:100%;"><i class="fas fa-check-double"></i> Verify Final Balance</button>`;
                }
                if (isRental) {
                    actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.openRentalReleaseModal(${data.id})" style="background:#5b5a9c;"><i class="fas fa-camera"></i> Release Equipment</button>`;
                } else {
                    actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(${data.id}, 'preparing')" style="background:#5b5a9c;"><i class="fas fa-utensils"></i> Start Preparation</button>`;
                }
            } else if (data.status === 'preparing') {
                if (data.venue === 'PICKUP') {
                    actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.validateAndProceed(' + data.id + ', \'ready_for_pickup\')" style="background:#10b981;"><i class="fas fa-shopping-bag"></i> Mark as Ready for Pickup</button>';
                } else {
                    if (isFoodOrder) {
                        actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'on_the_way\')" style="background:#0ea5e9;"><i class="fas fa-truck"></i> Dispatch Order</button>';
                    } else {
                        actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.validateAndProceed(' + data.id + ', \'ready_for_delivery\')" style="background:#10b981;"><i class="fas fa-box"></i> Mark as Ready for Delivery</button>';
                    }
                }
            } else if (data.status === 'ready_for_pickup') {
                actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-complete" onclick="window.confirmCompleteBooking(' + data.id + ')"><i class="fas fa-flag-checkered"></i> Mark as Picked Up (Complete)</button>';
            } else if (data.status === 'released') {
                if (isRental) {
                    actionsEl.innerHTML = `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.openRentalInspectionModal(${data.id})" style="background:#10b981;"><i class="fas fa-clipboard-check"></i> Inspect & Process Return</button>`;
                }
            } else if (data.status === 'ready_for_delivery') {
                actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'on_the_way\')" style="background:#0ea5e9;"><i class="fas fa-truck"></i> Out for Delivery</button>';
            } else if (data.status === 'on_the_way') {
                if (isPackage) {
                    actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'arrived\')" style="background:#6366f1;"><i class="fas fa-map-marker-alt"></i> Arrived at Location</button>';
                } else if (isFoodOrder) {
                    actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'arrived\')" style="background:#10b981;"><i class="fas fa-check-circle"></i> Mark as Delivered</button>';
                } else {
                    // Skip to Complete for Ala Carte (Services)
                    if (!isRental) {
                        actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-complete" onclick="window.confirmCompleteBooking(' + data.id + ')"><i class="fas fa-flag-checkered"></i> Mark as Delivered (Complete)</button>';
                    }
                }
            } else if (data.status === 'arrived') {
                if (isPackage) {
                    actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'setup_ongoing\')" style="background:#f97316;"><i class="fas fa-magic"></i> Setup & Serve</button>';
                } else if (isFoodOrder) {
                    actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-complete" onclick="window.confirmCompleteBooking(' + data.id + ')"><i class="fas fa-flag-checkered"></i> Mark Order Completed</button>';
                }
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
                const archiveLabel = isFoodOrder ? 'Archive Order' : (isPackage ? 'Archive Package Record' : 'Archive Booking');
                actionsEl.innerHTML = '<button type="button" class="btn-footer-action" style="background:#fef3c7;color:#92400e;border:1px solid #fcd34d;flex:1;" onclick="window.confirmArchiveBooking(' + data.id + ')"><i class="fas fa-archive"></i> ' + archiveLabel + '</button>';
            }
        }
        
        // Add Copy Payment Link Button (useful for sending to FB Walk-in customers)
        const noLinkStatuses = ['draft', 'pending_quotation', 'awaiting_caterer', 'awaiting_customer', 'pending', 'cancelled', 'completed'];
        if (!noLinkStatuses.includes(data.status) && data.paymentStatus !== 'paid' && data.amount !== "₱0.00") {
            actionsEl.innerHTML += `
                <button type="button" class="btn-footer-action" onclick="window.copyInvoiceLink(${data.id})" style="background: white; color: #475569; border: 1px solid #cbd5e1;">
                    <i class="fas fa-link"></i> Copy Payment Link
                </button>
            `;
        }

        const actionCenterWrapper = document.getElementById('actionCenterWrapper');
        if (actionCenterWrapper) {
            actionCenterWrapper.style.display = actionsEl.innerHTML.trim() !== '' ? 'block' : 'none';
        }
    }

    document.getElementById('modalBookedOn').innerText = data.bookedOn;
    const displayPaymentPlan = (isFoodOrder || data.paymentPlan === 'full') ? 'FULL PAYMENT' : (data.paymentPlan || 'downpayment').toUpperCase();
    document.getElementById('modalPaymentMethod').innerText = `Method: ${data.paymentMethod} (${displayPaymentPlan})`;
    const payRefEl = document.getElementById('modalPaymentRef');
    if (payRefEl) {
        if (data.paymentRef && data.paymentRef.trim() !== '') {
            payRefEl.innerText = `Ref: ${data.paymentRef}`;
            payRefEl.style.display = 'block';
        } else {
            payRefEl.style.display = 'none';
        }
    }
    document.getElementById('modalTotalAmount').innerText = data.amount;

    // --- PROFIT SUMMARY INJECTION FOR COMPLETED BOOKINGS ---
    const profitSummary = document.getElementById('completedProfitSummary');
    if (profitSummary) {
        if (data.status === 'completed') {
            profitSummary.style.display = 'block';
            const totalRevenue = parseFloat(data.totalRawAmount) || 0;
            const actualCost = parseFloat(data.actualCost) || 0;
            const profit = totalRevenue - actualCost;
            const margin = totalRevenue > 0 ? (profit / totalRevenue) * 100 : 0;

            const formatMoney = (val) => '₱' + val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            
            document.getElementById('psRevenue').innerText = formatMoney(totalRevenue);
            document.getElementById('psCost').innerText = formatMoney(actualCost);
            
            const psProfit = document.getElementById('psProfit');
            psProfit.innerText = formatMoney(profit);
            psProfit.style.color = profit >= 0 ? '#15803d' : '#ef4444';
            
            const psMargin = document.getElementById('psMargin');
            psMargin.innerText = Math.round(margin) + '%';
            if (margin >= 25) { psMargin.style.color = '#15803d'; }
            else if (margin >= 10) { psMargin.style.color = '#b45309'; }
            else { psMargin.style.color = '#ef4444'; }
            
        } else {
            profitSummary.style.display = 'none';
        }
    }
    // -------------------------------------------------------
    
    const guestCountEl = document.getElementById('modalGuestCount');
    if (guestCountEl) {
        if (isFoodOrder) {
            guestCountEl.style.display = 'none';
        } else {
            guestCountEl.style.display = 'inline-flex';
            guestCountEl.innerHTML = '<i class="fas fa-users" style="margin-right: 4px;"></i>' + data.guestCount + ' Guests';
        }
    }
    
    // Handle Due Date section display logic
    const dueDateCard = document.getElementById('dueDateCardPremium');
    const modalDueDate = document.getElementById('modalDueDate');
    const badgeContainer = document.getElementById('dueDateBadgeContainer');
    
    const isEarlyStage = ['pending', 'pending_quotation', 'awaiting_caterer', 'awaiting_customer', 'awaiting_payment', 'pending_payment'].includes(data.status);
    if (data.paymentPlan === 'full' || data.paymentStatus === 'paid' || isEarlyStage) {
        if (dueDateCard) dueDateCard.style.display = 'none';
    } else {
        if (dueDateCard) dueDateCard.style.display = 'block';
        if (!data.balanceDue) {
            if (modalDueDate) modalDueDate.innerHTML = '<span style="color:#ef4444;"><i class="fas fa-exclamation-circle"></i> Needs Deadline</span>';
            if (badgeContainer) badgeContainer.innerHTML = '<span class="due-date-badge missing">Action Required</span>';
        } else {
            // Simple format for display
            const parts = data.balanceDue.split('-');
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const formatted = `${months[parseInt(parts[1])-1]} ${parts[2]}, ${parts[0]}`;
            if (modalDueDate) modalDueDate.innerText = formatted;
            if (badgeContainer) badgeContainer.innerHTML = '<span class="due-date-badge"><i class="fas fa-check-circle"></i> Deadline Set</span>';
        }
    }

    var displaySec = document.getElementById('dueDateDisplaySection');
    if (displaySec) displaySec.style.display = 'block';
    
    var editSec = document.getElementById('dueDateEditSection');
    if (editSec) editSec.style.display = 'none';
    
    var dueDateInput = document.getElementById('balanceDueDateInput');
    if (dueDateInput) {
        dueDateInput.value = data.balanceDue || '';
        // Ensure min date is today
        const today = new Date().toISOString().split('T')[0];
        dueDateInput.min = today;
    }

    var pStatusEl = document.getElementById('modalPaymentStatus');
    var pLabels = { 
        'paid': 'Fully Paid', 
        'deposit_paid': 'Downpayment Paid', 
        'proof_submitted': 'Proof Sent', 
        'balance_proof_submitted': 'Balance Proof Sent', 
        'pending': 'Payment Pending',
        'reupload_requested': 'Re-upload Requested',
        'balance_reupload_requested': 'Balance Re-upload Requested'
    };
    if (pStatusEl) {
        pStatusEl.innerText = pLabels[data.paymentStatus] || data.paymentStatus.replace(/_/g, ' ').toUpperCase();
    }

    // Handle Checklist Display Logic
    const checklistSection = document.getElementById('modalChecklistSection');
    if (checklistSection) {
        if (['pending', 'pending_quotation', 'awaiting_caterer', 'awaiting_payment'].includes(data.status)) {
            checklistSection.style.display = 'none';
        } else {
            checklistSection.style.display = 'block';
        }
    }

    // Load Checklist Tasks
    loadBookingTasks(data.id);
    
    // Load History
    loadBookingHistory(data.id);
    
    // Load Notes
    const notesEl = document.getElementById('modalCatererNotes');
    if (notesEl) notesEl.value = btn.dataset.catererNotes || '';
    
    // Update Stepper
    updateBookingStepper(data.status, isPackage, isFoodOrder);
    
    // Load Chat Messages
    loadBookingMessages(data.id);
    
    // Always default to overview tab
    var ovTabBtn = document.querySelector('.mtab-btn-pro[onclick*="overview"]');
    if (ovTabBtn) switchBookingTab('overview', ovTabBtn);
    
    // Populate the expense tab automatically so it's ready
    var expenseBtn = btn.closest('.action-dropdown-menu')?.querySelector('button[onclick*="openExpenseTracker"]');
    if (expenseBtn) {
        document.getElementById('expenseBookingId').value = data.id;
        var totalAmount = parseFloat(expenseBtn.getAttribute('data-total-amount')) || 0;
        document.getElementById('bookingTotalAmount').value = totalAmount;
        var modalTotal = document.getElementById('modalBookingTotal');
        if (modalTotal) modalTotal.innerText = '₱' + totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        
        var container = document.getElementById('actualExpenseRows');
        if (container) {
            container.innerHTML = '';
            var breakdown = [];
            try {
                var breakdownStr = expenseBtn.getAttribute('data-breakdown');
                if (breakdownStr) {
                    var unescaped = breakdownStr.replace(/&quot;/g, '"');
                    breakdown = JSON.parse(unescaped);
                    if (typeof breakdown === 'string') breakdown = JSON.parse(breakdown);
                }
            } catch (e) {}
            
            if (breakdown && breakdown.length > 0) {
                breakdown.forEach(function(exp) {
                    var row = document.createElement('tr');
                    row.className = 'expense-item-row';
                    row.style.borderBottom = '1px solid #f1f5f9';
                    row.innerHTML = `
                        <td style="padding: 0.5rem 1rem;">
                            <input type="text" class="form-control form-control-sm exp-name" value="${exp.name}" placeholder="Item" style="width: 100%; border: none; background: transparent; font-weight: 600; color: #334155; padding: 0.25rem 0; box-shadow: none;">
                        </td>
                        <td style="padding: 0.5rem 1rem;">
                            <input type="text" class="form-control form-control-sm exp-amount js-format-comma" value="${Number(exp.amount).toLocaleString('en-US', {minimumFractionDigits: 2})}" oninput="if(window.applyCommaFormatting) window.applyCommaFormatting(this); calculateActualExpenses()" style="width: 100%; border: none; background: transparent; font-weight: 700; color: #0f172a; text-align: right; padding: 0.25rem 0; box-shadow: none;">
                        </td>
                        <td style="padding: 0.5rem; text-align: center;">
                            <button type="button" class="btn btn-sm text-danger" onclick="this.closest('tr').remove(); calculateActualExpenses()" style="background: transparent; border: none; padding: 0.25rem 0.5rem;">
                                <i class="fas fa-times"></i>
                            </button>
                        </td>
                    `;
                    container.appendChild(row);
                });
            } else {
                addExpenseRow();
            }
            calculateActualExpenses();
        }
    }

    bk_openModal('bookingDetailModal');
}

function bk_closeBookingDetailModal() { 
    bk_closeModal('bookingDetailModal'); 
}

function switchBookingTab(tabId, targetEl) {
    document.querySelectorAll('.mtab-pane-pro').forEach(function(p) { p.classList.remove('active'); });
    document.querySelectorAll('.mtab-btn-pro').forEach(function(b) { 
        b.classList.remove('active');
        b.style.borderBottomColor = 'transparent';
        b.style.color = '#64748b';
    });
    var pane = document.getElementById('btab-' + tabId);
    if (pane) pane.classList.add('active');
    
    var activeBtn = targetEl || event?.currentTarget;
    if (activeBtn) {
        activeBtn.classList.add('active');
        activeBtn.style.borderBottomColor = 'var(--primary-color)';
        activeBtn.style.color = 'var(--primary-color)';
    }

    var saveBtn = document.getElementById('saveExpenseBtn');
    if (saveBtn) {
        if (tabId === 'financials') {
            saveBtn.style.display = 'flex';
        } else {
            saveBtn.style.display = 'none';
        }
    }
}

function resetBookingTabs() {
    document.querySelectorAll('.mtab-pane-pro').forEach(function(p) { p.classList.remove('active'); });
    document.querySelectorAll('.mtab-btn-pro').forEach(function(b) { b.classList.remove('active'); });
    var summaryTab = document.getElementById('btab-summary');
    if (summaryTab) summaryTab.classList.add('active');
    var firstBtn = document.querySelector('.mtab-btn-pro');
    if (firstBtn) firstBtn.classList.add('active');
}

// Global copy payment link function
window.copyInvoiceLink = function(bookingId) {
    const url = window.location.origin + '/customer/booking/' + bookingId + '/invoice';
    navigator.clipboard.writeText(url).then(() => {
        if (window.showSuccess) {
            window.showSuccess('Payment link copied to clipboard!');
        } else {
            alert('Payment link copied to clipboard!');
        }
    }).catch(err => {
        console.error('Could not copy text: ', err);
        if (window.showError) {
            window.showError('Failed to copy link.');
        } else {
            alert('Failed to copy link. Please manually copy: ' + url);
        }
    });
};

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
    const btn = window.event ? window.event.target.closest('button') : null;
    let originalText = '';
    
    if (btn) {
        originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = 'Saving...';
    }
    
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
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}

// ─── NEW: STEPPER LOGIC ──────────────────────────────────────────────────────

function updateBookingStepper(status, isPackage, isFoodOrder) {
    let steps;
    if (isFoodOrder) {
        steps = ['pending', 'preparing', 'on_the_way', 'arrived', 'completed'];
    } else {
        steps = isPackage 
            ? ['pending', 'confirmed', 'preparing', 'on_the_way', 'in_progress', 'completed']
            : ['pending', 'confirmed', 'preparing', 'on_the_way', 'completed'];
    }
        
    const ongoingStep = document.getElementById('stepperStepOngoing');
    if (ongoingStep) ongoingStep.style.display = (isPackage && !isFoodOrder) ? 'block' : 'none';
    
    const completedStepDot = document.getElementById('stepperStepCompletedDot');
    if (completedStepDot) completedStepDot.innerHTML = (isPackage && !isFoodOrder) ? '6' : '5';

    // Treat 'arrived' or 'setup_ongoing' as 'in_progress' for the stepper (non-food)
    let currentIdx = steps.indexOf(status);
    if (!isFoodOrder) {
        if (currentIdx === -1 && (status === 'arrived' || status === 'setup_ongoing')) {
            currentIdx = steps.indexOf('in_progress');
        }
    }
    // Treat ready_for_pickup/delivery as preparing
    if (currentIdx === -1 && (status === 'ready_for_pickup' || status === 'ready_for_delivery')) {
        currentIdx = steps.indexOf('preparing');
    }
    // Treat confirmed as pending for food orders if it wasn't caught
    if (isFoodOrder && status === 'confirmed') {
        currentIdx = steps.indexOf('preparing');
    }
    
    document.querySelectorAll('.step-pro').forEach((step) => {
        if (step.style.display === 'none') return;
        
        const stepStatus = step.getAttribute('data-step');
        const idx = steps.indexOf(stepStatus);
        
        const dot = step.querySelector('.step-dot');
        step.classList.remove('active', 'completed');
        
        if (idx < currentIdx) {
            step.classList.add('completed');
            if (dot) dot.innerHTML = '<i class="fas fa-check"></i>';
        } else if (idx === currentIdx) {
            step.classList.add('active');
            // Retain original number
            if (dot) dot.innerHTML = (idx + 1).toString();
        } else {
            if (dot) dot.innerHTML = (idx + 1).toString();
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
    var todayStr = new Date().toISOString().split('T')[0];
    if (newDate <= todayStr) { window.showError('Deadline must be set to a future date (at least tomorrow).'); return; }
    if (currentEventDate && newDate > currentEventDate) { window.showError('Deadline cannot be after the event date. It must be settled before or on the event day.'); return; }
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
    
    // --- TIER 2: 24-HOUR LEAD TIME VALIDATION ---
    const rowBtn = document.querySelector(`.view-details[data-id="${bookingId}"]`);
    if (rowBtn && rowBtn.dataset.eventDate) {
        const eventDate = new Date(rowBtn.dataset.eventDate);
        const now = new Date();
        
        // If event date is exactly today or tomorrow, calculate strict hour diff
        // eventDate defaults to midnight UTC, so we add 12 hours to approximate midday PHT
        eventDate.setHours(eventDate.getHours() + 12);
        
        const diffMs = eventDate.getTime() - now.getTime();
        const diffHours = diffMs / (1000 * 60 * 60);

        // If the event is less than 24 hours away and they are just now accepting it, block it.
        // Exception: If they are just verifying the FINAL balance (isPayment=true and status is already confirmed), 
        // we shouldn't block. But confirmAcceptBooking is mainly used for initial accept/payment proof.
        // To be safe, we check if the status is still 'pending' or 'awaiting_payment'.
        const rawStatus = rowBtn.dataset.status;
        if ((rawStatus === 'pending' || rawStatus === 'pending_payment' || rawStatus === 'awaiting_payment') && diffHours < 24) {
            window.showAlert({
                type: 'error',
                title: 'Validation Failed',
                message: 'You have breached the 24-hour minimum preparation lead time. You can no longer accept this booking to protect event quality. Please mark as Rejected.',
                confirmText: 'Understood'
            });
            return;
        }
    }

    
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
                if (window.refreshBookingsTable) window.refreshBookingsTable();
            }
        },
        confirmTitle, confirmBtn, 'success'
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
    
    const btn = window.event ? (window.event.target.closest('button') || document.querySelector('#rejectReasonModal .btn-sm-danger')) : document.querySelector('#rejectReasonModal .btn-sm-danger');
    let originalText = '';
    if (btn) {
        originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Rejecting...';
    }
    
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
            if (window.refreshBookingsTable) window.refreshBookingsTable();
        } else {
            window.showError(data.detail || 'Failed to reject booking.');
        }
    } catch (err) {
        window.showError('Error connecting to server.');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}

function confirmCompleteBooking(bookingId) {
    const viewBtn = document.querySelector(`.view-details[data-id="${bookingId}"]`);
    const isPaid = viewBtn && viewBtn.dataset.paymentStatus === 'paid';
    
    if (!isPaid) {
        window.showError("Booking cannot be completed. Payment status must be 'Paid' first.");
        return;
    }

    window.showConfirm('Is the event finished and everything settled?',
        async function() {
            var result = await window.apiAction('/caterer/bookings/' + bookingId + '/update-status', { 
                method: 'POST', 
                body: JSON.stringify({status: 'completed'}) 
            });

            if (result && result.status === 'success') {
                window.showToast('Booking successfully marked as Completed! Great job!', 'success');
                if (window.refreshBookingsTable) window.refreshBookingsTable();
                
                setTimeout(() => {
                    const btn = document.querySelector(`.view-details[data-id="${bookingId}"]`);
                    if (btn && document.getElementById('bookingDetailModal').classList.contains('active')) {
                        window.showBookingDetails(btn);
                    }
                }, 500);
            }
        },
        'Mark as Completed?', 'Yes, Event Finished', 'success'
    );
}

window.validateAndProceed = function(bookingId, stage) {
    console.log('[BookingsJS] validateAndProceed triggered', {bookingId, stage});
    const progressEl = document.getElementById('checklistProgressText');
    const tasksCount = document.querySelectorAll('.task-item-pro').length;
    console.log('[BookingsJS] Checklist progress:', progressEl ? progressEl.innerText : 'null', 'Tasks:', tasksCount);
    
    if (tasksCount > 0 && progressEl && progressEl.innerText.trim() !== '100%') {
        alert('Operations Checklist must be 100% complete before you can dispatch the order.');
        return;
    }
    
    console.log('[BookingsJS] Validation passed. Opening dispatchProofModal.');
    
    // Panel Defense: Enforce Photographic Evidence
    document.getElementById('dispatchProofBookingId').value = bookingId;
    document.getElementById('dispatchProofStage').value = stage;
    document.getElementById('dispatchProofImage').value = '';
    bk_openModal('dispatchProofModal');
}

function closeDispatchProofModal() {
    bk_closeModal('dispatchProofModal');
}

window.submitDispatchProof = async function(event) {
    event.preventDefault();
    const fileInput = document.getElementById('dispatchProofImage');
    if (!fileInput.files || fileInput.files.length === 0) {
        window.showError('Please upload a photo of the prepared food.');
        return;
    }

    const bookingId = document.getElementById('dispatchProofBookingId').value;
    const stage = document.getElementById('dispatchProofStage').value;
    const btn = document.getElementById('dispatchProofSubmitBtn');
    
    const oldText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';

    const formData = new FormData();
    formData.append('stage', stage);
    formData.append('proof_image', fileInput.files[0]);

    try {
        const response = await fetch('/caterer/bookings/' + bookingId + '/dispatch-proof', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.status === 'success') {
            closeDispatchProofModal();
            window.showToast('Dispatch proof uploaded and status updated.', 'success');
            if (window.refreshBookingsTable) window.refreshBookingsTable();
            
            setTimeout(() => {
                const btnView = document.querySelector(`.view-details[data-id="${bookingId}"]`);
                if (btnView && document.getElementById('bookingDetailModal').classList.contains('active')) {
                    window.showBookingDetails(btnView);
                }
            }, 500);
        } else {
            window.showError(data.detail || 'Failed to upload dispatch proof.');
        }
    } catch (err) {
        window.showError('Connection error while uploading proof.');
    } finally {
        btn.innerHTML = oldText;
        btn.disabled = false;
    }
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
            var result = await window.apiAction('/caterer/bookings/' + bookingId + '/update-status', { 
                method: 'POST', 
                body: JSON.stringify({ status: status }) 
            });

            if (result && result.status === 'success') {
                window.showToast('Status updated successfully and customer notified.', 'success');
                if (window.refreshBookingsTable) window.refreshBookingsTable();
                
                // Re-open modal if it was open
                setTimeout(() => {
                    const btn = document.querySelector(`.view-details[data-id="${bookingId}"]`);
                    if (btn && document.getElementById('bookingDetailModal').classList.contains('active')) {
                        window.showBookingDetails(btn);
                    }
                }, 500);
            }
        },
        titles[status] || 'Update Status', 'Yes, Proceed', 'primary'
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
                if (window.refreshBookingsTable) window.refreshBookingsTable();
                
                setTimeout(() => {
                    const btn = document.querySelector(`.view-details[data-id="${bookingId}"]`);
                    if (btn && document.getElementById('bookingDetailModal').classList.contains('active')) {
                        window.showBookingDetails(btn);
                    }
                }, 500);
            }
        },
        'Request New Proof?', 'Yes, Notify Customer', 'warning'
    );
}

function confirmArchiveBooking(bookingId) {
    window.showConfirm('This booking will be moved to the archives and can no longer be modified.',
        async function() { await window.apiAction('/caterer/bookings/' + bookingId + '/archive', { method: 'POST' }); },
        'Archive Booking #' + bookingId, 'Archive Now', 'danger'
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
function initWalkinLocation() {
    const provSelect = document.getElementById('bookProvince');
    const citySelect = document.getElementById('bookCity');
    const brgySelect = document.getElementById('bookBarangay');
    if (!provSelect || !citySelect || !brgySelect) return;

    if (typeof LOCATION_DATA === 'undefined') {
        console.warn('[BookingsJS] LOCATION_DATA not found. Retrying...');
        setTimeout(initWalkinLocation, 500);
        return;
    }

    provSelect.addEventListener('change', () => {
        citySelect.innerHTML = '<option value="">Select City...</option>';
        brgySelect.innerHTML = '<option value="">Select Barangay...</option>';
        
        const prov = provSelect.value;
        if (prov && LOCATION_DATA[prov]) {
            const cities = Object.keys(LOCATION_DATA[prov]).sort();
            cities.forEach(city => {
                const opt = document.createElement('option');
                opt.value = opt.textContent = city;
                citySelect.appendChild(opt);
            });
        }
    });

    citySelect.addEventListener('change', () => {
        brgySelect.innerHTML = '<option value="">Select Barangay...</option>';
        const prov = provSelect.value;
        const city = citySelect.value;
        if (prov && city && LOCATION_DATA[prov] && LOCATION_DATA[prov][city]) {
            LOCATION_DATA[prov][city].sort().forEach(b => {
                const opt = document.createElement('option');
                opt.value = opt.textContent = b;
                brgySelect.appendChild(opt);
            });
        }
    });
}

window.toggleBookingExportMenu = function(event) {
    event.stopPropagation();
    const menu = document.getElementById('bookingExportMenu');
    if (menu) {
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    }
};

document.addEventListener('click', function(e) {
    const menu = document.getElementById('bookingExportMenu');
    if (menu && !e.target.closest('.action-dropdown-container')) {
        menu.style.display = 'none';
    }
});

window.exportBookings = function(format) {
    const menu = document.getElementById('bookingExportMenu');
    if (menu) menu.style.display = 'none';
    
    const rows = document.querySelectorAll('.bookings-list-table tbody tr.booking-row-item');
    const searchInput = (document.getElementById('bookingSearchInput') ? document.getElementById('bookingSearchInput').value : '').toLowerCase();
    const statusFilter = document.getElementById('statusFilter') ? document.getElementById('statusFilter').value : '';
    const visibleRows = Array.from(rows).filter(function(row) {
        const rawStatus = row.dataset.status || '';
        const payStatus = row.dataset.paymentStatus || '';
        const rowText = row.innerText.toLowerCase();
        
        const matchesSearch = rowText.indexOf(searchInput) > -1;
        let matchesStatus = false;
        
        if (statusFilter === '') {
            matchesStatus = true;
        } else if (statusFilter === 'action_required') {
            const needsSignature = ['pending_quotation', 'awaiting_caterer'].includes(rawStatus);
            const needsPaymentVerify = ['proof_submitted', 'balance_proof_submitted'].includes(payStatus);
            const isUrgent = row.dataset.isUrgent === 'true';
            matchesStatus = needsSignature || needsPaymentVerify || isUrgent;
        } else if (statusFilter === 'pending') {
            matchesStatus = ['pending', 'awaiting_caterer', 'pending_quotation'].includes(rawStatus);
        } else {
            matchesStatus = rawStatus === statusFilter;
        }
        
        return matchesSearch && matchesStatus;
    });
    
    if (visibleRows.length === 0) {
        alert("No bookings visible to export. Try clearing your filters.");
        return;
    }

    const data = [];
    visibleRows.forEach(row => {
        try {
            const cells = row.querySelectorAll('td');
            if (cells.length < 7) return;
            
            // Clean up innerText by replacing newlines with spaces and trimming
            const clean = (text) => text.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
            
            const idText = clean(cells[0].innerText);
            const customer = clean(cells[1].innerText);
            const eventInfo = clean(cells[2].innerText);
            const dateTime = clean(cells[3].innerText);
            const guests = clean(cells[4].innerText);
            const amount = clean(cells[5].innerText).replace('₱', '').trim();
            const status = clean(cells[6].innerText);
            
            data.push({ idText, customer, eventInfo, dateTime, guests, amount, status });
        } catch(e) {
            console.error('Row parsing error', e);
        }
    });

    if (data.length === 0) return;

    if (format === 'excel') {
        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += "Booking ID,Customer,Event,Date & Time,Guests,Amount,Status\n";
        
        data.forEach(d => {
            const escapeCSV = (val) => '"' + String(val).replace(/"/g, '""') + '"';
            const rowStr = [d.idText, d.customer, d.eventInfo, d.dateTime, d.guests, d.amount, d.status].map(escapeCSV).join(",");
            csvContent += rowStr + "\n";
        });
        
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `bookings_export_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } 
    else if (format === 'pdf' || format === 'word') {
        let html = `
        <html><head><title>Bookings Report</title>
        <style>
            body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; padding: 2rem; color: #333; }
            h2 { border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; color: #0f172a; margin-bottom: 25px; }
            .meta-info { margin-bottom: 20px; font-size: 14px; color: #64748b; }
            table { width: 100%; border-collapse: collapse; font-size: 12px; }
            th, td { border: 1px solid #cbd5e1; padding: 12px 8px; text-align: left; vertical-align: top; }
            th { background: #f8fafc; font-weight: 700; color: #475569; text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em; }
            tr:nth-child(even) { background: #fcfcfd; }
            .amount { font-weight: bold; color: #0f172a; white-space: nowrap; }
            .status { font-weight: bold; color: #64748b; }
        </style></head><body>
        <h2>Bookings Database Report</h2>
        <div class="meta-info"><strong>Generated on:</strong> ${new Date().toLocaleString()}</div>
        <table>
            <thead>
                <tr>
                    <th width="10%">ID</th>
                    <th width="20%">Customer</th>
                    <th width="20%">Event Info</th>
                    <th width="15%">Date & Time</th>
                    <th width="10%">Guests</th>
                    <th width="12%">Amount</th>
                    <th width="13%">Status</th>
                </tr>
            </thead>
            <tbody>
        `;
        
        data.forEach(d => {
            html += `<tr>
                <td><strong>${d.idText}</strong></td>
                <td>${d.customer}</td>
                <td>${d.eventInfo}</td>
                <td>${d.dateTime}</td>
                <td>${d.guests}</td>
                <td class="amount">${d.amount}</td>
                <td class="status">${d.status}</td>
            </tr>`;
        });
        
        html += `</tbody></table></body></html>`;

        if (format === 'word') {
            const blob = new Blob(['\ufeff', html], {
                type: 'application/msword'
            });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `bookings_export_${new Date().toISOString().split('T')[0]}.doc`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } else {
            const printWindow = window.open('', '_blank');
            printWindow.document.write(html);
            printWindow.document.close();
            setTimeout(() => {
                printWindow.print();
            }, 500);
        }
    }
};

// ─── CONSULTATION CHAT ───────────────────────────────────────────────────────

async function loadBookingMessages(bookingId) {
    const container = document.getElementById('modalChatMessages');
    const formBookingId = document.getElementById('chatBookingId');
    if (formBookingId) formBookingId.value = bookingId;
    
    if (!container) return;
    
    container.innerHTML = '<div style="text-align:center;padding:2rem;color:#94a3b8;"><i class="fas fa-spinner fa-spin"></i> Loading messages...</div>';
    
    try {
        const res = await fetch(`/caterer/api/bookings/${bookingId}/messages`);
        const result = await res.json();
        
        if (result.status === 'success') {
            const messages = result.messages;
            if (messages.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; color: var(--dm-slate-400); font-size: 0.85rem; margin-top: 2rem;">
                        <i class="fas fa-comments fa-2x" style="opacity: 0.3; margin-bottom: 0.5rem; display: block;"></i>
                        No messages yet. Start a conversation with your customer!
                    </div>
                `;
            } else {
                container.innerHTML = messages.map(msg => {
                    const justify = msg.is_me ? 'flex-end' : 'flex-start';
                    const bg = msg.is_me ? 'var(--primary-color)' : 'white';
                    const color = msg.is_me ? 'white' : 'var(--up-slate-900)';
                    const radius = msg.is_me ? '16px 16px 0 16px' : '16px 16px 16px 0';
                    const icon = msg.is_me ? '<div style="width:32px;height:32px;border-radius:50%;background:var(--dm-slate-200);display:flex;align-items:center;justify-content:center;color:var(--up-slate-900);font-size:0.75rem;flex-shrink:0;"><i class="fas fa-store"></i></div>' : '<div style="width:32px;height:32px;border-radius:50%;background:var(--up-slate-900);display:flex;align-items:center;justify-content:center;color:white;font-size:0.75rem;flex-shrink:0;"><i class="fas fa-user"></i></div>';
                    
                    let attachmentHtml = '';
                    if (msg.attachment_url) {
                        attachmentHtml = `
                            ${msg.message ? '<br><br>' : ''}
                            <a href="${msg.attachment_url}" target="_blank" style="color: inherit; text-decoration: underline; font-size: 0.75rem;"><i class="fas fa-paperclip"></i> View Attachment</a>
                        `;
                    }
                    
                    return `
                        <div style="display: flex; gap: 0.75rem; justify-content: ${justify};">
                            ${!msg.is_me ? icon : ''}
                            <div style="max-width: 80%;">
                                <div style="background: ${bg}; color: ${color}; padding: 0.75rem 1rem; border-radius: ${radius}; box-shadow: 0 2px 4px rgba(0,0,0,0.05); font-size: 0.85rem; line-height: 1.4;">
                                    ${msg.message ? msg.message : ''}
                                    ${attachmentHtml}
                                </div>
                                <div style="font-size: 0.65rem; color: var(--dm-slate-400); margin-top: 4px; text-align: ${msg.is_me ? 'right' : 'left'};">
                                    ${msg.created_at}
                                </div>
                            </div>
                            ${msg.is_me ? icon : ''}
                        </div>
                    `;
                }).join('');
                container.scrollTop = container.scrollHeight;
            }
        }
    } catch (err) {
        container.innerHTML = '<div style="text-align:center;padding:2rem;color:#ef4444;">Failed to load messages.</div>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('modalChatForm');
    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('chatSubmitBtn');
            const messageInput = document.getElementById('chatMessageInput');
            const attachmentInput = document.getElementById('chatAttachmentInput');
            const bookingId = document.getElementById('chatBookingId').value;
            
            if (!messageInput.value.trim() && !attachmentInput.files.length) return;
            
            const originalBtn = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            btn.disabled = true;
            
            const formData = new FormData(chatForm);
            
            try {
                const res = await fetch(`/bookings/${bookingId}/messages`, {
                    method: 'POST',
                    body: formData
                });
                if (res.ok) {
                    messageInput.value = '';
                    attachmentInput.value = '';
                    loadBookingMessages(bookingId);
                } else {
                    window.showError("Failed to send message.");
                }
            } catch (err) {
                window.showError("Network error while sending message.");
            } finally {
                btn.innerHTML = originalBtn;
                btn.disabled = false;
            }
        });
    }
});

// ─── EQUIPMENT RENTAL HANDLERS ───────────────────────────────────────────────

window.openRentalReleaseModal = function(bookingId) {
    document.getElementById('releaseBookingId').value = bookingId;
    bk_openModal('rentalReleaseModal');
};

window.closeRentalReleaseModal = function() {
    bk_closeModal('rentalReleaseModal');
    document.getElementById('rentalReleaseForm').reset();
};

window.submitRentalRelease = async function(e) {
    e.preventDefault();
    const btn = document.getElementById('releaseSubmitBtn');
    const form = document.getElementById('rentalReleaseForm');
    const bookingId = document.getElementById('releaseBookingId').value;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    
    try {
        const formData = new FormData(form);
        const res = await fetch(`/caterer/rentals/${bookingId}/release`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        
        if (data.success) {
            Swal.fire({icon: 'success', title: 'Equipment Released', text: data.message});
            closeRentalReleaseModal();
            if (window.refreshBookingsTable) window.refreshBookingsTable();
        } else {
            Swal.fire({icon: 'error', title: 'Action Failed', text: data.message});
        }
    } catch (err) {
        Swal.fire({icon: 'error', title: 'Network Error', text: 'Failed to communicate with server.'});
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Release Equipment';
    }
};

window.openRentalInspectionModal = function(bookingId) {
    document.getElementById('inspectBookingId').value = bookingId;
    bk_openModal('rentalInspectionModal');
    toggleDamagePhotoRequirement();
};

window.closeRentalInspectionModal = function() {
    bk_closeModal('rentalInspectionModal');
    document.getElementById('rentalInspectionForm').reset();
    toggleDamagePhotoRequirement();
};

window.toggleDamagePhotoRequirement = function() {
    const deductionInput = document.getElementById('deductionAmount');
    const photoGroup = document.getElementById('damagePhotoGroup');
    const photoInput = document.getElementById('damagePhoto');
    
    if (parseFloat(deductionInput.value) > 0) {
        photoGroup.style.display = 'block';
        photoInput.required = true;
    } else {
        photoGroup.style.display = 'none';
        photoInput.required = false;
    }
};

window.submitRentalInspection = async function(e) {
    e.preventDefault();
    const btn = document.getElementById('inspectSubmitBtn');
    const form = document.getElementById('rentalInspectionForm');
    const bookingId = document.getElementById('inspectBookingId').value;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    
    try {
        const formData = new FormData(form);
        const res = await fetch(`/caterer/rentals/${bookingId}/inspect`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        
        if (data.success) {
            Swal.fire({icon: 'success', title: 'Inspection Complete', text: data.message});
            closeRentalInspectionModal();
            if (window.refreshBookingsTable) window.refreshBookingsTable();
        } else {
            Swal.fire({icon: 'error', title: 'Action Failed', text: data.message});
        }
    } catch (err) {
        Swal.fire({icon: 'error', title: 'Network Error', text: 'Failed to communicate with server.'});
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Complete Return';
    }
};
