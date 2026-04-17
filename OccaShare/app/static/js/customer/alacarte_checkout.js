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
    let idFile = null;
    let selfieFrames = [];
    let isMobile = () => /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

    // --- PERSISTENCE KEY ---
    const storageKey = `alc_checkout_${catererId}_${menuId}`;

    // --- SETUP DATE MIN ---
    const dateInput = document.getElementById('delivery_date');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.setAttribute('min', today);
    }

    // --- PROGRESS PERSISTENCE ---
    function saveFormProgress() {
        const form = document.getElementById('checkoutForm');
        if (!form) return;

        const data = {
            currentScreen: currentScreen,
            formData: {
                full_name: form.full_name?.value,
                contact_number: form.contact_number?.value,
                delivery_date: form.delivery_date?.value,
                delivery_time: form.delivery_time?.value,
                address: form.address?.value,
                quantity: form.quantity_input?.value,
                fulfillment: form.fulfillment?.value,
                payment_method: form.payment_method?.value,
                id_type: form.id_type?.value,
                id_number: form.id_number?.value
            }
        };
        localStorage.setItem(storageKey, JSON.stringify(data));
    }

    function loadFormProgress() {
        const saved = localStorage.getItem(storageKey);
        if (!saved) return;

        try {
            const data = JSON.parse(saved);
            const form = document.getElementById('checkoutForm');
            if (!form) return;

            if (data.formData) {
                const setVal = (fieldName, val) => {
                    const el = form.elements[fieldName] || document.getElementById(fieldName);
                    if (el && val !== undefined) el.value = val;
                };

                setVal('full_name', data.formData.full_name);
                setVal('contact_number', data.formData.contact_number);
                setVal('delivery_date', data.formData.delivery_date);
                setVal('delivery_time', data.formData.delivery_time);
                setVal('address', data.formData.address);
                setVal('quantity_input', data.formData.quantity);
                setVal('id_type', data.formData.id_type);
                setVal('id_number', data.formData.id_number);

                if (data.formData.fulfillment) {
                    const rad = form.querySelector(`input[name="fulfillment"][value="${data.formData.fulfillment}"]`);
                    if (rad) {
                        rad.checked = true;
                        updateFulfillment(rad);
                    }
                }

                if (data.formData.payment_method) {
                    const rad = form.querySelector(`input[name="payment_method"][value="${data.formData.payment_method}"]`);
                    if (rad) rad.checked = true;
                }
            }

            updateCheckoutSummary();
            
            // Restore screen if further than 1
            if (data.currentScreen > 1) {
                // Bypass validation during auto-restoration
                setTimeout(() => {
                    nextScreen(data.currentScreen, true);
                    // Re-run ID validation after navigation is stable
                    if (form.id_type && form.id_type.value) {
                        validateIdSelection();
                    }
                }, 300);
            }
        } catch (e) {
            console.error("Failed to load progress:", e);
        }
    }

    // --- HARDENED NAVIGATION ---
    window.nextScreen = function (screenNumber, force = false) {
        try {
            if (!force && screenNumber > currentScreen) {
                if (!validateScreen(currentScreen)) return;
            }
            
            const targetScreen = document.getElementById(`screen-${screenNumber}`);
            if (!targetScreen) {
                console.error("Screen not found:", screenNumber);
                return;
            }

            document.querySelectorAll('.checkout-screen').forEach(s => s.classList.remove('active'));
            targetScreen.classList.add('active');

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
            saveFormProgress();

            const sidebar = document.querySelector('.calculator-sidebar');
            const grid = document.querySelector('.details-grid');
            if (screenNumber === 2) {
                if (sidebar) sidebar.style.display = 'none';
                if (grid) grid.style.setProperty('grid-template-columns', '1fr', 'important');
            } else {
                if (sidebar) sidebar.style.display = 'block';
                if (grid) grid.style.setProperty('grid-template-columns', '1fr 350px', 'important');
            }

            if (screenNumber === 4) populateReview();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } catch (err) {
            console.error("Navigation error:", err);
            if (!force) alert("Navigation Error: " + err.message);
        }
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
                if (el && !el.value.trim()) {
                    showError(field.id, field.msg);
                    isValid = false;
                }
            });

            // Specific Phone Validation
            const phoneEl = document.getElementById('contact_number');
            if (phoneEl) {
                const phone = phoneEl.value.replace(/\D/g, '');
                if (phone.length !== 11 && phone.length > 0) {
                    showError('contact_number', 'err-contact_number');
                    isValid = false;
                }
            }
        }
        
        if (n === 2) {
            // In the new 5-step KYC sequence, the 'Next' button is only enabled when verified.
            // If the button is enabled, allow the screen change.
            const nextBtn = document.getElementById('id-next-btn');
            if (nextBtn && nextBtn.disabled) {
                if (window.showToast) window.showToast("Please complete the identity verification first.", "error");
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

    // Clear errors on input and Save progress
    document.querySelectorAll('.form-input, select, textarea, input[type="radio"]').forEach(input => {
        input.addEventListener('input', function() {
            if (this.classList.contains('form-input')) {
                this.classList.remove('error');
                const errId = 'err-' + (this.id || this.name);
                const errEl = document.getElementById(errId);
                if (errEl) errEl.classList.remove('show');
            }
            saveFormProgress();
        });
        input.addEventListener('change', saveFormProgress);
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

      // --- IDENTITY / KYC LOGIC (1:1 PORT FROM PACKAGE WIZARD) ---
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
        const idTypeEl = document.getElementById('id_type');
        const idNumberEl = document.getElementById('id_number');
        if (!idTypeEl || !idNumberEl) return;

        const idType = idTypeEl.value.trim();
        const idInput = idNumberEl;
        const validationMsg = document.getElementById('alc-id-validation-msg');
        const scanBox = document.getElementById('alc-option-scan');
        const uploadBox = document.getElementById('alc-option-upload');

        let value = idInput.value.trim();
        let isValid = false;

        // Reset state
        idInput.style.borderColor = '';
        if (validationMsg) {
            validationMsg.innerText = '';
            validationMsg.style.color = '';
        }

        const disableCard = (el) => {
            if (!el) return;
            el.classList.add('disabled');
            el.style.setProperty('opacity', '0.3', 'important');
            el.style.setProperty('pointer-events', 'none', 'important');
            el.style.borderColor = '';
            el.style.background = '';
        };

        const enableCard = (el) => {
            if (!el) return;
            el.classList.remove('disabled');
            el.style.setProperty('opacity', '1', 'important');
            el.style.setProperty('pointer-events', 'auto', 'important');
        };

        disableCard(scanBox);
        disableCard(uploadBox);

        if (idType && validationPatterns[idType]) {
            const pattern = validationPatterns[idType];
            const formatted = pattern.format(value);
            
            if (formatted !== value) {
                idInput.value = formatted;
                value = formatted;
            }
            
            isValid = pattern.regex.test(value);
            idInput.placeholder = pattern.placeholder;

            if (value.length === 0) {
                idInput.style.borderColor = 'var(--kyc-slate-200)';
                if (validationMsg) {
                    validationMsg.innerText = 'Enter your ' + idType + ' number.';
                    validationMsg.style.color = 'var(--kyc-slate-400)';
                }
            } else if (isValid) {
                idInput.style.borderColor = 'var(--kyc-accent)';
                if (validationMsg) {
                    validationMsg.innerHTML = '<i class="fas fa-check-circle"></i> Format valid';
                    validationMsg.style.color = 'var(--kyc-accent)';
                }

                enableCard(scanBox);
                enableCard(uploadBox);

                if (isMobile() && scanBox) {
                    scanBox.style.borderColor = 'var(--kyc-accent)';
                    scanBox.style.background = 'var(--kyc-accent-soft)';
                }
            } else {
                idInput.style.borderColor = '#ef4444';
                if (validationMsg) {
                    validationMsg.innerText = 'Invalid ' + idType + ' format';
                    validationMsg.style.color = '#ef4444';
                }
            }
        } else {
            idInput.placeholder = 'Enter ID number';
            if (validationMsg && idType) {
                validationMsg.innerText = 'Please select a valid ID type.';
                validationMsg.style.color = 'var(--kyc-slate-400)';
            }
        }

        saveFormProgress();
    };

    window.handleUploadClick = function() {
        if (document.getElementById('alc-option-upload').classList.contains('disabled')) {
            console.log("Upload clicked but card is disabled");
            return;
        }
        document.getElementById('id_document_input').click();
    };

    window.previewKycId = function(input) {
        if (input.files && input.files[0]) {
            idFile = input.files[0];
            const reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById('id-image-preview').src = e.target.result;
                idUploaded = true;
                updateInternalKycStep(2);
            };
            reader.readAsDataURL(idFile);
        }
    };

    window.startIdScanner = async function() {
        if (document.getElementById('alc-option-scan').classList.contains('disabled')) {
            console.log("Scan clicked but card is disabled");
            return;
        }
        updateInternalKycStep('scanner');
        const video = document.getElementById('id-scanner-webcam');
        try {
            videoStream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } } 
            });
            video.srcObject = videoStream;
        } catch (err) {
            console.warn("Rear camera failed, fallback to default", err);
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
        
        canvas.toBlob((blob) => {
            idFile = new File([blob], "id_capture.jpg", { type: "image/jpeg" });
            const reader = new FileReader();
            reader.onload = (e) => {
                document.getElementById('id-image-preview').src = e.target.result;
                idUploaded = true;
                stopVideoStream();
                updateInternalKycStep(2);
            };
            reader.readAsDataURL(idFile);
        }, 'image/jpeg', 0.95);
    };

    window.proceedToOcr = function() {
        updateInternalKycStep(3);
        updateStatusTracker(2);

        // Simulated QC Progress
        const stages = ['qc-resolution', 'qc-focus', 'qc-ocr'];
        stages.forEach((id, i) => {
            setTimeout(() => {
                const el = document.getElementById(id);
                if (el) {
                    el.style.color = 'var(--kyc-accent)';
                    el.querySelector('i').className = 'fas fa-check-circle';
                }
                if (i === stages.length - 1) {
                    setTimeout(() => initWebcamSubstep(), 800);
                }
            }, (i + 1) * 600);
        });
    };

    async function initWebcamSubstep() {
        updateInternalKycStep(4);
        updateStatusTracker(3);
        const video = document.getElementById('webcam');
        try {
            videoStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
            video.srcObject = videoStream;
        } catch (err) {
            console.error("Liveness webcam failed", err);
        }
    }

    window.beginLivenessSequence = async function() {
        const countdownEl = document.getElementById('selfie-countdown');
        const feedbackEl = document.getElementById('liveness-feedback');
        document.getElementById('btn-begin-capture').style.display = 'none';

        selfieFrames = [];
        const prompts = ["Look into the camera", "Blink slowly", "Stay still..."];

        for (let i = 0; i < 3; i++) {
            feedbackEl.innerText = prompts[i];
            countdownEl.style.display = 'block';
            for (let count = 3; count > 0; count--) {
                countdownEl.innerText = count;
                await new Promise(r => setTimeout(r, 800));
            }
            countdownEl.innerText = "📸";
            await new Promise(r => setTimeout(r, 200));
            countdownEl.style.display = 'none';

            captureSelfieFrame(i + 1);
            await new Promise(r => setTimeout(r, 500));
        }

        finalizeLiveness();
    };

    function captureSelfieFrame(index) {
        const video = document.getElementById('webcam');
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);

        canvas.toBlob((blob) => {
            const file = new File([blob], `selfie_${index}.jpg`, { type: 'image/jpeg' });
            selfieFrames.push(file);

            const gallery = document.getElementById('selfie-gallery');
            const img = document.createElement('img');
            img.src = URL.createObjectURL(blob);
            img.style.cssText = "width: 80px; height: 80px; object-fit: cover; border-radius: 12px; border: 2px solid var(--kyc-accent);";
            gallery.appendChild(img);
        }, 'image/jpeg', 0.9);
    }

    function finalizeLiveness() {
        stopVideoStream();
        updateInternalKycStep(5);
        updateStatusTracker(4);
    }

    window.retryLiveness = function() {
        selfieFrames = [];
        document.getElementById('selfie-gallery').innerHTML = '';
        document.getElementById('btn-begin-capture').style.display = 'block';
        initWebcamSubstep();
    };

    window.confirmIdentityReview = function() {
        faceCaptured = true;
        document.getElementById('id-next-btn').disabled = false;
        if (window.showToast) window.showToast("Identity verified successfully!", "success");
        else alert("Identity verified!");
    };

    function stopVideoStream() {
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
            videoStream = null;
        }
    }

    window.updateInternalKycStep = function(step) {
        document.querySelectorAll('.kyc-phase').forEach(p => p.style.display = 'none');
        const target = (typeof step === 'string') ? `kyc-step-${step}` : `kyc-step-${step}`;
        const el = document.getElementById(target);
        if (el) el.style.display = 'block';
    };

    function updateStatusTracker(step) {
        document.querySelectorAll('.step-node').forEach((node, index) => {
            if (index + 1 < step) {
                node.classList.add('completed');
                node.classList.remove('active');
            } else if (index + 1 === step) {
                node.classList.add('active');
                node.classList.remove('completed');
            } else {
                node.classList.remove('active', 'completed');
            }
        });
    }

    window.resetKycStep = function(step) {
        stopVideoStream();
        updateInternalKycStep(step);
        if (step === 1) updateStatusTracker(1);
    };

    // Initialize logic on load
    loadFormProgress();
    setTimeout(() => {
        if (document.getElementById('id_type')) window.validateIdSelection();
    }, 100);

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
        
        // Handle images from KYC flow
        if (idFile) {
            formData.set('id_file', idFile);
        }

        if (selfieFrames.length > 0) {
            // For A La Carte submit, we send the first frame as the primary selfie
            // Since the frames are Blobs in selfieFrames array (from captureFrame)
            // But the backend expects selfie_base64 or similar. 
            // In A La Carte JS, selfieFrames contains Blobs. Let's convert the first one to Base64.
            const reader = new FileReader();
            const base64Promise = new Promise(resolve => {
                reader.onload = () => resolve(reader.result);
                reader.readAsDataURL(selfieFrames[0]);
            });
            const b64 = await base64Promise;
            formData.append('selfie_base64', b64);
        }

        try {
            const response = await fetch('/bookings/alacarte/checkout/submit', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            if (result.success) {
                localStorage.removeItem(storageKey);
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
