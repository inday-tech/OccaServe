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

            const switchBtn = document.getElementById('switch-camera-btn');
            if (switchBtn) {
                switchBtn.style.display = availableDevices.length > 1 ? 'inline-block' : 'none';
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

    window.handleUploadClick = function () {
        if (document.getElementById('option-upload').classList.contains('disabled')) {
            if (window.showError) window.showError('Please select an ID type and enter a valid ID number first.', 'Incomplete Data'); else alert('Please select an ID type and enter a valid ID number first.');
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
            if (res.ok) {
                document.getElementById('qc-ocr').style.color = 'var(--kyc-accent)';
                document.getElementById('qc-ocr').querySelector('i').className = 'fas fa-check-circle';
                
                setTimeout(() => {
                    document.getElementById('ocr-loading').style.display = 'none';
                    document.getElementById('scanner-container').style.display = 'block';
                    updateStatusTracker(3);
                }, 800);
            } else {
                const data = await res.json();
                if (window.showError) window.showError('Verification Error: ' + (data.detail || 'Failed to process ID'), 'Error'); else alert('Verification Error: ' + (data.detail || 'Failed to process ID'));
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
            { video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } } },
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

    window.startIdScanner = async function (deviceId = null) {
        if (document.getElementById('option-scan').classList.contains('disabled')) {
            if (window.showError) window.showError('ID type and number are required.', 'Missing Fields'); else alert('ID type and number are required.');
            return;
        }

        const video = document.getElementById('id-webcam');
        const scannerContainer = document.getElementById('id-scanner-container');
        const formContainer = document.getElementById('step-id-form');

        if (idStream) {
            idStream.getTracks().forEach(track => track.stop());
        }

        let constraints;
        if (deviceId) {
            constraints = { video: { deviceId: { exact: deviceId }, width: { ideal: 1920 }, height: { ideal: 1080 } } };
        } else {
            constraints = { 
                video: { 
                    facingMode: currentFacingMode, 
                    width: { ideal: 1920 }, 
                    height: { ideal: 1080 } 
                } 
            };
        }

        try {
            idStream = await navigator.mediaDevices.getUserMedia(constraints);
            video.srcObject = idStream;
            formContainer.style.display = 'none';
            scannerContainer.style.display = 'block';
            
            // Re-enumerate to show switch button if multiple cameras exist
            await getCameraDevices();
        } catch (err) {
            console.error("Camera access failed:", err);
            // Fallback to any camera
            try {
                idStream = await navigator.mediaDevices.getUserMedia({ video: true });
                video.srcObject = idStream;
                formContainer.style.display = 'none';
                scannerContainer.style.display = 'block';
                await getCameraDevices();
            } catch (e) {
                showCameraError();
            }
        }
    };

    window.switchCamera = function () {
        // Toggle facing mode for simpler mobile switching
        currentFacingMode = (currentFacingMode === "environment") ? "user" : "environment";
        console.log("[KYC] Switching to:", currentFacingMode);
        window.startIdScanner();
    };

    function showCameraError() {
        let msg = "Unable to access camera. Please ensure camera permissions are allowed.";
        if (!window.isSecureContext) {
            msg = "Camera access is restricted in non-secure HTTP. Please use HTTPS.";
        }
        if (window.showError) window.showError(msg, 'Error'); else alert(msg);
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

