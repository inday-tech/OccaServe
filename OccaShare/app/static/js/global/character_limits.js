(function () {
    const DEFAULT_LIMIT = 300;
    const LONG_LIMITS = [
        [/businessdescription|business_description|portfolioDescriptionInput/i, 1000],
        [/package description|package_description/i, 1000],
        [/(^|\s)description(\s|$)/i, 500],
        [/revision_item_changes/i, 1000],
        [/revision_reason/i, 300],
        [/cash_instructions/i, 500],
        [/general_terms|terms_and_conditions|policies|policy/i, 5000],
        [/maintenance_message|^content$|postdescription/i, 1000]
    ];
    const shortTextPattern = /(description|desc|notes?|reason|comment|remarks?|requests?|details?|message|msg|reply|theme|highlights|caption|summary|decision)/i;
    const excludedPattern = /(terms|polic(?:y|ies)|address|venue|location|password|email|phone|reference|account|number)/i;

    function characterCount(value) {
        return Array.from(value || '').length;
    }

    function getLimit(field) {
        if (field.dataset.charLimit) return Number(field.dataset.charLimit);
        const key = `${field.name || ''} ${field.id || ''}`.trim().toLowerCase();
        const longLimit = LONG_LIMITS.find(([pattern]) => pattern.test(key));
        if (longLimit) return longLimit[1];
        if (excludedPattern.test(key)) return null;
        if (field.matches('textarea') && shortTextPattern.test(key)) return DEFAULT_LIMIT;
        if (field.matches('input[type="text"]') && shortTextPattern.test(key)) return DEFAULT_LIMIT;
        return null;
    }

    function showCounter(field) {
        if (!(field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement)) return;
        if (field.dataset.charCounterReady === 'true' || field.disabled || field.readOnly) return;
        const limit = getLimit(field);
        if (!limit || !Number.isFinite(limit)) return;

        field.dataset.charCounterReady = 'true';
        field.dataset.charLimit = String(limit);
        field.dataset.charPreviousValue = field.value;
        const counter = field.id === 'businessDescriptionInput'
            ? document.getElementById('descCharCounter')
            : null;
        const counterElement = counter || document.createElement('div');
        counterElement.classList.add('character-counter');
        counterElement.setAttribute('aria-live', 'polite');
        counterElement.id = counterElement.id || `char-counter-${Math.random().toString(36).slice(2)}`;
        if (!counter) field.insertAdjacentElement('afterend', counterElement);
        const existingDescription = field.getAttribute('aria-describedby');
        field.setAttribute('aria-describedby', [existingDescription, counterElement.id].filter(Boolean).join(' '));

        function update(message) {
            const count = characterCount(field.value);
            const overLimit = count > limit;
            counterElement.textContent = message || (overLimit
                ? `This saved value is ${count}/${limit} characters. Remove text to meet the limit.`
                : count === limit ? `Maximum reached (${count}/${limit}).` : `${count}/${limit}`);
            counterElement.classList.toggle('is-limit-reached', count >= limit);
            counterElement.classList.toggle('is-over-limit', overLimit);
            field.setAttribute('aria-invalid', overLimit ? 'true' : 'false');
        }

        field.addEventListener('beforeinput', event => {
            if (!event.inputType || !event.inputType.startsWith('insert')) return;
            const currentCount = characterCount(field.value);
            const start = field.selectionStart ?? field.value.length;
            const end = field.selectionEnd ?? start;
            const inserted = event.data || '';
            const nextCount = currentCount - characterCount(field.value.slice(start, end)) + characterCount(inserted);
            if (nextCount > limit) {
                event.preventDefault();
                update(`Maximum ${limit} characters (${currentCount}/${limit}). Remove text before adding more.`);
            }
        });

        field.addEventListener('input', () => {
            if (characterCount(field.value) > limit) {
                field.value = field.dataset.charPreviousValue || '';
                update(`Maximum ${limit} characters. Extra text was not added.`);
                return;
            }
            field.dataset.charPreviousValue = field.value;
            update();
        });

        update();
    }

    function scan(root) {
        if (root instanceof Element && root.matches('textarea, input[type="text"]')) showCounter(root);
        if (root.querySelectorAll) root.querySelectorAll('textarea, input[type="text"]').forEach(showCounter);
    }

    function start() {
        scan(document);
        new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(node => {
            if (node.nodeType === Node.ELEMENT_NODE) scan(node);
        }))).observe(document.body, { childList: true, subtree: true });
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
    else start();
})();
