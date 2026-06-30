import os

file_path = r"c:\OccaServe\OccaShare\app\static\js\customer\alacarte_checkout.js"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """
    if (deliveryTimeInput && deliveryTimeInput.value) {
        resetError('delivery_time');
        const dt = deliveryTimeInput.value;
        const bh = rules.business_hours || {};
        
        if (bh.open_time && dt < bh.open_time) showError('delivery_time', `Time is before operating hours (${bh.open_time})`);
        if (bh.close_time && dt > bh.close_time) showError('delivery_time', `Time is after operating hours (${bh.close_time})`);"""

replacement = """
    const format12Hour = (timeStr) => {
        if (!timeStr) return '';
        let [h, m] = timeStr.split(':');
        let hours = parseInt(h);
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12 || 12;
        return `${hours}:${m} ${ampm}`;
    };

    if (deliveryTimeInput && deliveryTimeInput.value) {
        resetError('delivery_time');
        const dt = deliveryTimeInput.value;
        const bh = rules.business_hours || {};
        
        if (bh.open_time && dt < bh.open_time) showError('delivery_time', `Time is before operating hours (${format12Hour(bh.open_time)})`);
        if (bh.close_time && dt > bh.close_time) showError('delivery_time', `Time is after operating hours (${format12Hour(bh.close_time)})`);"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched time format in JS")
else:
    print("Could not find target block")
