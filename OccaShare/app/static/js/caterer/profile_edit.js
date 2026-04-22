/**
 * Caterer Profile Edit JavaScript
 * Handles tab switching and gallery management
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Tab Switching Logic
    const tabSelectors = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabSelectors.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            // Remove active classes
            tabSelectors.forEach(s => s.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Add active classes to target
            btn.classList.add('active');
            const targetContent = document.getElementById(targetTab);
            if (targetContent) {
                targetContent.classList.add('active');
            }

            // Re-render any charts or specialized components if needed
            window.dispatchEvent(new Event('resize'));
        });
    });

    // 2. Color Input Syncing (Visual feedback)
    const colorInputs = document.querySelectorAll('input[type="color"]');
    colorInputs.forEach(input => {
        input.addEventListener('input', () => {
            const codeTag = input.nextElementSibling;
            if (codeTag && codeTag.tagName === 'CODE') {
                codeTag.textContent = input.value.toUpperCase();
            }
        });
    });

    // 3. Real-time Payment Field Validation (Mobile Wallets & Banks)
    const mobileWalletInputs = [
        document.querySelector('input[name="gcash_number"]'),
        document.querySelector('input[name="maya_number"]')
    ];

    // Helper function to show/hide error message and red border
    function toggleError(inputElement, showError, message) {
        let errorEl = inputElement.nextElementSibling;

        // If error element doesn't exist yet, create it
        if (!errorEl || !errorEl.classList.contains('validation-error-text')) {
            errorEl = document.createElement('div');
            errorEl.className = 'validation-error-text';
            inputElement.parentNode.insertBefore(errorEl, inputElement.nextSibling);
        }

        if (showError) {
            inputElement.classList.add('input-error');
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        } else {
            inputElement.classList.remove('input-error');
            errorEl.style.display = 'none';
        }
    }


window.openPasswordModal = function() {
    const modal = document.getElementById('passwordModal');
    if (modal) {
        modal.style.display = 'flex';
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                modal.classList.add('active');
            });
        });
    }
    document.body.style.overflow = 'hidden';
}

window.closePasswordModal = function() {
    const modal = document.getElementById('passwordModal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => {
            if (!modal.classList.contains('active')) {
                modal.style.display = 'none';
            }
        }, 400);
    }
    document.body.style.overflow = 'auto';
    const form = document.getElementById('changePasswordForm');
    if (form) form.reset();
}

    mobileWalletInputs.forEach(input => {
        if (input) {
            input.addEventListener('input', (e) => {
                let val = e.target.value.replace(/\D/g, '');
                if (val.length > 11) val = val.slice(0, 11);
                e.target.value = val;

                if (val.length > 0) {
                    if (!val.startsWith('09') && !val.startsWith('639')) {
                        toggleError(input, true, "Number must start with 09");
                    } else if (val.length < 11) {
                        toggleError(input, true, "Number must be exactly 11 digits");
                    } else {
                        toggleError(input, false, "");
                    }
                } else {
                    toggleError(input, false, "");
                }
            });
            input.addEventListener('blur', (e) => {
                let val = e.target.value;
                if (val.length > 0 && (val.length !== 11 || (!val.startsWith('09') && !val.startsWith('639')))) {
                    toggleError(input, true, "Invalid mobile number format.");
                }
            });
        }
    });

    const bankInput = document.querySelector('input[name="bank_account_number"]');
    if (bankInput) {
        bankInput.addEventListener('input', (e) => {
            let val = e.target.value;
            // Immediately show error if letters/symbols are typed
            if (/[^\d]/.test(val)) {
                toggleError(bankInput, true, "Bank accounts must contain numbers only.");
            } else {
                toggleError(bankInput, false, "");
            }
            // Still enforce cleaning
            val = val.replace(/\D/g, '');
            if (val.length > 20) val = val.slice(0, 20);
            e.target.value = val;
        });
    }

    // Assistant function to detect keyboard smashing or non-words
    function isGibberish(text) {
        if (!text) return false;
        if (text.length < 2 && text.length > 0) return "Must be at least 2 characters.";

        // No word can be over 18 characters without spaces (except some very rare edge cases)
        const words = text.split(' ');
        for (let w of words) {
            if (w.length > 18) return "Words cannot exceed 18 letters without a space.";
        }

        // 5 or more identical letters in sequence
        if (/([A-Za-z0-9])\1{4,}/.test(text)) return "Please enter a valid real name (too many identical characters).";

        // 6 or more consonants in a row (excluding 'y' as it acts as a vowel)
        if (/[bcdfghjklmnpqrstvwxz]{6,}/i.test(text)) return "Please enter a valid real name (too many consonants).";

        // Common keyboard smashes
        const smashes = ['asdf', 'fdsa', 'qwer', 'rewq', 'zxcv', 'vcxz', 'hjkl', 'lkjh'];
        for (let s of smashes) {
            if (text.toLowerCase().includes(s)) return "Please enter a valid real name (keyboard smash detected).";
        }

        return false;
    }

    const bankNameInput = document.querySelector('input[name="bank_account_name"]');
    if (bankNameInput) {
        bankNameInput.addEventListener('input', (e) => {
            let val = e.target.value;
            let errorMessage = "";
            let gibberishError = isGibberish(val);

            // Allow letters, spaces, dots, commas, hyphens. Block others.
            if (/[^A-Za-zñÑ\s\.\,\-]/.test(val)) {
                errorMessage = "Account Name can only contain letters, spaces, and basic punctuation (.,-)";
            } else if (gibberishError) {
                errorMessage = gibberishError;
            }

            if (errorMessage) {
                toggleError(bankNameInput, true, errorMessage);
            } else {
                toggleError(bankNameInput, false, "");
            }

            e.target.value = val.replace(/[^A-Za-zñÑ\s\.\,\-]/g, '');
        });
    }

    const bankInstInput = document.querySelector('input[name="bank_name"]');
    if (bankInstInput) {
        bankInstInput.addEventListener('input', (e) => {
            let val = e.target.value;
            let errorMessage = "";
            let gibberishError = isGibberish(val);

            // Allow letters, numbers, spaces, dots, commas, hyphens, ampersands. Block others.
            if (/[^A-Za-z0-9\s\.\,\-\&]/.test(val)) {
                errorMessage = "Bank Name can only contain letters, numbers, spaces, and basic punctuation (.,-&)";
            } else if (gibberishError) {
                errorMessage = gibberishError;
            }

            if (errorMessage) {
                toggleError(bankInstInput, true, errorMessage);
            } else {
                toggleError(bankInstInput, false, "");
            }

            e.target.value = val.replace(/[^A-Za-z0-9\s\.\,\-\&]/g, '');
        });
    }

    // 4. Magic Color Extraction from Logo
    const logoInput = document.getElementById('logoInput');
    const magicBtn = document.getElementById('magicExtractBtn');

    if (magicBtn && logoInput) {
        magicBtn.addEventListener('click', () => {
            if (logoInput.files && logoInput.files[0]) {
                extractColors(logoInput.files[0]);
            } else {
                window.showError("Please select a logo file first.");
            }
        });
    }

    async function extractColors(file) {
        magicBtn.classList.add('processing');
        magicBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';

        try {
            let bitmap;
            // Cross-browser: createImageBitmap is not supported in older Safari (<15)
            if (window.createImageBitmap) {
                bitmap = await createImageBitmap(file);
            } else {
                // Fallback: Use standard Image load
                bitmap = await new Promise((resolve, reject) => {
                    const img = new Image();
                    img.onload = () => resolve(img);
                    img.onerror = reject;
                    img.src = URL.createObjectURL(file);
                });
            }

            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            // Resize for faster processing
            const maxDim = 150; 
            let width = bitmap.width || bitmap.naturalWidth;
            let height = bitmap.height || bitmap.naturalHeight;
            if (width > height) {
                if (width > maxDim) {
                    height = Math.round(height * maxDim / width);
                    width = maxDim;
                }
            } else {
                if (height > maxDim) {
                    width = Math.round(width * maxDim / height);
                    height = maxDim;
                }
            }

            canvas.width = width;
            canvas.height = height;
            ctx.drawImage(bitmap, 0, 0, width, height);

            // Cleanup object URL if fallback was used
            if (!window.createImageBitmap && bitmap.src) {
                URL.revokeObjectURL(bitmap.src);
            }

            const imageData = ctx.getImageData(0, 0, width, height).data;
            const colorCounts = {};
            
            // Sample pixels
            for (let i = 0; i < imageData.length; i += 4) {
                const r = imageData[i];
                const g = imageData[i + 1];
                const b = imageData[i + 2];
                const a = imageData[i + 3];

                // Skip transparent or near-white/near-black pixels
                if (a < 128) continue;
                const brightness = (r + g + b) / 3;
                if (brightness > 245 || brightness < 10) continue;

                // Simple quantization to reduce similar colors
                const q = 24; // Finer quantization
                const qr = Math.round(r / q) * q;
                const qg = Math.round(g / q) * q;
                const qb = Math.round(b / q) * q;
                const key = `${qr},${qg},${qb}`;
                colorCounts[key] = (colorCounts[key] || 0) + 1;
            }

            // Sort by frequency
            const sortedColors = Object.entries(colorCounts)
                .map(([rgbStr, count]) => {
                    const rgb = rgbStr.split(',').map(Number);
                    const hex = rgbToHex(rgb[0], rgb[1], rgb[2]);
                    const hsv = rgbToHsv(rgb[0], rgb[1], rgb[2]);
                    return { hex, count, ...hsv };
                })
                .sort((a, b) => b.count - a.count);
            
            if (sortedColors.length > 0) {
                // Analysis logic:
                // Primary: The most dominant non-neutral color.
                // Secondary: The next dominant color that's distinct from Primary.
                // Accent: The most saturated color among top candidates.
                // Highlight: A distinct, vibrant color (usually high saturation, different hue).

                const primary = sortedColors[0].hex;
                
                // Find Secondary (distinct from primary by hue or significant saturation)
                let secondaryCandidate = sortedColors.find(c => 
                    Math.abs(c.h - sortedColors[0].h) > 0.1 || Math.abs(c.s - sortedColors[0].s) > 0.3
                );
                const secondary = secondaryCandidate ? secondaryCandidate.hex : primary;

                // Highlight/Accent: Find most saturated colors
                const bySaturation = [...sortedColors].slice(0, 10).sort((a, b) => b.s - a.s);
                const accent = bySaturation[0].hex;
                const highlight = bySaturation[1] ? bySaturation[1].hex : (bySaturation[0] ? bySaturation[0].hex : primary);

                applyPalette({
                    primary: primary,
                    secondary: secondary,
                    accent: accent,
                    highlight: highlight
                });
            }

        } catch (err) {
            console.error("Color extraction failed:", err);
            window.showError("Could not extract colors from this image. Please try another one.");
        } finally {
            magicBtn.classList.remove('processing');
            magicBtn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i> Analyze Colors';
        }
    }

    // Helper: RGB to HSV for better color analysis
    function rgbToHsv(r, g, b) {
        r /= 255, g /= 255, b /= 255;
        const max = Math.max(r, g, b), min = Math.min(r, g, b);
        let h, s, v = max;
        const d = max - min;
        s = max === 0 ? 0 : d / max;
        if (max === min) {
            h = 0;
        } else {
            switch (max) {
                case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                case g: h = (b - r) / d + 2; break;
                case b: h = (r - g) / d + 4; break;
            }
            h /= 6;
        }
        return { h, s, v };
    }

    function rgbToHex(r, g, b) {
        return "#" + [r, g, b].map(x => {
            const hex = x.toString(16);
            return hex.length === 1 ? "0" + hex : hex;
        }).join("").toUpperCase();
    }

    // 4. Branding Advanced Interactivity
    const fontSelect = document.querySelector('select[name="font_family"]');
    const radiusInput = document.querySelector('input[name="border_radius"]');
    const sidebarToggles = document.querySelectorAll('input[name="sidebar_mode"]');
    const platformLogoCheck = document.getElementById('showPlatformLogo');
    const presetItems = document.querySelectorAll('.preset-item');

    // Preset Palettes
    presetItems.forEach(item => {
        item.addEventListener('click', () => {
            const palette = {
                primary: item.getAttribute('data-primary'),
                secondary: item.getAttribute('data-secondary'),
                accent: item.getAttribute('data-accent'),
                highlight: item.getAttribute('data-highlight')
            };
            applyPalette(palette);
        });
    });

    // Font Family Updates
    if (fontSelect) {
        fontSelect.addEventListener('change', () => {
            updateMockup();
        });
    }

    // Border Radius Updates
    if (radiusInput) {
        radiusInput.addEventListener('input', (e) => {
            // Update the label text in the label itself if we wanted, but let's just update mockup
            const parentLabel = radiusInput.previousElementSibling;
            if (parentLabel) {
                parentLabel.textContent = `Interface Roundness (${e.target.value}px)`;
            }
            updateMockup();
        });
    }

    // Sidebar Mode Updates
    sidebarToggles.forEach(toggle => {
        toggle.addEventListener('change', () => {
            updateMockup();
        });
    });

    // Platform Logo Visibility
    if (platformLogoCheck) {
        platformLogoCheck.addEventListener('change', () => {
            updateMockup();
        });
    }

    function applyPalette(palette) {
        const pInput = document.querySelector('input[name="primary_color"]');
        const sInput = document.querySelector('input[name="secondary_color"]');
        const aInput = document.querySelector('input[name="accent_color"]');
        const hInput = document.querySelector('input[name="highlight_color"]');

        if (pInput) { pInput.value = palette.primary; pInput.dispatchEvent(new Event('input')); }
        if (sInput) { sInput.value = palette.secondary; sInput.dispatchEvent(new Event('input')); }
        if (aInput) { aInput.value = palette.accent; aInput.dispatchEvent(new Event('input')); }
        if (hInput) { hInput.value = palette.highlight; hInput.dispatchEvent(new Event('input')); }

        // Preview in UI instantly
        document.documentElement.style.setProperty('--primary-color', palette.primary);
        document.documentElement.style.setProperty('--accent-color', palette.accent);
        document.documentElement.style.setProperty('--highlight-color', palette.highlight);
        
        updateMockup();
        
        // Success feedback if it was from magic button, but let's keep it simple
    }

    function updateMockup() {
        const palette = {
            primary: document.querySelector('input[name="primary_color"]')?.value || '#FF7B54',
            secondary: document.querySelector('input[name="secondary_color"]')?.value || '#2D4059',
            accent: document.querySelector('input[name="accent_color"]')?.value || '#FFB26B',
            highlight: document.querySelector('input[name="highlight_color"]')?.value || '#48BB78'
        };

        const mockBody = document.querySelector('.preview-mockup-pro');
        const mockSidebar = document.querySelector('.mock-sidebar');
        const mockItemActive = document.querySelector('.mock-menu-item.active');
        const mockButton = document.querySelector('.mock-btn-pro');
        const mockTag = document.querySelector('.mock-tag-pro');
        const mockLogo = document.querySelector('.mock-logo');

        // Styles
        if (mockSidebar) mockSidebar.style.backgroundColor = palette.secondary;
        if (mockItemActive) mockItemActive.style.backgroundColor = palette.primary;
        if (mockButton) mockButton.style.backgroundColor = palette.primary;
        if (mockTag) mockTag.style.backgroundColor = palette.highlight;
        if (mockLogo) mockLogo.style.border = `2px solid ${palette.highlight}`;

        // Focus text on Catering
        if (mockButton) mockButton.innerText = "Catering Actions";
        if (mockTag) mockTag.innerText = "Verified Caterer";

        // Font
        const selectedFont = fontSelect ? fontSelect.value : 'Inter';
        if (mockBody) mockBody.style.fontFamily = selectedFont;

        // Radius
        const radius = radiusInput ? radiusInput.value : 12;
        document.documentElement.style.setProperty('--preview-radius', `${radius / 2}px`); // Scaled for mockup

        // Sidebar Mode
        const mode = document.querySelector('input[name="sidebar_mode"]:checked')?.value || 'full';
        if (mockSidebar) {
            mockSidebar.style.width = mode === 'icons' ? '25px' : '45px';
        }

        // Platform Logo
        const showLogo = platformLogoCheck ? platformLogoCheck.checked : true;
    }

    // Connect manual color changes
    const colorInputsForMock = document.querySelectorAll('input[type="color"]');
    colorInputsForMock.forEach(input => {
        input.addEventListener('input', () => {
            updateMockup();
        });
    });

    // Logo image preview in mockup
    if (logoInput) {
        logoInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const mockLogo = document.querySelector('.mock-logo');
                    if (mockLogo) {
                        mockLogo.style.backgroundImage = `url(${e.target.result})`;
                        mockLogo.style.backgroundSize = 'cover';
                        mockLogo.style.backgroundPosition = 'center';
                        mockLogo.style.backgroundColor = 'transparent';
                    }
                };
                reader.readAsDataURL(this.files[0]);
            }
        });
    }

    // Prevent form submission if there are validation errors
    const profileForm = document.querySelector('.profile-edit-form');
    if (profileForm) {
        profileForm.addEventListener('submit', function (e) {
            const errors = document.querySelectorAll('.input-error');
            if (errors.length > 0) {
                e.preventDefault();
                window.showError("Please correct the highlighted errors in your payment details before saving.");

                // Automatically switch to the Payments tab so the user sees the error
                const paymentsTabBtn = document.querySelector('.tab-btn[data-tab="payments"]');
                if (paymentsTabBtn) paymentsTabBtn.click();

                errors[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            // Re-validate everything just before submit to ensure they didn't bypass by not blurring
            const bankName = bankInstInput ? bankInstInput.value : "";
            const accountName = bankNameInput ? bankNameInput.value : "";

            let gError1 = isGibberish(bankName);
            let gError2 = isGibberish(accountName);

            if (gError1 || gError2) {
                e.preventDefault();
                window.showError(gError1 || gError2);
                if (paymentsTabBtn) paymentsTabBtn.click();
            }
        });
    }
});

/**
 * Archives a gallery item
 * @param {number} itemId 
 */
async function archiveGalleryItem(itemId) {
    window.showConfirm('Are you sure you want to archive this photo? It will be moved to your archives.', async () => {
        try {
            const response = await fetch(`/caterer/gallery/${itemId}/archive`, {
                method: 'POST',
            });

            if (response.ok) {
                // Remove the element from DOM
                const btn = document.querySelector(`button[onclick="archiveGalleryItem(${itemId})"]`);
                if (btn) {
                    const itemWrapper = btn.closest('.gallery-item-wrapper');
                    if (itemWrapper) {
                        itemWrapper.style.opacity = '0';
                        itemWrapper.style.transform = 'scale(0.8)';
                        setTimeout(() => itemWrapper.remove(), 300);
                    }
                }
                window.showSuccess('Gallery item archived successfully');
            } else {
                const data = await response.json();
                window.showError(data.detail || 'Failed to archive item');
            }
        } catch (error) {
            console.error('Error archiving gallery item:', error);
            window.showError('An error occurred while archiving the item.');
        }
    }, "Archive Photo?", "Yes, Archive");
}
