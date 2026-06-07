/**
 * Caterer Profile Edit Logic
 * Handles color extraction, live branding preview, payment validation, and tab management.
 */
document.addEventListener('DOMContentLoaded', function () {
    // 1. Tab Management Logic
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            // Toggle Buttons
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Toggle Contents
            tabContents.forEach(content => {
                if (content.id === targetTab) {
                    content.classList.add('active');
                } else {
                    content.classList.remove('active');
                }
            });

            // Update URL hash without scroll
            history.replaceState(null, null, '#' + targetTab);
        });
    });

    // Restore Tab from Hash
    const currentHash = window.location.hash.substring(1);
    if (currentHash) {
        const targetBtn = document.querySelector(`.tab-btn[data-tab="${currentHash}"]`);
        if (targetBtn) targetBtn.click();
    }

    // 2. Color Code Sync (Color Input -> Text Span)
    const colorInputs = document.querySelectorAll('input[type="color"]');
    colorInputs.forEach(input => {
        input.addEventListener('input', (e) => {
            const codeSpan = input.nextElementSibling;
            if (codeSpan && codeSpan.classList.contains('color-code')) {
                codeSpan.textContent = e.target.value.toUpperCase();
            }
        });
    });

    // 3. Magic Palette extraction has been migrated to use ColorThief below

    // 4. Advanced Branding Sync
    const fontSelect = document.querySelector('select[name="font_family"]');
    const radiusInput = document.querySelector('input[name="border_radius"]');
    const textureSelect = document.querySelector('select[name="dashboard_texture"]');
    const sidebarDecorSelect = document.querySelector('select[name="sidebar_decoration"]');
    const headerDecorSelect = document.querySelector('select[name="header_decoration"]');
    const presetItems = document.querySelectorAll('.preset-item');

    function applyPalette(palette) {
        const fields = {
            primary_color: palette.primary,
            secondary_color: palette.secondary,
            accent_color: palette.accent,
            highlight_color: palette.highlight
        };

        for (const [name, val] of Object.entries(fields)) {
            const input = document.querySelector(`input[name="${name}"]`);
            if (input && val) {
                input.value = val;
                const code = input.nextElementSibling;
                if (code && code.classList.contains('color-code')) code.textContent = val.toUpperCase();
            }
        }
        updateMockup();
    }

    function updateMockup() {
        const mockup = document.getElementById('mockupContainer');
        if (!mockup) return;

        const getVal = (name) => document.querySelector(`input[name="${name}"]`)?.value;
        
        const colors = {
            primary: getVal('primary_color'),
            secondary: getVal('secondary_color'),
            accent: getVal('accent_color'),
            highlight: getVal('highlight_color')
        };

        mockup.style.setProperty('--primary-color', colors.primary);
        mockup.style.setProperty('--secondary-color', colors.secondary);
        mockup.style.setProperty('--accent-color', colors.accent);
        mockup.style.setProperty('--highlight-color', colors.highlight);

        const mSidebar = document.getElementById('mockSidebar');
        const mHeader = document.getElementById('mockHeader');
        const mMainBody = document.getElementById('mockMainBody');
        const mCards = mockup.querySelectorAll('.mock-mini-card, .mock-card-large');
        const mBtn = document.getElementById('mockActionBtn');

        if (mSidebar) mSidebar.style.background = '#ffffff';
        if (mHeader) mHeader.style.background = '#ffffff';
        
        if (mMainBody) mMainBody.className = 'mock-content-body texture-' + (textureSelect?.value || 'none');
        
        mockup.classList.remove('glass-active');

        mockup.style.fontFamily = fontSelect?.value || 'Inter';
        const radius = radiusInput?.value || 12;
        mockup.style.setProperty('--preview-radius', radius + 'px');

        // Decorations Logic
        const sDecor = sidebarDecorSelect?.value || 'none';
        const hDecor = headerDecorSelect?.value || 'none';
        
        let sHtml = '';
        if (sDecor === 'chef-hat') {
            sHtml = '<div class="mock-sidebar-decor sticker-1"><i class="fas fa-hat-chef"></i></div>' +
                    '<div class="mock-sidebar-decor sticker-2" style="top:30%;"><i class="fas fa-utensils"></i></div>' +
                    '<div class="mock-sidebar-decor sticker-3" style="top:50%;"><i class="fas fa-mitten"></i></div>';
        } else if (sDecor === 'food-pack') {
            sHtml = '<div class="mock-sidebar-decor sticker-1"><i class="fas fa-pizza-slice" style="color: #ed8936;"></i></div>' +
                    '<div class="mock-sidebar-decor sticker-2" style="top:30%; color: #ecc94b;"><i class="fas fa-hamburger"></i></div>' +
                    '<div class="mock-sidebar-decor sticker-3" style="top:50%; color: #f687b3;"><i class="fas fa-ice-cream"></i></div>';
        } else if (sDecor === 'party-pack') {
            sHtml = '<div class="mock-sidebar-decor sticker-1"><i class="fas fa-balloons" style="color: #4299e1;"></i></div>' +
                    '<div class="mock-sidebar-decor sticker-2" style="top:30%; color: #ed64a6;"><i class="fas fa-glass-cheers"></i></div>' +
                    '<div class="mock-sidebar-decor sticker-3" style="top:50%; color: #48bb78;"><i class="fas fa-music"></i></div>';
        } else if (sDecor === 'steam') {
            sHtml = '<div class="mock-sidebar-decor sticker-1"><i class="fas fa-mug-hot steam-icon"></i></div>' +
                    '<div class="mock-sidebar-decor sticker-2" style="top:40%; color:#a0aec0;"><i class="fas fa-cookie-bite"></i></div>';
        }
        
        const existingSDecors = mSidebar.querySelectorAll('.mock-sidebar-decor');
        existingSDecors.forEach(d => d.remove());
        if (sHtml) mSidebar.insertAdjacentHTML('beforeend', sHtml);

        let hHtml = '';
        if (hDecor === 'utensils') {
            hHtml = '<div class="mock-header-decor" style="left:5%;"><i class="fas fa-utensils"></i></div>' +
                    '<div class="mock-header-decor" style="left:20%; color:#ecc94b;"><i class="fas fa-wine-glass"></i></div>' +
                    '<div class="mock-header-decor" style="left:40%;"><i class="fas fa-cheese"></i></div>' +
                    '<div class="mock-header-decor" style="left:60%; color:#ed8936;"><i class="fas fa-pizza-slice"></i></div>' +
                    '<div class="mock-header-decor" style="left:85%;"><i class="fas fa-ice-cream"></i></div>';
        } else if (hDecor === 'sparkles') {
            hHtml = '<div class="mock-header-decor" style="left:10%; opacity:0.6;"><i class="fas fa-sparkles fa-spin" style="color:#f6e05e;"></i></div>' +
                    '<div class="mock-header-decor" style="left:35%; opacity:0.6;"><i class="fas fa-star" style="color:#f6e05e;"></i></div>' +
                    '<div class="mock-header-decor" style="left:65%; opacity:0.6;"><i class="fas fa-shimmer" style="color:#f6e05e;"></i></div>' +
                    '<div class="mock-header-decor" style="left:90%; opacity:0.6;"><i class="fas fa-star-shooting" style="color:#f6e05e;"></i></div>';
        } else if (hDecor === 'delivery') {
            hHtml = '<div class="mock-header-decor" style="left:15%;"><i class="fas fa-truck-container" style="color:var(--primary-color);"></i></div>' +
                    '<div class="mock-header-decor" style="left:50%;"><i class="fas fa-box-check" style="color:var(--highlight-color);"></i></div>' +
                    '<div class="mock-header-decor" style="left:85%;"><i class="fas fa-map-marker-alt" style="color:var(--accent-color);"></i></div>';
        }
        
        const existingHDecors = mHeader.querySelectorAll('.mock-header-decor');
        existingHDecors.forEach(d => d.remove());
        if (hHtml) mHeader.insertAdjacentHTML('beforeend', hHtml);
        
        mCards.forEach(c => c.style.borderRadius = radius + 'px');
        if (mBtn) mBtn.style.borderRadius = (radius * 0.8) + 'px';
        const mSearch = mockup.querySelector('.mock-search-bar');
        if (mSearch) mSearch.style.borderRadius = radius + 'px';
    }

    // Event Listeners for Live Preview
    [fontSelect, radiusInput, textureSelect, sidebarDecorSelect, headerDecorSelect].forEach(el => {
        if (!el) return;
        const evt = el.tagName === 'INPUT' && el.type === 'range' ? 'input' : 'change';
        el.addEventListener(evt, () => {
            if (el === radiusInput) document.documentElement.style.setProperty('--border-radius', radiusInput.value + 'px');
            if (el === fontSelect) document.documentElement.style.setProperty('--font-family', fontSelect.value);
            updateMockup();
        });
        if (el.type === 'color') {
            el.addEventListener('input', updateMockup);
        }
    });

    // Color input sync with global CSS
    const hexToRgbGlobal = (hex) => {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? { r: parseInt(result[1], 16), g: parseInt(result[2], 16), b: parseInt(result[3], 16) } : null;
    };
    
    document.querySelectorAll('input[type="color"]').forEach(input => {
        input.addEventListener('input', () => {
            const name = input.getAttribute('name');
            const cssVar = `--${name.replace('_', '-')}`;
            document.documentElement.style.setProperty(cssVar, input.value);
            const rgb = hexToRgbGlobal(input.value);
            if (rgb) document.documentElement.style.setProperty(`${cssVar}-rgb`, `${rgb.r}, ${rgb.g}, ${rgb.b}`);
        });
    });

    presetItems.forEach(item => {
        item.addEventListener('click', () => {
            applyPalette({
                primary: item.getAttribute('data-primary'),
                secondary: item.getAttribute('data-secondary'),
                accent: item.getAttribute('data-accent'),
                highlight: item.getAttribute('data-highlight')
            });
        });
    });

    // Logo image preview
    document.querySelectorAll('.form-file-input').forEach(input => {
        input.addEventListener('change', function() {
            if (this.files?.[0]) {
                const reader = new FileReader();
                reader.onload = e => {
                    const mockLogo = document.querySelector('.mock-logo');
                    if (mockLogo) {
                        mockLogo.style.backgroundImage = `url(${e.target.result})`;
                        mockLogo.style.backgroundSize = 'contain';
                        mockLogo.style.backgroundRepeat = 'no-repeat';
                        mockLogo.style.backgroundPosition = 'center';
                        mockLogo.style.backgroundColor = 'transparent';
                    }
                    
                    // Also update the sidebar logo preview!
                    const sidebarLogo = document.querySelector('.profile-sidebar-logo');
                    if (sidebarLogo) {
                        sidebarLogo.innerHTML = `<img src="${e.target.result}" alt="Business Logo" style="width: 100%; height: 100%; object-fit: cover;">`;
                    }
                };
                reader.readAsDataURL(this.files[0]);
            }
        });
    });

    // Magic Palette Extraction Logic using Event Delegation
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.magic-extract-shared');
        if (!btn) return;
        
        e.preventDefault();
        console.log("Analyze & Apply clicked!");
        
        const fileInput = document.querySelector('input[name="logo_brand"]');
        const file = fileInput ? fileInput.files[0] : null;
        
        if (!file && !document.querySelector('.profile-sidebar-logo img')) {
            if (typeof Swal !== 'undefined') {
                Swal.fire('Requirement', 'Please upload a logo in the Professional Branding tab first!', 'warning');
            } else {
                alert('Please upload a logo in the Professional Branding tab first!');
            }
            return;
        }
        
        const btnOriginalHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
        btn.disabled = true;

        const processImage = (imgSrc) => {
            const img = new Image();
            if (imgSrc.startsWith('http') || imgSrc.startsWith('/')) {
                img.crossOrigin = "Anonymous";
            }
            img.src = imgSrc;
            img.onload = function() {
                try {
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    const size = 150; 
                    canvas.width = size;
                    canvas.height = size;
                    ctx.drawImage(img, 0, 0, size, size);

                    const imageData = ctx.getImageData(0, 0, size, size).data;
                    const colorCounts = {};
                    const q = 16; 

                    for (let i = 0; i < imageData.length; i += 4) {
                        const r = imageData[i], g = imageData[i + 1], b = imageData[i + 2], a = imageData[i + 3];
                        if (a < 128) continue; 

                        const avg = (r + g + b) / 3;
                        if (avg > 240 || avg < 15) continue; 

                        const qr = Math.round(r / q) * q;
                        const qg = Math.round(g / q) * q;
                        const qb = Math.round(b / q) * q;
                        const key = `${qr},${qg},${qb}`;
                        colorCounts[key] = (colorCounts[key] || 0) + 1;
                    }

                    const rgbToHex = (r, g, b) => "#" + [r, g, b].map(x => x.toString(16).padStart(2, '0')).join('').toUpperCase();
                    const hexToRgb = (hex) => {
                        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
                        return result ? { r: parseInt(result[1], 16), g: parseInt(result[2], 16), b: parseInt(result[3], 16) } : {r:0,g:0,b:0};
                    };
                    const rgbToHsv = (r, g, b) => {
                        r /= 255, g /= 255, b /= 255;
                        const max = Math.max(r, g, b), min = Math.min(r, g, b);
                        let h, s, v = max;
                        const d = max - min;
                        s = max === 0 ? 0 : d / max;
                        if (max === min) h = 0;
                        else {
                            switch (max) {
                                case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                                case g: h = (b - r) / d + 2; break;
                                case b: h = (r - g) / d + 4; break;
                            }
                            h /= 6;
                        }
                        return { h, s, v };
                    };
                    const hsvToRgb = (h, s, v) => {
                        let r, g, b;
                        const i = Math.floor(h * 6);
                        const f = h * 6 - i;
                        const p = v * (1 - s);
                        const q = v * (1 - f * s);
                        const t = v * (1 - (1 - f) * s);
                        switch (i % 6) {
                            case 0: r = v, g = t, b = p; break;
                            case 1: r = q, g = v, b = p; break;
                            case 2: r = p, g = v, b = t; break;
                            case 3: r = p, g = q, b = v; break;
                            case 4: r = t, g = p, b = v; break;
                            case 5: r = v, g = p, b = q; break;
                        }
                        return { r: Math.round(r * 255), g: Math.round(g * 255), b: Math.round(b * 255) };
                    };

                    const sortedColors = Object.entries(colorCounts)
                        .map(([rgbStr, count]) => {
                            const rgb = rgbStr.split(',').map(Number);
                            const hex = rgbToHex(rgb[0], rgb[1], rgb[2]);
                            const hsv = rgbToHsv(rgb[0], rgb[1], rgb[2]);
                            return { hex, count, ...hsv };
                        })
                        .sort((a, b) => b.count - a.count);
                    
                    if (sortedColors.length === 0) throw new Error("No usable colors extracted.");

                    const hueGroups = {};
                    sortedColors.forEach(c => {
                        const hKey = Math.floor(c.h * 12);
                        if (!hueGroups[hKey]) hueGroups[hKey] = [];
                        hueGroups[hKey].push(c);
                    });

                    const groups = Object.values(hueGroups).sort((a, b) => {
                        const countA = a.reduce((sum, curr) => sum + curr.count, 0);
                        const countB = b.reduce((sum, curr) => sum + curr.count, 0);
                        return countB - countA;
                    });

                    const getBalancedColor = (candidates) => {
                        return candidates.sort((a, b) => {
                            const scoreA = (a.s > 0.2 ? 1 : 0) + (a.v > 0.2 && a.v < 0.8 ? 1 : 0);
                            const scoreB = (b.s > 0.2 ? 1 : 0) + (b.v > 0.2 && b.v < 0.8 ? 1 : 0);
                            return scoreB - scoreA || b.count - a.count;
                        })[0];
                    };

                    let primary = getBalancedColor(groups[0]).hex;

                    let secondary;
                    if (groups[1]) {
                        secondary = getBalancedColor(groups[1]).hex;
                    } else {
                        const pRgb = hexToRgb(primary);
                        secondary = rgbToHex(Math.max(0, pRgb.r - 40), Math.max(0, pRgb.g - 40), Math.max(0, pRgb.b - 40));
                    }

                    const allBySaturation = [...sortedColors].sort((a, b) => b.s - a.s);
                    let accent = (allBySaturation.find(c => c.s > 0.4 && c.v > 0.4) || allBySaturation[0]).hex;

                    const highlight = rgbToHex(
                        Math.min(255, hexToRgb(primary).r + 180),
                        Math.min(255, hexToRgb(primary).g + 180),
                        Math.min(255, hexToRgb(primary).b + 180)
                    );

                    const sanitize = (hex) => {
                        const hsv = rgbToHsv(...Object.values(hexToRgb(hex)));
                        if (hsv.s > 0.85 || hsv.v > 0.95) {
                            const rgb = hsvToRgb(hsv.h, Math.min(hsv.s, 0.7), Math.min(hsv.v, 0.8));
                            return rgbToHex(rgb.r, rgb.g, rgb.b);
                        }
                        return hex;
                    };

                    const applyColor = (name, hex) => {
                        const input = document.querySelector(`input[name="${name}"]`);
                        if (input) {
                            input.value = hex;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            const span = input.nextElementSibling;
                            if (span && span.classList.contains('color-code')) {
                                span.textContent = hex.toUpperCase();
                            }
                        }
                    };

                    applyColor('primary_color', sanitize(primary));
                    applyColor('secondary_color', sanitize(secondary));
                    applyColor('accent_color', sanitize(accent));
                    applyColor('highlight_color', sanitize(highlight));
                    
                    if (typeof updateMockup === 'function') updateMockup();

                    if (typeof Swal !== 'undefined') {
                        Swal.fire('Palette Generated!', 'Magic Palette applied. Elite dashboard theme generated.', 'success');
                    } else {
                        alert('Palette Generated! Magic Palette applied.');
                    }
                } catch (err) {
                    console.error("Extraction error", err);
                    if (typeof Swal !== 'undefined') {
                        Swal.fire('Extraction Failed', 'Failed to extract colors. Please try a different image format.', 'error');
                    } else {
                        alert('Extraction Failed: Failed to extract colors.');
                    }
                } finally {
                    btn.innerHTML = btnOriginalHtml;
                    btn.disabled = false;
                }
            };
            img.onerror = () => {
                if (typeof Swal !== 'undefined') {
                    Swal.fire('Load Failed', 'Failed to load image for extraction.', 'error');
                } else {
                    alert('Load Failed: Failed to load image for extraction.');
                }
                btn.innerHTML = btnOriginalHtml;
                btn.disabled = false;
            };
        };

        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => processImage(event.target.result);
            reader.readAsDataURL(file);
        } else {
            const existingImg = document.querySelector('.profile-sidebar-logo img');
            if (existingImg) processImage(existingImg.src);
        }
    });

    // Initial Update
    updateMockup();

    // Hook up danger zone buttons
    const btnDeactivate = document.getElementById('btnDeactivate');
    const btnReactivate = document.getElementById('btnReactivate');
    const btnDelete = document.getElementById('btnDeleteRequest');

    if (btnDeactivate) {
        btnDeactivate.addEventListener('click', (e) => {
            e.preventDefault();
            handleDeactivate();
        });
    }
    if (btnReactivate) {
        btnReactivate.addEventListener('click', (e) => {
            e.preventDefault();
            handleReactivate();
        });
    }
    if (btnDelete) {
        btnDelete.addEventListener('click', (e) => {
            e.preventDefault();
            handleDeleteRequest();
        });
    }
});

// Gallery Archive Function
async function archiveGalleryItem(itemId) {
    if (!confirm('Archive this photo?')) return;
    try {
        const response = await fetch(`/caterer/gallery/${itemId}/archive`, { method: 'POST' });
        if (response.ok) {
            const btn = document.querySelector(`button[onclick="archiveGalleryItem(${itemId})"]`);
            const item = btn?.closest('.gallery-item-wrapper');
            if (item) {
                item.style.opacity = '0';
                item.style.transform = 'scale(0.8)';
                setTimeout(() => item.remove(), 300);
            }
            if (window.showSuccess) window.showSuccess('Photo archived successfully.');
        }
    } catch (err) { console.error(err); }
}

// Notification Preferences
async function saveNotificationPrefs() {
    const btn = document.getElementById('saveNotifsBtn');
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    btn.disabled = true;

    const prefs = {};
    document.querySelectorAll('#notifPrefsList input[data-pref]').forEach(input => {
        prefs[input.dataset.pref] = input.checked;
    });

    try {
        const response = await fetch('/caterer/settings/notifications', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(prefs)
        });
        const result = await response.json();
        if (result.status === 'success') {
            if (window.showSuccess) window.showSuccess('Notification preferences saved!');
        } else {
            if (window.showError) window.showError(result.message || 'Failed to save.');
        }
    } catch (err) {
        console.error(err);
        if (window.showError) window.showError('An error occurred. Please try again.');
    } finally {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    }
}

// Account Deactivation
async function handleDeactivate() {
    if (typeof Swal !== "undefined") {
        const result = await Swal.fire({
            title: "Deactivate Account?",
            text: "Your profile will be hidden from customers. Are you sure?",
            icon: "warning",
            showCancelButton: true,
            confirmButtonColor: "#f39c12",
            cancelButtonColor: "#3085d6",
            confirmButtonText: "Yes, deactivate it!"
        });
        if (!result.isConfirmed) return;
    } else {
        if (!confirm("Are you sure you want to deactivate your account? Your profile will be hidden from customers.")) return;
    }
    try {
        const res = await window.apiAction("/caterer/settings/deactivate", { method: "POST" });
        if (res) setTimeout(() => window.location.href = "/login", 1500);
    } catch (e) {}
}

async function handleReactivate() {
    if (typeof Swal !== "undefined") {
        const result = await Swal.fire({
            title: "Reactivate Account?",
            text: "Your profile will be visible to customers again.",
            icon: "info",
            showCancelButton: true,
            confirmButtonColor: "#2ecc71",
            cancelButtonColor: "#3085d6",
            confirmButtonText: "Yes, reactivate it!"
        });
        if (!result.isConfirmed) return;
    } else {
        if (!confirm("Are you sure you want to reactivate your account? Your profile will be visible again.")) return;
    }
    try {
        const res = await window.apiAction("/caterer/settings/reactivate", { method: "POST" });
        if (res) setTimeout(() => window.location.reload(), 1500);
    } catch (e) {}
}

async function handleDeleteRequest() {
    if (typeof Swal !== "undefined") {
        const result = await Swal.fire({
            title: "PERMANENTLY DELETE ACCOUNT?",
            text: "WARNING: All data, dishes, and history will be lost. This cannot be undone!",
            icon: "error",
            showCancelButton: true,
            confirmButtonColor: "#d33",
            cancelButtonColor: "#3085d6",
            confirmButtonText: "Yes, delete my account forever!"
        });
        if (!result.isConfirmed) return;
    } else {
        if (!confirm("WARNING: Are you absolutely sure you want to PERMANENTLY delete your account? All data, dishes, and history will be lost. This cannot be undone.")) return;
    }
    try {
        const res = await window.apiAction("/caterer/settings/delete", { method: "POST" });
        if (res) setTimeout(() => window.location.href = "/login", 2000);
    } catch (e) {}
}

// Reset Brand to Defaults
async function resetBrandDefaults() {
    if (!window.showStandardConfirm) return;

    const { isConfirmed } = await window.showStandardConfirm({
        title: 'Reset Brand Settings?',
        message: 'This will clear all your custom colors, fonts, textures, and decorations, reverting to OccaServe defaults.',
        icon: 'warning',
        confirmButtonText: 'Yes, reset to defaults'
    });

    if (!isConfirmed) return;

    try {
        const response = await fetch('/caterer/settings/reset-brand', { method: 'POST' });
        const resJson = await response.json();
        if (resJson.status === 'success') {
            if (window.showSuccess) window.showSuccess('Brand settings reset! Reloading page...');
            setTimeout(() => window.location.reload(), 1500);
        } else {
            if (window.showError) window.showError(resJson.message || 'Failed to reset.');
        }
    } catch (err) {
        console.error(err);
        if (window.showError) window.showError('An error occurred.');
    }
}
