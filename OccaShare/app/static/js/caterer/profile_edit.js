/**
 * Caterer Profile Edit Logic - Settings Sidebar Layout
 * Handles sidebar navigation, accordion groups, color extraction, live branding preview.
 */

// ─── Section Metadata ───
const SECTION_META = {
    'general':          { title: 'Business Info',          subtitle: 'Core identity details of your catering business.' },
    'location':         { title: 'Location & Contact',     subtitle: 'Your official business address used for search and bookings.' },
    'payment-methods':  { title: 'Payment Methods',        subtitle: 'Configure how customers can pay you and where you\'ll receive your earnings.' },
    'booking-policies': { title: 'Booking Policies',       subtitle: 'Set clear expectations for bookings, payments, and cancellations.' },
    'brand':            { title: 'Brand Colors & Style',   subtitle: 'Customize the look and feel of your caterer portal.' },
    'verification':     { title: 'Verification Center',    subtitle: 'Submit your compliance documents. These are private and never visible to customers.' },
    'account':          { title: 'Account & Security',     subtitle: 'Manage your personal info, notifications, and account preferences.' },
};

// ─── Sidebar Section Switching ───
window.switchSettingsSection = function(sectionId) {
    document.querySelectorAll('.settings-section').forEach(s => s.classList.remove('active'));
    const target = document.getElementById('section-' + sectionId);
    if (target) target.classList.add('active');

    document.querySelectorAll('.snav-item').forEach(item => item.classList.remove('active'));
    const activeNavItem = document.querySelector(`.snav-item[data-section="${sectionId}"]`);
    if (activeNavItem) activeNavItem.classList.add('active');

    const meta = SECTION_META[sectionId] || {};
    const titleEl = document.getElementById('contentPanelTitle');
    const subtitleEl = document.getElementById('contentPanelSubtitle');
    if (titleEl) titleEl.textContent = meta.title || sectionId;
    if (subtitleEl) subtitleEl.textContent = meta.subtitle || '';

    history.replaceState(null, null, '#' + sectionId);

    if (sectionId === 'location') {
        setTimeout(() => {
            if (typeof mapInitialized !== 'undefined' && !mapInitialized) {
                if (typeof initLocationMap === 'function') initLocationMap();
            } else if (typeof map !== 'undefined' && map && typeof google !== 'undefined') {
                google.maps.event.trigger(map, 'resize');
                if (typeof marker !== 'undefined') map.setCenter(marker.getPosition());
            }
        }, 250);
    }

    const contentEl = document.querySelector('.settings-content');
    if (contentEl) contentEl.scrollTo({ top: 0, behavior: 'smooth' });
};

// ─── Accordion Toggle for Nav Groups ───
window.toggleNavGroup = function(groupId) {
    const group = document.getElementById(groupId);
    if (!group) return;
    const header = group.querySelector('.snav-group-header');
    const items = group.querySelector('.snav-group-items');
    const isExpanded = header.classList.contains('expanded');

    if (isExpanded) {
        header.classList.remove('expanded');
        items.style.maxHeight = '0px';
        items.style.opacity = '0';
        setTimeout(() => { items.style.display = 'none'; }, 280);
    } else {
        header.classList.add('expanded');
        items.style.display = 'flex';
        items.style.maxHeight = '0px';
        items.style.opacity = '0';
        requestAnimationFrame(() => {
            items.style.maxHeight = items.scrollHeight + 'px';
            items.style.opacity = '1';
        });
    }
};

document.addEventListener('DOMContentLoaded', function () {
    // 1. Sidebar Nav Click Handlers
    document.querySelectorAll('.snav-item').forEach(item => {
        item.addEventListener('click', () => {
            const sectionId = item.getAttribute('data-section');
            if (!sectionId) return;

            const parentGroup = item.closest('.snav-group');
            if (parentGroup) {
                const header = parentGroup.querySelector('.snav-group-header');
                if (header && !header.classList.contains('expanded')) {
                    toggleNavGroup(parentGroup.id);
                }
            }

            switchSettingsSection(sectionId);
        });
    });

    // Restore Section from Hash
    const currentHash = window.location.hash.substring(1);
    if (currentHash && SECTION_META[currentHash]) {
        const navItem = document.querySelector(`.snav-item[data-section="${currentHash}"]`);
        if (navItem) {
            const parentGroup = navItem.closest('.snav-group');
            if (parentGroup) {
                const groupHeader = parentGroup.querySelector('.snav-group-header');
                if (groupHeader && !groupHeader.classList.contains('expanded')) {
                    const groupItems = parentGroup.querySelector('.snav-group-items');
                    groupHeader.classList.add('expanded');
                    if (groupItems) { groupItems.style.display = 'flex'; groupItems.style.maxHeight = '999px'; groupItems.style.opacity = '1'; }
                }
            }
        }
        switchSettingsSection(currentHash);
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
        
        const existingSDecors = mSidebar?.querySelectorAll('.mock-sidebar-decor');
        existingSDecors?.forEach(d => d.remove());
        if (sHtml && mSidebar) mSidebar.insertAdjacentHTML('beforeend', sHtml);

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
        
        const existingHDecors = mHeader?.querySelectorAll('.mock-header-decor');
        existingHDecors?.forEach(d => d.remove());
        if (hHtml && mHeader) mHeader.insertAdjacentHTML('beforeend', hHtml);
        
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
            updateMockup();
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

    // Logo image preview + sidebar logo update
    document.querySelectorAll('.logo-input-shared').forEach(input => {
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
                    // Update the sidebar logo in the new layout
                    const sidebarLogo = document.getElementById('sidebarLogoDisplay');
                    if (sidebarLogo) {
                        sidebarLogo.innerHTML = `<img src="${e.target.result}" alt="Business Logo" style="width: 100%; height: 100%; object-fit: cover;">`;
                    }
                };
                reader.readAsDataURL(this.files[0]);
            }
        });
    });

    // Magic Palette Extraction via Event Delegation
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.magic-extract-shared');
        if (!btn) return;
        
        e.preventDefault();
        
        const fileInput = document.querySelector('input[name="logo_brand"]');
        const file = fileInput ? fileInput.files[0] : null;
        
        if (!file && !document.getElementById('sidebarLogoDisplay')?.querySelector('img')) {
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
                    Vibrant.from(img).getPalette().then((palette) => {
                        const getHex = (swatch) => swatch ? swatch.getHex() : null;
                        
                        const lightenHex = (hex, percent) => {
                            if (!hex) return '#ffffff';
                            let r = parseInt(hex.slice(1, 3), 16),
                                g = parseInt(hex.slice(3, 5), 16),
                                b = parseInt(hex.slice(5, 7), 16);
                            r = Math.min(255, Math.floor(r + (255 - r) * percent));
                            g = Math.min(255, Math.floor(g + (255 - g) * percent));
                            b = Math.min(255, Math.floor(b + (255 - b) * percent));
                            return `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`;
                        };

                        const hexDiff = (hex1, hex2) => {
                            if(!hex1 || !hex2) return 0;
                            let r1 = parseInt(hex1.slice(1, 3), 16), g1 = parseInt(hex1.slice(3, 5), 16), b1 = parseInt(hex1.slice(5, 7), 16);
                            let r2 = parseInt(hex2.slice(1, 3), 16), g2 = parseInt(hex2.slice(3, 5), 16), b2 = parseInt(hex2.slice(5, 7), 16);
                            return Math.abs(r1-r2) + Math.abs(g1-g2) + Math.abs(b1-b2);
                        };

                        // Primary: Dominant brand color
                        let primary = getHex(palette.Vibrant) || getHex(palette.Muted) || '#FF7B54';
                        
                        // Secondary: Dark neutral. Fallback to #2F2F2F if too close to primary
                        let secondary = getHex(palette.DarkMuted) || getHex(palette.DarkVibrant);
                        if (!secondary || hexDiff(primary, secondary) < 150) {
                            secondary = '#2F2F2F';
                        }

                        // Accent: Vibrant or complementary. Fallback if too close to primary
                        let accent = getHex(palette.LightVibrant) || getHex(palette.Muted);
                        if (!accent || hexDiff(primary, accent) < 100) {
                            accent = '#FFB17A'; // OccaServe soft orange
                        }

                        // Highlight: Very light tint of Primary (85% lighter) for backgrounds
                        let highlight = lightenHex(primary, 0.85);

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

                        applyColor('primary_color', primary);
                        applyColor('secondary_color', secondary);
                        applyColor('accent_color', accent);
                        applyColor('highlight_color', highlight);
                        
                        if (typeof updateMockup === 'function') updateMockup();

                        if (typeof Swal !== 'undefined') {
                            Swal.fire('Palette Generated!', 'Magic Palette applied. Elite dashboard theme generated.', 'success');
                        }
                    }).catch(err => {
                        console.error("Extraction error", err);
                        if (typeof Swal !== 'undefined') {
                            Swal.fire('Extraction Failed', 'Failed to extract colors. Please try a different image format.', 'error');
                        }
                    }).finally(() => {
                        btn.innerHTML = btnOriginalHtml;
                        btn.disabled = false;
                    });
                } catch (err) {
                    btn.innerHTML = btnOriginalHtml;
                    btn.disabled = false;
                }
            };
            img.onerror = () => {
                if (typeof Swal !== 'undefined') {
                    Swal.fire('Load Failed', 'Failed to load image for extraction.', 'error');
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
            const existingImg = document.getElementById('sidebarLogoDisplay')?.querySelector('img');
            if (existingImg) processImage(existingImg.src);
        }
    });

    // Initial Preview Update
    updateMockup();

    // Hook up danger zone buttons
    const btnDeactivate = document.getElementById('btnDeactivate');
    const btnReactivate = document.getElementById('btnReactivate');
    const btnDelete = document.getElementById('btnDeleteRequest');

    if (btnDeactivate) {
        btnDeactivate.addEventListener('click', (e) => { e.preventDefault(); handleDeactivate(); });
    }
    if (btnReactivate) {
        btnReactivate.addEventListener('click', (e) => { e.preventDefault(); handleReactivate(); });
    }
    if (btnDelete) {
        btnDelete.addEventListener('click', (e) => { e.preventDefault(); handleDeleteRequest(); });
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
        const result = await Swal.fire({ title: "Deactivate Account?", text: "Your profile will be hidden from customers. Are you sure?", icon: "warning", showCancelButton: true, confirmButtonColor: "#f39c12", cancelButtonColor: "#3085d6", confirmButtonText: "Yes, deactivate it!" });
        if (!result.isConfirmed) return;
    } else {
        if (!confirm("Are you sure you want to deactivate your account?")) return;
    }
    try {
        const res = await window.apiAction("/caterer/settings/deactivate", { method: "POST" });
        if (res) setTimeout(() => window.location.href = "/login", 1500);
    } catch (e) {}
}

async function handleReactivate() {
    if (typeof Swal !== "undefined") {
        const result = await Swal.fire({ title: "Reactivate Account?", text: "Your profile will be visible to customers again.", icon: "info", showCancelButton: true, confirmButtonColor: "#2ecc71", cancelButtonColor: "#3085d6", confirmButtonText: "Yes, reactivate it!" });
        if (!result.isConfirmed) return;
    } else {
        if (!confirm("Are you sure you want to reactivate your account?")) return;
    }
    try {
        const res = await window.apiAction("/caterer/settings/reactivate", { method: "POST" });
        if (res) setTimeout(() => window.location.reload(), 1500);
    } catch (e) {}
}

async function handleDeleteRequest() {
    if (typeof Swal !== "undefined") {
        const result = await Swal.fire({ title: "PERMANENTLY DELETE ACCOUNT?", text: "WARNING: All data, dishes, and history will be lost. This cannot be undone!", icon: "error", showCancelButton: true, confirmButtonColor: "#d33", cancelButtonColor: "#3085d6", confirmButtonText: "Yes, delete my account forever!" });
        if (!result.isConfirmed) return;
    } else {
        if (!confirm("WARNING: Are you absolutely sure?")) return;
    }
    try {
        const res = await window.apiAction("/caterer/settings/delete", { method: "POST" });
        if (res) setTimeout(() => window.location.href = "/login", 2000);
    } catch (e) {}
}

// Reset Brand to Defaults
async function resetBrandDefaults() {
    let isConfirmed = false;
    if (typeof Swal !== 'undefined') {
        const result = await Swal.fire({
            title: 'Reset Brand Settings?',
            text: 'This will clear all your custom colors, fonts, textures, and decorations, reverting to OccaServe defaults.',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Yes, reset to defaults',
            cancelButtonText: 'Cancel',
            confirmButtonColor: '#ef4444'
        });
        isConfirmed = result.isConfirmed;
    } else {
        isConfirmed = confirm('Reset Brand Settings?\n\nThis will clear all your custom colors, fonts, textures, and decorations, reverting to OccaServe defaults.');
    }
    
    if (!isConfirmed) return;
    
    try {
        const response = await fetch('/caterer/settings/reset-brand', { method: 'POST' });
        const resJson = await response.json();
        if (resJson.status === 'success') {
            if (typeof Swal !== 'undefined') {
                Swal.fire({ title: 'Reset Successful!', text: 'Brand settings reset! Reloading page...', icon: 'success', timer: 1500, showConfirmButton: false });
            } else {
                alert('Brand settings reset! Reloading page...');
            }
            setTimeout(() => window.location.reload(), 1500);
        } else {
            if (window.showError) window.showError(resJson.message || 'Failed to reset.');
            else alert(resJson.message || 'Failed to reset.');
        }
    } catch (err) {
        console.error(err);
        if (window.showError) window.showError('An error occurred.');
        else alert('An error occurred.');
    }
}

// Submit Verification Center documents via AJAX
async function submitVerification() {
    const btn = document.getElementById('btnSubmitVerification');
    const idFront = document.getElementById('verif_id_front').files[0];
    const permit = document.getElementById('verif_permit').files[0];
    const hasId = document.querySelector('#verif_id_front').nextElementSibling?.classList.contains('field-hint');
    const hasPermit = document.querySelector('#verif_permit').nextElementSibling?.classList.contains('field-hint');

    if (!idFront && !hasId) { 
        if (typeof Swal !== 'undefined') Swal.fire({ toast: true, position: 'top-end', icon: 'warning', title: 'Government ID (Front) is required.', showConfirmButton: false, timer: 3000 });
        else alert("Government ID (Front) is required."); 
        return; 
    }
    if (!permit && !hasPermit) { 
        if (typeof Swal !== 'undefined') Swal.fire({ toast: true, position: 'top-end', icon: 'warning', title: 'Business Permit is required.', showConfirmButton: false, timer: 3000 });
        else alert("Business Permit is required."); 
        return; 
    }

    const formData = new FormData();
    formData.append('id_type', document.getElementById('verif_id_type').value);
    if (idFront) formData.append('id_front', idFront);
    const idBack = document.getElementById('verif_id_back').files[0];
    if (idBack) formData.append('id_back', idBack);
    
    // Phase 2: Attach selfie to FormData
    const selfie = document.getElementById('verif_selfie').files[0];
    if (selfie) formData.append('selfie', selfie);
    
    if (permit) formData.append('permit', permit);
    formData.append('permit_expiry', document.getElementById('verif_permit_expiry').value);
    const dti = document.getElementById('verif_dti').files[0];
    if (dti) formData.append('dti', dti);
    const bir = document.getElementById('verif_bir').files[0];
    if (bir) formData.append('bir', bir);
    const mayors = document.getElementById('verif_mayors').files[0];
    if (mayors) formData.append('mayors', mayors);

    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
    btn.disabled = true;

    try {
        const response = await fetch('/caterer/verification/submit', { method: 'POST', body: formData });
        const result = await response.json();
        if (result.success) {
            if (typeof Swal !== 'undefined') {
                Swal.fire({ toast: true, position: 'top-end', icon: 'success', title: 'Verification documents submitted!', showConfirmButton: false, timer: 3000 });
            } else {
                alert('Verification documents submitted!');
            }
            setTimeout(() => window.location.reload(), 1500);
        } else {
            if (typeof Swal !== 'undefined') {
                Swal.fire({ toast: true, position: 'top-end', icon: 'error', title: result.message || "Failed to submit documents.", showConfirmButton: false, timer: 3000 });
            } else {
                alert(result.message || "Failed to submit documents.");
            }
        }
    } catch (err) {
        console.error(err);
        if (typeof Swal !== 'undefined') {
            Swal.fire({ toast: true, position: 'top-end', icon: 'error', title: 'An unexpected error occurred.', showConfirmButton: false, timer: 3000 });
        } else {
            alert('An unexpected error occurred.');
        }
    } finally {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    }
}
