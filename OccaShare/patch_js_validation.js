import fs from 'fs';

const filePath = 'C:\\OccaServe\\OccaShare\\app\\static\\js\\customer\\alacarte_checkout.js';
let content = fs.readFileSync(filePath, 'utf8');

const validationCode = `
// Universal Scheduling Validation
function validateSchedulingRules() {
    if (!window.catererRules) return true;
    
    let isValid = true;
    const rules = window.catererRules;
    
    // Clear previous errors
    document.querySelectorAll('.schedule-rule-error').forEach(e => e.remove());
    
    const showError = (inputId, message) => {
        const input = document.getElementById(inputId);
        if (input) {
            input.style.borderColor = '#ef4444';
            const err = document.createElement('div');
            err.className = 'schedule-rule-error field-error show';
            err.style.color = '#ef4444';
            err.style.fontSize = '0.75rem';
            err.style.marginTop = '4px';
            err.innerText = message;
            input.parentNode.appendChild(err);
            isValid = false;
        }
    };
    
    const resetError = (inputId) => {
        const input = document.getElementById(inputId);
        if (input) input.style.borderColor = '';
    };

    const deliveryTimeInput = document.getElementById('delivery_time');
    const pulloutTimeInput = document.getElementById('pullout_time');
    const eventDurationInput = document.getElementById('event_duration');
    const deliveryDateInput = document.getElementById('delivery_date');
    
    if (deliveryTimeInput && deliveryTimeInput.value) {
        resetError('delivery_time');
        const dt = deliveryTimeInput.value;
        const bh = rules.business_hours || {};
        
        if (bh.open_time && dt < bh.open_time) showError('delivery_time', \`Time is before operating hours (\${bh.open_time})\`);
        if (bh.close_time && dt > bh.close_time) showError('delivery_time', \`Time is after operating hours (\${bh.close_time})\`);
        
        // Lead time validation
        if (deliveryDateInput && deliveryDateInput.value && rules.food_rules && rules.food_rules.lead_time_hours) {
            const selectedDate = new Date(deliveryDateInput.value + 'T' + dt);
            const now = new Date();
            const diffHours = (selectedDate - now) / (1000 * 60 * 60);
            if (diffHours < rules.food_rules.lead_time_hours) {
                resetError('delivery_date');
                showError('delivery_date', \`Requires \${rules.food_rules.lead_time_hours} hours lead time.\`);
            }
        }
    }
    
    if (pulloutTimeInput && pulloutTimeInput.value && rules.equipment_rules) {
        resetError('pullout_time');
        const er = rules.equipment_rules;
        if (deliveryTimeInput && deliveryTimeInput.value) {
            // Calculate rental duration
            const d1 = new Date(\`2000-01-01T\${deliveryTimeInput.value}\`);
            let d2 = new Date(\`2000-01-01T\${pulloutTimeInput.value}\`);
            if (d2 < d1) d2.setDate(d2.getDate() + 1); // Over-night assumption
            
            const diffHours = (d2 - d1) / (1000 * 60 * 60);
            if (er.min_rental_hours && diffHours < er.min_rental_hours) showError('pullout_time', \`Minimum rental is \${er.min_rental_hours} hours\`);
            if (er.max_rental_hours && diffHours > er.max_rental_hours) showError('pullout_time', \`Maximum rental is \${er.max_rental_hours} hours\`);
        }
    }
    
    if (eventDurationInput && eventDurationInput.value && rules.service_rules) {
        resetError('event_duration');
        const sr = rules.service_rules;
        const duration = parseInt(eventDurationInput.value);
        if (sr.min_duration_hours && duration < sr.min_duration_hours) showError('event_duration', \`Minimum service is \${sr.min_duration_hours} hours\`);
        if (sr.max_duration_hours && duration > sr.max_duration_hours) showError('event_duration', \`Maximum service is \${sr.max_duration_hours} hours\`);
    }

    return isValid;
}

// Attach validation to inputs
document.addEventListener('DOMContentLoaded', () => {
    ['delivery_time', 'delivery_date', 'pullout_time', 'event_duration'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', validateSchedulingRules);
    });
});
`;

if (!content.includes('validateSchedulingRules')) {
    content += '\\n' + validationCode;
    
    // Inject it into nextScreen or step validation if possible
    // We'll replace the line that usually does: if (!validateStep1()) return;
    // Actually, looking at script_1.js logic, let's just intercept the generic submit or checkout
    const hook = \`
window.nextScreen = function(stepNum) {
    if (stepNum === 2) {
        if (!validateSchedulingRules()) {
            // alert('Please fix scheduling errors before proceeding.');
            return;
        }
    }\`;
    
    content = content.replace('window.nextScreen = function(stepNum) {', hook);
    content = content.replace('function nextScreen(stepNum) {', hook.replace('window.nextScreen =', 'function nextScreen'));
    
    fs.writeFileSync(filePath, content);
    console.log('JS validation patched.');
} else {
    console.log('Already patched.');
}
