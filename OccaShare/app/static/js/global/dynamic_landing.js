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

    // 2. SCROLL EFFECT (Glassmorphic Header)
    window.addEventListener('scroll', () => {
        if (!navbar) return;
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // 3. AJAX CATEGORY FILTERING
    categoryLinks.forEach(link => {
        link.addEventListener('click', async (e) => {
            if (window.location.pathname !== '/' || e.ctrlKey || e.metaKey) return;
            e.preventDefault();
            
            const url = new URL(link.href);
            const type = url.searchParams.get('type');
            
            const typeSelect = document.getElementById('eventTypeSelect');
            if (typeSelect) typeSelect.value = type || '';
            
            const section = document.getElementById('caterers');
            if (section) section.scrollIntoView({ behavior: 'smooth' });
            
            await performDeepSearch();
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

    // 5. LIVE SEARCH & DEEP SEARCH
    const searchInput = document.getElementById('catererSearchInput');
    const locationInput = document.getElementById('locationSearchInput');
    const typeSelect = document.getElementById('eventTypeSelect');
    
    let searchTimeout;
    const triggerSearch = () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            performDeepSearch();
        }, 500);
    };

    if (searchInput) searchInput.addEventListener('input', triggerSearch);
    if (locationInput) locationInput.addEventListener('input', triggerSearch);
    if (typeSelect) typeSelect.addEventListener('change', performDeepSearch);

    window.performDeepSearch = async () => {
        if (!catererGrid) return;

        const q = searchInput ? searchInput.value : '';
        const loc = locationInput ? locationInput.value : '';
        const type = typeSelect ? typeSelect.value : '';

        // Show Skeleton placeholders
        catererGrid.style.opacity = '0.7';
        
        try {
            const params = new URLSearchParams({ q, location: loc, type });
            const response = await fetch(`/caterers/api/filter?${params.toString()}`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            if (!response.ok) throw new Error('Search failed');
            const html = await response.text();
            
            catererGrid.style.transition = 'opacity 0.2s ease';
            catererGrid.style.opacity = '0';
            
            setTimeout(() => {
                catererGrid.innerHTML = html;
                catererGrid.style.opacity = '1';
                
                // Refresh Scroll Animations for new results
                catererGrid.querySelectorAll('.animate-on-scroll').forEach(el => window.observer.observe(el));
            }, 200);

        } catch (err) {
            console.error('Search error:', err);
            catererGrid.style.opacity = '1';
        }
    };

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
});
