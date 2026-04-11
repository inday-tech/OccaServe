/**
 * Direct Payment Gateway Logic
 * Handles method selection, app-linking, and simulated processing sequence
 */

function selectPaymentMethod(method, element) {
    // 1. Update hidden input for form submission
    document.getElementById('selected-method').value = method;

    // 2. Update active UI state on cards
    document.querySelectorAll('.method-card').forEach(card => {
        card.classList.remove('active');
    });
    element.classList.add('active');

    // 3. Show specific Payment Details container
    const detailsContainer = document.getElementById('payment-details-container');
    detailsContainer.style.display = 'block';
    detailsContainer.classList.add('animate-up');

    // Hide all individual details first
    document.querySelectorAll('.payment-content-block').forEach(block => {
        block.style.display = 'none';
    });

    // Show the selected one
    const activeDetails = document.querySelector(`.payment-content-block[data-method-content="${method}"]`);
    if (activeDetails) {
        activeDetails.style.display = 'block';
    }

    // 4. Handle Proof Upload requirements and submit button states
    const proofSection = document.getElementById('proof-upload-section');
    const fileInput = document.getElementById('payment_proof');
    const submitBtn = document.getElementById('submit-payment-btn');

    // Enable the submit button
    submitBtn.disabled = false;
    submitBtn.style.opacity = '1';
    submitBtn.style.pointerEvents = 'auto';

    if (method === 'Cash') {
        proofSection.style.display = 'none';
        fileInput.required = false;
        submitBtn.innerHTML = `Complete Booking (Manual Arrangement) <i class="fas fa-check-circle"></i>`;
    } else {
        proofSection.style.display = 'block';
        fileInput.required = true;
        submitBtn.innerHTML = `Confirm & Submit Payment <i class="fas fa-shield-alt"></i>`;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('form');
    const actions = document.getElementById('wizard-actions');
    const processing = document.getElementById('payment-processing');
    const statusText = document.getElementById('processing-status');
    const msgText = document.getElementById('processing-msg');
    const progressBar = document.getElementById('progress-bar');

    if (form && actions && processing) {
        form.onsubmit = function (e) {
            e.preventDefault(); // Intercept for simulation

            actions.style.display = 'none';
            processing.style.display = 'flex';

            const method = document.getElementById('selected-method').value;
            
            // GATEWAY SIMULATION SEQUENCE
            const steps = [
                { status: "Connecting to Secure Gateway...", msg: "Validating transaction details...", progress: 30 },
                { status: `Awaiting ${method} confirmation...`, msg: "Synchronizing with payment provider...", progress: 60 },
                { status: "Finalizing Payment...", msg: "Creating secure booking record...", progress: 90 },
                { status: "Success!", msg: "Redirecting back to marketplace...", progress: 100 }
            ];

            let stepIdx = 0;
            const interval = setInterval(() => {
                if (stepIdx < steps.length) {
                    const step = steps[stepIdx];
                    statusText.textContent = step.status;
                    msgText.textContent = step.msg;
                    progressBar.style.width = `${step.progress}%`;
                    stepIdx++;
                } else {
                    clearInterval(interval);
                    // Actual Form Submit
                    form.submit();
                }
            }, 1200);

            return false;
        };
    }
});
