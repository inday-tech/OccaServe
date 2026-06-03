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
    document.querySelectorAll('input[type="color"]').forEach(input => {
        input.addEventListener('input', () => {
            const name = input.getAttribute('name');
            const cssVar = `--${name.replace('_', '-')}`;
            document.documentElement.style.setProperty(cssVar, input.value);
            const rgb = hexToRgb(input.value);
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
    logoInputs.forEach(input => {
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

    // Magic Palette Extraction Logic
    const magicBtns = document.querySelectorAll('.magic-extract-shared');
    magicBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get file from the input closest to this button, or fallback to the first one found
            const formGroup = this.closest('.form-group') || this.closest('.logo-extraction-row') || document;
            const fileInput = formGroup.querySelector('.logo-input-shared') || document.querySelector('.logo-input-shared');
            const file = fileInput ? fileInput.files[0] : null;
            
            if (!file && !document.querySelector('.profile-sidebar-logo img')) {
                if (window.showError) window.showError("Please select a logo file first!");
                else alert("Please select a logo file first!");
                return;
            }
            
            const btnOriginalHtml = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
            this.disabled = true;

            const processImage = (imgSrc) => {
                const img = new Image();
                img.crossOrigin = "Anonymous";
                img.src = imgSrc;
                img.onload = function() {
                    try {
                        const colorThief = new ColorThief();
                        const dominantColor = colorThief.getColor(img);
                        const palette = colorThief.getPalette(img, 3) || [];
                        
                        const rgbToHex = (r, g, b) => '#' + [r, g, b].map(x => {
                            const hex = x.toString(16);
                            return hex.length === 1 ? '0' + hex : hex;
                        }).join('');

                        const primaryHex = rgbToHex(dominantColor[0], dominantColor[1], dominantColor[2]);
                        const secondaryHex = palette.length > 0 ? rgbToHex(palette[0][0], palette[0][1], palette[0][2]) : primaryHex;
                        const accentHex = palette.length > 1 ? rgbToHex(palette[1][0], palette[1][1], palette[1][2]) : primaryHex;
                        const highlightHex = palette.length > 2 ? rgbToHex(palette[2][0], palette[2][1], palette[2][2]) : accentHex;

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

                        applyColor('primary_color', primaryHex);
                        applyColor('secondary_color', secondaryHex);
                        applyColor('accent_color', accentHex);
                        applyColor('highlight_color', highlightHex);
                        
                        if (typeof updateMockup === 'function') updateMockup();

                        if (window.showSuccess) window.showSuccess("Magic Palette applied successfully!");
                        else alert("Magic Palette applied successfully!");
                    } catch (err) {
                        console.error("Extraction error", err);
                        if (window.showError) window.showError("Failed to extract colors. Please try a different image format.");
                    } finally {
                        btn.innerHTML = btnOriginalHtml;
                        btn.disabled = false;
                    }
                };
                img.onerror = () => {
                    if (window.showError) window.showError("Failed to load image for extraction.");
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
    });

    // Initial Update
    updateMockup();
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
    if (!window.Swal) return;

    const { value: reason, isConfirmed } = await Swal.fire({
        title: 'Deactivate Account',
        text: 'Please provide a reason for deactivating your account (optional):',
        input: 'text',
        inputPlaceholder: 'e.g. Taking a break, remodeling...',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Proceed to Deactivate'
    });

    if (!isConfirmed) return; // User cancelled

    const confirmResult = await Swal.fire({
        title: 'Are you absolutely sure?',
        text: 'Your business will be hidden from customers. You can reactivate anytime by logging back in and going to settings.',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, deactivate my account'
    });

    if (!confirmResult.isConfirmed) return;

    try {
        const response = await fetch('/caterer/settings/deactivate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason: reason || 'No reason provided' })
        });
        const result = await response.json();
        if (result.status === 'success') {
            if (window.showSuccess) window.showSuccess('Account deactivated. Redirecting...');
            setTimeout(() => window.location.href = '/auth/logout', 2000);
        } else {
            if (window.showError) window.showError(result.message || 'Failed to deactivate.');
        }
    } catch (err) {
        console.error(err);
        if (window.showError) window.showError('An error occurred.');
    }
}

// Account Deletion Request
async function handleDeleteRequest() {
    if (!window.Swal) return;

    const { value: confirmed, isConfirmed } = await Swal.fire({
        title: 'Request Account Deletion',
        html: 'Permanently delete all your data. This action <b>cannot be undone</b>.<br><br>Type <strong>DELETE</strong> to confirm:',
        input: 'text',
        inputPlaceholder: 'DELETE',
        icon: 'error',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Request Deletion'
    });

    if (!isConfirmed) return;

    if (confirmed !== 'DELETE') {
        if (window.showError) window.showError('You must type "DELETE" exactly to confirm.');
        return;
    }

    if (window.showSuccess) {
        window.showSuccess('Your deletion request has been submitted. An admin will review and process it within 7 business days.');
    }
}

// Reset Brand to Defaults
async function resetBrandDefaults() {
    if (!window.Swal) return;

    const result = await Swal.fire({
        title: 'Reset Brand Settings?',
        text: 'This will clear all your custom colors, fonts, textures, and decorations, reverting to OccaServe defaults.',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, reset to defaults'
    });

    if (!result.isConfirmed) return;

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
