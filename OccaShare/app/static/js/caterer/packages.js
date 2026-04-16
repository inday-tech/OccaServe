// Professional Package Management Logic (Safety Hardened v11.1)

function openAddPackageModal() {
    try {
        const form = document.getElementById('packageForm');
        if (!form) return;
        
        const title = document.getElementById('packageModalTitle');
        if (title) title.innerText = 'Create New Package';

        form.action = '/caterer/packages/add';
        form.reset();

        // Clear dynamic custom ones specifically
        document.querySelectorAll('.custom-inclusion').forEach(el => el.remove());

        // Explicitly uncheck default inclusions
        form.querySelectorAll('input[name="inclusions"]').forEach(input => {
            input.checked = false;
        });
        
        // Reset tabs safely
        const tabBtns = document.querySelectorAll('#packageModal .modal-tabs-pro .mtab-btn');
        if (tabBtns.length > 0) {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabBtns[0].classList.add('active');
        }

        const tabPanes = document.querySelectorAll('#packageModal .tab-pane-pro');
        if (tabPanes.length > 0) {
            tabPanes.forEach(p => p.classList.remove('active'));
            const basicTab = document.getElementById('tab-basic');
            if (basicTab) basicTab.classList.add('active');
        }

        showModal();
    } catch (e) {
        console.error('Error opening package modal:', e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    try {
        if (window.ValidationManager) {
            // Initialize Package Form Validation
            new window.ValidationManager('packageForm', {
                'name': { unique: true, uniqueApi: '/caterer/api/validate-package-name', label: 'package' },
                'service_duration': { numericOnly: true },
                'price_per_head': { numericOnly: true, max: 100000, autoStop: true },
                'cost_price': { numericOnly: true, max: 100000, autoStop: true },
                'min_contract_amount': { numericOnly: true, max: 10000000, autoStop: true }
            });

            // Initialize Menu Form (Mini version in packages.html)
            new window.ValidationManager('menuForm', {
                'name': { unique: true, uniqueApi: '/caterer/api/validate-dish-name', label: 'dish' },
                'cost_price': { numericOnly: true, max: 100000, autoStop: true },
                'addon_price': { numericOnly: true, max: 50000, autoStop: true }
            });
        }
    } catch (e) {
        console.error('Validation init error:', e);
    }
});

function showModal() {
    const el = document.getElementById('packageModal');
    if (!el) return;
    el.style.display = 'flex';
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            el.classList.add('active');
        });
    });
}

function hideModal() {
    const el = document.getElementById('packageModal');
    if (!el) return;
    el.classList.remove('active');
    setTimeout(() => {
        if (!el.classList.contains('active')) {
            el.style.display = 'none';
        }
    }, 400);
}

function addCustomInclusion() {
    try {
        const input = document.getElementById('customInclusionInput');
        if (!input) return;
        const val = input.value.trim();
        if (val) {
            const matrix = document.getElementById('inclusionMatrix');
            if (!matrix) return;
            // Prevent duplicates physically
            if (!matrix.querySelector(`input[value="${val}"]`)) {
                const newLabel = document.createElement('label');
                newLabel.className = 'matrix-item custom-inclusion';
                newLabel.innerHTML = `<input type="checkbox" name="inclusions" value="${val}" checked> ${val}`;
                matrix.appendChild(newLabel);
            }
            input.value = '';
        }
    } catch (e) {
        console.error('Custom inclusion error:', e);
    }
}

function switchPackageTab(el, tabName) {
    if (!el) return;
    try {
        const modalBody = el.closest('.occ-modal-body');
        if (!modalBody) return;

        // Toggle Panes safely
        const panes = modalBody.querySelectorAll('.tab-pane-pro');
        if (panes.length > 0) {
            panes.forEach(p => p.classList.remove('active'));
        }
        
        const targetPane = document.getElementById('tab-' + tabName);
        if (targetPane) {
            targetPane.classList.add('active');
        }

        // Toggle Buttons safely
        const parent = el.parentElement;
        if (parent) {
            parent.querySelectorAll('.mtab-btn').forEach(b => b.classList.remove('active'));
        }
        el.classList.add('active');
    } catch (e) {
        console.error('Tab switch error:', e);
    }
}

async function editPackage(pkgId) {
    try {
        const response = await fetch(`/caterer/packages/${pkgId}/details`);
        if (!response.ok) throw new Error('Failed to fetch');

        const pkg = await response.json();

        const title = document.getElementById('packageModalTitle');
        if (title) title.innerText = 'Edit Package';

        const form = document.getElementById('packageForm');
        if (!form) return;
        form.action = `/caterer/packages/${pkgId}/update`;

        // Populate fields safely
        if (form.name) form.name.value = pkg.name || '';
        if (form.description) form.description.value = pkg.description || '';
        if (form.service_type) form.service_type.value = pkg.service_type || 'General';
        if (form.price_per_head) form.price_per_head.value = pkg.price_per_head || '';
        if (form.min_contract_amount) form.min_contract_amount.value = pkg.min_contract_amount || '';
        if (form.min_guests) form.min_guests.value = pkg.min_guests || 10;
        if (form.max_guests) form.max_guests.value = pkg.max_guests || '';
        if (form.service_duration) form.service_duration.value = pkg.service_duration || 8;
        if (form.cost_price) form.cost_price.value = pkg.cost_price || 0;

        const costContainer = document.getElementById('costRowsContainer');
        if (costContainer) {
            costContainer.innerHTML = '';
            if (pkg.cost_breakdown && pkg.cost_breakdown.length > 0) {
                pkg.cost_breakdown.forEach(item => {
                    const row = document.createElement('div');
                    row.className = 'premium-cost-row';
                    row.innerHTML = `
                        <div class="premium-cost-input-group">
                            <label>Expense Item</label>
                            <input type="text" class="premium-cost-control cost-name" value="${item.name}" placeholder="Expense Name">
                        </div>
                        <div class="premium-cost-input-group" style="max-width: 120px;">
                            <label>Cost (₱)</label>
                            <input type="number" class="premium-cost-control cost-amount" value="${item.amount}" placeholder="0" min="0" oninput="calculateCosts()">
                        </div>
                        <button type="button" class="btn-remove-cost" onclick="this.parentElement.remove(); calculateCosts()"><i class="fas fa-trash-alt"></i></button>
                    `;
                    costContainer.appendChild(row);
                });
            } else {
                if (window.addCostRow) window.addCostRow('costRowsContainer');
            }
            if (window.calculateCosts) window.calculateCosts();
        }

        // Apply immediate formatting
        if (window.applyCommaFormatting) {
            const numFields = ['price_per_head', 'min_contract_amount', 'cost_price', 'min_guests', 'max_guests', 'service_duration'];
            numFields.forEach(f => {
                if (form[f]) window.applyCommaFormatting(form[f]);
            });
        }

        // Clear previous dynamically created inclusions
        document.querySelectorAll('.custom-inclusion').forEach(el => el.remove());

        // Handle inclusions
        const inclusions = pkg.inclusions || {};
        form.querySelectorAll('input[name="inclusions"]').forEach(input => input.checked = false);
        
        const matrix = document.getElementById('inclusionMatrix');
        if (matrix) {
            Object.keys(inclusions).forEach(inc => {
                if (inclusions[inc]) {
                    const existing = form.querySelector(`input[name="inclusions"][value="${inc}"]`);
                    if (!existing) {
                        const newLabel = document.createElement('label');
                        newLabel.className = 'matrix-item custom-inclusion';
                        newLabel.innerHTML = `<input type="checkbox" name="inclusions" value="${inc}" checked> ${inc}`;
                        matrix.appendChild(newLabel);
                    } else {
                        existing.checked = true;
                    }
                }
            });
        }
        
        // Reset tabs to logistics on edit
        const tabBtns = document.querySelectorAll('#packageModal .modal-tabs-pro .mtab-btn');
        if (tabBtns.length > 0) {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabBtns[0].classList.add('active');
        }
        const tabPanes = document.querySelectorAll('#packageModal .tab-pane-pro');
        if (tabPanes.length > 0) {
            tabPanes.forEach(p => p.classList.remove('active'));
            const basicTab = document.getElementById('tab-basic');
            if (basicTab) basicTab.classList.add('active');
        }

        form.dispatchEvent(new Event('input'));
        showModal();
    } catch (error) {
        console.error('Edit fetch failed:', error);
        if (window.showError) window.showError('Could not load package details.');
    }
}

async function togglePackageStatus(pkgId, element) {
    try {
        const response = await fetch(`/caterer/packages/${pkgId}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (data.status === 'success') {
            const label = element.querySelector('.label') || element;
            const pkgName = element.closest('.package-card-pro')?.querySelector('.package-name-pro')?.innerText || 'Package';
            
            if (data.is_active) {
                element.classList.add('active');
                if (label.tagName === 'SPAN') label.innerText = 'active';
                if (window.showToast) window.showToast(`${pkgName} is now visible to customers.`, 'success');
            } else {
                element.classList.remove('active');
                if (label.tagName === 'SPAN') label.innerText = 'hidden';
                if (window.showToast) window.showToast(`${pkgName} is now hidden from customers.`, 'info');
            }
        }
    } catch (error) {
        console.error('Toggle failed:', error);
    }
}

function showMenuModal(packageId, packageName) {
    try {
        const pkgIdInput = document.getElementById('modalMenuPackageId');
        if (pkgIdInput) pkgIdInput.value = packageId;
        
        const display = document.getElementById('targetPkgDisplay');
        if (display) display.innerText = `Package: ${packageName}`;
        
        const menuForm = document.getElementById('menuForm');
        if (menuForm) menuForm.action = `/caterer/packages/${packageId}/menu/add`;

        const container = document.getElementById('menuItemsContainer');
        if (container) {
            container.innerHTML = '<div class="text-center p-4"><i class="fas fa-spinner fa-spin fa-2x text-primary"></i></div>';

            fetch(`/caterer/packages/${packageId}/menu`)
                .then(response => response.json())
                .then(data => {
                    container.innerHTML = '';
                    if (data && data.length > 0) {
                        data.forEach(item => {
                            const row = document.createElement('div');
                            row.className = 'menu-item-pro-row';
                            row.innerHTML = `
                                <img src="${item.image_url || '/static/images/default_dish.jpg'}" class="dish-thumb">
                                <div class="dish-info-pro">
                                    <h6>${item.name}</h6>
                                    <span>${item.category} • ${item.is_addon ? 'Premium Add-on' : 'Included'}</span>
                                </div>
                                <button type="button" class="btn btn-link text-danger p-0" onclick="deleteMenuItem(${item.id})">
                                    <i class="fas fa-times-circle"></i>
                                </button>
                            `;
                            container.appendChild(row);
                        });
                    } else {
                        container.innerHTML = '<p class="text-center text-muted p-3">No items curated for this package yet.</p>';
                    }
                });
        }

        const el = document.getElementById('menuModal');
        if (!el) return;
        el.style.display = 'flex';
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                el.classList.add('active');
            });
        });
    } catch (e) {
        console.error('Menu modal error:', e);
    }
}

function hideMenuModal() {
    const el = document.getElementById('menuModal');
    if (!el) return;
    el.classList.remove('active');
    setTimeout(() => {
        if (!el.classList.contains('active')) {
            el.style.display = 'none';
        }
    }, 400);
}

function confirmArchiveDish(id) {
    if (window.showConfirm) {
        window.showConfirm("Are you sure you want to archive this dish? It will be moved to your archives and hidden from your offerings.", async () => {
            await window.apiAction(`/caterer/menu/${id}/archive`, { method: 'POST' });
        }, "Archive Dish?", "Yes, Archive Dish");
    }
}

async function archivePackage(pkgId) {
    if (window.showConfirm) {
        window.showConfirm('Are you sure you want to archive this package? It will be moved to your archives and hidden from your offerings.', async () => {
            await window.apiAction(`/caterer/packages/${pkgId}/archive`, { method: 'POST' });
        }, "Archive Package?", "Yes, Archive");
    }
}

async function deleteMenuItem(itemId) {
    if (window.showConfirm) {
        window.showConfirm('Remove this dish from this package? (It will remain in your library)', async () => {
            try {
                const pkgId = document.getElementById('modalMenuPackageId').value;
                const response = await fetch(`/caterer/packages/${pkgId}/menu/${itemId}/unlink`, { method: 'POST' });
                if (response.ok) {
                    const pkgName = document.getElementById('targetPkgDisplay').innerText.replace('Package: ', '');
                    showMenuModal(pkgId, pkgName);
                    if (window.showToast) window.showToast('Dish removed from package', 'success');
                }
            } catch (error) {
                console.error('Error:', error);
                if (window.showError) window.showError('Could not remove dish.');
            }
        });
    }
}

function switchMenuMode(mode) {
    try {
        document.querySelectorAll('.menu-mode-pane').forEach(p => p.style.display = 'none');
        const target = document.getElementById('menu-mode-' + mode);
        if (target) target.style.display = 'block';
        
        const menuModal = document.getElementById('menuModal');
        if (menuModal) {
            const menuBtns = menuModal.querySelectorAll('.mtab-btn');
            menuBtns.forEach(btn => {
                btn.classList.remove('active');
                const text = btn.innerText.toLowerCase();
                if (mode === 'current' && (text.includes('curated') || text.includes('menu'))) btn.classList.add('active');
                if (mode === 'library' && text.includes('library')) btn.classList.add('active');
                if (mode === 'new' && (text.includes('new') || text.includes('dish'))) btn.classList.add('active');
            });
        }

        if (mode === 'library') {
            loadLibraryItems();
        }
    } catch (e) {
        console.error('Menu mode error:', e);
    }
}

async function loadLibraryItems() {
    const container = document.getElementById('libraryItemsContainer');
    if (!container) return;
    const pkgId = document.getElementById('modalMenuPackageId').value;
    container.innerHTML = '<div class="text-center p-4"><i class="fas fa-spinner fa-spin fa-2x text-primary"></i></div>';

    try {
        const [libRes, pkgRes] = await Promise.all([
            fetch('/caterer/api/menu'),
            fetch(`/caterer/packages/${pkgId}/details`)
        ]);
        
        const library = await libRes.json();
        const pkgMenuRes = await fetch(`/caterer/packages/${pkgId}/menu`);
        const pkgMenu = await pkgMenuRes.json();
        const linkedIds = pkgMenu.map(i => i.id);

        container.innerHTML = '';
        if (library.length > 0) {
            library.forEach(item => {
                const isLinked = linkedIds.includes(item.id);
                const row = document.createElement('div');
                row.className = 'menu-item-pro-row library-item';
                row.dataset.name = item.name.toLowerCase();
                row.innerHTML = `
                    <img src="${item.image_url || '/static/images/default_dish.jpg'}" class="dish-thumb">
                    <div class="dish-info-pro">
                        <h6>${item.name}</h6>
                        <span>${item.category}</span>
                    </div>
                    ${isLinked ? 
                        '<span class="badge bg-success-light text-success rounded-pill px-3 py-1 small">Linked</span>' : 
                        `<button type="button" class="btn btn-sm btn-outline-primary rounded-pill px-3" onclick="linkLibraryItem(${item.id})">Link</button>`
                    }
                `;
                container.appendChild(row);
            });
        } else {
            container.innerHTML = '<p class="text-center text-muted p-3">Your library is empty. Add items first!</p>';
        }
    } catch (e) {
        container.innerHTML = '<p class="text-center text-danger p-3">Error loading library.</p>';
    }
}

async function linkLibraryItem(itemId) {
    try {
        const pkgId = document.getElementById('modalMenuPackageId').value;
        const formData = new FormData();
        formData.append('item_id', itemId);

        const response = await fetch(`/caterer/packages/${pkgId}/menu/link`, {
            method: 'POST',
            body: formData
        });
        if (response.ok) {
            loadLibraryItems();
            if (window.showToast) window.showToast('Dish linked to package', 'success');
        } else {
            if (window.showError) window.showError('Could not link item.');
        }
    } catch (e) {
        console.error('Link failed:', e);
    }
}

function filterLibraryItems() {
    const input = document.getElementById('librarySearchInput');
    if (!input) return;
    const query = input.value.toLowerCase();
    document.querySelectorAll('.library-item').forEach(item => {
        item.style.display = item.dataset.name.includes(query) ? 'flex' : 'none';
    });
}

// Global Event Listeners
document.addEventListener('DOMContentLoaded', function () {
    try {
        // Add-on Price Toggle
        const isAddonCheck = document.getElementById('is_addon');
        if (isAddonCheck) {
            isAddonCheck.addEventListener('change', function () {
                const priceGroup = document.getElementById('addonPriceGroup');
                if (priceGroup) {
                    priceGroup.style.display = this.checked ? 'block' : 'none';
                    if (this.checked) {
                        const input = priceGroup.querySelector('input');
                        if (input) input.focus();
                    }
                }
            });
        }

        // Link Toggle Button Text Update
        const linkToggle = document.getElementById('link_to_package');
        if (linkToggle) {
            linkToggle.addEventListener('change', function () {
                const btn = document.getElementById('menuSubmitBtn');
                if (btn) {
                    btn.innerText = this.checked ? 'Add to Library & Package' : 'Add to Library Only';
                }
            });
        }

        // AJAX Form Submission for Packages
        const pkgForm = document.getElementById('packageForm');
        if (pkgForm) {
            pkgForm.addEventListener('submit', async function (e) {
                e.preventDefault();
                const submitBtn = this.querySelector('button[type="submit"]');
                if (!submitBtn) return;
                const originalText = submitBtn.innerText;
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

                // Sanitize numeric inputs
                this.querySelectorAll('.js-format-comma').forEach(input => {
                    input.value = input.value.replace(/,/g, '');
                });

                const formData = new FormData(this);
                try {
                    const response = await fetch(this.action, {
                        method: 'POST',
                        body: formData
                    });

                    if (response.ok) {
                        hideModal();
                        const url = new URL(window.location.href);
                        url.searchParams.set('success_msg', 'Package saved successfully!');
                        window.location.href = url.pathname + url.search + url.hash;
                    } else {
                        if (window.showError) window.showError('Error saving package details.');
                        submitBtn.disabled = false;
                        submitBtn.innerText = originalText;
                    }
                } catch (error) {
                    console.error('Submission error:', error);
                    submitBtn.disabled = false;
                    submitBtn.innerText = originalText;
                }
            });
        }

        // AJAX Form Submission for Menu Items
        const mForm = document.getElementById('menuForm');
        if (mForm) {
            mForm.addEventListener('submit', async function (e) {
                e.preventDefault();
                const submitBtn = this.querySelector('button[type="submit"]');
                if (!submitBtn) return;
                const originalText = submitBtn.innerText;
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Curating...';

                this.querySelectorAll('.js-format-comma').forEach(input => {
                    input.value = input.value.replace(/,/g, '');
                });

                const formData = new FormData(this);
                try {
                    const response = await fetch(this.action, {
                        method: 'POST',
                        body: formData
                    });
                    if (response.ok) {
                        this.reset();
                        const addonGroup = document.getElementById('addonPriceGroup');
                        if (addonGroup) addonGroup.style.display = 'none';

                        const pkgId = document.getElementById('modalMenuPackageId').value;
                        const display = document.getElementById('targetPkgDisplay');
                        const pkgName = display ? display.innerText.replace('Package: ', '') : '';
                        showMenuModal(pkgId, pkgName);

                        if (window.showToast) window.showToast('New dish added and curated!', 'success');
                        submitBtn.disabled = false;
                        submitBtn.innerText = originalText;
                    } else {
                        if (window.showError) window.showError('Failed to add dish.');
                        submitBtn.disabled = false;
                        submitBtn.innerText = originalText;
                    }
                } catch (error) {
                    console.error('Menu save error:', error);
                    submitBtn.disabled = false;
                    submitBtn.innerText = originalText;
                }
            });
        }
    } catch (e) {
        console.error('Global listener init error:', e);
    }
});

window.onclick = function (event) {
    if (event.target.classList.contains('occ-modal-overlay')) {
        hideModal();
        hideMenuModal();
    }
}

// Expose functions globally
window.openAddPackageModal = openAddPackageModal;
window.hideModal = hideModal;
window.switchPackageTab = switchPackageTab;
window.addCustomInclusion = addCustomInclusion;
window.editPackage = editPackage;
window.togglePackageStatus = togglePackageStatus;
window.showMenuModal = showMenuModal;
window.hideMenuModal = hideMenuModal;
window.archivePackage = archivePackage;
window.deleteMenuItem = deleteMenuItem;
window.switchMenuMode = switchMenuMode;
window.linkLibraryItem = linkLibraryItem;
window.filterLibraryItems = filterLibraryItems;
