/**
 * Admin Verification Detail - Diamond Standard Terminal
 * Cinematic Reveals | Scanning Logic | Advanced Comparison
 */

document.addEventListener('DOMContentLoaded', () => {
    initCinematicReveals();
    startScanningSequence();
    initQuickDecisions();
    initImageControls();
    initBiometricTerminal();
});

/**
 * Cinematic Staggered Reveals
 */
function initCinematicReveals() {
    const cards = document.querySelectorAll('.reveal-card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('revealed');
        }, index * 150);
    });
}

/**
 * Living AI Scanning Sequence
 */
function startScanningSequence() {
    const boxes = document.querySelectorAll('.img-preview-box');
    const gauge = document.querySelector('.gauge-fill');
    const syncIndicators = document.querySelectorAll('.live-sync-indicator');

    // Start scan animation
    boxes.forEach(box => {
        box.classList.add('scanning');
        const scanLine = box.querySelector('.scan-line');
        if (scanLine) scanLine.style.display = 'block';
    });

    // Simulating biometric analysis stages
    setTimeout(() => {
        animateMatchGauge(gauge);
    }, 1200);

    setTimeout(() => {
        boxes.forEach(box => {
            box.classList.remove('scanning');
            const scanLine = box.querySelector('.scan-line');
            if (scanLine) scanLine.style.opacity = '0';
        });

        // Show success pulse on sync indicators
        syncIndicators.forEach(indicator => {
            indicator.style.background = 'rgba(16, 185, 129, 0.15)';
            indicator.style.transition = 'background 0.5s ease';
        });
    }, 3000);
}

function animateMatchGauge(gauge) {
    if (!gauge) return;

    const score = parseInt(gauge.dataset.score) || 0;
    const radius = 35;
    const circumference = 2 * Math.PI * radius;

    gauge.style.strokeDasharray = circumference;
    const offset = circumference - (score / 100) * circumference;

    // Use a more dynamic easing
    gauge.style.transition = 'stroke-dashoffset 2s cubic-bezier(0.34, 1.56, 0.64, 1)';
    gauge.style.strokeDashoffset = offset;
}

/**
 * Image Controls & Controls
 */
function initImageControls() {
    const previewBoxes = document.querySelectorAll('.img-preview-box');

    previewBoxes.forEach(box => {
        const img = box.querySelector('img');
        const brightBtn = box.querySelector('.btn-bright');

        if (img && brightBtn) {
            let brightness = 100;
            brightBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                brightness = brightness >= 200 ? 100 : brightness + 50;
                img.style.filter = `brightness(${brightness}%)`;
                brightBtn.classList.toggle('active', brightness > 100);
            });
        }

        box.addEventListener('mousemove', (e) => {
            if (document.body.classList.contains('compare-terminal-active')) return;
            const rect = box.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            img.style.transformOrigin = `${x}% ${y}%`;
            img.style.transform = 'scale(2)';
        });

        box.addEventListener('mouseleave', () => {
            img.style.transform = 'scale(1)';
        });
    });
}

/**
 * Advanced Biometric Terminal Logic
 */
function initBiometricTerminal() {
    const launchBtn = document.getElementById('launch-compare-btn');
    const closeBtn = document.querySelector('.btn-close-terminal');
    const terminal = document.getElementById('biometric-terminal');
    const viewport = document.getElementById('terminal-viewport');

    // Controls
    const opacitySlider = document.getElementById('opacity-slider');
    const scaleSlider = document.getElementById('scale-slider');
    const toggleLayoutBtn = document.getElementById('btn-toggle-layout');
    const resetBtn = document.getElementById('btn-reset-terminal');

    // Images
    const idImg = document.getElementById('terminal-id-img');
    const selfieImg = document.getElementById('terminal-selfie-img');
    const selfieView = document.querySelector('.selfie-view');

    if (!launchBtn || !terminal) return;

    const openTerminal = () => {
        document.body.classList.add('compare-terminal-active');
        terminal.style.display = 'flex';
        // Reset to side-by-side on open
        viewport.className = 'terminal-viewport side-by-side';
        resetTerminal();
    };

    const closeTerminal = () => {
        document.body.classList.remove('compare-terminal-active');
        terminal.style.display = 'none';
    };

    const resetTerminal = () => {
        opacitySlider.value = 0;
        scaleSlider.value = 100;
        selfieView.style.opacity = '1';
        idImg.style.transform = 'scale(1)';
        selfieImg.style.transform = 'scale(1)';
        if (viewport.classList.contains('overlay-mode')) {
            selfieView.style.opacity = '0.5';
        }
    };

    launchBtn.addEventListener('click', openTerminal);
    closeBtn.addEventListener('click', closeTerminal);

    // Opacity Logic (Only for Overlay Mode)
    opacitySlider.addEventListener('input', (e) => {
        if (viewport.classList.contains('overlay-mode')) {
            selfieView.style.opacity = e.target.value / 100;
        }
    });

    // Scale Logic
    scaleSlider.addEventListener('input', (e) => {
        const scale = e.target.value / 100;
        idImg.style.transform = `scale(${scale})`;
        selfieImg.style.transform = `scale(${scale})`;
    });

    // Layout Toggle
    toggleLayoutBtn.addEventListener('click', () => {
        const isOverlay = viewport.classList.toggle('overlay-mode');
        viewport.classList.toggle('side-by-side', !isOverlay);

        if (isOverlay) {
            selfieView.style.opacity = '0.5';
            opacitySlider.value = 50;
            toggleLayoutBtn.innerHTML = '<i class="fas fa-columns"></i> SIDE-BY-SIDE';
        } else {
            selfieView.style.opacity = '1';
            opacitySlider.value = 100;
            toggleLayoutBtn.innerHTML = '<i class="fas fa-layer-group"></i> OVERLAY MODE';
        }
    });

    resetBtn.addEventListener('click', resetTerminal);

    // Keyboard ESC to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeTerminal();
    });
}

/**
 * Quick Decision Automation
 */
function initQuickDecisions() {
    const area = document.querySelector('.decision-automation-area');
    const notes = document.querySelector('textarea[name="notes"]');

    if (!area || !notes) return;

    area.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-template');
        if (!btn) return;

        const template = btn.dataset.template;
        notes.value = template;

        btn.classList.add('pulse-once');
        setTimeout(() => btn.classList.remove('pulse-once'), 500);
        notes.focus();
    });
}
