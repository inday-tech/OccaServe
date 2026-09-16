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
    window.setUniversalFilter = setUniversalFilter;
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
    window.refreshOpenBookingWorkspace = function(bookingId) {
        if (!currentBookingId || String(currentBookingId) !== String(bookingId)) return;
        const viewButton = document.querySelector(`button.view-details[data-id="${bookingId}"]`);
        if (!viewButton) return;
        viewButton.dataset.workspaceHydrated = '';
        showBookingDetails(viewButton);
    };
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
            const newBanner = doc.getElementById('alertBanner');
            const currentBanner = document.getElementById('alertBanner');
            
            if (currentBanner && newBanner) {
                currentBanner.outerHTML = newBanner.outerHTML;
            } else if (!currentBanner && newBanner) {
                const kpiGrid = document.querySelector('.kpi-grid-clean');
                if (kpiGrid) {
                    kpiGrid.insertAdjacentHTML('afterend', newBanner.outerHTML);
                }
            } else if (currentBanner && !newBanner) {
                currentBanner.remove();
            }

            if (newTbody) {
                document.querySelector('.bookings-list-table tbody').innerHTML = newTbody.innerHTML;
                const allRows = Array.from(document.querySelectorAll('.bookings-list-table tbody tr.booking-row-item'));
                filteredRows = allRows;
                initDetailListeners();
                filterBookings();
            }
        } catch(e) {
            console.error('Failed to refresh bookings table', e);
            setTimeout(() => window.location.reload(), 1500); // Fallback
        }
    };
    
    // Operations Checklist
    window.loadBookingTasks = loadBookingTasks;
    window.addNewCustomTask = addNewCustomTask;
    window.addBookingTaskFromInput = addBookingTaskFromInput;
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
    if (id === 'bookingDetailModal') {
        const msgInput = document.getElementById('chatMessageInput');
        if (msgInput) msgInput.value = '';
        const attInput = document.getElementById('chatAttachmentInput');
        if (attInput) attInput.value = '';
    }
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

/* ─── Safe action menu toggle & context-aware overflow builder ─── */
function closeAllBookingMenus() {
    document.querySelectorAll('.overflow-menu').forEach(function(m) {
        m.classList.remove('open', 'position-top');
        m.style.display = 'none';
        m.style.top = '';
        m.style.right = '';
        m.style.left = '';
        m.style.bottom = '';
    });
}

function setupMenuKeyboardNav(menuEl) {
    if (!menuEl) return;
    const items = Array.from(menuEl.querySelectorAll('.overflow-action-item'));
    if (!items.length) return;
    items.forEach(function(item, idx) {
        item.tabIndex = 0;
        item.onkeydown = function(e) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                const next = items[(idx + 1) % items.length];
                if (next) next.focus();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                const prev = items[(idx - 1 + items.length) % items.length];
                if (prev) prev.focus();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                closeAllBookingMenus();
                const trigger = menuEl.parentElement ? menuEl.parentElement.querySelector('.overflow-trigger') : null;
                if (trigger) trigger.focus();
            }
        };
    });
}

function toggleActionMenuBookings(id, event) {
    if (event) {
        event.stopPropagation();
        if (event.preventDefault) event.preventDefault();
    }
    var target = document.getElementById('actionMenu-' + id);
    if (!target) return;

    var trigger = (event && (event.currentTarget || event.target.closest('.overflow-trigger'))) 
                  || (target.parentElement ? target.parentElement.querySelector('.overflow-trigger') : null);

    var isOpen = target.classList.contains('open') && target.style.display === 'block';

    // Close all open menus first
    closeAllBookingMenus();

    if (isOpen) {
        return;
    }

    // Attach target directly to document.body so no parent overflow can clip it
    if (target.parentElement !== document.body) {
        document.body.appendChild(target);
    }

    // Open target with fixed positioning
    target.classList.add('open');
    target.style.display = 'block';
    target.style.position = 'fixed';
    target.style.zIndex = '9999999';

    try {
        const bid = target.getAttribute('data-booking-id') || id;
        const status = (target.getAttribute('data-status') || '').toLowerCase();
        const payment = (target.getAttribute('data-payment-status') || '').toLowerCase();
        const totalAmount = parseFloat(target.getAttribute('data-total-amount') || '0');
        const amountPaid = parseFloat(target.getAttribute('data-amount-paid') || '0');
        const isPackage = (target.getAttribute('data-is-package') || 'false') === 'true';
        const isVerified = (target.getAttribute('data-is-verified') || 'false') === 'true';
        const userId = target.getAttribute('data-user-id') || '';

        const container = target.querySelector('.dynamic-actions');
        if (container) {
            container.innerHTML = '';

            const addAction = (label, icon, onClick, isDestructive = false) => {
                const b = document.createElement('button');
                b.type = 'button';
                b.className = 'overflow-action-item' + (isDestructive ? ' overflow-action-item--destructive' : '');
                b.innerHTML = `<i class="fas ${icon}"></i> <span>${label}</span>`;
                b.addEventListener('click', function(ev) {
                    ev.stopPropagation();
                    closeAllBookingMenus();
                    onClick();
                });
                container.appendChild(b);
            };

            const addSeparator = () => {
                const sep = document.createElement('div');
                sep.className = 'overflow-separator';
                container.appendChild(sep);
            };

            // 1. Edit Booking (Status not completed, cancelled, or expired)
            if (!['completed', 'cancelled', 'expired'].includes(status)) {
                addAction('Edit Booking', 'fa-edit', function() {
                    currentBookingId = bid;
                    if (typeof window.openEditBookingModal === 'function') {
                        window.openEditBookingModal();
                    } else {
                        const viewBtn = target.querySelector('.view-details');
                        if (viewBtn) window.showBookingDetails(viewBtn);
                    }
                });
            }

            // 2. Update Payment (Has total > 0, not fully paid, not cancelled)
            const isFullyPaid = (totalAmount > 0 && amountPaid >= totalAmount) || ['paid', 'fully_paid'].includes(payment);
            if (totalAmount > 0 && !isFullyPaid && status !== 'cancelled') {
                addAction('Update Payment', 'fa-money-bill-wave', function() {
                    const viewBtn = target.querySelector('.view-details');
                    if (viewBtn) {
                        window.showBookingDetails(viewBtn);
                        setTimeout(function() {
                            const finBtn = document.querySelector('#bookingDetailModal [data-tab="finance"]');
                            if (finBtn && typeof window.switchBookingTab === 'function') {
                                window.switchBookingTab('finance', finBtn);
                            }
                        }, 350);
                    }
                });
            }

            // 3. View Customer (Has userId)
            if (userId) {
                addAction('View Customer', 'fa-user', function() {
                    const viewBtn = target.querySelector('.view-details');
                    if (viewBtn) {
                        window.showBookingDetails(viewBtn);
                        setTimeout(function() {
                            const chatBtn = document.querySelector('#bookingDetailModal [data-tab="chat"]');
                            if (chatBtn && typeof window.switchBookingTab === 'function') {
                                window.switchBookingTab('chat', chatBtn);
                            }
                        }, 350);
                    }
                });
            }

            // 4. Preparation Checklist
            if (['confirmed', 'preparing', 'setup_ongoing', 'in_progress', 'ready_for_delivery', 'ready_for_pickup', 'arrived'].includes(status)) {
                addAction('Preparation Checklist', 'fa-tasks', function() {
                    const viewBtn = target.querySelector('.view-details');
                    if (viewBtn) {
                        window.showBookingDetails(viewBtn);
                        setTimeout(function() {
                            const chk = document.getElementById('modalChecklistSection');
                            if (chk) chk.scrollIntoView({ behavior: 'smooth' });
                            if (typeof window.loadBookingTasks === 'function') {
                                window.loadBookingTasks(bid);
                            }
                        }, 350);
                    }
                });
            }

            // 5. View Activity (Always)
            addAction('View Activity', 'fa-history', function() {
                const viewBtn = target.querySelector('.view-details');
                if (viewBtn) {
                    window.showBookingDetails(viewBtn);
                    setTimeout(function() {
                        const actBtn = document.querySelector('#bookingDetailModal [data-tab="activity"]');
                        if (actBtn && typeof window.switchBookingTab === 'function') {
                            window.switchBookingTab('activity', actBtn);
                        }
                        if (typeof window.loadBookingHistory === 'function') {
                            window.loadBookingHistory(bid);
                        }
                    }, 350);
                }
            });

            // 6. Copy Payment Link (Payable booking with userId)
            if (userId && !['completed', 'cancelled'].includes(status) && !isFullyPaid) {
                addAction('Copy Payment Link', 'fa-link', function() {
                    if (typeof window.copyInvoiceLink === 'function') {
                        window.copyInvoiceLink(bid);
                    }
                });
            }

            // 7. Cancel Booking (Destructive - Status not completed, cancelled, or expired)
            if (!['completed', 'cancelled', 'expired'].includes(status)) {
                addSeparator();
                addAction('Cancel Booking', 'fa-times-circle', function() {
                    if (typeof window.confirmRejectBooking === 'function') {
                        window.confirmRejectBooking(bid);
                    }
                }, true);
            }

            setupMenuKeyboardNav(target);
        }
    } catch (e) {
        console.error('Failed to build action menu', e);
    }

    // Now calculate position after actions are added and target has real height
    if (trigger) {
        const triggerRect = trigger.getBoundingClientRect();
        const menuRect = target.getBoundingClientRect();
        const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
        const viewportWidth = window.innerWidth || document.documentElement.clientWidth;

        let topPos = triggerRect.bottom + 6;
        if (topPos + menuRect.height > viewportHeight - 12) {
            const aboveTop = triggerRect.top - menuRect.height - 6;
            if (aboveTop >= 10) {
                topPos = aboveTop;
                target.classList.add('position-top');
            } else {
                topPos = Math.max(10, viewportHeight - menuRect.height - 12);
                target.classList.remove('position-top');
            }
        } else {
            target.classList.remove('position-top');
        }

        let rightPos = viewportWidth - triggerRect.right;
        if (rightPos < 10) rightPos = 10;
        if (viewportWidth - rightPos - menuRect.width < 10) {
            rightPos = Math.max(10, viewportWidth - menuRect.width - 10);
        }

        target.style.top = topPos + 'px';
        target.style.right = rightPos + 'px';
        target.style.left = 'auto';
        target.style.bottom = 'auto';
    }
}

window.toggleActionMenuBookings = toggleActionMenuBookings;
window.closeAllBookingMenus = closeAllBookingMenus;

// Close overflow menus on click-outside, scroll, resize, or Escape key
document.addEventListener('click', function(e) {
    if (!e.target.closest('.overflow-menu') && !e.target.closest('.overflow-trigger')) {
        closeAllBookingMenus();
    }
});

window.addEventListener('scroll', function() {
    closeAllBookingMenus();
}, true);

window.addEventListener('resize', function() {
    closeAllBookingMenus();
});

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeAllBookingMenus();
    }
});

document.addEventListener('DOMContentLoaded', function () {
    console.log('[BookingsJS] Initializing components... [v1.8-robust]');

    try {
        // Override toggleActionMenu for this page
        window.toggleActionMenu = toggleActionMenuBookings;
        window.toggleActionMenuBookings = toggleActionMenuBookings;

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

        // 5. Wire search input (visible) to filtering with debounce
        const searchEl = document.getElementById('bookingSearchInput');
        if (searchEl) {
            let sTimer = null;
            searchEl.addEventListener('input', function() {
                clearTimeout(sTimer);
                sTimer = setTimeout(() => { filterBookings(); }, 200);
            });
        }

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

        // Polling removed in favor of accurate server-side rendering
        console.log('[BookingsJS] Manage Bookings JS Ready. [v2.0-english-standard]');
    } catch (err) {
        console.error('[BookingsJS] CRITICAL ERROR DURING INIT:', err);
    }
});

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

function setUniversalFilter(filterVal) {
    const statusSelect = document.getElementById('statusFilter');
    const sourceSelect = document.getElementById('sourceFilter');
    const uniSelect = document.getElementById('universalFilter');

    if (filterVal === 'online' || filterVal === 'walkin') {
        if (sourceSelect) {
            sourceSelect.value = (sourceSelect.value === filterVal) ? '' : filterVal;
        }
        if (statusSelect) statusSelect.value = '';
        if (uniSelect) uniSelect.value = sourceSelect ? sourceSelect.value : filterVal;
    } else if (filterVal === 'completed' || filterVal === 'cancelled' || filterVal === 'pending' || filterVal === 'confirmed' || filterVal === 'preparing' || filterVal === 'in_progress') {
        if (statusSelect) {
            statusSelect.value = (statusSelect.value === filterVal) ? '' : filterVal;
        }
        if (sourceSelect) sourceSelect.value = '';
        if (uniSelect) uniSelect.value = statusSelect ? statusSelect.value : filterVal;
    } else if (filterVal === 'all') {
        if (statusSelect) statusSelect.value = '';
        if (sourceSelect) sourceSelect.value = '';
        if (uniSelect) uniSelect.value = 'all';
    }

    filterBookings();
}

function filterBookings() {
    const searchInput = document.getElementById('bookingSearchInput') ? document.getElementById('bookingSearchInput').value.trim().toLowerCase() : '';
    const statusFilter = document.getElementById('statusFilter') ? document.getElementById('statusFilter').value.toLowerCase() : '';
    const sourceFilter = document.getElementById('sourceFilter') ? document.getElementById('sourceFilter').value.toLowerCase() : '';
    const universalFilter = document.getElementById('universalFilter') ? document.getElementById('universalFilter').value.toLowerCase() : '';

    // Synchronize KPI card highlights with current filter selection
    const kpiOnline = document.getElementById('kpi-card-online');
    if (kpiOnline) kpiOnline.classList.toggle('active-kpi', sourceFilter === 'online' || universalFilter === 'online');

    const kpiWalkin = document.getElementById('kpi-card-walkin');
    if (kpiWalkin) kpiWalkin.classList.toggle('active-kpi', sourceFilter === 'walkin' || universalFilter === 'walkin');

    const kpiCompleted = document.getElementById('kpi-card-completed');
    if (kpiCompleted) kpiCompleted.classList.toggle('active-kpi', statusFilter === 'completed' || universalFilter === 'completed');

    const kpiCancelled = document.getElementById('kpi-card-cancelled');
    if (kpiCancelled) kpiCancelled.classList.toggle('active-kpi', statusFilter === 'cancelled' || universalFilter === 'cancelled');

    // Filter table rows and smart cards simultaneously
    const tableRows = Array.from(document.querySelectorAll('tr.booking-row-item'));
    const cards = Array.from(document.querySelectorAll('.smart-booking-card'));
    const allItems = tableRows.length > 0 ? tableRows : cards;

    filteredRows = allItems.filter(function(el) {
        const rawStatus = (el.dataset.status || '').toLowerCase();
        const payStatus = (el.dataset.paymentStatus || '').toLowerCase();
        const rawEntry = (el.dataset.entryMethod || el.dataset.source || '').toLowerCase();
        const searchText = (el.dataset.searchText || el.textContent || '').toLowerCase();

        // 1. Search text matching
        if (searchInput && searchText.indexOf(searchInput) === -1) {
            return false;
        }

        // 2. Status filtering
        const activeStatus = statusFilter || (['pending','confirmed','completed','cancelled'].includes(universalFilter) ? universalFilter : '');
        if (activeStatus) {
            if (activeStatus === 'pending') {
                const isPending = ['pending', 'draft', 'inquiry', 'awaiting_customer', 'pending_quotation', 'awaiting_caterer', 'awaiting_payment', 'pending_payment', 'pending_review', 'under_review'].includes(rawStatus);
                if (!isPending) return false;
            } else if (activeStatus === 'confirmed') {
                if (rawStatus !== 'confirmed') return false;
            } else if (activeStatus === 'preparing') {
                if (rawStatus !== 'preparing') return false;
            } else if (activeStatus === 'in_progress') {
                const isOngoing = ['in_progress', 'setup_ongoing', 'on_the_way', 'ready_for_delivery', 'ready_for_pickup', 'arrived'].includes(rawStatus);
                if (!isOngoing) return false;
            } else if (activeStatus === 'completed') {
                if (rawStatus !== 'completed') return false;
            } else if (activeStatus === 'cancelled') {
                const isCancelled = ['cancelled', 'rejected', 'void'].includes(rawStatus);
                if (!isCancelled) return false;
            } else if (rawStatus !== activeStatus) {
                return false;
            }
        }

        // 3. Source filtering
        const activeSource = sourceFilter || (['online','walkin'].includes(universalFilter) ? universalFilter : '');
        if (activeSource) {
            if (activeSource === 'online') {
                const isOnline = rawEntry === 'online' || rawEntry.indexOf('website') > -1 || rawEntry.indexOf('occaserve') > -1;
                if (!isOnline) return false;
            } else if (activeSource === 'walkin') {
                const isWalkin = rawEntry === 'walkin' || rawEntry === 'walk_in' || rawEntry === 'internal' || rawEntry.indexOf('walk') > -1;
                if (!isWalkin) return false;
            }
        }

        return true;
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

    // Collect IDs of items for this page
    const pageItems = filteredRows.slice(startIdx, endIdx);
    const visibleIds = new Set();
    pageItems.forEach(function(item) {
        const rowId = item.id.replace('booking-row-', '');
        if (rowId) visibleIds.add(rowId);
        if (item.dataset.bookingId) visibleIds.add(item.dataset.bookingId.replace('BK-', '').replace(/^0+/, ''));
    });

    // Hide/show table rows
    document.querySelectorAll('tr.booking-row-item').forEach(function(r) { 
        const id = r.id.replace('booking-row-', '');
        r.style.display = visibleIds.has(id) ? '' : 'none'; 
    });

    // Hide/show smart cards
    document.querySelectorAll('.smart-booking-card').forEach(function(c) { 
        const btn = c.querySelector('button');
        let cardId = null;
        if (btn && btn.getAttribute('onclick')) {
            const m = btn.getAttribute('onclick').match(/(?:toggleActionMenuBookings\(['"]?|#actionMenu-)(\d+)/);
            if (m) cardId = m[1];
        }
        if (!cardId) {
            const refEl = c.querySelector('.smart-booking-ref');
            if (refEl) {
                const rm = refEl.textContent.match(/\d+/);
                if (rm) cardId = String(parseInt(rm[0], 10));
            }
        }
        if (cardId) {
            c.style.display = visibleIds.has(cardId) ? '' : 'none';
        } else {
            c.style.display = 'none';
        }
    });

    const searchEmpty = document.getElementById('searchEmptyState');
    if (searchEmpty) {
        searchEmpty.style.display = filteredRows.length === 0 ? '' : 'none';
    }
    const smartEmpty = document.getElementById('smartSearchEmptyState');
    if (smartEmpty) smartEmpty.style.display = filteredRows.length === 0 ? '' : 'none';

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
        totalExpense += parseFloat(String(rawVal).replace(/,/g, '')) || 0;
    });
    
    var bookingTotalEl = document.getElementById('bookingTotalAmount');
    var bookingTotal = bookingTotalEl ? (parseFloat(String(bookingTotalEl.value).replace(/,/g, '')) || 0) : 0;
    var profit = bookingTotal - totalExpense;
    var roi = 0;
    var isZeroExpense = false;
    if (totalExpense > 0) {
        roi = (profit / totalExpense) * 100;
    } else if (bookingTotal > 0) {
        roi = 100;
        isZeroExpense = true;
    }
    
    // Update Displays
    var display = document.getElementById('totalActualExpenseDisplay');
    if (display) display.innerText = '₱' + totalExpense.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    
    var profitDisplay = document.getElementById('modalEstimateProfit');
    if (profitDisplay) {
        profitDisplay.innerText = '₱' + profit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        profitDisplay.style.color = profit >= 0 ? '#10b981' : '#ef4444';
    }
    
    var roiDisplay = document.getElementById('modalRoiPercent');
    if (roiDisplay) {
        var roiText = roiDisplay.querySelector('span');
        var roiIcon = document.getElementById('roiTrendIcon');
        
        if (roiText) {
            roiText.innerText = Math.round(roi) + (isZeroExpense ? '%*' : '%');
            roiDisplay.title = isZeroExpense ? 'Gross margin (no expenses recorded yet)' : 'Return on Investment (Profit / Expense)';
        }
        
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
    if (btn.dataset.workspaceHydrated !== 'true') {
        if (btn.dataset.workspaceHydrated === 'loading') return;
        btn.dataset.workspaceHydrated = 'loading';
        bk_openModal('bookingDetailModal');
        const loadingStatus = document.getElementById('modalStatus');
        if (loadingStatus) loadingStatus.innerText = 'Loading booking...';
        fetch(`/caterer/api/bookings/${btn.dataset.id}/details`, { headers: { 'Accept': 'application/json' } })
            .then(response => {
                if (!response.ok) throw new Error('Unable to load booking details');
                return response.json();
            })
            .then(detail => {
                const user = detail.user || {};
                const fields = {
                    status: detail.status || btn.dataset.status || '',
                    paymentStatus: detail.payment_status || btn.dataset.paymentStatus || 'no_payment',
                    source: detail.booking_source || btn.dataset.source || '',
                    sourceKind: detail.source_kind || (detail.user_id ? 'online' : 'walkin'),
                    entryMethod: detail.entry_method || '',
                    paymentRecordsJson: JSON.stringify(detail.payment_records || []),
                    eventDate: detail.event_date || '',
                    eventTime: detail.event_time || 'TBA',
                    customer: detail.customer_name || [user.first_name, user.last_name].filter(Boolean).join(' ') || 'Walk-in Customer',
                    email: user.email || detail.customer_email || '',
                    contact: user.phone_number || detail.customer_contact || '',
                    venue: detail.venue || 'Not specified',
                    eventType: detail.event_type || 'Booking',
                    specificName: (detail.package && detail.package.name) || detail.event_name || detail.event_type || 'Booking',
                    guestCount: detail.guest_count || 0,
                    totalRawAmount: detail.total_amount || 0,
                    amountPaid: detail.amount_paid || 0,
                    paymentMethod: detail.payment_method || 'Not specified',
                    paymentPlan: detail.payment_plan || 'downpayment',
                    paymentRef: detail.payment_reference || '',
                    bookedOn: detail.created_at ? new Date(detail.created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }) : 'Not available',
                    balanceDue: detail.balance_due_date ? detail.balance_due_date.slice(0, 10) : '',
                    actualCost: detail.actual_cost || 0,
                    targetUserId: detail.user_id || (detail.user ? detail.user.id : ''),
                    isPackage: detail.is_package,
                    isFoodOrder: detail.document_type === 'invoice' || detail.event_type === 'Ala Carte Order',
                    isVerified: user.is_verified,
                    preparationStatus: detail.preparation_status || 'not_started',
                    requests: detail.special_requests || '',
                    documentType: detail.document_type || '',
                    proofUrl: detail.payment_proof_url || '',
                    balanceProofUrl: detail.balance_proof_url || '',
                    hasMenu: Boolean(detail.package || (detail.selected_items && detail.selected_items.length)),
                    catererNotes: detail.caterer_notes || ''
                };
                Object.entries(fields).forEach(([key, value]) => {
                    btn.dataset[key] = value == null ? '' : String(value);
                });
                btn.dataset.workspaceHydrated = 'true';
                showBookingDetails(btn);
            })
            .catch(error => {
                btn.dataset.workspaceHydrated = '';
                const status = document.getElementById('modalStatus');
                if (status) status.innerText = 'Unable to load';
                if (window.showError) window.showError(error.message || 'Unable to load booking details.');
            });
        return;
    }
    var data = btn.dataset;
    var bookingStatus = data.status || '';
    var totalAmountValue = Math.max(parseFloat(data.totalRawAmount) || 0, 0);
    var paidAmountValue = Math.max(parseFloat(data.amountPaid) || 0, 0);
    data.amount = '₱' + totalAmountValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    data.totalRawAmount = String(totalAmountValue);
    resetBookingTabs();
    currentBookingId = data.id;
    window.currentBookingTargetUserId = data.targetUserId;
    window.currentBookingStatus = data.status;
    currentEventDate = data.eventDate;

    const resetModalTab = (id, fallback) => {
        const element = document.getElementById(id);
        if (element && !element.innerHTML.trim()) element.innerHTML = fallback;
    };
    resetModalTab('modalHistoryTimeline', '<div style="color:#64748b; text-align:center; padding:1rem;">No activity recorded for this booking.</div>');
    
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
    
    const vAmountPaid = document.getElementById('vAmountPaid'); if(vAmountPaid) vAmountPaid.innerText = '₱' + paidAmountValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const vRefNumber = document.getElementById('vRefNumber'); if(vRefNumber) vRefNumber.innerText = data.paymentRef || 'N/A';
    const vPaymentStatus = document.getElementById('vPaymentStatus'); 
    if(vPaymentStatus) {
        let pStatus = data.paymentStatus || 'pending';
        let pColor = '#d97706'; let pBg = '#fef3c7';
        if (data.status === 'inquiry' || data.status === 'draft') {
            pStatus = 'not requested yet';
            pColor = '#64748b'; pBg = '#f1f5f9';
        } else if (pStatus === 'paid' || pStatus === 'fully_paid') { pColor = '#16a34a'; pBg = '#dcfce3'; }
        else if (pStatus === 'expired') { pColor = '#991b1b'; pBg = '#fef2f2'; }
        vPaymentStatus.innerHTML = `<span class="badge" style="background: ${pBg}; color: ${pColor};">${pStatus.replace('_', ' ').toUpperCase()}</span>`;
    }
    // ---------------------------------

    const isFoodOrder = data.isFoodOrder === 'true' || data.isFoodOrder === true;
    const formattedRefId = (isFoodOrder ? 'ORD-' : 'BK-') + String(data.id).padStart(6, '0');
    let titlePrefix = isFoodOrder ? 'Food Order #' : (data.status === 'pending_review' ? 'Inquiry Details #' : 'Booking #');
    
    const mbTitle = document.getElementById('modalBookingId');
    if (mbTitle) mbTitle.innerText = titlePrefix + formattedRefId;
    const mbId = document.getElementById('modalBookingIdMobile');
    if (mbId) mbId.innerText = (isFoodOrder ? 'Order #' : 'Booking #') + formattedRefId;
    
    // Urgent Indicator in Modal Header
    if (data.isUrgent === 'true') {
        if (mbTitle) mbTitle.innerHTML = `${titlePrefix}${formattedRefId} <span style="background: #fff1f2; color: #e11d48; font-size: 0.65rem; padding: 2px 8px; border-radius: 50px; margin-left: 8px; border: 1px solid #fecdd3; vertical-align: middle;"><i class="fas fa-clock"></i> URGENT</span>`;
        if (mbId) mbId.innerHTML = `${(isFoodOrder ? 'Order #' : 'Booking #')}${formattedRefId} <span style="background: #fff1f2; color: #e11d48; font-size: 0.65rem; padding: 2px 8px; border-radius: 50px; margin-left: 8px; border: 1px solid #fecdd3; vertical-align: middle;"><i class="fas fa-clock"></i> URGENT</span>`;
    }

    const modalSource = document.getElementById('modalBookingSource');
    const modalSourceMobile = document.getElementById('modalBookingSourceMobile');
    const modalSourceBadge = document.getElementById('modalBookingSourceBadge');
    const modalSourceBadgeMobile = document.getElementById('modalBookingSourceBadgeMobile');
    const modalSourceIcon = document.getElementById('modalBookingSourceIcon');
    const modalSourceSubtext = document.getElementById('modalBookingSourceSubtext');
    const modalSourceSubtextMobile = document.getElementById('modalBookingSourceSubtextMobile');

    const sourceValue = (data.source || '').toString().trim().toLowerCase();
    const rawSourceKind = (data.sourceKind || data.entryMethod || '').toString().trim().toLowerCase();
    const _targetUid = (data.targetUserId || '').toString().trim();
    const _hasUser = _targetUid !== '' && _targetUid !== 'null' && _targetUid !== 'undefined' && _targetUid !== '0';
    const isWalkin = sourceValue.includes('walk') || sourceValue === 'manual' || sourceValue.includes('internal')
        || rawSourceKind.includes('walk') || rawSourceKind === 'manual'
        || (!_hasUser && !sourceValue.includes('online'));
    
    const sourceText = isWalkin ? 'WALK-IN' : 'ONLINE';
    const sourceSubtext = isWalkin ? 'Created by Caterer' : 'Booked by Customer';
    
    if (modalSource) modalSource.innerText = sourceText;
    if (modalSourceMobile) modalSourceMobile.innerText = sourceText;
    if (modalSourceSubtext) modalSourceSubtext.innerText = sourceSubtext;
    if (modalSourceSubtextMobile) modalSourceSubtextMobile.innerText = sourceSubtext;

    if (modalSourceBadge) {
        modalSourceBadge.style.background = isWalkin ? '#ffedd5' : '#f3e8ff';
        modalSourceBadge.style.color = isWalkin ? '#c2410c' : '#7e22ce';
        modalSourceBadge.style.border = isWalkin ? '1px solid #fed7aa' : '1px solid #e9d5ff';
    }
    if (modalSourceBadgeMobile) {
        modalSourceBadgeMobile.style.background = isWalkin ? '#ffedd5' : '#f3e8ff';
        modalSourceBadgeMobile.style.color = isWalkin ? '#c2410c' : '#7e22ce';
        modalSourceBadgeMobile.style.border = isWalkin ? '1px solid #fed7aa' : '1px solid #e9d5ff';
    }
    if (modalSourceIcon) {
        modalSourceIcon.className = isWalkin ? 'fas fa-store' : 'fas fa-globe';
    }

    // Chat Tab Conditional Rendering
    const tabBtnChat = document.getElementById('tabBtnChat');
    const chatOnlineView = document.getElementById('chatOnlineView');
    const chatWalkinView = document.getElementById('chatWalkinView');
    if (tabBtnChat) {
        if (isWalkin) {
            tabBtnChat.style.display = 'inline-flex';
            tabBtnChat.innerHTML = '<span>Contact Customer</span>';
            if (chatOnlineView) chatOnlineView.style.display = 'none';
            if (chatWalkinView) chatWalkinView.style.display = 'flex';
            
            // Set SMS and Email Links
            const smsLink = document.getElementById('walkinCommSms');
            const emailLink = document.getElementById('walkinCommEmail');
            if (smsLink && data.contact) smsLink.href = 'sms:' + data.contact;
            if (emailLink && data.email) emailLink.href = 'mailto:' + data.email;
        } else {
            tabBtnChat.style.display = 'inline-flex';
            tabBtnChat.innerHTML = '<span>Communication</span>';
            if (chatOnlineView) chatOnlineView.style.display = 'flex';
            if (chatWalkinView) chatWalkinView.style.display = 'none';
        }
    }

    configureBookingTabs(data, { isWalkin, isFoodOrder });

    const mCust = document.getElementById('modalCustomer'); if (mCust) mCust.innerText = data.customer || '';
    const mEmail = document.getElementById('modalEmail'); if (mEmail) mEmail.innerText = data.email || '';
    const labelEl = document.getElementById('modalEventDetailsLabel');
    if (labelEl) {
        labelEl.innerText = isFoodOrder ? 'Order Details' : 'Event Details';
    }
    const mEvName = document.getElementById('modalEventName'); if (mEvName) mEvName.innerText = data.specificName || data.eventName || '';
    const mEvType = document.getElementById('modalEventType'); if (mEvType) mEvType.innerHTML = `<i class="fas fa-tag" style="margin-right: 4px;"></i>${data.eventType || ''}`;
    const mVenue = document.getElementById('modalVenue'); if (mVenue) mVenue.innerText = data.venue || '';
    
    const reqEl = document.getElementById('modalRequests');
    if (reqEl) {
        if (!data.requests || data.requests.trim() === '' || data.requests === 'None') {
            reqEl.innerHTML = '<div style="color: #64748b; font-style: normal; display: flex; align-items: center; gap: 8px;"><i class="fas fa-info-circle" style="color: #94a3b8;"></i> No special requests recorded for this booking.</div>';
            reqEl.style.background = '#f8fafc';
            reqEl.style.borderColor = '#e2e8f0';
            reqEl.style.color = '#64748b';
        } else {
            reqEl.innerText = data.requests;
            reqEl.style.background = '#fffbeb';
            reqEl.style.borderColor = '#fef3c7';
            reqEl.style.color = '#92400e';
        }
    }
    const menuSpan = document.getElementById('menuBreakdownHeaderSpan');
    if (menuSpan) {
        if (data.eventType === 'Equipment Rental') {
            menuSpan.innerHTML = '<i class="fas fa-tools" style="color: var(--primary-color);"></i> Rented Equipment & Item Breakdown';
        } else if (data.eventType === 'Service Only') {
            menuSpan.innerHTML = '<i class="fas fa-user-tie" style="color: var(--primary-color);"></i> Staffing & Service Inclusions Breakdown';
        } else if (isFoodOrder || data.eventType === 'Ala Carte Order') {
            menuSpan.innerHTML = '<i class="fas fa-utensils" style="color: var(--primary-color);"></i> Food Orders & Ala Carte Breakdown';
        } else {
            menuSpan.innerHTML = '<i class="fas fa-layer-group" style="color: var(--primary-color);"></i> Final Menu & Package Inclusions Breakdown';
        }
    }
    const titleMaster = document.getElementById('titleMasterContract');
    const descMaster = document.getElementById('descMasterContract');
    const btnMaster = document.getElementById('btnViewMasterContract');
    if (titleMaster && descMaster && btnMaster) {
        if (data.eventType === 'Equipment Rental' || data.documentType === 'rental_agreement') {
            titleMaster.innerHTML = '<i class="fas fa-file-contract" style="color: var(--primary-color, #FF7B54); font-size: 1rem;"></i> Equipment Rental Agreement & Liability Terms';
            descMaster.innerText = 'Access digitally signed Rental Agreement & Equipment Liability Terms governing equipment return and damage policies.';
            btnMaster.innerHTML = '<i class="fas fa-file-contract" style="margin-right: 8px;"></i> View Equipment Rental Agreement';
        } else if (data.eventType === 'Service Only' || data.documentType === 'service_agreement') {
            titleMaster.innerHTML = '<i class="fas fa-file-contract" style="color: var(--primary-color, #FF7B54); font-size: 1rem;"></i> Event Service Agreement & Staffing Terms';
            descMaster.innerText = 'Access digitally signed Service Agreement governing labor, staffing hours, and on-site service terms.';
            btnMaster.innerHTML = '<i class="fas fa-user-tie" style="margin-right: 8px;"></i> View Service Terms & Agreement';
        } else if (isFoodOrder || data.eventType === 'Ala Carte Order' || data.documentType === 'invoice') {
            titleMaster.innerHTML = '<i class="fas fa-file-invoice-dollar" style="color: var(--primary-color, #FF7B54); font-size: 1rem;"></i> Order Confirmation & Delivery Invoice';
            descMaster.innerText = 'Access itemized food order confirmation, delivery/pickup instructions, and invoice terms.';
            btnMaster.innerHTML = '<i class="fas fa-file-invoice-dollar" style="margin-right: 8px;"></i> View Order Invoice & Terms';
        } else {
            titleMaster.innerHTML = '<i class="fas fa-file-contract" style="color: var(--primary-color, #FF7B54); font-size: 1rem;"></i> Master Catering Service Agreement';
            descMaster.innerText = 'Access digitally signed Master Service Agreement and complete package terms.';
            btnMaster.innerHTML = '<i class="fas fa-file-signature" style="margin-right: 8px;"></i> View Master Service Agreement';
        }
        
        // Hide Contract Card completely for Walk-ins since they don't have accounts to sign with
        if (isWalkin && titleMaster.parentElement) {
            titleMaster.parentElement.style.display = 'none';
        } else if (titleMaster.parentElement) {
            titleMaster.parentElement.style.display = 'flex';
        }
    }
    const linkKyc = document.getElementById('linkViewCustomerAudit');
    if (linkKyc) {
        if (!data.targetUserId || data.targetUserId === 'undefined' || data.targetUserId === '') {
            linkKyc.style.opacity = '0.6';
            linkKyc.title = 'No registered KYC profile for this customer';
        } else {
            linkKyc.style.opacity = '1';
            linkKyc.title = 'View verified identity and KYC audit profile';
        }
    }

    // --- POPULATE COMPACT HEADER SUMMARY BAR ---
    const hCust = document.getElementById('headerSummaryCustomer'); if (hCust) hCust.innerText = data.customer || 'Walk-in Customer';
    const hType = document.getElementById('headerSummaryEventType'); if (hType) hType.innerText = data.eventType || 'Booking';
    const hDate = document.getElementById('headerSummaryDate'); if (hDate) hDate.innerText = formattedDate;
    const hTime = document.getElementById('headerSummaryTime'); if (hTime) hTime.innerText = formattedTime;
    const hPax = document.getElementById('headerSummaryPax'); if (hPax) hPax.innerText = (data.guestCount || 0) + ' pax';
    const hVenue = document.getElementById('headerSummaryVenue'); if (hVenue) hVenue.innerText = data.venue || 'TBA';

    // --- POPULATE OVERVIEW TAB: Event Information Card ---
    const ovEvType = document.getElementById('ovEventType'); if (ovEvType) ovEvType.innerText = data.eventType || '—';
    const ovEvDate = document.getElementById('ovEventDate'); if (ovEvDate) ovEvDate.innerText = formattedDate;
    const ovEvTime = document.getElementById('ovEventTime'); if (ovEvTime) ovEvTime.innerText = formattedTime;
    const ovPax = document.getElementById('ovGuestCount'); if (ovPax) ovPax.innerText = (data.guestCount || 0) + ' pax';
    const ovVen = document.getElementById('ovVenue'); if (ovVen) ovVen.innerText = data.venue || 'Not specified';

    // --- POPULATE OVERVIEW TAB: Booking Information Card ---
    const ovRef = document.getElementById('ovBookingRef'); if (ovRef) ovRef.innerText = formattedRefId;
    const ovSrcBadge = document.getElementById('ovSourceBadge');
    if (ovSrcBadge) {
        ovSrcBadge.innerText = sourceText;
        ovSrcBadge.style.color = isWalkin ? '#c2410c' : '#7e22ce';
    }
    const ovCreated = document.getElementById('ovCreatedDate'); if (ovCreated) ovCreated.innerText = data.bookedOn || '—';
    const ovStatusTxt = document.getElementById('ovStatusText');
    const ovStaff = document.getElementById('ovAssignedStaff'); if (ovStaff) ovStaff.innerText = isWalkin ? 'Caterer / Staff (Walk-in)' : 'Customer (Online Booking)';

    // --- POPULATE OVERVIEW TAB: Financial Overview ---
    const ovTot = document.getElementById('ovTotalDisplay'); if (ovTot) ovTot.innerText = data.amount;
    const ovPaid = document.getElementById('ovPaidDisplay'); if (ovPaid) ovPaid.innerText = '₱' + paidAmountValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const ovBal = document.getElementById('ovBalanceDisplay'); if (ovBal) ovBal.innerText = '₱' + Math.max(totalAmountValue - paidAmountValue, 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    // --- POPULATE CUSTOMER TAB ---
    const custNote = document.getElementById('custSourceNote');
    if (custNote) {
        custNote.innerText = isWalkin ? 'WALK-IN ENTRY' : 'ONLINE ACCOUNT';
        custNote.style.background = isWalkin ? '#ffedd5' : '#e0e7ff';
        custNote.style.color = isWalkin ? '#c2410c' : '#3730a3';
    }
    const custName = document.getElementById('custFullName'); if (custName) custName.innerText = data.customer || 'Walk-in Customer';
    const custMob = document.getElementById('custMobile'); if (custMob) custMob.innerText = data.contact || 'No mobile provided';
    const custEm = document.getElementById('custEmail'); if (custEm) custEm.innerText = data.email || 'No email provided';
    const custTyp = document.getElementById('custType'); if (custTyp) custTyp.innerText = isWalkin ? 'Walk-in Customer (Manual Entry)' : 'Registered Platform User';

    const btnCall = document.getElementById('btnCallCustomer');
    if (btnCall) {
        if (data.contact) { btnCall.href = 'tel:' + data.contact; btnCall.style.pointerEvents = 'auto'; btnCall.style.opacity = '1'; }
        else { btnCall.href = '#'; btnCall.style.pointerEvents = 'none'; btnCall.style.opacity = '0.5'; }
    }
    const btnEm = document.getElementById('btnEmailCustomer');
    if (btnEm) {
        if (data.email) { btnEm.href = 'mailto:' + data.email; btnEm.style.pointerEvents = 'auto'; btnEm.style.opacity = '1'; }
        else { btnEm.href = '#'; btnEm.style.pointerEvents = 'none'; btnEm.style.opacity = '0.5'; }
    }

    // --- POPULATE ORDER & PACKAGE TAB ---
    const orderPkg = document.getElementById('orderPkgName'); if (orderPkg) orderPkg.innerText = data.specificName || data.eventType || 'Standard Package';
    const orderMeta = document.getElementById('orderPkgMeta'); if (orderMeta) orderMeta.innerText = isFoodOrder ? 'Ala Carte / Direct Food Order' : (Number(data.guestCount) ? `For ${data.guestCount} pax` : 'Custom Package');
    const orderPrice = document.getElementById('orderPkgPrice'); if (orderPrice) orderPrice.innerText = data.amount;

    // --- POPULATE PAYMENT TAB ---
    const payBadge = document.getElementById('paymentTabBadge');
    if (payBadge) {
        let pSt = (data.paymentStatus || 'unpaid').toUpperCase().replace(/_/g, ' ');
        payBadge.innerText = pSt;
        if (pSt === 'PAID' || pSt === 'FULLY PAID') { payBadge.style.background = '#dcfce7'; payBadge.style.color = '#166534'; }
        else { payBadge.style.background = '#fff7ed'; payBadge.style.color = '#c2410c'; }
    }
    const payTot = document.getElementById('payTotalAmount'); if (payTot) payTot.innerText = data.amount;
    const payPd = document.getElementById('payTotalPaid'); if (payPd) payPd.innerText = '₱' + paidAmountValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const payBal = document.getElementById('payBalance'); if (payBal) payBal.innerText = '₱' + Math.max(totalAmountValue - paidAmountValue, 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    // Payment History Table Population
    const payRows = document.getElementById('paymentHistoryRows');
    if (payRows) {
        let records = [];
        try { if (data.paymentRecordsJson) records = JSON.parse(data.paymentRecordsJson); } catch (e) {}
        if (records.length > 0) {
            payRows.innerHTML = records.map(r => {
                const rDate = r.payment_date ? new Date(r.payment_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'N/A';
                const rAmt = '₱' + (parseFloat(r.amount) || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                return `<tr>
                    <td style="padding: 0.75rem 1rem; color: #334155;">${rDate}</td>
                    <td style="padding: 0.75rem 1rem; color: #334155; font-weight: 600;">${r.payment_method || 'Cash'}</td>
                    <td style="padding: 0.75rem 1rem; color: #64748b;">${r.reference_notes || 'N/A'}</td>
                    <td style="padding: 0.75rem 1rem; text-align: right; font-weight: 800; color: #166534;">${rAmt}</td>
                    <td style="padding: 0.75rem 1rem; text-align: center;"><span style="background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 800;">VERIFIED</span></td>
                </tr>`;
            }).join('');
        } else if (paidAmountValue > 0) {
            payRows.innerHTML = `<tr>
                <td style="padding: 0.75rem 1rem; color: #334155;">${data.bookedOn || formattedDate}</td>
                <td style="padding: 0.75rem 1rem; color: #334155; font-weight: 600;">${data.paymentMethod || 'Cash'}</td>
                <td style="padding: 0.75rem 1rem; color: #64748b;">${data.paymentRef || 'Recorded by Caterer'}</td>
                <td style="padding: 0.75rem 1rem; text-align: right; font-weight: 800; color: #166534;">₱${paidAmountValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td style="padding: 0.75rem 1rem; text-align: center;"><span style="background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 800;">RECORDED</span></td>
            </tr>`;
        } else {
            payRows.innerHTML = `<tr><td colspan="5" style="padding: 1.5rem; text-align: center; color: #94a3b8;">No payment records found.</td></tr>`;
        }
    }

    var statusEl = document.getElementById('modalStatus');
    var statusElMobile = document.getElementById('modalStatusMobile');
    var statusLabels = {
        inquiry: 'Inquiry', draft: 'Draft', pending: 'Pending Payment', pending_review: 'New Inquiry',
        pending_quotation: 'Quotation Pending', awaiting_caterer: 'For Caterer Action',
        awaiting_customer: 'For Customer Action', awaiting_payment: 'Awaiting Payment',
        confirmed: 'Confirmed', preparing: 'Preparing', ready_for_pickup: 'Ready for Pickup',
        ready_for_delivery: 'Ready for Delivery', on_the_way: 'Out for Delivery', arrived: 'Arrived',
        setup_ongoing: 'Setup Ongoing', in_progress: 'In Progress', completed: 'Completed',
        cancelled: 'Cancelled', tentative: 'Tentative'
    };
    var statusText = data.displayStatus || statusLabels[bookingStatus] || bookingStatus.replace(/_/g, ' ').toUpperCase() || 'Status unavailable';
    
    if (statusEl) {
        statusEl.innerText = statusText;
        statusEl.className = 'badge-status';
    }
    
    if (statusElMobile) {
        statusElMobile.innerText = statusText;
        statusElMobile.className = 'badge-status';
    }
    
    var statusMap = {
        'inquiry': 'badge-draft',
        'draft': 'badge-draft',
        'pending': 'badge-pending',
        'pending_review': 'badge-pending',
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
    var badgeClass = data.displayBadge || statusMap[data.status] || 'badge-draft';
    if (statusEl) statusEl.classList.add(...badgeClass.trim().split(/\s+/));
    if (statusElMobile) statusElMobile.classList.add(...badgeClass.trim().split(/\s+/));

    // Also populate overview tab status text
    if (ovStatusTxt) {
        ovStatusTxt.innerText = statusText;
        const statusColorMap = {
            confirmed: '#16a34a', completed: '#16a34a', preparing: '#2563eb',
            on_the_way: '#7c3aed', arrived: '#0891b2', setup_ongoing: '#ca8a04',
            cancelled: '#dc2626', pending: '#d97706', pending_review: '#d97706',
            draft: '#64748b', inquiry: '#64748b'
        };
        ovStatusTxt.style.color = statusColorMap[bookingStatus] || '#0f172a';
    }

    // Payment Status Badge in header
    const paymentBadgeHeader = document.getElementById('modalPaymentStatusBadge');
    if (paymentBadgeHeader) {
        let pSt = (data.paymentStatus || 'unpaid').toUpperCase().replace(/_/g, ' ');
        paymentBadgeHeader.innerText = pSt;
        if (pSt === 'PAID' || pSt === 'FULLY PAID') {
            paymentBadgeHeader.style.background = '#dcfce7'; paymentBadgeHeader.style.color = '#166534'; paymentBadgeHeader.style.border = '1px solid #bbf7d0';
        } else {
            paymentBadgeHeader.style.background = '#fff7ed'; paymentBadgeHeader.style.color = '#c2410c'; paymentBadgeHeader.style.border = '1px solid #fed7aa';
        }
    }

    renderOverviewWorkspace(data, { isWalkin, isFoodOrder });

    var menuSource = document.getElementById('booking-items-' + data.id);
    var menuTarget = document.getElementById('modalMenuItems');
    var menuSection = document.getElementById('modalMenuSection');
    var menuDetailsBlock = document.getElementById('modalMenuDetailsBlock');
    
    let hasMenuData = data.hasMenu === 'true';
    if (hasMenuData && menuSource && menuSource.innerHTML.trim() !== '') {
        var menuCard = document.getElementById('menuCard');
        if (menuCard) menuCard.style.display = '';
        if (menuTarget) menuTarget.innerHTML = menuSource.innerHTML;
        if (menuSection) menuSection.style.display = 'block';
        if (menuDetailsBlock) menuDetailsBlock.style.display = 'block';
    } else {
        var emptyMenuCard = document.getElementById('menuCard');
        if (emptyMenuCard) emptyMenuCard.style.display = 'none';
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
        if (!hasProof) {
            proofContainer.innerHTML = '<div style="color: #94a3b8; font-size: 0.85rem; padding: 1rem 0; text-align: center; width: 100%;">No payment proofs uploaded yet.</div>';
        }
        proofSection.style.display = 'block';
    }

    // RISK ALERT HANDLING
    var riskAlert = document.getElementById('modalRiskAlert');
    var riskAlertMobile = document.getElementById('modalRiskAlertMobile');
    if (riskAlert) {
        let alertHtml = '';
        if (data.paymentStatus === 'expired') {
            alertHtml = '<span style="background:#fff1f2; color:#e11d48; border:1px solid #fecdd3; padding: 4px 12px; border-radius: 50px; font-weight: 800; font-size: 0.75rem; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-exclamation-triangle"></i> RESERVATION EXPIRED</span>';
        } else if (data.isPast === 'true') {
            alertHtml = '<span style="background:#fff1f2; color:#e11d48; border:1px solid #fecdd3; padding: 4px 12px; border-radius: 50px; font-weight: 800; font-size: 0.75rem; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-calendar-times"></i> EVENT DATE PASSED</span>';
        } else if (['pending', 'pending_quotation', 'awaiting_payment', 'awaiting_caterer'].includes(data.status) && (data.isUrgent === 'true' || data.isUrgent === true)) {
            alertHtml = '<span style="background:#fff1f2; color:#e11d48; border:1px solid #fecdd3; padding: 4px 12px; border-radius: 50px; font-weight: 800; font-size: 0.75rem; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-clock"></i> URGENT REQUEST</span>';
        }
        
        if (alertHtml) {
            riskAlert.style.display = 'block';
            riskAlert.innerHTML = alertHtml;
            riskAlert.style.background = 'transparent';
            riskAlert.style.border = 'none';
            riskAlert.style.padding = '0';
            
            if (riskAlertMobile) {
                riskAlertMobile.style.display = 'block';
                riskAlertMobile.innerHTML = alertHtml;
            }
        } else {
            riskAlert.style.display = 'none';
            if (riskAlertMobile) riskAlertMobile.style.display = 'none';
        }
    }

    
var actionsEl = document.getElementById('bookingModalActionsTop') || document.getElementById('bookingModalActions');
    const isVerified = data.isVerified === 'true' || data.isVerified === true;
    const targetUserId = data.targetUserId;
    const isPackage = data.isPackage === 'true' || data.isPackage === true;

    const isRental = data.eventType === 'Equipment Rental';
    
    // Show/hide manual payment card
    const manualPaymentCard = document.getElementById('manualPaymentCard');
    if (manualPaymentCard) {
        if (data.source && data.source.toLowerCase() !== 'occaserve online' && data.source !== 'Online') {
            manualPaymentCard.style.display = 'block';
        } else {
            manualPaymentCard.style.display = 'none';
        }
    }

    
    const totalAmountRaw = parseFloat(data.totalRawAmount || '0');
    let amountPaid = 0;
    if (data.paymentStatus === 'paid' || data.paymentStatus === 'fully_paid' || data.status === 'completed') {
        amountPaid = totalAmountRaw;
    } else if (data.status !== 'pending' && data.status !== 'awaiting_payment' && data.status !== 'pending_quotation' && data.status !== 'awaiting_caterer') {
        amountPaid = totalAmountRaw * 0.5;
    }
    const balance = totalAmountRaw - amountPaid;
    const prepStatus = data.preparationStatus || 'not_started';

    let nextStepMsg = 'No further action required.';
    let actionBtnHtml = '';

    if (data.status === 'cancelled') {
        nextStepMsg = isWalkin ? 'This walk-in booking has been cancelled.' : 'This customer booking has been cancelled.';
    } else if (data.status === 'completed') {
        nextStepMsg = isWalkin ? 'This walk-in booking is completed.' : 'This customer booking is completed.';
    } else if (isWalkin) {
        // WALK-IN WORKFLOW
        if (data.status === 'draft') {
            nextStepMsg = 'Complete customer and service information for this walk-in booking.';
            actionBtnHtml = `<button type="button" onclick="window.openEditBookingModal()" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#d97706; color:#b45309; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-edit"></i> Complete Booking</button>`;
        } else if (data.status === 'pending') {
            nextStepMsg = 'Verify the entered details and confirm this walk-in booking.';
            actionBtnHtml = `<button type="button" onclick="window.confirmAcceptBooking(${data.id}, false, false, ${isPackage})" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#10b981; color:#047857; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-check-circle"></i> Confirm Walk-in Booking</button>`;
        } else if (data.status === 'confirmed') {
            nextStepMsg = 'This booking was manually created by the caterer. Verify details and proceed with preparation.';
            actionBtnHtml = `<button type="button" onclick="window.updateBookingStage(${data.id}, 'preparing')" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#10b981; color:#047857; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-utensils"></i> Start Preparation</button>`;
        } else if (data.status === 'preparing') {
            nextStepMsg = 'Preparation is currently in progress. Continue monitoring the preparation checklist.';
            actionBtnHtml = `<button type="button" onclick="window.switchBookingTab('tasks', document.querySelector('.mtab-btn-pro[onclick*=\\'tasks\\']'))" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#10b981; color:#047857; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-tasks"></i> Open Preparation Checklist</button>`;
        } else if (data.status === 'ready_for_delivery') {
            nextStepMsg = 'Walk-in items are prepared. Dispatch when the team departs.';
            actionBtnHtml = `<button type="button" onclick="window.updateBookingStage(${data.id}, 'on_the_way')" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#2563eb; color:#1d4ed8; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-truck"></i> Out for Delivery</button>`;
        } else if (data.status === 'ready_for_pickup') {
            nextStepMsg = 'Walk-in order is ready for customer pickup.';
            actionBtnHtml = `<button type="button" onclick="window.confirmCompleteBooking(${data.id})" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#10b981; color:#047857; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-flag-checkered"></i> Mark Picked Up</button>`;
        } else if (data.status === 'on_the_way') {
            nextStepMsg = 'Walk-in order is in transit to the venue.';
            actionBtnHtml = `<button type="button" onclick="window.updateBookingStage(${data.id}, 'arrived')" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#2563eb; color:#1d4ed8; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-map-marker-alt"></i> Mark Arrived</button>`;
        } else if (data.status === 'arrived') {
            nextStepMsg = 'Team arrived at venue. Begin setup and service.';
            actionBtnHtml = `<button type="button" onclick="window.updateBookingStage(${data.id}, 'setup_ongoing')" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#2563eb; color:#1d4ed8; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-magic"></i> Start Setup</button>`;
        } else if (data.status === 'setup_ongoing' || data.status === 'in_progress') {
            nextStepMsg = 'Walk-in event is ongoing. Mark completed when finished.';
            actionBtnHtml = `<button type="button" onclick="window.confirmCompleteBooking(${data.id})" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#10b981; color:#047857; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-flag-checkered"></i> Mark Completed</button>`;
        }
    } else {
        // ONLINE CUSTOMER WORKFLOW
        if (data.status === 'inquiry') {
            nextStepMsg = 'Customer submitted booking inquiry. Prepare or review quotation.';
            actionBtnHtml = `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.openQuotationWorkspace(${data.id})"><i class="fas fa-file-invoice-dollar"></i> Prepare Quotation</button>`;
        } else if (data.status === 'pending_quotation') {
            nextStepMsg = 'Quotation sent. Waiting for customer to approve quotation.';
        } else if (data.status === 'awaiting_caterer') {
            nextStepMsg = 'Customer accepted quotation. Sign the service contract to finalize.';
            actionBtnHtml = `<button type="button" onclick="window.openIframeModal('/caterer/bookings/${data.id}/sign?modal=true', 'Sign Service Agreement')" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#2563eb; color:#1d4ed8; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-pen-nib"></i> Sign Contract Now</button>`;
        } else if (data.status === 'awaiting_customer') {
            nextStepMsg = 'Waiting for customer to sign the contract.';
        } else if (data.paymentStatus === 'expired') {
            nextStepMsg = 'Reservation expired. Please cancel or archive this booking.';
        } else if (data.status === 'pending') {
            if (data.paymentStatus === 'proof_submitted') {
                nextStepMsg = 'Customer submitted payment proof. Review and verify.';
                actionBtnHtml = `<button type="button" onclick="window.confirmAcceptBooking(${data.id}, true, ${isVerified}, ${isPackage})" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#10b981; color:#047857; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-check-double"></i> Verify Payment & Accept</button>`;
            } else if (data.paymentStatus === 'reupload_requested') {
                nextStepMsg = 'Re-upload requested. Waiting for customer to resubmit.';
            } else {
                nextStepMsg = 'Customer submitted booking request. Review booking details.';
                actionBtnHtml = `<button type="button" onclick="switchBookingTab('details', document.querySelector('[data-tab=\\'details\\']'))" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#2563eb; color:#1d4ed8; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-eye"></i> Review Booking</button>`;
            }
        } else if (data.status === 'confirmed') {
            if (data.paymentStatus === 'balance_proof_submitted') {
                nextStepMsg = 'Customer submitted final balance proof. Please verify.';
                actionBtnHtml = `<button type="button" onclick="window.confirmAcceptBooking(${data.id}, true)" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#10b981; color:#047857; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-check-double"></i> Verify Balance Proof</button>`;
            } else {
                nextStepMsg = 'This customer booking is confirmed and ready for preparation.';
                actionBtnHtml = `<button type="button" onclick="window.updateBookingStage(${data.id}, 'preparing')" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#10b981; color:#047857; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-utensils"></i> Start Preparation</button>`;
            }
        } else if (data.status === 'preparing') {
            nextStepMsg = 'Preparation is ongoing. Continue tracking tasks.';
            actionBtnHtml = `<button type="button" onclick="window.switchBookingTab('tasks', document.querySelector('.mtab-btn-pro[onclick*=\\'tasks\\']'))" class="btn-sm-outline" style="background:white; height:36px; font-size:0.75rem; white-space:nowrap; border-color:#10b981; color:#047857; cursor:pointer; width: 100%; margin-top: 10px;"><i class="fas fa-tasks"></i> Open Preparation Checklist</button>`;
        } else if (data.status === 'ready_for_pickup') {
            nextStepMsg = 'Waiting for customer to pick up the items.';
        } else if (data.status === 'ready_for_delivery') {
            nextStepMsg = 'Mark as out for delivery.';
        } else if (data.status === 'on_the_way') {
            nextStepMsg = isPackage ? 'Arrive at the venue location.' : 'Deliver items to customer.';
        } else if (data.status === 'arrived') {
            nextStepMsg = isPackage ? 'Setup the event and start serving.' : 'Complete the delivery/order.';
        } else if (data.status === 'setup_ongoing' || data.status === 'in_progress') {
            if (balance <= 0) {
                nextStepMsg = 'Event in progress. Mark as completed when done.';
            } else {
                if (data.paymentStatus === 'balance_proof_submitted') nextStepMsg = 'Verify final balance proof.';
                else nextStepMsg = 'Event in progress. Waiting for final bill settlement.';
            }
        }
    }
    var unifiedNST = document.getElementById('unifiedNextStepText');
    if (unifiedNST) unifiedNST.innerText = nextStepMsg;

    var primaryActionEl = document.getElementById('unifiedNextStepActionContainer');
    if (primaryActionEl) {
        primaryActionEl.innerHTML = '';
        primaryActionEl.style.display = 'none';
        if (actionBtnHtml) {
            primaryActionEl.innerHTML = actionBtnHtml;
            primaryActionEl.style.display = 'block';
        }
    }
    
    var mobileCST = document.getElementById('mobileCompactStatusText');
    var mobileCNST = document.getElementById('mobileCompactNextStatusText');
    if (mobileCST) mobileCST.innerText = statusText;
    if (mobileCNST) mobileCNST.innerText = nextStepMsg;

    if (actionsEl) {
        actionsEl.style.display = 'flex';
        actionsEl.innerHTML = '';

        // Edit Booking Button
        const canEditBooking = !['confirmed', 'preparing', 'setup_ongoing', 'in_progress', 'ready_for_pickup', 'ready_for_delivery', 'on_the_way', 'completed', 'cancelled'].includes(data.status) && !['paid', 'fully_paid', 'proof_submitted'].includes(data.paymentStatus);
        
        if (canEditBooking) {
            actionsEl.innerHTML += `<button onclick="window.openEditBookingModal()" class="btn-sm-outline" style="background:white; border:1px solid #cbd5e1; color:#475569; justify-content:flex-start; width:100%; margin-bottom: 8px; text-align: left; transition: background 0.2s;"><i class="fas fa-edit" style="width:20px; text-align:center;"></i> Modify Booking Details</button>`;
        } else {
            actionsEl.innerHTML += `<button class="btn-sm-outline" disabled title="Modification locked. Booking is fully paid or completed." style="background:#f8fafc; border:1px solid #e2e8f0; color:#94a3b8; justify-content:flex-start; width:100%; margin-bottom: 8px; text-align: left; cursor:not-allowed;"><i class="fas fa-lock" style="width:20px; text-align:center;"></i> Modification Locked</button>`;
        }

        const btnModifyTab = document.getElementById('btnModifyBookingDetailsTab');
        if (btnModifyTab) {
            if (canEditBooking) {
                btnModifyTab.disabled = false;
                btnModifyTab.innerHTML = `<i class="fas fa-edit"></i> Modify Booking`;
                btnModifyTab.style.cursor = 'pointer';
                btnModifyTab.style.opacity = '1';
                btnModifyTab.title = 'Edit booking details';
            } else {
                btnModifyTab.disabled = true;
                btnModifyTab.innerHTML = `<i class="fas fa-lock"></i> Locked`;
                btnModifyTab.style.cursor = 'not-allowed';
                btnModifyTab.style.opacity = '0.6';
                btnModifyTab.title = 'Modification locked. Booking is fully paid or completed.';
            }
        }

        
        // --- KYC WARNING BANNER ---
        var kycStatusEl = document.getElementById('modalKycStatus');
        if (kycStatusEl) {
            if (isWalkin) {
                kycStatusEl.innerHTML = `<div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;"><strong>No website account</strong> &bull; Platform KYC: N/A</div>`;
            } else if (!isVerified) {
                kycStatusEl.innerHTML = `<span style="color: #c2410c; background: #ffedd5; padding: 2px 6px; border-radius: 4px; font-weight: 700;"><i class="fas fa-clock"></i> Verification Pending by Admin</span>`;
            } else {
                kycStatusEl.innerHTML = `<span style="color: #15803d; background: #dcfce7; padding: 2px 6px; border-radius: 4px; font-weight: 700;"><i class="fas fa-check-circle"></i> Identity Verified by Admin</span>`;
            }
        }

        const plan = (data.paymentPlan || 'downpayment').toUpperCase();
        
        if (data.paymentStatus === 'expired') {
            actionsEl.innerHTML = `
                <div style="width: 100%; display: flex; flex-direction: column; gap: 1rem; background: #fff1f2; padding: 1rem; border-radius: 12px; border: 1px solid #fecdd3;">
                    <div style="display: flex; flex-direction: column; gap: 0.5rem; color: #881337; font-size: 0.85rem; font-weight: 600; text-align: center;">
                        <div style="width: 40px; height: 40px; border-radius: 50%; background: #ffe4e6; display: flex; align-items: center; justify-content: center; color: #e11d48; font-size: 1.2rem; margin: 0 auto;">
                            <i class="fas fa-clock"></i>
                        </div>
                        <div>
                            <div style="font-weight: 800; color: #991b1b; margin-bottom: 2px;">Reservation Expired</div>
                            <div style="font-size: 0.8rem; color: #be123c; font-weight: 500;">Failed to submit payment proof on time. Slot is no longer secured.</div>
                        </div>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                        <button type="button" onclick="window.confirmRejectBooking(${data.id})" style="background: #e11d48; color: white; border: none; padding: 0.65rem 1rem; border-radius: 8px; font-weight: 700; font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.5rem; transition: all 0.2s; box-shadow: 0 2px 6px rgba(225,29,72,0.25); width: 100%;">
                            <i class="fas fa-times-circle"></i> Cancel Booking
                        </button>
                        <button type="button" onclick="window.confirmArchiveBooking(${data.id})" style="background: white; color: #475569; border: 1px solid #cbd5e1; padding: 0.65rem 1rem; border-radius: 8px; font-weight: 600; font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.5rem; transition: all 0.2s; width: 100%;">
                            <i class="fas fa-archive"></i> Archive Record
                        </button>
                    </div>
                </div>
            `;
        } else if (data.status === 'pending') {
            const isCashOrCOD = data.paymentMethod === 'CASH' || data.paymentMethod === 'COD';
            const isPayment = data.paymentStatus === 'proof_submitted';
            let btnLabel = isPayment ? `Verify ${plan} & Accept` : 'Confirm & Accept Booking';
            let rejectLabel = 'Reject Booking';
            if (isFoodOrder) {
                btnLabel = isPayment ? `Verify Payment & Accept Order` : 'Confirm & Accept Order';
                rejectLabel = 'Reject Order';
            }
            const btnIcon = isPayment ? 'fa-check-double' : 'fa-check-circle';
            
            if (isWalkin) {
                if (primaryActionEl) {
                    primaryActionEl.innerHTML = `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.confirmAcceptBooking(${data.id}, false, ${isVerified}, ${isPackage})"><i class="fas fa-check-circle"></i> Confirm Walk-in Booking</button>`;
                    primaryActionEl.style.display = 'block';
                } else {
                    actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.confirmAcceptBooking(${data.id}, false, ${isVerified}, ${isPackage})"><i class="fas fa-check-circle"></i> Confirm Walk-in Booking</button>`;
                }
                actionsEl.innerHTML += `<button type="button" class="btn-footer-action" onclick="window.confirmRejectBooking(${data.id})" style="background: white; color: #e11d48; border: 1px solid #fecdd3; font-weight: 600;"><i class="fas fa-times-circle"></i> Cancel Walk-in Booking</button>`;
            } else if (isPayment || isCashOrCOD) {
                if (primaryActionEl) {
                    primaryActionEl.innerHTML = `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.confirmAcceptBooking(${data.id}, ${isPayment}, ${isVerified}, ${isPackage})"><i class="fas ${btnIcon}"></i> ${btnLabel}</button>`;
                    primaryActionEl.style.display = 'block';
                } else {
                    actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.confirmAcceptBooking(${data.id}, ${isPayment}, ${isVerified}, ${isPackage})"><i class="fas ${btnIcon}"></i> ${btnLabel}</button>`;
                }
                
                if (isPayment) {
                    actionsEl.innerHTML += `<button type="button" class="btn-footer-action" onclick="window.requestNewProof(${data.id})" style="background: white; color: #475569; border: 1px solid #cbd5e1; font-weight: 600;"><i class="fas fa-redo"></i> Request New Proof</button>`;
                }
                actionsEl.innerHTML += `<button type="button" class="btn-footer-action" onclick="window.confirmRejectBooking(${data.id})" style="background: white; color: #e11d48; border: 1px solid #fecdd3; font-weight: 600;"><i class="fas fa-times-circle"></i> ${rejectLabel}</button>`;
            } else if (data.paymentStatus === 'reupload_requested') {
                actionsEl.innerHTML += `<div style="padding: 0.65rem 1rem; color: #9f1239; background: #ffe4e6; border: 1px solid #fecdd3; border-radius: 8px; font-size: 0.85rem; font-weight: 600; flex: 1; display: flex; align-items: center; gap: 0.5rem;"><i class="fas fa-exclamation-triangle"></i> Re-upload Requested. Waiting for customer.</div>`;
                actionsEl.innerHTML += `<button type="button" class="btn-footer-action" onclick="window.confirmRejectBooking(${data.id})" style="background: white; color: #e11d48; border: 1px solid #fecdd3; font-weight: 600;"><i class="fas fa-times-circle"></i> ${rejectLabel}</button>`;
            } else {
                actionsEl.innerHTML += `<div style="padding: 0.65rem 1rem; color: #b45309; background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; font-size: 0.85rem; font-weight: 600; flex: 1; display: flex; align-items: center; gap: 0.5rem;"><i class="fas fa-clock"></i> Awaiting Payment Proof from Customer</div>`;
                actionsEl.innerHTML += `<button type="button" class="btn-footer-action" onclick="window.confirmRejectBooking(${data.id})" style="background: white; color: #e11d48; border: 1px solid #fecdd3; font-weight: 600;"><i class="fas fa-times-circle"></i> ${rejectLabel}</button>`;
            }
            
        } else if (data.status === 'awaiting_caterer') {
            actionsEl.innerHTML = `
                <button type="button" onclick="window.openIframeModal('/caterer/bookings/${data.id}/sign?modal=true', 'Sign Service Agreement')" class="btn-footer-action btn-status-confirm"><i class="fas fa-pen-nib"></i> Sign Contract Now</button>
                <button type="button" class="btn-footer-action" onclick="window.confirmRejectBooking(${data.id})" style="background: white; color: #e11d48; border: 1px solid #fecdd3; font-weight: 600;"><i class="fas fa-times-circle"></i> Reject Booking</button>
            `;
            
        } else if (data.status === 'awaiting_customer') {
            actionsEl.innerHTML = `
                <div style="padding: 0.65rem 1rem; color: #b45309; background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; font-size: 0.85rem; font-weight: 600; flex: 1; display: flex; align-items: center; gap: 0.5rem;"><i class="fas fa-clock"></i> Waiting for Customer to Sign</div>
                <button type="button" class="btn-footer-action" onclick="window.confirmRejectBooking(${data.id})" style="background: white; color: #e11d48; border: 1px solid #fecdd3; font-weight: 600;"><i class="fas fa-times-circle"></i> Cancel Booking</button>
            `;
            
        } else if (data.status === 'pending_quotation') {
            actionsEl.innerHTML = `
                <div style="padding: 0.65rem 1rem; color: #b45309; background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; font-size: 0.85rem; font-weight: 600; flex: 1; display: flex; align-items: center; gap: 0.5rem;"><i class="fas fa-file-invoice-dollar"></i> Waiting for Customer Approval</div>
                <button type="button" class="btn-footer-action" onclick="window.confirmRejectBooking(${data.id})" style="background: white; color: #e11d48; border: 1px solid #fecdd3; font-weight: 600;"><i class="fas fa-times-circle"></i> Cancel Booking</button>
            `;
            
        } else if (data.status === 'draft') {
            actionsEl.innerHTML = `
                <button type="button" class="btn-footer-action" onclick="window.confirmRejectBooking(${data.id})" style="background: white; color: #e11d48; border: 1px solid #fecdd3; font-weight: 600;"><i class="fas fa-trash-alt"></i> Delete Draft</button>
            `;
            
        } else if (data.status === 'inquiry') {
            actionsEl.innerHTML = `
                <button type="button" class="btn-footer-action btn-status-confirm" onclick="window.openQuotationWorkspace(${data.id})"><i class="fas fa-file-invoice-dollar"></i> Prepare Quotation</button>
                <button type="button" class="btn-footer-action" onclick="window.openEditBookingModal()" style="background: white; color: #475569; border: 1px solid #cbd5e1; font-weight: 600;"><i class="fas fa-edit"></i> Edit Details</button>
            `;
            
        } else if (data.status === 'tentative') {
            actionsEl.innerHTML = `
                <div style="padding: 0.65rem 1rem; color: #b45309; background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; font-size: 0.85rem; font-weight: 600; flex: 1; display: flex; align-items: center; gap: 0.5rem;"><i class="fas fa-calendar-alt"></i> Tentative Reservation. Awaiting initial deposit.</div>
                <button type="button" class="btn-footer-action" onclick="window.confirmRejectBooking(${data.id})" style="background: white; color: #e11d48; border: 1px solid #fecdd3; font-weight: 600;"><i class="fas fa-times-circle"></i> Cancel Tentative</button>
            `;
            
        } else {
            // ─── CONSOLIDATED OPERATIONAL LIFECYCLE ───
            // Both Ala Carte (8 Steps) and Package (6 Steps) share these event milestones
            if (data.status === 'confirmed') {
                if (data.paymentStatus === 'balance_proof_submitted') {
                    actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-confirm pulse-update" onclick="window.confirmAcceptBooking(${data.id}, true)" style="margin-bottom:0.5rem;width:100%;"><i class="fas fa-check-double"></i> Verify Final Balance</button>`;
                }
                if (isRental) {
                    actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.openRentalReleaseModal(${data.id})"><i class="fas fa-camera"></i> Release Equipment</button>`;
                } else {
                    actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(${data.id}, 'preparing')"><i class="fas fa-utensils"></i> Start Preparation</button>`;
                }
            } else if (data.status === 'preparing') {
                if (data.venue === 'PICKUP') {
                    actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.validateAndProceed(' + data.id + ', \'ready_for_pickup\')"><i class="fas fa-shopping-bag"></i> Mark as Ready for Pickup</button>';
                } else {
                    if (isFoodOrder) {
                        actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'on_the_way\')"><i class="fas fa-truck"></i> Dispatch Order</button>';
                    } else {
                        actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.validateAndProceed(' + data.id + ', \'ready_for_delivery\')"><i class="fas fa-box"></i> Mark as Ready for Delivery</button>';
                    }
                }
            } else if (data.status === 'ready_for_pickup') {
                actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-complete" onclick="window.confirmCompleteBooking(' + data.id + ')"><i class="fas fa-flag-checkered"></i> Mark as Picked Up (Complete)</button>';
            } else if (data.status === 'released') {
                if (isRental) {
                    actionsEl.innerHTML = `<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.openRentalInspectionModal(${data.id})"><i class="fas fa-clipboard-check"></i> Inspect & Process Return</button>`;
                }
            } else if (data.status === 'ready_for_delivery') {
                actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'on_the_way\')"><i class="fas fa-truck"></i> Out for Delivery</button>';
            } else if (data.status === 'on_the_way') {
                if (isPackage) {
                    actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'arrived\')"><i class="fas fa-map-marker-alt"></i> Arrived at Location</button>';
                } else if (isFoodOrder) {
                    actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'arrived\')"><i class="fas fa-check-circle"></i> Mark as Delivered</button>';
                } else {
                    // Skip to Complete for Ala Carte (Services)
                    if (!isRental) {
                        actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-complete" onclick="window.confirmCompleteBooking(' + data.id + ')"><i class="fas fa-flag-checkered"></i> Mark as Delivered (Complete)</button>';
                    }
                }
            } else if (data.status === 'arrived') {
                if (isPackage) {
                    actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-confirm" onclick="window.updateBookingStage(' + data.id + ', \'setup_ongoing\')"><i class="fas fa-magic"></i> Setup & Serve</button>';
                } else if (isFoodOrder) {
                    actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-complete" onclick="window.confirmCompleteBooking(' + data.id + ')"><i class="fas fa-flag-checkered"></i> Mark Order Completed</button>';
                }
            } else if (data.status === 'setup_ongoing' || data.status === 'in_progress') {
                if (data.paymentStatus === 'paid' || data.amount === "₱0.00" || data.paymentPlan === 'full') {
                    const btnLabel = isPackage ? 'Mark as Completed' : 'Mark as Completed';
                    if (primaryActionEl) {
                        primaryActionEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-complete" onclick="window.confirmCompleteBooking(' + data.id + ')"><i class="fas fa-flag-checkered"></i> ' + btnLabel + '</button>';
                        primaryActionEl.style.display = 'block';
                    } else {
                        actionsEl.innerHTML = '<button type="button" class="btn-footer-action btn-status-complete" onclick="window.confirmCompleteBooking(' + data.id + ')"><i class="fas fa-flag-checkered"></i> ' + btnLabel + '</button>';
                    }
                } else {
                    if (data.paymentStatus === 'balance_proof_submitted') {
                        if (primaryActionEl) {
                            primaryActionEl.innerHTML = `<button type="button" class="btn-footer-action btn-status-confirm pulse-update" onclick="window.confirmAcceptBooking(${data.id}, true)" style="width:100%;"><i class="fas fa-check-double"></i> Verify Final Balance</button>`;
                            primaryActionEl.style.display = 'block';
                        }
                        actionsEl.innerHTML += `<button type="button" class="btn-footer-action btn-status-reject" onclick="window.requestNewProof(${data.id})" style="margin-top:0.5rem; width:100%;"><i class="fas fa-undo"></i> Request Correct Balance Proof</button>`;
                    } else {
                        if (primaryActionEl) {
                            primaryActionEl.innerHTML = `<button type="button" class="btn-footer-action" onclick="window.copyInvoiceLink(${data.id})" style="background: var(--primary-color); color: white; border: none; font-weight: 600;"><i class="fas fa-paper-plane"></i> Send Final Payment Request</button>`;
                            primaryActionEl.style.display = 'block';
                        }
                    }
                }
            } else if (data.status === 'completed' || data.status === 'cancelled') {
                const archiveLabel = isFoodOrder ? 'Archive Order' : (isPackage ? 'Archive Package Record' : 'Archive Booking');
                actionsEl.innerHTML = `<button type="button" class="btn-footer-action" style="background: white; color: #475569; border: 1px solid #cbd5e1; font-weight: 600;" onclick="window.confirmArchiveBooking(${data.id})"><i class="fas fa-archive"></i> ${archiveLabel}</button>`;
            }
        }
        
        // Contextual Quick Nav Actions based on Walk-in vs Online
        if (isWalkin) {
            actionsEl.innerHTML += `<button type="button" class="btn-sm-outline" onclick="switchBookingTab('details', document.querySelector('[data-tab=\\'details\\']'))" style="background:white; border:1px solid #cbd5e1; color:#475569; justify-content:flex-start; width:100%; margin-bottom: 6px; text-align: left;"><i class="fas fa-list-check" style="width:20px; text-align:center; color: var(--primary-color);"></i> View Services & Amounts</button>`;
            actionsEl.innerHTML += `<button type="button" class="btn-sm-outline" onclick="switchBookingTab('finance', document.querySelector('[data-tab=\\'finance\\']'))" style="background:white; border:1px solid #cbd5e1; color:#475569; justify-content:flex-start; width:100%; margin-bottom: 6px; text-align: left;"><i class="fas fa-receipt" style="width:20px; text-align:center; color: #16a34a;"></i> View Payment</button>`;
            if (['confirmed', 'preparing', 'ready_for_delivery', 'ready_for_pickup', 'on_the_way', 'arrived', 'setup_ongoing', 'in_progress'].includes(data.status)) {
                actionsEl.innerHTML += `<button type="button" class="btn-sm-outline" onclick="window.switchBookingTab('tasks', document.querySelector('.mtab-btn-pro[onclick*=\\'tasks\\']'))" style="background:white; border:1px solid #cbd5e1; color:#475569; justify-content:flex-start; width:100%; margin-bottom: 6px; text-align: left;"><i class="fas fa-tasks" style="width:20px; text-align:center; color: #0284c7;"></i> Open Preparation Checklist</button>`;
            }
            actionsEl.innerHTML += `<button type="button" class="btn-sm-outline" onclick="switchBookingTab('activity', document.querySelector('[data-tab=\\'activity\\']'))" style="background:white; border:1px solid #cbd5e1; color:#475569; justify-content:flex-start; width:100%; margin-bottom: 8px; text-align: left;"><i class="fas fa-history" style="width:20px; text-align:center; color: #64748b;"></i> View Activity</button>`;
        } else {
            actionsEl.innerHTML += `<button type="button" class="btn-sm-outline" onclick="switchBookingTab('details', document.querySelector('[data-tab=\\'details\\']'))" style="background:white; border:1px solid #cbd5e1; color:#475569; justify-content:flex-start; width:100%; margin-bottom: 6px; text-align: left;"><i class="fas fa-user-circle" style="width:20px; text-align:center; color: #7c3aed;"></i> View Customer Details</button>`;
            if (['inquiry', 'pending_quotation', 'awaiting_customer', 'awaiting_caterer'].includes(data.status)) {
                actionsEl.innerHTML += `<button type="button" class="btn-sm-outline" onclick="window.openQuotationWorkspace(${data.id})" style="background:white; border:1px solid #cbd5e1; color:#475569; justify-content:flex-start; width:100%; margin-bottom: 6px; text-align: left;"><i class="fas fa-file-invoice-dollar" style="width:20px; text-align:center; color: var(--primary-color);"></i> View Quotation</button>`;
            }
            actionsEl.innerHTML += `<button type="button" class="btn-sm-outline" onclick="switchBookingTab('finance', document.querySelector('[data-tab=\\'finance\\']'))" style="background:white; border:1px solid #cbd5e1; color:#475569; justify-content:flex-start; width:100%; margin-bottom: 6px; text-align: left;"><i class="fas fa-receipt" style="width:20px; text-align:center; color: #16a34a;"></i> View Payment</button>`;
            if (['confirmed', 'preparing', 'ready_for_delivery', 'ready_for_pickup', 'on_the_way', 'arrived', 'setup_ongoing', 'in_progress'].includes(data.status)) {
                actionsEl.innerHTML += `<button type="button" class="btn-sm-outline" onclick="window.switchBookingTab('tasks', document.querySelector('.mtab-btn-pro[onclick*=\\'tasks\\']'))" style="background:white; border:1px solid #cbd5e1; color:#475569; justify-content:flex-start; width:100%; margin-bottom: 6px; text-align: left;"><i class="fas fa-tasks" style="width:20px; text-align:center; color: #0284c7;"></i> Open Preparation Checklist</button>`;
            }
            actionsEl.innerHTML += `<button type="button" class="btn-sm-outline" onclick="switchBookingTab('activity', document.querySelector('[data-tab=\\'activity\\']'))" style="background:white; border:1px solid #cbd5e1; color:#475569; justify-content:flex-start; width:100%; margin-bottom: 8px; text-align: left;"><i class="fas fa-history" style="width:20px; text-align:center; color: #64748b;"></i> View Activity</button>`;
        }

        // Add Copy Payment Link Button (useful for sending to FB Walk-in customers)
        const noLinkStatuses = ['draft', 'inquiry', 'tentative', 'pending_quotation', 'awaiting_caterer', 'awaiting_customer', 'pending', 'cancelled', 'completed', 'expired'];
        if (!noLinkStatuses.includes(data.status) && data.paymentStatus !== 'paid' && data.paymentStatus !== 'expired' && data.amount !== "₱0.00") {
            actionsEl.innerHTML += `
                <button type="button" class="btn-footer-action" onclick="window.copyInvoiceLink(${data.id})" style="background: white; color: #475569; border: 1px solid #cbd5e1; font-weight: 600;">
                    <i class="fas fa-link"></i> Copy Payment Link
                </button>
            `;
        }

        const oldWrapper = document.getElementById('actionCenterWrapper');
        const hasActions = actionsEl.innerHTML.trim() !== '';
        if (oldWrapper) {
            oldWrapper.style.display = 'none'; // Ensure old desktop wrapper is hidden on new UI
        }
        
        // Reset Mobile Sticky Footer Actions
        const actionCard = document.getElementById('actionCardSticky');
        const actionIcon = document.getElementById('mobileActionToggleIcon');
        const actionText = document.getElementById('mobileActionToggleText');
        const isMobile = window.innerWidth <= 768;
        
        if (actionCard) {
            actionCard.style.display = hasActions ? 'block' : 'none';
            if (hasActions) {
                if (isMobile) {
                    // Start collapsed on mobile so content isn't blocked
                    actionCard.classList.add('collapsed');
                    if (actionIcon) actionIcon.className = 'fas fa-chevron-up';
                    if (actionText) actionText.innerText = 'Show Actions';
                } else {
                    actionCard.classList.remove('collapsed');
                    if (actionIcon) actionIcon.className = 'fas fa-chevron-down';
                    if (actionText) actionText.innerText = 'Hide Actions';
                }
            }
        }
    }

    const bookedOnEl = document.getElementById('modalBookedOn');
    if (bookedOnEl) bookedOnEl.innerText = data.bookedOn || 'Not available';
    const headerSummary = document.getElementById('modalHeaderSummary');
    if (headerSummary) {
        const eventDateLabel = data.eventDate ? new Date(data.eventDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Date not set';
        const bookingTypeLabel = isWalkin ? 'Walk-in Booking' : 'Online Booking';
        headerSummary.innerHTML = [
            `<span><i class="fas fa-user"></i>${data.customer || 'Customer not set'}</span>`,
            `<span><i class="fas fa-calendar-day"></i>${data.eventType || 'Event not set'} · ${eventDateLabel}</span>`,
            `<span><i class="fas fa-users"></i>${data.guestCount || 0} guests</span>`,
            `<span><i class="fas ${isWalkin ? 'fa-store' : 'fa-globe'}"></i>${bookingTypeLabel}</span>`
        ].join('');
    }
    const displayPaymentPlan = (isFoodOrder || data.paymentPlan === 'full') ? 'FULL PAYMENT' : (data.paymentPlan || 'downpayment').toUpperCase();
    const paymentMethodEl = document.getElementById('modalPaymentMethod');
    if (paymentMethodEl) {
        paymentMethodEl.innerText = `${data.paymentMethod} (${displayPaymentPlan})`;
    }
    const payRefEl = document.getElementById('modalPaymentRef');
    if (payRefEl) {
        if (data.paymentRef && data.paymentRef.trim() !== '') {
            payRefEl.innerText = `Ref: ${data.paymentRef}`;
            payRefEl.style.display = 'inline-block';
        } else {
            payRefEl.style.display = 'none';
        }
    }
    
    document.getElementById('modalTotalAmount').innerText = data.amount;
    var totalElMobile = document.getElementById('modalTotalAmountMobile');
    if (totalElMobile) totalElMobile.innerText = data.amount;
    
    // Overview Cards logic
    let totalRaw = Math.max(parseFloat(data.totalRawAmount) || 0, 0);
    let paidRaw = Math.max(parseFloat(data.amountPaid) || 0, 0);
    if (data.paymentStatus === 'paid' || data.paymentStatus === 'fully_paid') {
        paidRaw = Math.max(paidRaw, totalRaw);
    }
    paidRaw = Math.min(paidRaw, totalRaw);
    let balanceRaw = Math.max(totalRaw - paidRaw, 0);
    const formatMoney = (val) => '₱' + val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    
    // Populate Compact Header Summary
    const custName = data.customer || 'Customer not set';
    const eventTypeStr = data.eventType || 'Event';
    const eventDateStr = data.eventDate ? new Date(data.eventDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Date not set';
    const eventTimeStr = data.eventTime || 'TBA';
    const guestPaxStr = (data.guestCount || 0) + ' pax';
    const venueStr = data.venue || 'TBA';

    const hsCust = document.getElementById('headerSummaryCustomer'); if (hsCust) hsCust.innerText = custName;
    const hsEvent = document.getElementById('headerSummaryEventType'); if (hsEvent) hsEvent.innerText = eventTypeStr;
    const hsDate = document.getElementById('headerSummaryDate'); if (hsDate) hsDate.innerText = eventDateStr;
    const hsTime = document.getElementById('headerSummaryTime'); if (hsTime) hsTime.innerText = eventTimeStr;
    const hsPax = document.getElementById('headerSummaryPax'); if (hsPax) hsPax.innerText = guestPaxStr;
    const hsVenue = document.getElementById('headerSummaryVenue'); if (hsVenue) hsVenue.innerText = venueStr;

    // Populate Source Badge in Header & Badges
    const srcBadge = document.getElementById('modalBookingSourceBadge');
    const srcIcon = document.getElementById('modalBookingSourceIcon');
    const srcText = document.getElementById('modalBookingSource');
    if (srcBadge) {
        if (isWalkin) {
            srcBadge.style.background = '#ffedd5'; srcBadge.style.color = '#c2410c'; srcBadge.style.borderColor = '#fed7aa';
            if (srcIcon) srcIcon.className = 'fas fa-store';
            if (srcText) srcText.innerText = 'WALK-IN';
        } else {
            srcBadge.style.background = '#f3e8ff'; srcBadge.style.color = '#7e22ce'; srcBadge.style.borderColor = '#e9d5ff';
            if (srcIcon) srcIcon.className = 'fas fa-globe';
            if (srcText) srcText.innerText = 'ONLINE';
        }
    }

    // Populate Overview Tab Cards
    const ovEvType = document.getElementById('ovEventType'); if (ovEvType) ovEvType.innerText = eventTypeStr;
    const ovEvDate = document.getElementById('ovEventDate'); if (ovEvDate) ovEvDate.innerText = eventDateStr;
    const ovEvTime = document.getElementById('ovEventTime'); if (ovEvTime) ovEvTime.innerText = eventTimeStr;
    const ovEvPax = document.getElementById('ovGuestCount'); if (ovEvPax) ovEvPax.innerText = guestPaxStr;
    const ovEvVenue = document.getElementById('ovVenue'); if (ovEvVenue) ovEvVenue.innerText = venueStr;
    const ovEvMotif = document.getElementById('ovMotif'); if (ovEvMotif) ovEvMotif.innerText = data.requests || 'Not specified';

    const ovBkRef = document.getElementById('ovBookingRef'); if (ovBkRef) ovBkRef.innerText = '#' + (data.bookingRef || ('BK-' + String(data.id).padStart(6, '0')));
    const ovSrcBadge = document.getElementById('ovSourceBadge'); if (ovSrcBadge) ovSrcBadge.innerText = isWalkin ? 'WALK-IN' : 'ONLINE';
    const ovCreated = document.getElementById('ovCreatedDate'); if (ovCreated) ovCreated.innerText = data.bookedOn || '—';
    const ovStatus = document.getElementById('ovStatusText'); if (ovStatus) ovStatus.innerText = (data.status || 'Confirmed').toUpperCase();

    const ovTot = document.getElementById('ovTotalDisplay'); if (ovTot) ovTot.innerText = formatMoney(totalRaw);
    const ovPaid = document.getElementById('ovPaidDisplay'); if (ovPaid) ovPaid.innerText = formatMoney(paidRaw);
    const ovBal = document.getElementById('ovBalanceDisplay'); if (ovBal) ovBal.innerText = formatMoney(balanceRaw);

    // Populate Customer Tab
    const cName = document.getElementById('custFullName'); if (cName) cName.innerText = custName;
    const cMobile = document.getElementById('custMobile'); if (cMobile) cMobile.innerText = data.contact || 'No contact provided';
    const cEmail = document.getElementById('custEmail'); if (cEmail) cEmail.innerText = data.email || 'No email provided';
    const cType = document.getElementById('custType'); if (cType) cType.innerText = isWalkin ? 'Walk-in Customer' : 'Online Registered Customer';
    const cNote = document.getElementById('custSourceNote');
    if (cNote) {
        if (isWalkin) {
            cNote.innerText = 'WALK-IN ENTRY'; cNote.style.background = '#ffedd5'; cNote.style.color = '#c2410c';
        } else {
            cNote.innerText = 'ONLINE RESERVATION'; cNote.style.background = '#f3e8ff'; cNote.style.color = '#7e22ce';
        }
    }
    const btnCall = document.getElementById('btnCallCustomer');
    if (btnCall) {
        if (data.contact) { btnCall.href = 'tel:' + data.contact; btnCall.style.display = 'inline-flex'; }
        else { btnCall.style.display = 'none'; }
    }
    const btnEmail = document.getElementById('btnEmailCustomer');
    if (btnEmail) {
        if (data.email) { btnEmail.href = 'mailto:' + data.email; btnEmail.style.display = 'inline-flex'; }
        else { btnEmail.style.display = 'none'; }
    }

    // Populate Order & Package Tab
    const oPkgName = document.getElementById('orderPkgName'); if (oPkgName) oPkgName.innerText = data.specificName || 'Catering Package';
    const oPkgMeta = document.getElementById('orderPkgMeta'); if (oPkgMeta) oPkgMeta.innerText = (data.guestCount || 0) + ' pax · ' + (data.eventType || 'Event');
    const oPkgPrice = document.getElementById('orderPkgPrice'); if (oPkgPrice) oPkgPrice.innerText = formatMoney(totalRaw);

    // Populate Payment Tab
    const pTot = document.getElementById('payTotalAmount'); if (pTot) pTot.innerText = formatMoney(totalRaw);
    const pPaid = document.getElementById('payTotalPaid'); if (pPaid) pPaid.innerText = formatMoney(paidRaw);
    const pBal = document.getElementById('payBalance'); if (pBal) pBal.innerText = formatMoney(balanceRaw);
    const pTabBadge = document.getElementById('paymentTabBadge');
    if (pTabBadge) {
        const pStatus = data.paymentStatus || 'unpaid';
        pTabBadge.innerText = pStatus.replace(/_/g, ' ').toUpperCase();
        if (pStatus === 'paid' || pStatus === 'fully_paid') {
            pTabBadge.style.background = '#dcfce7'; pTabBadge.style.color = '#15803d';
        } else {
            pTabBadge.style.background = '#fff7ed'; pTabBadge.style.color = '#c2410c';
        }
    }

    // Populate Footer Actions Button Visibility
    const btnCopyLink = document.getElementById('btnFooterCopyPaymentLink');
    if (btnCopyLink) {
        if (!isWalkin && data.paymentStatus !== 'paid' && totalRaw > 0) {
            btnCopyLink.style.display = 'inline-flex';
        } else {
            btnCopyLink.style.display = 'none';
        }
    }

    let dtTotal = document.getElementById('modalTotalAmount');
    let dtPaid = document.getElementById('headerPaidAmount');
    let dtBalance = document.getElementById('headerBalanceAmount');
    
    let moTotal = document.getElementById('modalTotalAmountMobile');
    let moPaid = document.getElementById('headerPaidAmountMobile');
    let moBalance = document.getElementById('headerBalanceAmountMobile');

    const quotationPending = ['inquiry', 'draft'].includes(data.status) && totalRaw <= 0;
    const financialLabel = document.getElementById('modalFinancialLabel');
    if (financialLabel) financialLabel.innerText = quotationPending ? 'Quotation' : 'Total';
    if (dtTotal) dtTotal.innerText = quotationPending ? 'Not quoted yet' : formatMoney(totalRaw);
    if (moTotal) moTotal.innerText = quotationPending ? 'Not quoted yet' : formatMoney(totalRaw);

    if (data.status === 'inquiry' || data.status === 'draft') {
        if (dtPaid) dtPaid.innerHTML = '₱0.00 paid';
        if (dtBalance) dtBalance.innerHTML = '<span style="color:#94a3b8;">Not Applicable</span>';
        if (moPaid) moPaid.innerHTML = '₱0.00 paid';
        if (moBalance) moBalance.innerHTML = '<span style="color:#94a3b8;">N/A</span>';
    } else {
        if (dtPaid) dtPaid.innerHTML = formatMoney(paidRaw) + ' paid';
        if (dtBalance) dtBalance.innerHTML = formatMoney(balanceRaw) + ' balance';
        if (moPaid) moPaid.innerHTML = formatMoney(paidRaw) + ' paid';
        if (moBalance) moBalance.innerHTML = formatMoney(balanceRaw) + ' balance';
    }

    const financeTotal = document.getElementById('financeTotalAmount');
    const financePaid = document.getElementById('financePaidAmount');
    const financeBalance = document.getElementById('financeBalanceAmount');
    const financeStatus = document.getElementById('financePaymentStatus');
    if (financeTotal) financeTotal.innerText = totalRaw > 0 ? formatMoney(totalRaw) : 'Not yet quoted';
    if (financePaid) financePaid.innerText = formatMoney(paidRaw);
    if (financeBalance) financeBalance.innerText = data.status === 'inquiry' || data.status === 'draft' ? 'Not applicable' : formatMoney(balanceRaw);
    if (financeStatus) {
        const financeLabels = { paid: 'Fully Paid', fully_paid: 'Fully Paid', deposit_paid: 'Downpayment Paid', proof_submitted: 'Proof Sent', balance_proof_submitted: 'Balance Proof Sent', pending: 'Payment Pending', unpaid: 'Unpaid', partial: 'Partial' };
        financeStatus.innerText = data.status === 'inquiry' || data.status === 'draft' ? 'Not applicable' : (financeLabels[data.paymentStatus] || (data.paymentStatus || 'Payment status unavailable').replace(/_/g, ' '));
    }

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
    var pStatusElText = document.getElementById('modalPaymentStatusText');
    var pStatusBadge = document.getElementById('modalPaymentStatusBadge');
    var pStatusMobile = document.getElementById('modalPaymentStatusMobile');
    
    var pLabels = { 
        'paid': 'Fully Paid', 
        'deposit_paid': 'Downpayment Paid', 
        'proof_submitted': 'Proof Sent', 
        'balance_proof_submitted': 'Balance Proof Sent', 
        'pending': 'Payment Pending',
        'reupload_requested': 'Re-upload Requested',
        'balance_reupload_requested': 'Balance Re-upload Requested',
        'expired': 'Overdue / Expired'
    };
    
    var paymentStatus = data.paymentStatus || 'pending';
    var labelText = pLabels[paymentStatus] || paymentStatus.replace(/_/g, ' ').toUpperCase();
    if (pStatusEl) pStatusEl.innerText = labelText;
    if (pStatusElText) pStatusElText.innerText = labelText;
    if (pStatusBadge) pStatusBadge.innerText = labelText;
    if (pStatusMobile) pStatusMobile.innerText = labelText;

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
    
    // Check if row has unread chat indicator and show badge on the Consultation Chat tab in modal
    const chatTabBtn = document.querySelector('.mtab-btn-pro[onclick*="\'chat\'"]');
    const rowEl = document.getElementById(`booking-row-${data.id}`);
    if (chatTabBtn) {
        const hasUnread = rowEl && rowEl.querySelector('span[title="Unread Consultation Messages"]');
        if (hasUnread) {
            chatTabBtn.innerHTML = `<i class="fas fa-comments"></i> Consultation Chat <span style="background: #3b82f6; color: white; font-size: 0.65rem; font-weight: 800; padding: 2px 6px; border-radius: 12px; margin-left: 6px;">New</span>`;
        } else {
            chatTabBtn.innerHTML = `<i class="fas fa-comments"></i> Consultation Chat`;
        }
    }
    
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

window.actionCenterMinimized = false;
window.toggleActionCenter = function(forceExpand) {
    const wrapper = document.getElementById('actionCenterWrapper');
    const actionsTop = document.getElementById('bookingModalActionsTop') || document.getElementById('bookingModalActions');
    const toggleText = document.getElementById('actionCenterToggleText');
    const toggleIcon = document.getElementById('actionCenterToggleIcon');
    const toggleBtn = document.getElementById('btnToggleActionCenter');
    const header = document.getElementById('actionCenterHeader');
    
    if (!wrapper || !actionsTop) return;

    if (typeof forceExpand === 'boolean') {
        window.actionCenterMinimized = !forceExpand;
    } else {
        window.actionCenterMinimized = !window.actionCenterMinimized;
    }

    if (window.actionCenterMinimized) {
        // Minimize (Collapse up/down)
        actionsTop.style.display = 'none';
        wrapper.style.padding = '0.65rem 2rem';
        if (header) header.style.marginBottom = '0';
        if (toggleText) toggleText.innerText = 'Expand Actions';
        if (toggleIcon) toggleIcon.className = 'fas fa-chevron-up';
        if (toggleBtn) {
            toggleBtn.style.background = 'var(--primary-color, #800000)';
            toggleBtn.style.color = '#ffffff';
            toggleBtn.style.borderColor = 'var(--primary-color, #800000)';
            toggleBtn.style.boxShadow = '0 2px 6px rgba(0,0,0,0.15)';
        }
    } else {
        // Expand (Show actions)
        actionsTop.style.display = 'flex';
        wrapper.style.padding = '1.25rem 2rem';
        if (header) header.style.marginBottom = '0.85rem';
        if (toggleText) toggleText.innerText = 'Minimize';
        if (toggleIcon) toggleIcon.className = 'fas fa-chevron-down';
        if (toggleBtn) {
            toggleBtn.style.background = '#f1f5f9';
            toggleBtn.style.color = '#475569';
            toggleBtn.style.borderColor = '#cbd5e1';
            toggleBtn.style.boxShadow = 'none';
        }
    }
};

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
    if (tabId === 'operations' && typeof currentBookingId !== 'undefined' && currentBookingId) {
        loadBookingTasks(currentBookingId);
    }
}

function configureBookingTabs(data, context) {
    const visibleTabs = {
        overview: true,
        customer: true,
        order: true,
        payment: true,
        preparation: true,
        activity: true
    };

    Object.entries(visibleTabs).forEach(([tabId, isVisible]) => {
        const button = document.querySelector(`#bookingDetailModal [data-tab="${tabId}"]`);
        const pane = document.getElementById(`btab-${tabId}`);
        if (button) button.style.display = isVisible ? 'inline-flex' : 'none';
    });

    const activeButton = document.querySelector('#bookingDetailModal .mtab-btn-pro.active');
    const activeTab = activeButton?.dataset.tab;
    if (!visibleTabs[activeTab]) {
        const fallback = Object.keys(visibleTabs).find(tabId => visibleTabs[tabId]);
        const fallbackButton = document.querySelector(`#bookingDetailModal [data-tab="${fallback}"]`);
        switchBookingTab(fallback, fallbackButton);
    }
}

window.openQuotationWorkspace = function(bookingId) {
    window.location.href = `/caterer/bookings/${bookingId}/quotation`;
};

function renderOverviewWorkspace(data, context) {
    const status = data.status || '';
    const total = Math.max(parseFloat(data.totalRawAmount) || 0, 0);
    const missing = [];
    const openEdit = 'window.openEditBookingModal()';
    const addAttention = (label, actionLabel = 'Edit details') => missing.push(`<div class="workspace-attention-item"><span><i class="fas fa-exclamation-circle"></i> ${label}</span><button type="button" onclick="${openEdit}">${actionLabel}</button></div>`);

    if (!data.venue || data.venue === 'Not specified') addAttention('Venue not specified', 'Add venue');
    if (!Number(data.guestCount)) addAttention('Guest count not set', 'Set guests');
    if (!data.eventDate) addAttention('Event date not set', 'Set date');
    if (status === 'inquiry' && total <= 0) addAttention('Quotation not prepared', 'Prepare quote');

    const attention = document.getElementById('overviewAttention');
    if (attention) attention.innerHTML = missing.length ? missing.join('') : '<div class="workspace-attention-ok"><i class="fas fa-check-circle"></i> Booking information is complete.</div>';

    const eventDate = data.eventDate ? new Date(data.eventDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Not set';
    const paid = Math.max(parseFloat(data.amountPaid) || 0, 0);
    const balance = Math.max(total - paid, 0);
    const summary = document.getElementById('overviewSummary');
    if (summary) {
        const packageName = data.specificName && data.specificName !== data.eventType ? data.specificName : (data.eventType || 'Not selected');
        const sourceLabel = context.isWalkin ? 'Walk-in Booking' : 'Online Booking';
        const createdByLabel = context.isWalkin ? 'Caterer / Staff' : 'Customer';
        summary.innerHTML = [
            ['Customer', data.customer || 'Not set'],
            ['Booking Source', sourceLabel],
            ['Created By', createdByLabel],
            ['Event Type', data.eventType || 'Not set'],
            ['Event Date', eventDate],
            ['Number of Guests', Number(data.guestCount) ? `${data.guestCount} guests` : 'Not set'],
            ['Venue', data.venue || 'Not specified'],
            ['Services / Package', packageName],
            ['Total', '₱' + total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })],
            ['Paid', '₱' + paid.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })],
            ['Balance', '₱' + balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })]
        ].map(([label, value]) => `<div class="workspace-summary-item"><span>${label}</span><strong>${value}</strong></div>`).join('');
    }

    // Dynamic Source + Status primary action matrix
    let primaryTitle = 'Booking requires review.';
    let primaryDesc = 'Review the booking details and choose the next available action.';
    let primaryBtnText = 'Review Details';
    let primaryBtnAction = `switchBookingTab('details', document.querySelector('[data-tab="details"]'))`;
    let primaryEyebrow = context.isWalkin ? 'Walk-in Booking Action' : 'Customer Booking Action';

    if (context.isWalkin) {
        if (status === 'draft') {
            primaryTitle = 'Draft Walk-in Booking.';
            primaryDesc = 'Complete the required customer and service details for this walk-in booking.';
            primaryBtnText = 'Complete Booking';
            primaryBtnAction = 'window.openEditBookingModal()';
        } else if (status === 'pending') {
            primaryTitle = 'WALK-IN BOOKING: Review & Confirm';
            primaryDesc = 'This booking was manually created. Verify the customer, event details, and service amounts before confirming.';
            primaryBtnText = 'Review & Confirm';
            primaryBtnAction = `window.confirmAcceptBooking(${data.id}, false, false, ${data.isPackage === 'true'})`;
        } else if (status === 'confirmed') {
            primaryTitle = 'WALK-IN BOOKING: Ready for Preparation';
            primaryDesc = 'This booking was manually created by the caterer. Verify the customer, event details, selected services, and amounts before proceeding with preparation.';
            primaryBtnText = 'Start Preparation';
            primaryBtnAction = `window.updateBookingStage(${data.id}, 'preparing')`;
        } else if (status === 'preparing') {
            primaryTitle = 'WALK-IN BOOKING: Preparation Ongoing';
            primaryDesc = 'Preparation is currently in progress. Continue monitoring the preparation checklist and prepare requirements.';
            primaryBtnText = 'Open Preparation Checklist';
            primaryBtnAction = `window.switchBookingTab('tasks', document.querySelector('.mtab-btn-pro[onclick*="tasks"]'))`;
        } else if (status === 'ready_for_delivery') {
            primaryTitle = 'Walk-in Booking: Ready for Delivery.';
            primaryDesc = 'Event items are prepared. Start delivery when team is dispatching.';
            primaryBtnText = 'Out for Delivery';
            primaryBtnAction = `window.updateBookingStage(${data.id}, 'on_the_way')`;
        } else if (status === 'ready_for_pickup') {
            primaryTitle = 'Walk-in Booking: Ready for Pickup.';
            primaryDesc = 'Items are ready. Complete the booking after the customer collects them.';
            primaryBtnText = 'Mark Picked Up';
            primaryBtnAction = `window.confirmCompleteBooking(${data.id})`;
        } else if (status === 'on_the_way') {
            primaryTitle = 'Walk-in Booking: In Transit.';
            primaryDesc = 'The delivery team is on the way to the venue.';
            primaryBtnText = 'Mark Arrived';
            primaryBtnAction = `window.updateBookingStage(${data.id}, 'arrived')`;
        } else if (status === 'arrived') {
            primaryTitle = 'Walk-in Booking: Arrived at Venue.';
            primaryDesc = 'Team has arrived. Proceed with setup and serving.';
            primaryBtnText = context.isFoodOrder ? 'Mark Completed' : 'Start Setup';
            primaryBtnAction = context.isFoodOrder ? `window.confirmCompleteBooking(${data.id})` : `window.updateBookingStage(${data.id}, 'setup_ongoing')`;
        } else if (status === 'setup_ongoing' || status === 'in_progress') {
            primaryTitle = 'Walk-in Booking: Event in Progress.';
            primaryDesc = 'Service is ongoing. Mark completed when all services are concluded.';
            primaryBtnText = 'Mark Completed';
            primaryBtnAction = `window.confirmCompleteBooking(${data.id})`;
        } else if (status === 'completed') {
            primaryTitle = 'Walk-in Booking Completed.';
            primaryDesc = 'This walk-in booking is completed. All services have been fulfilled.';
            primaryBtnText = '';
            primaryBtnAction = '';
        } else if (status === 'cancelled') {
            primaryTitle = 'Walk-in Booking Cancelled.';
            primaryDesc = 'This walk-in booking has been cancelled and closed.';
            primaryBtnText = '';
            primaryBtnAction = '';
        }
    } else {
        // Online Customer Booking
        if (status === 'inquiry') {
            primaryTitle = 'Customer submitted booking inquiry.';
            primaryDesc = 'The customer is waiting for a quotation before confirming.';
            primaryBtnText = 'Prepare Quotation';
            primaryBtnAction = `window.openQuotationWorkspace(${data.id})`;
        } else if (status === 'pending_quotation') {
            primaryTitle = 'Quotation sent to customer.';
            primaryDesc = 'Quotation is awaiting customer approval. Send reminder if needed.';
            primaryBtnText = 'View Quotation';
            primaryBtnAction = `window.location.href='/caterer/bookings/${data.id}/quotation'`;
        } else if (status === 'awaiting_caterer') {
            primaryTitle = 'Customer accepted quotation.';
            primaryDesc = 'Review customer confirmation and sign service contract.';
            primaryBtnText = 'Sign Contract';
            primaryBtnAction = `window.openIframeModal('/caterer/bookings/${data.id}/sign?modal=true', 'Sign Service Agreement')`;
        } else if (status === 'awaiting_customer') {
            primaryTitle = 'Customer action is pending.';
            primaryDesc = 'Waiting for customer signature or confirmation.';
            primaryBtnText = 'Send Reminder';
            primaryBtnAction = `window.sendPaymentReminder(${data.id})`;
        } else if (status === 'pending') {
            if (data.paymentStatus === 'proof_submitted') {
                primaryTitle = 'Customer submitted payment proof.';
                primaryDesc = 'Verify payment proof and confirm customer booking.';
                primaryBtnText = 'Verify & Accept';
                primaryBtnAction = `window.confirmAcceptBooking(${data.id}, true, false, ${data.isPackage === 'true'})`;
            } else {
                primaryTitle = 'Customer submitted booking request.';
                primaryDesc = 'Review customer booking details and verify payment status.';
                primaryBtnText = 'Review Booking';
                primaryBtnAction = `switchBookingTab('details', document.querySelector('[data-tab="details"]'))`;
            }
        } else if (status === 'confirmed') {
            primaryTitle = 'CUSTOMER BOOKING: Confirmed & Ready';
            primaryDesc = 'This customer booking is confirmed and ready for preparation. Review event requirements before starting preparation.';
            primaryBtnText = 'Start Preparation';
            primaryBtnAction = `window.updateBookingStage(${data.id}, 'preparing')`;
        } else if (status === 'preparing') {
            primaryTitle = 'CUSTOMER BOOKING: Preparation in Progress';
            primaryDesc = 'Preparation is ongoing. Monitor the preparation checklist and prepare food/services.';
            primaryBtnText = 'Open Preparation Checklist';
            primaryBtnAction = `window.switchBookingTab('tasks', document.querySelector('.mtab-btn-pro[onclick*="tasks"]'))`;
        } else if (status === 'ready_for_delivery') {
            primaryTitle = 'Booking ready for delivery.';
            primaryDesc = 'Event items are prepared. Dispatch when ready.';
            primaryBtnText = 'Out for Delivery';
            primaryBtnAction = `window.updateBookingStage(${data.id}, 'on_the_way')`;
        } else if (status === 'ready_for_pickup') {
            primaryTitle = 'Order ready for pickup.';
            primaryDesc = 'Customer will collect the items at the premises.';
            primaryBtnText = 'Mark Picked Up';
            primaryBtnAction = `window.confirmCompleteBooking(${data.id})`;
        } else if (status === 'on_the_way') {
            primaryTitle = 'Booking in transit.';
            primaryDesc = 'Delivery team is en route to customer venue.';
            primaryBtnText = 'Mark Arrived';
            primaryBtnAction = `window.updateBookingStage(${data.id}, 'arrived')`;
        } else if (status === 'arrived') {
            primaryTitle = 'Team arrived at venue.';
            primaryDesc = 'Setup catering equipment, service stations, and food.';
            primaryBtnText = context.isFoodOrder ? 'Mark Completed' : 'Start Setup';
            primaryBtnAction = context.isFoodOrder ? `window.confirmCompleteBooking(${data.id})` : `window.updateBookingStage(${data.id}, 'setup_ongoing')`;
        } else if (status === 'setup_ongoing' || status === 'in_progress') {
            primaryTitle = 'Event service in progress.';
            primaryDesc = 'Event is underway. Mark completed when finished.';
            primaryBtnText = 'Mark Completed';
            primaryBtnAction = `window.confirmCompleteBooking(${data.id})`;
        } else if (status === 'completed') {
            primaryTitle = 'Customer booking completed.';
            primaryDesc = 'Event successfully completed. Record closed for audit.';
            primaryBtnText = '';
            primaryBtnAction = '';
        } else if (status === 'cancelled') {
            primaryTitle = 'Booking cancelled.';
            primaryDesc = 'This booking was cancelled.';
            primaryBtnText = '';
            primaryBtnAction = '';
        }
    }

    const title = document.getElementById('overviewNextActionTitle');
    const description = document.getElementById('overviewNextActionDescription');
    const button = document.getElementById('overviewNextActionButton');
    const eyebrowEl = document.querySelector('#overviewNextAction .workspace-eyebrow');
    if (eyebrowEl) eyebrowEl.innerHTML = `<i class="fas ${context.isWalkin ? 'fa-store' : 'fa-globe'}"></i> ${primaryEyebrow}`;
    if (title) title.innerText = primaryTitle;
    if (description) description.innerText = primaryDesc;
    if (button) button.innerHTML = primaryBtnText ? `<button type="button" onclick="${primaryBtnAction}"><i class="fas fa-arrow-right"></i> ${primaryBtnText}</button>` : '';

    const lifecycle = document.getElementById('overviewLifecycle');
    const early = ['inquiry', 'pending_quotation', 'awaiting_customer'];
    const stages = early.includes(status) ? ['Inquiry', 'Quotation', 'Customer decision', 'Confirmed'] : ['Confirmed', 'Preparing', 'Setup', 'Ongoing', 'Completed'];
    const stageKeys = early.includes(status) ? ['inquiry', 'pending_quotation', 'awaiting_customer', 'confirmed'] : ['confirmed', 'preparing', 'setup_ongoing', 'in_progress', 'completed'];
    let currentIndex = stageKeys.indexOf(status);
    if (currentIndex < 0 && ['ready_for_delivery', 'ready_for_pickup', 'on_the_way', 'arrived'].includes(status)) currentIndex = 1;
    if (currentIndex < 0 && status === 'cancelled') currentIndex = 0;
    if (lifecycle) lifecycle.innerHTML = stages.map((stage, index) => `<div class="workspace-lifecycle-step ${index < currentIndex ? 'done' : ''} ${index === currentIndex ? 'current' : ''}"><span class="dot"></span>${stage}</div>`).join('');
}

function resetBookingTabs() {
    document.querySelectorAll('.mtab-pane-pro').forEach(function(p) { p.classList.remove('active'); });
    document.querySelectorAll('.mtab-btn-pro').forEach(function(b) { 
        b.style.display = 'flex';
        b.classList.remove('active');
        b.style.borderBottomColor = 'transparent';
        b.style.color = '#64748b';
    });
    document.querySelectorAll('.mtab-pane-pro').forEach(function(p) { p.style.display = ''; });
    var ovTab = document.getElementById('btab-overview') || document.getElementById('btab-summary');
    if (ovTab) ovTab.classList.add('active');
    var firstBtn = document.querySelector('.mtab-btn-pro');
    if (firstBtn) {
        firstBtn.classList.add('active');
        firstBtn.style.borderBottomColor = 'var(--primary-color)';
        firstBtn.style.color = 'var(--primary-color)';
    }
}

// Global copy payment link function
window.copyInvoiceLink = function(bookingId) {
    const url = window.location.origin + '/customer/booking/' + bookingId + '/invoice';
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(() => {
            if (window.showSuccess) window.showSuccess('Payment link copied to clipboard!');
            else alert('Payment link copied to clipboard!');
        }).catch(err => {
            alert('Failed to copy: ' + url);
        });
    } else {
        const el = document.createElement('textarea');
        el.value = url;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        if (window.showSuccess) window.showSuccess('Payment link copied to clipboard!');
        else alert('Payment link copied to clipboard!');
    }

};

// ─── NEW: AUDIT HISTORY ──────────────────────────────────────────────────────

async function loadBookingHistory(bookingId) {
    const container = document.getElementById('modalHistoryTimeline');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;padding:2rem;color:#94a3b8;">Loading activity...</div>';
    
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
                        <div class="timeline-note-pro">
                            ${item.notes || 'Status changed automatically.'}
                            <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px; font-weight: 600;">
                                <i class="fas ${item.actor === 'Customer' ? 'fa-user' : 'fa-user-tie'}" style="margin-right: 4px; color: ${item.actor === 'Customer' ? '#7c3aed' : '#c2410c'};"></i>
                                ${item.status === 'created' ? 'Created by:' : 'Updated by:'} <strong>${item.actor || 'System'}</strong>
                            </div>
                        </div>
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
        const data = await window.apiAction(`/caterer/api/bookings/${currentBookingId}/notes`, {
            method: 'POST',
            body: JSON.stringify({ notes: notes })
        });
        
        if (data && data.status === 'success') {
            // Update the data attribute on the view button to persist change
            const viewBtn = document.querySelector(`.view-details[data-id="${currentBookingId}"]`);
            if (viewBtn) viewBtn.dataset.catererNotes = notes;
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}

// ─── NEW: STEPPER LOGIC ──────────────────────────────────────────────────────

function updateBookingStepper(status, isPackage, isFoodOrder) {
    const stepper = document.querySelector('.booking-stepper-pro');
    const preOperationalStatuses = ['inquiry', 'draft', 'pending_review', 'pending_quotation', 'awaiting_caterer', 'awaiting_customer', 'tentative'];
    if (stepper) {
        stepper.style.display = preOperationalStatuses.includes(status) ? 'none' : '';
    }
    if (preOperationalStatuses.includes(status)) return;

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
    if (!newDate) { window.showToast('Please select a valid date.', 'error'); return; }
    var todayStr = new Date().toISOString().split('T')[0];
    if (newDate < todayStr) { window.showToast('Deadline cannot be set in the past.', 'error'); return; }
    if (currentEventDate && newDate > currentEventDate) { window.showToast('Deadline cannot be after the event date. It must be settled before or on the event day.', 'error'); return; }
    
    const data = await window.apiAction('/caterer/api/bookings/' + currentBookingId + '/set-due-date', {
        method: 'POST',
        body: JSON.stringify({ due_date: newDate })
    });
    
    if (data && data.status === 'success') {
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
    }
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
    const isWalkinBooking = rowBtn ? (rowBtn.dataset.bookingSource === 'Walk-in' || !rowBtn.dataset.targetUserId || rowBtn.dataset.targetUserId === 'None') : false;
    
    if (!isVerified && isPackage && !isWalkinBooking) {
        window.showAlert({
            type: 'warning',
            title: 'Customer Not Verified',
            message: 'This customer has not yet been verified by the Admin. Are you sure you want to accept this booking?',
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
        window.showToast('Please provide a reason for the rejection.', 'error');
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
        const data = await window.apiAction(`/caterer/bookings/${rejectionBookingId}/reject`, {
            method: 'POST',
            body: JSON.stringify({ reason: reason })
        });
        
        if (data && data.status === 'success') {
            bk_closeModal('rejectReasonModal');
            bk_closeModal('bookingDetailModal');
            if (window.refreshBookingsTable) window.refreshBookingsTable();
        }
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
    
    // Status-dependent checklist titles and static tasks
    let status = window.currentBookingStatus || 'confirmed';
    let checklistTitle = 'Checklist';
    
    const staticChecklists = {
        'inquiry': {
            title: 'Inquiry Checklist',
            tasks: ['Customer details', 'Event details', 'Availability checked', 'Quoted Package', 'Follow-up sent']
        },
        'tentative': {
            title: 'Confirmation Checklist',
            tasks: ['Quote accepted', 'Contract signed', 'Deposit received', 'Hold expiration check']
        },
        'setup_ongoing': {
            title: 'Setup Checklist',
            tasks: ['Venue Arrival', 'Tables & Chairs', 'Equipment', 'Buffet Area', 'Food Setup']
        },
        'in_progress': {
            title: 'Event Monitoring',
            tasks: ['Event started', 'Issues monitored', 'Special requests handled', 'Completion confirmed']
        },
        'completed': {
            title: 'Post-Event',
            tasks: ['Final payment collected', 'Expenses recorded', 'Completion report', 'Customer feedback']
        },
        'cancelled': {
            title: 'Cancellation',
            tasks: ['Archived']
        }
    };

    const sectionTitleContainer = document.getElementById('modalChecklistSection');
    const titleEl = sectionTitleContainer ? sectionTitleContainer.previousElementSibling.querySelector('.exec-title') : null;

    if (staticChecklists[status]) {
        // Render static visual checklist
        const cl = staticChecklists[status];
        if (titleEl) titleEl.innerText = cl.title;
        
        let checkedCount = 0;
        let html = '';
        cl.tasks.forEach((t, i) => {
            let isChecked = false;
            // visually check everything for past/ongoing states, keep unchecked for tentative/inquiry
            if (status === 'completed' || status === 'setup_ongoing' || status === 'in_progress' || status === 'cancelled') isChecked = true;
            if (isChecked) checkedCount++;
            html += `
            <div class="task-item-pro ${isChecked ? 'completed' : ''}" style="cursor: default;">
                <div class="task-checkbox-pro">
                    ${isChecked ? '<i class="fas fa-check"></i>' : ''}
                </div>
                <div class="task-title" style="flex:1;">${t}</div>
            </div>`;
        });
        
        const progress = Math.round((checkedCount / cl.tasks.length) * 100);
        if (progressText) progressText.innerText = progress + '%';
        if (progressBar) progressBar.style.width = progress + '%';
        
        listContainer.innerHTML = html;
        return;
    }

    // Default to dynamic API tasks for Confirmed/Preparing
    if (titleEl) titleEl.innerText = (status === 'preparing') ? 'Preparation Checklist' : 'Pre-Event Checklist';
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
    
    const rawTitle = prompt("Enter task description (e.g., Finalize flower arrangements):");
    if (!rawTitle) return;
    const title = rawTitle.trim().replace(/<[^>]*>?/gm, '');
    if (title === "") {
        window.showError("Please enter a valid task description.");
        return;
    }
    if (title.length < 3) {
        window.showError("Task description is too short (min 3 characters).");
        return;
    }
    if (title.length > 120) {
        window.showError("Task description exceeds 120 characters.");
        return;
    }

    try {
        const res = await fetch(`/caterer/api/bookings/${currentBookingId}/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: title })
        });
        
        if (res.ok) {
            window.showSuccess("Custom task added successfully.");
            loadBookingTasks(currentBookingId);
        } else {
            window.showError('Failed to add task.');
        }
    } catch (err) {
        window.showError('Error adding task.');
    }
}

async function addBookingTaskFromInput() {
    if (!currentBookingId) return;
    const inputEl = document.getElementById('newTaskInput');
    if (!inputEl) return;
    const rawTitle = inputEl.value;
    if (!rawTitle || !rawTitle.trim()) {
        window.showError("Please enter a task description in the input field.");
        return;
    }
    const title = rawTitle.trim().replace(/<[^>]*>?/gm, '');
    if (title.length < 3) {
        window.showError("Task description is too short (min 3 characters).");
        return;
    }
    if (title.length > 120) {
        window.showError("Task description exceeds 120 characters.");
        return;
    }

    try {
        const res = await fetch(`/caterer/api/bookings/${currentBookingId}/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: title })
        });
        
        if (res.ok) {
            inputEl.value = '';
            window.showSuccess("Task added successfully.");
            loadBookingTasks(currentBookingId);
        } else {
            window.showError('Failed to add task.');
        }
    } catch (err) {
        window.showError('Error adding task.');
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
            // Remove unread chat badge from table row since messages are now read
            const rowEl = document.getElementById(`booking-row-${bookingId}`);
            if (rowEl) {
                const badge = rowEl.querySelector('span[title="Unread Consultation Messages"]');
                if (badge) badge.remove();
            }
            // Remove 'New' badge from chat tab button in modal
            const chatTabBtn = document.querySelector('.mtab-btn-pro[onclick*="\'chat\'"]');
            if (chatTabBtn) {
                const newBadge = chatTabBtn.querySelector('span');
                if (newBadge) newBadge.remove();
            }

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
                    
                    const seenStatusHtml = msg.is_me ? (msg.is_read ? '<span style="color: #3b82f6; font-weight: 700; margin-left: 6px;"><i class="fas fa-check-double"></i> Seen</span>' : '<span style="color: #94a3b8; margin-left: 6px;"><i class="fas fa-check"></i> Sent</span>') : '';

                    return `
                        <div style="display: flex; gap: 0.75rem; justify-content: ${justify};">
                            ${!msg.is_me ? icon : ''}
                            <div style="max-width: 80%;">
                                <div style="background: ${bg}; color: ${color}; padding: 0.75rem 1rem; border-radius: ${radius}; box-shadow: 0 2px 4px rgba(0,0,0,0.05); font-size: 0.85rem; line-height: 1.4;">
                                    ${msg.message ? msg.message : ''}
                                    ${attachmentHtml}
                                </div>
                                <div style="font-size: 0.65rem; color: var(--dm-slate-400); margin-top: 4px; text-align: ${msg.is_me ? 'right' : 'left'};">
                                    ${msg.created_at}${seenStatusHtml}
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
            
            if (!messageInput.value.trim() && !attachmentInput.files.length) {
                window.showError("Please enter a consultation message or attach a document before sending.");
                return;
            }
            if (attachmentInput.files.length > 0) {
                const file = attachmentInput.files[0];
                const maxSize = 10 * 1024 * 1024; // 10MB limit
                if (file.size > maxSize) {
                    window.showError("Attachment size exceeds the 10MB security limit. Please upload a smaller file.");
                    return;
                }
            }
            
            const originalBtn = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            btn.disabled = true;
            
            const formData = new FormData(chatForm);
            
            try {
                const res = await fetch(`/bookings/${bookingId}/messages`, {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
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

window.toggleMobileActions = function() {
    const card = document.getElementById('actionCardSticky');
    const icon = document.getElementById('mobileActionToggleIcon');
    const text = document.getElementById('mobileActionToggleText');
    
    if (card && icon && text) {
        if (card.classList.contains('collapsed')) {
            card.classList.remove('collapsed');
            icon.className = 'fas fa-chevron-down';
            text.innerText = 'Hide Actions';
        } else {
            card.classList.add('collapsed');
            icon.className = 'fas fa-chevron-up';
            text.innerText = 'Show Actions';
        }
    }
};

window.openIframeModal = function(url, title) {
    const modal = document.getElementById('iframeModal');
    if (!modal) return;
    
    document.getElementById('iframeModalTitle').innerText = title || 'View Document';
    document.getElementById('iframeModalLoading').style.display = 'flex';
    document.getElementById('iframeModalContent').src = url;
    
    modal.style.display = 'flex';
    setTimeout(() => modal.classList.add('active'), 10);
};


window.sendPaymentReminder = function(bookingId) {
    if (!bookingId) return;
    const url = window.location.origin + '/customer/booking/' + bookingId + '/invoice';
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(() => {
            if (window.showSuccess) window.showSuccess('Payment link copied to clipboard!');
            else alert('Payment link copied to clipboard!');
        }).catch(err => {
            alert('Failed to copy: ' + url);
        });
    } else {
        const el = document.createElement('textarea');
        el.value = url;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        if (window.showSuccess) window.showSuccess('Payment link copied to clipboard!');
        else alert('Payment link copied to clipboard!');
    }

};

window.recordOfflinePayment = function(bookingId) {
    if (!bookingId) return;
    window.openIframeModal('/caterer/bookings/' + bookingId + '/payments/offline', 'Record Offline Payment');
};

window.sendPaymentLink = function(bookingId) {
    window.sendPaymentReminder(bookingId);
};

document.addEventListener("DOMContentLoaded", function() {
    const urlParams = new URLSearchParams(window.location.search);
    const focusId = urlParams.get("focus") || urlParams.get("focus_id") || urlParams.get("booking_id");
    if (focusId) {
        setTimeout(() => {
            const btn = document.querySelector(`button.view-details[data-id="${focusId}"]`);
            if (btn) {
                btn.click();
            }
        }, 500);
    }
});



// ─── PHASE 2: EDIT BOOKING & PREPARATION ──────────────────────────────────────────

window.openEditBookingModal = function() {
    if (!currentBookingId) return;
    
    // Fetch current booking data
    fetch(`/caterer/api/bookings/${currentBookingId}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('editBookingId').value = data.id;
            document.getElementById('editBookingOriginalStatus').value = data.status;
            
            document.getElementById('editCustomerName').value = data.customerName || data.customer;
            document.getElementById('editEventDate').value = data.date;
            document.getElementById('editEventTime').value = data.time || '00:00';
            document.getElementById('editVenue').value = data.venue;
            document.getElementById('editGuestCount').value = data.guests;
            
            const reasonContainer = document.getElementById('editReasonContainer');
            const reasonInput = document.getElementById('editModificationReason');
            
            if (['confirmed', 'preparing', 'on_the_way', 'in_progress', 'ready_for_pickup', 'ready_for_delivery'].includes(data.status)) {
                reasonContainer.style.display = 'block';
                reasonInput.required = true;
            } else {
                reasonContainer.style.display = 'none';
                reasonInput.required = false;
                reasonInput.value = '';
            }
            
            window.openModal('editBookingModal');
        })
        .catch(err => alert("Error fetching booking details: " + err));
};

window.submitEditBooking = async function(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSubmitEdit');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    
    const id = document.getElementById('editBookingId').value;
    const data = {
        customer_name: document.getElementById('editCustomerName').value,
        event_date: document.getElementById('editEventDate').value,
        event_time: document.getElementById('editEventTime').value,
        venue_address: document.getElementById('editVenue').value,
        guest_count: document.getElementById('editGuestCount').value,
        reason: document.getElementById('editModificationReason').value
    };
    
    try {
        const res = await window.apiAction(`/caterer/api/bookings/${id}/edit`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (res) {
            window.closeModal('editBookingModal');
            if (window.showSuccess) window.showSuccess('Booking updated successfully.');
            // Refresh modal
            window.openBookingDetailModal(id);
        }
    } catch(err) {
        alert("Error saving booking: " + err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Save Changes';
    }
};

window.setPreparationDate = async function(bookingId) {
    const dateInput = document.getElementById(`prepDateInput_${bookingId}`);
    if (!dateInput || !dateInput.value) {
        alert("Please select a preparation date first.");
        return;
    }
    
    try {
        const res = await window.apiAction(`/caterer/api/bookings/${bookingId}/prep-date`, {
            method: 'POST',
            body: JSON.stringify({ preparation_date: dateInput.value })
        });
        if (res) {
            if (window.showSuccess) window.showSuccess('Preparation lead time scheduled.');
            window.openBookingDetailModal(bookingId);
        }
    } catch(err) {
        alert("Error setting prep date: " + err);
    }
};


// ─── PHASE 3: MANUAL PAYMENTS ───────────────────────────────────────────────

window.submitManualPayment = async function(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSubmitPayment');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Recording...';
    
    const data = {
        amount: document.getElementById('payAmount').value,
        payment_method: document.getElementById('payMethod').value,
        reference_number: document.getElementById('payReference').value,
        notes: document.getElementById('payNotes').value
    };
    
    try {
        const res = await window.apiAction(`/caterer/api/bookings/${currentBookingId}/record-payment`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (res) {
            if (window.showSuccess) window.showSuccess('Manual payment recorded successfully.');
            document.getElementById('recordPaymentForm').reset();
            window.openBookingDetailModal(currentBookingId);
        }
    } catch(err) {
        alert("Error recording payment: " + err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save"></i> Record Payment';
    }
};

window.toggleModalFullscreen = function(modalId, btn) {
    const modal = document.getElementById(modalId);
    if (modal) {
        const content = modal.querySelector('.modal-content-pro');
        if (content) {
            if (content.classList.contains('fullscreen-modal')) {
                content.classList.remove('fullscreen-modal');
                if (btn) btn.innerHTML = '<i class="fas fa-expand"></i>';
            } else {
                content.classList.add('fullscreen-modal');
                if (btn) btn.innerHTML = '<i class="fas fa-compress"></i>';
            }
        }
    }
};

