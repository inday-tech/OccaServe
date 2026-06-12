// MediaPipe imports loaded dynamically when needed (liveness step)
// to avoid blocking the entire module if the CDN is slow/unreachable
let _FaceLandmarker = null;
let _FilesetResolver = null;
async function loadMediaPipe() {
    if (!_FaceLandmarker) {
        try {
            const module = await import("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.8");
            _FaceLandmarker = module.FaceLandmarker;
            _FilesetResolver = module.FilesetResolver;
        } catch (e) {
            console.warn("[KYC] MediaPipe failed to load:", e);
        }
    }
    return { FaceLandmarker: _FaceLandmarker, FilesetResolver: _FilesetResolver };
}

const initKyc = () => {
    let bookingId = window.bookingId;
    let stream = null;
    let idFile = null;
    let selfieFrames = [];
    let pollingInterval = null;
    let ws = null;
    let availableDevices = [];
    let currentDeviceIndex = 0;
    let currentFacingMode = "environment";

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

            // Liveness Scanner Group
            const liveSwitchGroup = document.getElementById('liveness-camera-switch-group');
            if (liveSwitchGroup) {
                liveSwitchGroup.style.display = (availableDevices.length > 1 || isMobile()) ? 'flex' : 'none';
                const frontBtnL = document.getElementById('btn-live-cam-front');
                const backBtnL = document.getElementById('btn-live-cam-back');
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
        const cameraBox = document.getElementById('option-camera');
        const uploadBox = document.getElementById('option-upload');
        const helperText = document.getElementById('kyc-helper-text');

        if (idType) {
            // Enable cards with visual feedback
            cameraBox.classList.remove('disabled');
            uploadBox.classList.remove('disabled');

            // Update helper text
            if (helperText) {
                helperText.innerHTML = '<i class="fas fa-check-circle" style="margin-right: 0.35rem; color: var(--kyc-accent);"></i>Capture or upload a clear photo of your selected ID.';
                helperText.style.color = 'var(--kyc-accent)';
            }

            // Auto-highlight camera on mobile
            if (isMobile() && !cameraBox.classList.contains('active-option')) {
                cameraBox.style.borderColor = 'var(--kyc-accent)';
                cameraBox.style.backgroundColor = 'var(--kyc-accent-soft)';
            }
        } else {
            // Disable cards
            cameraBox.classList.add('disabled');
            uploadBox.classList.add('disabled');
            cameraBox.style.borderColor = '';
            cameraBox.style.backgroundColor = '';

            // Reset helper text
            if (helperText) {
                helperText.innerHTML = '<i class="fas fa-info-circle" style="margin-right: 0.35rem;"></i>Please select an ID type first to continue.';
                helperText.style.color = 'var(--kyc-slate-400)';
            }
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
            { id: 'id_type', errId: 'err-id_type', required: true },
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

        if (allValid && idType) {
            cameraBox.classList.remove('disabled');
            uploadBox.classList.remove('disabled');
        } else {
            cameraBox.classList.add('disabled');
            uploadBox.classList.add('disabled');
        }

        return allValid;
    };

    let idCameraStream = null;

    window.handleCameraClick = function () {
        const idType = document.getElementById('id_type').value;
        if (!idType) {
            if (window.showError) window.showError('❌ Please select an ID type.', 'Incomplete Data'); else alert('❌ Please select an ID type.');
            return;
        }

        if (isMobile()) {
            document.getElementById('id_camera').click();
        } else {
            openIdCameraModal();
        }
    };

    window.openIdCameraModal = async function () {
        const video = document.getElementById('id-webcam');
        const modal = document.getElementById('id-camera-modal');

        try {
            idCameraStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
                audio: false
            });
            video.srcObject = idCameraStream;
            modal.style.display = 'flex';
            requestAnimationFrame(() => {
                modal.classList.add('visible');
            });
        } catch (err) {
            console.error("Failed to open webcam:", err);
            // Fallback to file picker if camera is blocked/unavailable
            if (window.showError) {
                window.showError("Unable to access camera. Opening file explorer as fallback.", "Camera Error");
            }
            document.getElementById('id_camera').click();
        }
    };

    window.closeIdCameraModal = function () {
        const modal = document.getElementById('id-camera-modal');
        modal.classList.remove('visible');
        setTimeout(() => {
            modal.style.display = 'none';
            if (idCameraStream) {
                idCameraStream.getTracks().forEach(track => track.stop());
                idCameraStream = null;
            }
        }, 350);
    };

    window.captureIdFromWebcam = function () {
        const video = document.getElementById('id-webcam');
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Convert to dataUrl and load into the crop workspace
        const dataUrl = canvas.toDataURL('image/jpeg', 0.95);

        fetch(dataUrl)
            .then(res => res.blob())
            .then(blob => {
                idFile = new File([blob], "webcam_capture.jpg", { type: "image/jpeg" });
                window._ocrCompressedFile = null; // Reset crop
                window.closeIdCameraModal();
                window.showIdPreviewScreen(idFile);
            });
    };

    window.handleUploadClick = function () {
        const idType = document.getElementById('id_type').value;
        if (!idType) {
            if (window.showError) window.showError('❌ Please select an ID type.', 'Incomplete Data'); else alert('❌ Please select an ID type.');
            return;
        }
        document.getElementById('id_document').click();
    };

    // Default coordinate pins as percentages
    let pins = {
        tl: { x: 0.1, y: 0.15 },
        tr: { x: 0.9, y: 0.15 },
        br: { x: 0.9, y: 0.85 },
        bl: { x: 0.1, y: 0.85 }
    };

    window.showIdPreviewScreen = function (file) {
        document.getElementById('step-id-form').style.display = 'none';
        document.getElementById('id-preview').style.display = 'block';
        
        // Ensure preview mode is active, crop elements are hidden
        deactivateCropMode();

        const img = document.getElementById('id-image');
        const reader = new FileReader();
        reader.onload = function (e) {
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    };

    window.handleIdUpload = function (input) {
        if (input.files && input.files[0]) {
            idFile = input.files[0];
            window._ocrCompressedFile = null; // Reset crop
            window.showIdPreviewScreen(idFile);
        }
    };

    function initCropWorkspace() {
        updateCropOverlay();

        const pinIds = ['tl', 'tr', 'br', 'bl'];
        pinIds.forEach(id => {
            const pinEl = document.getElementById(`pin-${id}`);
            if (!pinEl) return;

            // Clone element to wipe previous drag listeners cleanly
            const newPinEl = pinEl.cloneNode(true);
            pinEl.parentNode.replaceChild(newPinEl, pinEl);

            setupDrag(newPinEl, id);
        });
    }

    function setupDrag(el, id) {
        const workspace = document.getElementById('crop-workspace-container');

        const onMove = (clientX, clientY) => {
            const rect = workspace.getBoundingClientRect();
            let x = (clientX - rect.left) / rect.width;
            let y = (clientY - rect.top) / rect.height;

            // Constrain pins within crop-workspace-container coordinates
            x = Math.max(0, Math.min(1, x));
            y = Math.max(0, Math.min(1, y));

            pins[id].x = x;
            pins[id].y = y;

            updateCropOverlay();
        };

        const onStart = (e) => {
            e.preventDefault();
            const moveHandler = (moveEvent) => {
                const touch = moveEvent.touches ? moveEvent.touches[0] : moveEvent;
                onMove(touch.clientX, touch.clientY);
            };
            const endHandler = () => {
                document.removeEventListener('mousemove', moveHandler);
                document.removeEventListener('mouseup', endHandler);
                document.removeEventListener('touchmove', moveHandler);
                document.removeEventListener('touchend', endHandler);
            };
            document.addEventListener('mousemove', moveHandler);
            document.addEventListener('mouseup', endHandler);
            document.addEventListener('touchmove', moveHandler, { passive: false });
            document.addEventListener('touchend', endHandler);
        };

        el.addEventListener('mousedown', onStart);
        el.addEventListener('touchstart', onStart, { passive: false });
    }

    function updateCropOverlay() {
        const workspace = document.getElementById('crop-workspace-container');
        if (!workspace) return;
        const rect = workspace.getBoundingClientRect();
        const width = rect.width;
        const height = rect.height;

        const pts = {
            tl: { x: pins.tl.x * width, y: pins.tl.y * height },
            tr: { x: pins.tr.x * width, y: pins.tr.y * height },
            br: { x: pins.br.x * width, y: pins.br.y * height },
            bl: { x: pins.bl.x * width, y: pins.bl.y * height }
        };

        // Reposition corner divs
        for (const id in pts) {
            const el = document.getElementById(`pin-${id}`);
            if (el) {
                el.style.left = `${pts[id].x}px`;
                el.style.top = `${pts[id].y}px`;
            }
        }

        // Redraw SVG polygon lines & mask cutout
        const poly = document.getElementById('crop-svg-polygon');
        const polyMask = document.getElementById('crop-svg-polygon-mask');
        const pointsStr = `${pts.tl.x},${pts.tl.y} ${pts.tr.x},${pts.tr.y} ${pts.br.x},${pts.br.y} ${pts.bl.x},${pts.bl.y}`;

        if (poly) poly.setAttribute('points', pointsStr);
        if (polyMask) polyMask.setAttribute('points', pointsStr);
    }

    window.addEventListener('resize', updateCropOverlay);

    // Solves system of 8 linear equations: A * x = B using Gaussian elimination
    function solveLinearSystem(A, B) {
        let n = 8;
        for (let i = 0; i < n; i++) {
            A[i].push(B[i]);
        }
        for (let i = 0; i < n; i++) {
            let maxRow = i;
            for (let k = i + 1; k < n; k++) {
                if (Math.abs(A[k][i]) > Math.abs(A[maxRow][i])) {
                    maxRow = k;
                }
            }
            let temp = A[i]; A[i] = A[maxRow]; A[maxRow] = temp;
            let diag = A[i][i];
            if (Math.abs(diag) < 1e-8) return null;
            for (let j = i; j <= n; j++) {
                A[i][j] /= diag;
            }
            for (let k = 0; k < n; k++) {
                if (k !== i) {
                    let factor = A[k][i];
                    for (let j = i; j <= n; j++) {
                        A[k][j] -= factor * A[i][j];
                    }
                }
            }
        }
        let X = [];
        for (let i = 0; i < n; i++) {
            X.push(A[i][n]);
        }
        return X;
    }

    function getPerspectiveTransform(src, dst) {
        let A = [];
        let B = [];
        for (let i = 0; i < 4; i++) {
            let u = dst[i].x;
            let v = dst[i].y;
            let x = src[i].x;
            let y = src[i].y;
            A.push([u, v, 1, 0, 0, 0, -u * x, -v * x]);
            B.push(x);
            A.push([0, 0, 0, u, v, 1, -u * y, -v * y]);
            B.push(y);
        }
        return solveLinearSystem(A, B);
    }

    window.cropAndFinalizeId = function () {
        const img = document.getElementById('id-image');
        const srcCanvas = document.getElementById('src-warp-canvas');
        const dstCanvas = document.getElementById('dst-warp-canvas');

        if (!img.src || img.naturalWidth === 0) {
            if (window.showError) window.showError("No image available for cropping.", "Cropping Error");
            return;
        }

        // Draw source natural image
        srcCanvas.width = img.naturalWidth;
        srcCanvas.height = img.naturalHeight;
        const srcCtx = srcCanvas.getContext('2d');
        srcCtx.drawImage(img, 0, 0);

        // Convert percentage pin positions to natural pixels
        const srcPts = [
            { x: pins.tl.x * img.naturalWidth, y: pins.tl.y * img.naturalHeight },
            { x: pins.tr.x * img.naturalWidth, y: pins.tr.y * img.naturalHeight },
            { x: pins.br.x * img.naturalWidth, y: pins.br.y * img.naturalHeight },
            { x: pins.bl.x * img.naturalWidth, y: pins.bl.y * img.naturalHeight }
        ];

        // Standard ID card ratio (approx 1.58:1)
        const dstWidth = 790;
        const dstHeight = 500;
        dstCanvas.width = dstWidth;
        dstCanvas.height = dstHeight;

        const dstPts = [
            { x: 0, y: 0 },
            { x: dstWidth, y: 0 },
            { x: dstWidth, y: dstHeight },
            { x: 0, y: dstHeight }
        ];

        const transform = getPerspectiveTransform(srcPts, dstPts);
        if (!transform) {
            if (window.showError) window.showError("Error computing document geometry.", "Warp Error");
            return;
        }

        const srcData = srcCtx.getImageData(0, 0, srcCanvas.width, srcCanvas.height);
        const dstCtx = dstCanvas.getContext('2d');
        const dstData = dstCtx.createImageData(dstWidth, dstHeight);

        const [a0, a1, a2, a3, a4, a5, a6, a7] = transform;

        for (let yPrime = 0; yPrime < dstHeight; yPrime++) {
            for (let xPrime = 0; xPrime < dstWidth; xPrime++) {
                let denom = a6 * xPrime + a7 * yPrime + 1;
                let x = (a0 * xPrime + a1 * yPrime + a2) / denom;
                let y = (a3 * xPrime + a4 * yPrime + a5) / denom;

                // Bilinear interpolation
                let x0 = Math.floor(x);
                let x1 = Math.min(x0 + 1, srcCanvas.width - 1);
                let y0 = Math.floor(y);
                let y1 = Math.min(y0 + 1, srcCanvas.height - 1);

                if (x0 >= 0 && x0 < srcCanvas.width && y0 >= 0 && y0 < srcCanvas.height) {
                    let dx = x - x0;
                    let dy = y - y0;

                    let idx00 = (y0 * srcCanvas.width + x0) * 4;
                    let idx10 = (y0 * srcCanvas.width + x1) * 4;
                    let idx01 = (y1 * srcCanvas.width + x0) * 4;
                    let idx11 = (y1 * srcCanvas.width + x1) * 4;

                    let dstIdx = (yPrime * dstWidth + xPrime) * 4;

                    for (let c = 0; c < 4; c++) {
                        let val = (1 - dx) * (1 - dy) * srcData.data[idx00 + c] +
                            dx * (1 - dy) * srcData.data[idx10 + c] +
                            (1 - dx) * dy * srcData.data[idx01 + c] +
                            dx * dy * srcData.data[idx11 + c];
                        dstData.data[dstIdx + c] = Math.round(val);
                    }
                }
            }
        }
        dstCtx.putImageData(dstData, 0, 0);

        // Convert dstCanvas to Blob
        dstCanvas.toBlob(async (blob) => {
            window._ocrCompressedFile = new File([blob], "cropped_id.jpg", { type: "image/jpeg" });

            // Set image preview src in OCR modal column
            const cropPreview = document.getElementById('ocr-crop-preview');
            if (cropPreview) {
                cropPreview.src = URL.createObjectURL(blob);
            }

            // Proceed to API verification
            await finalizeIdAndProceed();
        }, 'image/jpeg', 0.85);
    };

    window.resetIdUpload = function () {
        idFile = null;
        window._ocrCompressedFile = null;
        document.getElementById('id-preview').style.display = 'none';
        document.getElementById('step-id-form').style.display = 'block';
        document.getElementById('id_document').value = '';
        document.getElementById('id_camera').value = '';
    };

    window.activateCropMode = function () {
        // Change text
        document.getElementById('id-preview-title').innerText = "Adjust ID Corners";
        document.getElementById('id-preview-desc').innerText = "Drag the corner circles to align with the edges of your ID card for clean cropping and perspective correction.";
        
        // Dim image
        const img = document.getElementById('id-image');
        if (img) img.style.opacity = '0.65';
        
        // Show crop elements
        const cropSvg = document.getElementById('crop-svg');
        if (cropSvg) cropSvg.style.display = 'block';
        document.querySelectorAll('.crop-pin').forEach(pin => pin.style.display = 'flex');
        
        // Switch buttons
        document.getElementById('preview-actions-select').style.display = 'none';
        document.getElementById('preview-actions-crop').style.display = 'flex';
        
        // Initialize workspace coordinates
        pins = {
            tl: { x: 0.1, y: 0.15 },
            tr: { x: 0.9, y: 0.15 },
            br: { x: 0.9, y: 0.85 },
            bl: { x: 0.1, y: 0.85 }
        };
        initCropWorkspace();
    };

    window.deactivateCropMode = function () {
        // Change text
        document.getElementById('id-preview-title').innerText = "Review ID Photo";
        document.getElementById('id-preview-desc').innerText = "Review your uploaded ID card photo. You can scan it directly or crop it if needed.";
        
        // Reset image opacity
        const img = document.getElementById('id-image');
        if (img) img.style.opacity = '0.85';
        
        // Hide crop elements
        const cropSvg = document.getElementById('crop-svg');
        if (cropSvg) cropSvg.style.display = 'none';
        document.querySelectorAll('.crop-pin').forEach(pin => pin.style.display = 'none');
        
        // Switch buttons
        document.getElementById('preview-actions-select').style.display = 'flex';
        document.getElementById('preview-actions-crop').style.display = 'none';
    };

    window.scanDirectlyWithoutCrop = function () {
        window._ocrCompressedFile = null;
        finalizeIdAndProceed();
    };

    window.proceedToCamera = async function () {
        // Obsolete function, replaced by cropAndFinalizeId
        window.cropAndFinalizeId();
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

        // Use warped crop file if present, else compress original raw file
        let finalFile = window._ocrCompressedFile;
        if (!finalFile) {
            finalFile = idFile;
            try {
                const compressedBlob = await compressImage(idFile, 1280, 0.8);
                finalFile = new File([compressedBlob], idFile.name, { type: 'image/jpeg' });
                console.log(`[KYC] Compression: ${(idFile.size / 1024).toFixed(1)}KB -> ${(finalFile.size / 1024).toFixed(1)}KB`);
            } catch (e) {
                console.warn("[KYC] Compression failed, using original", e);
            }
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

                // Match/Mismatch Validation Check
                const selectedRaw = document.getElementById('id_type').value;
                const detectedRaw = result.extracted_data.document_type_detected || result.extracted_data.id_type || '';
                
                const selectedNorm = normalizeIdType(selectedRaw);
                const detectedNorm = normalizeIdType(detectedRaw);
                
                console.log(`[KYC] Comparing Selected='${selectedNorm}' vs Detected='${detectedNorm}'`);
                
                if (selectedNorm !== detectedNorm) {
                    showMismatchModal(selectedRaw, detectedRaw);
                    return;
                }

                // Crucial fields validation check: Ensure there is at least some readable text in name/ID number
                const fields = result.extracted_data.fields || result.extracted_data || {};
                let hasCrucialData = false;
                const crucialKeys = ['id_number', 'license_number', 'passport_number', 'last_name', 'first_name', 'given_names'];
                for (const key of crucialKeys) {
                    const rawVal = fields[key];
                    let val = '';
                    if (rawVal !== null && rawVal !== undefined) {
                        if (typeof rawVal === 'object' && rawVal.value !== undefined) {
                            val = String(rawVal.value);
                        } else {
                            val = String(rawVal);
                        }
                    }
                    val = val.trim().toUpperCase();
                    if (val && val !== 'NOT DETECTED' && val !== 'LOW CONFIDENCE' && !val.includes('XXXX-XXXX') && !val.includes('A00-00')) {
                        hasCrucialData = true;
                        break;
                    }
                }

                if (!hasCrucialData) {
                    console.warn('[KYC] No crucial fields extracted. Treating as Unrecognized/Invalid Document.');
                    showMismatchModal(selectedRaw, 'Other');
                    return;
                }

                if (window._ocrCompressedFile || result.autocrop_succeeded || result.success) {
                    window._ocrCompressedFile = finalFile;

                    const cropPreview = document.getElementById('ocr-crop-preview');
                    if (cropPreview) {
                        cropPreview.src = result.cropped_id_url || URL.createObjectURL(finalFile);
                    }
                    showOcrModal(result.extracted_data);
                } else {
                    // Fall back to manual crop workspace
                    document.getElementById('ocr-loading').style.display = 'none';
                    document.getElementById('step-id-form').style.display = 'none';
                    document.getElementById('id-preview').style.display = 'block';

                    // Change texts, dim image, show pins and crop overlay, switch action buttons
                    document.getElementById('id-preview-title').innerText = "Adjust ID Corners";
                    document.getElementById('id-preview-desc').innerText = "Drag the corner circles to align with the edges of your ID card for clean cropping and perspective correction.";
                    
                    const img = document.getElementById('id-image');
                    if (img) img.style.opacity = '0.65';
                    
                    const cropSvg = document.getElementById('crop-svg');
                    if (cropSvg) cropSvg.style.display = 'block';
                    document.querySelectorAll('.crop-pin').forEach(pin => pin.style.display = 'flex');
                    
                    document.getElementById('preview-actions-select').style.display = 'none';
                    document.getElementById('preview-actions-crop').style.display = 'flex';

                    const reader = new FileReader();
                    reader.onload = function (e) {
                        img.src = e.target.result;

                        // Reset pin defaults on fallback
                        pins = {
                            tl: { x: 0.15, y: 0.15 },
                            tr: { x: 0.85, y: 0.15 },
                            br: { x: 0.85, y: 0.85 },
                            bl: { x: 0.15, y: 0.85 }
                        };

                        if (img.complete) {
                            initCropWorkspace();
                        } else {
                            img.onload = function () {
                                initCropWorkspace();
                            };
                        }
                    };
                    reader.readAsDataURL(idFile);
                }
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
        if (!t) return 'Unknown';

        if (t.includes('phil') || t.includes('philsys') || t.includes('philid') || t.includes('national id')) return 'PhilSys / PhilID';
        if (t.includes('driver') || t.includes("driver's")) return "Driver's License";
        if (t.includes('passport')) return "Passport";
        return 'Unknown';
    }

    function getFriendlyIdTypeName(rawType) {
        const t = String(rawType).trim().toLowerCase();
        if (t.includes('phil') || t.includes('philsys') || t.includes('philid') || t.includes('national id')) return "PhilSys / PhilID";
        if (t.includes('driver') || t.includes("driver's")) return "Philippine Driver's License";
        if (t.includes('passport')) return "Philippine Passport";
        if (t === 'other' || t === 'unknown') return "Unrecognized Document Type";
        return rawType || "Unknown ID Type";
    }

    function showMismatchModal(selectedRaw, detectedRaw) {
        document.getElementById('ocr-loading').style.display = 'none';

        const selectedFriendly = getFriendlyIdTypeName(selectedRaw);
        const detectedFriendly = getFriendlyIdTypeName(detectedRaw);

        let selectedShort = "ID";
        const selectedNorm = normalizeIdType(selectedRaw);
        if (selectedNorm === "PhilSys / PhilID") selectedShort = "PhilSys ID";
        else if (selectedNorm === "Driver's License") selectedShort = "Driver's License";
        else if (selectedNorm === "Passport") selectedShort = "Passport";

        const labelEl = document.getElementById('mismatch-comparison-label');
        if (labelEl) {
            labelEl.innerHTML = `Selected ID Type: <span style="color: #475569;">${selectedFriendly}</span><br>Detected ID Type: <span style="color: #ef4444;">${detectedFriendly}</span>`;
        }

        const article = /^[aeiou]/i.test(detectedFriendly) ? 'an' : 'a';
        const msgBodyEl = document.getElementById('mismatch-msg-body');
        if (msgBodyEl) {
            msgBodyEl.innerHTML = `You selected <strong>${selectedFriendly}</strong>, but the uploaded document appears to be ${article} <strong>${detectedFriendly}</strong>.<br><br>Please upload a valid <strong>${selectedShort}</strong> or change your selected ID type before continuing.`;
        }

        const modal = document.getElementById('id-mismatch-modal');
        if (modal) {
            modal.style.display = 'flex';
            requestAnimationFrame(() => {
                modal.classList.add('visible');
            });
        }
    }

    window.closeMismatchModal = function () {
        const modal = document.getElementById('id-mismatch-modal');
        if (modal) {
            modal.classList.remove('visible');
            setTimeout(() => {
                modal.style.display = 'none';
            }, 350);
        }
    };

    window.handleMismatchRetake = function () {
        window.closeMismatchModal();
        resetToIdForm();
        updateStatusTracker(1);
        // Trigger retake
        window.handleCameraClick();
    };

    window.handleMismatchUpload = function () {
        window.closeMismatchModal();
        resetToIdForm();
        updateStatusTracker(1);
        // Trigger file picker
        window.handleUploadClick();
    };

    window.handleMismatchChangeType = function () {
        window.closeMismatchModal();
        // Reset steps and show form
        resetToIdForm();
        updateStatusTracker(1);
        
        // Focus the dropdown
        const selectEl = document.getElementById('id_type');
        if (selectEl) {
            selectEl.focus();
        }
    };

    function showOcrModal(data) {
        document.getElementById('ocr-loading').style.display = 'none';

        // Toggle success alert display
        const successAlert = document.getElementById('ocr-success-alert');
        if (successAlert) {
            successAlert.style.display = 'flex';
        }

        // Robust Helpers for nested object/dictionary value extraction
        function extractStringValue(obj) {
            if (obj === null || obj === undefined) return '';
            if (typeof obj !== 'object') {
                const str = String(obj).trim();
                return (str === 'NOT DETECTED' || str === 'LOW CONFIDENCE') ? '' : str;
            }
            if (obj.value !== undefined) return extractStringValue(obj.value);
            return '';
        }

        function extractConfidenceValue(obj) {
            if (obj === null || obj === undefined) return 95;
            if (typeof obj !== 'object') {
                const parsed = parseInt(obj);
                return isNaN(parsed) ? 95 : parsed;
            }
            if (obj.confidence !== undefined) return extractConfidenceValue(obj.confidence);
            if (obj.value !== undefined && typeof obj.value === 'object') return extractConfidenceValue(obj.value);
            return 95;
        }

        // Populate fields from extracted data
        const fields = data.fields || data || {};

        // Detect and normalize ID Type so it matches `ID_TYPE_CONFIG` keys
        const rawIdType = (document.getElementById('id_type') && document.getElementById('id_type').value) || data.document_type_detected || data.id_type || '';
        const idType = normalizeIdType(rawIdType, data);
        const configFields = ID_TYPE_CONFIG[idType] || ID_TYPE_CONFIG["PhilSys / PhilID"];

        // Set confidence bar
        let confidenceVal = data.confidence_score !== undefined ? data.confidence_score : (fields.confidence_score !== undefined ? fields.confidence_score : 0.95);
        if (confidenceVal <= 1.0) {
            confidenceVal = Math.round(confidenceVal * 100);
        } else {
            confidenceVal = Math.round(confidenceVal);
        }
        document.getElementById('ocr-confidence-fill').style.width = confidenceVal + '%';
        document.getElementById('ocr-confidence-pct').innerText = confidenceVal + '%';

        // Render dynamic fields
        const container = document.getElementById('ocr-dynamic-fields-container');
        container.innerHTML = ''; // Clear existing

        // Add responsive grid class
        container.className = 'ocr-fields-grid';

        configFields.forEach(field => {
            const rawVal = fields[field.key] || data[field.key];
            let val = extractStringValue(rawVal);
            let conf = extractConfidenceValue(rawVal);

            // Map common fallbacks if exact key isn't found
            if (!val) {
                let fallbackVal = null;
                if (field.key === 'id_number' || field.key === 'license_number' || field.key === 'passport_number') {
                    fallbackVal = fields.id_number || fields.pcn_number || fields.license_number || fields.passport_number || '';
                } else if (field.key === 'date_of_birth') {
                    fallbackVal = fields.date_of_birth || data.birth_date || fields.extracted_dob || '';
                } else if (field.key === 'given_names' || field.key === 'first_name') {
                    fallbackVal = fields.given_names || fields.first_name || data.first_name || '';
                } else if (field.key === 'last_name') {
                    fallbackVal = fields.last_name || data.last_name || '';
                } else if (field.key === 'middle_name') {
                    fallbackVal = fields.middle_name || data.middle_name || '';
                } else if (field.key === 'address') {
                    fallbackVal = fields.address || data.address || '';
                }

                if (fallbackVal) {
                    val = extractStringValue(fallbackVal);
                    conf = extractConfidenceValue(fallbackVal);
                }
            }

            // Build premium confidence badges
            let badgeColor = '#22c55e';
            let badgeBg = '#dcfce7';
            let badgeText = `${conf}%`;
            let badgeIcon = '<i class="fas fa-check-circle"></i>';
            let borderStyle = '';
            let inputClass = '';

            if (conf < 85) {
                badgeColor = '#ef4444';
                badgeBg = '#fee2e2';
                badgeIcon = '<i class="fas fa-exclamation-triangle"></i>';
                borderStyle = 'border: 1.5px solid #fca5a5;';
                inputClass = 'low-confidence';
            } else if (conf < 95) {
                badgeColor = '#eab308';
                badgeBg = '#fef9c3';
                badgeIcon = '<i class="fas fa-exclamation-circle"></i>';
                borderStyle = 'border: 1.5px solid #fef08a;';
                inputClass = 'mid-confidence';
            }

            if (!val) {
                badgeColor = '#94a3b8';
                badgeBg = '#f1f5f9';
                badgeText = 'Missing';
                badgeIcon = '<i class="fas fa-question-circle"></i>';
                inputClass = 'not-detected';
            }

            const html = `
                <div class="ocr-field-row" style="${borderStyle} padding: 0.75rem; background: #f8fafc; border-radius: 1rem; display: flex; flex-direction: column; gap: 0.35rem; position: relative;">
                     <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                         <div style="display: flex; align-items: center; gap: 0.5rem;">
                             <i class="fas ${field.icon}" style="color: var(--kyc-slate-400); font-size: 0.85rem;"></i>
                             <label style="margin: 0 !important; font-size: 0.7rem !important; font-weight: 800 !important; color: #94a3b8 !important; text-transform: uppercase !important; letter-spacing: 0.06em !important;">${field.label}</label>
                         </div>
                         <div style="display: flex; align-items: center; gap: 0.3rem; padding: 0.2rem 0.5rem; border-radius: 2rem; font-size: 0.65rem; font-weight: 800; color: ${badgeColor}; background: ${badgeBg};">
                             ${badgeIcon} <span>${badgeText}</span>
                         </div>
                     </div>
                     <input type="text" id="ocr-dynamic-${field.key}" value="${val}" placeholder="Enter ${field.label}" class="modern-input ${inputClass}" style="height: 2.5rem !important; padding: 0 0.75rem !important; font-size: 0.85rem !important; font-weight: 700 !important; border-radius: 0.65rem !important; border: 1.5px solid #e2e8f0; width: 100%; box-sizing: border-box;" oninput="this.className='modern-input';">
                </div>
            `;
            container.innerHTML += html;
        });

        // Also pre-fill the hidden id_number field if OCR found one
        let ocrIdNum = extractStringValue(data.id_number || fields.id_number || fields.pcn_number || fields.license_number || fields.passport_number);
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

    window.rescanId = function () {
        const modal = document.getElementById('ocr-verification-modal');
        modal.classList.remove('visible');
        setTimeout(() => {
            modal.style.display = 'none';
            resetIdUpload();
            updateStatusTracker(1);
        }, 350);
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
                    canvas.toBlob((blob) => {
                        resolve(blob);
                    }, 'image/jpeg', quality);
                };
                img.onerror = reject;
            };
            reader.onerror = reject;
        });
    }

    // MediaPipe & Active Challenge State Variables
    let faceLandmarker = null;
    let isLivenessRunning = false;
    let lastVideoTime = -1;
    let animationFrameId = null;

    // Canvas helper context for mirrored visual outline guide overlay
    let guideCanvas = document.getElementById('face-guide-canvas');
    let guideCtx = guideCanvas ? guideCanvas.getContext('2d') : null;

    // Liveness states
    const STATE_ALIGNING = 0;
    const STATE_COUNTDOWN = 1;
    const STATE_BLINK = 2;
    const STATE_VERIFYING = 3;
    const STATE_SUCCESS = 4;
    const STATE_FAILED = 5;

    let currentLivenessState = STATE_ALIGNING;
    let alignedStartTime = 0;
    let countdownValue = 3;
    let countdownInterval = null;
    let blinkStep = 0;
    selfieFrames = [];

    async function initializeFaceLandmarker() {
        if (faceLandmarker) return;
        try {
            console.log("[KYC] Initializing MediaPipe Face Landmarker...");
            const { FaceLandmarker, FilesetResolver } = await loadMediaPipe();
            if (!FaceLandmarker || !FilesetResolver) {
                throw new Error("MediaPipe libraries failed to load");
            }
            const vision = await FilesetResolver.forVisionTasks(
                "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.8/wasm"
            );
            faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
                baseOptions: {
                    modelAssetPath: "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
                    delegate: "GPU"
                },
                runningMode: "VIDEO",
                numFaces: 1
            });
            console.log("[KYC] MediaPipe Face Landmarker initialized successfully.");
        } catch (err) {
            console.error("[KYC] Failed to initialize Face Landmarker:", err);
            if (window.showError) {
                window.showError("Failed to initialize biometrics engine. Please ensure you are connected to the internet.", "Biometrics Error");
            }
        }
    }

    function setProgressRing(percent, color = null) {
        const ringFill = document.getElementById('progress-ring-fill');
        if (!ringFill) return;
        const offset = 930 - (percent / 100) * 930;
        ringFill.style.strokeDashoffset = offset;
        if (color) {
            ringFill.style.stroke = color;
        } else {
            ringFill.style.stroke = '';
        }
    }

    function updateInstruction(mainText, subText) {
        const mainEl = document.getElementById('scan-feedback');
        const subEl = document.getElementById('liveness-sub-feedback');
        if (mainEl) mainEl.innerText = mainText;
        if (subEl) subEl.innerText = subText;
    }

    window.startRealtimeScanner = async function () {
        const video = document.getElementById('webcam');
        const startBtn = document.getElementById('btn-start-camera');

        if (stream) {
            try {
                stream.getTracks().forEach(track => track.stop());
            } catch (e) { }
        }

        // Initialize or reset the verification session on the backend
        try {
            console.log("[KYC] Initializing backend liveness session...");
            await fetch(`/api/bookings/${bookingId}/kyc/session/init`, { method: 'POST' });
        } catch (initErr) {
            console.error("[KYC] Failed to initialize liveness session:", initErr);
        }

        currentLivenessState = STATE_ALIGNING;
        alignedStartTime = 0;
        countdownValue = 3;
        if (countdownInterval) clearInterval(countdownInterval);
        countdownInterval = null;
        blinkStep = 0;
        selfieFrames = [];
        setProgressRing(0);

        const circleContainer = document.getElementById('camera-circle-container');
        if (circleContainer) {
            circleContainer.classList.add('pulse-ring');
        }

        const checkmarkOverlay = document.getElementById('success-checkmark-overlay');
        if (checkmarkOverlay) {
            checkmarkOverlay.style.display = 'none';
        }

        updateInstruction("Preparing camera...", "Position your face within the circle");

        const configs = [
            { video: { facingMode: livenessFacingMode, width: { ideal: 640 }, height: { ideal: 480 } } },
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
                console.warn("Liveness camera failed config", err);
            }
        }

        if (success) {
            if (startBtn) startBtn.style.display = 'none';

            guideCanvas = document.getElementById('face-guide-canvas');
            if (guideCanvas) {
                guideCtx = guideCanvas.getContext('2d');
            }

            video.onloadedmetadata = () => {
                console.log("[KYC] Video metadata loaded");
                if (guideCanvas) {
                    guideCanvas.width = video.videoWidth || 640;
                    guideCanvas.height = video.videoHeight || 480;
                }
            };

            video.onplaying = () => {
                console.log("[KYC] Video playing");
                if (guideCanvas && (!guideCanvas.width || guideCanvas.width === 300)) {
                    guideCanvas.width = video.videoWidth || 640;
                    guideCanvas.height = video.videoHeight || 480;
                }
                lastVideoTime = -1;
                if (animationFrameId) cancelAnimationFrame(animationFrameId);
                animationFrameId = requestAnimationFrame(livenessDetectionLoop);
            };

            video.muted = true;
            video.srcObject = stream;

            try {
                await video.play();
            } catch (playErr) {
                console.warn("[KYC] video.play() failed:", playErr);
            }

            isLivenessRunning = true;

            if (video.readyState >= 2 && !video.paused) {
                console.log("[KYC] Video is already playing, manually triggering loop");
                video.onplaying();
            }

            updateInstruction("Align your face in the circle", "Loading biometrics...");
            initializeFaceLandmarker().then(() => {
                console.log("[KYC] Biometrics engine loaded in background");
                if (currentLivenessState === STATE_ALIGNING) {
                    updateInstruction("Align your face in the circle", "Position your face within the circle");
                }
            }).catch(err => {
                console.error("[KYC] Asynchronous biometrics load failed:", err);
            });

            await getCameraDevices();
        } else {
            if (window.showError) window.showError("Unable to access camera.", "Camera Error");
        }
    };

    function getDistance(p1, p2) {
        return Math.sqrt(
            Math.pow(p1.x - p2.x, 2) +
            Math.pow(p1.y - p2.y, 2) +
            Math.pow((p1.z || 0) - (p2.z || 0), 2)
        );
    }

    async function captureFrameToFile(challengeName) {
        const video = document.getElementById('webcam');
        const canvas = document.getElementById('frame-canvas') || document.createElement('canvas');
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        return new Promise((resolve) => {
            canvas.toBlob((blob) => {
                const file = new File([blob], `selfie_${challengeName}.jpg`, { type: 'image/jpeg' });
                resolve(file);
            }, 'image/jpeg', 0.90);
        });
    }

    async function livenessDetectionLoop() {
        const video = document.getElementById('webcam');
        if (!isLivenessRunning || !video || video.paused || video.ended) return;

        if (guideCanvas && guideCtx) {
            guideCtx.clearRect(0, 0, guideCanvas.width, guideCanvas.height);

            const cx = guideCanvas.width / 2;
            const cy = guideCanvas.height / 2;
            const rx = guideCanvas.width * 0.28;
            const ry = guideCanvas.height * 0.38;

            guideCtx.beginPath();
            guideCtx.ellipse(cx, cy, rx, ry, 0, 0, 2 * Math.PI);
            guideCtx.lineWidth = 4;
            guideCtx.setLineDash([8, 6]);
            guideCtx.strokeStyle = window._facePositionedCorrectly ? "#22c55e" : "#f97316";
            guideCtx.stroke();
            guideCtx.setLineDash([]);
        }

        if (faceLandmarker && video.currentTime !== lastVideoTime) {
            lastVideoTime = video.currentTime;

            const result = faceLandmarker.detectForVideo(video, performance.now());

            if (result.faceLandmarks && result.faceLandmarks.length > 0) {
                const landmarks = result.faceLandmarks[0];

                const eye_center_x = (landmarks[33].x + landmarks[263].x) / 2;
                const eye_dist = Math.abs(landmarks[263].x - landmarks[33].x);
                const nose_offset = (landmarks[1].x - eye_center_x) / eye_dist;

                const face_height = Math.abs(landmarks[152].y - landmarks[10].y);
                const nose_rel_y = (landmarks[1].y - landmarks[10].y) / face_height;

                // Relaxed centering and sizing checks for a much better UX
                const nose_x = landmarks[1].x;
                const nose_y = landmarks[1].y;
                const isScreenCentered = Math.abs(nose_x - 0.5) < 0.15 && Math.abs(nose_y - 0.5) < 0.15;
                const isCentered = isScreenCentered && Math.abs(nose_offset) < 0.30 && nose_rel_y > 0.35 && nose_rel_y < 0.68;
                const isProperSize = eye_dist > 0.12 && eye_dist < 0.55;

                // Debug frame logging (every 60 frames)
                if (!window._debugFrameCount) window._debugFrameCount = 0;
                window._debugFrameCount++;
                if (window._debugFrameCount % 60 === 0) {
                    console.log(`[KYC Align Debug] nose_offset: ${nose_offset.toFixed(3)} (target < 0.30), nose_rel_y: ${nose_rel_y.toFixed(3)} (target 0.35 - 0.68), eye_dist: ${eye_dist.toFixed(3)} (target 0.12 - 0.55)`);
                }

                if (currentLivenessState === STATE_ALIGNING) {
                    if (!isCentered || !isProperSize) {
                        window._facePositionedCorrectly = false;
                        alignedStartTime = 0;

                        const circleContainer = document.getElementById('camera-circle-container');
                        if (circleContainer) circleContainer.classList.add('pulse-ring');

                        let subPrompt = "Center your face inside the circle";
                        if (!isProperSize) {
                            subPrompt = eye_dist <= 0.16 ? "Move closer to the camera" : "Move further back";
                        }
                        updateInstruction("Align your face in the circle", subPrompt);
                        setProgressRing(0);
                    } else {
                        window._facePositionedCorrectly = true;

                        const circleContainer = document.getElementById('camera-circle-container');
                        if (circleContainer) circleContainer.classList.add('pulse-ring');

                        updateInstruction("Align your face in the circle", "Keep still...");
                        setProgressRing(0);

                        if (alignedStartTime === 0) {
                            alignedStartTime = Date.now();
                        } else if (Date.now() - alignedStartTime > 1500) {
                            currentLivenessState = STATE_COUNTDOWN;
                            alignedStartTime = 0;
                            countdownValue = 3;

                            const circleContainer = document.getElementById('camera-circle-container');
                            if (circleContainer) circleContainer.classList.remove('pulse-ring');

                            const countdownEl = document.getElementById('selfie-countdown');
                            if (countdownEl) {
                                countdownEl.innerText = countdownValue;
                                countdownEl.classList.add('show');
                            }
                            updateInstruction("Preparing to capture", "Keep steady...");
                            setProgressRing(0);

                            if (countdownInterval) clearInterval(countdownInterval);
                            countdownInterval = setInterval(() => {
                                countdownValue--;
                                if (countdownValue > 0) {
                                    if (countdownEl) countdownEl.innerText = countdownValue;
                                } else {
                                    clearInterval(countdownInterval);
                                    countdownInterval = null;
                                    if (countdownEl) countdownEl.classList.remove('show');

                                    currentLivenessState = STATE_BLINK;
                                    blinkStep = 0;
                                    selfieFrames = [];
                                    updateInstruction("Blink your eyes", "Look straight and blink naturally");
                                    setProgressRing(0);
                                }
                            }, 1000);
                        }
                    }
                } else if (currentLivenessState === STATE_COUNTDOWN) {
                    if (!isCentered || !isProperSize) {
                        if (!window._countdownLostStartTime) {
                            window._countdownLostStartTime = Date.now();
                        } else if (Date.now() - window._countdownLostStartTime > 1000) {
                            clearInterval(countdownInterval);
                            countdownInterval = null;
                            const countdownEl = document.getElementById('selfie-countdown');
                            if (countdownEl) countdownEl.classList.remove('show');
                            currentLivenessState = STATE_ALIGNING;
                            alignedStartTime = 0;
                            window._countdownLostStartTime = 0;
                            window._facePositionedCorrectly = false;
                            updateInstruction("Align your face in the circle", "Alignment lost, please realign");
                            setProgressRing(0);
                        }
                    } else {
                        window._countdownLostStartTime = 0;
                    }
                } else if (currentLivenessState === STATE_BLINK) {
                    if (!isCentered || !isProperSize) {
                        if (!window._blinkLostStartTime) {
                            window._blinkLostStartTime = Date.now();
                        } else if (Date.now() - window._blinkLostStartTime > 2000) {
                            currentLivenessState = STATE_ALIGNING;
                            alignedStartTime = 0;
                            blinkStep = 0;
                            selfieFrames = [];
                            window._blinkLostStartTime = 0;
                            window._facePositionedCorrectly = false;
                            updateInstruction("Align your face in the circle", "Alignment lost, please realign");
                            setProgressRing(0);
                            return;
                        }
                    } else {
                        window._blinkLostStartTime = 0;
                    }

                    const ear_left = getDistance(landmarks[159], landmarks[145]) / getDistance(landmarks[33], landmarks[133]);
                    const ear_right = getDistance(landmarks[386], landmarks[374]) / getDistance(landmarks[362], landmarks[263]);
                    const ear_avg = (ear_left + ear_right) / 2;

                    if (blinkStep === 0) {
                        if (ear_avg > 0.22) {
                            const file = await captureFrameToFile("open_1");
                            selfieFrames.push(file);
                            blinkStep = 1;
                            setProgressRing(33);
                            console.log("[KYC] Step 0 completed. Open 1 captured. EAR:", ear_avg);
                        }
                    } else if (blinkStep === 1) {
                        if (ear_avg < 0.17) {
                            const file = await captureFrameToFile("closed");
                            selfieFrames.push(file);
                            blinkStep = 2;
                            setProgressRing(66);
                            console.log("[KYC] Step 1 completed. Closed captured. EAR:", ear_avg);
                        }
                    } else if (blinkStep === 2) {
                        if (ear_avg > 0.22) {
                            const file = await captureFrameToFile("open_2");
                            selfieFrames.push(file);
                            blinkStep = 3;
                            setProgressRing(100, "#22c55e");
                            console.log("[KYC] Step 2 completed. Open 2 captured. EAR:", ear_avg);

                            isLivenessRunning = false;
                            if (stream) {
                                stream.getTracks().forEach(track => track.stop());
                                stream = null;
                            }
                            if (guideCtx) guideCtx.clearRect(0, 0, guideCanvas.width, guideCanvas.height);

                            currentLivenessState = STATE_VERIFYING;
                            updateInstruction("Verifying your identity...", "Analyzing biometrics");

                            await autoSubmitLiveness();
                        }
                    }
                }
            } else {
                window._facePositionedCorrectly = false;
                if (currentLivenessState === STATE_ALIGNING) {
                    alignedStartTime = 0;
                    updateInstruction("Align your face in the circle", "No face detected");
                    setProgressRing(0);
                } else if (currentLivenessState === STATE_COUNTDOWN) {
                    if (!window._countdownLostStartTime) {
                        window._countdownLostStartTime = Date.now();
                    } else if (Date.now() - window._countdownLostStartTime > 1000) {
                        clearInterval(countdownInterval);
                        countdownInterval = null;
                        const countdownEl = document.getElementById('selfie-countdown');
                        if (countdownEl) countdownEl.classList.remove('show');
                        currentLivenessState = STATE_ALIGNING;
                        alignedStartTime = 0;
                        window._countdownLostStartTime = 0;
                        updateInstruction("Align your face in the circle", "Face lost, please realign");
                        setProgressRing(0);
                    }
                } else if (currentLivenessState === STATE_BLINK) {
                    if (!window._blinkLostStartTime) {
                        window._blinkLostStartTime = Date.now();
                    } else if (Date.now() - window._blinkLostStartTime > 2000) {
                        currentLivenessState = STATE_ALIGNING;
                        alignedStartTime = 0;
                        blinkStep = 0;
                        selfieFrames = [];
                        window._blinkLostStartTime = 0;
                        updateInstruction("Align your face in the circle", "Face lost, please realign");
                        setProgressRing(0);
                    }
                }
            }
        }

        if (isLivenessRunning) {
            animationFrameId = requestAnimationFrame(livenessDetectionLoop);
        }
    }

    async function autoSubmitLiveness() {
        const activeBox = document.getElementById('active-challenges-box');
        if (activeBox) activeBox.style.display = 'none';

        const scannerContainer = document.getElementById('scanner-container');
        if (scannerContainer) scannerContainer.style.display = 'none';

        document.getElementById('step-processing').style.display = 'block';
        document.getElementById('status-text').innerText = 'Verifying Biometrics...';
        document.getElementById('status-text').style.color = '';
        document.getElementById('status-subtext').innerText = 'Analyzing your face against the ID. This may take a few seconds.';
        updateStatusTracker(4);

        const formData = new FormData();
        selfieFrames.forEach(file => formData.append('selfies', file));
        formData.append('completed_challenges', 'blink');

        try {
            const res = await fetch(`/api/bookings/${bookingId}/verify-full`, { method: 'POST', body: formData });
            if (res.ok) {
                initKycWebSocket();
                startPolling();
            } else {
                const data = await res.json();
                handleRejection(data.detail || "Verification failed");
            }
        } catch (err) {
            handleRejection("Connection lost.");
        }
    }

    window.beginLivenessSequence = async function () {
        // Automatically starts on Start Camera now, kept for backward compatibility
    };

    window.retryLiveness = function () {
        selfieFrames = [];
        blinkStep = 0;
        currentLivenessState = STATE_ALIGNING;
        alignedStartTime = 0;
        isLivenessRunning = false;

        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
            animationFrameId = null;
        }
        if (countdownInterval) {
            clearInterval(countdownInterval);
            countdownInterval = null;
        }

        const countdownEl = document.getElementById('selfie-countdown');
        if (countdownEl) countdownEl.classList.remove('show');

        const checkmarkOverlay = document.getElementById('success-checkmark-overlay');
        if (checkmarkOverlay) checkmarkOverlay.style.display = 'none';

        const livenessRetryBanner = document.getElementById('liveness-retry-banner');
        if (livenessRetryBanner) livenessRetryBanner.style.display = 'none';

        document.getElementById('liveness-review').style.display = 'none';
        document.getElementById('scanner-container').style.display = 'block';

        setProgressRing(0);
        updateInstruction("Preparing camera...", "Position your face within the circle");

        window.startRealtimeScanner();
    };

    window.submitLiveness = async function () {
        // Automatically handled by autoSubmitLiveness, kept for backward compatibility
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
                } else if (data.status === 'rejected' || data.status === 'failed') {
                    stopPolling();
                    if (ws) ws.close();
                    handleRejection(data.reason || "Verification failed");
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
                    stopPolling();
                    document.getElementById('step-processing').style.display = 'none';
                    const initLoading = document.getElementById('kyc-loading-init');
                    if (initLoading) initLoading.style.display = 'none';
                    document.getElementById('kyc-waiting-approval').style.display = 'block';
                    if (!ws) {
                        initKycWebSocket();
                    }
                    pollingInterval = setInterval(async () => {
                        try {
                            const r2 = await fetch(`/api/bookings/${bookingId}/status`);
                            const d2 = await r2.json();
                            if (d2.status === 'approved' || d2.status === 'verified') {
                                stopPolling();
                                handleApproval(d2);
                            } else if (d2.status === 'rejected' || d2.status === 'blocked' || d2.status === 'failed') {
                                stopPolling();
                                handleRejection(d2.reason || "Verification rejected by caterer");
                            }
                        } catch (e) { console.error("Polling error (phase 2)", e); }
                    }, 5000);
                } else if (data.status === 'liveliness_failed') {
                    stopPolling();
                    handleLivenessFailure(data.reason || "Liveness check failed. Please try again.");
                } else if (data.status === 'rejected' || data.status === 'blocked' || data.status === 'failed') {
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

    function initWebSocket(userId) { }

    function handleApproval(data) {
        const scannerContainer = document.getElementById('scanner-container');
        const checkmarkOverlay = document.getElementById('success-checkmark-overlay');

        if (scannerContainer && scannerContainer.style.display !== 'none' && checkmarkOverlay) {
            checkmarkOverlay.style.display = 'flex';
            updateInstruction("Identity Verified Successfully", "Your identity has been successfully verified. You may now proceed to the next step.");
            setProgressRing(100, "#22c55e");
        }

        document.getElementById('kyc-waiting-approval').style.display = 'none';
        const initLoading = document.getElementById('kyc-loading-init');
        if (initLoading) initLoading.style.display = 'none';

        const stepProcessing = document.getElementById('step-processing');
        if (stepProcessing) {
            if (scannerContainer && scannerContainer.style.display !== 'none') {
                // keep scanner visible to show checkmark
            } else {
                stepProcessing.style.display = 'block';
            }
        }

        document.getElementById('status-text').innerText = "Identity Verified Successfully";
        document.getElementById('status-text').style.color = "var(--kyc-accent)";
        document.getElementById('status-subtext').innerText = "Your identity has been successfully verified. You may now proceed to the next step.";

        document.getElementById('node-4').classList.add('completed');
        document.getElementById('node-4').classList.remove('active');

        setTimeout(() => {
            window.location.href = `/bookings/step/quotation/${bookingId}`;
        }, 2000);
    }

    function handleRejection(msg) {
        let title = "Verification Rejected";
        let message = msg;
        if (msg && msg.indexOf(" | ") !== -1) {
            const parts = msg.split(" | ");
            title = parts[0];
            message = parts[1];
        }

        document.getElementById('kyc-waiting-approval').style.display = 'none';
        const initLoading = document.getElementById('kyc-loading-init');
        if (initLoading) initLoading.style.display = 'none';

        document.getElementById('step-processing').style.display = 'block';
        document.getElementById('status-text').innerText = title;
        document.getElementById('status-text').style.color = "#ef4444";
        document.getElementById('status-subtext').innerText = message;

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
        let title = "Verification Failed";
        let message = msg;
        if (msg && msg.indexOf(" | ") !== -1) {
            const parts = msg.split(" | ");
            title = parts[0];
            message = parts[1];
        }

        document.getElementById('kyc-waiting-approval').style.display = 'none';
        const initLoading = document.getElementById('kyc-loading-init');
        if (initLoading) initLoading.style.display = 'none';
        document.getElementById('step-processing').style.display = 'none';

        const livenessRetryBanner = document.getElementById('liveness-retry-banner');
        if (livenessRetryBanner) {
            livenessRetryBanner.style.display = 'block';
            
            // Set dynamic title
            const titleEl = livenessRetryBanner.querySelector('div[style*="font-weight: 800"]');
            if (titleEl) titleEl.innerText = title;
            
            const msgEl = document.getElementById('liveness-retry-message');
            if (msgEl) msgEl.innerText = message;
        } else {
            if (window.showError) {
                window.showError(message, title);
            } else {
                alert(title + ': ' + message);
            }
        }

        fetch('/api/bookings/kyc/reset-liveness', { method: 'POST' }).catch(() => { });

        selfieFrames = [];
        blinkStep = 0;
        currentLivenessState = STATE_ALIGNING;
        alignedStartTime = 0;
        isLivenessRunning = false;

        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
            animationFrameId = null;
        }
        if (countdownInterval) {
            clearInterval(countdownInterval);
            countdownInterval = null;
        }

        const countdownEl = document.getElementById('selfie-countdown');
        if (countdownEl) countdownEl.classList.remove('show');

        const checkmarkOverlay = document.getElementById('success-checkmark-overlay');
        if (checkmarkOverlay) checkmarkOverlay.style.display = 'none';

        // Stop camera tracks so camera goes offline while waiting for the user to click retake
        if (stream) {
            try {
                stream.getTracks().forEach(track => track.stop());
            } catch (e) { }
            stream = null;
        }
        const video = document.getElementById('webcam');
        if (video) video.srcObject = null;
        if (guideCtx) guideCtx.clearRect(0, 0, guideCanvas.width, guideCanvas.height);

        document.getElementById('scanner-container').style.display = 'block';
        setProgressRing(0);
        updateInstruction("Verification failed", "Click 'Retake Verification' to try again");

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

    const scannerContainer = document.getElementById('scanner-container');
    if (scannerContainer && scannerContainer.style.display === 'block') {
        const failureBanner = document.getElementById('liveness-retry-banner');
        const isFailed = failureBanner && failureBanner.style.display === 'block';
        if (!isFailed) {
            console.log("[KYC] Page loaded in liveness step. Auto-starting camera...");
            window.startRealtimeScanner();
        } else {
            console.log("[KYC] Page loaded in failed liveness step. Waiting for user to click Retake...");
            updateInstruction("Verification failed", "Click 'Retake Verification' to try again");
        }
    }

    const waitingEl = document.getElementById('kyc-waiting-approval');
    const loadingInitEl = document.getElementById('kyc-loading-init');
    if ((waitingEl && waitingEl.style.display === 'block') || loadingInitEl) {
        console.log("[KYC] Page loaded in waiting/processing state. Initializing real-time listeners...");
        initKycWebSocket();
        startPolling();
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initKyc);
} else {
    initKyc();
}

