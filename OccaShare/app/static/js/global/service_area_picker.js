(function () {
    function initializePicker(picker) {
        const valueInput = picker.querySelector('input[type="hidden"][name="coverage_area"]');
        const trigger = picker.querySelector('.service-area-trigger');
        const triggerLabel = picker.querySelector('.service-area-trigger-label');
        const menu = picker.querySelector('.service-area-menu');
        const options = picker.querySelector('.service-area-options');
        const selectedList = picker.querySelector('.service-area-selected');
        const compact = picker.dataset.compact === 'true';
        if (!valueInput || !trigger || !triggerLabel || !menu || !options || (!compact && !selectedList)) return;

        const locations = window.LOCATION_DATA;
        if (!locations || typeof locations !== 'object') {
            console.error('Service-area picker could not load location options.');
            trigger.disabled = true;
            triggerLabel.textContent = 'Service area options are unavailable';
            return;
        }

        const selected = new Set(
            valueInput.value.split(',').map(value => value.trim()).filter(Boolean)
        );
        const buttonByValue = new Map();

        function updatePicker(userInitiated = false) {
            if (userInitiated) valueInput.classList.add('touched');
            valueInput.value = Array.from(selected).join(', ');
            picker.classList.toggle('has-selection', selected.size > 0);
            if (selectedList) selectedList.replaceChildren();

            if (!compact && selectedList) {
                selected.forEach(value => {
                    const chip = document.createElement('span');
                    chip.className = 'service-area-chip';
                    chip.append(document.createTextNode(value));

                    const remove = document.createElement('button');
                    remove.type = 'button';
                    remove.className = 'service-area-chip-remove';
                    remove.setAttribute('aria-label', `Remove ${value}`);
                    remove.textContent = '\u00d7';
                    remove.addEventListener('click', () => {
                        selected.delete(value);
                        const button = buttonByValue.get(value);
                        if (button) button.setAttribute('aria-pressed', 'false');
                        updatePicker(true);
                    });

                    chip.append(remove);
                    selectedList.append(chip);
                });
            }

            triggerLabel.textContent = selected.size === 0
                ? 'Choose one or more provinces'
                : compact
                    ? `${selected.size} service area${selected.size === 1 ? '' : 's'} selected`
                    : Array.from(selected).join(', ');
            trigger.setAttribute(
                'aria-label',
                selected.size ? `Selected service areas: ${Array.from(selected).join(', ')}` : 'Choose one or more provinces'
            );
            const errorWrapper = document.getElementById('coverageAreaCatWrapper');
            if (window.setDiamondError && (selected.size > 0
                || valueInput.classList.contains('touched')
                || errorWrapper?.classList.contains('error'))) {
                window.setDiamondError(
                    'coverageAreaCat',
                    selected.size ? '' : 'Select at least one service area.',
                    selected.size === 0
                );
            }
            if (userInitiated) {
                valueInput.dispatchEvent(new Event('input', { bubbles: true }));
                valueInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }

        function addChoice(parent, value, label) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'service-area-option';
            button.setAttribute('aria-pressed', String(selected.has(value)));
            button.textContent = label;
            button.addEventListener('click', () => {
                if (selected.has(value)) selected.delete(value);
                else selected.add(value);
                button.setAttribute('aria-pressed', String(selected.has(value)));
                updatePicker(true);
            });
            parent.append(button);
            buttonByValue.set(value, button);
        }

        Object.entries(locations)
            .sort(([left], [right]) => left.localeCompare(right))
            .forEach(([province]) => {
                addChoice(options, province, province);
            });

        trigger.addEventListener('click', () => {
            const isOpen = !menu.hidden;
            menu.hidden = isOpen;
            trigger.setAttribute('aria-expanded', String(!isOpen));
            if (!isOpen) {
                const triggerBounds = trigger.getBoundingClientRect();
                const spaceBelow = window.innerHeight - triggerBounds.bottom;
                menu.classList.toggle('opens-up', spaceBelow < 240 && triggerBounds.top > 240);
                options.querySelector('.service-area-option')?.focus();
            }
        });
        document.addEventListener('click', event => {
            if (!picker.contains(event.target)) {
                menu.hidden = true;
                trigger.setAttribute('aria-expanded', 'false');
                menu.classList.remove('opens-up');
            }
        });

        updatePicker();
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('[data-service-area-picker]').forEach(initializePicker);
    });
})();
