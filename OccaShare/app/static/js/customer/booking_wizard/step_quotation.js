// WebSocket for Real-time Signature Sync
function initSignatureWebSocket() {
    if (!window.userId || !window.bookingId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const clientId = `user_${window.userId}_signing_${window.bookingId}_${Math.random().toString(36).substr(2, 9)}`;
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/${clientId}`);

    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === 'signature_update' && data.booking_id == window.bookingId) {
            console.log('[WS] Received signature update:', data);
            
            // If it was signed by the other party, we need to refresh to show the button/signatures
            if (data.role === 'caterer') {
                if (window.showToast) {
                    window.showToast("The caterer has signed the contract. Loading the next step...", "info");
                    setTimeout(() => window.location.reload(), 2000);
                } else {
                    Swal.fire({
                        icon: 'info',
                        title: 'Contract Updated',
                        text: 'The caterer has signed the contract. Loading the next step...',
                        timer: 2000,
                        showConfirmButton: false
                    }).then(() => window.location.reload());
                }
            }
        }
    };

    ws.onclose = () => {
        console.log('[WS] Signing sync connection closed. Retrying in 5s...');
        setTimeout(initSignatureWebSocket, 5000);
    };
}

document.addEventListener('DOMContentLoaded', function () {
    const canvas = document.getElementById('signature-pad');
    if (canvas) {
        initSignatureWebSocket();
        sigPad = new SignaturePad(canvas, {
            backgroundColor: 'rgba(255, 255, 255, 0)',
            penColor: 'rgb(15, 23, 42)'
        });

        function resizeCanvas() {
            const ratio = Math.max(window.devicePixelRatio || 1, 1);
            canvas.width = canvas.offsetWidth * ratio;
            canvas.height = canvas.offsetHeight * ratio;
            canvas.getContext("2d").scale(ratio, ratio);
            sigPad.clear();
        }

        window.onresize = resizeCanvas;
        resizeCanvas();

        const placeholder = document.getElementById('sig-placeholder');
        
        sigPad.addEventListener('beginStroke', () => {
            if (placeholder) placeholder.style.display = 'none';
        });

        sigPad.addEventListener('change', () => {
            window.toggleApplyButton();
        });
    }
});

window.toggleApplyButton = function () {
    const agree = document.getElementById('agree_terms');
    const checkPayment = document.getElementById('check_payment');
    const checkCancel = document.getElementById('check_cancel');
    const btn = document.getElementById('btn-apply-sig');
    
    if (agree && checkPayment && checkCancel && btn) {
        const allChecked = agree.checked && checkPayment.checked && checkCancel.checked;
        btn.disabled = !(allChecked && sigPad && !sigPad.isEmpty());
    }
};

window.applySignatureLocal = function () {
    if (!sigPad || sigPad.isEmpty()) {
        if (window.showError) window.showError('Please sign the pad first.', 'Empty Signature'); else Swal.fire('Empty Signature', 'Please sign the pad first.', 'warning');
        return;
    }

    const signatureData = sigPad.toDataURL();
    const placeholder = document.getElementById('customer-sig-placeholder');
    const dateLabel = document.getElementById('customer-sig-date');
    const finalizeBtn = document.getElementById('btn-sign');
    const applyPrompt = document.getElementById('apply-prompt');

    if (placeholder) {
        placeholder.innerHTML = `<img src="${signatureData}" alt="Signature" class="formal-sig-img">`;
    }
    
    if (dateLabel) {
        const now = new Date();
        const formattedDate = now.getFullYear() + '-' + 
                              String(now.getMonth() + 1).padStart(2, '0') + '-' + 
                              String(now.getDate()).padStart(2, '0') + ' ' + 
                              String(now.getHours()).padStart(2, '0') + ':' + 
                              String(now.getMinutes()).padStart(2, '0');
        dateLabel.innerText = `Date Signed: ${formattedDate} (Pending Finalization)`;
        dateLabel.style.opacity = '1';
    }

    // Toggle visibility: hide prompt, show finalize button
    if (finalizeBtn) finalizeBtn.style.display = 'inline-flex';
    if (applyPrompt) applyPrompt.style.display = 'none';

    // Disable pad and apply button to lock it in visually
    sigPad.off();
    const btnApply = document.getElementById('btn-apply-sig');
    const agreeCheck = document.getElementById('agree_terms');
    if (btnApply) btnApply.disabled = true;
    if (agreeCheck) agreeCheck.disabled = true;
    const checkPayment = document.getElementById('check_payment');
    const checkCancel = document.getElementById('check_cancel');
    if (checkPayment) checkPayment.disabled = true;
    if (checkCancel) checkCancel.disabled = true;

    if (window.showToast) {
        window.showToast("Review your signature on the contract below, then click Finalize.", "success");
    } else {
        Swal.fire({
            icon: 'success',
            title: 'Signature Applied',
            text: 'Review your signature on the contract below, then click Finalize.',
            timer: 1500,
            showConfirmButton: false
        });
    }
};

window.clearSignature = function () {
    if (sigPad) {
        sigPad.clear();
        sigPad.on();
        const agreeCheck = document.getElementById('agree_terms');
        const btnApply = document.getElementById('btn-apply-sig');
        const finalizeBtn = document.getElementById('btn-sign');
        const applyPrompt = document.getElementById('apply-prompt');
        
        if (agreeCheck) {
            agreeCheck.checked = false;
            agreeCheck.disabled = false;
        }
        const checkPayment = document.getElementById('check_payment');
        const checkCancel = document.getElementById('check_cancel');
        if (checkPayment) { checkPayment.checked = false; checkPayment.disabled = false; }
        if (checkCancel) { checkCancel.checked = false; checkCancel.disabled = false; }
        if (btnApply) btnApply.disabled = true;
        if (finalizeBtn) finalizeBtn.style.display = 'none';
        if (applyPrompt) applyPrompt.style.display = 'flex';
        
        // Reset contract preview
        const placeholder = document.getElementById('customer-sig-placeholder');
        if (placeholder) {
            placeholder.innerHTML = '<div class="sig-awaiting">AWAITING CLIENT SIGNATURE</div>';
        }
        const dateLabel = document.getElementById('customer-sig-date');
        if (dateLabel) dateLabel.style.opacity = '0';
    }
};

window.setDPTier = async function (percent) {
    const isSigned = document.getElementById('signed-input')?.value === 'true';
    if (isSigned) return;

    const bookingId = window.location.pathname.split('/').pop();
    const dpValEl = document.getElementById('deposit-val');
    const input = document.getElementById('dp-percent-input');
    
    // UI Feedback for options
    document.querySelectorAll('.dp-option-landscape').forEach(opt => {
        opt.classList.remove('active');
        if (opt.querySelector('.dp-pct').textContent.includes(percent + '%')) {
            opt.classList.add('active');
        }
    });
    
    try {
        const response = await fetch(`/api/bookings/${bookingId}/update-dp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ percent: percent })
        });
        
        const data = await response.json();
        if (data.success) {
            input.value = percent;
            const formattedDeposit = '₱' + data.new_deposit.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
            if (dpValEl) dpValEl.textContent = formattedDeposit;
            
            // Update contract text REAL-TIME
            const contractPct = document.getElementById('contract-dp-pct');
            const contractVal = document.getElementById('contract-dp-val');
            
            if (contractPct) contractPct.innerText = percent;
            if (contractVal) contractVal.innerText = data.new_deposit.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
    } catch (error) {
        console.error('Error updating DP tier:', error);
    }
};

let sigPad; // Declare globally

window.submitSignature = async function () {
    if (!sigPad || sigPad.isEmpty()) {
        Swal.fire({
            icon: 'error',
            title: 'Action Required',
            text: 'Please sign before finalizing.',
            customClass: {
                popup: 'up-swal-popup',
                title: 'up-swal-title',
                html: 'up-swal-html',
                confirmButton: 'up-swal-confirm'
            }
        });
        return;
    }

    const signatureData = sigPad.toDataURL();

    Swal.fire({
        title: 'Finalizing Agreement...',
        text: 'Securing your booking and contract',
        allowOutsideClick: false,
        customClass: {
            popup: 'up-swal-popup',
            title: 'up-swal-title',
            html: 'up-swal-html'
        },
        didOpen: () => { Swal.showLoading(); }
    });

    try {
        const response = await fetch(`/api/bookings/${window.bookingId}/contract/sign?role=customer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ signature_data: signatureData })
        });

        const result = await response.json();
        if (result.success) {
            if (result.status === 'signed') {
                // Both signed! Move directly to payment
                if (window.showToast) {
                    window.showToast("Redirecting to payment step...", "success");
                    setTimeout(() => window.location.href = `/bookings/step/payment/${window.bookingId}`, 2000);
                } else {
                    Swal.fire({
                        icon: 'success',
                        title: 'Contract Successfully Signed!',
                        text: 'Redirecting to payment step...',
                        timer: 2000,
                        showConfirmButton: false,
                        customClass: {
                            popup: 'up-swal-popup',
                            title: 'up-swal-title',
                            html: 'up-swal-html'
                        }
                    }).then(() => window.location.href = `/bookings/step/payment/${window.bookingId}`);
                }
            } else {
                // Only customer signed, awaiting caterer
                if (window.showToast) {
                    window.showToast("Contract awaiting caterer's signature.", "success");
                    setTimeout(() => window.location.reload(), 2000);
                } else {
                    Swal.fire({
                        icon: 'success',
                        title: 'Your Signature Applied!',
                        text: 'The contract is now awaiting the caterer\'s signature. We will notify you once they sign.',
                        confirmButtonText: 'View Status',
                        customClass: {
                            popup: 'up-swal-popup',
                            title: 'up-swal-title',
                            html: 'up-swal-html',
                            confirmButton: 'up-swal-confirm'
                        }
                    }).then(() => window.location.reload());
                }
            }
        } else {
            throw new Error(result.error || 'Failed to sign contract');
        }
    } catch (error) {
        console.error('Error signing:', error);
        if (window.showError) window.showError(error.message || 'An error occurred while signing.', 'Error'); else Swal.fire('Error', error.message || 'An error occurred while signing.', 'error');
    }
};
window.scrollToContract = function() {
    const el = document.getElementById('contract-section');
    if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
};
