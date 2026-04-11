// Professional Package Management Logic

function openAddPackageModal() {
    const form = document.getElementById('packageForm');
    document.getElementById('packageModalTitle').innerText = 'Create New Package';

    form.action = '/caterer/packages/add';
    form.reset();

    // Clear dynamic custom ones specifically
    document.querySelectorAll('.custom-inclusion').forEach(el => el.remove());

    // Explicitly uncheck default inclusions
    form.querySelectorAll('input[name="inclusions"]').forEach(input => {
        input.checked = false;
    });
    
    // Reset tabs
    document.querySelectorAll('.modal-tabs-pro:nth-of-type(1) .mtab-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.modal-tabs-pro:nth-of-type(1) .mtab-btn:first-child').classList.add('active');
    document.querySelectorAll('#packageModal .tab-pane-pro').forEach(p => p.classList.remove('active'));
    document.getElementById('tab-basic').classList.add('active');

    validatePackageForm();
    showModal();
}

function validatePackageForm() {
    const form = document.getElementById('packageForm');
    if (!form) return;
    
    const submitBtn = form.querySelector('button[type="submit"]');
    if (!submitBtn) return;

    const name = form.name.value.trim();
    const desc = form.description.value.trim();
    const price = form.price_per_head.value;
    const minGuests = form.min_guests.value;

    if (name && desc && price && minGuests) {
        submitBtn.disabled = false;
        submitBtn.style.opacity = '1';
        submitBtn.style.cursor = 'pointer';
    } else {
        submitBtn.disabled = true;
        submitBtn.style.opacity = '0.5';
        submitBtn.style.cursor = 'not-allowed';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('packageForm');
    if (form) {
        form.addEventListener('input', validatePackageForm);
    }
});

function showModal() {
    document.getElementById('packageModal').style.display = 'flex';
}

function hideModal() {
    document.getElementById('packageModal').style.display = 'none';
}

function addCustomInclusion() {
    const input = document.getElementById('customInclusionInput');
    if (!input) return;
    const val = input.value.trim();
    if (val) {
        const matrix = document.getElementById('inclusionMatrix');
        // Prevent duplicates physically
        if (!matrix.querySelector(`input[value="${val}"]`)) {
            const newLabel = document.createElement('label');
            newLabel.className = 'matrix-item custom-inclusion';
            newLabel.innerHTML = `<input type="checkbox" name="inclusions" value="${val}" checked> ${val}`;
            matrix.appendChild(newLabel);
        }
        input.value = '';
    }
}

function switchPackageTab(event, tabName) {
    const modalBody = event.currentTarget.closest('.modal-body-pro');
    modalBody.querySelectorAll('.tab-pane-pro').forEach(p => p.classList.remove('active'));
    event.currentTarget.parentElement.querySelectorAll('.mtab-btn').forEach(b => b.classList.remove('active'));

    document.getElementById('tab-' + tabName).classList.add('active');
    event.currentTarget.classList.add('active');
}

async function editPackage(pkgId) {
    try {
        const response = await fetch(`/caterer/packages/${pkgId}/details`);
        if (!response.ok) throw new Error('Failed to fetch');

        const pkg = await response.json();

        document.getElementById('packageModalTitle').innerText = 'Edit Package';

        const form = document.getElementById('packageForm');
        form.action = `/caterer/packages/${pkgId}/update`;

        // Populate fields
        form.name.value = pkg.name || '';
        form.description.value = pkg.description || '';
        form.service_type.value = pkg.service_type || 'General';
        form.price_per_head.value = pkg.price_per_head || '';
        form.min_contract_amount.value = pkg.min_contract_amount || '';
        form.min_guests.value = pkg.min_guests || 10;
        form.max_guests.value = pkg.max_guests || '';
        form.service_duration.value = pkg.service_duration || 8;
        form.cost_price.value = pkg.cost_price || 0;

        // Apply immediate formatting
        if (window.applyCommaFormatting) {
            window.applyCommaFormatting(form.price_per_head);
            window.applyCommaFormatting(form.min_contract_amount);
            window.applyCommaFormatting(form.cost_price);
            window.applyCommaFormatting(form.min_guests);
            window.applyCommaFormatting(form.max_guests);
            window.applyCommaFormatting(form.service_duration);
        }

        // Clear previous dynamically created inclusions
        document.querySelectorAll('.custom-inclusion').forEach(el => el.remove());

        // Handle inclusions natively (dict vs list parsing based on payload)
        const inclusions = pkg.inclusions || {};
        
        // Reset all defaults first
        form.querySelectorAll('input[name="inclusions"]').forEach(input => input.checked = false);
        
        // Dynamically parse through the custom JSON
        const matrix = document.getElementById('inclusionMatrix');
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

        showModal();
    } catch (error) {
        console.error('Edit fetch failed:', error);
        window.showError('Could not load package details.');
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
                window.showToast(`${pkgName} is now visible to customers.`, 'success');
            } else {
                element.classList.remove('active');
                if (label.tagName === 'SPAN') label.innerText = 'hidden';
                window.showToast(`${pkgName} is now hidden from customers.`, 'info');
            }
        }
    } catch (error) {
        console.error('Toggle failed:', error);
    }
}

function showMenuModal(packageId, packageName) {
    document.getElementById('modalMenuPackageId').value = packageId;
    document.getElementById('targetPkgDisplay').innerText = `Package: ${packageName}`;
    document.getElementById('menuForm').action = `/caterer/packages/${packageId}/menu/add`;

    const container = document.getElementById('menuItemsContainer');
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

    document.getElementById('menuModal').style.display = 'flex';
}

function hideMenuModal() {
    document.getElementById('menuModal').style.display = 'none';
}

async    function confirmArchiveDish(id) {
        window.showConfirm("Are you sure you want to archive this dish? It will be moved to your archives and hidden from your offerings.", () => {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/caterer/menu/${id}/archive?next=/caterer/menu?success_msg=Dish+archived+successfully`;
            document.body.appendChild(form);
            form.submit();
        }, "Archive Dish?", "Yes, Archive Dish");
    }

async function archivePackage(pkgId) {
    window.showConfirm('Are you sure you want to archive this package? It will be moved to your archives and hidden from your offerings.', async () => {
        try {
            const response = await fetch(`/caterer/packages/${pkgId}/archive`, { method: 'POST' });
            if (response.ok) {
                const card = document.getElementById(`package-${pkgId}`);
                if (card) {
                    card.style.transform = 'scale(0.9)';
                    card.style.opacity = '0';
                    setTimeout(() => {
                        window.location.href = window.location.pathname + "?success_msg=Package+archived+successfully";
                    }, 400);
                } else {
                    window.location.href = window.location.pathname + "?success_msg=Package+archived+successfully";
                }
            } else {
                window.showError('Could not archive package. Please try again.');
            }
        } catch (error) {
            window.showError('Could not archive package. Please try again.');
        }
    }, "Archive Package?", "Yes, Archive");
}

async function deleteMenuItem(itemId) {
    window.showConfirm('Remove this dish from this package? (It will remain in your library)', async () => {
        try {
            const pkgId = document.getElementById('modalMenuPackageId').value;
            const response = await fetch(`/caterer/packages/${pkgId}/menu/${itemId}/unlink`, { method: 'POST' });
            if (response.ok) {
                const pkgName = document.getElementById('targetPkgDisplay').innerText.replace('Package: ', '');
                showMenuModal(pkgId, pkgName);
                window.showToast('Dish removed from package', 'success');
            }
        } catch (error) {
            console.error('Error:', error);
            window.showError('Could not remove dish.');
        }
    });
}

function switchMenuMode(mode) {
    document.querySelectorAll('.menu-mode-pane').forEach(p => p.style.display = 'none');
    document.getElementById('menu-mode-' + mode).style.display = 'block';
    
    const menuBtns = document.getElementById('menuModal').querySelectorAll('.mtab-btn');
    menuBtns.forEach(btn => {
        btn.classList.remove('active');
        if (mode === 'current' && btn.innerText.includes('Curated')) btn.classList.add('active');
        if (mode === 'library' && btn.innerText.includes('Library')) btn.classList.add('active');
        if (mode === 'new' && btn.innerText.includes('New')) btn.classList.add('active');
    });

    if (mode === 'library') {
        loadLibraryItems();
    }
}

async function loadLibraryItems() {
    const container = document.getElementById('libraryItemsContainer');
    const pkgId = document.getElementById('modalMenuPackageId').value;
    container.innerHTML = '<div class="text-center p-4"><i class="fas fa-spinner fa-spin fa-2x text-primary"></i></div>';

    try {
        const [libRes, pkgRes] = await Promise.all([
            fetch('/caterer/api/menu'),
            fetch(`/caterer/packages/${pkgId}/details`)
        ]);
        
        const library = await libRes.json();
        // We need to know which items are already linked to avoid duplicates
        // Let's use the package/menu endpoint instead of details for actual items
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
    const pkgId = document.getElementById('modalMenuPackageId').value;
    const formData = new FormData();
    formData.append('item_id', itemId);

    try {
        const response = await fetch(`/caterer/packages/${pkgId}/menu/link`, {
            method: 'POST',
            body: formData
        });
        if (response.ok) {
            loadLibraryItems(); // Refresh library view
            window.showToast('Dish linked to package', 'success');
        } else {
            window.showError('Could not link item.');
        }
    } catch (e) {
        console.error('Link failed:', e);
    }
}

function filterLibraryItems() {
    const query = document.getElementById('librarySearchInput').value.toLowerCase();
    document.querySelectorAll('.library-item').forEach(item => {
        item.style.display = item.dataset.name.includes(query) ? 'flex' : 'none';
    });
}

// Global Event Listeners
document.addEventListener('DOMContentLoaded', function () {
    // Add-on Price Toggle
    const isAddonCheck = document.getElementById('is_addon');
    if (isAddonCheck) {
        isAddonCheck.addEventListener('change', function () {
            const priceGroup = document.getElementById('addonPriceGroup');
            priceGroup.style.display = this.checked ? 'block' : 'none';
            if (this.checked) priceGroup.querySelector('input').focus();
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
            const originalText = submitBtn.innerText;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

            // Sanitize numeric inputs (remove commas)
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
                    // Use the new URL success message system
                    const url = new URL(window.location.href);
                    url.searchParams.set('success_msg', 'Package saved successfully!');
                    window.location.href = url.pathname + url.search + url.hash;
                } else {
                    window.showError('Error saving package details.');
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
    const menuForm = document.getElementById('menuForm');
    if (menuForm) {
        menuForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerText;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Curating...';

            // Sanitize numeric inputs (remove commas)
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
                    // Explicitly reset the addon group
                    document.getElementById('addonPriceGroup').style.display = 'none';

                    const pkgId = document.getElementById('modalMenuPackageId').value;
                    const pkgName = document.getElementById('targetPkgDisplay').innerText.replace('Package: ', '');
                    showMenuModal(pkgId, pkgName);

                    window.showToast('New dish added and curated!', 'success');
                    submitBtn.disabled = false;
                    submitBtn.innerText = originalText;
                } else {
                    window.showError('Failed to add dish.');
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
});

window.onclick = function (event) {
    if (event.target.classList.contains('modal-pro')) {
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
