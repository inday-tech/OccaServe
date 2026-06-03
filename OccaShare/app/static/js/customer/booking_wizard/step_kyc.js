document.addEventListener('DOMContentLoaded', function () {
    let bookingId = window.bookingId;
    let stream = null;
    let idFile = null;
    let selfieFrames = [];
    let pollingInterval = null;
    let ws = null;
    let availableDevices = [];
    let currentDeviceIndex = 0;

    // Mobile Detection
    const isMobile = () => /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

    // Desktop/Mobile Default Method
    function initDefaultMethod() {
        if (isMobile()) {
            console.log("[KYC] Mobile device detected. Auto-selecting 'Scan Live'.");
            // Highlight scan card slightly or purely rely on enabling buttons
        }
    }

    // UI State Management - Updated for Minimalist Stepper
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

    // Secure Context Check
    if (!window.isSecureContext) {
        console.warn("Not in a secure context. Camera access may be restricted.");
    }

    async function getCameraDevices() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            availableDevices = devices.filter(device => device.kind === 'videoinput');
            console.log("Available video devices:", availableDevices);

            // ID Scanner camera switch buttons
            const frontBtn = document.getElementById('btn-cam-front');
            const backBtn  = document.getElementById('btn-cam-back');
            if (frontBtn && backBtn) {
                if (currentFacingMode === "user") {
                    frontBtn.classList.add('active');
                    backBtn.classList.remove('active');
                } else {
                    backBtn.classList.add('active');
                    frontBtn.classList.remove('active');
                }
            }

            // Liveness Scanner Group
            const liveSwitchGroup = document.getElementById('liveness-camera-switch-group');
            if (liveSwitchGroup) {
                liveSwitchGroup.style.display = (availableDevices.length > 1 || isMobile()) ? 'flex' : 'none';
                const frontBtnL = document.getElementById('btn-live-cam-front');
                const backBtnL  = document.getElementById('btn-live-cam-back');
                if (frontBtnL && backBtnL) {
                    if (livenessFacingMode === "user") {
                        frontBtnL.classList.add('active');
                        backBtnL.classList.remove('active');
                    } else {
                        backBtnL.classList.add('active');
                        frontBtnL.classList.remove('active');
                    }
                }
            }
        } catch (err) {
            console.error("Error enumerating devices:", err);
        }
    }

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
        const cameraBox = document.getElementById('option-camera');
        const uploadBox = document.getElementById('option-upload');

        let value = idInput.value;
        let isIdNumberValid = false;

        if (idType && validationPatterns[idType]) {
            const pattern = validationPatterns[idType];

            // Auto-format
            const formatted = pattern.format(value);
            if (formatted !== value) {
                idInput.value = formatted;
                value = formatted;
            }

            isIdNumberValid = pattern.regex.test(value);
            idInput.placeholder = pattern.placeholder;

            if (value.length > 0) {
                if (isIdNumberValid) {
                    idInput.style.borderColor = 'var(--kyc-accent)';
                    validationMsg.innerText = 'Format valid';
                    validationMsg.style.color = 'var(--kyc-accent)';
                } else {
                    idInput.style.borderColor = '#ef4444';
                    validationMsg.innerText = 'Invalid ' + idType + ' format';
                    validationMsg.style.color = '#ef4444';
                }
            } else {
                idInput.style.borderColor = 'var(--kyc-slate-200)';
                validationMsg.innerText = '';
            }
        } else {
            idInput.placeholder = 'Enter ID number';
            idInput.style.borderColor = 'var(--kyc-slate-200)';
            validationMsg.innerText = '';
        }

        // Only require ID Type to be selected to enable upload/scan (OCR will extract the number)
        if (idType) {
            cameraBox.classList.remove('disabled');
            uploadBox.classList.remove('disabled');

            // Auto-focus the best method if not already selected
            if (isMobile() && !cameraBox.classList.contains('active-option')) {
                cameraBox.style.borderColor = 'var(--kyc-accent)';
                cameraBox.style.backgroundColor = 'var(--kyc-accent-soft)';
            }
        } else {
            cameraBox.classList.add('disabled');
            uploadBox.classList.add('disabled');
            cameraBox.style.borderColor = '';
            cameraBox.style.backgroundColor = '';
        }
    };

    // ─── CALABARZON City Data ───────────────────────────────────────────────────
    const calabarzonCities = {
        'Batangas': [
            'Agoncillo', 'Alitagtag', 'Balayan', 'Balete', 'Batangas City', 'Bauan',
            'Calaca', 'Calatagan', 'Cuenca', 'Ibaan', 'Laurel', 'Lemery', 'Lian',
            'Lipa City', 'Lobo', 'Mabini', 'Malvar', 'Mataas na Kahoy', 'Nasugbu',
            'Padre Garcia', 'Rosario', 'San Jose', 'San Juan', 'San Luis', 'San Nicolas',
            'San Pascual', 'Santa Teresita', 'Santo Tomas', 'Taal', 'Talisay',
            'Taysan', 'Tingloy', 'Tuy'
        ],
        'Cavite': [
            'Alfonso', 'Amadeo', 'Bacoor', 'Carmona', 'Cavite City', 'Dasmariñas',
            'General Emilio Aguinaldo', 'General Mariano Alvarez', 'General Trias',
            'Imus', 'Indang', 'Kawit', 'Magallanes', 'Maragondon', 'Mendez',
            'Naic', 'Noveleta', 'Rosario', 'Silang', 'Tagaytay City', 'Tanza',
            'Ternate', 'Trece Martires City'
        ],
        'Laguna': [
            'Alaminos', 'Bay', 'Biñan', 'Cabuyao', 'Calamba City', 'Cavinti',
            'Famy', 'Kalayaan', 'Liliw', 'Los Baños', 'Luisiana', 'Lumban',
            'Mabitac', 'Magdalena', 'Majayjay', 'Nagcarlan', 'Paete', 'Pagsanjan',
            'Pakil', 'Pangil', 'Pila', 'Rizal', 'San Pablo City', 'San Pedro',
            'Santa Cruz', 'Santa Maria', 'Santa Rosa City', 'Siniloan', 'Victoria'
        ],
        'Quezon': [
            'Agdangan', 'Alabat', 'Atimonan', 'Buenavista', 'Burdeos', 'Calauag',
            'Candelaria', 'Catanauan', 'Dolores', 'General Luna', 'General Nakar',
            'Guinayangan', 'Gumaca', 'Infanta', 'Jomalig', 'Lopez', 'Lucban',
            'Lucena City', 'Macalelon', 'Mauban', 'Mulanay', 'Padre Burgos',
            'Pagbilao', 'Panukulan', 'Patnanungan', 'Perez', 'Pitogo', 'Plaridel',
            'Polillo', 'Quezon', 'Real', 'Sampaloc', 'San Andres', 'San Antonio',
            'San Francisco', 'San Narciso', 'Sariaya', 'Tagkawayan', 'Tayabas City',
            'Tiaong', 'Unisan'
        ],
        'Rizal': [
            'Angono', 'Antipolo City', 'Baras', 'Binangonan', 'Cainta', 'Cardona',
            'Jala-Jala', 'Morong', 'Pililla', 'Rodriguez', 'San Mateo', 'Tanay',
            'Taytay', 'Teresa'
        ]
    };

    window.populateCities = function () {
        const province = document.getElementById('address_province').value;
        const citySelect = document.getElementById('address_city');
        citySelect.innerHTML = '<option value="">-- City / Municipality --</option>';
        if (province && calabarzonCities[province]) {
            calabarzonCities[province].forEach(city => {
                const opt = document.createElement('option');
                opt.value = city;
                opt.textContent = city;
                citySelect.appendChild(opt);
            });
            citySelect.disabled = false;
        } else {
            citySelect.disabled = true;
        }
    };

    // Helper: assemble and set the hidden #address field
    function assembleAddress() {
        const province = (document.getElementById('address_province')?.value || '').trim();
        const city = (document.getElementById('address_city')?.value || '').trim();
        const street = (document.getElementById('address_street')?.value || '').trim();
        const combined = [street, city, province].filter(Boolean).join(', ');
        const hiddenAddr = document.getElementById('address');
        if (hiddenAddr) hiddenAddr.value = combined;
        return combined;
    }

    // ─── Full-form Validation ────────────────────────────────────────────────────
    window.validateKycForm = function () {
        const fields = [
            { id: 'id_type',   errId: 'err-id_type',    required: true },
            { id: 'id_number', errId: 'err-id_number',  required: true },
        ];

        let allValid = true;
        fields.forEach(f => {
            const el = document.getElementById(f.id);
            const err = document.getElementById(f.errId);
            if (!el) return;
            const isEmpty = !el.value.trim();
            if (f.required && isEmpty) {
                el.classList.add('input-error');
                if (err) err.classList.add('visible');
                allValid = false;
            } else {
                el.classList.remove('input-error');
                if (err) err.classList.remove('visible');
            }
        });

        // Update hidden address
        assembleAddress();

        // Manage card enablement
        const cameraBox = document.getElementById('option-camera');
        const uploadBox = document.getElementById('option-upload');
        const idType = document.getElementById('id_type').value;
        const idNumber = document.getElementById('id_number').value.trim();

        if (allValid && idType && idNumber) {
            cameraBox.classList.remove('disabled');
            uploadBox.classList.remove('disabled');
        } else {
            cameraBox.classList.add('disabled');
            uploadBox.classList.add('disabled');
        }

        return allValid;
    };

    window.handleCameraClick = function () {
        const idType = document.getElementById('id_type').value;
        if (!idType) {
            if (window.showError) window.showError('❌ Please select an ID type.', 'Incomplete Data'); else alert('❌ Please select an ID type.');
            return;
        }
        document.getElementById('id_camera').click();
    };

    window.handleUploadClick = function () {
        const idType = document.getElementById('id_type').value;
        if (!idType) {
            if (window.showError) window.showError('❌ Please select an ID type.', 'Incomplete Data'); else alert('❌ Please select an ID type.');
            return;
        }
        document.getElementById('id_document').click();
    };

    window.handleIdUpload = function (input) {
        if (input.files && input.files[0]) {
            idFile = input.files[0];
            const reader = new FileReader();
            reader.onload = function (e) {
                document.getElementById('id-image').src = e.target.result;
                document.getElementById('step-id-form').style.display = 'none';
                document.getElementById('id-preview').style.display = 'block';
            };
            reader.readAsDataURL(idFile);
        }
    };

    window.resetIdUpload = function () {
        idFile = null;
        document.getElementById('id-preview').style.display = 'none';
        document.getElementById('step-id-form').style.display = 'block';
        document.getElementById('id_document').value = '';
        document.getElementById('id_camera').value = '';
    };

    window.proceedToCamera = async function () {
        // frictionless optimization: Skip redundant extract-id call as data is already provided or will be extracted during upload
        finalizeIdAndProceed();
    };

    window.finalizeIdAndProceed = async function () {
        const idType = document.getElementById('id_type').value;
        if (!idType) {
            if (window.showError) window.showError('Please select an ID type first.', 'Validation Error');
            return;
        }

        document.getElementById('step-id-form').style.display = 'none';
        document.getElementById('id-preview').style.display = 'none';
        document.getElementById('ocr-loading').style.display = 'block';
        document.getElementById('extraction-title').innerText = "Scanning Your ID";
        updateStatusTracker(2);
        
        // Simulated quality indicator progress
        const statusEl = document.getElementById('extraction-status');
        const indicators = ['qc-resolution', 'qc-focus', 'qc-ocr'];
        let indicatorIdx = 0;
        
        const progressTimer = setInterval(() => {
            if (indicatorIdx < indicators.length) {
                const el = document.getElementById(indicators[indicatorIdx]);
                if (el) {
                    el.style.color = 'var(--kyc-accent)';
                    el.querySelector('i').style.color = 'var(--kyc-accent)';
                }
                indicatorIdx++;
                if (indicatorIdx === 1) statusEl.innerText = "Analyzing document quality...";
                if (indicatorIdx === 2) statusEl.innerText = "Running AI-powered OCR extraction...";
                if (indicatorIdx === 3) statusEl.innerText = "Finalizing data extraction...";
            }
        }, 800);

        // --- CLIENT SIDE COMPRESSION ---
        let finalFile = idFile;
        try {
            const compressedBlob = await compressImage(idFile, 1280, 0.8);
            finalFile = new File([compressedBlob], idFile.name, { type: 'image/jpeg' });
            console.log(`[KYC] Compression: ${(idFile.size / 1024).toFixed(1)}KB -> ${(finalFile.size / 1024).toFixed(1)}KB`);
        } catch (e) {
            console.warn("[KYC] Compression failed, using original", e);
        }

        // Step 1: Call extract-id to get OCR data (NO validation yet)
        const extractForm = new FormData();
        extractForm.append('id_type', idType);
        extractForm.append('id_document', finalFile);

        try {
            const res = await fetch('/api/bookings/extract-id', { method: 'POST', body: extractForm });
            clearInterval(progressTimer);

            if (res.ok) {
                const result = await res.json();
                console.log('[KYC] OCR extraction result:', result);

                // Store the extracted data and temp URL for later upload
                window._ocrExtractedData = result.extracted_data || {};
                window._ocrTempIdUrl = result.temp_id_url || '';
                window._ocrCompressedFile = finalFile;

                // Populate the modal fields
                showOcrModal(result.extracted_data);
            } else {
                const data = await res.json().catch(() => ({}));
                if (window.showError) window.showError(data.detail || "OCR extraction failed. Please try again.", "Extraction Error");
                resetToIdForm();
            }
        } catch (err) {
            clearInterval(progressTimer);
            console.error('[KYC] Extract-id network error:', err);
            if (window.showError) window.showError("Connection lost during extraction.", "Network Error");
            resetToIdForm();
        }
    };

    function resetToIdForm() {
        document.getElementById('ocr-loading').style.display = 'none';
        document.getElementById('step-id-form').style.display = 'block';
    }

    // ─── OCR VERIFICATION MODAL ────────────────────────────────────────
    const ID_TYPE_CONFIG = {
        "PhilSys / PhilID": [
            { key: "id_number", label: "id number", icon: "fa-hashtag" },
            { key: "last_name", label: "Apelyido/Last Name", icon: "fa-user" },
            { key: "given_names", label: "Mga Pangalan/ Given Names", icon: "fa-user" },
            { key: "middle_name", label: "Gitnang Apelyido/ Middle Name", icon: "fa-user" },
            { key: "date_of_birth", label: "Petsa ng Kapanganakan/ Date of Birth", icon: "fa-calendar" },
            { key: "address", label: "Tirahan/ Address", icon: "fa-map-marker-alt" }
        ],
        "Driver's License": [
            { key: "last_name", label: "Last Name", icon: "fa-user" },
            { key: "first_name", label: "First Name", icon: "fa-user" },
            { key: "middle_name", label: "Middle Name", icon: "fa-user" },
            { key: "nationality", label: "Nationality", icon: "fa-flag" },
            { key: "sex", label: "Sex", icon: "fa-venus-mars" },
            { key: "date_of_birth", label: "Date of Birth", icon: "fa-calendar" },
            { key: "weight", label: "Weight(kg)", icon: "fa-weight" },
            { key: "height", label: "Height(m)", icon: "fa-arrows-alt-v" },
            { key: "address", label: "Address", icon: "fa-map-marker-alt" },
            { key: "license_number", label: "License No.", icon: "fa-hashtag" },
            { key: "expiration_date", label: "Expiration date", icon: "fa-calendar-times" },
            { key: "agency_code", label: "Agency Code", icon: "fa-building" },
            { key: "blood_type", label: "Blood type", icon: "fa-tint" },
            { key: "eyes_color", label: "Eyes Color", icon: "fa-eye" },
            { key: "restrictions", label: "Restrictions", icon: "fa-exclamation-triangle" },
            { key: "conditions", label: "Conditions", icon: "fa-notes-medical" }
        ],
        "Passport": [
            { key: "type", label: "Uri/ Type", icon: "fa-passport" },
            { key: "country_code", label: "Kodigo ng Bansa/ Country Code", icon: "fa-globe" },
            { key: "passport_number", label: "Pasaporte blg/ Passport No", icon: "fa-hashtag" },
            { key: "last_name", label: "Apelyido/Last Name", icon: "fa-user" },
            { key: "given_names", label: "Mga Pangalan/ Given Names", icon: "fa-user" },
            { key: "middle_name", label: "Gitnang Apelyido/ Middle Name", icon: "fa-user" },
            { key: "date_of_birth", label: "Araw ng Kapanganakan/ Date of Birth", icon: "fa-calendar" },
            { key: "nationality", label: "Nasyonalidad/ Nationality", icon: "fa-flag" },
            { key: "sex", label: "Kasarian/ Sex", icon: "fa-venus-mars" },
            { key: "place_of_birth", label: "Pook ng Kapanganakan/ Place of Birth", icon: "fa-map-marker-alt" },
            { key: "date_of_issue", label: "Araw ng Pagkakaloob/ Date of Issue", icon: "fa-calendar-check" },
            { key: "visa_until", label: "Petsa ng pagkawala ng visa/ Visa Until", icon: "fa-calendar-times" },
            { key: "issuing_authority", label: "may kapangyarihang nagkaloob/ issuing authority", icon: "fa-building" }
        ]
    };

    // Normalize various ID type labels (server/frontend may use slightly different strings)
    function normalizeIdType(rawType, data) {
        let t = rawType || (data && (data.document_type_detected || data.id_type)) || '';
        t = String(t).trim().toLowerCase();
        if (!t) return 'PhilSys / PhilID';

        if (t.includes('phil') || t.includes('philsys') || t.includes('philid') || t.includes('national id')) return 'PhilSys / PhilID';
        if (t.includes('driver') || t.includes("driver's")) return "Driver's License";
        if (t.includes('passport')) return 'Passport';
        if (t.includes('umid')) return 'UMID';
        // Fallback: return original casing if it matches a config key, else default to PhilSys
        for (const key in ID_TYPE_CONFIG) {
            if (key.toLowerCase() === t) return key;
        }
        return 'PhilSys / PhilID';
    }

    function showOcrModal(data) {
        document.getElementById('ocr-loading').style.display = 'none';

        // Populate fields from extracted data
        const fields = data.fields || data || {};
        
        // Detect and normalize ID Type so it matches `ID_TYPE_CONFIG` keys
        const rawIdType = (document.getElementById('id_type') && document.getElementById('id_type').value) || data.document_type_detected || data.id_type || '';
        const idType = normalizeIdType(rawIdType, data);
        const configFields = ID_TYPE_CONFIG[idType] || ID_TYPE_CONFIG["PhilSys / PhilID"];

        // Set confidence bar
        const confidence = Math.round((data.confidence_score || fields.confidence_score || 0) * 100);
        document.getElementById('ocr-confidence-fill').style.width = confidence + '%';
        document.getElementById('ocr-confidence-pct').innerText = confidence + '%';

        // Render dynamic fields
        const container = document.getElementById('ocr-dynamic-fields-container');
        container.innerHTML = ''; // Clear existing
        
        // Add responsive grid class
        container.className = 'ocr-fields-grid';
        
        configFields.forEach(field => {
            const rawVal = fields[field.key] || data[field.key];
            const val = rawVal && String(rawVal).trim() ? String(rawVal).trim() : '';
            
            // Map common fallbacks if exact key isn't found
            let finalVal = val;
            if (!finalVal) {
                if (field.key === 'id_number' || field.key === 'license_number' || field.key === 'passport_number') {
                    finalVal = fields.id_number || fields.pcn_number || fields.license_number || fields.passport_number || '';
                } else if (field.key === 'date_of_birth') {
                    finalVal = fields.date_of_birth || data.birth_date || fields.extracted_dob || '';
                } else if (field.key === 'given_names' || field.key === 'first_name') {
                    finalVal = fields.given_names || fields.first_name || data.first_name || '';
                } else if (field.key === 'last_name') {
                    finalVal = fields.last_name || data.last_name || '';
                } else if (field.key === 'middle_name') {
                    finalVal = fields.middle_name || data.middle_name || '';
                }
            }

            if (finalVal === 'NOT DETECTED') finalVal = '';

            const html = `
                <div class="ocr-field-row" style="border: none; padding: 0.5rem; background: #f8fafc; border-radius: 1rem; display: flex; align-items: center; gap: 1rem;">
                    <div class="ocr-field-icon"><i class="fas ${field.icon}"></i></div>
                    <div class="ocr-field-content">
                        <label>${field.label}</label>
                        <input type="text" id="ocr-dynamic-${field.key}" value="${finalVal}" placeholder="Enter ${field.label}" class="${finalVal ? '' : 'not-detected'}" oninput="this.classList.remove('not-detected')">
                    </div>
                </div>
            `;
            container.innerHTML += html;
        });

        // Also pre-fill the hidden id_number field if OCR found one
        const ocrIdNum = data.id_number || fields.id_number || fields.pcn_number || fields.license_number || fields.passport_number || '';
        if (ocrIdNum && !document.getElementById('id_number').value.trim()) {
            document.getElementById('id_number').value = ocrIdNum;
        }

        // Show modal with animation
        const modal = document.getElementById('ocr-verification-modal');
        modal.style.display = 'flex';
        requestAnimationFrame(() => {
            modal.classList.add('visible');
        });
    }

    window.cancelOcrModal = function () {
        const modal = document.getElementById('ocr-verification-modal');
        modal.classList.remove('visible');
        setTimeout(() => {
            modal.style.display = 'none';
            resetToIdForm();
            updateStatusTracker(1);
        }, 350);
    };

    window.rescanId = async function () {
        const idInputFile = document.getElementById('id_document')?.files?.[0];
        let fileToRescan = window._ocrCompressedFile || idFile || idInputFile;
        if (!fileToRescan) {
            if (window.showError) window.showError('No uploaded ID file found. Please upload or capture your ID again.', 'Rescan Error');
            window.cancelOcrModal();
            return;
        }

        const idType = document.getElementById('id_type')?.value || '';
        if (!idType) {
            if (window.showError) window.showError('Please select an ID type before rescanning.', 'Missing ID Type');
            window.cancelOcrModal();
            return;
        }

        // 1. Close the modal smoothly
        const modal = document.getElementById('ocr-verification-modal');
        modal.classList.remove('visible');
        setTimeout(() => { modal.style.display = 'none'; }, 350);

        // 2. Show the OCR loading animation
        await new Promise(r => setTimeout(r, 360)); // wait for modal close
        document.getElementById('step-id-form').style.display = 'none';
        document.getElementById('id-preview').style.display = 'none';
        document.getElementById('ocr-loading').style.display = 'block';
        document.getElementById('extraction-title').innerText = 'Re-scanning Your ID';
        updateStatusTracker(2);

        // Reset quality indicators before re-animating
        const indicators = ['qc-resolution', 'qc-focus', 'qc-ocr'];
        indicators.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.style.color = '';
                const icon = el.querySelector('i');
                if (icon) icon.style.color = '';
            }
        });

        // Animate quality indicators
        const statusEl = document.getElementById('extraction-status');
        statusEl.innerText = 'Scanning ID for key information...';
        let indicatorIdx = 0;
        const progressTimer = setInterval(() => {
            if (indicatorIdx < indicators.length) {
                const el = document.getElementById(indicators[indicatorIdx]);
                if (el) {
                    el.style.color = 'var(--kyc-accent)';
                    const icon = el.querySelector('i');
                    if (icon) icon.style.color = 'var(--kyc-accent)';
                }
                indicatorIdx++;
                if (indicatorIdx === 1) statusEl.innerText = 'Analyzing document quality...';
                if (indicatorIdx === 2) statusEl.innerText = 'Running AI-powered OCR extraction...';
                if (indicatorIdx === 3) statusEl.innerText = 'Finalizing data extraction...';
            }
        }, 800);

        async function getFileFromPreviewImage() {
            const img = document.getElementById('id-image');
            if (!img || !img.src) return null;

            const src = img.src;

            // Handle base64 / data: URIs directly (fetch() fails on data: URIs in most browsers)
            if (src.startsWith('data:')) {
                try {
                    const arr = src.split(',');
                    const mimeMatch = arr[0].match(/:(.*?);/);
                    const mime = mimeMatch ? mimeMatch[1] : 'image/jpeg';
                    const bstr = atob(arr[1]);
                    const n = bstr.length;
                    const u8arr = new Uint8Array(n);
                    for (let i = 0; i < n; i++) u8arr[i] = bstr.charCodeAt(i);
                    const blob = new Blob([u8arr], { type: mime });
                    return new File([blob], 'id_preview.jpg', { type: mime });
                } catch (err) {
                    console.warn('[KYC] Failed to decode base64 preview image', err);
                    return null;
                }
            }

            // Handle regular HTTP URLs
            try {
                const res = await fetch(src, { cache: 'no-store' });
                if (res.ok) {
                    const blob = await res.blob();
                    const extension = blob.type.split('/')[1] || 'jpg';
                    return new File([blob], `id_preview.${extension}`, { type: blob.type || 'image/jpeg' });
                }
            } catch (err) {
                console.warn('[KYC] Failed to fetch preview image source', err);
            }

            return null;
        }

        // If the compressed file isn't already stored, compress before rescanning.
        let finalFile = fileToRescan;
        if (!window._ocrCompressedFile && fileToRescan instanceof File) {
            try {
                const compressedBlob = await compressImage(fileToRescan, 1280, 0.8);
                finalFile = new File([compressedBlob], fileToRescan.name, { type: 'image/jpeg' });
                window._ocrCompressedFile = finalFile;
            } catch (err) {
                console.warn('[KYC] Rescan compression failed, sending original file', err);
                finalFile = fileToRescan;
            }
        }

        if (!finalFile) {
            finalFile = await getFileFromPreviewImage();
            if (finalFile) {
                window._ocrCompressedFile = finalFile;
            }
        }

        if (!finalFile) {
            if (window.showError) window.showError('Unable to reconstruct the uploaded ID image. Please upload it again.', 'Rescan Error');
            document.getElementById('ocr-loading').style.display = 'none';
            document.getElementById('id-preview').style.display = 'block';
            return;
        }

        // 3. Call extract-id again with the same file
        const extractForm = new FormData();
        extractForm.append('id_type', idType);
        extractForm.append('id_document', finalFile);

        try {
            const res = await fetch('/api/bookings/extract-id', { method: 'POST', body: extractForm });
            clearInterval(progressTimer);

            if (res.ok) {
                const result = await res.json();
                console.log('[KYC] Rescan OCR result:', result);

                // Update stored data with fresh scan results
                window._ocrExtractedData = result.extracted_data || {};
                window._ocrTempIdUrl = result.temp_id_url || window._ocrTempIdUrl;
                window._ocrCompressedFile = finalFile;

                // Show modal with fresh data
                showOcrModal(result.extracted_data);
            } else {
                const data = await res.json().catch(() => ({}));
                if (window.showError) window.showError(data.detail || 'Rescan failed. Please try again.', 'Rescan Error');
                document.getElementById('ocr-loading').style.display = 'none';
                document.getElementById('id-preview').style.display = 'block';
            }
        } catch (err) {
            clearInterval(progressTimer);
            console.error('[KYC] Rescan network error:', err);
            if (window.showError) window.showError('Connection lost during rescan.', 'Network Error');
            document.getElementById('ocr-loading').style.display = 'none';
            document.getElementById('id-preview').style.display = 'block';
        }
    };

    // ─── SAVE & CONTINUE → COMPLIANCE → UPLOAD → LIVENESS ────────────
    window.saveOcrAndContinue = async function () {
        const modal = document.getElementById('ocr-verification-modal');
        modal.classList.remove('visible');
        setTimeout(() => { modal.style.display = 'none'; }, 350);

        // Get reviewed/edited values from dynamic modal inputs
        const rawIdType = document.getElementById('id_type').value || '';
        const idType = normalizeIdType(rawIdType, window._ocrExtractedData);
        const configFields = ID_TYPE_CONFIG[idType] || ID_TYPE_CONFIG["PhilSys / PhilID"];
        
        let extracted = {};
        configFields.forEach(field => {
            const el = document.getElementById(`ocr-dynamic-${field.key}`);
            if (el) {
                extracted[field.key] = el.value.trim();
            }
        });

        // Update standard hidden form fields with extracted data
        const reviewedFirstName = extracted['given_names'] || extracted['first_name'] || '';
        const reviewedLastName = extracted['last_name'] || '';
        const reviewedMiddleName = extracted['middle_name'] || '';
        const reviewedIdNumber = extracted['id_number'] || extracted['license_number'] || extracted['passport_number'] || document.getElementById('id_number').value.trim();
        const reviewedDob = extracted['date_of_birth'] || '';
        const reviewedAddress = extracted['address'] || '';

        if (reviewedFirstName && document.getElementById('first_name')) document.getElementById('first_name').value = reviewedFirstName;
        if (reviewedLastName && document.getElementById('last_name')) document.getElementById('last_name').value = reviewedLastName;
        if (reviewedMiddleName && document.getElementById('middle_name')) document.getElementById('middle_name').value = reviewedMiddleName;
        if (reviewedIdNumber && document.getElementById('id_number')) document.getElementById('id_number').value = reviewedIdNumber;
        if (reviewedDob && document.getElementById('dob')) document.getElementById('dob').value = reviewedDob;
        if (reviewedAddress && document.getElementById('address')) document.getElementById('address').value = reviewedAddress;

        // Show Compliance Checking animation
        document.getElementById('compliance-checking').style.display = 'block';
        updateStatusTracker(2);

        // Animate compliance checklist items sequentially
        await runComplianceAnimation();

        // After compliance animation, proceed to actual upload
        document.getElementById('compliance-checking').style.display = 'none';
        await performIdUpload();
    };

    async function runComplianceAnimation() {
        const checks = [
            { id: 'comp-check-1', delay: 1200 },
            { id: 'comp-check-2', delay: 1000 },
            { id: 'comp-check-3', delay: 800 },
            { id: 'comp-check-4', delay: 600 }
        ];

        for (const check of checks) {
            await new Promise(r => setTimeout(r, check.delay));
            const item = document.getElementById(check.id);
            if (item) {
                item.classList.add('checked');
                const icon = item.querySelector('.check-icon');
                if (icon) icon.innerHTML = '<i class="fas fa-check"></i>';
            }
        }

        // Brief pause to let user see all green checks
        await new Promise(r => setTimeout(r, 800));
    }

    async function performIdUpload() {
        const formData = new FormData();
        formData.append('id_type', document.getElementById('id_type').value);
        formData.append('id_number', document.getElementById('id_number').value.trim());
        formData.append('id_document', window._ocrCompressedFile || idFile);
        formData.append('first_name', document.getElementById('first_name').value.trim());
        formData.append('middle_name', document.getElementById('middle_name')?.value?.trim() || '');
        formData.append('last_name', document.getElementById('last_name').value.trim());
        formData.append('dob', document.getElementById('dob').value);
        formData.append('address', document.getElementById('address').value.trim());
        formData.append('id_address_extracted', document.getElementById('id_address').value);

        try {
            const res = await fetch(`/api/bookings/${bookingId}/upload-id`, { method: 'POST', body: formData });
            if (res.ok) {
                // Transition to Premium Liveness Detection
                document.getElementById('scanner-container').style.display = 'block';
                document.getElementById('face-compare-row').style.display = 'flex';
                updateStatusTracker(3);

                // Show the uploaded ID as thumbnail in the compare row
                if (idFile) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        const thumb = document.getElementById('id-photo-thumb');
                        if (thumb) {
                            thumb.src = e.target.result;
                            thumb.style.display = 'block';
                            document.getElementById('id-photo-placeholder').style.display = 'none';
                        }
                    };
                    reader.readAsDataURL(idFile);
                }

                // Auto-start the liveness camera
                if (window.startRealtimeScanner) {
                    window.startRealtimeScanner();
                }
            } else {
                const data = await res.json().catch(() => ({}));
                if (window.showError) window.showError(data.detail || "Upload failed", "Upload Error");
                resetToIdForm();
                updateStatusTracker(1);
            }
        } catch (err) {
            if (window.showError) window.showError("Connection lost.", "Network Error");
            resetToIdForm();
            updateStatusTracker(1);
        }
    }

    // Helper: Client-side Image Compression
    async function compressImage(file, maxDim, quality) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = (event) => {
                const img = new Image();
                img.src = event.target.result;
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    let width = img.width;
                    let height = img.height;
                    
                    if (width > height) {
                        if (width > maxDim) {
                            height *= maxDim / width;
                            width = maxDim;
                        }
                    } else {
                        if (height > maxDim) {
                            width *= maxDim / height;
                            height = maxDim;
                        }
                    }
                    
                    canvas.width = width;
                    canvas.height = height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, width, height);
                    canvas.toBlob((blob) => resolve(blob), 'image/jpeg', quality);
                };
                img.onerror = (e) => reject(e);
            };
            reader.onerror = (e) => reject(e);
        });
    }

    window.startRealtimeScanner = async function () {
        const video = document.getElementById('webcam');
        const startBtn = document.getElementById('btn-start-camera');
        const beginBtn = document.getElementById('btn-begin-capture');

        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }

        const configs = [
            { video: { facingMode: livenessFacingMode, width: { ideal: 1280 }, height: { ideal: 720 } } },
            { video: { facingMode: livenessFacingMode } },
            { video: true }
        ];

        let success = false;
        for (const config of configs) {
            try {
                stream = await navigator.mediaDevices.getUserMedia(config);
                success = true;
                break;
            } catch (err) {
                console.warn("Liveness camera failed", err);
            }
        }

        if (success) {
            video.srcObject = stream;
            startBtn.style.display = 'none';
            beginBtn.style.display = 'inline-block';
            const feedbackEl = document.getElementById('scan-feedback');
            if (feedbackEl) feedbackEl.innerText = "Look into the center of the circle and click 'I'm Ready'";
            await getCameraDevices();
        } else {
            if (window.showError) window.showError("Unable to access camera.", "Camera Error"); else alert("Unable to access camera.");
        }
    };

    window.beginLivenessSequence = async function () {
        const countdownEl = document.getElementById('selfie-countdown');
        const feedbackEl = document.getElementById('scan-feedback');
        document.getElementById('btn-begin-capture').style.display = 'none';

        selfieFrames = [];
        const prompts = ["Look into the camera", "Blink slowly", "Stay still..."];

        for (let i = 0; i < 3; i++) {
            const feedbackEl = document.getElementById('scan-feedback');
            if (feedbackEl) feedbackEl.innerText = prompts[i];

            // 3-2-1 Countdown
            countdownEl.style.display = 'block';
            for (let count = 3; count > 0; count--) {
                countdownEl.innerText = count;
                await new Promise(r => setTimeout(r, 800));
            }
            countdownEl.innerText = "📸";
            await new Promise(r => setTimeout(r, 200));
            countdownEl.style.display = 'none';

            captureFrame(i + 1);
            await new Promise(r => setTimeout(r, 500));
        }

        finalizeCapture();
    };

    function captureFrame(index) {
        const video = document.getElementById('webcam');
        const canvas = document.getElementById('frame-canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);

        canvas.toBlob((blob) => {
            const file = new File([blob], `selfie_${index}.jpg`, { type: 'image/jpeg' });
            selfieFrames.push(file);

            // Add to gallery preview
            const gallery = document.getElementById('selfie-gallery');
            const img = document.createElement('img');
            img.src = URL.createObjectURL(blob);
            img.style.width = '80px';
            img.style.height = '80px';
            img.style.objectFit = 'cover';
            img.style.borderRadius = '8px';
            img.style.border = '2px solid var(--kyc-accent)';
            gallery.appendChild(img);
        }, 'image/jpeg', 0.9);
    }

    async function finalizeCapture() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }

        document.getElementById('scanner-container').style.display = 'none';
        document.getElementById('liveness-review').style.display = 'block';
    }

    window.retryLiveness = function () {
        selfieFrames = [];
        document.getElementById('selfie-gallery').innerHTML = '';
        document.getElementById('liveness-review').style.display = 'none';
        document.getElementById('scanner-container').style.display = 'block';
        document.getElementById('btn-start-camera').style.display = 'inline-block';
        document.getElementById('btn-begin-capture').style.display = 'none';
        const feedbackEl = document.getElementById('scan-feedback');
        if (feedbackEl) feedbackEl.innerText = "Tap 'Start Camera' to begin";
    };

    window.submitLiveness = async function () {
        document.getElementById('liveness-review').style.display = 'none';
        document.getElementById('step-processing').style.display = 'block';
        document.getElementById('status-text').innerText = 'Verifying Biometrics...';
        document.getElementById('status-text').style.color = '';
        document.getElementById('status-subtext').innerText = 'Analyzing your face against the ID. This may take a few seconds.';
        updateStatusTracker(4);

        const formData = new FormData();
        selfieFrames.forEach(file => formData.append('selfies', file));

        try {
            const res = await fetch(`/api/bookings/${bookingId}/verify-full`, { method: 'POST', body: formData });
            if (res.ok) {
                // Stay on the processing screen — polling will decide what to show next
                // (liveness failure → retry banner, or passed → waiting for caterer)
                initKycWebSocket();
                startPolling();
            } else {
                const data = await res.json();
                handleRejection(data.detail || "Upload failed");
            }
        } catch (err) {
            handleRejection("Connection lost.");
        }
    };

    function initKycWebSocket() {
        if (ws) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const clientId = `kyc_pkg_${bookingId}_${Date.now()}`;
        ws = new WebSocket(`${protocol}//${window.location.host}/verification/ws/${clientId}`);

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log("[KYC WS] Received update:", data);
            if (data.type === 'kyc_update') {
                if (data.status === 'approved' || data.status === 'verified' || data.status === 'manual_review_approved') {
                    stopPolling();
                    if (ws) ws.close();
                    handleApproval(data);
                } else if (data.status === 'liveliness_failed') {
                    stopPolling();
                    if (ws) ws.close();
                    handleLivenessFailure(data.reason || "Liveness check failed. Please try again.");
                } else if (data.status === 'rejected') {
                    stopPolling();
                    if (ws) ws.close();
                    handleRejection(data.reason || "Verification rejected by caterer");
                }
            }
        };

        ws.onclose = () => {
            console.log("[KYC WS] Connection closed. Falling back to primary polling.");
            ws = null;
        };

        ws.onerror = (err) => {
            console.error("[KYC WS] Error:", err);
            ws = null;
        };
    }


    function startPolling() {
        pollingInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/bookings/${bookingId}/status`);
                const data = await res.json();

                if (data.status === 'approved' || data.status === 'verified') {
                    stopPolling();
                    handleApproval(data);
                } else if (data.status === 'manual_review' || data.status === 'pending_manual_review') {
                    // Liveness passed — now show the waiting screen for caterer review
                    stopPolling();
                    document.getElementById('step-processing').style.display = 'none';
                    document.getElementById('kyc-waiting-approval').style.display = 'block';
                    // Keep WebSocket alive for real-time caterer approval notification
                    if (!ws) {
                        initKycWebSocket();
                    }
                    // Resume polling at a slower rate just to catch approval/rejection
                    pollingInterval = setInterval(async () => {
                        try {
                            const r2 = await fetch(`/api/bookings/${bookingId}/status`);
                            const d2 = await r2.json();
                            if (d2.status === 'approved' || d2.status === 'verified') {
                                stopPolling();
                                handleApproval(d2);
                            } else if (d2.status === 'rejected' || d2.status === 'blocked') {
                                stopPolling();
                                handleRejection(d2.reason || "Verification rejected by caterer");
                            }
                        } catch (e) { console.error("Polling error (phase 2)", e); }
                    }, 5000);
                } else if (data.status === 'liveliness_failed') {
                    // Liveness failed — show error immediately during liveness step
                    stopPolling();
                    handleLivenessFailure(data.reason || "Liveness check failed. Please try again.");
                } else if (data.status === 'rejected' || data.status === 'blocked') {
                    stopPolling();
                    handleRejection(data.reason || "Verification failed");
                }
            } catch (e) {
                console.error("Polling error", e);
            }
        }, 3000);
    }

    function stopPolling() {
        if (pollingInterval) clearInterval(pollingInterval);
    }

    // Deprecated in favor of initKycWebSocket
    function initWebSocket(userId) { }


    function handleApproval(data) {
        document.getElementById('kyc-waiting-approval').style.display = 'none';
        document.getElementById('step-processing').style.display = 'block';

        document.getElementById('status-text').innerText = "Identity Verified!";
        document.getElementById('status-text').style.color = "var(--kyc-accent)";
        document.getElementById('status-subtext').innerText = "Success! Continuing...";


        document.getElementById('node-4').classList.add('completed');
        document.getElementById('node-4').classList.remove('active');

        setTimeout(() => {
            document.getElementById('btn-next').style.display = 'inline-block';
            window.location.href = `/bookings/step/quotation/${bookingId}`;
        }, 2000);
    }

    function handleRejection(msg) {
        document.getElementById('kyc-waiting-approval').style.display = 'none';
        document.getElementById('step-processing').style.display = 'block';
        document.getElementById('status-text').innerText = "Verification Rejected";
        document.getElementById('status-text').style.color = "#ef4444";
        document.getElementById('status-subtext').innerText = msg;

        // Clear any existing buttons inside step-processing to avoid duplicates on fast polling
        const existingBtn = document.getElementById('step-processing').querySelector('.btn-retry-kyc');
        if (existingBtn) existingBtn.remove();

        const btn = document.createElement('button');
        btn.className = 'btn btn-primary btn-retry-kyc';
        btn.style.marginTop = '1rem';
        btn.innerText = 'Retry Verification';
        btn.onclick = () => window.location.reload();
        document.getElementById('step-processing').appendChild(btn);
    }

    function handleLivenessFailure(msg) {
        // Liveness failed: return user to selfie step so they can retry without losing ID data
        document.getElementById('kyc-waiting-approval').style.display = 'none';
        document.getElementById('step-processing').style.display = 'none';

        // Show a friendly error banner inside the liveness review / scanner area
        const livenessRetryBanner = document.getElementById('liveness-retry-banner');
        if (livenessRetryBanner) {
            livenessRetryBanner.style.display = 'block';
            const msgEl = document.getElementById('liveness-retry-message');
            if (msgEl) msgEl.innerText = msg;
        } else {
            // Fallback: show error modal and return to selfie step
            if (window.showError) {
                window.showError(msg, 'Liveness Check Failed');
            } else {
                alert('Liveness check failed: ' + msg);
            }
        }

        // Reset KYC status back to pending_liveliness so the next submit works
        fetch('/api/bookings/kyc/reset-liveness', { method: 'POST' }).catch(() => {});

        // Return user to the selfie capture screen (not a full reload)
        selfieFrames = [];
        const gallery = document.getElementById('selfie-gallery');
        if (gallery) gallery.innerHTML = '';
        document.getElementById('liveness-review').style.display = 'none';
        document.getElementById('scanner-container').style.display = 'block';
        const startBtn = document.getElementById('btn-start-camera');
        const beginBtn = document.getElementById('btn-begin-capture');
        if (startBtn) startBtn.style.display = 'inline-block';
        if (beginBtn) beginBtn.style.display = 'none';
        const feedbackEl = document.getElementById('scan-feedback');
        if (feedbackEl) feedbackEl.innerText = "Tap 'Start Camera' to begin";
        updateStatusTracker(3);
    }

    let livenessFacingMode = "user";

    window.switchLivenessCamera = function (mode = null) {
        if (mode) { livenessFacingMode = mode; }
        else { livenessFacingMode = (livenessFacingMode === "user") ? "environment" : "user"; }
        console.log("[KYC] Liveness Camera Switching to:", livenessFacingMode);
        window.startRealtimeScanner();
    };

    window.validateIdSelection();
    initDefaultMethod();

    // Re-initialize listeners if already in waiting state
    if (document.getElementById('kyc-waiting-approval').style.display === 'block') {
        console.log("[KYC] Page loaded in waiting state. Initializing real-time listeners...");
        initKycWebSocket();
        startPolling();
    }
});

