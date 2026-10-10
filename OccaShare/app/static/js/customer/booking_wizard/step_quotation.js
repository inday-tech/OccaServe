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
                const paymentUrl = `/bookings/step/payment/${window.bookingId}`;
                if (window.showToast) {
                    window.showToast("The agreement is fully signed. Taking you to payment...", "success");
                    setTimeout(() => window.location.assign(paymentUrl), 1500);
                } else {
                    Swal.fire({
                        icon: 'success',
                        title: 'Agreement Fully Signed',
                        text: 'Taking you to the payment step...',
                        timer: 1500,
                        showConfirmButton: false
                    }).then(() => window.location.assign(paymentUrl));
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

let dpUpdateRequest = 0;
window.setDPTier = async function (percent) {
    const isSigned = document.getElementById('signed-input')?.value === 'true';
    if (isSigned) return;

    percent = Number(percent);
    if (![30, 40, 50, 60, 70, 80, 90, 100].includes(percent)) return;

    const bookingId = window.bookingId || window.location.pathname.split('/').pop();
    const dpValEl = document.getElementById('deposit-val');
    const input = document.getElementById('dp-percent-input');
    const totalInput = document.getElementById('total-amount-input');
    const totalVal = totalInput ? Number(totalInput.value) : 0;
    const calculatedDeposit = Math.round((totalVal * percent / 100 + Number.EPSILON) * 100) / 100;
    const formattedDeposit = calculatedDeposit.toLocaleString('en-PH', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    const remainingBal = Math.max(0, totalVal - calculatedDeposit);

    // Update the breakdown immediately so every supported percentage recalculates on selection.
    if (input) input.value = percent;
    if (dpValEl) dpValEl.textContent = `\u20B1${formattedDeposit}`;
    const tierLabel = document.getElementById('selected-tier-label');
    if (tierLabel) tierLabel.textContent = percent === 100 ? '100% Full Payment' : `${percent}% Deposit`;
    const balValEl = document.getElementById('remaining-balance-val');
    if (balValEl) balValEl.textContent = `\u20B1${remainingBal.toLocaleString('en-PH', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    const balBox = document.getElementById('balance-box');
    if (balBox) balBox.style.display = (percent === 100 || remainingBal <= 0) ? 'none' : 'flex';
    const contractPct = document.getElementById('contract-dp-pct');
    const contractVal = document.getElementById('contract-dp-val');
    if (contractPct) contractPct.innerText = percent;
    if (contractVal) contractVal.innerText = formattedDeposit;

    const requestId = ++dpUpdateRequest;
    try {
        const response = await fetch(`/api/bookings/${bookingId}/update-dp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({ percent: percent })
        });
        const responseText = await response.text();
        let data;
        try {
            data = JSON.parse(responseText);
        } catch (_) {
            throw new Error(`The server could not save the deposit option (HTTP ${response.status}). Please reload and try again.`);
        }
        if (!response.ok || !data.success) {
            throw new Error(data.detail || data.error || 'The deposit option could not be saved. Please try again.');
        }
        // Ignore stale replies if the customer selected another percentage while this request was pending.
        if (requestId !== dpUpdateRequest) return;
    } catch (error) {
        console.error('Error updating DP tier:', error);
        if (requestId === dpUpdateRequest && window.showError) {
            window.showError(error.message || 'The deposit option could not be saved. Please try again.', 'Deposit not saved');
        }
    }
};

let sigPad; // Declare globally

window.submitSignature = async function () {
    if (!sigPad || sigPad.isEmpty()) {
        Swal.fire({
            icon: 'error',
            title: 'Action Required',
            text: 'Please sign before finalizing.',
            customClass: { popup: 'up-swal-popup', title: 'up-swal-title', html: 'up-swal-html', confirmButton: 'up-swal-confirm' }
        });
        return;
    }

    const signatureData = sigPad.toDataURL();
    const saveButton = document.getElementById('btn-sign');
    const originalButtonText = saveButton ? saveButton.innerHTML : '';
    if (saveButton) {
        saveButton.disabled = true;
        saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving signature...';
    }

    Swal.fire({
        title: 'Saving your signature...',
        text: 'Please wait while we save your signed agreement.',
        allowOutsideClick: false,
        showConfirmButton: false,
        customClass: { popup: 'up-swal-popup', title: 'up-swal-title', html: 'up-swal-html' },
        didOpen: () => Swal.showLoading()
    });

    try {
        const response = await fetch(`/api/bookings/${window.bookingId}/contract/sign?role=customer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({ signature_data: signatureData })
        });
        const responseText = await response.text();
        let result;
        try {
            result = JSON.parse(responseText);
        } catch (_) {
            throw new Error(`The server could not save your signature (HTTP ${response.status}). Please try again.`);
        }
        if (!response.ok || !result.success) {
            throw new Error(result.detail || result.error || result.message || 'Failed to save your signature.');
        }

        if (result.status === 'signed') {
            const confirmation = await Swal.fire({
                icon: 'success',
                title: 'Signature saved successfully!',
                text: 'Both parties have signed the agreement. You can continue to payment now.',
                confirmButtonText: 'Continue to payment',
                allowOutsideClick: false,
                customClass: { popup: 'up-swal-popup', title: 'up-swal-title', html: 'up-swal-html', confirmButton: 'up-swal-confirm' }
            });
            if (confirmation.isConfirmed) window.location.href = `/bookings/step/payment/${window.bookingId}`;
        } else {
            await Swal.fire({
                icon: 'success',
                title: 'Signature saved successfully!',
                text: 'Your agreement is now waiting for the caterer’s signature. You will be notified when they sign.',
                confirmButtonText: 'View status',
                allowOutsideClick: false,
                customClass: { popup: 'up-swal-popup', title: 'up-swal-title', html: 'up-swal-html', confirmButton: 'up-swal-confirm' }
            });
            window.location.reload();
        }
    } catch (error) {
        console.error('Error signing:', error);
        await Swal.fire({
            icon: 'error',
            title: 'Signature was not saved',
            text: error.message || 'An error occurred while signing. Please try again.',
            confirmButtonText: 'Try again',
            customClass: { popup: 'up-swal-popup', title: 'up-swal-title', html: 'up-swal-html', confirmButton: 'up-swal-confirm' }
        });
        if (saveButton) {
            saveButton.disabled = false;
            saveButton.innerHTML = originalButtonText;
        }
    }
};
window.scrollToContract = function() {
    const el = document.getElementById('contract-section');
    if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
};
