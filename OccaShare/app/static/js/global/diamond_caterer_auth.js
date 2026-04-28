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

    window.changeStepCat = function(n) {
        const form = document.getElementById('catererForm');
        if (!form) return;
        const steps = form.querySelectorAll('.form-step');
        const pSteps = document.querySelectorAll('.progress-step');
        
        // Progress to next step only if current is valid
        if (n === 1 && !validateCurrentStepCat()) return;

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

    function validateCurrentStepCat() {
        const step = document.getElementById(`step-${currentStepCat}`);
        if (!step) return true;
        
        const inputs = step.querySelectorAll('input[required], select[required]');
        let valid = true;
        
        // Accurate Mapping of Input IDs to validation prefixes/wrappers
        const idMap = {
            'full_name_cat': 'fullNameCat',
            'email_cat': 'emailCat',
            'mobile_number_cat': 'mobileCat',
            'password_cat': 'passwordCat',
            'confirm_password_cat': 'confirmCat',
            'business_name': 'businessName',
            'city_cat': 'cityCat',
            'barangay_cat': 'barangayCat',
            'business_type': 'businessType',
            'years_of_operation': 'years',
            'starting_price': 'price',
            'street_cat': 'streetCat',
            'business_description': 'description'
        };

        inputs.forEach(input => {
            const fieldId = input.id;
            const prefix = idMap[fieldId] || fieldId.replace('_cat', '').replace('_cat', 'Cat');
            
            const wrapper = document.getElementById(fieldId + 'Wrapper') || 
                            document.getElementById(prefix + 'Wrapper') ||
                            input.closest('.input-wrapper');

            // Add real-time listener to clear error
            if (input && !input.dataset.hasRealTimeListener) {
                input.addEventListener('input', () => {
                    if (wrapper) {
                        wrapper.classList.remove('error');
                        // Do not set inline max-height here, allow CSS to handle it via the 'error' class addition/removal.
                        const drawer = wrapper.querySelector('.error-drawer');
                        if (drawer) drawer.style.maxHeight = ''; 
                    }
                });
                input.dataset.hasRealTimeListener = "true";
            }

            if (!input.value.trim() || (input.tagName === 'SELECT' && !input.value)) {
                valid = false;
                if (wrapper) {
                    wrapper.classList.add('error');
                    wrapper.classList.remove('success');
                }
            } else {
                if (wrapper && wrapper.classList.contains('error')) {
                    valid = false;
                } else if (wrapper) {
                    wrapper.classList.add('success');
                    wrapper.classList.remove('error');
                }
            }
        });

        // Step 4 Verification Check
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

    window.updateFileNameCat = function(input, targetId) {
        const display = document.getElementById(targetId);
        if (display && input.files && input.files[0]) {
            display.innerText = input.files[0].name;
            display.style.color = 'var(--auth-primary)';
        }
    };

    let currentScanTypeCat = null;

    window.isMobileDeviceCat = function() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    };

    window.isWebcamSupportedCat = function() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    };

    /**
     * UNIVERSAL SCANNING HANDLER
     * Handles Permit, ID, and Selfie scans across all devices.
     */
    window.startUniversalScanCat = async function(type) {
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

    window.triggerNativeCaptureCat = function(type) {
        const inputId = type === 'permit' ? 'permit_cat' : (type === 'id' ? 'gov_id_cat' : 'selfie_cat');
        const input = document.getElementById(inputId);
        if (input) input.click();
    };

    async function openScannerModalCat(type) {
        const idTypeSelect = document.getElementById('id_type');
        const idType = idTypeSelect ? idTypeSelect.value : '';
        
        if (type === 'id' && !idType) {
            Swal.fire('Requirement', 'Please select an ID Type first!', 'warning');
            return;
        }

        const title = type === 'permit' ? 'Scan Business Permit' : (type === 'id' ? `Scan ${idType}` : 'Identity Verification');
        const icon = type === 'permit' ? 'fa-file-invoice' : (type === 'id' ? 'fa-id-card' : 'fa-user-astronaut');

        if (!window.Swal) return;

        Swal.fire({
            title: title,
            html: `
                <div class="scanner-modal-wrap" style="display: flex; flex-direction: column; align-items: center; padding: 1rem;">
                    <div id="scannerInstructions" class="scanner-instruction-banner" style="background: #f0fdf4; color: #15803d; font-size: 0.85rem; font-weight: 600; padding: 0.5rem 1rem; border-radius: 999px; margin-bottom: 1.25rem; border: 1px solid rgba(21, 128, 61, 0.2);">Preparing Camera...</div>
                    <div class="scanner-preview-container" style="position: relative; width: 100%; max-width: 360px; aspect-ratio: 4/3; border-radius: 1.5rem; overflow: hidden; border: 4px solid var(--auth-slate-200); box-shadow: var(--auth-shadow);">
                        <video id="modalWebcamVideo" autoplay playsinline style="width: 100%; height: 100%; object-fit: cover;"></video>
                        <canvas id="modalWebcamCanvas" style="display:none;"></canvas>
                        <div class="scanner-laser" style="position: absolute; width: 100%; height: 3px; background: #f97316; box-shadow: 0 0 12px #f97316; opacity: 0.8; left: 0; top: 0; animation: scan-laser-move 2s infinite ease-in-out;"></div>
                        <div class="scanner-guide-frame ${type}" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); border: 2px dashed rgba(255, 255, 255, 0.7); pointer-events: none; z-index: 10;
                            ${type === 'selfie' ? 'width: 180px; height: 180px; border-radius: 50%;' : 'width: 80%; height: 60%; border-radius: 0.5rem;'}"></div>
                    </div>
                    <p class="scanner-hint" id="scannerHint" style="font-size: 0.8rem; color: #64748b; font-weight: 500; margin-top: 1.25rem;">Align your ${type === 'selfie' ? 'face' : 'document'} comfortably inside the bounds.</p>
                    
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
            confirmButtonText: '📸 Capture',
            confirmButtonColor: '#f97316',
            cancelButtonText: 'Cancel',
            reverseButtons: true,
            allowOutsideClick: false,
            didOpen: async () => {
                const video = document.getElementById('modalWebcamVideo');
                const instr = document.getElementById('scannerInstructions');
                try {
                    streamCat = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } }
                    });
                    video.srcObject = streamCat;
                    if (instr) instr.innerText = type === 'selfie' ? "Center your face in the frame" : "Align document";
                } catch (err) {
                    Swal.showValidationMessage(`Camera Error: ${err.message}`);
                    setTimeout(() => Swal.close(), 2000);
                }
            },
            preConfirm: async () => {
                if (type === 'selfie') {
                    return await captureSequenceCat();
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
        const frames = [];
        const steps = [
            { text: "Look directly at the camera", delay: 800 },
            { text: "Now... BLINK your eyes", delay: 1000 },
            { text: "Slightly move your head", delay: 800 }
        ];

        for (const step of steps) {
            if (instr) {
                instr.innerText = step.text;
                instr.classList.add('active');
            }
            await new Promise(r => setTimeout(r, step.delay));
            
            const blob = await new Promise(resolve => {
                const video = document.getElementById('modalWebcamVideo');
                const canvas = document.getElementById('modalWebcamCanvas');
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
        
        // Show in UI
        const nameEl = document.getElementById('selfieNameCat');
        if (nameEl) {
            nameEl.innerText = "Sequence Captured";
        }

        // Trigger processing with multi-file support
        window.handleFileUploadCat(files, 'selfie');
        return true;
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

    window.handleFileUploadCat = async function(inputOrFile, type) {
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
        const fullName = document.getElementById('full_name_cat')?.value.trim() || "";
        
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
                if (result.ocr_data) {
                    const detectedName = result.ocr_data.full_name || result.ocr_data.business_name;
                    if (detectedName && detectedName !== "Not detected") {
                        const targetName = type === 'permit' ? businessName : fullName;
                        errorMsg = `Mismatch: Detected "${detectedName}" on document. Expected "${targetName}". Please ensure they match.`;
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

    window.previewLogoCat = function(input) {
        const preview = document.getElementById('logoPreviewCat');
        const icon = document.getElementById('logoDefaultIcon');
        const text = document.getElementById('uploadTextCat');
        
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
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

    window.initCatererGeoDropdowns = function() {
        // Relying on inline location_data.js script logic in template forms
    };
})();
