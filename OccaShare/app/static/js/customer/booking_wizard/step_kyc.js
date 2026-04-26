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

            const switchGroup = document.getElementById('camera-switch-group');
            const liveSwitchGroup = document.getElementById('liveness-camera-switch-group');
            
            // ID Scanner Group
            if (switchGroup) {
                switchGroup.style.display = 'flex'; // Force show for testing
                const frontBtn = document.getElementById('btn-cam-front');
                const backBtn = document.getElementById('btn-cam-back');
                if (frontBtn && backBtn) {
                    if (currentFacingMode === "user") {
                        frontBtn.classList.add('active');
                        backBtn.classList.remove('active');
                    } else {
                        backBtn.classList.add('active');
                        frontBtn.classList.remove('active');
                    }
                }
            }

            // Liveness Scanner Group
            if (liveSwitchGroup) {
                liveSwitchGroup.style.display = (availableDevices.length > 1 || isMobile()) ? 'flex' : 'none';
                const frontBtn = document.getElementById('btn-live-cam-front');
                const backBtn = document.getElementById('btn-live-cam-back');
                if (frontBtn && backBtn) {
                    if (livenessFacingMode === "user") {
                        frontBtn.classList.add('active');
                        backBtn.classList.remove('active');
                    } else {
                        backBtn.classList.add('active');
                        frontBtn.classList.remove('active');
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
        const scanBox = document.getElementById('option-scan');
        const uploadBox = document.getElementById('option-upload');

        let value = idInput.value;
        let isValid = false;

        if (idType && validationPatterns[idType]) {
            const pattern = validationPatterns[idType];

            // Auto-format
            const formatted = pattern.format(value);
            if (formatted !== value) {
                idInput.value = formatted;
                value = formatted;
            }

            isValid = pattern.regex.test(value);
            idInput.placeholder = pattern.placeholder;

            if (value.length > 0) {
                if (isValid) {
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
            validationMsg.innerText = '';
        }

        if (idType && isValid) {
            scanBox.classList.remove('disabled');
            uploadBox.classList.remove('disabled');
            
            // Auto-focus the best method if not already selected
            if (isMobile() && !scanBox.classList.contains('active-option')) {
                 scanBox.style.borderColor = 'var(--kyc-accent)';
                 scanBox.style.backgroundColor = 'var(--kyc-accent-soft)';
            }
        } else {
            scanBox.classList.add('disabled');
            uploadBox.classList.add('disabled');
            scanBox.style.borderColor = '';
            scanBox.style.backgroundColor = '';
        }
    };

    // ─── CALABARZON City Data ───────────────────────────────────────────────────
    const calabarzonCities = {
        'Batangas': [
            'Agoncillo','Alitagtag','Balayan','Balete','Batangas City','Bauan',
            'Calaca','Calatagan','Cuenca','Ibaan','Laurel','Lemery','Lian',
            'Lipa City','Lobo','Mabini','Malvar','Mataas na Kahoy','Nasugbu',
            'Padre Garcia','Rosario','San Jose','San Juan','San Luis','San Nicolas',
            'San Pascual','Santa Teresita','Santo Tomas','Taal','Talisay',
            'Taysan','Tingloy','Tuy'
        ],
        'Cavite': [
            'Alfonso','Amadeo','Bacoor','Carmona','Cavite City','Dasmariñas',
            'General Emilio Aguinaldo','General Mariano Alvarez','General Trias',
            'Imus','Indang','Kawit','Magallanes','Maragondon','Mendez',
            'Naic','Noveleta','Rosario','Silang','Tagaytay City','Tanza',
            'Ternate','Trece Martires City'
        ],
        'Laguna': [
            'Alaminos','Bay','Biñan','Cabuyao','Calamba City','Cavinti',
            'Famy','Kalayaan','Liliw','Los Baños','Luisiana','Lumban',
            'Mabitac','Magdalena','Majayjay','Nagcarlan','Paete','Pagsanjan',
            'Pakil','Pangil','Pila','Rizal','San Pablo City','San Pedro',
            'Santa Cruz','Santa Maria','Santa Rosa City','Siniloan','Victoria'
        ],
        'Quezon': [
            'Agdangan','Alabat','Atimonan','Buenavista','Burdeos','Calauag',
            'Candelaria','Catanauan','Dolores','General Luna','General Nakar',
            'Guinayangan','Gumaca','Infanta','Jomalig','Lopez','Lucban',
            'Lucena City','Macalelon','Mauban','Mulanay','Padre Burgos',
            'Pagbilao','Panukulan','Patnanungan','Perez','Pitogo','Plaridel',
            'Polillo','Quezon','Real','Sampaloc','San Andres','San Antonio',
            'San Francisco','San Narciso','Sariaya','Tagkawayan','Tayabas City',
            'Tiaong','Unisan'
        ],
        'Rizal': [
            'Angono','Antipolo City','Baras','Binangonan','Cainta','Cardona',
            'Jala-Jala','Morong','Pililla','Rodriguez','San Mateo','Tanay',
            'Taytay','Teresa'
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
        const city     = (document.getElementById('address_city')?.value || '').trim();
        const street   = (document.getElementById('address_street')?.value || '').trim();
        const combined = [street, city, province].filter(Boolean).join(', ');
        const hiddenAddr = document.getElementById('address');
        if (hiddenAddr) hiddenAddr.value = combined;
        return combined;
    }

    // ─── Full-form Validation ────────────────────────────────────────────────────
    window.validateKycForm = function () {
        const fields = [
            { id: 'first_name',       errId: 'err-first_name', required: true },
            { id: 'last_name',        errId: 'err-last_name',  required: true },
            { id: 'dob',              errId: 'err-dob',        required: true },
            { id: 'address_province', errId: 'err-province',   required: true },
            { id: 'address_city',     errId: 'err-city',       required: true },
            { id: 'address_street',   errId: 'err-street',     required: true },
            { id: 'id_type',          errId: 'err-id_type',    required: true },
            { id: 'id_number',        errId: 'err-id_number',  required: true },
        ];

        let allValid = true;
        fields.forEach(f => {
            const el  = document.getElementById(f.id);
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

        // Also update the hidden combined address
        assembleAddress();

        const scanBox   = document.getElementById('option-scan');
        const uploadBox = document.getElementById('option-upload');
        // Cards enabled only when ALL required fields are valid AND ID format passes
        const idFormatOk = !document.getElementById('option-scan').classList.contains('disabled') ||
                           (document.getElementById('id_type').value && document.getElementById('id_number').value.trim());
        if (allValid && document.getElementById('id_type').value && document.getElementById('id_number').value.trim()) {
            // Leave enablement to validateIdSelection which handles format check
        } else {
            scanBox.classList.add('disabled');
            uploadBox.classList.add('disabled');
        }

        return allValid;
    };

    window.handleUploadClick = function () {
        assembleAddress();
        const idType   = document.getElementById('id_type').value;
        const idNumber = document.getElementById('id_number').value.trim();
        const firstName = document.getElementById('first_name').value.trim();
        const lastName  = document.getElementById('last_name').value.trim();
        const dob       = document.getElementById('dob').value;
        const province  = document.getElementById('address_province').value;
        const city      = document.getElementById('address_city').value;
        const street    = document.getElementById('address_street').value.trim();

        if (!firstName || !lastName || !dob || !province || !city || !street) {
            validateKycForm(); // Show inline errors
            const msg = '❌ Please complete all required fields before proceeding.';
            if (window.showError) window.showError(msg, 'Incomplete Data'); else alert(msg);
            return;
        }

        if (!idType) {
            if (window.showError) window.showError('❌ Please select an ID type.', 'Incomplete Data'); else alert('❌ Please select an ID type.');
            return;
        }
        if (!idNumber) {
            if (window.showError) window.showError('❌ ID number is required.', 'Incomplete Data'); else alert('❌ ID number is required.');
            return;
        }

        const scanBox = document.getElementById('option-upload');
        if (scanBox.classList.contains('disabled')) {
            if (window.showError) window.showError('❌ Invalid ID number format for selected ID type.', 'Format Error'); else alert('❌ Invalid ID number format for selected ID type.');
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
    };

    window.proceedToCamera = async function () {
        // Assemble combined address into hidden field before submitting
        assembleAddress();
        const idType = document.getElementById('id_type').value;
        const idNumber = document.getElementById('id_number').value.trim();

        // Show Processing State
        document.getElementById('id-preview').style.display = 'none';
        document.getElementById('ocr-loading').style.display = 'block';
        updateStatusTracker(2);

        // Reset Quality Indicators
        const indicators = ['qc-resolution', 'qc-focus', 'qc-ocr'];
        indicators.forEach(id => {
            const el = document.getElementById(id);
            el.style.color = 'var(--kyc-slate-400)';
            el.querySelector('i').className = 'fas fa-circle-notch fa-spin';
        });

        const formData = new FormData();
        formData.append('id_type', idType);
        formData.append('id_number', idNumber);
        formData.append('id_document', idFile);
        formData.append('first_name', document.getElementById('first_name').value.trim());
        formData.append('middle_name', document.getElementById('middle_name').value.trim());
        formData.append('last_name', document.getElementById('last_name').value.trim());
        formData.append('dob', document.getElementById('dob').value);
        formData.append('address', document.getElementById('address').value.trim());

        try {
            // Simulated sequence for better UX
            setTimeout(() => {
                document.getElementById('qc-resolution').style.color = 'var(--kyc-accent)';
                document.getElementById('qc-resolution').querySelector('i').className = 'fas fa-check-circle';
            }, 600);
            
            setTimeout(() => {
                document.getElementById('qc-focus').style.color = 'var(--kyc-accent)';
                document.getElementById('qc-focus').querySelector('i').className = 'fas fa-check-circle';
            }, 1200);

            const res = await fetch(`/api/bookings/${bookingId}/upload-id`, { method: 'POST', body: formData });
            const data = await res.json();

            if (res.ok) {
                document.getElementById('qc-ocr').style.color = 'var(--kyc-accent)';
                document.getElementById('qc-ocr').querySelector('i').className = 'fas fa-check-circle';
                
                setTimeout(() => {
                    document.getElementById('ocr-loading').style.display = 'none';
                    document.getElementById('scanner-container').style.display = 'block';
                    updateStatusTracker(3);
                }, 800);
            } else {
                console.error("[KYC] ID Processing Failed:", data);
                // Extract error message - prioritize 'detail', then 'message', then fallback
                const errorMsg = data.detail || data.message || 'Failed to process ID. Please ensure the image is clear.';
                
                if (window.showError) {
                    window.showError(errorMsg, 'Verification Error');
                } else if (window.showToast) {
                    window.showToast(errorMsg, 'error');
                } else {
                    alert('Verification Error: ' + errorMsg);
                }
                
                document.getElementById('ocr-loading').style.display = 'none';
                document.getElementById('id-preview').style.display = 'block';
                updateStatusTracker(1);
            }
        } catch (err) {
            if (window.showError) window.showError('Connection timeout. Please try again.', 'Timeout'); else alert('Connection timeout. Please try again.');
            document.getElementById('ocr-loading').style.display = 'none';
            document.getElementById('id-preview').style.display = 'block';
            updateStatusTracker(1);
        }
    };

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
                document.getElementById('scan-line').style.display = 'block';
                document.getElementById('camera-placeholder').style.opacity = '0';
                startBtn.style.display = 'none';
                beginBtn.style.display = 'inline-block';
                document.getElementById('scan-feedback').innerText = "Look into the center of the circle and click 'I'm Ready'";
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
            feedbackEl.innerText = prompts[i];

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
        document.getElementById('camera-placeholder').style.opacity = '1';
        document.getElementById('scan-feedback').innerText = "Tap 'Start Camera' to begin";
    };

    window.submitLiveness = async function () {
        document.getElementById('liveness-review').style.display = 'none';
        document.getElementById('step-processing').style.display = 'block';
        updateStatusTracker(4);

        const formData = new FormData();
        selfieFrames.forEach(file => formData.append('selfies', file));

        try {
            const res = await fetch(`/api/bookings/${bookingId}/verify-full`, { method: 'POST', body: formData });
            if (res.ok) {
                // Success: Switch to Waiting Screen
                document.getElementById('step-processing').style.display = 'none';
                document.getElementById('kyc-waiting-approval').style.display = 'block';
                
                // Start Real-time listener
                initKycWebSocket();
                
                // Fallback polling
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
                if (data.status === 'approved' || data.status === 'manual_review_approved') {
                    stopPolling();
                    if (ws) ws.close();
                    handleApproval(data);
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

                if (data.status === 'approved') {
                    stopPolling();
                    handleApproval(data);
                } else if (data.status === 'manual_review') {
                    // Stay in polling/waiting mode, but update UI
                    document.getElementById('status-text').innerText = "Pending Review";
                    document.getElementById('status-text').style.color = "#f59e0b";
                    document.getElementById('status-subtext').innerText = "The caterer needs to perform a quick manual check of your identity documents.";
                    
                    // Initialize WebSocket if not already connected
                    if (!ws) {
                        initWebSocket(data.user_id);
                    }
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
        document.getElementById('status-text').innerText = "Failed";
        document.getElementById('status-text').style.color = "#ef4444";
        document.getElementById('status-subtext').innerText = msg;

        const btn = document.createElement('button');
        btn.className = 'btn btn-primary';
        btn.style.marginTop = '1rem';
        btn.innerText = 'Retry';
        btn.onclick = () => window.location.reload();
        document.getElementById('step-processing').appendChild(btn);
    }

    let idStream = null;
    let currentFacingMode = "environment";
    let livenessFacingMode = "user";

    window.startIdScanner = async function (deviceId = null) {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            showCameraError("Your browser does not support camera access or you are not using a secure connection (HTTPS). Please use the 'Upload File' option instead.");
            return;
        }

        const idType = document.getElementById('id_type').value;
        const idNumber = document.getElementById('id_number').value.trim();
        const firstName = document.getElementById('first_name').value.trim();
        const lastName  = document.getElementById('last_name').value.trim();
        const dob       = document.getElementById('dob').value;
        const province  = document.getElementById('address_province').value;
        const city      = document.getElementById('address_city').value;
        const street    = document.getElementById('address_street').value.trim();

        if (!firstName || !lastName || !dob || !province || !city || !street) {
            validateKycForm();
            const msg = '❌ Please complete all required fields before scanning.';
            if (window.showError) window.showError(msg, 'Missing Fields'); else alert(msg);
            return;
        }

        if (!idType) {
            if (window.showError) window.showError('❌ Please select an ID type.', 'Missing Fields'); else alert('❌ Please select an ID type.');
            return;
        }
        if (!idNumber) {
            if (window.showError) window.showError('❌ ID number is required.', 'Missing Fields'); else alert('❌ ID number is required.');
            return;
        }

        if (document.getElementById('option-scan').classList.contains('disabled')) {
            if (window.showError) window.showError('❌ Invalid ID number format for selected ID type.', 'Format Error'); else alert('❌ Invalid ID number format for selected ID type.');
            return;
        }

        const video = document.getElementById('id-webcam');
        const scannerContainer = document.getElementById('id-scanner-container');
        const formContainer = document.getElementById('step-id-form');

        if (idStream) {
            idStream.getTracks().forEach(track => track.stop());
        }

        let constraints = {
            video: {
                facingMode: currentFacingMode,
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        };

        if (deviceId) {
            constraints.video.deviceId = { exact: deviceId };
        }

        try {
            idStream = await navigator.mediaDevices.getUserMedia(constraints);
            video.srcObject = idStream;
            formContainer.style.display = 'none';
            scannerContainer.style.display = 'block';
            await getCameraDevices();
        } catch (err) {
            console.warn("First camera attempt failed, trying fallback...", err);
            try {
                // Fallback 1: No specific resolution
                idStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: currentFacingMode } });
                video.srcObject = idStream;
                formContainer.style.display = 'none';
                scannerContainer.style.display = 'block';
                await getCameraDevices();
            } catch (err2) {
                console.warn("Second camera attempt failed, trying basic...", err2);
                try {
                    // Fallback 2: Minimalist - just any video
                    idStream = await navigator.mediaDevices.getUserMedia({ video: true });
                    video.srcObject = idStream;
                    formContainer.style.display = 'none';
                    scannerContainer.style.display = 'block';
                    await getCameraDevices();
                } catch (err3) {
                    console.error("All camera attempts failed:", err3);
                    showCameraError();
                }
            }
        }
    };

    window.switchCamera = function (mode = null) {
        if (mode) {
            currentFacingMode = mode;
        } else {
            // Toggle facing mode if no mode specified
            currentFacingMode = (currentFacingMode === "environment") ? "user" : "environment";
        }
        
        console.log("[KYC] ID Camera Switching to:", currentFacingMode);
        window.startIdScanner();
    };

    window.switchLivenessCamera = function (mode = null) {
        if (mode) {
            livenessFacingMode = mode;
        } else {
            livenessFacingMode = (livenessFacingMode === "user") ? "environment" : "user";
        }
        
        console.log("[KYC] Liveness Camera Switching to:", livenessFacingMode);
        window.startRealtimeScanner();
    };

    function showCameraError() {
        let msg = "Unable to access camera. Please ensure camera permissions are allowed. Alternatively, you can use the 'Upload File' option.";
        if (!window.isSecureContext) {
            msg = "Camera access is restricted in non-secure HTTP. Please use HTTPS or use the 'Upload File' option.";
        }
        if (window.showError) window.showError(msg, 'Camera Access Error'); else alert(msg);
    }

    window.stopIdScanner = function () {
        if (idStream) {
            idStream.getTracks().forEach(track => track.stop());
            idStream = null;
        }
        document.getElementById('id-scanner-container').style.display = 'none';
        document.getElementById('step-id-form').style.display = 'block';
    };

    window.captureIdFromCamera = function () {
        const video = document.getElementById('id-webcam');
        if (!video.videoWidth) {
            if (window.showToast) window.showToast("Waiting for camera to warm up...", "info"); else alert("Waiting for camera to warm up...");
            return;
        }
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);

        canvas.toBlob((blob) => {
            idFile = new File([blob], "id_captured.jpg", { type: "image/jpeg" });
            const reader = new FileReader();
            reader.onload = function (e) {
                document.getElementById('id-image').src = e.target.result;
                document.getElementById('id-preview').style.display = 'block';
                document.getElementById('id-scanner-container').style.display = 'none';
            };
            reader.readAsDataURL(idFile);
            stopIdScanner();
        }, 'image/jpeg', 0.95);
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

