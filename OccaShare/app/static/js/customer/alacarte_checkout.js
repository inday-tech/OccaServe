document.addEventListener('DOMContentLoaded', function () {
    const itemPrice = window.itemPrice || 0;
    const catererId = window.catererId;
    const menuId = window.menuId;

    let deliveryFee = 150;
    let currentScreen = 1;

    // Webcam Variables
    let videoStream = null;
    let faceCaptured = false;
    let idUploaded = false;

    // --- SETUP DATE MIN ---
    const dateInput = document.getElementById('delivery_date');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.setAttribute('min', today);
    }

    // --- SCREEN NAVIGATION ---
    window.nextScreen = function (screenNumber) {
        // Validation for each screen
        if (screenNumber > currentScreen) {
            if (!validateScreen(currentScreen)) return;
        }
        
        // Hide current, show next
        document.querySelectorAll('.checkout-screen').forEach(s => s.classList.remove('active'));
        document.getElementById(`screen-${screenNumber}`).classList.add('active');

        // Update stepper UI
        document.querySelectorAll('.mini-step').forEach((s, idx) => {
            if (idx + 1 < screenNumber) {
                s.classList.add('completed');
                s.classList.remove('active');
            } else if (idx + 1 === screenNumber) {
                s.classList.add('active');
                s.classList.remove('completed');
            } else {
                s.classList.remove('active', 'completed');
            }
        });

        currentScreen = screenNumber;

        // Toggle Sidebar Visibility for Identity Screen (Consistency)
        const sidebar = document.querySelector('.calculator-sidebar');
        const grid = document.querySelector('.details-grid');
        if (screenNumber === 2) {
            if (sidebar) sidebar.style.display = 'none';
            if (grid) grid.style.setProperty('grid-template-columns', '1fr', 'important');
        } else {
            if (sidebar) sidebar.style.display = 'block';
            if (grid) grid.style.setProperty('grid-template-columns', '1fr 350px', 'important');
        }

        // If entering Screen 4, populate review data
        if (screenNumber === 4) {
            populateReview();
        }

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    function validateScreen(n) {
        const form = document.getElementById('checkoutForm');
        let isValid = true;

        // Reset previous errors
        document.querySelectorAll('.field-error').forEach(el => el.classList.remove('show'));
        document.querySelectorAll('.form-input').forEach(el => el.classList.remove('error'));

        if (n === 1) {
            const requiredFields = [
                { id: 'full_name', msg: 'err-full_name' },
                { id: 'contact_number', msg: 'err-contact_number' },
                { id: 'delivery_date', msg: 'err-delivery_date' },
                { id: 'delivery_time', msg: 'err-delivery_time' },
                { id: 'address', msg: 'err-address' },
                { id: 'quantity_input', msg: 'err-quantity' }
            ];

            requiredFields.forEach(field => {
                const el = document.getElementById(field.id);
                if (!el.value.trim()) {
                    showError(field.id, field.msg);
                    isValid = false;
                }
            });

            // Specific validation
            const qtyInput = document.getElementById('quantity_input');
            const qty = parseInt(qtyInput.value) || 0;
            if (qty <= 0 || qty > 100) {
                showError('quantity_input', 'err-quantity');
                isValid = false;
            }

            // Specific Phone Validation
            const phone = document.getElementById('contact_number').value.replace(/\D/g, '');
            if (phone.length !== 11 && phone.length > 0) {
                showError('contact_number', 'err-contact_number');
                isValid = false;
            }
        }
        
        if (n === 2) {
            if (!idUploaded) {
                document.getElementById('err-id_file').classList.add('show');
                isValid = false;
            }
            if (!faceCaptured) {
                document.getElementById('err-selfie').classList.add('show');
                isValid = false;
            }
        }

        if (!isValid) {
            const firstError = document.querySelector('.field-error.show');
            if (firstError) firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        return isValid;
    }

    function showError(inputId, errorId) {
        const input = document.getElementById(inputId);
        const error = document.getElementById(errorId);
        if (input) input.classList.add('error');
        if (error) error.classList.add('show');
    }

    // Clear errors on input
    document.querySelectorAll('.form-input').forEach(input => {
        input.addEventListener('input', function() {
            this.classList.remove('error');
            const errId = 'err-' + (this.id || this.name);
            const errEl = document.getElementById(errId);
            if (errEl) errEl.classList.remove('show');
        });
    });

    const qtyField = document.getElementById('quantity_input');
    if (qtyField) {
        qtyField.addEventListener('change', updateCheckoutSummary);
    }

    // --- SUMMARY UPDATES ---
    window.updateCheckoutSummary = function () {
        const qty = parseInt(document.getElementById('quantity_input').value) || 1;
        const baseTotal = itemPrice * qty;
        const grandTotal = baseTotal + deliveryFee;

        document.getElementById('sum-base-price').innerText = '₱' + baseTotal.toLocaleString(undefined, { minimumFractionDigits: 2 });
        document.getElementById('sum-qty').innerText = 'x' + qty;
        document.getElementById('sum-delivery-fee').innerText = '₱' + deliveryFee.toLocaleString(undefined, { minimumFractionDigits: 2 });
        document.getElementById('sum-grand-total').innerText = '₱' + grandTotal.toLocaleString(undefined, { minimumFractionDigits: 2 });
    };

    window.updateFulfillment = function (radio) {
        const labels = radio.closest('.option-grid').querySelectorAll('.option-card');
        labels.forEach(l => l.classList.remove('selected'));
        radio.parentElement.classList.add('selected');

        if (radio.value === 'pickup') {
            deliveryFee = 0;
            const addrGroup = document.querySelector('textarea[name="address"]').closest('.form-group');
            if (addrGroup) addrGroup.style.display = 'none';
        } else {
            deliveryFee = 150;
            const addrGroup = document.querySelector('textarea[name="address"]').closest('.form-group');
            if (addrGroup) addrGroup.style.display = 'block';
        }
        updateCheckoutSummary();
    };

    // --- ID PREVIEW ---
    window.previewID = function (input) {
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = function (e) {
                const prev = document.getElementById('id-preview');
                prev.src = e.target.result;
                prev.style.display = 'block';
                idUploaded = true;
                checkIdentityCompletion();
            };
            reader.readAsDataURL(input.files[0]);
        }
    };

    // --- IDENTITY / KYC LOGIC (Package Sync) ---
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
        const validationMsg = document.getElementById('id-validation-msg');
        const scanBox = document.getElementById('option-scan');
        const uploadBox = document.getElementById('option-upload');

        if (!idInput) return;

        let value = idInput.value;
        let isValid = false;

        if (idType && validationPatterns[idType]) {
            const pattern = validationPatterns[idType];
            const formatted = pattern.format(value);
            if (formatted !== value) {
                idInput.value = formatted;
                value = formatted;
            }
            isValid = pattern.regex.test(value);
            idInput.placeholder = pattern.placeholder;

            if (value.length > 0) {
                if (isValid) {
                    idInput.style.setProperty('border-color', '#10b981', 'important');
                    idInput.style.setProperty('background', '#f0fdf4', 'important');
                    if (validationMsg) {
                        validationMsg.innerText = '✓ Format valid';
                        validationMsg.style.color = '#10b981';
                        validationMsg.style.display = 'block';
                    }
                } else {
                    idInput.style.setProperty('border-color', '#ef4444', 'important');
                    idInput.style.setProperty('background', '#fffafa', 'important');
                    if (validationMsg) {
                        validationMsg.innerText = 'Invalid ' + idType + ' format';
                        validationMsg.style.color = '#ef4444';
                        validationMsg.style.display = 'block';
                    }
                }
            } else {
                idInput.style.borderColor = '';
                idInput.style.background = '';
                if (validationMsg) validationMsg.innerText = '';
            }
        }

        if (idType && isValid) {
            scanBox.classList.remove('disabled');
            uploadBox.classList.remove('disabled');
            scanBox.style.setProperty('opacity', '1', 'important');
            uploadBox.style.setProperty('opacity', '1', 'important');
            scanBox.style.setProperty('cursor', 'pointer', 'important');
            uploadBox.style.setProperty('cursor', 'pointer', 'important');
            scanBox.style.setProperty('pointer-events', 'auto', 'important');
            uploadBox.style.setProperty('pointer-events', 'auto', 'important');
        } else {
            scanBox.classList.add('disabled');
            uploadBox.classList.add('disabled');
            scanBox.style.setProperty('opacity', '0.5', 'important');
            uploadBox.style.setProperty('opacity', '0.5', 'important');
            scanBox.style.setProperty('cursor', 'not-allowed', 'important');
            uploadBox.style.setProperty('not-allowed', 'pointer', 'important');
            scanBox.style.setProperty('pointer-events', 'none', 'important');
            uploadBox.style.setProperty('pointer-events', 'none', 'important');
        }
    };

    window.handleKycAction = function(method) {
        // Double check disabled status
        const uploadBox = document.getElementById('option-upload');
        if (uploadBox && uploadBox.classList.contains('disabled')) return;
        
        if (method === 'upload') {
            document.getElementById('id_document_input').click();
        } else {
            initIdScanner();
        }
    };

    async function initIdScanner() {
        updateInternalKycStep('scan'); // Using a custom string for the ID scanner phase
        const video = document.getElementById('id-scanner-webcam');
        try {
            videoStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
            video.srcObject = videoStream;
        } catch (err) {
            console.error(err);
            alert('Could not access rear camera. Using front camera instead.');
            try {
                videoStream = await navigator.mediaDevices.getUserMedia({ video: true });
                video.srcObject = videoStream;
            } catch (e) {
                alert('Camera access failed.');
            }
        }
    }

    window.captureIdPhoto = function() {
        const video = document.getElementById('id-scanner-webcam');
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const dataUrl = canvas.toDataURL('image/jpeg');
        document.getElementById('id-image-preview').src = dataUrl;
        
        // Stop ID Scanner stream
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
            videoStream = null;
        }
        
        updateInternalKycStep(2); // Move to Preview
        idUploaded = true;
        checkIdentityCompletion();
    };

    window.previewKycId = function(input) {
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById('id-image-preview').src = e.target.result;
                updateInternalKycStep(2);
                idUploaded = true;
                checkIdentityCompletion();
            };
            reader.readAsDataURL(input.files[0]);
        }
    };

    window.updateInternalKycStep = function(step) {
        document.querySelectorAll('.kyc-phase').forEach(p => p.style.display = 'none');
        
        const phaseId = (typeof step === 'string') ? `kyc-phase-${step}` : `kyc-phase-${step}`;
        const phaseEl = document.getElementById(phaseId);
        if (phaseEl) phaseEl.style.display = 'block';
        
        // Stepper Nodes (Details: 1, Document: 2, Biometrics: 3, Process: 4)
        document.querySelectorAll('.sub-step').forEach((node, i) => {
            let active = false;
            if (step === 'scan') active = (i === 1); // Document phase
            else if (typeof step === 'number') active = (i+1) <= step;
            node.classList.toggle('active', active);
        });
    };

    window.resetKycStep = function(step) {
        updateInternalKycStep(step);
        idUploaded = false;
        faceCaptured = false;
        checkIdentityCompletion();
    };

    window.proceedToOcr = function() {
        updateInternalKycStep(3);
        
        // Simulated OCR Success
        setTimeout(() => document.getElementById('qc-res').classList.add('success'), 600);
        setTimeout(() => document.getElementById('qc-align').classList.add('success'), 1200);
        setTimeout(() => {
            document.getElementById('qc-ocr').classList.add('success');
            setTimeout(() => {
                initWebcamSubstep();
            }, 800);
        }, 1800);
    };

    async function initWebcamSubstep() {
        updateInternalKycStep(4);
        const video = document.getElementById('webcam');
        try {
            videoStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
            video.srcObject = videoStream;
        } catch (err) {
            console.error(err);
            alert('Camera access failed.');
        }
    }

    // --- WEBCAM LOGIC (Refined for Phase 4) ---
    window.captureSelfie = function () {
        const video = document.getElementById('webcam');
        const canvas = document.createElement('canvas'); // hidden canvas
        const context = canvas.getContext('2d');
        
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const dataUrl = canvas.toDataURL('image/jpeg');
        document.getElementById('selfie-preview').src = dataUrl;
        
        // UI Switch
        document.getElementById('webcam-section').style.display = 'none';
        document.getElementById('selfie-preview-container').style.display = 'block';

        faceCaptured = true;
        checkIdentityCompletion();
        
        // Stop stream
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
        }
    };

    window.resetSelfie = function () {
        faceCaptured = false;
        document.querySelector('.webcam-box').style.display = 'block';
        document.getElementById('start-webcam-btn').style.display = 'block';
        document.getElementById('selfie-preview-container').style.display = 'none';
        checkIdentityCompletion();
    };

    function checkIdentityCompletion() {
        if (idUploaded && faceCaptured) {
            document.getElementById('id-next-btn').disabled = false;
        } else {
            document.getElementById('id-next-btn').disabled = true;
        }
    }

    // --- REVIEW POPULATION ---
    function populateReview() {
        const form = document.getElementById('checkoutForm');
        document.getElementById('rev-name').innerText = form.full_name.value;
        document.getElementById('rev-datetime').innerText = form.delivery_date.value + ' @ ' + form.delivery_time.value;
        
        const fulfillment = form.fulfillment.value;
        if (fulfillment === 'pickup') {
            document.getElementById('rev-location').innerText = 'PICKUP AT STORE';
        } else {
            document.getElementById('rev-location').innerText = form.address.value;
        }
        
        document.getElementById('rev-paymode').innerText = form.payment_method.value;
    }

    // --- FINAL SUBMISSION ---
    window.submitAtaCarteOrder = async function() {
        const btn = document.getElementById('final-submit-btn');
        const loading = document.getElementById('place-order-loading');
        
        btn.disabled = true;
        loading.style.display = 'block';

        const form = document.getElementById('checkoutForm');
        const formData = new FormData(form);
        
        // Add images and extra data
        formData.append('caterer_id', catererId);
        formData.append('menu_id', menuId);
        formData.append('total_amount', parseFloat(document.getElementById('sum-grand-total').innerText.replace(/[^\d.-]/g, '')));
        
        // Handle captured IDs (if from camera)
        const idImg = document.getElementById('id-image-preview').src;
        if (idImg.startsWith('data:')) {
            // Convert dataURL to blob for id_file
            const blob = await (await fetch(idImg)).blob();
            formData.set('id_file', blob, 'id_capture.jpg');
        }

        const selfieImg = document.getElementById('selfie-preview').src;
        if (selfieImg.startsWith('data:')) {
            formData.append('selfie_base64', selfieImg);
        }

        try {
            const response = await fetch('/bookings/alacarte/checkout/submit', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            if (result.success) {
                nextScreen(5);
            } else {
                alert('Order failed: ' + result.message);
                btn.disabled = false;
                loading.style.display = 'none';
            }
        } catch (e) {
            console.error(e);
            alert('An error occurred. Please try again.');
            btn.disabled = false;
            loading.style.display = 'none';
        }
    };
});
