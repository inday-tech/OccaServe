/**
 * Dynamic Landing Page Controller
 * Enhances the landing page with "Web App" features
 */

document.addEventListener('DOMContentLoaded', () => {
    const navbar = document.getElementById('mainNavbar');
    const catererGrid = document.querySelector('.caterer-grid-new');
    const categoryLinks = document.querySelectorAll('.event-card');

    // 1. GLOBAL INTERSECTION OBSERVER (For Entrance Animations)
    window.observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.animate-on-scroll').forEach((el) => {
        window.observer.observe(el);
    });

    // 3. AJAX CATEGORY FILTERING (injects into unified search)
    const unifiedInput = document.getElementById('unifiedSearchInput');
    const searchLoader = document.getElementById('searchLoader');

    categoryLinks.forEach(link => {
        link.addEventListener('click', async (e) => {
            if (window.location.pathname !== '/' || e.ctrlKey || e.metaKey) return;
            e.preventDefault();

            const url = new URL(link.href);
            const type = url.searchParams.get('type');

            // Inject into unified search input
            if (unifiedInput && type) {
                unifiedInput.value = type;
                unifiedInput.focus();
            }

            const section = document.getElementById('caterers');
            if (section) section.scrollIntoView({ behavior: 'smooth' });

            await performUnifiedSearch();
        });
    });

    // 4. STATS COUNTER ANIMATION
    const statsSection = document.querySelector('.section-stats-bar');
    const statsNumbers = document.querySelectorAll('.stat-number');
    let counted = false;

    const countUp = () => {
        statsNumbers.forEach(num => {
            const target = parseInt(num.getAttribute('data-target'));
            let count = 0;
            const duration = 2000;
            const startTime = performance.now();

            const updateCount = (timestamp) => {
                const elapsed = timestamp - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const currentCount = Math.floor(progress * target);

                num.innerText = currentCount.toLocaleString() + (target > 50 && progress === 1 ? '+' : '');

                if (progress < 1) {
                    requestAnimationFrame(updateCount);
                }
            };
            requestAnimationFrame(updateCount);
        });
    };

    const statsObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && !counted) {
            countUp();
            counted = true;
        }
    }, { threshold: 0.2 });

    if (statsSection) statsObserver.observe(statsSection);

    // 5. UNIFIED LIVE SEARCH (single input, deep search)
    let searchTimeout;
    const triggerUnifiedSearch = () => {
        clearTimeout(searchTimeout);
        if (searchLoader) searchLoader.style.display = 'flex';
        // Hide hint once user starts typing
        const hint = document.querySelector('.search-hint');
        if (hint && unifiedInput && unifiedInput.value.length > 0) {
            hint.style.display = 'none';
        } else if (hint) {
            hint.style.display = '';
        }
        searchTimeout = setTimeout(() => {
            performUnifiedSearch();
        }, 350);
    };

    if (unifiedInput) unifiedInput.addEventListener('input', triggerUnifiedSearch);

    async function performUnifiedSearch() {
        if (!catererGrid) return;

        const q = unifiedInput ? unifiedInput.value.trim() : '';

        // Get user location from sessionStorage if available
        const userLat = sessionStorage.getItem('user_lat');
        const userLon = sessionStorage.getItem('user_lon');

        catererGrid.style.transition = 'opacity 0.2s ease';
        catererGrid.style.opacity = '0.5';

        try {
            const params = new URLSearchParams({ q });
            if (userLat && userLon) {
                params.append('lat', userLat);
                params.append('lon', userLon);
            }

            const response = await fetch(`/caterers/api/search?${params.toString()}`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            if (!response.ok) throw new Error('Search failed');
            const html = await response.text();

            catererGrid.style.opacity = '0';

            setTimeout(() => {
                catererGrid.innerHTML = html;
                catererGrid.style.opacity = '1';
                // Refresh scroll animations for new results
                catererGrid.querySelectorAll('.animate-on-scroll').forEach(el => window.observer.observe(el));

                // Update distance badges on newly loaded cards
                calculateDistancesOnCards();

                // If location was used, show a subtle hint
                if (userLat && userLon && !q) {
                    const header = document.querySelector('#caterers .section-header p');
                    if (header && !header.innerText.includes('near you')) {
                        header.innerHTML = '<i class="fas fa-location-dot" style="color:#f97316;"></i> Showing caterers <span style="color:#f97316; font-weight:700;">nearest to you</span> first.';
                    }
                }
            }, 200);

        } catch (err) {
            console.error('Search error:', err);
            catererGrid.style.opacity = '1';
        } finally {
            if (searchLoader) searchLoader.style.display = 'none';
        }
    }

    // Expose globally
    window.performUnifiedSearch = performUnifiedSearch;
    window.performDeepSearch = performUnifiedSearch;

    // 6. CONTACT FORM SUBMISSION (AJAX)
    window.submitContactForm = async (event) => {
        event.preventDefault();
        const form = event.target;
        const formData = new FormData(form);
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;

        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
        submitBtn.disabled = true;

        try {
            const response = await fetch('/contact/api', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'success',
                        title: 'Message Sent!',
                        text: 'Thank you for reaching out. Our team will get back to you soon.',
                        confirmButtonColor: '#f97316'
                    });
                } else {
                    alert('Message sent successfully!');
                }
                form.reset();
            } else {
                throw new Error('Failed to send message');
            }
        } catch (error) {
            console.error('Error submitting form:', error);
            if (typeof Swal !== 'undefined') {
                Swal.fire({ icon: 'error', title: 'Oops...', text: 'Something went wrong. Please try again later.' });
            } else {
                alert('Error sending message.');
            }
        } finally {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    };

    // 7. CLIENT-SIDE DISTANCE CALCULATION (fallback for static page load)
    calculateDistancesOnCards();

    // 8. AUTO-SORT on page load if location is already cached from a previous session
    const cachedLat = sessionStorage.getItem('user_lat');
    const cachedLon = sessionStorage.getItem('user_lon');
    if (cachedLat && cachedLon) {
        setLocationActiveUI();
        performUnifiedSearch();
    }

}); // END DOMContentLoaded


// ─── GEOLOCATION ──────────────────────────────────────────────────────────────

window.triggerGeolocation = function () {
    const btn = document.getElementById('locateMeBtn');
    const icon = document.getElementById('locateMeIcon');
    const label = document.getElementById('locateMeLabel');

    if (!('geolocation' in navigator)) {
        alert('Geolocation is not supported by your browser.');
        return;
    }

    // Loading state
    if (icon) icon.className = 'fas fa-spinner fa-spin';
    if (label) label.textContent = 'Locating...';
    if (btn) btn.disabled = true;

    navigator.geolocation.getCurrentPosition(function (position) {
        sessionStorage.setItem('user_lat', position.coords.latitude);
        sessionStorage.setItem('user_lon', position.coords.longitude);

        setLocationActiveUI();

        if (window.performUnifiedSearch) {
            window.performUnifiedSearch();
        }
    }, function (error) {
        // Reset button on error
        if (icon) icon.className = 'fas fa-location-crosshairs';
        if (label) label.textContent = 'Near Me';
        if (btn) btn.disabled = false;

        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'warning',
                title: 'Location Access Denied',
                text: 'Please allow location permissions to sort caterers by distance.',
                confirmButtonColor: '#f97316'
            });
        } else {
            alert('Location Access Denied. Please allow location permissions to find nearby caterers.');
        }
    }, { timeout: 10000 });
};

function setLocationActiveUI() {
    const btn = document.getElementById('locateMeBtn');
    const icon = document.getElementById('locateMeIcon');
    const label = document.getElementById('locateMeLabel');
    const badge = document.getElementById('locationStatusBadge');

    if (btn) {
        btn.style.background = '#16a34a';
        btn.style.boxShadow = '0 3px 12px rgba(22,163,74,0.3)';
        btn.disabled = false;
    }
    if (icon) icon.className = 'fas fa-circle-check';
    if (label) label.textContent = 'Nearby';
    if (badge) badge.style.display = 'block';
}

window.clearUserLocation = function () {
    sessionStorage.removeItem('user_lat');
    sessionStorage.removeItem('user_lon');

    const btn = document.getElementById('locateMeBtn');
    const icon = document.getElementById('locateMeIcon');
    const label = document.getElementById('locateMeLabel');
    const badge = document.getElementById('locationStatusBadge');

    if (btn) {
        btn.style.background = 'var(--lp-primary, #f97316)';
        btn.style.boxShadow = '0 3px 12px rgba(249,115,22,0.3)';
        btn.disabled = false;
    }
    if (icon) icon.className = 'fas fa-location-crosshairs';
    if (label) label.textContent = 'Near Me';
    if (badge) badge.style.display = 'none';

    // Reset the section header back to default
    const header = document.querySelector('#caterers .section-header p');
    if (header) header.innerHTML = 'Discover handpicked catering professionals trusted by hundreds of clients.';

    // Re-fetch sorted by rating (default)
    if (window.performUnifiedSearch) window.performUnifiedSearch();
};

// Haversine client-side distance calculation (fills in badges if backend didn't compute them)
function calculateDistancesOnCards() {
    const userLat = sessionStorage.getItem('user_lat');
    const userLon = sessionStorage.getItem('user_lon');
    if (!userLat || !userLon) return;

    document.querySelectorAll('.dist-display').forEach(el => {
        const lat = parseFloat(el.getAttribute('data-lat'));
        const lon = parseFloat(el.getAttribute('data-lon'));
        if (!lat || !lon) return;

        const R = 6371;
        const dLat = (lat - parseFloat(userLat)) * Math.PI / 180;
        const dLon = (lon - parseFloat(userLon)) * Math.PI / 180;
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(parseFloat(userLat) * Math.PI / 180) * Math.cos(lat * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const d = (R * c).toFixed(1);

        const distText = el.querySelector('.dist-text');
        if (distText) {
            distText.innerText = d + ' km away';
            el.style.display = 'flex';
        }
    });
}
