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
        if (typeof window.resetBookingCustomerDetails === 'function') window.resetBookingCustomerDetails();
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
        const rawBid = target.getAttribute('data-id') || id || target.getAttribute('data-booking-id') || '';
        const cleanBid = String(rawBid).replace(/\D/g, '') || String(rawBid);
        const bid = cleanBid;
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

            // 4. Preparation Status
            if (['confirmed', 'preparing', 'setup_ongoing', 'in_progress', 'ready_for_delivery', 'ready_for_pickup', 'arrived'].includes(status)) {
                addAction('Event Preparation', 'fa-clipboard-check', function() {
                    const viewBtn = target.querySelector('.view-details');
                    if (viewBtn) {
                        window.showBookingDetails(viewBtn);
                        setTimeout(function() {
                            const prepBtn = document.getElementById('tabBtnPreparation');
                            if (prepBtn && typeof switchBookingTab === 'function') {
                                switchBookingTab('preparation', prepBtn);
                            }
                            const card = document.querySelector('#btab-preparation .prep-status-card');
                            if (card) card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
        if (item.dataset.bookingId) {
            visibleIds.add(item.dataset.bookingId);
            visibleIds.add(item.dataset.bookingId.replace(/^[A-Za-z]+-/, '').replace(/^0+/, ''));
        }
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

// ─── BOOKING DETAILS HYDRATION ─────────────────────────────────────────────

function hydrateButtonDataset(btn, detail) {
    if (!btn || !detail) return;
    const isManual = detail.source_kind === 'manual' || !detail.has_registered_customer;
    const customerRef = detail.customer_ref || detail.customer_reference || btn.dataset.customerRef || '';
    
    const fields = {
        status: detail.status || btn.dataset.status || '',
        paymentStatus: detail.payment_status || btn.dataset.paymentStatus || 'unpaid',
        source: detail.booking_source || (isManual ? 'MANUAL' : 'ONLINE'),
        sourceKind: detail.source_kind || (isManual ? 'manual' : 'online'),
        sourceLabel: detail.source_label || (isManual ? 'MANUAL BOOKING' : 'ONLINE BOOKING'),
        bookingChannel: detail.booking_channel || btn.dataset.bookingChannel || (isManual ? 'Manual / Direct Inquiry' : 'OccaServe Website'),
        addedBy: detail.added_by || btn.dataset.addedBy || (isManual ? 'Caterer / Staff' : 'Customer'),
        celebrantName: detail.celebrant_name || '',
        paymentRecordsJson: JSON.stringify(detail.payment_records || []),
        eventDate: detail.event_date || btn.dataset.eventDate || '',
        eventTime: detail.event_time || btn.dataset.eventTime || 'TBA',
        customerRef: customerRef,
        customer: customerRef || (isManual ? 'Walk-in Customer' : 'Customer'),
        email: '',
        contact: '',
        venue: detail.venue || btn.dataset.venue || 'Not specified',
        eventType: detail.event_type || btn.dataset.eventType || 'Booking',
        specificName: (detail.package && detail.package.name) || detail.event_name || detail.event_type || 'Booking',
        guestCount: detail.guest_count || btn.dataset.guestCount || 0,
        totalRawAmount: detail.total_amount != null ? detail.total_amount : (btn.dataset.totalRawAmount || 0),
        amountPaid: detail.amount_paid != null ? detail.amount_paid : (btn.dataset.amountPaid || 0),
        balance: detail.balance_amount != null
            ? detail.balance_amount
            : (detail.payment_summary && detail.payment_summary.remaining_balance != null
                ? detail.payment_summary.remaining_balance
                : Math.max(Number(detail.total_amount || 0) - Number(detail.amount_paid || 0), 0)),
        pendingAmount: detail.pending_amount != null ? detail.pending_amount : (btn.dataset.pendingAmount || 0),
        remainingAfterVerification: detail.remaining_after_verification != null ? detail.remaining_after_verification : (btn.dataset.remainingAfterVerification || 0),
        isUnderReview: String(Boolean(detail.is_under_review || detail.needs_verification || ['proof_submitted', 'balance_proof_submitted', 'cash_payment_requested', 'cash_balance_requested'].includes(detail.payment_status))),
        needsVerification: String(Boolean(detail.needs_verification || detail.is_under_review)),
        canStartPreparation: String(Boolean(detail.can_start_preparation)),
        paymentMethod: detail.payment_method || btn.dataset.paymentMethod || 'Not specified',
        paymentPlan: detail.payment_plan || btn.dataset.paymentPlan || 'downpayment',
        paymentRef: detail.payment_reference || btn.dataset.paymentRef || '',
        bookedOn: detail.created_at ? new Date(detail.created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }) : (btn.dataset.bookedOn || '—'),
        balanceDue: detail.balance_due_date ? detail.balance_due_date.slice(0, 10) : (btn.dataset.balanceDue || ''),
        actualCost: detail.actual_cost || 0,
        hasRegisteredCustomer: String(Boolean(detail.has_registered_customer)),
        isPackage: detail.is_package != null ? String(detail.is_package) : (btn.dataset.isPackage || 'true'),
        isFoodOrder: String(detail.document_type === 'invoice' || detail.event_type === 'Ala Carte Order'),
        isVerified: String(Boolean(detail.customer_is_verified)),
        hasKycRecord: 'false',
        hasContract: String(Boolean(detail.contract && detail.contract.has_contract)),
        verificationJson: '{}',
        contractJson: JSON.stringify(detail.contract || {}),
        packageJson: JSON.stringify(detail.package || {}),
        catererServicesJson: JSON.stringify(detail.caterer_services || []),
        selectedServicesJson: JSON.stringify(detail.services || []),
        selectedItemsJson: JSON.stringify(detail.selected_items || []),
        equipmentItemsJson: JSON.stringify(detail.equipment_items || []),
        preparationStatus: detail.preparation_status || 'not_started',
        requests: detail.special_requests || btn.dataset.requests || '',
        motif: detail.motif_theme || detail.motif || btn.dataset.motif || '',
        documentType: detail.document_type || '',
        bookingRef: detail.booking_ref || detail.booking_reference || btn.dataset.bookingRef || '',
        proofUrl: detail.payment_proof_url || '',
        balanceProofUrl: detail.balance_proof_url || '',
        hasMenu: String(Boolean(detail.package || (detail.selected_items && detail.selected_items.length))),
        customRequirementsJson: JSON.stringify(detail.custom_requirements || {}),
        catererNotes: detail.caterer_notes || ''
    };
    Object.entries(fields).forEach(([key, value]) => {
        btn.dataset[key] = value == null ? '' : String(value);
    });
    btn.dataset.workspaceHydrated = 'true';
}

let customerDetailsLoadedForBookingId = null;

window.resetBookingCustomerDetails = function() {
    customerDetailsLoadedForBookingId = null;
    const gate = document.getElementById('custDetailsGate');
    const details = document.getElementById('custDetailsContent');
    const error = document.getElementById('custDetailsError');
    const button = document.getElementById('btnViewCustomerDetails');
    if (gate) gate.style.display = 'flex';
    if (details) details.style.display = 'none';
    if (error) { error.style.display = 'none'; error.textContent = ''; }
    if (button) { button.disabled = false; button.innerHTML = '<i class="fas fa-user-lock"></i> View Customer Details'; }
    ['custFullName', 'custMobile', 'custEmail', 'custType'].forEach(function(id) {
        const field = document.getElementById(id);
        if (field) field.textContent = '—';
    });
    const emailBadge = document.getElementById('custEmailVerifiedBadge');
    if (emailBadge) emailBadge.style.display = 'none';
    [['btnCallCustomer', 'tel:'], ['btnSmsCustomer', 'sms:'], ['btnEmailCustomer', 'mailto:']].forEach(function(item) {
        const link = document.getElementById(item[0]);
        if (link) { link.href = 'javascript:void(0)'; link.style.opacity = '0.5'; }
    });
};

window.loadCustomerDetails = async function() {
    const bookingId = String(currentBookingId || '').replace(/\D/g, '');
    if (!bookingId || customerDetailsLoadedForBookingId === bookingId) return;

    const button = document.getElementById('btnViewCustomerDetails');
    const error = document.getElementById('custDetailsError');
    if (button) { button.disabled = true; button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading details'; }
    if (error) { error.style.display = 'none'; error.textContent = ''; }

    try {
        const response = await fetch(`/caterer/api/bookings/${bookingId}/customer-details`, {
            headers: { 'Accept': 'application/json' }
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Customer details are unavailable.');
        if (String(currentBookingId || '').replace(/\D/g, '') !== bookingId) return;

        document.getElementById('custFullName').textContent = data.name || (data.is_manual ? 'Walk-in customer' : 'Customer name not provided');
        document.getElementById('custMobile').textContent = data.phone || 'Not provided';
        document.getElementById('custEmail').textContent = data.email || 'Not provided';
        document.getElementById('custType').textContent = data.is_manual ? 'Manual / Walk-in Client' : 'Registered Customer';
        const emailBadge = document.getElementById('custEmailVerifiedBadge');
        if (emailBadge) emailBadge.style.display = data.email && data.email_verified ? 'inline-block' : 'none';

        const phone = data.phone || '';
        const email = data.email || '';
        [['btnCallCustomer', phone ? `tel:${phone}` : ''], ['btnSmsCustomer', phone ? `sms:${phone}` : ''], ['btnEmailCustomer', email ? `mailto:${email}` : '']].forEach(function(item) {
            const link = document.getElementById(item[0]);
            if (link) { link.href = item[1] || 'javascript:void(0)'; link.style.opacity = item[1] ? '1' : '0.5'; }
        });

        customerDetailsLoadedForBookingId = bookingId;
        const gate = document.getElementById('custDetailsGate');
        const details = document.getElementById('custDetailsContent');
        if (gate) gate.style.display = 'none';
        if (details) details.style.display = 'block';
        if (button) button.innerHTML = '<i class="fas fa-user-check"></i> Customer Details Viewed';
    } catch (err) {
        if (error) { error.textContent = err.message || 'Could not load customer details.'; error.style.display = 'block'; }
        if (button) { button.disabled = false; button.innerHTML = '<i class="fas fa-user-lock"></i> Try Again'; }
    }
};


// ─── HELPER: Sync Left-Footer Buttons to Booking Status ─────────────────────
// Active unpaid bookings can be cancelled; closed bookings can be archived.
// NOTE: .occ-modal-footer .btn-secondary-pro uses display:inline-flex !important,
// so we must hide via class (.is-footer-btn-hidden) not style.display.
function _syncFooterButtons(cleanId, normStatus, isFullyPaid) {
    var cancelBtn = document.getElementById('btnFooterCancelBooking');
    var archiveBtn = document.getElementById('btnFooterArchiveBooking');
    if (!cancelBtn && !archiveBtn) return;

    var s = String(normStatus || '').toLowerCase().trim();
    var id = String(cleanId || currentBookingId || '').replace(/\D/g, '') || cleanId;
    if (typeof isFullyPaid !== 'boolean') {
        var viewBtn = document.querySelector(`.view-details[data-id="${id}"]`);
        var total = Math.max(parseFloat(viewBtn?.dataset?.totalRawAmount) || 0, 0);
        var paid = Math.max(parseFloat(viewBtn?.dataset?.amountPaid) || 0, 0);
        var balance = Math.max(parseFloat(viewBtn?.dataset?.balance) || (total - paid), 0);
        var paymentStatus = String(viewBtn?.dataset?.paymentStatus || '').toLowerCase();
        isFullyPaid = (total > 0 && paid >= total - 0.009 && balance <= 0.009)
            || (total <= 0 && ['paid', 'fully_paid'].includes(paymentStatus));
    }

    // Closed / terminal — Archive only
    var CLOSED = {
        completed: 1, cancelled: 1, canceled: 1, rejected: 1,
        declined: 1, expired: 1, archived: 1, void: 1, released: 1
    };
    var canArchive = !!CLOSED[s];
    var canCancel = !canArchive && !isFullyPaid;

    function setFooterBtnVisible(btn, visible) {
        if (!btn) return;
        btn.classList.toggle('is-footer-btn-hidden', !visible);
        btn.setAttribute('aria-hidden', visible ? 'false' : 'true');
        btn.tabIndex = visible ? 0 : -1;
        if (visible) {
            btn.style.setProperty('display', 'inline-flex', 'important');
        } else {
            btn.style.setProperty('display', 'none', 'important');
        }
    }

    setFooterBtnVisible(cancelBtn, canCancel);
    if (cancelBtn) {
        cancelBtn.onclick = function (e) {
            if (e) { e.preventDefault(); e.stopPropagation(); }
            confirmRejectBooking(id);
        };
    }

    setFooterBtnVisible(archiveBtn, canArchive);
    if (archiveBtn) {
        archiveBtn.onclick = function (e) {
            if (e) { e.preventDefault(); e.stopPropagation(); }
            confirmArchiveBooking(id);
        };
    }
}

// ─── MODAL: BOOKING DETAILS ──────────────────────────────────────────────────

function showBookingDetails(btn) {
    var data = btn.dataset;
    var rawId = data.id || data.bookingId || '';
    var cleanId = String(rawId).replace(/\D/g, '') || String(rawId);
    var wasModalOpen = document.getElementById('bookingDetailModal')?.classList.contains('active');
    var previousBookingId = String(currentBookingId || '');
    if (!wasModalOpen || previousBookingId !== cleanId) window.resetBookingCustomerDetails();
    data.id = cleanId;

    var sourceVal = (data.source || '').toString().toLowerCase();
    var sourceKindVal = (data.sourceKind || '').toString().toLowerCase();
    var isManual = sourceKindVal === 'manual' || data.isWalkin === 'true' || data.isManual === 'true' || sourceVal.includes('walk') || sourceVal.includes('manual');
    var bookingStatus = (data.status || 'pending').toLowerCase();
    var paymentStatus = (data.paymentStatus || 'unpaid').toLowerCase();

    var totalAmountValue = Math.max(parseFloat(data.totalRawAmount) || 0, 0);
    var paidAmountValue = Math.max(parseFloat(data.amountPaid) || 0, 0);
    if ((paymentStatus === 'paid' || paymentStatus === 'fully_paid') && totalAmountValue > 0 && paidAmountValue <= 0) {
        paidAmountValue = totalAmountValue;
    }
    var balanceValue = Math.max(parseFloat(data.balance) || (totalAmountValue - paidAmountValue), 0);
    var isFullyPaidNow = totalAmountValue > 0 && paidAmountValue >= totalAmountValue - 0.009 && balanceValue <= 0.009;

    // Under-review: trust API flag first, then payment_status, then proof+unpaid heuristic
    var reviewStatuses = ['proof_submitted', 'balance_proof_submitted', 'cash_payment_requested', 'cash_balance_requested', 'pending_verification'];
    var isUnderReview = (
        data.isUnderReview === 'true' ||
        data.needsVerification === 'true' ||
        reviewStatuses.includes(paymentStatus) ||
        (Boolean(data.proofUrl || data.balanceProofUrl) && paidAmountValue <= 0 && ['pending', 'awaiting_payment', 'pending_payment'].includes(bookingStatus) && !['deposit_paid', 'paid', 'fully_paid'].includes(paymentStatus))
    );
    var pendingReviewAmount = Math.max(parseFloat(data.pendingAmount) || 0, 0);
    var remainingAfterVerif = Math.max(parseFloat(data.remainingAfterVerification) || 0, 0);
    data.isUnderReview = isUnderReview ? 'true' : 'false';
    data.needsVerification = isUnderReview ? 'true' : 'false';

    var formattedTotal = '₱' + totalAmountValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    var formattedPaid = '₱' + paidAmountValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    var formattedBalance = '₱' + balanceValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    var formattedPending = '₱' + pendingReviewAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    data.amount = formattedTotal;
    data.totalRawAmount = String(totalAmountValue);
    data.amountPaid = String(paidAmountValue);
    data.balance = String(balanceValue);

    currentBookingId = cleanId;
    window.currentBookingStatus = data.status;
    currentEventDate = data.eventDate;

    const prepStatusButton = document.getElementById('btnUpdatePrepStatus');
    const isStatusLocked = ['completed', 'delivered'].includes(bookingStatus);
    if (prepStatusButton) {
        prepStatusButton.disabled = isStatusLocked;
        prepStatusButton.title = isStatusLocked ? 'Completed bookings are locked.' : 'Update preparation status';
        prepStatusButton.innerHTML = isStatusLocked
            ? '<i class="fas fa-lock"></i> Status Locked'
            : '<i class="fas fa-sync-alt"></i> Update Status';
    }

    // Immediately sync footer buttons so Archive/Cancel visibility is correct before hydration
    _syncFooterButtons(cleanId, bookingStatus, isFullyPaidNow);

    // Background hydration (silent, non-blocking)
    if (btn.dataset.workspaceHydrated !== 'true' && btn.dataset.workspaceHydrated !== 'loading') {
        btn.dataset.workspaceHydrated = 'loading';
        fetch(`/caterer/api/bookings/${cleanId}/details`, { headers: { 'Accept': 'application/json' } })
            .then(function(res) { return res.ok ? res.json() : null; })
            .then(function(detail) {
                if (detail) {
                    hydrateButtonDataset(btn, detail);
                } else {
                    btn.dataset.workspaceHydrated = 'true';
                }
                if (String(currentBookingId) === String(cleanId) && document.getElementById('bookingDetailModal')?.classList.contains('active')) {
                    showBookingDetails(btn);
                }
            })
            .catch(function(err) {
                btn.dataset.workspaceHydrated = 'true';
                console.warn('Background details fetch failed, retaining preloaded data:', err);
            });
    }

    // Date & Time formatting
    var edate = new Date(data.eventDate);
    var formattedDate = !isNaN(edate.getTime()) ? edate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : (data.eventDate || 'Date TBA');
    var formattedTime = data.eventTime || 'TBA';
    var paxCount = data.guestCount || 0;
    var isFoodOrder = data.isFoodOrder === 'true' || data.isFoodOrder === true;
    var isRentalOrder = data.documentType === 'rental_agreement' || data.eventType === 'Equipment Rental';
    var candidateRef = data.bookingRef || data.booking_ref || '';
    if (data.bookingRef && (!candidateRef || candidateRef.startsWith('BK-')) && !data.bookingRef.startsWith('BK-')) {
        candidateRef = data.bookingRef;
    }
    var formattedRefId = candidateRef || ('BK-' + String(cleanId).padStart(6, '0'));
    var titlePrefix = isRentalOrder ? 'Rental Agreement #' : (isFoodOrder ? 'Food Order #' : (bookingStatus === 'pending_review' || bookingStatus === 'inquiry' ? 'Inquiry Details #' : 'Booking #'));

    // ─── 1. MODAL HEADER POPULATION ──────────────────────────────────────────
    var mbTitle = document.getElementById('modalBookingId');
    if (mbTitle) {
        if (data.isUrgent === 'true') {
            mbTitle.innerHTML = `${titlePrefix}${formattedRefId} <span style="background: #fff1f2; color: #e11d48; font-size: 0.65rem; padding: 2px 8px; border-radius: 50px; margin-left: 8px; border: 1px solid #fecdd3; vertical-align: middle;"><i class="fas fa-clock"></i> URGENT</span>`;
        } else {
            mbTitle.innerText = titlePrefix + formattedRefId;
        }
    }

    // Source Badge
    var srcBadge = document.getElementById('modalBookingSourceBadge');
    if (srcBadge) {
        if (isManual) {
            srcBadge.className = 'badge-status badge-manual';
            srcBadge.innerHTML = '<i class="fas fa-store" style="margin-right: 4px;"></i> MANUAL BOOKING';
            srcBadge.style.background = '#ffedd5';
            srcBadge.style.color = '#c2410c';
            srcBadge.style.borderColor = '#fed7aa';
        } else {
            srcBadge.className = 'badge-status badge-online';
            srcBadge.innerHTML = '<i class="fas fa-globe" style="margin-right: 4px;"></i> ONLINE BOOKING';
            srcBadge.style.background = '#f3e8ff';
            srcBadge.style.color = '#7e22ce';
            srcBadge.style.borderColor = '#e9d5ff';
        }
    }

    // Booking Status Badge
    var stBadge = document.getElementById('modalStatus');
    if (stBadge) {
        var statusLabel = (bookingStatus || 'pending').replace(/_/g, ' ').toUpperCase();
        var stBg = '#f1f5f9', stColor = '#475569', stBorder = '#cbd5e1';
        if (bookingStatus === 'confirmed') {
            stBg = '#dcfce7'; stColor = '#166534'; stBorder = '#bbf7d0';
        } else if (bookingStatus === 'preparing') {
            stBg = '#e0e7ff'; stColor = '#4338ca'; stBorder = '#c7d2fe';
        } else if (bookingStatus === 'completed') {
            stBg = '#f0fdf4'; stColor = '#15803d'; stBorder = '#86efac';
        } else if (bookingStatus === 'cancelled') {
            stBg = '#fee2e2'; stColor = '#b91c1c'; stBorder = '#fecaca';
        } else if (isUnderReview) {
            stBg = '#fef3c7'; stColor = '#92400e'; stBorder = '#fde68a';
            if (paymentStatus === 'cash_payment_requested' || paymentStatus === 'cash_balance_requested') {
                statusLabel = 'CONFIRM CASH';
            } else if (paymentStatus === 'balance_proof_submitted') {
                statusLabel = 'VERIFY BALANCE';
            } else {
                statusLabel = 'VERIFY PAYMENT';
            }
        } else if (bookingStatus === 'pending' || bookingStatus === 'pending_review' || bookingStatus === 'inquiry' || bookingStatus === 'awaiting_payment') {
            stBg = '#fef3c7'; stColor = '#92400e'; stBorder = '#fde68a';
            if (bookingStatus === 'pending_review') statusLabel = 'NEW INQUIRY';
            else if (bookingStatus === 'pending' || bookingStatus === 'awaiting_payment') statusLabel = 'PENDING PAY';
        }
        stBadge.innerText = statusLabel;
        stBadge.style.background = stBg;
        stBadge.style.color = stColor;
        stBadge.style.borderColor = stBorder;
    }

    // Payment Status Badge — amounts win over stale payment_status flags
    var payBadge = document.getElementById('modalPaymentStatusBadge');
    if (payBadge) {
        var isFullyPaidNow = totalAmountValue > 0 && paidAmountValue >= totalAmountValue - 0.009 && balanceValue <= 0.009;
        if (isFullyPaidNow) {
            payBadge.innerText = 'FULLY PAID';
            payBadge.style.background = '#dcfce7'; payBadge.style.color = '#166534'; payBadge.style.borderColor = '#bbf7d0';
        } else if (isUnderReview) {
            payBadge.innerText = 'PAYMENT UNDER REVIEW';
            payBadge.style.background = '#fef3c7'; payBadge.style.color = '#92400e'; payBadge.style.borderColor = '#fde68a';
        } else if (totalAmountValue > 0 && (paidAmountValue > 0 || paymentStatus.includes('partial') || paymentStatus.includes('downpayment') || paymentStatus === 'deposit_paid')) {
            payBadge.innerText = 'PARTIALLY PAID';
            payBadge.style.background = '#e0f2fe'; payBadge.style.color = '#0369a1'; payBadge.style.borderColor = '#bae6fd';
        } else {
            payBadge.innerText = 'UNPAID';
            payBadge.style.background = '#fff7ed'; payBadge.style.color = '#c2410c'; payBadge.style.borderColor = '#fed7aa';
        }
    }

    // Booking Channel & Added By & Created Date
    var channelEl = document.getElementById('modalBookingChannel');
    if (channelEl) channelEl.innerText = data.bookingChannel || (isManual ? 'Manual / Direct Inquiry' : 'OccaServe Website');

    var addedByEl = document.getElementById('modalAddedBy');
    if (addedByEl) addedByEl.innerText = data.addedBy || (isManual ? 'Caterer' : 'Customer');

    var createdDateEl = document.getElementById('modalCreatedDate');
    if (createdDateEl) createdDateEl.innerText = data.bookedOn || '—';

    // Customer Headline & Subline
    var custHeadline = document.getElementById('modalCustomerHeadline');
    if (custHeadline) custHeadline.innerText = data.customerRef || 'Customer Ref';

    var custVerifBadge = document.getElementById('modalCustomerVerificationBadge');
    if (custVerifBadge) custVerifBadge.style.display = 'none';

    var eventSubline = document.getElementById('modalEventSublineText');
    if (eventSubline) {
        var celebrantPart = data.celebrantName ? ` • Celebrant: ${data.celebrantName}` : '';
        eventSubline.innerText = `${data.eventType || 'Event'}${celebrantPart} • ${formattedDate} • ${formattedTime} • ${paxCount} pax`;
    }

    var venueText = document.getElementById('modalVenueText');
    if (venueText) venueText.innerText = data.venue || 'Not specified';

    // Header Financial Display
    var headerTotal = document.getElementById('modalHeaderTotal');
    if (headerTotal) headerTotal.innerText = formattedTotal;

    var headerPaid = document.getElementById('modalHeaderPaid');
    if (headerPaid) headerPaid.innerText = formattedPaid + ' paid';

    var headerBal = document.getElementById('modalHeaderBalance');
    if (headerBal) headerBal.innerText = formattedBalance + ' bal';

    // ─── 2. TAB CONFIGURATION ────────────────────────────────────────────────
    var contextObj = {
        isManual: isManual,
        hasKycRecord: data.hasKycRecord === 'true' || data.isVerified === 'true',
        hasContractRecord: data.hasContractRecord === 'true' || Boolean(data.contractId)
    };
    configureBookingTabs(data, contextObj);

    // ─── CONSULTATION CHAT SETUP ─────────────────────────────────────────────
    var onlineChatView = document.getElementById('modalChatOnlineView');
    var manualChatView = document.getElementById('modalChatManualView');
    var chatBadge = document.getElementById('modalChatTabBadge');
    var unreadChatCount = parseInt(data.unreadChat || '0', 10);

    if (isManual) {
        if (onlineChatView) onlineChatView.style.display = 'none';
        if (manualChatView) manualChatView.style.display = 'flex';
        var manChannelDisp = document.getElementById('modalManualChannelDisplay');
        if (manChannelDisp) manChannelDisp.innerText = data.bookingChannel || 'Manual / Direct Inquiry';
        if (chatBadge) chatBadge.style.display = 'none';
    } else {
        if (manualChatView) manualChatView.style.display = 'none';
        if (onlineChatView) onlineChatView.style.display = 'flex';
        var chatCustHdr = document.getElementById('modalChatCustomerHeader');
        if (chatCustHdr) chatCustHdr.innerText = (data.customerRef || 'Customer') + ' Consultation';
        var chatSubline = document.getElementById('modalChatBookingSubline');
        if (chatSubline) chatSubline.innerText = `${titlePrefix}${formattedRefId} • ${data.eventType || 'Online Booking'}`;
        var chatFormBid = document.getElementById('modalChatBookingId');
        if (chatFormBid) chatFormBid.value = cleanId;

        if (chatBadge) {
            if (unreadChatCount > 0) {
                chatBadge.textContent = unreadChatCount;
                chatBadge.style.display = 'inline-block';
            } else {
                chatBadge.style.display = 'none';
            }
        }
    }

    // ─── 3. TAB 1: OVERVIEW ──────────────────────────────────────────────────
    renderOverviewWorkspace(data, contextObj);

    // Event Info Card
    var ovType = document.getElementById('ovEventType'); if (ovType) ovType.innerText = data.eventType || 'Event';
    var ovCel = document.getElementById('ovCelebrant'); if (ovCel) ovCel.innerText = data.celebrantName || 'N/A';
    var ovDt = document.getElementById('ovEventDate'); if (ovDt) ovDt.innerText = formattedDate;
    var ovTm = document.getElementById('ovEventTime'); if (ovTm) ovTm.innerText = formattedTime;
    var ovPax = document.getElementById('ovGuestCount'); if (ovPax) ovPax.innerText = `${paxCount} pax`;
    var ovMot = document.getElementById('ovMotif'); if (ovMot) ovMot.innerText = data.motif || 'Not specified';
    var ovVen = document.getElementById('ovVenue'); if (ovVen) ovVen.innerText = data.venue || 'Not specified';

    // Booking Info Card
    var ovRef = document.getElementById('ovBookingRef'); if (ovRef) ovRef.innerText = '#' + formattedRefId;
    var ovSrc = document.getElementById('ovSourceBadge');
    if (ovSrc) {
        ovSrc.innerText = isManual ? 'MANUAL BOOKING' : 'ONLINE BOOKING';
        ovSrc.style.color = isManual ? '#c2410c' : '#4338ca';
    }
    var ovChan = document.getElementById('ovBookingChannel'); if (ovChan) ovChan.innerText = data.bookingChannel || (isManual ? 'Manual / Direct Inquiry' : 'OccaServe Website');
    var ovAdd = document.getElementById('ovAddedBy'); if (ovAdd) ovAdd.innerText = data.addedBy || (isManual ? 'Caterer' : 'Customer');
    var ovCreated = document.getElementById('ovCreatedDate'); if (ovCreated) ovCreated.innerText = data.bookedOn || '—';
    var ovCustRef = document.getElementById('ovCustomerRef'); if (ovCustRef) ovCustRef.innerText = data.customerRef || '—';
    var ovSt = document.getElementById('ovStatusText');
    if (ovSt) {
        if (isUnderReview) {
            ovSt.innerText = (paymentStatus === 'cash_payment_requested' || paymentStatus === 'cash_balance_requested')
                ? 'CONFIRM CASH'
                : (paymentStatus === 'balance_proof_submitted' ? 'VERIFY BALANCE' : 'VERIFY PAYMENT');
        } else if (bookingStatus === 'pending' || bookingStatus === 'awaiting_payment') {
            ovSt.innerText = 'PENDING PAY';
        } else {
            ovSt.innerText = (bookingStatus || 'pending').replace(/_/g, ' ').toUpperCase();
        }
    }

    // Financial Overview Box
    var ovTot = document.getElementById('ovTotalDisplay'); if (ovTot) ovTot.innerText = formattedTotal;
    var ovBal = document.getElementById('ovBalanceDisplay'); if (ovBal) ovBal.innerText = formattedBalance;
    var ovPaySt = document.getElementById('ovPaymentStatusDisplay');

    // Paid display: show submitted-under-review vs verified-paid
    var ovPd = document.getElementById('ovPaidDisplay');
    if (ovPd) {
        if (isUnderReview && pendingReviewAmount > 0) {
            ovPd.innerHTML = `<span style="color:#92400e; font-weight:700;">Submitted: ${formattedPending}</span> <span style="color:#94a3b8; font-size:0.78em;">(Under Review)</span><br><span style="color:#16a34a; font-size:0.85em;">Verified: ${formattedPaid}</span>`;
        } else {
            ovPd.innerText = formattedPaid;
        }
    }

    if (ovPaySt) {
        var isFullyPaidOv = totalAmountValue > 0 && paidAmountValue >= totalAmountValue - 0.009 && balanceValue <= 0.009;
        if (isFullyPaidOv) {
            ovPaySt.innerText = 'FULLY PAID'; ovPaySt.style.color = '#10b981';
        } else if (isUnderReview) {
            ovPaySt.innerText = 'UNDER REVIEW'; ovPaySt.style.color = '#d97706';
        } else if (totalAmountValue > 0 && (paidAmountValue > 0 || paymentStatus.includes('partial') || paymentStatus === 'deposit_paid')) {
            ovPaySt.innerText = 'PARTIALLY PAID'; ovPaySt.style.color = '#38bdf8';
        } else {
            ovPaySt.innerText = 'UNPAID'; ovPaySt.style.color = '#f59e0b';
        }
    }

    // Process/Booking Status Workflow Tracker
    renderProcessWorkflow(bookingStatus, paymentStatus, totalAmountValue, paidAmountValue, isUnderReview);

    // ─── 4. TAB 2: CUSTOMER ──────────────────────────────────────────────────
    var custSrcNote = document.getElementById('custSourceNote');
    if (custSrcNote) {
        custSrcNote.innerText = isManual ? 'MANUAL ENTRY' : 'ONLINE ACCOUNT';
        custSrcNote.style.background = isManual ? '#ffedd5' : '#e0e7ff';
        custSrcNote.style.color = isManual ? '#c2410c' : '#4338ca';
    }
    var custRef = document.getElementById('custCustomerRef');
    if (custRef) custRef.textContent = data.customerRef || '—';

    // ─── 5. TAB 3: EVENT & PACKAGE / SERVICES ────────────────────────────────
    var paneOnline = document.getElementById('paneOnlinePackageView');
    var paneManual = document.getElementById('paneManualServicesView');
    if (isManual) {
        if (paneOnline) paneOnline.style.display = 'none';
        if (paneManual) paneManual.style.display = 'flex';

        // Populate Selected Services Container
        var servContainer = document.getElementById('manualSelectedServicesContainer');
        if (servContainer) {
            servContainer.innerHTML = '';
            var services = [];
            try {
                services = JSON.parse(data.selectedServicesJson || '[]');
                if (!services.length) {
                    services = JSON.parse(data.selectedItemsJson || '[]').filter(function(item) {
                        return item.type === 'service';
                    });
                }
            } catch(e) {}

            if (services && services.length > 0) {
                services.forEach(function(s) {
                    var sRow = document.createElement('div');
                    sRow.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 0.85rem 1rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;';
                    sRow.innerHTML = `
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <div style="width: 32px; height: 32px; border-radius: 6px; background: #e0f2fe; color: #0284c7; display: flex; align-items: center; justify-content: center; font-size: 0.85rem;">
                                <i class="fas fa-concierge-bell"></i>
                            </div>
                            <div>
                                <div style="font-weight: 700; color: #0f172a; font-size: 0.9rem;">${s.name || 'Service'}</div>
                                <div style="font-size: 0.75rem; color: #64748b;">${s.category || 'Event Service'}</div>
                            </div>
                        </div>
                        <div style="font-weight: 800; font-size: 1rem; color: #0f172a;">
                            ₱${Number(s.price || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                    `;
                    servContainer.appendChild(sRow);
                });
            } else {
                servContainer.innerHTML = `
                    <div style="padding: 1.5rem; text-align: center; color: #64748b; background: #f8fafc; border-radius: 8px; border: 1px dashed #cbd5e1;">
                        <i class="fas fa-clipboard-list" style="font-size: 1.5rem; color: #94a3b8; margin-bottom: 0.5rem; display: block;"></i>
                        <strong>${data.specificName || data.eventType || 'Event Services'}</strong>
                        <div style="font-size: 0.8rem; margin-top: 4px;">Custom package negotiated directly with the caterer.</div>
                    </div>
                `;
            }
        }

        // Equipment items
        var eqSection = document.getElementById('manualEquipmentSection');
        var eqList = document.getElementById('manualEquipmentList');
        if (eqSection && eqList) {
            var eqItems = [];
            try { eqItems = JSON.parse(data.equipmentItemsJson || '[]'); } catch(e) {}
            if (eqItems && eqItems.length > 0) {
                eqSection.style.display = 'block';
                eqList.innerHTML = '';
                eqItems.forEach(function(eq) {
                    var eqRow = document.createElement('div');
                    eqRow.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 0.65rem 0.85rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.82rem;';
                    eqRow.innerHTML = `
                        <span><i class="fas fa-box" style="color: #94a3b8; margin-right: 6px;"></i> ${eq.name} (x${eq.quantity || 1})</span>
                        <strong style="color: #0f172a;">₱${Number(eq.price || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</strong>
                    `;
                    eqList.appendChild(eqRow);
                });
            } else {
                eqSection.style.display = 'none';
            }
        }

        var manServTotal = document.getElementById('manualServicesTotalDisplay');
        if (manServTotal) manServTotal.innerText = formattedTotal;

    } else {
        if (paneOnline) paneOnline.style.display = 'flex';
        if (paneManual) paneManual.style.display = 'none';

        var packageDetails = {};
        try { packageDetails = JSON.parse(data.packageJson || '{}'); } catch(e) {}
        var hasPackageDetails = Boolean(packageDetails.id);
        var onTitle = document.getElementById('onPkgTitle');
        if (onTitle) onTitle.innerText = packageDetails.name || data.specificName || 'Selected Event Services';
        var onPrice = document.getElementById('onPkgPrice');
        var onPriceLabel = document.getElementById('onPkgPriceLabel');
        if (hasPackageDetails) {
            var packageUnitPrice = Number(packageDetails.price_per_head || packageDetails.price || 0);
            var packagePricingMode = packageDetails.pricing_mode || (packageDetails.price_unit === 'per_guest' ? 'per_pax' : 'fixed');
            var packagePrice = Number(packageDetails.price || packageUnitPrice);
            if (packagePricingMode === 'fixed' || packageDetails.price_unit !== 'per_guest') {
                var minimumGuests = Number(packageDetails.min_guests || 0);
                if (Number(paxCount) > minimumGuests && Number(packageDetails.additional_guest_price) > 0) {
                    packagePrice += (Number(paxCount) - minimumGuests) * Number(packageDetails.additional_guest_price);
                }
            } else {
                packagePrice = packageUnitPrice * Number(paxCount || 1);
            }
            if (onPrice) onPrice.innerText = '₱' + packagePrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            if (onPriceLabel) onPriceLabel.innerText = 'Base Package Price';
        } else {
            if (onPrice) onPrice.innerText = formattedTotal;
            if (onPriceLabel) onPriceLabel.innerText = 'Booking Amount';
        }
        var onMeta = document.getElementById('onPkgMeta');
        if (onMeta) {
            var packageMeta = [];
            if (hasPackageDetails && packageDetails.min_guests) {
                packageMeta.push(packageDetails.max_guests
                    ? `${packageDetails.min_guests}–${packageDetails.max_guests} guest capacity`
                    : `Minimum ${packageDetails.min_guests} guests`);
            } else if (!hasPackageDetails) {
                packageMeta.push(`${paxCount} guests for this booking`);
            }
            if (hasPackageDetails && packageDetails.service_duration) packageMeta.push(`${packageDetails.service_duration} hrs`);
            if (hasPackageDetails && packageDetails.service_type) packageMeta.push(packageDetails.service_type);
            onMeta.innerText = packageMeta.join(' • ') || 'Package details not available';
        }
        var onDescription = document.getElementById('onPkgDescription');
        if (onDescription) {
            onDescription.innerText = packageDetails.description || '';
            onDescription.style.display = packageDetails.description ? 'block' : 'none';
        }
        var onMotif = document.getElementById('onPkgMotifText'); if (onMotif) onMotif.innerText = data.motif || 'Not specified';
        var onReq = document.getElementById('onPkgRequestsText'); if (onReq) onReq.innerText = data.requests || 'None';

        var onInclusions = document.getElementById('onPkgInclusionsContainer');
        if (onInclusions) {
            var customReqs = {};
            try { customReqs = JSON.parse(data.customRequirementsJson || '{}'); } catch(e){}
            var custPayload = customReqs.customization || null;

            if (custPayload && custPayload.menu_groups && custPayload.menu_groups.length > 0) {
                onInclusions.innerHTML = '';
                var badgeDiv = document.createElement('div');
                badgeDiv.style.cssText = 'padding: 0.5rem 0.75rem; background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px; margin-bottom: 0.75rem; font-size: 0.8rem; font-weight: 800; color: #c2410c; display: flex; align-items: center; gap: 6px;';
                badgeDiv.innerHTML = '<i class="fas fa-sliders-h"></i> Customer Selected Menu Options';
                onInclusions.appendChild(badgeDiv);

                custPayload.menu_groups.forEach(function(group) {
                    var gBox = document.createElement('div');
                    gBox.style.cssText = 'margin-bottom: 0.75rem; background: #ffffff; border: 1px solid #fed7aa; border-radius: 8px; padding: 0.65rem 0.85rem;';
                    var gTitle = document.createElement('div');
                    gTitle.style.cssText = 'font-size: 0.78rem; font-weight: 800; color: #9a3412; text-transform: uppercase; margin-bottom: 0.35rem;';
                    gTitle.innerText = group.group_name;
                    gBox.appendChild(gTitle);

                    var dList = document.createElement('div');
                    dList.style.cssText = 'display: flex; flex-wrap: wrap; gap: 0.4rem;';
                    (group.selected_dishes || []).forEach(function(d) {
                        var dSpan = document.createElement('span');
                        dSpan.style.cssText = 'font-size: 0.8rem; font-weight: 700; color: #1e293b; background: #f8fafc; border: 1px solid #e2e8f0; padding: 2px 8px; border-radius: 6px; display: inline-flex; align-items: center; gap: 4px;';
                        var priceTag = '';
                        if (d.pricing_type === 'per_pax' && d.price > 0) priceTag = ` (+₱${d.price}/pax)`;
                        else if (d.pricing_type === 'fixed' && d.price > 0) priceTag = ` (+₱${d.price})`;
                        dSpan.innerHTML = `<i class="fas fa-check text-success" style="font-size: 0.7rem;"></i> ${d.name}${priceTag}`;
                        dList.appendChild(dSpan);
                    });
                    gBox.appendChild(dList);
                    onInclusions.appendChild(gBox);
                });

                if (custPayload.optional_services && custPayload.optional_services.length > 0) {
                    var sBox = document.createElement('div');
                    sBox.style.cssText = 'background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 0.65rem 0.85rem;';
                    var sTitle = document.createElement('div');
                    sTitle.style.cssText = 'font-size: 0.78rem; font-weight: 800; color: #1e40af; text-transform: uppercase; margin-bottom: 0.35rem;';
                    sTitle.innerText = 'Selected Optional Services';
                    sBox.appendChild(sTitle);

                    var sList = document.createElement('div');
                    sList.style.cssText = 'display: flex; flex-wrap: wrap; gap: 0.4rem;';
                    custPayload.optional_services.forEach(function(svc) {
                        var sSpan = document.createElement('span');
                        sSpan.style.cssText = 'font-size: 0.8rem; font-weight: 700; color: #1e3a8a; background: #ffffff; border: 1px solid #bfdbfe; padding: 2px 8px; border-radius: 6px; display: inline-flex; align-items: center; gap: 4px;';
                        var pTag = '';
                        if (svc.price > 0) pTag = ` (₱${svc.price})`;
                        sSpan.innerHTML = `<i class="fas fa-plus-circle text-primary" style="font-size: 0.7rem;"></i> ${svc.name}${pTag}`;
                        sList.appendChild(sSpan);
                    });
                    sBox.appendChild(sList);
                    onInclusions.appendChild(sBox);
                }
            } else {
                var selectedItems = [];
                try {
                    selectedItems = JSON.parse(data.selectedItemsJson || '[]').filter(function(item) {
                        return item.type === 'menu_item' || item.type === 'service';
                    });
                } catch(e) {}
                if (!selectedItems.length) {
                    try { selectedItems = JSON.parse(data.selectedServicesJson || '[]'); } catch(e) {}
                }
                var selectedMenuItems = selectedItems.some(function(item) { return item.type === 'menu_item'; });
                var selectedNames = new Set(selectedItems.map(function(item) { return String(item.name || '').trim().toLowerCase(); }));
                if (!selectedMenuItems) {
                    (packageDetails.menu_items || []).forEach(function(item) {
                        var itemName = String(item.name || '').trim();
                        var itemKey = itemName.toLowerCase();
                        if (itemName && !selectedNames.has(itemKey)) {
                            selectedItems.push({ name: itemName, type: 'menu_item', is_included: true, quantity: 1, price: 0 });
                            selectedNames.add(itemKey);
                        }
                    });
                }
                (packageDetails.service_items || []).concat(packageDetails.equipment_items || []).forEach(function(item) {
                    var itemName = String(item.name || '').trim();
                    var itemKey = itemName.toLowerCase();
                    if (itemName && !selectedNames.has(itemKey)) {
                        selectedItems.push({ name: itemName, type: 'included', is_included: true, quantity: item.quantity || 1, price: 0 });
                        selectedNames.add(itemKey);
                    }
                });
                (packageDetails.inclusions || []).forEach(function(inclusion) {
                    var itemName = String(typeof inclusion === 'string' ? inclusion : (inclusion.name || inclusion.label || '')).trim();
                    var itemKey = itemName.toLowerCase();
                    if (itemName && !selectedNames.has(itemKey)) {
                        selectedItems.push({
                            name: itemName,
                            type: 'included',
                            is_included: true,
                            quantity: typeof inclusion === 'object' ? (inclusion.quantity || inclusion.qty || 1) : 1,
                            price: 0
                        });
                        selectedNames.add(itemKey);
                    }
                });
                if (selectedItems && selectedItems.length > 0) {
                    onInclusions.innerHTML = '';
                    selectedItems.forEach(function(item) {
                        var incRow = document.createElement('div');
                        incRow.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 0.85rem;';
                        incRow.innerHTML = `
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <i class="fas fa-check-circle" style="color: #16a34a;"></i>
                                <span style="font-weight: 700; color: #0f172a;">${item.name}</span>
                                ${item.quantity > 1 ? `<span style="font-size: 0.75rem; color: #64748b;">(x${item.quantity})</span>` : ''}
                            </div>
                            <span style="font-weight: 800; color: #0f172a;">${item.is_included ? 'Included' : '₱' + Number(item.price || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
                        `;
                        onInclusions.appendChild(incRow);
                    });
                } else {
                    onInclusions.innerHTML = `
                        <div style="padding: 1rem; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; color: #475569; font-size: 0.85rem;">
                            <i class="fas fa-info-circle" style="color: #0284c7; margin-right: 6px;"></i> Includes full setup, buffet station, service staff, dinnerware, and standard decor package.
                        </div>
                    `;
                }
            }
        }
    }

    // ─── 6. TAB 4: VERIFICATION (ONLINE ONLY) ────────────────────────────────
    if (!isManual && data.hasKycRecord === 'true') {
        var kycInfo = {}; try { kycInfo = JSON.parse(data.verificationJson || '{}'); } catch(e){}
        var kycIsVerified = kycInfo.is_verified === true || kycInfo.is_verified === 'true' || String(kycInfo.status || '').toLowerCase() === 'verified';
        var vBadge = document.getElementById('verifStatusBadge');
        if (vBadge) {
            vBadge.innerText = kycInfo.status || 'PENDING';
            vBadge.style.background = kycIsVerified ? '#dcfce7' : '#fef3c7';
            vBadge.style.color = kycIsVerified ? '#166534' : '#92400e';
        }
        var vDoc = document.getElementById('verifDocText');
        var idSubmitted = kycInfo.id_submitted === true || kycInfo.id_submitted === 'true';
        if (vDoc) {
            vDoc.innerText = idSubmitted
                ? 'Submitted'
                : 'Not Submitted';
        }
        var ocrCompleted = kycInfo.ocr_completed === true || kycInfo.ocr_completed === 'true';
        var livenessCompleted = kycInfo.liveness_completed === true || kycInfo.liveness_completed === 'true';
        var vOcr = document.getElementById('verifOcrText'); if (vOcr) vOcr.innerText = ocrCompleted ? 'OCR Completed' : 'Pending';
        var vLiv = document.getElementById('verifLivenessText'); if (vLiv) vLiv.innerText = livenessCompleted ? 'Face Check Passed' : 'Pending';
        var vDocIcon = document.getElementById('verifDocIcon');
        var vOcrIcon = document.getElementById('verifOcrIcon');
        var vLivIcon = document.getElementById('verifLivenessIcon');
        [[vDocIcon, idSubmitted], [vOcrIcon, ocrCompleted], [vLivIcon, livenessCompleted]].forEach(function(entry) {
            if (!entry[0]) return;
            entry[0].className = entry[1] ? 'fas fa-check-circle' : 'fas fa-minus-circle';
            entry[0].style.color = entry[1] ? '#16a34a' : '#94a3b8';
        });
        var vTime = document.getElementById('verifTimestampVal'); if (vTime) vTime.innerText = kycInfo.verified_at || 'Not recorded';
    }

    // ─── 7. TAB 5: CONTRACT (ONLINE ONLY) ────────────────────────────────────
    if (!isManual && data.hasContract === 'true') {
        var contractInfo = {}; try { contractInfo = JSON.parse(data.contractJson || '{}'); } catch(e){}
        var cBadge = document.getElementById('contractStatusBadge');
        if (cBadge) cBadge.innerText = (contractInfo.status || 'PENDING').replace(/_/g, ' ').toUpperCase();

        var cCust = document.getElementById('contractCustSigText');
        if (cCust) {
            if (contractInfo.customer_signed) {
                cCust.innerText = 'Signed on ' + (contractInfo.customer_signed_at || 'record');
                cCust.style.color = '#16a34a';
            } else {
                cCust.innerText = 'Awaiting Customer Signature';
                cCust.style.color = '#94a3b8';
            }
        }

        var cCat = document.getElementById('contractCatSigText');
        if (cCat) {
            if (contractInfo.caterer_signed) {
                cCat.innerText = 'Signed on ' + (contractInfo.caterer_signed_at || 'record');
                cCat.style.color = '#16a34a';
            } else {
                cCat.innerText = 'Awaiting Caterer Signature';
                cCat.style.color = '#94a3b8';
            }
        }

        var noticeEl = document.getElementById('contractExpiryNotice');
        var signBtn = document.getElementById('btnViewContractModal');
        if (contractInfo.is_past_event) {
            if (noticeEl) noticeEl.style.display = 'block';
            if (signBtn) signBtn.style.display = 'none';
        } else {
            if (noticeEl) noticeEl.style.display = 'none';
            if (signBtn) signBtn.style.display = 'inline-flex';
        }
    }

    // ─── 8. TAB 6: PAYMENT ───────────────────────────────────────────────────
    var pTot = document.getElementById('payTotalAmount'); if (pTot) pTot.innerText = formattedTotal;
    var pBal = document.getElementById('payBalance'); if (pBal) pBal.innerText = formattedBalance;

    // Show submitted/verified breakdown in the Paid cell
    var pPaid = document.getElementById('payTotalPaid');
    if (pPaid) {
        if (isUnderReview && pendingReviewAmount > 0) {
            pPaid.innerHTML = `${formattedPaid} <span style="color:#92400e; font-size:0.82em; background:#fef3c7; border:1px solid #fde68a; padding:1px 6px; border-radius:4px; margin-left:4px;">(${formattedPending} Under Review)</span>`;
        } else {
            pPaid.innerText = formattedPaid;
        }
    }

    var pBadge = document.getElementById('paymentTabBadge');
    if (pBadge) {
        if (balanceValue <= 0) {
            pBadge.innerText = 'FULLY PAID'; pBadge.style.background = '#dcfce7'; pBadge.style.color = '#166534';
        } else if (isUnderReview) {
            pBadge.innerText = 'UNDER REVIEW'; pBadge.style.background = '#fef3c7'; pBadge.style.color = '#92400e';
        } else if (paidAmountValue > 0) {
            pBadge.innerText = 'PARTIALLY PAID'; pBadge.style.background = '#e0f2fe'; pBadge.style.color = '#0369a1';
        } else {
            pBadge.innerText = 'UNPAID'; pBadge.style.background = '#fff7ed'; pBadge.style.color = '#c2410c';
        }
    }

    var balanceReviewStatuses = ['balance_proof_submitted', 'cash_balance_requested'];
    var isBalanceUnderReview = balanceReviewStatuses.includes(String(paymentStatus || '').toLowerCase());

    var btnCopyLink = document.getElementById('btnPaymentTabCopyLink');
    if (btnCopyLink) {
        btnCopyLink.style.display = (isManual || balanceValue <= 0) ? 'none' : 'inline-flex';
    }

    var btnRecPay = document.getElementById('btnPaymentRecordAction');
    if (btnRecPay) {
        // Online + Manual: allow recording Cash/GCash/Bank when remaining balance exists
        // Hide while customer proof/cash request is awaiting verification
        btnRecPay.style.display = (balanceValue > 0 && !isBalanceUnderReview) ? 'inline-flex' : 'none';
        if (balanceValue > 0 && !isBalanceUnderReview) {
            btnRecPay.innerHTML = '<i class="fas fa-plus-circle"></i> Record Payment (Cash / GCash / Bank)';
        }
    }

    var btnVerifyBal = document.getElementById('btnVerifyBalanceProofAction');
    if (btnVerifyBal) {
        btnVerifyBal.style.display = (paymentStatus === 'balance_proof_submitted') ? 'inline-flex' : 'none';
    }

    var btnConfirmCashBal = document.getElementById('btnConfirmCashBalanceAction');
    if (btnConfirmCashBal) {
        btnConfirmCashBal.style.display = (paymentStatus === 'cash_balance_requested') ? 'inline-flex' : 'none';
    }

    var balGuide = document.getElementById('paymentBalanceSettleGuide');
    if (balGuide) {
        if (balanceValue > 0 && !isBalanceUnderReview) {
            balGuide.style.display = 'block';
            balGuide.innerHTML = isManual
                ? '<i class="fas fa-info-circle" style="color:#0284c7;"></i> Record Cash, GCash, or Bank payment received for the remaining balance.'
                : '<i class="fas fa-info-circle" style="color:#0284c7;"></i> Customer can upload GCash/Bank proof or request Cash via the payment link. Or record payment here if they already paid you offline.';
        } else if (paymentStatus === 'balance_proof_submitted') {
            balGuide.style.display = 'block';
            balGuide.innerHTML = '<i class="fas fa-shield-alt" style="color:#0284c7;"></i> Customer uploaded a balance payment proof. Verify it to mark Fully Paid.';
        } else if (paymentStatus === 'cash_balance_requested') {
            balGuide.style.display = 'block';
            balGuide.innerHTML = '<i class="fas fa-money-bill-wave" style="color:#16a34a;"></i> Customer requested cash for the remaining balance. Confirm only after you received the cash.';
        } else {
            balGuide.style.display = 'none';
        }
    }

    // Receipts / Uploaded Proofs
    var proofSec = document.getElementById('modalProofSection');
    var proofCont = document.getElementById('modalProofContainer');
    if (proofSec && proofCont) {
        var hasProof = Boolean(data.proofUrl || data.balanceProofUrl);
        if (hasProof) {
            proofSec.style.display = 'block';
            proofCont.innerHTML = '';
            if (data.proofUrl) {
                var downLink = document.createElement('a');
                downLink.href = data.proofUrl;
                downLink.target = '_blank';
                downLink.className = 'btn-secondary-pro';
                downLink.style.cssText = 'padding: 0.5rem 1rem; font-size: 0.82rem; font-weight: 700; text-decoration: none; display: inline-flex; align-items: center; gap: 6px;';
                downLink.innerHTML = '<i class="fas fa-image"></i> View Initial Payment Proof';
                proofCont.appendChild(downLink);
            }
            if (data.balanceProofUrl) {
                var balLink = document.createElement('a');
                balLink.href = data.balanceProofUrl;
                balLink.target = '_blank';
                balLink.className = 'btn-secondary-pro';
                balLink.style.cssText = 'padding: 0.5rem 1rem; font-size: 0.82rem; font-weight: 700; text-decoration: none; display: inline-flex; align-items: center; gap: 6px;';
                balLink.innerHTML = '<i class="fas fa-image"></i> View Balance Payment Proof';
                proofCont.appendChild(balLink);
            }
        } else {
            proofSec.style.display = 'none';
        }
    }

    // Payment History Rows
    var pRows = document.getElementById('paymentHistoryRows');
    if (pRows) {
        var records = [];
        try { records = JSON.parse(data.paymentRecordsJson || '[]'); } catch(e) {}
        if (records && records.length > 0) {
            pRows.innerHTML = '';
            records.forEach(function(rec) {
                var rDate = rec.payment_date ? new Date(rec.payment_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—';
                var rRow = document.createElement('tr');
                rRow.style.borderBottom = '1px solid #f1f5f9';
                var recStatusUpper = (rec.status || 'VERIFIED').toUpperCase();
                var recIsUnderReview = recStatusUpper === 'UNDER REVIEW';
                var recStatusBg = recIsUnderReview ? '#fef3c7' : '#dcfce7';
                var recStatusColor = recIsUnderReview ? '#92400e' : '#166534';
                var recAmtColor = recIsUnderReview ? '#92400e' : '#166534';
                var refText = rec.reference_notes || rec.reference_number || rec.notes || '—';
                rRow.innerHTML = `
                    <td style="padding: 0.75rem 1rem; font-weight: 600; color: #0f172a;">${rDate}</td>
                    <td style="padding: 0.75rem 1rem; color: #334155; text-transform: capitalize;">${rec.payment_method || 'Offline Payment'}</td>
                    <td style="padding: 0.75rem 1rem; color: #64748b;">${rec.recorded_by_type === 'caterer' ? 'Caterer' : 'Customer'}</td>
                    <td style="padding: 0.75rem 1rem; color: #64748b; font-family: monospace; font-size: 0.78rem;">${refText}</td>
                    <td style="padding: 0.75rem 1rem; text-align: right; font-weight: 800; color: ${recAmtColor};">₱${Number(rec.amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                    <td style="padding: 0.75rem 1rem; text-align: center;">
                        <span style="font-size: 0.7rem; font-weight: 800; padding: 2px 8px; border-radius: 4px; background: ${recStatusBg}; color: ${recStatusColor};">${recStatusUpper}</span>
                    </td>
                `;
                pRows.appendChild(rRow);
            });
        } else {
            pRows.innerHTML = '<tr><td colspan="6" style="padding: 1.5rem; text-align: center; color: #94a3b8;">No payment records found.</td></tr>';
        }
    }

    // Expense Tracker
    var expId = document.getElementById('expenseBookingId'); if (expId) expId.value = cleanId;
    var expTot = document.getElementById('bookingTotalAmount'); if (expTot) expTot.value = totalAmountValue;
    var expMb = document.getElementById('modalBookingTotal'); if (expMb) expMb.innerText = formattedTotal;

    var container = document.getElementById('actualExpenseRows');
    if (container) {
        container.innerHTML = '';
        var breakdown = [];
        try {
            var breakdownStr = data.expenseBreakdown;
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
            if (window.addExpenseRow) addExpenseRow();
        }
        if (window.calculateActualExpenses) calculateActualExpenses();
    }

    // ─── 9. TAB 7: PREPARATION & TAB 8: ACTIVITY ─────────────────────────────
    try {
        if (typeof window.loadBookingTasks === 'function') window.loadBookingTasks(cleanId);
    } catch(e) {
        console.warn('loadBookingTasks error:', e);
    }
    try {
        if (typeof window.loadBookingHistory === 'function') window.loadBookingHistory(cleanId);
    } catch(e) {
        console.warn('loadBookingHistory error:', e);
    }

    // ─── 10. FOOTER ACTIONS ──────────────────────────────────────────────────
    // Re-sync after full hydration to ensure status from API is reflected
    _syncFooterButtons(cleanId, bookingStatus, isFullyPaidNow);

    var rightActions = document.getElementById('modalFooterRightActions');
    if (rightActions) {
        var actionButtonsHtml = '';
        if (bookingStatus === 'pending_review' || bookingStatus === 'inquiry') {
            actionButtonsHtml += `<button type="button" onclick="confirmBookingDirect('${cleanId}')" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #16a34a; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-check"></i> Accept Booking</button>`;
        } else if (bookingStatus === 'pending' || bookingStatus === 'awaiting_payment' || bookingStatus === 'pending_payment') {
            if (isUnderReview || paymentStatus === 'proof_submitted' || (data.proofUrl && paidAmountValue <= 0)) {
                if (paymentStatus === 'cash_payment_requested') {
                    actionButtonsHtml += `<button type="button" onclick="window.confirmCashPayment('${cleanId}')" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #16a34a; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-money-bill-wave"></i> Confirm Cash Received</button>`;
                } else {
                    actionButtonsHtml += `<button type="button" onclick="window.verifyPayment('${cleanId}', false)" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #0284c7; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-shield-alt"></i> Verify Payment Proof</button>`;
                }
            } else if (isManual) {
                actionButtonsHtml += `<button type="button" onclick="openRecordPaymentModal()" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #16a34a; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-plus-circle"></i> Record Payment</button>`;
            } else {
                actionButtonsHtml += `<button type="button" onclick="window.copyInvoiceLink('${cleanId}')" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #ea580c; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-link"></i> Copy Payment Link</button>`;
            }
        } else if (data.paymentStatus === 'balance_proof_submitted' || data.paymentStatus === 'cash_balance_requested') {
            if (data.paymentStatus === 'cash_balance_requested') {
                actionButtonsHtml += `<button type="button" onclick="window.confirmCashPayment('${cleanId}')" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #16a34a; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-money-bill-wave"></i> Confirm Cash Balance</button>`;
            } else {
                actionButtonsHtml += `<button type="button" onclick="window.verifyPayment('${cleanId}', true)" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #0284c7; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-shield-alt"></i> Verify Balance Proof</button>`;
            }
        } else if (bookingStatus === 'confirmed') {
            actionButtonsHtml += `<button type="button" onclick="updateBookingStage('${cleanId}', 'preparing')" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: var(--primary-color, #800020); color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-utensils"></i> Start Preparation</button>`;
        } else if (bookingStatus === 'preparing') {
            actionButtonsHtml += `<button type="button" onclick="window.requestReadyForDelivery('${cleanId}')" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #0284c7; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-clipboard-check"></i> ${isFoodOrder ? 'Ready for Delivery / Pickup' : 'Preparation Complete'}</button>`;
        } else if (bookingStatus === 'ready_for_delivery') {
            actionButtonsHtml += `<button type="button" onclick="updateBookingStage('${cleanId}', 'on_the_way')" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #0284c7; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-truck"></i> ${isFoodOrder ? 'Out for Delivery' : 'Depart for Venue'}</button>`;
        } else if (bookingStatus === 'on_the_way') {
            actionButtonsHtml += `<button type="button" onclick="updateBookingStage('${cleanId}', 'arrived')" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #0284c7; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-map-marker-alt"></i> ${isFoodOrder ? 'Mark Arrived' : 'Mark Arrived at Venue'}</button>`;
        } else if (bookingStatus === 'ready_for_pickup') {
            var canCompletePickup = totalAmountValue > 0 && paidAmountValue >= (totalAmountValue - 0.009) && balanceValue <= 0.009;
            if (canCompletePickup) {
                actionButtonsHtml += `<button type="button" onclick="window.confirmCompleteBooking('${cleanId}')" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #16a34a; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-check"></i> ${isFoodOrder ? 'Mark Picked Up' : 'Mark Collected'}</button>`;
            } else {
                actionButtonsHtml += `<button type="button" onclick="window.openBalanceSettlement('${cleanId}')" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #ea580c; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-wallet"></i> Settle Remaining Balance First</button>`;
            }
        } else if (bookingStatus === 'arrived') {
            actionButtonsHtml += `<button type="button" onclick="updateBookingStage('${cleanId}', 'setup_ongoing')" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #0284c7; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-tools"></i> ${isFoodOrder ? 'Start Setup' : 'Start Event Setup'}</button>`;
        } else if (['in_progress', 'setup_ongoing'].includes(bookingStatus)) {
            var canCompleteNow = totalAmountValue > 0 && paidAmountValue >= (totalAmountValue - 0.009) && balanceValue <= 0.009;
            if (canCompleteNow) {
                actionButtonsHtml += `<button type="button" onclick="window.confirmCompleteBooking('${cleanId}')" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #16a34a; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-flag-checkered"></i> ${isFoodOrder ? 'Mark as Completed' : 'Complete Event'}</button>`;
            } else if (paymentStatus === 'balance_proof_submitted') {
                actionButtonsHtml += `<button type="button" onclick="window.verifyPayment('${cleanId}', true)" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #0284c7; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-shield-alt"></i> Verify Balance Proof</button>`;
            } else if (paymentStatus === 'cash_balance_requested') {
                actionButtonsHtml += `<button type="button" onclick="window.confirmCashPayment('${cleanId}')" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #16a34a; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-money-bill-wave"></i> Confirm Cash Balance</button>`;
            } else {
                actionButtonsHtml += `<button type="button" onclick="window.openBalanceSettlement('${cleanId}')" class="btn-primary" style="padding: 0.6rem 1.25rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; background: #ea580c; color: white; border: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-wallet"></i> Settle Remaining Balance First</button>`;
            }
        }

        rightActions.innerHTML = actionButtonsHtml + `
            <button type="button" onclick="bk_closeBookingDetailModal()" class="btn-secondary-pro" style="padding: 0.6rem 1.4rem; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer;">
                Close
            </button>
        `;
    }

    // Open Modal
    bk_openModal('bookingDetailModal');
}

// End of showBookingDetails

function bk_closeBookingDetailModal() { 
    if (typeof window.resetBookingCustomerDetails === 'function') window.resetBookingCustomerDetails();
    bk_closeModal('bookingDetailModal'); 
}

// ─── PROCESS / BOOKING STATUS WORKFLOW RENDERER ─────────────────────────────
function renderProcessWorkflow(bookingStatus, paymentStatus, totalAmount, amountPaid, isUnderReview) {
    // Map status → active step index (0-based)
    var STEPS = ['created', 'quotation', 'confirmation', 'payment', 'preparation', 'completion'];
    var STEP_DESCS = [
        'Booking has been created and is awaiting review.',
        'Quotation / pricing is being prepared or reviewed.',
        'Booking is confirmed and contract/agreement is signed.',
        'Payment processing — downpayment or full settlement.',
        'Event preparation is underway by the catering team.',
        'Event completed successfully.'
    ];

    var s = (bookingStatus || '').toLowerCase();
    var p = (paymentStatus || '').toLowerCase();
    var isFullyPaid = totalAmount > 0 && amountPaid >= totalAmount - 0.01;

    var activeIdx = 0; // default: Created
    var desc = STEP_DESCS[0];

    if (s === 'completed') {
        activeIdx = 5; desc = STEP_DESCS[5];
    } else if (['preparing', 'setup_ongoing', 'in_progress', 'on_the_way', 'ready_for_delivery', 'ready_for_pickup', 'arrived'].includes(s)) {
        activeIdx = 4; desc = STEP_DESCS[4];
    } else if (isFullyPaid || ['paid', 'fully_paid'].includes(p) || (amountPaid > 0 && !isUnderReview)) {
        activeIdx = 3; desc = 'Payment verified. Booking is now financially settled or partially settled.';
    } else if (isUnderReview || ['proof_submitted', 'balance_proof_submitted', 'cash_payment_requested', 'cash_balance_requested'].includes(p)) {
        activeIdx = 3; desc = 'Payment proof submitted and under review by the caterer.';
    } else if (['confirmed', 'awaiting_payment', 'pending_payment'].includes(s)) {
        activeIdx = 2; desc = STEP_DESCS[2];
    } else if (['quotation_phase', 'pending_quotation', 'awaiting_caterer', 'pending_review', 'under_review'].includes(s)) {
        activeIdx = 1; desc = STEP_DESCS[1];
    } else {
        activeIdx = 0; desc = STEP_DESCS[0];
    }

    // Update step visuals
    STEPS.forEach(function(name, idx) {
        var stepEl = document.getElementById('procStep_' + name);
        if (!stepEl) return;
        var dot = stepEl.querySelector('.proc-dot');
        var label = stepEl.querySelector('.proc-label');
        if (idx < activeIdx) {
            // Completed step
            if (dot) { dot.style.background = '#f97316'; dot.style.borderColor = '#f97316'; dot.style.color = '#ffffff'; dot.innerHTML = '<i class="fas fa-check" style="font-size:0.75rem;"></i>'; }
            if (label) { label.style.color = '#f97316'; }
        } else if (idx === activeIdx) {
            // Current/active step
            var activeBg = s === 'cancelled' ? '#ef4444' : 'var(--primary-color, #800020)';
            var activeBorder = s === 'cancelled' ? '#ef4444' : 'var(--primary-color, #800020)';
            if (dot) { dot.style.background = activeBg; dot.style.borderColor = activeBorder; dot.style.color = '#ffffff'; dot.innerHTML = String(idx + 1); dot.style.boxShadow = '0 0 0 4px rgba(128,0,32,0.15)'; }
            if (label) { label.style.color = s === 'cancelled' ? '#ef4444' : 'var(--primary-color, #800020)'; label.style.fontWeight = '800'; }
        } else {
            // Future step
            if (dot) { dot.style.background = '#f1f5f9'; dot.style.borderColor = '#e2e8f0'; dot.style.color = '#94a3b8'; dot.style.boxShadow = 'none'; dot.innerHTML = String(idx + 1); }
            if (label) { label.style.color = '#94a3b8'; label.style.fontWeight = '700'; }
        }
    });

    // Update connectors — turn orange for completed segments
    var connectors = document.querySelectorAll('#ovProcessWorkflow .proc-connector');
    connectors.forEach(function(conn, idx) {
        conn.style.background = idx < activeIdx ? '#f97316' : '#e2e8f0';
    });

    // Update status description
    var descEl = document.getElementById('ovProcessStatusDesc');
    if (descEl) {
        descEl.innerHTML = '<i class="fas fa-info-circle" style="color: var(--primary-color, #800020); margin-right: 6px;"></i>' + desc;
    }
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
    document.querySelectorAll('#bookingDetailModal .mtab-pane-pro').forEach(function(p) { 
        p.classList.remove('active'); 
        p.style.display = 'none';
    });
    document.querySelectorAll('#bookingDetailModal .mtab-btn-pro').forEach(function(b) { 
        b.classList.remove('active');
        b.style.borderBottomColor = 'transparent';
        b.style.color = '#64748b';
    });
    var pane = document.getElementById('btab-' + tabId);
    if (pane) {
        pane.classList.add('active');
        pane.style.display = 'flex';
    }
    
    var activeBtn = targetEl || document.querySelector(`#bookingDetailModal .mtab-btn-pro[data-tab="${tabId}"]`) || (typeof event !== 'undefined' ? event?.currentTarget : null);
    if (activeBtn) {
        activeBtn.classList.add('active');
        activeBtn.style.borderBottomColor = '#ea580c';
        activeBtn.style.color = '#ea580c';
    }

    if (tabId === 'chat' && typeof currentBookingId !== 'undefined' && currentBookingId) {
        // Clear unread badge on tab
        var chatBadge = document.getElementById('modalChatTabBadge');
        if (chatBadge) chatBadge.style.display = 'none';

        // Clear unread badge on table row
        var rowEl = document.getElementById('booking-row-' + currentBookingId);
        if (rowEl) {
            rowEl.dataset.unreadChat = '0';
            var rowBadge = rowEl.querySelector('span[title="Unread Consultation Messages"]');
            if (rowBadge) rowBadge.remove();
        }

        // Load messages if online view is active
        var onlineView = document.getElementById('modalChatOnlineView');
        if (onlineView && onlineView.style.display !== 'none') {
            loadBookingMessages(currentBookingId);
        }
    } else if (tabId === 'preparation' && typeof currentBookingId !== 'undefined' && currentBookingId) {
        if (typeof window.loadBookingTasks === 'function') {
            window.loadBookingTasks(currentBookingId);
        }
    } else if (tabId === 'activity' && typeof currentBookingId !== 'undefined' && currentBookingId) {
        if (typeof window.loadBookingHistory === 'function') {
            window.loadBookingHistory(currentBookingId);
        }
    }
}

function configureBookingTabs(data, context) {
    context = context || {};
    const sourceVal = (data?.source || '').toString().toLowerCase();
    const sourceKindVal = (data?.sourceKind || '').toString().toLowerCase();
    const isManual = (typeof context.isManual !== 'undefined') 
        ? Boolean(context.isManual) 
        : (sourceKindVal === 'manual' || data?.isWalkin === 'true' || data?.isManual === 'true' || sourceVal.includes('walk') || sourceVal.includes('manual'));
    const hasKyc = (typeof context.hasKycRecord !== 'undefined')
        ? Boolean(context.hasKycRecord)
        : (data?.hasKycRecord === 'true' || data?.isVerified === 'true');
    const hasContract = (typeof context.hasContractRecord !== 'undefined')
        ? Boolean(context.hasContractRecord)
        : (data?.hasContractRecord === 'true' || Boolean(data?.contractId));

    const visibleTabs = {
        overview: true,
        customer: true,
        services: true,
        chat: true,
        verification: !isManual && hasKyc,
        contract: !isManual && hasContract,
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
    const activeTab = activeButton?.dataset?.tab;
    if (activeTab && !visibleTabs[activeTab]) {
        const fallbackButton = document.getElementById('tabBtnOverview');
        switchBookingTab('overview', fallbackButton);
    }
}

window.openQuotationWorkspace = function(bookingId) {
    window.location.href = `/caterer/bookings/${bookingId}/quotation`;
};

function renderOverviewWorkspace(data, context) {
    if (!data) return;
    context = context || {};
    const status = (data.status || '').toLowerCase();
    const sourceVal = (data.source || '').toString().toLowerCase();
    const sourceKindVal = (data.sourceKind || '').toString().toLowerCase();
    const isManual = (typeof context.isManual !== 'undefined') 
        ? Boolean(context.isManual) 
        : (sourceKindVal === 'manual' || data.isWalkin === 'true' || data.isManual === 'true' || sourceVal.includes('walk') || sourceVal.includes('manual'));
    const isFoodOrder = data.isFoodOrder === 'true' || data.isFoodOrder === true;
    const total = Math.max(parseFloat(data.totalRawAmount) || 0, 0);
    const cleanId = data.id;

    // Missing info check
    const missing = [];
    const openEdit = 'window.openEditBookingModal()';
    const addAttention = (label, actionLabel = 'Edit details') => missing.push(`<div style="display:flex; justify-content:space-between; align-items:center; padding:4px 0;"><span><i class="fas fa-exclamation-circle" style="color:#d97706; margin-right:6px;"></i> ${label}</span><button type="button" onclick="${openEdit}" style="background:none; border:none; color:#b45309; font-weight:700; cursor:pointer; text-decoration:underline;">${actionLabel}</button></div>`);

    if (!data.venue || data.venue === 'Not specified') addAttention('Venue address not specified', 'Set venue');
    if (!Number(data.guestCount)) addAttention('Guest count not set', 'Set pax');
    if (!data.eventDate) addAttention('Event date not set', 'Set date');
    if (status === 'inquiry' && total <= 0) addAttention('Quotation not prepared yet', 'Prepare quote');

    const attBox = document.getElementById('modalOverviewAttentionBox');
    const attList = document.getElementById('modalOverviewAttentionList');
    if (attBox && attList) {
        if (missing.length > 0) {
            attBox.style.display = 'block';
            attList.innerHTML = missing.join('');
        } else {
            attBox.style.display = 'none';
        }
    }

    // Dynamic Source + Status primary action matrix
    let primaryTitle = 'Booking Confirmed & Ready for Preparation';
    let primaryDesc = 'Review event schedule and confirmed requirements before starting preparation.';
    let primaryBtnText = 'Start Preparation';
    let primaryBtnAction = `window.updateBookingStage(${cleanId}, 'preparing')`;
    let primaryEyebrow = isManual ? 'MANUAL BOOKING ADVISORY' : 'ONLINE BOOKING ADVISORY';

    if (status === 'cancelled' || status === 'canceled' || status === 'rejected') {
        primaryTitle = 'Booking Cancelled';
        primaryDesc = 'This booking is closed. Use Archive Booking below to remove it from your active list.';
        primaryBtnText = '';
        primaryBtnAction = '';
    } else if (status === 'completed') {
        primaryTitle = 'Event Completed';
        primaryDesc = 'All services for this event have been fulfilled. Use Archive Booking below to move it out of your active list.';
        primaryBtnText = '';
        primaryBtnAction = '';
    } else if (isManual) {
        // Manual booking workflow
        if (status === 'draft' || status === 'inquiry') {
            primaryTitle = 'Manual Booking: Draft / Inquiry';
            primaryDesc = 'Record payment from customer or edit details to confirm reservation.';
            primaryBtnText = 'Record Payment';
            primaryBtnAction = 'openRecordPaymentModal()';
        } else if (status === 'pending') {
            primaryTitle = 'Manual Booking: Review & Confirm';
            primaryDesc = 'Verify customer, event details, and selected services before confirming.';
            primaryBtnText = 'Confirm Booking';
            primaryBtnAction = `window.confirmAcceptBooking(${cleanId}, false, false, ${data.isPackage === 'true'})`;
        } else if (status === 'confirmed') {
            primaryTitle = 'Manual Booking: Confirmed & Ready';
            primaryDesc = 'Booking is confirmed. Proceed to food and event preparation.';
            primaryBtnText = 'Start Preparation';
            primaryBtnAction = `window.updateBookingStage(${cleanId}, 'preparing')`;
        } else if (status === 'preparing') {
            primaryTitle = 'Manual Booking: Preparation Ongoing';
            primaryDesc = 'Check off food prep, staffing, and equipment checklist items.';
            primaryBtnText = 'Open Checklist';
            primaryBtnAction = `switchBookingTab('preparation', document.getElementById('tabBtnPreparation'))`;
        } else if (status === 'ready_for_delivery') {
            primaryTitle = isFoodOrder ? 'Order Ready for Delivery' : 'Catering Ready for Event Service';
            primaryDesc = isFoodOrder ? 'Items prepared. Dispatch delivery team when ready.' : 'Food and equipment are prepared. Send the catering team to the venue when ready.';
            primaryBtnText = isFoodOrder ? 'Out for Delivery' : 'Depart for Venue';
            primaryBtnAction = `window.updateBookingStage(${cleanId}, 'on_the_way')`;
        } else if (status === 'ready_for_pickup') {
            primaryTitle = isFoodOrder ? 'Order Ready for Customer Pickup' : 'Catering Ready for Customer Collection';
            primaryDesc = isFoodOrder ? 'Items are ready. Mark picked up when customer collects.' : 'The catering booking is ready. Mark collected when the customer arrives.';
            primaryBtnText = isFoodOrder ? 'Mark Picked Up' : 'Mark Collected';
            primaryBtnAction = `window.confirmCompleteBooking(${cleanId})`;
        } else if (status === 'on_the_way') {
            primaryTitle = isFoodOrder ? 'Order in Transit to Venue' : 'Catering Team En Route';
            primaryDesc = isFoodOrder ? 'Delivery team is en route.' : 'The catering team is on the way to the event venue.';
            primaryBtnText = isFoodOrder ? 'Mark Arrived' : 'Mark Arrived at Venue';
            primaryBtnAction = `window.updateBookingStage(${cleanId}, 'arrived')`;
        } else if (status === 'arrived') {
            primaryTitle = isFoodOrder ? 'Order Arrived at Venue' : 'Catering Team at Venue';
            primaryDesc = isFoodOrder ? 'The delivery has arrived at the venue.' : 'Set up the catering stations and prepare for service.';
            primaryBtnText = isFoodOrder ? 'Confirm Arrival' : 'Start Event Setup';
            primaryBtnAction = `window.updateBookingStage(${cleanId}, 'setup_ongoing')`;
        } else if (status === 'setup_ongoing' || status === 'in_progress') {
            primaryTitle = 'Event Service Ongoing';
            primaryDesc = 'On-site event service in progress. Mark completed when finished.';
            primaryBtnText = isFoodOrder ? 'Mark as Completed' : 'Complete Event';
            primaryBtnAction = `window.confirmCompleteBooking(${cleanId})`;
        }
    } else {
        // Online booking workflow
        if (status === 'inquiry') {
            primaryTitle = 'Customer Submitted Booking Inquiry';
            primaryDesc = 'The customer is waiting for a quotation before confirming.';
            primaryBtnText = 'Prepare Quotation';
            primaryBtnAction = `window.openQuotationWorkspace(${cleanId})`;
        } else if (status === 'pending_quotation') {
            primaryTitle = 'Quotation Sent to Customer';
            primaryDesc = 'Quotation sent. Awaiting customer review and approval.';
            primaryBtnText = 'View Quotation';
            primaryBtnAction = `window.location.href='/caterer/bookings/${cleanId}/quotation'`;
        } else if (status === 'awaiting_caterer') {
            primaryTitle = 'Customer Accepted Quotation';
            primaryDesc = 'Sign the service agreement to finalize customer booking.';
            primaryBtnText = 'Sign Agreement';
            primaryBtnAction = `window.openIframeModal('/caterer/bookings/${cleanId}/sign?modal=true', 'Sign Service Agreement')`;
        } else if (status === 'awaiting_customer') {
            primaryTitle = 'Awaiting Customer Signature';
            primaryDesc = 'Customer needs to sign the agreement to proceed.';
            primaryBtnText = '';
            primaryBtnAction = '';
        } else if (status === 'pending' || status === 'awaiting_payment' || status === 'pending_payment') {
            const ps = (data.paymentStatus || '').toLowerCase();
            const underReview = data.isUnderReview === 'true' || ['proof_submitted', 'cash_payment_requested', 'pending_verification'].includes(ps) || Boolean(data.proofUrl);
            if (underReview) {
                if (ps === 'cash_payment_requested') {
                    primaryTitle = 'Customer Requested Cash Payment';
                    primaryDesc = 'Confirm only after you have physically received the cash payment.';
                    primaryBtnText = 'Confirm Cash Received';
                    primaryBtnAction = `window.confirmCashPayment(${cleanId})`;
                } else {
                    primaryTitle = 'Customer Submitted Payment Proof';
                    primaryDesc = 'Verify payment receipt and confirm booking. Deposit verification secures the booking and allows preparation.';
                    primaryBtnText = 'Verify & Confirm';
                    primaryBtnAction = `window.verifyPayment(${cleanId}, false)`;
                }
            } else {
                primaryTitle = 'Payment Required';
                primaryDesc = 'Customer has not submitted payment yet. Share the payment link or wait for proof upload.';
                primaryBtnText = 'Copy Payment Link';
                primaryBtnAction = `window.copyInvoiceLink('${cleanId}')`;
            }
        } else if (status === 'confirmed') {
            if (data.paymentStatus === 'balance_proof_submitted') {
                primaryTitle = 'Customer Submitted Balance Proof';
                primaryDesc = 'Customer uploaded remaining balance proof (GCash/Bank). Verify receipt to mark Fully Paid.';
                primaryBtnText = 'Verify Balance Proof';
                primaryBtnAction = `window.verifyPayment(${cleanId}, true)`;
            } else if (data.paymentStatus === 'cash_balance_requested') {
                primaryTitle = 'Customer Requested Cash for Balance';
                primaryDesc = 'Confirm only after you have physically received the remaining cash payment.';
                primaryBtnText = 'Confirm Cash Balance';
                primaryBtnAction = `window.confirmCashPayment(${cleanId})`;
            } else {
                const remBal = Math.max(total - Math.max(parseFloat(data.amountPaid) || 0, 0), 0);
                if (remBal > 0.009) {
                    primaryTitle = 'Outstanding Balance Remaining';
                    primaryDesc = 'Customer may pay via GCash, Bank, or Cash. Record payment if already received, or share the payment link.';
                    primaryBtnText = 'Record / Settle Balance';
                    primaryBtnAction = `window.openBalanceSettlement('${cleanId}')`;
                } else {
                    primaryTitle = 'Booking Confirmed & Ready for Preparation';
                    primaryDesc = 'Required deposit has been verified. The booking is secured and preparation can begin.';
                    primaryBtnText = 'Start Preparation';
                    primaryBtnAction = `window.updateBookingStage(${cleanId}, 'preparing')`;
                }
            }
        } else if (status === 'preparing') {
            primaryTitle = 'Customer Booking: Preparation in Progress';
            primaryDesc = 'Track checklist items and kitchen readiness.';
            primaryBtnText = 'Open Checklist';
            primaryBtnAction = `switchBookingTab('preparation', document.getElementById('tabBtnPreparation'))`;
        } else if (status === 'ready_for_delivery') {
            primaryTitle = isFoodOrder ? 'Ready for Delivery' : 'Catering Ready for Event Service';
            primaryDesc = isFoodOrder ? 'Items prepared. Dispatch delivery team when ready.' : 'Food and equipment are prepared. Send the catering team to the venue when ready.';
            primaryBtnText = isFoodOrder ? 'Out for Delivery' : 'Depart for Venue';
            primaryBtnAction = `window.updateBookingStage(${cleanId}, 'on_the_way')`;
        } else if (status === 'ready_for_pickup') {
            primaryTitle = isFoodOrder ? 'Ready for Pickup' : 'Catering Ready for Customer Collection';
            primaryDesc = isFoodOrder ? 'Waiting for customer collection.' : 'The catering booking is ready. Mark collected when the customer arrives.';
            primaryBtnText = isFoodOrder ? 'Mark Picked Up' : 'Mark Collected';
            primaryBtnAction = `window.confirmCompleteBooking(${cleanId})`;
        } else if (status === 'on_the_way') {
            primaryTitle = isFoodOrder ? 'Order in Transit' : 'Catering Team En Route';
            primaryDesc = isFoodOrder ? 'Delivery team is en route to venue.' : 'The catering team is on the way to the event venue.';
            primaryBtnText = isFoodOrder ? 'Mark Arrived' : 'Mark Arrived at Venue';
            primaryBtnAction = `window.updateBookingStage(${cleanId}, 'arrived')`;
        } else if (status === 'arrived') {
            primaryTitle = isFoodOrder ? 'Order Arrived at Venue' : 'Catering Team at Venue';
            primaryDesc = isFoodOrder ? 'The delivery has arrived at the venue.' : 'Set up the catering stations and prepare for service.';
            primaryBtnText = isFoodOrder ? 'Confirm Arrival' : 'Start Event Setup';
            primaryBtnAction = `window.updateBookingStage(${cleanId}, 'setup_ongoing')`;
        } else if (status === 'setup_ongoing' || status === 'in_progress') {
            primaryTitle = 'Event Service Ongoing';
            primaryDesc = 'Event is in progress. Mark completed when finished.';
            primaryBtnText = isFoodOrder ? 'Mark as Completed' : 'Complete Event';
            primaryBtnAction = `window.confirmCompleteBooking(${cleanId})`;
        }
    }

    // Block Mark Completed in overview until remaining balance is fully settled
    const paidAmt = Math.max(parseFloat(data.amountPaid) || 0, 0);
    const isFullyPaidOverview = total > 0 && paidAmt >= (total - 0.009);
    if (String(primaryBtnAction || '').includes('confirmCompleteBooking') && !isFullyPaidOverview) {
        primaryTitle = 'Outstanding Balance Remaining';
        primaryDesc = 'Settle via GCash, Bank, or Cash before marking Completed. Record payment if already received.';
        primaryBtnText = 'Settle Remaining Balance First';
        primaryBtnAction = `window.openBalanceSettlement('${cleanId}')`;
    }

    const eyebrow = document.getElementById('modalOverviewActionEyebrow');
    if (eyebrow) eyebrow.innerHTML = `<i class="fas ${isManual ? 'fa-store' : 'fa-globe'}"></i> ${primaryEyebrow}`;
    const title = document.getElementById('modalOverviewActionTitle');
    if (title) title.innerText = primaryTitle;
    const desc = document.getElementById('modalOverviewActionDesc');
    if (desc) desc.innerText = primaryDesc;
    const btnWrap = document.getElementById('modalOverviewActionBtnWrap');
    if (btnWrap) {
        // Lifecycle Archive/Cancel live only in the footer — overview shows next operational step only
        const btnBg = String(primaryBtnAction || '').includes('openBalanceSettlement') ? '#ea580c' : '#16a34a';
        btnWrap.innerHTML = primaryBtnText ? `
            <button type="button" class="btn-primary overview-next-action-btn" style="background:${btnBg}; color:white; border:none; padding:8px 18px; border-radius:8px; font-weight:700; font-size:0.85rem; cursor:pointer; display:inline-flex; align-items:center; gap:6px; box-shadow:0 2px 6px rgba(0,0,0,0.15);" onclick="${primaryBtnAction}">
                ${primaryBtnText}
            </button>
        ` : '';
    }

    // Keep footer Cancel/Archive in sync with the same status used by the advisory
    const paidAmount = Math.max(parseFloat(data.amountPaid) || 0, 0);
    const balance = Math.max(parseFloat(data.balance) || (total - paidAmount), 0);
    const isFullyPaid = total > 0 && paidAmount >= total - 0.009 && balance <= 0.009;
    _syncFooterButtons(cleanId, status, isFullyPaid);
}

// ─── REALTIME BOOKING ACTION FEEDBACK ─────────────────────────────────────────
const BOOKING_ACTION_TOASTS = {
    preparing: 'Preparation started. Customer notified.',
    ready_for_delivery: 'Marked ready for delivery. Customer notified.',
    ready_for_pickup: 'Marked ready for pickup. Customer notified.',
    on_the_way: 'Out for delivery. Customer notified.',
    arrived: 'Marked arrived at venue. Customer notified.',
    setup_ongoing: 'Setup started. Customer notified.',
    in_progress: 'Event service started. Customer notified.',
    completed: 'Booking marked as Completed!',
    archive: 'Booking moved to archives.',
    verify_payment: 'Payment verified successfully!',
    verify_balance: 'Balance verified — booking is Fully Paid!',
    cash_received: 'Cash payment confirmed!',
    cancel: 'Booking successfully cancelled.',
    accept: 'Booking confirmed successfully!',
    copy_link: 'Payment link copied to clipboard!'
};

async function refreshBookingUiRealtime(bookingId, opts = {}) {
    const cleanId = String(bookingId || currentBookingId || '').replace(/\D/g, '');
    const {
        toast,
        toastType = 'success',
        newStatus = null,
        newPaymentStatus = null,
        closeModal = false,
        removeRow = false
    } = opts;

    if (toast && typeof window.showToast === 'function') {
        window.showToast(toast, toastType);
    }

    if (removeRow && cleanId) {
        const row = document.querySelector(`.view-details[data-id="${cleanId}"]`)?.closest('tr');
        if (row) row.remove();
    }

    let btn = cleanId ? document.querySelector(`.view-details[data-id="${cleanId}"]`) : null;
    if (btn) {
        if (newStatus) btn.dataset.status = newStatus;
        if (newPaymentStatus) btn.dataset.paymentStatus = newPaymentStatus;
        btn.dataset.workspaceHydrated = '';
    }

    if (closeModal) {
        if (typeof bk_closeBookingDetailModal === 'function') bk_closeBookingDetailModal();
        else if (typeof bk_closeModal === 'function') bk_closeModal('bookingDetailModal');
    }

    if (typeof window.refreshDashboardData === 'function') {
        try { window.refreshDashboardData(); } catch (e) {}
    }

    if (typeof window.refreshBookingsTable === 'function') {
        try { await window.refreshBookingsTable(); } catch (e) {}
    }

    if (!closeModal && !removeRow && cleanId) {
        const modal = document.getElementById('bookingDetailModal');
        btn = document.querySelector(`.view-details[data-id="${cleanId}"]`);
        if (modal && modal.classList.contains('active') && btn) {
            btn.dataset.workspaceHydrated = '';
            showBookingDetails(btn);
        } else if (newStatus && modal && modal.classList.contains('active')) {
            window.currentBookingStatus = newStatus;
            _syncFooterButtons(cleanId, newStatus);
        }
    }
}
window.refreshBookingUiRealtime = refreshBookingUiRealtime;

// ═══ BALANCE SETTLEMENT HELPER ═══
window.openBalanceSettlement = function(bookingId) {
    const cleanId = String(bookingId || currentBookingId || '').replace(/\D/g, '');
    const viewBtn = cleanId ? document.querySelector(`.view-details[data-id="${cleanId}"]`) : null;
    const ps = String(viewBtn?.dataset?.paymentStatus || '').toLowerCase();

    if (typeof window.switchBookingTab === 'function') {
        window.switchBookingTab('payment', document.getElementById('tabBtnPayment'));
    }

    setTimeout(function() {
        if (ps === 'balance_proof_submitted' && typeof window.verifyPayment === 'function') {
            window.verifyPayment(cleanId, true);
            return;
        }
        if (ps === 'cash_balance_requested' && typeof window.confirmCashPayment === 'function') {
            window.confirmCashPayment(cleanId);
            return;
        }
        if (typeof window.openRecordPaymentModal === 'function') {
            window.openRecordPaymentModal();
        }
    }, 180);
};

// ═══ RECORD PAYMENT MODAL LOGIC ═══
window.toggleRecordPaymentRefField = function() {
    const methodEl = document.getElementById('recPayMethod');
    const wrap = document.getElementById('recPayRefWrap');
    const refInput = document.getElementById('recPayRef');
    const reqMark = document.getElementById('recPayRefRequiredMark');
    if (!methodEl || !wrap || !refInput) return;

    const method = String(methodEl.value || 'Cash').toLowerCase();
    const needsRef = ['gcash', 'bank transfer', 'bank', 'maya', 'check'].includes(method);
    wrap.style.display = needsRef ? 'block' : 'none';
    refInput.required = needsRef;
    if (reqMark) reqMark.style.display = needsRef ? 'inline' : 'none';
    if (!needsRef) refInput.value = '';
};

window.openRecordPaymentModal = function() {
    const modal = document.getElementById('recordPaymentModal');
    if (!modal) return;

    const payBalEl = document.getElementById('payBalance') || document.getElementById('modalHeaderBalance');
    let balanceVal = 0;
    if (payBalEl) {
        const text = payBalEl.innerText.replace(/[^0-9.-]+/g, "");
        balanceVal = parseFloat(text) || 0;
    }

    const balNotice = document.getElementById('recPayBalanceNotice');
    if (balNotice) {
        balNotice.innerText = '₱' + balanceVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    const amountInput = document.getElementById('recPayAmount') || document.getElementById('payAmount');
    if (amountInput) {
        amountInput.value = balanceVal > 0 ? balanceVal : '';
    }

    const methodInput = document.getElementById('recPayMethod');
    if (methodInput) methodInput.value = 'Cash';

    const refInput = document.getElementById('recPayRef') || document.getElementById('payReference');
    if (refInput) refInput.value = '';
    const notesInput = document.getElementById('recPayNotes') || document.getElementById('payNotes');
    if (notesInput) notesInput.value = '';

    window.toggleRecordPaymentRefField();

    modal.style.zIndex = '10005';
    modal.style.display = 'flex';
    void modal.offsetHeight;
    modal.classList.add('active');

    if (amountInput) amountInput.focus();
};

window.closeRecordPaymentModal = function() {
    const modal = document.getElementById('recordPaymentModal');
    if (!modal) return;
    modal.classList.remove('active');
    setTimeout(() => {
        if (!modal.classList.contains('active')) {
            modal.style.display = 'none';
        }
    }, 250);
};

window.submitRecordPayment = async function(event) {
    if (event && event.preventDefault) event.preventDefault();
    if (event && event.stopPropagation) event.stopPropagation();

    const bookingId = String(currentBookingId || window.currentBookingId || '').replace(/\D/g, '');
    if (!bookingId) {
        if (window.showError) window.showError('No booking selected.');
        return false;
    }

    const amountInput = document.getElementById('recPayAmount') || document.getElementById('payAmount');
    const methodInput = document.getElementById('recPayMethod') || document.getElementById('payMethod');
    const refInput = document.getElementById('recPayRef') || document.getElementById('payReference');
    const notesInput = document.getElementById('recPayNotes') || document.getElementById('payNotes');

    const amount = parseFloat(amountInput?.value || 0);
    const method = methodInput?.value || 'Cash';
    const reference = (refInput?.value || '').trim();
    const notes = (notesInput?.value || '').trim();
    const methodL = String(method).toLowerCase();
    const needsRef = ['gcash', 'bank transfer', 'bank', 'maya', 'check'].includes(methodL);

    if (amount <= 0 || isNaN(amount)) {
        if (typeof window.showError === 'function') window.showError('Payment amount must be greater than zero.');
        else alert('Payment amount must be greater than zero.');
        return false;
    }
    if (needsRef && !reference) {
        if (typeof window.showError === 'function') window.showError('Reference number is required for GCash / Bank / Maya.');
        else alert('Reference number is required for GCash / Bank / Maya.');
        if (refInput) refInput.focus();
        return false;
    }

    const submitBtn = document.getElementById('btnSubmitRecPay') || event?.target?.querySelector?.('button[type="submit"]');
    const originalText = submitBtn ? submitBtn.innerHTML : 'Save Payment';
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    }

    try {
        const response = await fetch(`/caterer/api/bookings/${bookingId}/record-payment`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                amount: amount,
                payment_method: method,
                reference_number: reference,
                notes: notes
            })
        });

        let result = {};
        try { result = await response.json(); } catch (e) {}

        if (response.ok && (result.success || result.status === 'success')) {
            if (typeof window.showToast === 'function') {
                window.showToast(result.message || 'Payment recorded successfully', 'success');
            } else if (typeof window.showSuccess === 'function') {
                window.showSuccess(result.message || 'Payment recorded successfully');
            }

            const form = document.getElementById('recordPaymentForm');
            if (form) form.reset();
            window.closeRecordPaymentModal();

            await refreshBookingUiRealtime(bookingId, {
                newPaymentStatus: result.new_payment_status || null,
                closeModal: false
            });
        } else {
            const msg = (Array.isArray(result.detail) ? result.detail.map(d => d.msg || d).join(', ') : null)
                || result.detail || result.message || 'Failed to record payment.';
            if (typeof window.showError === 'function') window.showError(msg);
            else alert(msg);
        }
    } catch(err) {
        console.error('Error recording payment:', err);
        if (typeof window.showError === 'function') window.showError('An unexpected network error occurred.');
        else alert('An unexpected network error occurred.');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    }
    return false;
};


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
        firstBtn.style.borderBottomColor = '#ea580c';
        firstBtn.style.color = '#ea580c';
    }
}

// Global copy payment link function
// Global copy payment link function — customer payment page (deposit or remaining balance)
window.copyInvoiceLink = function(bookingId) {
    const cleanId = String(bookingId || currentBookingId || '').replace(/\D/g, '');
    if (!cleanId) {
        if (window.showError) window.showError('No booking selected.');
        return;
    }

    const viewBtn = document.querySelector(`.view-details[data-id="${cleanId}"]`);
    const total = Math.max(parseFloat(viewBtn?.dataset?.totalRawAmount) || 0, 0);
    const paid = Math.max(parseFloat(viewBtn?.dataset?.amountPaid) || 0, 0);
    const hasRemaining = total > 0 && paid < (total - 0.009);
    const path = hasRemaining
        ? `/bookings/step/payment/${cleanId}?balance=true`
        : `/bookings/step/payment/${cleanId}`;
    const url = window.location.origin + path;
    const toastMsg = hasRemaining
        ? 'Remaining balance payment link copied!'
        : 'Payment link copied to clipboard!';

    const onCopied = () => {
        if (window.showToast) window.showToast(toastMsg, 'success');
        else if (window.showSuccess) window.showSuccess(toastMsg);
        else alert(toastMsg);
    };
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(onCopied).catch(() => {
            if (window.showToast) window.showToast('Failed to copy payment link.', 'error');
            else alert('Failed to copy: ' + url);
        });
    } else {
        const el = document.createElement('textarea');
        el.value = url;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        onCopied();
    }
};

// ─── NEW: AUDIT HISTORY ──────────────────────────────────────────────────────

async function loadBookingHistory(bookingId) {
    const cleanId = String(bookingId || currentBookingId || '').replace(/\D/g, '');
    const container = document.getElementById('modalHistoryTimeline');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;padding:2rem;color:#94a3b8;">Loading activity...</div>';
    
    try {
        const res = await fetch(`/caterer/api/bookings/${cleanId}/history`);
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
        const cleanId = String(currentBookingId || '').replace(/\D/g, '');
        const data = await window.apiAction(`/caterer/api/bookings/${cleanId}/notes`, {
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
    const cleanId = String(bookingId || currentBookingId || '').replace(/\D/g, '');
    currentBookingIdForContract = cleanId;
    var body = document.getElementById('contractModalBody');
    if (!body) return;
    body.innerHTML = '<div style="text-align:center;padding:4rem;"><i class="fas fa-circle-notch fa-spin fa-3x" style="color:var(--primary-color);"></i></div>';
    bk_openModal('contractModal');
    fetch('/caterer/api/bookings/' + cleanId + '/contract/content')
        .then(function(r) { return r.text(); })
        .then(function(html) { body.innerHTML = html; })
        .catch(function() { body.innerHTML = '<p style="color:#ef4444;text-align:center;">Failed to load contract.</p>'; });
}

function closeContractModal() { bk_closeModal('contractModal'); }

function printContract(bookingId) {
    const cleanId = String(bookingId || currentBookingId || '').replace(/\D/g, '');
    var url = '/caterer/bookings/' + cleanId + '/contract';
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
    
    const cleanId = String(currentBookingId || '').replace(/\D/g, '');
    const data = await window.apiAction('/caterer/api/bookings/' + cleanId + '/set-due-date', {
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
        
        var btn = document.querySelector('.view-details[data-id="' + cleanId + '"]');
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
        const cleanId = String(currentBookingId || '').replace(/\D/g, '');
        const res = await fetch(`/caterer/api/bookings/${cleanId}/verify-proof`, { method: 'POST' });
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
            var result = await window.apiAction(url, { method: 'POST', muteToast: true });
            if (result && result.status === 'success') {
                await refreshBookingUiRealtime(bookingId, {
                    toast: isPayment ? BOOKING_ACTION_TOASTS.verify_payment : BOOKING_ACTION_TOASTS.accept,
                    newStatus: 'confirmed',
                    newPaymentStatus: isPayment ? 'paid' : null,
                    closeModal: false
                });
            }
        },
        confirmTitle, confirmBtn, 'success'
    );
}

let rejectionBookingId = null;

function confirmRejectBooking(bookingId) {
    rejectionBookingId = bookingId || currentBookingId || window.currentBookingId || null;
    const inputEl = document.getElementById('rejectReasonInput');
    if (inputEl) inputEl.value = '';
    bk_openModal('rejectReasonModal');
}

async function submitRejectionWithReason() {
    const targetId = rejectionBookingId || currentBookingId || window.currentBookingId;
    if (!targetId) {
        window.showToast('No booking selected to cancel.', 'error');
        return;
    }
    
    const reason = document.getElementById('rejectReasonInput').value.trim();
    if (!reason) {
        window.showToast('Please provide a reason for the cancellation.', 'error');
        return;
    }
    
    const btn = window.event ? (window.event.target.closest('button') || document.querySelector('#rejectReasonModal .btn-sm-danger')) : document.querySelector('#rejectReasonModal .btn-sm-danger');
    let originalText = '';
    if (btn) {
        originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cancelling...';
    }
    
    try {
        const data = await window.apiAction(`/caterer/bookings/${targetId}/reject`, {
            method: 'POST',
            body: JSON.stringify({ reason: reason })
        });
        
        if (data && (data.status === 'success' || data.success)) {
            await refreshBookingUiRealtime(targetId, {
                toast: BOOKING_ACTION_TOASTS.cancel,
                newStatus: 'cancelled',
                closeModal: true,
                removeRow: false
            });
            bk_closeModal('rejectReasonModal');
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}

function isBookingFullyPaidFromDom(bookingId) {
    const cleanId = String(bookingId || currentBookingId || '').replace(/\D/g, '');
    const viewBtn = cleanId ? document.querySelector(`.view-details[data-id="${cleanId}"]`) : null;
    const total = Math.max(parseFloat(viewBtn?.dataset?.totalRawAmount) || parseFloat(document.getElementById('modalHeaderTotal')?.dataset?.raw) || 0, 0);
    let paid = Math.max(parseFloat(viewBtn?.dataset?.amountPaid) || 0, 0);
    // Fallback: parse header paid text
    if (!paid) {
        const paidEl = document.getElementById('modalHeaderPaid');
        if (paidEl) paid = parseFloat(String(paidEl.innerText).replace(/[^0-9.-]+/g, '')) || 0;
    }
    let totalVal = total;
    if (!totalVal) {
        const totalEl = document.getElementById('modalHeaderTotal');
        if (totalEl) totalVal = parseFloat(String(totalEl.innerText).replace(/[^0-9.-]+/g, '')) || 0;
    }
    const balEl = document.getElementById('modalHeaderBalance');
    const bal = balEl ? (parseFloat(String(balEl.innerText).replace(/[^0-9.-]+/g, '')) || 0) : Math.max(totalVal - paid, 0);
    return totalVal > 0 && paid >= (totalVal - 0.009) && bal <= 0.009;
}

function confirmCompleteBooking(bookingId) {
    if (!isBookingFullyPaidFromDom(bookingId)) {
        window.showError('Cannot mark as Completed while there is still a remaining balance. Settle and verify the full payment first.');
        return;
    }

    window.showConfirm('Is the event finished and everything settled?',
        async function() {
            var result = await window.apiAction('/caterer/bookings/' + bookingId + '/update-status', { 
                method: 'POST', 
                body: JSON.stringify({status: 'completed'}),
                muteToast: true
            });

            if (result && result.status === 'success') {
                await refreshBookingUiRealtime(bookingId, {
                    toast: BOOKING_ACTION_TOASTS.completed,
                    newStatus: 'completed',
                    newPaymentStatus: 'paid'
                });
            }
        },
        'Mark as Completed?', 'Yes, Event Finished', 'success'
    );
}

window.validateAndProceed = function(bookingId, stage) {
    if (stage === 'ready_for_delivery' || stage === 'ready_for_pickup') {
        if (typeof window.requestReadyForDelivery === 'function') {
            window.requestReadyForDelivery(bookingId);
        } else {
            updateBookingStage(bookingId, stage);
        }
        return;
    }

    const proofBooking = document.getElementById('dispatchProofBookingId');
    const proofStage = document.getElementById('dispatchProofStage');
    if (proofBooking && proofStage) {
        proofBooking.value = bookingId;
        proofStage.value = stage;
        const img = document.getElementById('dispatchProofImage');
        if (img) img.value = '';
        bk_openModal('dispatchProofModal');
    } else {
        updateBookingStage(bookingId, stage);
    }
};

window.requestReadyForDelivery = async function(bookingId) {
    const cleanId = String(bookingId || currentBookingId || '').replace(/\D/g, '');
    if (!cleanId) return;

    // Keep preparation status in sync with the footer action
    try {
        await fetch('/caterer/api/bookings/' + cleanId + '/preparation-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify({ status: 'ready_for_delivery' })
        });
    } catch (e) {}

    updateBookingStage(cleanId, 'ready_for_delivery');
};

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
    if (String(bookingId) === String(currentBookingId) && ['completed', 'delivered'].includes(String(window.currentBookingStatus || '').toLowerCase())) {
        if (window.showToast) window.showToast('Completed bookings are locked.', 'error');
        return;
    }

    if (status === 'completed') {
        confirmCompleteBooking(bookingId);
        return;
    }

    const viewBtn = document.querySelector(`.view-details[data-id="${String(bookingId).replace(/\D/g, '')}"]`);
    const isFoodOrder = viewBtn?.dataset?.isFoodOrder === 'true';
    const labels = {
        'preparing': 'Start preparation for this event?',
        'ready_for_delivery': isFoodOrder ? 'Is the order packed and ready for delivery?' : 'Are the food and event equipment prepared and ready to be sent to the venue?',
        'ready_for_pickup': isFoodOrder ? 'Is the order ready for the customer to pick up?' : 'Is the catering booking ready for customer collection?',
        'on_the_way': isFoodOrder ? 'Is the team/rider currently in transit to the location?' : 'Has the catering team left for the event venue?',
        'arrived': isFoodOrder ? 'Has the order/team arrived at the venue?' : 'Has the catering team arrived at the event venue?',
        'setup_ongoing': 'Has the setup and food service started?',
        'in_progress': 'Has event service officially started?'
    };
    const titles = {
        'preparing': 'Start Preparation?',
        'ready_for_delivery': isFoodOrder ? 'Mark as Ready?' : 'Preparation Complete?',
        'ready_for_pickup': isFoodOrder ? 'Ready for Pickup?' : 'Ready for Collection?',
        'on_the_way': isFoodOrder ? 'Dispatch Order?' : 'Depart for Venue?',
        'arrived': isFoodOrder ? 'Order Arrived?' : 'Catering Team Arrived?',
        'setup_ongoing': 'Start Event Setup?',
        'in_progress': 'Start Event Service?'
    };

    window.showConfirm(labels[status] || 'Are you sure you want to proceed?',
        async function() {
            var result = await window.apiAction('/caterer/bookings/' + bookingId + '/update-status', { 
                method: 'POST', 
                body: JSON.stringify({ status: status }),
                muteToast: true
            });

            if (result && result.status === 'success') {
                await refreshBookingUiRealtime(bookingId, {
                    toast: BOOKING_ACTION_TOASTS[status] || 'Status updated successfully.',
                    newStatus: status
                });
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
                body: JSON.stringify({ reason: reason }),
                muteToast: true
            });
            if (result && result.status === 'success') {
                await refreshBookingUiRealtime(bookingId, {
                    toast: 'Notification sent to customer.',
                    newPaymentStatus: 'unpaid'
                });
            }
        },
        'Request New Proof?', 'Yes, Notify Customer', 'warning'
    );
}

function confirmArchiveBooking(bookingId) {
    const cleanId = String(bookingId || currentBookingId).replace(/\D/g, '') || String(bookingId);
    if (!cleanId) return;

    window.showConfirm(
        'This booking will be moved to the Archive Center and removed from your active bookings table. You can review, restore, or permanently delete it from Archives anytime.',
        async function() {
            try {
                const result = await window.apiAction('/caterer/bookings/' + cleanId + '/archive', {
                    method: 'POST',
                    muteToast: true
                });
                if (result && (result.status === 'success' || result.success)) {
                    await refreshBookingUiRealtime(cleanId, {
                        toast: BOOKING_ACTION_TOASTS.archive,
                        newStatus: 'archived',
                        closeModal: true,
                        removeRow: true
                    });
                }
            } catch (e) {
                console.error(e);
                if (window.showError) window.showError('Could not archive booking. Please try again.');
            }
        },
        'Archive Booking #' + cleanId, 'Yes, Archive', 'danger'
    );
}

function togglePackageAccordion(btn) {
    const accordion = btn.closest('.package-accordion');
    if (accordion) {
        accordion.classList.toggle('active');
    }
}

function verifyPayment(bookingId, isBalance) {
    const cleanId = String(bookingId || currentBookingId || window.currentBookingId).replace(/\D/g, '') || String(bookingId);
    if (!cleanId) return;

    var isBal = Boolean(isBalance);
    var title = isBal ? 'Verify Balance Payment Proof' : 'Verify Downpayment Proof';
    var msg = isBal 
        ? 'Have you checked and confirmed the customer’s uploaded balance payment receipt? This will mark the booking as FULLY PAID.' 
        : 'Have you verified the customer’s payment proof? This will confirm the booking.';

    window.showConfirm(msg,
        async function() {
            var url = '/caterer/payments/' + cleanId + '/confirm';
            var result = await window.apiAction(url, { method: 'POST', muteToast: true });
            if (result && (result.status === 'success' || result.success)) {
                await refreshBookingUiRealtime(cleanId, {
                    toast: isBal ? BOOKING_ACTION_TOASTS.verify_balance : BOOKING_ACTION_TOASTS.verify_payment,
                    newStatus: 'confirmed',
                    newPaymentStatus: isBal ? 'paid' : 'deposit_paid'
                });
            }
        },
        title, 'Yes, Verify & Accept', 'success'
    );
}

function confirmCashPayment(bookingId, customerName, amount, paymentStatus) {
    const cleanId = String(bookingId || currentBookingId || window.currentBookingId).replace(/\D/g, '') || String(bookingId);
    if (!cleanId) return;

    // Resolve amount from args, modal dataset, or 0 (backend will default)
    let amountVal = parseFloat(amount);
    if (!amountVal || isNaN(amountVal)) {
        const btn = document.querySelector(`.view-details[data-id="${cleanId}"]`);
        if (btn) {
            amountVal = parseFloat(btn.dataset.pendingAmount) || parseFloat(btn.dataset.verifiedPaid) || 0;
            const total = parseFloat(btn.dataset.totalRawAmount) || 0;
            const paid = parseFloat(btn.dataset.amountPaid) || 0;
            if (!amountVal) amountVal = Math.max(total - paid, 0) || total;
        }
    }
    if (!amountVal || isNaN(amountVal)) amountVal = 0;

    const today = new Date().toISOString().slice(0, 10);
    const label = customerName ? ` from ${customerName}` : '';

    window.showConfirm(
        `Confirm that you have physically received ₱${Number(amountVal).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} cash${label}?`,
        async function() {
            var result = await window.apiAction('/caterer/payments/' + cleanId + '/confirm-cash', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    amount_received: amountVal,
                    payment_date: today,
                    notes: ''
                }),
                muteToast: true
            });
            if (result && (result.status === 'success' || result.success)) {
                await refreshBookingUiRealtime(cleanId, {
                    toast: BOOKING_ACTION_TOASTS.cash_received,
                    newStatus: 'confirmed',
                    newPaymentStatus: 'paid'
                });
            }
        },
        'Confirm Cash Payment', 'Yes, Cash Received', 'success'
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
window.togglePackageAccordion = togglePackageAccordion;
window.confirmAcceptBooking = confirmAcceptBooking;
window.confirmRejectBooking = confirmRejectBooking;
window.confirmCompleteBooking = confirmCompleteBooking;
window.updateBookingStage = updateBookingStage;
window.requestNewProof = requestNewProof;
window.verifyPayment = verifyPayment;
window.confirmCashPayment = confirmCashPayment;
window.confirmArchiveBooking = confirmArchiveBooking;
window.requestReadyForDelivery = window.requestReadyForDelivery;

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

/* ─── PREPARATION STATUS TRACKER ─── */

window._prepCache = { status: 'not_started', progress: 0, label: 'Not Started', statuses: [] };

const PREP_PROGRESS_FALLBACK = {
    not_started: 0,
    preparing: 40,
    ready_for_delivery: 60,
    setup_in_progress: 80,
    ready_for_event: 90,
    completed: 100
};

function _prepFormatUpdated(iso) {
    if (!iso) return '—';
    try {
        const d = new Date(iso);
        if (isNaN(d.getTime())) return '—';
        return d.toLocaleString('en-US', {
            month: 'long', day: 'numeric', year: 'numeric',
            hour: 'numeric', minute: '2-digit'
        });
    } catch (e) { return '—'; }
}

function _renderPrepStatusUI(prep) {
    if (!prep) return;
    window._prepCache = Object.assign({}, window._prepCache, prep);

    const badge = document.getElementById('prepCurrentStatusBadge');
    const pctEl = document.getElementById('prepProgressPercent');
    const bar = document.getElementById('prepProgressBar');
    const updated = document.getElementById('prepLastUpdated');

    const emoji = prep.emoji || '⚪';
    const label = prep.label || 'Not Started';
    const progress = (prep.progress != null) ? prep.progress : (PREP_PROGRESS_FALLBACK[prep.status] || 0);

    if (badge) {
        badge.innerText = emoji + ' ' + label;
        badge.style.background = prep.bg || '#f1f5f9';
        badge.style.color = prep.color || '#475569';
    }
    if (pctEl) pctEl.innerText = progress + '%';
    if (bar) bar.style.width = progress + '%';
    if (updated) updated.innerText = _prepFormatUpdated(prep.last_updated);
}

async function loadBookingTasks(bookingId) {
    // Kept name for compatibility with existing callers — loads preparation STATUS only
    const cleanId = String(bookingId || currentBookingId || '').replace(/\D/g, '');
    if (!cleanId) return;

    const badge = document.getElementById('prepCurrentStatusBadge');
    if (badge) badge.innerText = 'Loading…';

    try {
        const res = await fetch('/caterer/api/bookings/' + cleanId + '/preparation', {
            headers: { 'Accept': 'application/json' }
        });
        if (!res.ok) throw new Error('Failed to load preparation status');
        const prep = await res.json();
        _renderPrepStatusUI(prep);
    } catch (err) {
        console.error('Error loading preparation status:', err);
        if (badge) badge.innerText = '⚪ Not Started';
    }
}

window.openPrepStatusModal = function() {
    if (['completed', 'delivered'].includes(String(window.currentBookingStatus || '').toLowerCase())) {
        if (window.showToast) window.showToast('Completed bookings are locked.', 'error');
        return;
    }

    const modal = document.getElementById('prepStatusModal');
    const list = document.getElementById('prepStatusOptions');
    if (!modal || !list) return;

    const current = (window._prepCache && window._prepCache.status) || 'not_started';
    const statuses = (window._prepCache && window._prepCache.statuses && window._prepCache.statuses.length)
        ? window._prepCache.statuses
        : [
            { key: 'not_started', label: 'Not Started', progress: 0, emoji: '⚪' },
            { key: 'preparing', label: 'Preparing', progress: 40, emoji: '🟡' },
            { key: 'ready_for_delivery', label: 'Preparation Complete', progress: 60, emoji: '🔵' },
            { key: 'setup_in_progress', label: 'Setup in Progress', progress: 80, emoji: '🟠' },
            { key: 'ready_for_event', label: 'Ready for Event', progress: 90, emoji: '🟣' },
            { key: 'completed', label: 'Completed', progress: 100, emoji: '🟢' }
        ];

    list.innerHTML = statuses.map(function(s) {
        const active = s.key === current ? ' active' : '';
        return '<button type="button" class="prep-status-option' + active + '" onclick="selectPrepStatus(\'' + s.key + '\')">' +
            '<span>' + (s.emoji || '') + ' ' + s.label + '</span>' +
            '<span class="pct">' + s.progress + '%</span></button>';
    }).join('');

    if (typeof bk_openModal === 'function') bk_openModal('prepStatusModal');
    else modal.style.display = 'flex';
};

window.closePrepStatusModal = function() {
    if (typeof bk_closeModal === 'function') bk_closeModal('prepStatusModal');
    else {
        const modal = document.getElementById('prepStatusModal');
        if (modal) modal.style.display = 'none';
    }
};

window.selectPrepStatus = async function(statusKey) {
    const cleanId = String(currentBookingId || '').replace(/\D/g, '');
    if (!cleanId || !statusKey) return;
    if (['completed', 'delivered'].includes(String(window.currentBookingStatus || '').toLowerCase())) {
        if (window.showToast) window.showToast('Completed bookings are locked.', 'error');
        closePrepStatusModal();
        return;
    }

    try {
        const res = await fetch('/caterer/api/bookings/' + cleanId + '/preparation-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify({ status: statusKey })
        });
        const data = await res.json().catch(function() { return {}; });
        if (!res.ok) throw new Error(data.detail || 'Failed to update preparation status');

        if (data.preparation) _renderPrepStatusUI(data.preparation);
        if (data.booking_status) window.currentBookingStatus = data.booking_status;

        closePrepStatusModal();
        if (window.showToast) window.showToast(data.message || 'Preparation status updated.', 'success');

        if (window.refreshBookingsTable) window.refreshBookingsTable();
        setTimeout(function() {
            const btn = document.querySelector('.view-details[data-id="' + cleanId + '"]');
            const modalEl = document.getElementById('bookingDetailModal');
            if (btn && modalEl && modalEl.classList.contains('active')) {
                if (data.booking_status) btn.dataset.status = data.booking_status;
                if (typeof showBookingDetails === 'function') showBookingDetails(btn);
            }
        }, 400);
    } catch (err) {
        if (window.showError) window.showError(err.message || 'Error updating status');
    }
};

window.requestReadyForDelivery = async function(bookingId) {
    const cleanId = String(bookingId || currentBookingId || '').replace(/\D/g, '');
    if (!cleanId) return;

    try {
        await fetch('/caterer/api/bookings/' + cleanId + '/preparation-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify({ status: 'ready_for_delivery' })
        });
    } catch (e) {}

    updateBookingStage(cleanId, 'ready_for_delivery');
};

// Compatibility stubs (old checklist helpers no longer used by Preparation tab)
async function addNewCustomTask() { openPrepStatusModal(); }
async function addBookingTaskFromInput() { openPrepStatusModal(); }
async function toggleTaskStatus() {}
async function deleteTask() {}

window.loadBookingTasks = loadBookingTasks;
window.addNewCustomTask = addNewCustomTask;
window.toggleTaskStatus = toggleTaskStatus;
window.deleteTask = deleteTask;

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
            if (cells.length < 6) return;
            
            // Clean up innerText by replacing newlines with spaces and trimming
            const clean = (text) => text.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
            
            const idText = clean(cells[0].innerText);
            const customerRef = clean(cells[1].innerText);
            const eventInfo = clean(cells[2].innerText);
            const dateTime = clean(cells[3].innerText);
            const statusBilling = clean(cells[4].innerText);
            
            data.push({ idText, customerRef, eventInfo, dateTime, statusBilling });
        } catch(e) {
            console.error('Row parsing error', e);
        }
    });

    if (data.length === 0) return;

    if (format === 'excel') {
        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += "Booking ID,Customer Ref,Event,Date & Time,Status & Billing\n";
        
        data.forEach(d => {
            const escapeCSV = (val) => '"' + String(val).replace(/"/g, '""') + '"';
            const rowStr = [d.idText, d.customerRef, d.eventInfo, d.dateTime, d.statusBilling].map(escapeCSV).join(",");
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
                    <th width="12%">Booking Ref</th>
                    <th width="18%">Customer Ref</th>
                    <th width="22%">Event Info</th>
                    <th width="18%">Date & Time</th>
                    <th width="30%">Status & Billing</th>
                </tr>
            </thead>
            <tbody>
        `;
        
        data.forEach(d => {
            html += `<tr>
                <td><strong>${d.idText}</strong></td>
                <td>${d.customerRef}</td>
                <td>${d.eventInfo}</td>
                <td>${d.dateTime}</td>
                <td class="status">${d.statusBilling}</td>
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
    const formBookingId = document.getElementById('modalChatBookingId');
    if (formBookingId) formBookingId.value = bookingId;
    
    if (!container) return;
    
    container.innerHTML = '<div style="text-align:center;padding:2.5rem;color:#94a3b8;"><i class="fas fa-spinner fa-spin fa-2x"></i><p style="margin-top:0.5rem;font-size:0.85rem;">Loading consultation messages...</p></div>';
    
    try {
        const res = await fetch(`/bookings/${bookingId}/messages`, {
            headers: { 'Accept': 'application/json' }
        });
        const result = await res.json();
        
        if (result.status === 'success') {
            // Remove unread chat badge from table row since messages are now read
            const rowEl = document.getElementById(`booking-row-${bookingId}`);
            if (rowEl) {
                rowEl.dataset.unreadChat = '0';
                const badge = rowEl.querySelector('span[title="Unread Consultation Messages"]');
                if (badge) badge.remove();
            }
            // Remove unread badge from chat tab in modal
            const chatBadge = document.getElementById('modalChatTabBadge');
            if (chatBadge) chatBadge.style.display = 'none';

            const messages = result.messages || [];
            if (messages.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 3.5rem 1.5rem; color: #64748b; margin: auto;">
                        <div style="width: 56px; height: 56px; border-radius: 50%; background: #fff7ed; color: #ea580c; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; margin: 0 auto 0.85rem; border: 1px solid #fed7aa;">
                            <i class="fas fa-comments"></i>
                        </div>
                        <h4 style="margin: 0 0 0.35rem; font-size: 1.05rem; font-weight: 850; color: #0f172a;">No messages yet</h4>
                        <p style="margin: 0; font-size: 0.85rem; color: #64748b; max-width: 320px; margin: 0 auto;">Start a conversation with the customer about their booking.</p>
                    </div>
                `;
            } else {
                container.innerHTML = messages.map(msg => {
                    const isMe = msg.is_me;
                    const justify = isMe ? 'flex-end' : 'flex-start';
                    const bg = isMe ? 'var(--primary-color, #ea580c)' : '#ffffff';
                    const color = isMe ? '#ffffff' : '#0f172a';
                    const border = isMe ? 'none' : '1px solid #e2e8f0';
                    const radius = isMe ? '16px 16px 4px 16px' : '16px 16px 16px 4px';
                    const senderLabel = isMe ? 'You (Caterer)' : (msg.sender_name || 'Customer');
                    const labelColor = isMe ? 'rgba(255,255,255,0.85)' : '#ea580c';
                    
                    let attachmentHtml = '';
                    if (msg.attachment_url) {
                        const isImg = /\.(jpg|jpeg|png|webp|gif)$/i.test(msg.attachment_url);
                        if (isImg) {
                            attachmentHtml = `
                                <div style="margin-top: 8px;">
                                    <a href="${msg.attachment_url}" target="_blank" style="display: block;">
                                        <img src="${msg.attachment_url}" style="max-width: 100%; max-height: 180px; border-radius: 8px; border: 1px solid rgba(0,0,0,0.1); object-fit: cover;" alt="Attachment">
                                    </a>
                                </div>
                            `;
                        } else {
                            attachmentHtml = `
                                <div style="margin-top: 8px;">
                                    <a href="${msg.attachment_url}" target="_blank" style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; background: ${isMe ? 'rgba(255,255,255,0.2)' : '#f1f5f9'}; border-radius: 6px; color: ${isMe ? '#ffffff' : '#0f172a'}; font-size: 0.75rem; text-decoration: none; font-weight: 700;">
                                        <i class="fas fa-file-download"></i> View Attached Document
                                    </a>
                                </div>
                            `;
                        }
                    }
                    
                    const seenStatusHtml = isMe 
                        ? (msg.is_read ? '<span style="color: #60a5fa; font-weight: 700; margin-left: 6px;"><i class="fas fa-check-double"></i> Seen</span>' : '<span style="color: #cbd5e1; margin-left: 6px;"><i class="fas fa-check"></i> Sent</span>') 
                        : '';

                    return `
                        <div style="display: flex; justify-content: ${justify}; width: 100%;">
                            <div style="max-width: 78%; display: flex; flex-direction: column; align-items: ${isMe ? 'flex-end' : 'flex-start'};">
                                <span style="font-size: 0.7rem; font-weight: 800; color: ${labelColor}; margin-bottom: 3px; display: inline-flex; align-items: center; gap: 4px;">
                                    <i class="fas ${isMe ? 'fa-store' : 'fa-user'}"></i> ${senderLabel}
                                </span>
                                <div style="background: ${bg}; color: ${color}; border: ${border}; padding: 0.75rem 1rem; border-radius: ${radius}; box-shadow: 0 1px 3px rgba(0,0,0,0.05); font-size: 0.85rem; line-height: 1.45; word-break: break-word;">
                                    ${msg.message ? `<div>${msg.message}</div>` : ''}
                                    ${attachmentHtml}
                                </div>
                                <div style="font-size: 0.68rem; color: #94a3b8; margin-top: 3px; text-align: ${isMe ? 'right' : 'left'};">
                                    ${msg.created_at || ''}${seenStatusHtml}
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
                container.scrollTop = container.scrollHeight;
            }
        } else {
            container.innerHTML = `<div style="text-align:center;padding:2rem;color:#ef4444;">${result.message || 'Failed to load messages.'}</div>`;
        }
    } catch (err) {
        console.error('Error loading consultation messages:', err);
        container.innerHTML = '<div style="text-align:center;padding:2rem;color:#ef4444;">Failed to connect to consultation thread.</div>';
    }
}

function handleModalChatFileSelect(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const maxSizeMb = Number(window.MAX_UPLOAD_SIZE_MB) || 5;
        if (file.size > maxSizeMb * 1024 * 1024) {
            alert(`File size exceeds the ${maxSizeMb}MB limit. Please choose a smaller file.`);
            input.value = '';
            return;
        }
        const nameEl = document.getElementById('modalChatAttachmentName');
        if (nameEl) {
            nameEl.innerHTML = `<i class="fas fa-paperclip"></i> ${file.name}`;
        }
        const previewEl = document.getElementById('modalChatAttachmentPreview');
        if (previewEl) previewEl.style.display = 'flex';
    }
}

function clearModalChatAttachment() {
    const input = document.getElementById('modalChatFileInput');
    if (input) input.value = '';
    const previewEl = document.getElementById('modalChatAttachmentPreview');
    if (previewEl) previewEl.style.display = 'none';
}

async function sendBookingChatMessage(e) {
    e.preventDefault();
    const form = document.getElementById('modalChatForm');
    const input = document.getElementById('modalChatMessageInput');
    const fileInput = document.getElementById('modalChatFileInput');
    const btn = document.getElementById('modalChatSubmitBtn');
    const bookingId = currentBookingId || document.getElementById('modalChatBookingId')?.value;

    if (!bookingId) return;

    const messageText = (input?.value || '').trim();
    const hasFile = fileInput?.files && fileInput.files.length > 0;

    if (!messageText && !hasFile) return;

    const originalBtnHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    const formData = new FormData(form);
    if (!formData.get('booking_id')) {
        formData.append('booking_id', bookingId);
    }

    try {
        const res = await fetch(`/bookings/${bookingId}/messages`, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        });
        const result = await res.json();
        if (result.success || result.status === 'success') {
            if (input) input.value = '';
            clearModalChatAttachment();
            loadBookingMessages(bookingId);
        } else {
            alert(result.message || 'Failed to send message.');
        }
    } catch (err) {
        console.error('Error sending message:', err);
        alert('Connection error while sending message.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalBtnHtml;
    }
}

// Global WebSocket handler for consultation messages
window.onNewBookingMessage = function(data) {
    if (!data) return;
    const bId = String(data.booking_id);
    
    // 1. If currently viewing this booking in modal:
    if (String(currentBookingId) === bId && document.getElementById('bookingDetailModal')?.classList.contains('active')) {
        const chatPane = document.getElementById('btab-chat');
        if (chatPane && chatPane.classList.contains('active')) {
            loadBookingMessages(bId);
        } else {
            const badge = document.getElementById('modalChatTabBadge');
            if (badge) {
                const curr = parseInt(badge.textContent || '0', 10) + 1;
                badge.textContent = curr;
                badge.style.display = 'inline-block';
            }
        }
    }

    // 2. Update table row badge:
    const rowEl = document.getElementById(`booking-row-${bId}`);
    if (rowEl) {
        let badge = rowEl.querySelector('span[title="Unread Consultation Messages"]');
        let count = parseInt(rowEl.dataset.unreadChat || '0', 10) + 1;
        rowEl.dataset.unreadChat = String(count);
        if (!badge) {
            badge = document.createElement('span');
            badge.setAttribute('title', 'Unread Consultation Messages');
            badge.style.cssText = 'background: #3b82f6; color: white; font-size: 0.65rem; font-weight: 850; padding: 2px 7px; border-radius: 10px; display: inline-flex; align-items: center; gap: 3px; box-shadow: 0 1px 3px rgba(59,130,246,0.2);';
            badge.innerHTML = `<i class="fas fa-comment-dots"></i> ${count}`;
            const targetContainer = rowEl.querySelector('td:nth-child(2) div') || rowEl.querySelector('td:first-child') || rowEl;
            targetContainer.appendChild(badge);
        } else {
            badge.innerHTML = `<i class="fas fa-comment-dots"></i> ${count}`;
        }
    }
};

window.loadBookingMessages = loadBookingMessages;
window.sendBookingChatMessage = sendBookingChatMessage;
window.handleModalChatFileSelect = handleModalChatFileSelect;
window.clearModalChatAttachment = clearModalChatAttachment;

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
    
    const header = document.getElementById('iframeModalHeader');
    const box = modal.querySelector('.occ-modal-box');
    if (url.includes('/sign')) {
        if (header) header.style.display = 'none';
        if (box) {
            box.style.maxWidth = '1280px';
            box.style.width = '96%';
            box.style.height = '94vh';
        }
    } else {
        if (header) header.style.display = 'flex';
        if (box) {
            box.style.maxWidth = '1000px';
            box.style.width = '95%';
            box.style.height = '95vh';
        }
    }
    
    const titleEl = document.getElementById('iframeModalTitle');
    if (titleEl) titleEl.innerText = title || 'View Document';
    const loadingEl = document.getElementById('iframeModalLoading');
    if (loadingEl) loadingEl.style.display = 'flex';
    const iframeEl = document.getElementById('iframeModalContent');
    if (iframeEl) iframeEl.src = url;
    
    modal.style.display = 'flex';
    setTimeout(() => modal.classList.add('active'), 10);
};

window.closeIframeModal = function() {
    const modal = document.getElementById('iframeModal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => {
            modal.style.display = 'none';
            const iframe = document.getElementById('iframeModalContent');
            if (iframe) iframe.src = '';
        }, 300);
    }
};


window.sendPaymentReminder = function(bookingId) {
    window.copyInvoiceLink(bookingId);
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
    const cleanId = String(currentBookingId).replace(/\D/g, '');
    if (!cleanId) return;
    
    // Fetch current booking data
    fetch(`/caterer/api/bookings/${cleanId}/details`)
        .then(res => res.json())
        .then(data => {
            if (!data || !data.id) return;
            const elId = document.getElementById('editBookingId'); if (elId) elId.value = data.id;
            const elSt = document.getElementById('editBookingOriginalStatus'); if (elSt) elSt.value = data.status || '';
            
            const elCust = document.getElementById('editCustomerName'); if (elCust) elCust.value = data.customer_name || data.customerName || data.customer || '';
            const elDate = document.getElementById('editEventDate'); if (elDate) elDate.value = data.event_date || data.date || '';
            const elTime = document.getElementById('editEventTime'); if (elTime) elTime.value = data.event_time || data.time || '00:00';
            const elVenue = document.getElementById('editVenue'); if (elVenue) elVenue.value = data.venue || '';
            const elPax = document.getElementById('editGuestCount'); if (elPax) elPax.value = data.guest_count || data.guests || '';
            
            const reasonContainer = document.getElementById('editReasonContainer');
            const reasonInput = document.getElementById('editModificationReason');
            
            if (reasonContainer && reasonInput) {
                if (['confirmed', 'preparing', 'on_the_way', 'in_progress', 'ready_for_pickup', 'ready_for_delivery'].includes(data.status)) {
                    reasonContainer.style.display = 'block';
                    reasonInput.required = true;
                } else {
                    reasonContainer.style.display = 'none';
                    reasonInput.required = false;
                    reasonInput.value = '';
                }
            }
            
            if (typeof window.bk_openModal === 'function') window.bk_openModal('editBookingModal');
            else if (typeof window.openModal === 'function') window.openModal('editBookingModal');
        })
        .catch(err => console.error("Error fetching booking details:", err));
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


// ─── END MANUAL PAYMENTS ───────────────────────────────────────────────

window.submitManualPayment = window.submitRecordPayment;

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
