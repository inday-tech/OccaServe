let currentBookingId = null;

document.addEventListener('DOMContentLoaded', function () {
    // Add click listeners to all detail buttons
    document.querySelectorAll('.view-details').forEach(btn => {
        btn.addEventListener('click', function () {
            showBookingDetails(this);
        });
    });
});

function showBookingDetails(btn) {
    const data = btn.dataset;
    currentBookingId = data.id;
    const modal = document.getElementById('bookingDetailModal');
    if (!modal) return;

    document.getElementById('modalBookingId').innerText = `Booking #${data.id}`;
    document.getElementById('modalCustomer').innerText = data.customer;
    document.getElementById('modalEmail').innerText = data.email;
    document.getElementById('modalEventName').innerText = data.eventName;
    document.getElementById('modalEventType').innerText = data.eventType;
    document.getElementById('modalVenue').innerText = data.venue;
    document.getElementById('modalRequests').innerText = data.requests;

    // Status styling
    const statusEl = document.getElementById('modalStatus');
    statusEl.innerText = data.status;
    const statusColors = {
        'pending': { color: '#92400e', bg: '#fef3c7' },
        'confirmed': { color: '#166534', bg: '#dcfce7' },
        'completed': { color: '#1e40af', bg: '#dbeafe' },
        'cancelled': { color: '#991b1b', bg: '#fee2e2' }
    };
    const style = statusColors[data.status] || { color: '#374151', bg: '#f1f5f9' };
    statusEl.style.color = style.color;
    statusEl.style.backgroundColor = style.bg;

    // Menu items
    const menuSource = document.getElementById(`booking-items-${data.id}`);
    const menuTarget = document.getElementById('modalMenuItems');
    const menuSection = document.getElementById('modalMenuSection');

    if (menuSource) {
        menuTarget.innerHTML = menuSource.innerHTML;
        if (menuSection) menuSection.style.display = 'block';
    } else {
        menuTarget.innerHTML = '<p style="color: #64748b; font-size: 0.9rem;">No menu items selected.</p>';
    }

    // Payment Proofs
    const proofUrl = data.proofUrl;
    const balanceProofUrl = data.balanceProofUrl;
    const proofSection = document.getElementById('modalProofSection');
    const proofContainer = document.getElementById('modalProofContainer');

    if (proofSection && proofContainer) {
        proofContainer.innerHTML = '';
        let hasProof = false;

        if (proofUrl) {
            hasProof = true;
            proofContainer.innerHTML += `
                <a href="${proofUrl}" target="_blank" class="modal-proof-item">
                    <img src="${proofUrl}" class="modal-proof-img" onerror="this.src='/static/images/file-placeholder.png'">
                    <span class="modal-proof-label">Downpayment Proof</span>
                </a>
            `;
        }

        if (balanceProofUrl) {
            hasProof = true;
            proofContainer.innerHTML += `
                <a href="${balanceProofUrl}" target="_blank" class="modal-proof-item">
                    <img src="${balanceProofUrl}" class="modal-proof-img" onerror="this.src='/static/images/file-placeholder.png'">
                    <span class="modal-proof-label">Balance Proof</span>
                </a>
            `;
        }

        proofSection.style.display = hasProof ? 'block' : 'none';
    }

    // Actions
    const actionsEl = document.getElementById('bookingModalActions');

    actionsEl.innerHTML = '';


    if (data.status === 'pending') {
        const isPayment = data.paymentStatus === 'proof_submitted';
        actionsEl.innerHTML += `
            <button type="button" class="btn-footer-action btn-status-confirm" onclick="window.confirmAcceptBooking(${data.id}, ${isPayment})">
                <i class="fas fa-check-circle"></i>
                ${isPayment ? 'Confirm Payment' : 'Accept Booking'}
            </button>
            <button type="button" class="btn-footer-action btn-status-reject" onclick="window.confirmRejectBooking(${data.id})">
                <i class="fas fa-times-circle"></i> Reject
            </button>
        `;
    } else if (data.status === 'awaiting_caterer') {
        const signLink = document.createElement('a');
        signLink.href = `/caterer/bookings/${data.id}/sign`;
        signLink.className = 'btn-footer-action btn-status-confirm';
        signLink.style.textDecoration = 'none';
        signLink.innerHTML = '<i class="fas fa-pen-nib"></i> Sign Contract Now';
        actionsEl.appendChild(signLink);

        const rejectBtn = document.createElement('button');
        rejectBtn.type = 'button';
        rejectBtn.className = 'btn-footer-action btn-status-reject';
        rejectBtn.onclick = () => window.confirmRejectBooking(data.id);
        rejectBtn.innerHTML = '<i class="fas fa-times-circle"></i> Reject';
        actionsEl.appendChild(rejectBtn);
    } else if (data.status === 'confirmed') {
        // If balance proof uploaded, show confirm balance button
        if (data.paymentStatus === 'balance_proof_submitted') {
            actionsEl.innerHTML += `
                <button type="button" class="btn-footer-action btn-status-confirm" onclick="window.confirmAcceptBooking(${data.id}, true)">
                    <i class="fas fa-check-double"></i> Confirm Full Payment
                </button>
            `;
        }

        // Only show Mark as Completed if fully paid
        if (data.paymentStatus === 'paid') {
            actionsEl.innerHTML += `
                <button type="button" class="btn-footer-action btn-status-complete" onclick="window.confirmCompleteBooking(${data.id})">
                    <i class="fas fa-flag-checkered"></i> Mark Completed
                </button>
            `;
        } else {
            actionsEl.innerHTML += `
                <div class="completion-pending-hint">
                    <i class="fas fa-lock"></i> Awaiting Full Payment Before Completion
                </div>
            `;
        }
    } else if (data.status === 'completed' || data.status === 'cancelled') {
        actionsEl.innerHTML += `
            <button type="button" class="btn-footer-action" style="background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; flex: 1;"
                onclick="window.confirmArchiveBooking(${data.id})">
                <i class="fas fa-archive"></i> Archive Booking
            </button>
        `;
    }

    // Payment info
    document.getElementById('modalBookedOn').innerText = data.bookedOn;
    document.getElementById('modalPaymentMethod').innerText = `Method: ${data.paymentMethod}`;
    document.getElementById('modalTotalAmount').innerText = data.amount;
    document.getElementById('modalGuestCount').innerText = `${data.guestCount} Guests`;
    document.getElementById('modalDueDate').innerText = data.balanceDue ? data.balanceDue : 'Not Set';

    // Reset due date edit UI
    document.getElementById('dueDateDisplaySection').style.display = 'block';
    document.getElementById('dueDateEditSection').style.display = 'none';
    document.getElementById('balanceDueDateInput').value = data.balanceDue || '';
    // Restrict past dates
    const todayStr = new Date().toISOString().split('T')[0];
    document.getElementById('balanceDueDateInput').min = todayStr;


    const pStatusEl = document.getElementById('modalPaymentStatus');
    const pStatusLabels = {
        'paid': 'Fully Paid',
        'deposit_paid': 'Downpayment Paid',
        'proof_submitted': 'Downpayment Proof Sent',
        'balance_proof_submitted': 'Balance Proof Sent',
        'pending': 'Payment Pending'
    };
    pStatusEl.innerText = pStatusLabels[data.paymentStatus] || data.paymentStatus;

    if (data.paymentStatus === 'paid') {
        pStatusEl.style.color = '#166534';
        pStatusEl.style.background = '#dcfce7';
    } else if (data.paymentStatus === 'deposit_paid') {
        pStatusEl.style.color = '#115e59';
        pStatusEl.style.background = '#ccfbf1';
    } else if (data.paymentStatus === 'proof_submitted' || data.paymentStatus === 'balance_proof_submitted') {
        pStatusEl.style.color = '#92400e';
        pStatusEl.style.background = '#fef3c7';
    } else {
        pStatusEl.style.color = '#991b1b';
        pStatusEl.style.background = '#fee2e2';
    }

    // No History

    modal.style.display = 'flex';
}

// function promptCancel(bookingId) {
//     // Removed per Phase 10E requirements to prevent intentional/scam cancellations by caterer
// }


function showMenuDetails(bookingId) {
    const btn = document.querySelector(`.view-details[data-id="${bookingId}"]`);
    if (btn) showBookingDetails(btn);
}

function closeModal() {
    const modal = document.getElementById('bookingDetailModal');
    if (modal) modal.style.display = 'none';
}

let currentBookingIdForContract = null;

function openContractModal(bookingId) {
    currentBookingIdForContract = bookingId;
    const modal = document.getElementById('contractModal');
    const body = document.getElementById('contractModalBody');
    modal.style.display = 'flex';

    fetch(`/api/bookings/${bookingId}/contract/content`)
        .then(response => response.text())
        .then(html => {
            body.innerHTML = html;
        })
        .catch(err => {
            body.innerHTML = '<p style="color: #ef4444; text-align: center;">Failed to load contract content.</p>';
            console.error(err);
        });
}

function closeContractModal() {
    document.getElementById('contractModal').style.display = 'none';
}

function printContract(bookingId) {
    const url = `/caterer/bookings/${bookingId}/contract`;
    const printWindow = window.open(url, '_blank');
    printWindow.onload = function () {
        printWindow.print();
    };
}

// Due Date Management
function toggleDueDateEdit() {
    const display = document.getElementById('dueDateDisplaySection');
    const edit = document.getElementById('dueDateEditSection');
    const btnEdit = document.getElementById('btnEditDueDate');
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
    const newDate = document.getElementById('balanceDueDateInput').value;
    if (!newDate) {
        window.showError("Please select a valid date.");
        return;
    }

    try {
        const today = new Date().toISOString().split('T')[0];
        if (newDate < today) {
            window.showError("Warning: You are setting a due date in the past. Please select a current or future date.");
            return;
        }

        const response = await fetch(`/api/bookings/${currentBookingId}/set-due-date`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ due_date: newDate })
        });

        if (response.ok) {
            document.getElementById('modalDueDate').innerText = newDate;
            toggleDueDateEdit();

            // Update the data attribute on the button so it persists if modal is reopened
            const btn = document.querySelector(`.view-details[data-id="${currentBookingId}"]`);
            if (btn) btn.dataset.balanceDue = newDate;

            window.showSuccess("Due date updated successfully!");
        } else {
            const err = await response.json();
            window.showError(err.detail || "Failed to update due date.", "Error");
        }
    } catch (error) {
        console.error("Error saving due date:", error);
        window.showError("An error occurred while saving the due date.");
    }
}

// Confirmation Wrappers for Actions
function confirmAcceptBooking(bookingId, isPayment = false) {
    const title = isPayment ? "Confirm Payment?" : "Accept Booking?";
    const message = isPayment
        ? "Sigurado ka bang natanggap mo na ang bayad? Ito ay magpapalit sa status ng booking bilang 'Confirmed'."
        : "Nais mo bang tanggapin ang booking na ito? Pakisiguradong tama ang lahat ng detalye bago mag-proceed.";

    window.showConfirm(message, () => {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = isPayment ? `/caterer/payments/${bookingId}/confirm` : `/caterer/bookings/${bookingId}/accept`;
        document.body.appendChild(form);
        form.submit();
    }, title, isPayment ? "Yes, Confirm Payment" : "Yes, Accept Booking");
}

function confirmRejectBooking(bookingId) {
    window.showConfirm(
        "Naniniwala ka bang nais mong i-REJECT ang booking na ito? Ang action na ito ay permanent at hindi na mababawi.",
        () => {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/caterer/bookings/${bookingId}/reject`;
            document.body.appendChild(form);
            form.submit();
        },
        "Reject Booking?",
        "Yes, Reject Booking"
    );
}

function confirmCompleteBooking(bookingId) {
    window.showConfirm(
        "Tapos na ba ang event? Ang pag-marka nito bilang 'Completed' ay maglilipat sa status nito sa history.",
        () => {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/caterer/bookings/${bookingId}/complete`;
            document.body.appendChild(form);
            form.submit();
        },
        "Mark as Completed?",
        "Yes, Event Finished"
    );
}

function confirmArchiveBooking(bookingId) {
    window.showConfirm(
        "Nais mo bang i-archive ang booking na ito? Ito ay ililipat sa iyong archives folder.",
        () => {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/caterer/bookings/${bookingId}/archive`;
            document.body.appendChild(form);
            form.submit();
        },
        "Archive Booking?",
        "Yes, Archive"
    );
}

// Global exposure
// window.promptCancel = promptCancel; // promptCancel was removed
window.showMenuDetails = showMenuDetails;

window.closeModal = closeModal;
window.openContractModal = openContractModal;
window.closeContractModal = closeContractModal;
window.printContract = printContract;
window.toggleDueDateEdit = toggleDueDateEdit;
window.saveDueDate = saveDueDate;

// Export confirmation functions
window.confirmAcceptBooking = confirmAcceptBooking;
window.confirmRejectBooking = confirmRejectBooking;
window.confirmCompleteBooking = confirmCompleteBooking;
window.confirmArchiveBooking = confirmArchiveBooking;

// Close when clicking outside
window.onclick = function (event) {
    const detailModal = document.getElementById('bookingDetailModal');
    const contractModal = document.getElementById('contractModal');
    if (event.target == detailModal) {
        closeModal();
    }
    if (event.target == contractModal) {
        closeContractModal();
    }
}
