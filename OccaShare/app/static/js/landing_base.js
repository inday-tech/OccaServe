document.addEventListener('DOMContentLoaded', function () {
    (function () {
        /* ============================================================
           NAV ACTIVE-LINK HIGHLIGHTING
           Strategy:
             - On the home page (data-nav-page="home"): use IntersectionObserver
               to watch sections and highlight matching nav links.
             - On every other page: match body[data-nav-page] to nav links
               with matching [data-nav] attribute.
             - On login page ("login"): highlight #navLoginBtn with active-page class.
             - On register page ("register"): highlight #navSignupBtn with active-page class.
        ============================================================ */

        const NAV_PAGE = document.body.dataset.navPage || '';
        const navLinks = document.querySelectorAll('.nav-links a');
        const loginBtn = document.getElementById('navLoginBtn');
        const signupBtn = document.getElementById('navSignupBtn');

        function clearActive() {
            navLinks.forEach(a => a.classList.remove('active'));
            if (loginBtn) loginBtn.classList.remove('active-page');
            if (signupBtn) signupBtn.classList.remove('active-page');
        }

        function setActive(navValue) {
            clearActive();
            navLinks.forEach(a => {
                if (a.dataset.nav === navValue) a.classList.add('active');
            });
        }

        /* ---- HOME PAGE: Scrollspy implementation ---- */
        if (NAV_PAGE === 'home' || NAV_PAGE === '') {
            const sections = document.querySelectorAll("section[id], header[id]");
            
            window.addEventListener("scroll", () => {
                let current = "";
                
                sections.forEach(section => {
                    const sectionTop = section.offsetTop;
                    const sectionHeight = section.clientHeight;
                    // Trigger the nav highlight when the section is at the top 1/3rd of the viewport
                    if (window.scrollY >= sectionTop - (window.innerHeight / 3)) {
                        current = section.getAttribute("id");
                    }
                });

                if (window.scrollY < 100) {
                    current = "home";
                }

                clearActive();
                navLinks.forEach(link => {
                    const navMatch = link.getAttribute("data-nav");
                    if (navMatch === current) {
                        link.classList.add("active");
                    }
                });
            });

            // Trigger scroll event on load to set initial state
            window.dispatchEvent(new Event("scroll"));
        }
        else if (NAV_PAGE === 'login') {
            clearActive();
            if (loginBtn) loginBtn.classList.add('active-page');
        }

        /* ---- AUTH BUTTON HIGHLIGHT: Register page ---- */
        else if (NAV_PAGE === 'register') {
            clearActive();
            if (signupBtn) signupBtn.classList.add('active-page');
        }

        /* ---- ALL OTHER PAGES: match data-nav attribute ---- */
        else {
            if (NAV_PAGE) {
                setActive(NAV_PAGE);
            } else {
                // If no nav_page is defined, default highlight to Home
                setActive('home');
            }
        }

        /* ---- MOBILE HAMBURGER ---- */
        const hamburger = document.querySelector('.hamburger');
        const navMenu = document.querySelector('.nav-menu');
        if (hamburger && navMenu) {
            console.log("Hamburger initialized");
            hamburger.addEventListener('click', (e) => {
                e.preventDefault();
                console.log("Hamburger clicked");
                hamburger.classList.toggle('active');
                navMenu.classList.toggle('active');
            });
            document.querySelectorAll('.nav-links a').forEach(link => {
                link.addEventListener('click', () => {
                    hamburger.classList.remove('active');
                    navMenu.classList.remove('active');
                });
            });
        }

        /* ---- NAVBAR SCROLL SHRINK ---- */
        const navbar = document.getElementById('mainNavbar');
        if (navbar) {
            window.addEventListener('scroll', () => {
                navbar.style.boxShadow = window.scrollY > 40
                    ? '0 2px 20px rgba(0,0,0,0.12)'
                    : '';
            }, { passive: true });
        }
    })();
});
