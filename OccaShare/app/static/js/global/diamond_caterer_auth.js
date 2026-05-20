/**
 * DIAMOND STANDARD CATERER AUTH LOGIC
 * Handles multi-step navigation and geographic data site-wide.
 */

(function () {
    let currentStepCat = 1;
    const totalStepsCat = 4;

    const LAGUNA_DATA = {
        "Santa Cruz": [
            "Alipit", "Bagumbayan", "Bubukal", "Calios", "Duhat",
            "Gatid", "Jasaan", "Labuin", "Malinao", "Oogong",
            "Pagsawitan", "Palasan", "Patimbao", "Poblacion I",
            "Poblacion II", "Poblacion III", "Poblacion IV",
            "Poblacion V", "San Jose", "San Juan", "San Pablo Norte",
            "San Pablo Sur", "Santisima Cruz", "Santo Angel Central",
            "Santo Angel Norte", "Santo Angel Sur"
        ]
    };

    window.changeStepCat = async function (n) {
        const form = document.getElementById('catererForm');
        if (!form) return;
        const steps = form.querySelectorAll('.form-step');
        const pSteps = document.querySelectorAll('.progress-step');

        // Progress to next step only if current is valid
        if (n === 1) {
            const stepValid = await validateCurrentStepCat();
            if (!stepValid) return;
        }

        steps[currentStepCat - 1].classList.remove('active');
        currentStepCat += n;

        if (currentStepCat > totalStepsCat) {
            submitCatererForm();
            currentStepCat = totalStepsCat;
            return;
        }

        steps[currentStepCat - 1].classList.add('active');

        // Update Progress Tracker
        pSteps.forEach((s, idx) => {
            if (idx + 1 < currentStepCat) s.className = 'progress-step completed';
            else if (idx + 1 === currentStepCat) s.className = 'progress-step active';
            else s.className = 'progress-step';
        });

        // Update Buttons
        const prevBtn = document.getElementById('prevBtnCat');
        const nextBtn = document.getElementById('nextBtnCat');
        if (prevBtn) prevBtn.style.display = currentStepCat === 1 ? 'none' : 'block';

        if (nextBtn) {
            const btnText = nextBtn.querySelector('span') || nextBtn;
            if (btnText === nextBtn) {
                nextBtn.innerText = currentStepCat === totalStepsCat ? 'Complete Registration' : 'Next Step';
            } else {
                btnText.innerText = currentStepCat === totalStepsCat ? 'Complete Registration' : 'Next Step';
            }
        }
    };

    async function validateCurrentStepCat() {
        const step = document.getElementById(`step-${currentStepCat}`);
        if (!step) return true;

        let valid = true;

        // 1. Force touched class and trigger input dispatch on all fields in this step
        const inputs = step.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.classList.add('touched');
            input.dispatchEvent(new Event('input', { bubbles: true }));
        });

        // 2. Perform formatting checks for Step 1
        if (currentStepCat === 1) {
            // First Name, Middle Name, Last Name
            const fnEl = document.getElementById('first_name_cat');
            const mnEl = document.getElementById('middle_name_cat');
            const lnEl = document.getElementById('last_name_cat');

            const fnVal = (fnEl?.value || '').trim();
            const mnVal = (mnEl?.value || '').trim();
            const lnVal = (lnEl?.value || '').trim();

            // Check formats using central diamondValidators
            if (fnEl) {
                const res = window.diamondValidators.name(fnVal);
                window.setDiamondError('firstNameCat', res.message, !res.valid);
                if (!res.valid) valid = false;
            }
            if (lnEl) {
                const res = window.diamondValidators.name(lnVal);
                window.setDiamondError('lastNameCat', res.message, !res.valid);
                if (!res.valid) valid = false;
            }
            if (mnEl && mnVal) {
                const res = window.diamondValidators.name(mnVal);
                window.setDiamondError('middleNameCat', res.message, !res.valid);
                if (!res.valid) valid = false;
            }

            // Cross check names identically
            if (fnVal && lnVal && fnVal.toLowerCase() === lnVal.toLowerCase()) {
                window.setDiamondError('firstNameCat', "First & Last name cannot be identical");
                window.setDiamondError('lastNameCat', "First & Last name cannot be identical");
                valid = false;
            }
            if (fnVal && mnVal && fnVal.toLowerCase() === mnVal.toLowerCase()) {
                window.setDiamondError('firstNameCat', "First & Middle name cannot be identical");
                window.setDiamondError('middleNameCat', "First & Middle name cannot be identical");
                valid = false;
            }
            if (mnVal && lnVal && mnVal.toLowerCase() === lnVal.toLowerCase()) {
                window.setDiamondError('middleNameCat', "Middle & Last name cannot be identical");
                window.setDiamondError('lastNameCat', "Middle & Last name cannot be identical");
                valid = false;
            }

            // Email Format
            const emailEl = document.getElementById('email_cat');
            if (emailEl) {
                const res = window.diamondValidators.email(emailEl.value);
                window.setDiamondError('emailCat', res.message, !res.valid);
                if (!res.valid) valid = false;
            }

            // Mobile Format
            const mobileEl = document.getElementById('mobile_number_cat');
            if (mobileEl) {
                const res = window.diamondValidators.mobile(mobileEl.value);
                window.setDiamondError('mobileCat', res.message, !res.valid);
                if (!res.valid) valid = false;
            }

            // Passwords Format
            const passEl = document.getElementById('password_cat');
            const confirmEl = document.getElementById('confirm_password_cat');
            if (passEl) {
                const res = window.diamondValidators.password(passEl.value);
                window.setDiamondError('passwordCat', res.message, !res.valid);
                if (!res.valid) valid = false;
            }
            if (confirmEl) {
                if (passEl && passEl.value !== confirmEl.value) {
                    window.setDiamondError('confirmCat', "Passwords do not match");
                    valid = false;
                } else if (!confirmEl.value) {
                    window.setDiamondError('confirmCat', "Required");
                    valid = false;
                }
            }

            // If the formatting validation passed so far, perform awaited AJAX uniqueness checks
            if (valid) {
                if (emailEl && emailEl.value) {
                    try {
                        const response = await fetch(`/auth/check-email?email=${encodeURIComponent(emailEl.value)}`);
                        const data = await response.json();
                        if (!data.available) {
                            window.setDiamondError('emailCat', data.message || "Email already taken");
                            valid = false;
                        }
                    } catch (err) { console.error("Email uniqueness check failed", err); }
                }

                if (mobileEl && mobileEl.value) {
                    const cleanPhone = mobileEl.value.replace(/\s/g, '');
                    try {
                        const response = await fetch(`/auth/check-phone?phone=${encodeURIComponent(cleanPhone)}`);
                        const data = await response.json();
                        if (!data.available) {
                            window.setDiamondError('mobileCat', data.message || "This number is already registered.");
                            valid = false;
                        }
                    } catch (err) { console.error("Phone uniqueness check failed", err); }
                }
            }
        }

        // 3. Perform formatting checks for Step 2
        if (currentStepCat === 2) {
            const bizNameEl = document.getElementById('business_name');
            if (bizNameEl) {
                const res = window.diamondValidators.businessNameFormat(bizNameEl.value);
                window.setDiamondError('businessName', res.message, !res.valid);
                if (!res.valid) valid = false;
            }

            const cityEl = document.getElementById('city_cat');
            if (cityEl && (!cityEl.value || cityEl.value.trim() === '')) {
                window.setDiamondError('cityCat', "Required");
                valid = false;
            }

            const brgyEl = document.getElementById('barangay_cat');
            if (brgyEl && (!brgyEl.value || brgyEl.value.trim() === '')) {
                window.setDiamondError('barangayCat', "Required");
                valid = false;
            }

            const streetEl = document.getElementById('street_cat');
            if (streetEl && (!streetEl.value || streetEl.value.trim() === '')) {
                window.setDiamondError('streetCat', "Required");
                valid = false;
            }

            const bizTypeEl = document.getElementById('business_type');
            if (bizTypeEl && (!bizTypeEl.value || bizTypeEl.value.trim() === '')) {
                window.setDiamondError('businessType', "Required");
                valid = false;
            }

            const yearsEl = document.getElementById('years_of_operation');
            if (yearsEl) {
                const res = window.diamondValidators.years(yearsEl.value);
                window.setDiamondError('years', res.message, !res.valid);
                if (!res.valid) valid = false;
            }

            const descEl = document.getElementById('business_description');
            if (descEl && (!descEl.value || descEl.value.trim() === '')) {
                window.setDiamondError('description', "Required");
                valid = false;
            }

            // If formatting passed, run awaited business name uniqueness check
            if (valid && bizNameEl && bizNameEl.value) {
                try {
                    const response = await fetch(`/auth/check-business-name?name=${encodeURIComponent(bizNameEl.value)}`);
                    const data = await response.json();
                    if (!data.available) {
                        window.setDiamondError('businessName', "Business name already registered");
                        valid = false;
                    }
                } catch (err) { console.error("Business uniqueness check failed", err); }
            }
        }

        // 4. Perform formatting checks for Step 3
        if (currentStepCat === 3) {
            const minPaxEl = document.getElementById('min_pax');
            if (minPaxEl) {
                const res = window.diamondValidators.minPax(minPaxEl.value);
                window.setDiamondError('minPax', res.message, !res.valid);
                if (!res.valid) valid = false;
            }

            const priceEl = document.getElementById('starting_price');
            if (priceEl) {
                const res = window.diamondValidators.price(priceEl.value);
                window.setDiamondError('price', res.message, !res.valid);
                if (!res.valid) valid = false;
            }

            // Event Types Validation
            const eventCheckboxes = step.querySelectorAll('input[name="event_type_choice"]:checked');
            const eventErrorDrawer = document.getElementById('eventTypeError');
            if (eventCheckboxes.length === 0) {
                valid = false;
                if (eventErrorDrawer) {
                    eventErrorDrawer.innerText = "Please select at least one event type";
                    eventErrorDrawer.style.display = 'block';
                }
            } else {
                let otherError = false;
                const otherCheck = document.getElementById('eventOtherCheck');
                if (otherCheck && otherCheck.checked) {
                    const otherInput = document.getElementById('event_type_other');
                    if (!otherInput || !otherInput.value.trim()) {
                        valid = false;
                        otherError = true;
                        if (eventErrorDrawer) {
                            eventErrorDrawer.innerText = "Please specify the other event type";
                            eventErrorDrawer.style.display = 'block';
                        }
                        if (otherInput) otherInput.style.borderColor = '#ef4444';
                    } else {
                        if (otherInput) otherInput.style.borderColor = '';
                    }
                }

                if (!otherError && eventErrorDrawer) {
                    eventErrorDrawer.style.display = 'none';
                }
            }

            // Sample Menu Validation
            const menuInput = document.getElementById('sample_menu_cat');
            const menuBox = document.getElementById('menuBoxCat');
            const menuError = document.getElementById('menuErrorCat');
            if (menuInput && menuBox) {
                if (menuInput.files.length === 0 && !menuBox.classList.contains('scanned-success')) {
                    valid = false;
                    menuBox.style.borderColor = '#ef4444';
                    if (menuError) {
                        menuError.innerText = "Sample Menu is required";
                        menuError.style.display = 'block';
                        menuError.style.color = '#ef4444';
                    }
                } else {
                    menuBox.style.borderColor = '';
                    if (menuError && menuError.innerText === "Sample Menu is required") {
                        menuError.innerText = "";
                        menuError.style.display = 'none';
                    }
                }
            }
        }

        // 5. Step 4 Verification Check
        if (currentStepCat === 4) {
            const permitScanned = document.getElementById('permitBoxCat').classList.contains('scanned-success');
            const idScanned = document.getElementById('govIdBoxCat').classList.contains('scanned-success');
            const selfieScanned = document.getElementById('selfieBoxCat').classList.contains('scanned-success');

            if (!permitScanned || !idScanned || !selfieScanned) {
                if (window.Swal) {
                    Swal.fire({
                        icon: 'warning',
                        title: 'Verification Incomplete',
                        text: 'Please ensure your Permit, ID, and Selfie are successfully verified before proceeding.',
                        confirmButtonColor: '#f97316'
                    });
                }
                valid = false;
            }
        }

        // 6. Generic check for any element with .input-wrapper.error inside the current step
        const errorWrappers = step.querySelectorAll('.input-wrapper.error');
        if (errorWrappers.length > 0) {
            valid = false;
            // Focus on the first error field
            errorWrappers[0].querySelector('input, select, textarea')?.focus();
        }

        // Sync full name if on Step 1
        if (currentStepCat === 1 && typeof window.composeFullNameCat === 'function') {
            window.composeFullNameCat();
        }

        return valid;
    }

    async function submitCatererForm() {
        const form = document.getElementById('catererForm');
        if (!form) return;

        // Final Verification Safeguard
        const permitScanned = document.getElementById('permitBoxCat').classList.contains('scanned-success');
        const idScanned = document.getElementById('govIdBoxCat').classList.contains('scanned-success');
        const selfieScanned = document.getElementById('selfieBoxCat').classList.contains('scanned-success');

        if (!permitScanned || !idScanned || !selfieScanned) {
            if (window.Swal) {
                Swal.fire({
                    icon: 'error',
                    title: 'Security Check Required',
                    text: 'Full identity verification is required. Please follow the instructions in Step 4.',
                    confirmButtonColor: '#f97316'
                });
            }
            return;
        }

        const formData = new FormData(form);
        const submitBtn = document.getElementById('nextBtnCat');

        if (submitBtn) submitBtn.disabled = true;
        const originalText = submitBtn.innerHTML;
        submitBtn.innerText = 'Creating Account...';

        try {
            updateAddressCat();

            // Consolidate checkboxes
            const checkboxes = form.querySelectorAll('input[name="event_type_choice"]:checked');
            const eventTypes = Array.from(checkboxes).map(cb => cb.value).join(',');
            formData.set('event_types', eventTypes);

            // Sanitize numeric fields (remove commas)
            const numericFields = ['min_pax', 'starting_price', 'years_of_operation'];
            numericFields.forEach(f => {
                const val = formData.get(f);
                if (val) formData.set(f, val.toString().replace(/,/g, ''));
            });

            const response = await fetch('/auth/register', {
                method: 'POST',
                body: formData
            });

            if (response.redirected) {
                window.location.href = response.url;
            } else {
                const result = await response.json();
                if (result.status === 'success' || result.redirect) {
                    window.location.href = result.redirect || '/auth/verify-email';
                } else if (window.Swal) {
                    Swal.fire({ icon: 'error', title: 'Registration Failed', text: result.message || 'Please check your information.' });
                }
            }
        } catch (error) {
            console.error('Registration error:', error);
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        }
    }

    function updateAddressCat() {
        const prov = "Laguna";
        const city = document.getElementById('city_cat')?.value;
        const brgy = document.getElementById('barangay_cat')?.value;
        const street = document.getElementById('street_cat')?.value;
        const hiddenAddress = document.getElementById('address_cat_hidden');
        if (hiddenAddress && city && brgy) {
            hiddenAddress.value = `${street || ''}, ${brgy}, ${city}, ${prov}`;
        }
    }

    let lastUploadedIdPath = null;
    let streamCat = null;

    window.updateFileNameCat = function (input, targetId) {
        const display = document.getElementById(targetId);
        if (display && input.files && input.files[0]) {
            display.innerText = input.files[0].name;
            display.style.color = 'var(--auth-primary)';
        }
    };

    let currentScanTypeCat = null;

    window.isMobileDeviceCat = function () {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    };

    window.isWebcamSupportedCat = function () {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    };

    /**
     * UNIVERSAL SCANNING HANDLER
     * Handles Permit, ID, and Selfie scans across all devices.
     */
    window.startUniversalScanCat = async function (type) {
        currentScanTypeCat = type;

        // Log for debugging cross-device behavior
        console.log(`[KYC] Initiating ${type} scan. Device: ${window.isMobileDeviceCat() ? 'Mobile' : 'Desktop'}`);

        // MOBILE FLOW: Use native camera app (highest doc clarity)
        if (window.isMobileDeviceCat()) {
            window.triggerNativeCaptureCat(type);
            return;
        }

        // DESKTOP FLOW: Use Live Scanner Modal
        if (!window.isWebcamSupportedCat()) {
            alert("Webcam not supported. Please upload a file manually.");
            window.triggerNativeCaptureCat(type);
            return;
        }

        openScannerModalCat(type);
    };

    window.triggerNativeCaptureCat = function (type) {
        const inputId = type === 'permit' ? 'permit_cat' : (type === 'id' ? 'gov_id_cat' : 'selfie_cat');
        const input = document.getElementById(inputId);
        if (input) input.click();
    };

    async function openScannerModalCat(type) {
        const idTypeSelect = document.getElementById('id_type') || document.getElementById('id_type_cat');
        const idType = idTypeSelect ? idTypeSelect.value : '';
        const idNumberInput = document.getElementById('id_number') || document.getElementById('id_number_cat');
        const idNumber = idNumberInput ? idNumberInput.value.trim() : '';

        if (type === 'id' && !idType) {
            Swal.fire('Requirement', 'Please select an ID Type first!', 'warning');
            return;
        }

        if (type === 'id' && !idNumber) {
            Swal.fire('Requirement', 'Please enter your ID Number first before scanning.', 'warning');
            if (idNumberInput) idNumberInput.focus();
            return;
        }

        if (!window.Swal) return;

        // === SELFIE: Show Liveness Warning Screen First ===
        if (type === 'selfie') {
            const warningResult = await Swal.fire({
                title: '',
                html: `
                    <div style="text-align:left; font-family:'Poppins',sans-serif; position:relative; padding: 0.5rem;">
                        <button type="button" class="swal2-close" onclick="Swal.close()" style="position:absolute; top:-10px; right:0; display:block !important; font-size:1.5rem; color:#1e293b;">&times;</button>
                        
                        <h2 style="font-size:1.5rem; font-weight:800; color:#1e293b; margin-bottom:0.5rem;">Take Live Selfie</h2>
                        <p style="font-size:0.85rem; color:#475569; margin-bottom:1.25rem; line-height:1.5;">
                            You will go through a face verification process to prove that you are a real person.
                        </p>
                        
                        <div style="background:#fffbeb; border:1px solid #fde68a; border-radius:0.75rem; padding:1rem; margin-bottom:1.5rem; display:flex; align-items:flex-start; gap:1rem;">
                            <div style="background:#fef3c7; width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                                <i class="fas fa-exclamation-triangle" style="color:#d97706; font-size:0.8rem;"></i>
                            </div>
                            <div>
                                <div style="font-weight:700; color:#92400e; font-size:0.85rem;">Photosensitivity warning</div>
                                <div style="font-size:0.75rem; color:#b45309; line-height:1.4; margin-top:2px;">This check displays colored lights. Use caution if you are photosensitive.</div>
                            </div>
                        </div>
                        
                        <p style="font-size:0.95rem; font-weight:700; color:#1e293b; text-align:center; margin-bottom:1.5rem; letter-spacing:-0.01em;">
                            Align your face and press Start Liveness to proceed
                        </p>

                        <div style="margin-bottom:1.5rem; text-align:center;">
                            <img src="/static/img/liveness_guide.png" style="width:100%; max-width:300px; border-radius:12px;" alt="Liveness Guide">
                            <div style="display:grid; grid-template-columns:1fr 1fr; margin-top:0.5rem; font-size:0.75rem; font-weight:600;">
                                <div style="color:#10b981;">Good Fit</div>
                                <div style="color:#ef4444;">Too Far</div>
                            </div>
                        </div>

                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:2rem;">
                            <div style="display:flex; flex-direction:column; align-items:center; gap:0.5rem; text-align:center;">
                                <div style="width:32px; height:32px; background:#ecfdf5; border-radius:50%; display:flex; align-items:center; justify-content:center;">
                                    <i class="fas fa-check" style="color:#10b981; font-size:0.8rem;"></i>
                                </div>
                                <span style="font-size:0.65rem; color:#475569; font-weight:600; line-height:1.2;">Hijab-friendly verification</span>
                            </div>
                            <div style="display:flex; flex-direction:column; align-items:center; gap:0.5rem; text-align:center;">
                                <div style="width:32px; height:32px; background:#fef2f2; border-radius:50%; display:flex; align-items:center; justify-content:center;">
                                    <i class="fas fa-times" style="color:#ef4444; font-size:0.8rem;"></i>
                                </div>
                                <span style="font-size:0.65rem; color:#475569; font-weight:600; line-height:1.2;">Avoid wearing cap</span>
                            </div>
                            <div style="display:flex; flex-direction:column; align-items:center; gap:0.5rem; text-align:center;">
                                <div style="width:32px; height:32px; background:#ecfdf5; border-radius:50%; display:flex; align-items:center; justify-content:center;">
                                    <i class="fas fa-check" style="color:#10b981; font-size:0.8rem;"></i>
                                </div>
                                <span style="font-size:0.65rem; color:#475569; font-weight:600; line-height:1.2;">Use enough lighting</span>
                            </div>
                            <div style="display:flex; flex-direction:column; align-items:center; gap:0.5rem; text-align:center;">
                                <div style="width:32px; height:32px; background:#fef2f2; border-radius:50%; display:flex; align-items:center; justify-content:center;">
                                    <i class="fas fa-times" style="color:#ef4444; font-size:0.8rem;"></i>
                                </div>
                                <span style="font-size:0.65rem; color:#475569; font-weight:600; line-height:1.2;">Avoid wearing glasses</span>
                            </div>
                        </div>

                        <p style="font-size:0.7rem; color:#64748b; line-height:1.4; text-align:center; margin-bottom:1.5rem;">
                            By proceeding, you allow the collection, use, and disclosure of your personal data for identity verification and safety purposes.
                        </p>
                    </div>
                `,
                confirmButtonText: '<i class="fas fa-play"></i> Start Liveness',
                confirmButtonColor: '#2563eb',
                showCancelButton: true,
                cancelButtonText: 'Cancel',
                reverseButtons: true,
                allowOutsideClick: false,
                customClass: {
                    popup: 'premium-auth-swal',
                    confirmButton: 'swal2-confirm-liveness'
                },
                showCloseButton: true
            });

            if (!warningResult.isConfirmed) return;
        }

        // === Proceed to Camera Modal ===
        const title = type === 'permit' ? 'Scan Business Permit' : (type === 'id' ? `Scan ${idType}` : 'Live Face Verification');

        Swal.fire({
            title: title,
            html: `
                <div class="scanner-modal-wrap" style="display: flex; flex-direction: column; align-items: center; padding: 1rem;">
                    <div id="scannerInstructions" class="scanner-instruction-banner" style="background: #f0fdf4; color: #15803d; font-size: 0.85rem; font-weight: 600; padding: 0.5rem 1rem; border-radius: 999px; margin-bottom: 1.25rem; border: 1px solid rgba(21, 128, 61, 0.2);">Preparing Camera...</div>
                    <div class="scanner-preview-container" style="position: relative; width: 100%; max-width: 360px; aspect-ratio: ${type === 'selfie' ? '1' : '4/3'}; border-radius: ${type === 'selfie' ? '50%' : '1.5rem'}; overflow: hidden; border: 4px solid ${type === 'selfie' ? '#2563eb' : '#e2e8f0'}; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
                        <video id="modalWebcamVideo" autoplay playsinline style="width: 100%; height: 100%; object-fit: cover;"></video>
                        <canvas id="modalWebcamCanvas" style="display:none;"></canvas>
                        ${type !== 'selfie' ? '<div class="scanner-laser" style="position: absolute; width: 100%; height: 3px; background: #f97316; box-shadow: 0 0 12px #f97316; opacity: 0.8; left: 0; top: 0; animation: scan-laser-move 2s infinite ease-in-out;"></div>' : ''}
                        <div class="scanner-guide-frame ${type}" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); border: 2px dashed rgba(255, 255, 255, 0.7); pointer-events: none; z-index: 10;
                            ${type === 'selfie' ? 'width: 180px; height: 180px; border-radius: 50%;' : 'width: 80%; height: 60%; border-radius: 0.5rem;'}"></div>
                    </div>
                    <div id="livenessStepIndicator" style="margin-top:1rem; display:${type === 'selfie' ? 'flex' : 'none'}; gap:0.5rem; align-items:center;">
                        <div id="stepDot1" style="width:10px; height:10px; border-radius:50%; background:#2563eb; transition:all 0.3s;"></div>
                        <div id="stepDot2" style="width:10px; height:10px; border-radius:50%; background:#cbd5e1; transition:all 0.3s;"></div>
                        <div id="stepDot3" style="width:10px; height:10px; border-radius:50%; background:#cbd5e1; transition:all 0.3s;"></div>
                    </div>
                    <p class="scanner-hint" id="scannerHint" style="font-size: 0.8rem; color: #64748b; font-weight: 500; margin-top: 1rem;">Align your ${type === 'selfie' ? 'face' : 'document'} comfortably inside the bounds.</p>
                    
                    <style>
                        @keyframes scan-laser-move {
                            0% { top: 0%; }
                            50% { top: 100%; }
                            100% { top: 0%; }
                        }
                    </style>
                </div>
            `,
            showCancelButton: true,
            confirmButtonText: type === 'selfie' ? '🔍 Verifying...' : '📸 Capture',
            confirmButtonColor: type === 'selfie' ? '#2563eb' : '#f97316',
            cancelButtonText: 'Cancel',
            reverseButtons: true,
            allowOutsideClick: false,
            showConfirmButton: type !== 'selfie',
            didOpen: async () => {
                const video = document.getElementById('modalWebcamVideo');
                const instr = document.getElementById('scannerInstructions');
                try {
                    try {
                        streamCat = await navigator.mediaDevices.getUserMedia({
                            video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } }
                        });
                    } catch (e) {
                        console.warn("Failed to load with ideal constraints, falling back to default video.");
                        streamCat = await navigator.mediaDevices.getUserMedia({ video: true });
                    }
                    if (video) {
                        video.srcObject = streamCat;
                        video.setAttribute("playsinline", true);
                        video.setAttribute("autoplay", true);
                        video.onloadedmetadata = () => {
                            video.play().catch(err => console.error("Error playing video:", err));
                        };
                    }
                    if (instr) instr.innerText = type === 'selfie' ? "Center your face in the frame" : "Align document";

                    // Auto-start liveness sequence for selfie
                    if (type === 'selfie') {
                        setTimeout(async () => {
                            const result = await captureSequenceCat();
                            if (result) Swal.close();
                        }, 800);
                    }
                } catch (err) {
                    Swal.showValidationMessage(`Camera Error: ${err.message}`);
                    setTimeout(() => Swal.close(), 2000);
                }
            },

            preConfirm: async () => {
                if (type === 'selfie') {
                    return true;
                } else {
                    return captureFromModalCat(type);
                }
            },
            willClose: () => {
                if (streamCat) {
                    streamCat.getTracks().forEach(t => t.stop());
                    streamCat = null;
                }
            }
        });
    }

    async function captureSequenceCat() {
        const instr = document.getElementById('scannerInstructions');
        const video = document.getElementById('modalWebcamVideo');
        const canvas = document.getElementById('modalWebcamCanvas');

        if (!video || !canvas) return false;

        if (typeof FaceMesh !== 'undefined') {
            if (instr) {
                instr.innerText = "Initializing AI Scanner...";
                instr.style.background = "#f0fdf4";
                instr.style.color = "#15803d";
            }

            return new Promise((resolve) => {
                const frames = [];
                let currentStep = 1;
                let lookStraightStartTime = 0;

                const faceMesh = new FaceMesh({
                    locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
                });

                faceMesh.setOptions({
                    maxNumFaces: 1,
                    refineLandmarks: true,
                    minDetectionConfidence: 0.6,
                    minTrackingConfidence: 0.6
                });

                function getEAR(landmarks, eyeIndices) {
                    const p1 = landmarks[eyeIndices[0]];
                    const p2 = landmarks[eyeIndices[1]];
                    const p3 = landmarks[eyeIndices[2]];
                    const p4 = landmarks[eyeIndices[3]];
                    const p5 = landmarks[eyeIndices[4]];
                    const p6 = landmarks[eyeIndices[5]];

                    const v1 = Math.hypot(p2.x - p6.x, p2.y - p6.y);
                    const v2 = Math.hypot(p3.x - p5.x, p3.y - p5.y);
                    const h = Math.hypot(p1.x - p4.x, p1.y - p4.y);

                    return h > 0 ? (v1 + v2) / (2.0 * h) : 0;
                }

                faceMesh.onResults((results) => {
                    if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
                        if (instr) {
                            instr.innerText = "No face detected. Please face the camera.";
                            instr.style.background = "#fee2e2";
                            instr.style.color = "#991b1b";
                        }
                        return;
                    }

                    const landmarks = results.multiFaceLandmarks[0];

                    // Occlusion & Obstruction Detection
                    const criticalPoints = [1, 33, 263, 61, 291];
                    const boundsCheck = criticalPoints.some(idx => !landmarks[idx] || landmarks[idx].x < 0 || landmarks[idx].x > 1 || landmarks[idx].y < 0 || landmarks[idx].y > 1);

                    // Calculate Nose Centering
                    const nose = landmarks[1];
                    const leftEye = landmarks[33];
                    const rightEye = landmarks[263];

                    let yawRatio = 1.0;
                    if (nose && leftEye && rightEye) {
                        const distL = Math.hypot(nose.x - leftEye.x, nose.y - leftEye.y);
                        const distR = Math.hypot(nose.x - rightEye.x, nose.y - rightEye.y);
                        yawRatio = distR > 0 ? distL / distR : 5;
                    }

                    if (boundsCheck || yawRatio > 2.5 || yawRatio < 0.4) {
                        if (instr) {
                            instr.innerText = "⚠️ Tanggalin yung mga nakaharang sa mukha";
                            instr.style.background = "#fee2e2";
                            instr.style.color = "#991b1b";
                        }
                        return;
                    }

                    const leftEAR = getEAR(landmarks, [33, 160, 158, 133, 153, 144]);
                    const rightEAR = getEAR(landmarks, [362, 385, 387, 263, 373, 380]);
                    const avgEAR = (leftEAR + rightEAR) / 2.0;

                    if (currentStep === 1) {
                        if (instr) {
                            instr.innerText = "👀 Step 1: Look directly at the camera";
                            instr.style.background = "#dbeafe";
                            instr.style.color = "#1e40af";
                        }
                        updateStepDots(1);

                        if (yawRatio >= 0.7 && yawRatio <= 1.4) {
                            if (lookStraightStartTime === 0) lookStraightStartTime = Date.now();
                            if (Date.now() - lookStraightStartTime > 1200) {
                                captureFrame();
                                currentStep = 2;
                                lookStraightStartTime = 0;
                            }
                        } else {
                            lookStraightStartTime = 0;
                        }
                    } else if (currentStep === 2) {
                        if (instr) {
                            instr.innerText = "😉 Step 2: Now BLINK your eyes slowly";
                            instr.style.background = "#fef3c7";
                            instr.style.color = "#92400e";
                        }
                        updateStepDots(2);

                        if (avgEAR < 0.18) {
                            captureFrame();
                            currentStep = 3;
                            updateStepDots(3);
                            captureFrame();

                            if (instr) {
                                instr.innerText = "✅ Liveness Verified!";
                                instr.style.background = "#f0fdf4";
                                instr.style.color = "#15803d";
                            }

                            faceMesh.close();
                            finishSequence();
                        }
                    }
                });

                function updateStepDots(step) {
                    for (let i = 1; i <= 3; i++) {
                        const dot = document.getElementById('stepDot' + i);
                        if (dot) {
                            if (i < step) {
                                dot.style.background = '#10b981';
                                dot.style.width = '10px';
                                dot.style.height = '10px';
                            } else if (i === step) {
                                dot.style.background = '#2563eb';
                                dot.style.width = '14px';
                                dot.style.height = '14px';
                            } else {
                                dot.style.background = '#cbd5e1';
                                dot.style.width = '10px';
                                dot.style.height = '10px';
                            }
                        }
                    }
                }

                function captureFrame() {
                    const context = canvas.getContext('2d');
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    context.drawImage(video, 0, 0, canvas.width, canvas.height);
                    canvas.toBlob((blob) => {
                        frames.push(blob);
                    }, 'image/jpeg', 0.9);
                }

                function finishSequence() {
                    setTimeout(() => {
                        const filename = `selfie_sequence_${Date.now()}.jpg`;
                        const files = frames.map((blob, i) => new File([blob], `frame_${i}_${filename}`, { type: "image/jpeg" }));

                        const nameEl = document.getElementById('selfieNameCat');
                        if (nameEl) nameEl.innerText = "Real-time Scan Completed";

                        window.handleFileUploadCat(files, 'selfie');
                        resolve(true);
                    }, 500);
                }

                const analyzeFrame = async () => {
                    if (video.readyState >= 2 && currentStep <= 2) {
                        try {
                            await faceMesh.send({ image: video });
                        } catch (e) { }
                    }
                    if (currentStep <= 2) {
                        requestAnimationFrame(analyzeFrame);
                    }
                };

                analyzeFrame();
            });
        } else {
            console.warn("[KYC] MediaPipe not loaded. Falling back to countdown mode.");
            const frames = [];
            const steps = [
                { text: "Look directly at the camera", delay: 800 },
                { text: "Now... BLINK your eyes", delay: 1000 },
                { text: "Hold still...", delay: 800 }
            ];

            for (const step of steps) {
                if (instr) {
                    instr.innerText = step.text;
                    instr.classList.add('active');
                }
                await new Promise(r => setTimeout(r, step.delay));

                const blob = await new Promise(resolve => {
                    const context = canvas.getContext('2d');
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    context.drawImage(video, 0, 0, canvas.width, canvas.height);
                    canvas.toBlob(resolve, 'image/jpeg', 0.9);
                });
                frames.push(blob);
            }

            const filename = `selfie_sequence_${Date.now()}.jpg`;
            const files = frames.map((blob, i) => new File([blob], `frame_${i}_${filename}`, { type: "image/jpeg" }));

            const nameEl = document.getElementById('selfieNameCat');
            if (nameEl) nameEl.innerText = "Sequence Captured";

            window.handleFileUploadCat(files, 'selfie');
            return true;
        }
    }


    function captureFromModalCat(type) {
        const video = document.getElementById('modalWebcamVideo');
        const canvas = document.getElementById('modalWebcamCanvas');
        if (!video || !canvas) return;

        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        return new Promise((resolve) => {
            canvas.toBlob((blob) => {
                const filename = `${type}_capture_${Date.now()}.jpg`;
                const file = new File([blob], filename, { type: "image/jpeg" });

                // Show in UI
                const nameId = type === 'permit' ? 'permitNameCat' : (type === 'id' ? 'govIdNameCat' : 'selfieNameCat');
                const nameEl = document.getElementById(nameId);
                if (nameEl) {
                    nameEl.innerText = "Captured from Camera";
                    nameEl.style.display = 'block';
                }

                // Trigger processing
                window.handleFileUploadCat(file, type);
                resolve(true);
            }, 'image/jpeg', 0.95);
        });
    }

    window.handleFileUploadCat = async function (inputOrFile, type) {
        const boxId = type === 'permit' ? 'permitBoxCat' : (type === 'id' ? 'govIdBoxCat' : 'selfieBoxCat');
        const statusId = type === 'permit' ? 'permitStatusCat' : (type === 'id' ? 'govIdStatusCat' : 'selfieStatusCat');
        const errorId = type === 'permit' ? 'permitOcrErrorCat' : (type === 'id' ? 'govIdOcrErrorCat' : 'selfieErrorCat');

        let box = document.getElementById(boxId) || document.getElementById(type === 'id' ? 'govIdBox' : (type === 'selfie' ? 'selfieBox' : 'permitBox'));
        let statusLabel = document.getElementById(statusId) || document.getElementById(type === 'id' ? 'govIdStatus' : (type === 'selfie' ? 'selfieStatus' : 'permitStatus'));
        let errorDiv = document.getElementById(errorId) || document.getElementById(type === 'id' ? 'govIdOcrError' : (type === 'selfie' ? 'selfieError' : 'permitOcrError'));

        let files = [];
        if (Array.isArray(inputOrFile)) {
            files = inputOrFile;
        } else if (inputOrFile instanceof File) {
            files = [inputOrFile];
        } else if (inputOrFile.files && inputOrFile.files[0]) {
            files = Array.from(inputOrFile.files);
        }

        if (files.length === 0) return;

        // Populate the hidden input for form submission
        const inputId = type === 'permit' ? 'permit_cat' : (type === 'id' ? 'gov_id_cat' : 'selfie_cat');
        const altInputId = type === 'permit' ? 'permit' : (type === 'id' ? 'gov_id' : 'selfie');
        const realInput = document.getElementById(inputId) || document.getElementById(altInputId);
        if (realInput && files.length > 0) {
            const dt = new DataTransfer();
            files.forEach(f => dt.items.add(f));
            realInput.files = dt.files;
        }

        // Reset states to "Elite Scanning"
        box.classList.add('scanning');
        box.classList.remove('scanned-success', 'scanned-error');
        if (errorDiv) errorDiv.style.display = 'none';

        statusLabel.innerText = "Analyzing Content...";

        // NEW: Full Screen Blocking Spinner
        if (window.Swal) {
            Swal.fire({
                title: '🔒 Secure AI Verification',
                html: `
                    <div style="margin-top: 1rem;">
                        <div class="spinner-container" style="display: flex; justify-content: center; margin-bottom: 1.5rem;">
                            <div style="width: 50px; height: 50px; border: 4px solid rgba(249, 115, 22, 0.1); border-top-color: #f97316; border-radius: 50%; animation: spin-premium 1s linear infinite;"></div>
                        </div>
                        <p style="font-size: 0.95rem; font-weight: 600; color: #1e293b; margin-bottom: 0.5rem;">Analyzing your ${type === 'permit' ? 'Business Permit' : (type === 'id' ? 'ID Card' : 'Facial Scan')}...</p>
                        <p style="font-size: 0.8rem; color: #64748b;">This process is fully encrypted and secure.</p>
                        <style>
                            @keyframes spin-premium {
                                0% { transform: rotate(0deg); }
                                100% { transform: rotate(360deg); }
                            }
                        </style>
                    </div>
                `,
                allowOutsideClick: false,
                allowEscapeKey: false,
                showConfirmButton: false,
                background: '#ffffff',
                backdrop: 'rgba(15, 23, 42, 0.6)',
                customClass: {
                    popup: 'premium-auth-swal',
                }
            });
        }

        const formData = new FormData();
        files.forEach(f => formData.append('document', f));
        formData.append('doc_type', type);

        if (type === 'selfie' && lastUploadedIdPath) {
            formData.append('reference_doc', lastUploadedIdPath);
        }

        const businessName = document.getElementById('business_name')?.value.trim() || "";
        // Compose full name from separate fields (checking both _cat and regular IDs)
        const fnCat = (document.getElementById('first_name_cat')?.value || document.getElementById('first_name')?.value || '').trim();
        const lnCat = (document.getElementById('last_name_cat')?.value || document.getElementById('last_name')?.value || '').trim();
        const mnCat = (document.getElementById('middle_name_cat')?.value || document.getElementById('middle_name')?.value || '').trim();
        const fullName = `${fnCat} ${mnCat ? mnCat + ' ' : ''}${lnCat}`.trim();
        // Update hidden full_name_cat field
        const hiddenFn = document.getElementById('full_name_cat') || document.getElementById('full_name');
        if (hiddenFn) hiddenFn.value = fullName;

        formData.append('user_name', type === 'permit' ? businessName : fullName);
        if (type === 'permit') formData.append('owner_name', fullName);
        if (type === 'id') {
            formData.append('id_type', document.getElementById('id_type_cat')?.value || document.getElementById('id_type')?.value);
            formData.append('id_number', document.getElementById('id_number_cat')?.value || document.getElementById('id_number')?.value || "");
        }

        try {
            const response = await fetch('/auth/scan-document', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();

            box.classList.remove('scanning');

            // Close the blocking spinner
            if (window.Swal) {
                Swal.close();
            }

            if (result.status === 'matched' || result.status === 'approved') {
                box.classList.add('scanned-success');
                statusLabel.innerText = type === 'selfie' ? "Identity Matched" : "Verification Passed";

                // Show Success Toast
                if (window.Swal) {
                    const Toast = Swal.mixin({
                        toast: true,
                        position: 'top-end',
                        showConfirmButton: false,
                        timer: 3000,
                        timerProgressBar: true
                    });
                    Toast.fire({
                        icon: 'success',
                        title: `${type === 'id' ? 'ID' : (type === 'selfie' ? 'Face Scan' : 'Permit')} verified successfully!`
                    });
                }

                if (type === 'id' && result.doc_path) {
                    lastUploadedIdPath = result.doc_path;
                }
            } else {
                box.classList.add('scanned-error');
                statusLabel.innerText = "Validation Failed";

                let errorMsg = result.failure_reason || "Verification failed.";

                // Enrich with OCR detection data if available 
                if (!result.failure_reason && result.ocr_data) {
                    const detectedName = result.ocr_data.full_name_extracted || result.ocr_data.full_name || result.ocr_data.business_name;
                    if (detectedName && detectedName !== "Not detected") {
                        const targetName = type === 'permit' ? businessName : fullName;
                        const detectedId = result.ocr_data.id_number_extracted || result.ocr_data.id_number || '';
                        errorMsg = `Mismatch: Detected "${detectedName}"${detectedId ? `, ID: "${detectedId}"` : ''} on document. Expected "${targetName}".`;
                    }
                }

                if (errorDiv) {
                    errorDiv.innerText = errorMsg;
                    errorDiv.style.display = 'block';
                }

                // Clear the input file so they must try again
                if (inputOrFile instanceof HTMLInputElement) {
                    inputOrFile.value = '';
                }
            }
        } catch (err) {
            console.error("Scan error:", err);
            box.classList.remove('scanning');
            box.classList.add('scanned-error');
            statusLabel.innerText = "System Timeout";
            // Close the blocking spinner on error
            if (window.Swal) {
                Swal.close();
            }
        }
    };

    window.previewLogoCat = function (input) {
        const preview = document.getElementById('logoPreviewCat');
        const icon = document.getElementById('logoDefaultIcon');
        const text = document.getElementById('uploadTextCat');

        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = function (e) {
                if (preview) {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                }
                if (icon) icon.style.display = 'none';
                if (text) text.innerText = 'Logo Selected: ' + input.files[0].name;
            }
            reader.readAsDataURL(input.files[0]);
        }
    };

    window.composeFullNameCat = function () {
        const fn = (document.getElementById('first_name_cat')?.value || '').trim();
        const ln = (document.getElementById('last_name_cat')?.value || '').trim();
        const mn = (document.getElementById('middle_name_cat')?.value || '').trim();
        const hidden = document.getElementById('full_name_cat');
        if (hidden) {
            hidden.value = `${fn} ${mn ? mn + ' ' : ''}${ln}`.trim();
        }
    };

    window.initCatererGeoDropdowns = function () {
        const provSelect = document.getElementById('province_cat');
        const citySelect = document.getElementById('city_cat');
        const brgySelect = document.getElementById('barangay_cat');

        if (!provSelect || !citySelect) return;

        if (typeof window.LOCATION_DATA === 'undefined') {
            setTimeout(window.initCatererGeoDropdowns, 200);
            return;
        }

        provSelect.addEventListener('change', () => {
            citySelect.innerHTML = '<option value="">-- City --</option>';
            if (brgySelect) brgySelect.innerHTML = '<option value="">-- Barangay --</option>';

            const prov = provSelect.value;
            if (prov && window.LOCATION_DATA[prov]) {
                const cities = Object.keys(window.LOCATION_DATA[prov]).sort();
                cities.forEach(city => {
                    const opt = document.createElement('option');
                    opt.value = opt.textContent = city;
                    citySelect.appendChild(opt);
                });

                if (cities.length > 0 && brgySelect) {
                    const firstCity = cities[0];
                    citySelect.value = firstCity;

                    if (window.LOCATION_DATA[prov][firstCity]) {
                        window.LOCATION_DATA[prov][firstCity].sort().forEach(b => {
                            const opt = document.createElement('option');
                            opt.value = opt.textContent = b;
                            brgySelect.appendChild(opt);
                        });
                    }
                }
            }
        });

        citySelect.addEventListener('change', () => {
            if (brgySelect) brgySelect.innerHTML = '<option value="">-- Barangay --</option>';
            const prov = provSelect.value;
            const city = citySelect.value;

            if (prov && city && window.LOCATION_DATA[prov] && window.LOCATION_DATA[prov][city]) {
                window.LOCATION_DATA[prov][city].sort().forEach(b => {
                    const opt = document.createElement('option');
                    opt.value = opt.textContent = b;
                    brgySelect.appendChild(opt);
                });
            }
        });

        if (provSelect.value) {
            provSelect.dispatchEvent(new Event('change'));
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        window.initCatererGeoDropdowns();

        // Set up real-time error clearing for Step 3
        document.querySelectorAll('input[name="event_type_choice"]').forEach(cb => {
            cb.addEventListener('change', () => {
                const eventErrorDrawer = document.getElementById('eventTypeError');
                const checked = document.querySelectorAll('input[name="event_type_choice"]:checked');
                if (eventErrorDrawer && checked.length > 0) {
                    if (eventErrorDrawer.innerText === "Please select at least one event type") {
                        eventErrorDrawer.style.display = 'none';
                    }
                }
            });
        });

        const eventOtherInput = document.getElementById('event_type_other');
        if (eventOtherInput) {
            eventOtherInput.addEventListener('input', () => {
                const eventErrorDrawer = document.getElementById('eventTypeError');
                if (eventOtherInput.value.trim()) {
                    eventOtherInput.style.borderColor = '';
                    if (eventErrorDrawer && eventErrorDrawer.innerText === "Please specify the other event type") {
                        eventErrorDrawer.style.display = 'none';
                    }
                }
            });
        }

        const menuInputCat = document.getElementById('sample_menu_cat');
        if (menuInputCat) {
            menuInputCat.addEventListener('change', () => {
                if (menuInputCat.files.length > 0) {
                    const menuBox = document.getElementById('menuBoxCat');
                    const menuError = document.getElementById('menuErrorCat');
                    if (menuBox) menuBox.style.borderColor = '';
                    if (menuError && menuError.innerText === "Sample Menu is required") {
                        menuError.style.display = 'none';
                    }
                }
            });
        }
    });
})();
