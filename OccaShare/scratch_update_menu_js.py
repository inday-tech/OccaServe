import re

filepath = 'c:/OccaServe/OccaShare/templates/caterer/menu.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace everything from <script> to </script>
js_pattern = r'<script>.*?</script>'
new_js = """<script>
    const modal = document.getElementById('menuModal');
    const form = document.getElementById('menuForm');
    const modalTitle = document.getElementById('menuModalTitle');
    const imagePreviewContainer = document.getElementById('imagePreviewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const photoDropzone = document.getElementById('photoDropzone');

    function openAddMenuModal() {
        modalTitle.innerHTML = '<i class="fas fa-utensils-alt"></i> Add New Dish';
        form.action = '/caterer/menu/add';
        form.reset();
        removeImage();
        
        if (document.getElementById('menuErrorDrawer')) document.getElementById('menuErrorDrawer').style.display = 'none';
        
        if (window.openModal) {
            window.openModal('menuModal');
        } else {
            modal.style.display = 'flex';
            requestAnimationFrame(() => modal.classList.add('active'));
        }
        calculateMenuCosts();
    }

    async function editMenuItem(el) {
        const btn = document.querySelector('#menuForm button[type="submit"]');
        if (btn) btn.disabled = false;
        try {
            const item = {
                id: el.dataset.id,
                name: el.dataset.name,
                category: el.dataset.category,
                description: el.dataset.description,
                price: el.dataset.price,
                cost_price: el.dataset.costPrice,
                pricing_unit: el.dataset.pricingUnit,
                is_hidden: el.dataset.isHidden === 'true',
                image_url: el.dataset.imageUrl
            };

            modalTitle.innerHTML = '<i class="fas fa-edit"></i> Edit Dish';
            form.action = `/caterer/menu/${item.id}/update`;
            form.name.value = item.name;
            
            const catSelect = form.category;
            const catOptions = Array.from(catSelect.options).map(o => o.value);
            if (catOptions.includes(item.category)) {
                catSelect.value = item.category;
                document.getElementById('customCategoryInput').style.display = 'none';
                document.getElementById('customCategoryInput').required = false;
            } else {
                catSelect.value = 'Other';
                document.getElementById('customCategoryInput').style.display = 'block';
                document.getElementById('customCategoryInput').value = item.category;
                document.getElementById('customCategoryInput').required = true;
            }

            form.description.value = item.description || '';
            form.price.value = item.price || 0;
            form.cost_price.value = item.cost_price || 0;
            form.unit_type.value = item.pricing_unit || 'Per Pax';
            form.status.value = item.is_hidden ? 'unavailable' : 'available';

            if (window.applyCommaFormatting) {
                window.applyCommaFormatting(form.price);
                window.applyCommaFormatting(form.cost_price);
            }

            if (item.image_url) {
                imagePreview.src = item.image_url;
                imagePreviewContainer.style.display = 'block';
                photoDropzone.style.display = 'none';
            } else {
                removeImage();
            }

            if (window.openModal) window.openModal('menuModal');
            else modal.style.display = 'flex';
            
            calculateMenuCosts();
            form.dispatchEvent(new Event('input', { bubbles: true }));
        } catch (err) { console.error("Edit error:", err); }
    }

    function calculateMenuCosts() {
        const sellInput = document.querySelector('input[name="price"]');
        const costInput = document.getElementById('cost_price_input');
        const badge = document.getElementById('roiMarginBadge');
        if (!sellInput || !costInput || !badge) return;
        const sell = parseFloat(sellInput.value.replace(/,/g, '')) || 0;
        const cost = parseFloat(costInput.value.replace(/,/g, '')) || 0;
        
        if (sell > 0) {
            const profit = sell - cost;
            const margin = (profit / sell) * 100;
            
            badge.innerText = `Estimated Profit: ₱${profit.toLocaleString(undefined, {minimumFractionDigits: 2})} (${margin.toFixed(1)}%)`;
            if (margin < 0) {
                badge.innerText = `Estimated Loss: ₱${Math.abs(profit).toLocaleString(undefined, {minimumFractionDigits: 2})} (${Math.abs(margin).toFixed(1)}%)`;
                badge.style.background = 'var(--danger-color, #ef4444)';
                badge.style.color = 'white';
            } else if (margin < 20) {
                badge.style.background = '#fef3c7';
                badge.style.color = '#d97706';
            } else {
                badge.style.background = '#dcfce7';
                badge.style.color = '#166534';
            }
        } else {
            badge.innerText = 'Profit: --';
            badge.style.background = '#f1f5f9';
            badge.style.color = '#64748b';
        }
    }

    function previewImage(event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = e => {
                imagePreview.src = e.target.result;
                imagePreviewContainer.style.display = 'block';
                photoDropzone.style.display = 'none';
            };
            reader.readAsDataURL(file);
        }
    }

    function removeImage() {
        imagePreview.src = '';
        imagePreviewContainer.style.display = 'none';
        if (photoDropzone) photoDropzone.style.display = 'flex';
        document.getElementById('menuImageInput').value = '';
    }

    function toggleCustomCategory() {
        const catSelect = document.getElementById('modalCategory');
        const customInput = document.getElementById('customCategoryInput');
        if (catSelect.value === 'Other') {
            customInput.style.display = 'block';
            customInput.required = true;
        } else {
            customInput.style.display = 'none';
            customInput.required = false;
        }
    }

    function toggleDropdown(btn, e) {
        if (e) e.stopPropagation();
        const menu = btn.nextElementSibling;
        const isActive = menu.classList.contains('active');
        document.querySelectorAll('.dropdown-menu-glass').forEach(d => d.classList.remove('active'));
        if (!isActive) menu.classList.add('active');
    }

    function filterByCategory(cat) {
        document.querySelectorAll('.cat-chip').forEach(c => c.classList.toggle('active', c.dataset.cat === cat));
        applyFilters(cat);
    }

    function filterMenu() { 
        const activeChip = document.querySelector('.cat-chip.active');
        applyFilters(activeChip ? activeChip.dataset.cat : 'all'); 
    }

    function applyFilters(cat) {
        const query = document.getElementById('menuSearchInput').value.toLowerCase();
        const cards = document.querySelectorAll('.menu-item-card-premium');
        let count = 0;
        cards.forEach(card => {
            const textContent = card.textContent.toLowerCase();
            const matchQuery = textContent.includes(query);
            const matchCat = cat === 'all' || card.dataset.category === cat;
            if (matchQuery && matchCat) {
                card.style.display = 'flex';
                count++;
            } else card.style.display = 'none';
        });
        const empty = document.querySelector('.empty-state:not(#searchEmptyState)');
        const searchEmpty = document.getElementById('searchEmptyState');
        if (empty && cards.length > 0) empty.style.display = 'none';
        if (searchEmpty) searchEmpty.style.display = count === 0 ? 'flex' : 'none';
    }

    function confirmArchiveDish(id) {
        const archiveModal = document.getElementById('archiveDishModal');
        const btn = document.querySelector(`.dropdown-item-pro[data-id="${id}"]`);
        document.getElementById('archiveItemName').innerText = btn ? btn.dataset.name : 'this dish';
        document.getElementById('confirmArchiveBtn').onclick = async () => {
            const res = await window.apiAction(`/caterer/menu/${id}/archive`, { method: 'POST' });
            if (res) {
                if (window.closeModal) window.closeModal('archiveDishModal');
                setTimeout(() => window.location.reload(), 500);
            }
        };
        if (window.openModal) window.openModal('archiveDishModal');
        else archiveModal.style.display = 'flex';
    }

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        if (!this.checkValidity()) {
            this.reportValidity();
            return;
        }
        const btn = this.querySelector('button[type="submit"]');
        this.querySelectorAll('.js-format-comma').forEach(i => i.value = i.value.replace(/,/g, ''));
        
        // --- CUSTOM CATEGORY LOGIC ---
        const catSelect = this.querySelector('select[name="category"]');
        const customInput = document.getElementById('customCategoryInput');
        if (catSelect.value === 'Other' && customInput && customInput.value.trim() !== '') {
            const newOpt = new Option(customInput.value.trim(), customInput.value.trim(), true, true);
            catSelect.appendChild(newOpt);
        }
        
        // --- PRICING & MARGIN VALIDATION ---
        const sellPrice = parseFloat(this.querySelector('input[name="price"]').value) || 0;
        const costPrice = parseFloat(document.getElementById('cost_price_input').value) || 0;
        
        if (sellPrice <= 0) {
            alert("Selling Price must be greater than zero.");
            if (btn) btn.disabled = false;
            return;
        }
        if (costPrice < 0) {
            alert("Estimated Cost cannot be negative.");
            if (btn) btn.disabled = false;
            return;
        }

        const data = new FormData(this);
        
        // Map status to is_hidden for backend
        data.set('is_hidden', this.querySelector('#modalStatus').value === 'unavailable');

        if (window.apiAction) {
            const res = await window.apiAction(this.action, { method: 'POST', body: data }, btn);
            if (res) setTimeout(() => window.location.reload(), 800);
        }
    });

    document.addEventListener('DOMContentLoaded', () => {
        const sp = document.querySelector('input[name="price"]');
        const cp = document.getElementById('cost_price_input');
        if (sp) sp.addEventListener('input', calculateMenuCosts);
        if (cp) cp.addEventListener('input', calculateMenuCosts);
        calculateMenuCosts();
    });

    window.addEventListener('click', e => {
        if (!e.target.closest('.card-options-glass')) {
            document.querySelectorAll('.dropdown-menu-glass').forEach(d => d.classList.remove('active'));
        }
    });

    // Listen to global header search
    window.addEventListener('globalSearch', function(e) {
        const hiddenInput = document.getElementById('menuSearchInput');
        if (hiddenInput) {
            hiddenInput.value = e.detail.value;
            filterMenu();
        }
    });
</script>"""

content = re.sub(js_pattern, new_js, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated JS in menu.html")
