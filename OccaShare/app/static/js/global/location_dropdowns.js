(function () {
    function initializeDropdown(select) {
        if (select.dataset.locationDropdownInitialized === 'true') return;

        const menu = document.createElement('div');
        menu.className = 'location-dropdown-menu';
        menu.id = `${select.id}-options`;
        menu.setAttribute('role', 'listbox');
        menu.hidden = true;
        document.body.append(menu);

        select.dataset.locationDropdownInitialized = 'true';
        select.setAttribute('aria-controls', menu.id);
        select.setAttribute('aria-expanded', 'false');

        let optionButtons = [];

        function updateOptions() {
            optionButtons.forEach(optionButton => {
                optionButton.setAttribute('aria-selected', String(optionButton.dataset.value === select.value));
            });
        }

        function renderOptions() {
            menu.replaceChildren();
            optionButtons = [];

            Array.from(select.options).forEach(option => {
                if (!option.value || option.disabled || option.hidden) return;

                const optionButton = document.createElement('button');
                optionButton.type = 'button';
                optionButton.className = 'location-dropdown-option';
                optionButton.dataset.value = option.value;
                optionButton.setAttribute('role', 'option');
                optionButton.setAttribute('aria-selected', String(option.value === select.value));
                optionButton.textContent = option.textContent.trim();
                optionButton.addEventListener('click', () => {
                    select.value = option.value;
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                    updateOptions();
                    closeMenu(true);
                });
                optionButton.addEventListener('keydown', event => {
                    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                        event.preventDefault();
                        const step = event.key === 'ArrowDown' ? 1 : -1;
                        const index = optionButtons.indexOf(optionButton);
                        optionButtons[(index + step + optionButtons.length) % optionButtons.length]?.focus();
                    } else if (event.key === 'Escape') {
                        event.preventDefault();
                        closeMenu(true);
                    } else if (event.key === 'Tab') {
                        closeMenu(false);
                    }
                });
                menu.append(optionButton);
                optionButtons.push(optionButton);
            });
            updateOptions();
        }

        function closeMenu(returnFocus) {
            menu.hidden = true;
            select.setAttribute('aria-expanded', 'false');
            if (returnFocus) select.focus();
        }

        function openMenu() {
            if (select.disabled || optionButtons.length === 0) return;

            const bounds = select.getBoundingClientRect();
            const viewportHeight = window.visualViewport?.height || window.innerHeight;
            const viewportTop = window.visualViewport?.offsetTop || 0;
            const viewportBottom = viewportTop + viewportHeight;
            const gap = 2;
            const edge = 8;
            const maxMenuHeight = viewportHeight * 0.32;
            const spaceBelow = viewportBottom - bounds.bottom - edge - gap;
            const spaceAbove = bounds.top - viewportTop - edge - gap;
            const opensUp = spaceBelow < maxMenuHeight && spaceAbove > spaceBelow;
            const availableHeight = Math.max(1, Math.min(
                maxMenuHeight,
                opensUp ? spaceAbove : spaceBelow
            ));
            const menuWidth = Math.min(bounds.width, window.innerWidth - edge * 2);

            menu.style.position = 'fixed';
            menu.style.width = `${menuWidth}px`;
            menu.style.left = `${Math.max(edge, Math.min(bounds.left, window.innerWidth - menuWidth - edge))}px`;
            menu.style.maxHeight = `${availableHeight}px`;
            menu.hidden = false;
            select.setAttribute('aria-expanded', 'true');

            const menuHeight = menu.getBoundingClientRect().height;
            menu.style.top = `${opensUp
                ? Math.max(viewportTop + edge, bounds.top - menuHeight - gap)
                : Math.min(bounds.bottom + gap, viewportBottom - menuHeight - edge)}px`;

            const selected = optionButtons.find(optionButton =>
                optionButton.getAttribute('aria-selected') === 'true'
            );
            const focusTarget = selected || optionButtons[0];
            focusTarget.focus({ preventScroll: true });
            const optionBottom = focusTarget.offsetTop + focusTarget.offsetHeight;
            if (optionBottom > menu.scrollTop + menu.clientHeight) {
                menu.scrollTop = optionBottom - menu.clientHeight;
            } else if (focusTarget.offsetTop < menu.scrollTop) {
                menu.scrollTop = focusTarget.offsetTop;
            }
        }

        select.addEventListener('mousedown', event => {
            event.preventDefault();
            select.focus();
        });
        select.addEventListener('click', event => {
            event.preventDefault();
            if (menu.hidden) openMenu();
            else closeMenu(false);
        });
        select.addEventListener('keydown', event => {
            if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(event.key)) {
                event.preventDefault();
                openMenu();
            } else if (event.key === 'Escape') {
                closeMenu(false);
            }
        });
        select.addEventListener('change', updateOptions);
        window.addEventListener('resize', () => {
            if (!menu.hidden) closeMenu(false);
        });
        window.addEventListener('scroll', event => {
            if (!menu.hidden && !(event.target instanceof Node && menu.contains(event.target))) {
                closeMenu(false);
            }
        }, true);

        new MutationObserver(renderOptions).observe(select, {
            attributes: true,
            attributeFilter: ['disabled'],
            childList: true
        });
        renderOptions();
    }

    document.addEventListener('click', event => {
        if (!(event.target instanceof Element)) return;
        document.querySelectorAll('.location-dropdown-menu:not([hidden])').forEach(menu => {
            const select = document.querySelector(`[aria-controls="${menu.id}"]`);
            if (!menu.contains(event.target) && !select?.contains(event.target)) {
                menu.hidden = true;
                select?.setAttribute('aria-expanded', 'false');
            }
        });
    });

    function initialize() {
        document.querySelectorAll('select[data-location-dropdown]').forEach(initializeDropdown);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
})();
