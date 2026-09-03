import re

with open('app/static/js/caterer/bookings.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

replacement = '''
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(() => {
            if (window.showSuccess) window.showSuccess('Payment link copied to clipboard!');
            else alert('Payment link copied to clipboard!');
        }).catch(err => {
            alert('Failed to copy: ' + url);
        });
    } else {
        const el = document.createElement('textarea');
        el.value = url;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        if (window.showSuccess) window.showSuccess('Payment link copied to clipboard!');
        else alert('Payment link copied to clipboard!');
    }
'''

js_content = re.sub(
    r'navigator\.clipboard\.writeText\(url\)\.then\(\(\) => \{[\s\S]*?\}\)\.catch\(err => \{[\s\S]*?\}\);',
    replacement,
    js_content
)

with open('app/static/js/caterer/bookings.js', 'w', encoding='utf-8') as f:
    f.write(js_content)
print('Fixed clipboard fallback in bookings.js')
