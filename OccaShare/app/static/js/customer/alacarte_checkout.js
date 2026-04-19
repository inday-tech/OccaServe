document.addEventListener('DOMContentLoaded', function () {
    const itemPrice = window.itemPrice || 0;
    const catererId = window.catererId;
    const menuId = window.menuId;

    let deliveryFee = 150; // Default to delivery as it's checked in HTML
    let currentScreen = 1;
    
    // RECOVER SESSION: Use a more robust check
    const sessionKey = `alc_draft_${window.catererId}_${window.menuId}`;
    let bookingId = sessionStorage.getItem(sessionKey); 
    
    // Function to ensure we always have the latest ID
    function getActiveBookingId() {
        if (!bookingId) {
            bookingId = sessionStorage.getItem(sessionKey);
        }
        return bookingId;
    }

    if (bookingId) {
        console.log("[CHECKOUT] Found existing session:", bookingId);
    }

    // Webcam Variables
    let videoStream = null;
    let idFile = null;
    let selfieFrames = [];
    let isMobile = () => /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

    // --- SETUP DATE MIN ---
    const dateInput = document.getElementById('delivery_date');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.setAttribute('min', today);
    }

    // --- NAVIGATION LOGIC ---
    window.nextScreen = async function (n, force = false) {
        if (!force && n > currentScreen) {
            if (!validateScreen(currentScreen)) return;
            
            // SPECIAL: Create Draft Booking when moving from Step 1 to Step 2
            if (currentScreen === 1 && n === 2) {
                const ok = await createDraftBooking();
                if (!ok) return;

                // AUTO-SKIP: If verified, jump from 1 -> 3 (Skip Identity)
                if (window.isVerified) {
                    return nextScreen(3, true);
                }
            }
        }

        // Hide all screens, show target
        document.querySelectorAll('.checkout-screen').forEach(s => s.classList.remove('active'));
        const target = document.getElementById(`screen-${n}`);
        if (target) target.classList.add('active');

        // Update Stepper
        updateStepper(n);
        currentScreen = n;

        // Side-effects
        if (n === 2) {
            // Optional: Auto-start something for KYC?
        }
        if (n === 3) populateReview();

        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    function updateStepper(n) {
        document.querySelectorAll('.mini-step').forEach((step, idx) => {
            const stepNum = idx + 1;
            if (stepNum < n) {
                step.classList.add('completed');
                step.classList.remove('active');
            } else if (stepNum === n) {
                step.classList.add('active');
                step.classList.remove('completed');
            } else {
                step.classList.remove('active', 'completed');
            }
        });
    }

    // --- FORM VALIDATION ---
    function validateScreen(n) {
        let isValid = true;
        document.querySelectorAll('.field-error').forEach(el => el.classList.remove('show'));
        document.querySelectorAll('.form-input').forEach(el => el.classList.remove('error'));

        if (n === 1) {
            const fulfillment = document.querySelector('input[name="fulfillment"]:checked').value;
            const required = ['full_name', 'contact_number', 'delivery_date', 'delivery_time'];
            if (fulfillment === 'delivery') required.push('address');

            required.forEach(id => {
                const el = document.getElementById(id);
                if (el && !el.value.trim()) {
                    showError(id, `err-${id}`);
                    isValid = false;
                }
            });
            
            const phone = document.getElementById('contact_number').value.replace(/\D/g, '');
            if (phone.length !== 11 && phone.length > 0) {
                showError('contact_number', 'err-contact_number');
                isValid = false;
            }
        }
        
        if (n === 2) {
            const nextBtn = document.getElementById('id-next-btn');
            if (nextBtn && nextBtn.disabled) {
                if (window.showToast) window.showToast("Please complete identity verification.", "error");
                isValid = false;
            }
        }

        return isValid;
    }

    function showError(inputId, errId) {
        const input = document.getElementById(inputId);
        const err = document.getElementById(errId);
        if (input) input.classList.add('error');
        if (err) err.classList.add('show');
    }

    // --- DRAFT CREATION ---
    async function createDraftBooking() {
        const form = document.getElementById('checkoutForm');
        const formData = new FormData(form);
        formData.append('caterer_id', catererId);
        formData.append('menu_id', menuId);
        formData.append('is_draft', 'true');
        formData.append('total_amount', calculateTotal());

        try {
            const btn = document.querySelector('#screen-1 .btn-wizard-next');
            btn.innerHTML = 'Securing Details... <i class="fas fa-spinner fa-spin"></i>';
            btn.disabled = true;

            const res = await fetch('/bookings/alacarte/checkout/draft', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            if (data.success) {
                bookingId = data.booking_id;
                sessionStorage.setItem(sessionKey, bookingId); // Persist ID
                console.log("[CHECKOUT] Draft created/updated:", bookingId);
                return true;
            } else {
                alert("Error creating booking: " + data.message);
                return false;
            }
        } catch (e) {
            console.error(e);
            alert("Connection error occurred.");
            return false;
        } finally {
            const btn = document.querySelector('#screen-1 .btn-wizard-next');
            btn.innerHTML = 'Next Step: Verification <i class="fas fa-chevron-right"></i>';
            btn.disabled = false;
        }
    }

    // --- IDENTITY / KYC LOGIC (SYNCED WITH PACKAGE WIZARD) ---
    const validationPatterns = {
        'PhilSys / PhilID': {
            regex: /^\d{4}-\d{4}-\d{4}-\d{4}$/,
            placeholder: '0000-0000-0000-0000',
            format: (v) => v.replace(/\D/g, '').replace(/(\d{4})(?=\d)/g, '$1-').substring(0, 19)
        },
        'Driver\'s License': {
            regex: /^[A-Z]\d{2}-\d{2}-\d{6}$/,
            placeholder: 'A00-00-000000',
            format: (v) => {
                let clean = v.replace(/[^A-Za-z0-9]/g, '').toUpperCase();
                let res = '';
                if (clean.length > 0) res += clean[0];
                if (clean.length > 1) res += clean.substring(1, 3);
                if (clean.length > 3) res = res.substring(0, 3) + '-' + clean.substring(3, 5);
                if (clean.length > 5) res = res.substring(0, 6) + '-' + clean.substring(5, 11);
                return res.substring(0, 13);
            }
        },
        'Passport': {
            regex: /^([A-Z]\d{7}[A-Z]|[A-Z]{2}\d{7})$/,
            placeholder: 'A0000000A or AA0000000',
            format: (v) => v.replace(/[^A-Za-z0-9]/g, '').toUpperCase().substring(0, 9)
        },
        'UMID': {
            regex: /^\d{4}-\d{7}-\d{1}$/,
            placeholder: '0000-0000000-0',
            format: (v) => {
                let clean = v.replace(/\D/g, '');
                let res = '';
                if (clean.length > 4) {
                    res = clean.substring(0, 4) + '-' + clean.substring(4, 11);
                    if (clean.length > 11) res += '-' + clean.substring(11, 12);
                } else {
                    res = clean;
                }
                return res.substring(0, 14);
            }
        }
    };

    window.validateIdSelection = function () {
        const idType = document.getElementById('id_type').value;
        const idInput = document.getElementById('id_number');
        const msg = document.getElementById('alc-id-validation-msg');
        const scanCard = document.getElementById('alc-option-scan');
        const uploadCard = document.getElementById('alc-option-upload');

        let value = idInput.value;
        let isValid = false;

        if (idType && validationPatterns[idType]) {
            const p = validationPatterns[idType];
            const formatted = p.format(value);
            if (formatted !== value) { idInput.value = formatted; value = formatted; }
            isValid = p.regex.test(value);
            idInput.placeholder = p.placeholder;
            
            if (value.length > 0) {
                msg.innerHTML = isValid ? '<i class="fas fa-check-circle"></i> Format Valid' : 'Invalid format for ' + idType;
                msg.style.color = isValid ? 'var(--checkout-success)' : '#ef4444';
                idInput.style.borderColor = isValid ? 'var(--checkout-success)' : '#ef4444';
            } else {
                msg.innerText = '';
                idInput.style.borderColor = '';
            }
        }

        if (isValid) {
            scanCard.classList.remove('disabled');
            uploadCard.classList.remove('disabled');
        } else {
            scanCard.classList.add('disabled');
            uploadCard.classList.add('disabled');
        }
    };

    window.handleUploadClick = function() {
        if (document.getElementById('alc-option-upload').classList.contains('disabled')) return;
        document.getElementById('id_document_input').click();
    };

    window.previewKycId = function(input) {
        if (input.files && input.files[0]) {
            idFile = input.files[0];
            const reader = new FileReader();
            reader.onload = (e) => {
                document.getElementById('id-image-preview').src = e.target.result;
                updateKycStep(2);
            };
            reader.readAsDataURL(idFile);
        }
    };

    window.startIdScanner = async function() {
        if (document.getElementById('alc-option-scan').classList.contains('disabled')) return;
        updateKycStep('scanner');
        const video = document.getElementById('id-scanner-webcam');
        try {
            videoStream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'environment', width: { ideal: 1280 } } 
            });
            video.srcObject = videoStream;
        } catch (e) {
            videoStream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = videoStream;
        }
    };

    window.captureIdPhoto = function() {
        const video = document.getElementById('id-scanner-webcam');
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        
        canvas.toBlob(blob => {
            idFile = new File([blob], "id_scan.jpg", { type: "image/jpeg" });
            document.getElementById('id-image-preview').src = URL.createObjectURL(blob);
            stopStream();
            updateKycStep(2);
        }, 'image/jpeg', 0.95);
    };

    window.proceedToOcr = async function() {
        if (!bookingId) {
            if (window.showToast) window.showToast("Booking session not found. Please restart.", "error");
            return;
        }

        // Show Loading State
        updateKycStep(3);
        updateInternalStepper(2);
        
        // --- REAL API CALL: UPLOAD ID ---
        const formData = new FormData();
        formData.append('id_type', document.getElementById('id_type').value);
        formData.append('id_number', document.getElementById('id_number').value);
        formData.append('id_document', idFile);

        try {
            const res = await fetch(`/api/bookings/${bookingId}/upload-id`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();

            if (!res.ok) {
                // Return to ID upload with error
                if (window.showToast) window.showToast(data.detail || "ID validation failed", "error");
                updateKycStep(1);
                updateInternalStepper(1);
                return;
            }

            // Simulating quality gates for UX but API is already done
            const nodes = ['qc-resolution', 'qc-focus', 'qc-ocr'];
            nodes.forEach((id, i) => {
                setTimeout(() => {
                    const el = document.getElementById(id);
                    el.style.color = 'var(--checkout-success)';
                    el.querySelector('i').className = 'fas fa-check-circle';
                    if (i === 2) setTimeout(() => initLiveness(), 1000);
                }, (i + 1) * 300);
            });

        } catch (e) {
            console.error(e);
            if (window.showToast) window.showToast("Service connection error", "error");
            updateKycStep(1);
        }
    };


    async function initLiveness() {
        updateKycStep(4);
        updateInternalStepper(3);
        const video = document.getElementById('webcam');
        try {
            videoStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
            video.srcObject = videoStream;
        } catch (e) { console.error(e); }
    }

    window.beginLivenessSequence = async function() {
        const countdown = document.getElementById('selfie-countdown');
        const feedback = document.getElementById('liveness-feedback');
        document.getElementById('btn-begin-capture').style.display = 'none';
        
        selfieFrames = [];
        const prompts = ["Center your face", "Blink slowly", "Hold still..."];
        
        for (let i = 0; i < 3; i++) {
            feedback.innerText = prompts[i];
            countdown.style.display = 'block';
            for (let c = 3; c > 0; c--) {
                countdown.innerText = c;
                await new Promise(r => setTimeout(r, 800));
            }
            countdown.innerText = "📸";
            await new Promise(r => setTimeout(r, 200));
            countdown.style.display = 'none';
            
            saveSelfieFrame(i + 1);
            await new Promise(r => setTimeout(r, 500));
        }
        
        stopStream();
        updateKycStep(5);
        updateInternalStepper(4);
    };

    function saveSelfieFrame(idx) {
        const video = document.getElementById('webcam');
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        
        canvas.toBlob(blob => {
            selfieFrames.push(new File([blob], `selfie_${idx}.jpg`, { type: 'image/jpeg' }));
            const img = document.createElement('img');
            img.src = URL.createObjectURL(blob);
            img.style.cssText = "width: 70px; height: 70px; object-fit: cover; border-radius: 12px; border: 2px solid var(--kyc-accent);";
            document.getElementById('selfie-gallery').appendChild(img);
        }, 'image/jpeg', 0.9);
    }

    window.confirmIdentityReview = async function() {
        if (selfieFrames.length < 1) {
            if (window.showToast) window.showToast("Please capture your liveness photo", "error");
            return;
        }

        const btn = event.target.closest('button');
        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Securing...';

        // --- REAL API CALL: VERIFY FULL (Selfies) ---
        const formData = new FormData();
        selfieFrames.forEach((file, idx) => {
            formData.append('selfies', file);
        });

        try {
            const res = await fetch(`/api/bookings/${bookingId}/verify-full`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();

            if (!res.ok) {
                if (window.showToast) window.showToast(data.detail || "Selfie validation failed", "error");
                btn.disabled = false;
                btn.innerHTML = originalHtml;
                return;
            }

            // Success: Switch to Waiting Screen
            updateKycStep('waiting');
            
            // Start Real-time listener
            initKycWebSocket();
            
        } catch (e) {
            console.error(e);
            if (window.showToast) window.showToast("Network error", "error");
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    };

    let kycWs = null;
    function initKycWebSocket() {
        if (kycWs) return;
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const clientId = `kyc_${bookingId}_${Date.now()}`;
        kycWs = new WebSocket(`${protocol}//${window.location.host}/verification/ws/${clientId}`);
        
        kycWs.onmessage = function(event) {
            const data = JSON.parse(event.data);
            console.log("KYC WebSocket Message:", data);
            
            if (data.type === 'kyc_update') {
                if (data.status === 'approved' || data.status === 'manual_review_approved') {
                    if (window.showToast) window.showToast("Identity Verified by Caterer!", "success");
                    kycWs.close();
                    nextScreen(3, true); // Proceed to Payment
                } else if (data.status === 'rejected') {
                    if (window.showToast) window.showToast("Identity Verification Rejected: " + (data.reason || ""), "error");
                    kycWs.close();
                    kycWs = null;
                    updateKycStep(1); // Allow retry
                }
            }
        };

        kycWs.onclose = function() {
            kycWs = null;
            // Immediate fallback to polling if socket closes while still waiting
            if (document.getElementById('kyc-step-waiting').style.display !== 'none') {
                pollKycStatus();
            }
        };
    }

    async function pollKycStatus() {
        if (document.getElementById('kyc-step-waiting').style.display === 'none') return;
        
        try {
            const res = await fetch(`/api/bookings/${bookingId}/status`);
            const data = await res.json();
            
            if (data.status === 'approved') {
                nextScreen(3, true);
            } else if (data.status === 'rejected') {
                if (window.showToast) window.showToast("Verification Rejected", "error");
                updateKycStep(1);
            } else {
                // Check again in 4 seconds
                setTimeout(pollKycStatus, 4000);
            }
        } catch (e) {
            setTimeout(pollKycStatus, 5000);
        }
    }


    window.retryLiveness = function() {
        selfieFrames = [];
        document.getElementById('selfie-gallery').innerHTML = '';
        document.getElementById('btn-begin-capture').style.display = 'block';
        initLiveness();
    };

    window.resetKycStep = function(s) {
        stopStream();
        updateKycStep(s);
        if (s === 1) updateInternalStepper(1);
    };

    function updateKycStep(s) {
        document.querySelectorAll('.kyc-phase').forEach(p => p.style.display = 'none');
        const el = document.getElementById(`kyc-step-${s}`);
        if (el) el.style.display = 'block';
    }

    function updateInternalStepper(n) {
        document.querySelectorAll('.step-node').forEach((node, idx) => {
            const step = idx + 1;
            if (step < n) { node.classList.add('completed'); node.classList.remove('active'); }
            else if (step === n) { node.classList.add('active'); node.classList.remove('completed'); }
            else { node.classList.remove('active', 'completed'); }
        });
    }

    function stopStream() {
        if (videoStream) {
            videoStream.getTracks().forEach(t => t.stop());
            videoStream = null;
        }
    }

    // --- SUMMARY & FULFILLMENT ---
    window.updateCheckoutSummary = function() {
        const qty = parseInt(document.getElementById('quantity_input').value) || 1;
        const base = itemPrice * qty;
        const total = base + deliveryFee;
        
        document.getElementById('sum-base-price').innerText = '₱' + base.toLocaleString(undefined, { minimumFractionDigits: 2 });
        document.getElementById('sum-qty').innerText = 'x' + qty;
        document.getElementById('sum-delivery-fee').innerText = '₱' + deliveryFee.toLocaleString(undefined, { minimumFractionDigits: 2 });
        document.getElementById('sum-grand-total').innerText = '₱' + total.toLocaleString(undefined, { minimumFractionDigits: 2 });
    };

    window.updateFulfillment = function(el) {
        const cards = el.closest('.option-grid').querySelectorAll('.option-card');
        cards.forEach(c => c.classList.remove('selected'));
        el.parentElement.classList.add('selected');
        
        const addressSection = document.getElementById('address-section');
        if (el.value === 'pickup') {
            deliveryFee = 0;
            document.getElementById('delivery-row').style.display = 'none';
            if (addressSection) addressSection.classList.add('hidden-address');
        } else {
            deliveryFee = 150;
            document.getElementById('delivery-row').style.display = 'flex';
            if (addressSection) addressSection.classList.remove('hidden-address');
        }
        updateCheckoutSummary();
    };

    // Initial call to sync UI
    const defaultFulfillment = document.querySelector('input[name="fulfillment"]:checked');
    if (defaultFulfillment) window.updateFulfillment(defaultFulfillment);

    function calculateTotal() {
        return parseFloat(document.getElementById('sum-grand-total').innerText.replace(/[^\d.-]/g, ''));
    }

    function populateReview() {
        const form = document.getElementById('checkoutForm');
        document.getElementById('rev-name').innerText = form.full_name.value;
        document.getElementById('rev-phone').innerText = form.contact_number.value;
        document.getElementById('rev-datetime').innerText = `${form.delivery_date.value} @ ${form.delivery_time.value}`;
        
        const mode = form.fulfillment.value;
        document.getElementById('rev-location').innerText = mode === 'pickup' ? 'STORE PICKUP' : form.address.value;
    }

    // --- FINAL SUBMIT ---
    window.submitAtaCarteOrder = async function() {
        // Fallback recovery
        const currentId = getActiveBookingId();
        
        if (!currentId) {
            alert("Session lost. Please try going back to the first step to re-save your details.");
            console.error("[CHECKOUT] Submission failed: No bookingId found.");
            return;
        }

        const btn = document.getElementById('final-submit-btn');
        const loader = document.getElementById('place-order-loading');
        btn.disabled = true;
        loader.style.display = 'block';

        const form = document.getElementById('checkoutForm');
        const formData = new FormData(form);
        formData.append('booking_id', currentId);
        formData.append('caterer_id', catererId);
        formData.append('menu_id', menuId);
        formData.append('total_amount', calculateTotal());
        
        if (idFile) formData.append('id_file', idFile);
        if (selfieFrames.length > 0) {
            // Send first frame as primary selfie
            const reader = new FileReader();
            const b64 = await new Promise(r => {
                reader.onload = () => r(reader.result);
                reader.readAsDataURL(selfieFrames[0]);
            });
            formData.append('selfie_base64', b64);
        }

        try {
            const res = await fetch('/bookings/alacarte/checkout/submit', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.success) {
                sessionStorage.removeItem(sessionKey); // Clear session on success
                nextScreen(5, true);
            } else {
                const errMsg = data.message || (data.detail ? JSON.stringify(data.detail) : "Unknown Error");
                alert("Order Error: " + errMsg);
                btn.disabled = false;
                loader.style.display = 'none';
            }
        } catch (e) {
            alert("Network error.");
            btn.disabled = false;
            loader.style.display = 'none';
        }
    };
});
