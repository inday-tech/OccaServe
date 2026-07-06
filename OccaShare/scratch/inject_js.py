import codecs

with codecs.open('c:\\OccaServe\\OccaShare\\templates\\caterer\\packages.html', 'r', 'utf-8') as f:
    content = f.read()

script = """
<script>
window.toggleLibItemSelectCard = function(card, id) {
    const cb = card.querySelector('input[type="checkbox"]');
    if (!cb) return;
    cb.checked = !cb.checked;

    if (cb.checked) {
        card.classList.add('selected');
        card.style.background = '#f0fdf4';
        card.style.borderColor = 'var(--primary-color)';
        const i = card.querySelector('i');
        if (i) {
            i.className = 'fas fa-check-circle';
            i.parentElement.style.color = 'var(--primary-color)';
        }
    } else {
        card.classList.remove('selected');
        card.style.background = 'white';
        card.style.borderColor = '#e2e8f0';
        const i = card.querySelector('i');
        if (i) {
            i.className = 'far fa-circle';
            i.parentElement.style.color = '#cbd5e1';
        }
    }

    if (card.closest('#tab-menu')) {
        if (typeof updateSelectionRulesBuilder === 'function') {
            updateSelectionRulesBuilder();
        }
    }
};

window.toggleAllInContainer = function(checkbox, containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    
    const cards = container.querySelectorAll('.menu-select-card');
    cards.forEach(card => {
        const cb = card.querySelector('input[type="checkbox"]');
        if (!cb) return;
        
        if (cb.checked !== checkbox.checked) {
            card.click();
        }
    });
};
</script>
"""

if 'window.toggleLibItemSelectCard' not in content:
    content = content.replace('{% endblock %}', script + '\n{% endblock %}')
    with codecs.open('c:\\OccaServe\\OccaShare\\templates\\caterer\\packages.html', 'w', 'utf-8') as f:
        f.write(content)
    print('Injected JS into packages.html!')
else:
    print('JS already in packages.html')
