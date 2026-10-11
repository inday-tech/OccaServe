// caterer/portfolio.js

let coverPhotoFile = null;
let galleryFiles = [];
let existingGalleryUrls = [];
let deletedGalleryIds = [];
let highlightsTagify = null;
let hasExistingCoverPhoto = false;
let portfolioSaving = false;

document.addEventListener("DOMContentLoaded", () => {
    // Initialize Tagify for highlights
    const highlightsInput = document.getElementById('highlightsInput');
    if (highlightsInput) {
        highlightsTagify = new Tagify(highlightsInput, {
            dropdown: {
                classname: "tags-look",
                enabled: 0,
                closeOnSelect: false
            }
        });
    }

    // Check for search query in URL
    const urlParams = new URLSearchParams(window.location.search);
    const searchQ = urlParams.get('search') || urlParams.get('q');
    if (searchQ) {
        filterPortfolios(searchQ);
        const globalSearchInput = document.getElementById('globalSearchInput');
        if (globalSearchInput) globalSearchInput.value = searchQ;
    }

    window.addEventListener('globalSearch', (e) => {
        filterPortfolios(e.detail?.value || '');
    });

    const form = document.getElementById('portfolioForm');
    form.addEventListener('input', updatePortfolioSubmitState);
    form.addEventListener('change', updatePortfolioSubmitState);
    updatePortfolioSubmitState();
});

function filterPortfolios(query) {
    const q = (query || '').toLowerCase().trim();
    const cards = document.querySelectorAll('.portfolio-card');
    cards.forEach(card => {
        const text = card.textContent.toLowerCase();
        card.style.display = (!q || text.includes(q)) ? '' : 'none';
    });
}

function openPortfolioModal() {
    const form = document.getElementById('portfolioForm');
    form.reset();
    form.action = '/caterer/portfolio/create';
    document.getElementById('portfolioIdInput').value = '';
    coverPhotoFile = null;
    hasExistingCoverPhoto = false;
    galleryFiles = [];
    existingGalleryUrls = [];
    deletedGalleryIds = [];
    if (highlightsTagify) highlightsTagify.removeAllTags();
    document.getElementById('coverImg').style.display = 'none';
    document.getElementById('coverImg').src = '';
    document.getElementById('coverPlaceholder').style.display = 'flex';
    renderGalleryPreviews();
    togglePortfolioCustomEventType();
    document.querySelector('#portfolioModal .occ-modal-title').innerText = 'Add Portfolio Entry';
    document.getElementById('portfolioModal').classList.add('active');
    document.body.style.overflow = 'hidden';
    updatePortfolioSubmitState();
}

function closePortfolioModal() {
    document.getElementById('portfolioModal').classList.remove('active');
    document.body.style.overflow = '';
    
    // Reset Form
    document.getElementById('portfolioForm').reset();
    if(highlightsTagify) highlightsTagify.removeAllTags();
    
    // Reset previews
    coverPhotoFile = null;
    hasExistingCoverPhoto = false;
    document.getElementById('coverImg').style.display = 'none';
    document.getElementById('coverImg').src = '';
    document.getElementById('coverPlaceholder').style.display = 'flex';
    
    galleryFiles = [];
    existingGalleryUrls = [];
    deletedGalleryIds = [];
    renderGalleryPreviews();
    togglePortfolioCustomEventType();
    updatePortfolioSubmitState();
}

function togglePortfolioCustomEventType() {
    const eventType = document.getElementById('portfolioEventTypeInput');
    const customType = document.getElementById('portfolioCustomEventTypeInput');
    if (!eventType || !customType) return;

    const isOther = eventType.value === 'Other';
    customType.hidden = !isOther;
    customType.disabled = !isOther;
    customType.required = isOther;
    updatePortfolioSubmitState();
}

function isPortfolioFormValid() {
    const form = document.getElementById('portfolioForm');
    const eventType = document.getElementById('portfolioEventTypeInput').value;
    const customType = document.getElementById('portfolioCustomEventTypeInput').value.trim();
    const title = document.getElementById('portfolioTitleInput').value.trim();
    const description = document.getElementById('portfolioDescriptionInput').value.trim();

    return form.checkValidity()
        && title.length > 0
        && description.length > 0
        && (eventType !== 'Other' || customType.length > 0)
        && (hasExistingCoverPhoto || Boolean(coverPhotoFile));
}

function updatePortfolioSubmitState() {
    const submitButton = document.getElementById('submitPortfolioBtn');
    if (submitButton) {
        submitButton.disabled = portfolioSaving || !isPortfolioFormValid();
    }
}

function previewCoverPhoto(input) {
    if (input.files && input.files[0]) {
        coverPhotoFile = input.files[0];
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('coverImg').src = e.target.result;
            document.getElementById('coverImg').style.display = 'block';
            document.getElementById('coverPlaceholder').style.display = 'none';
        }
        reader.readAsDataURL(coverPhotoFile);
        updatePortfolioSubmitState();
    }
}

function previewGalleryPhotos(input) {
    if (input.files) {
        const remainingSlots = 10 - galleryFiles.length;
        const newFiles = Array.from(input.files).slice(0, remainingSlots);
        
        if (input.files.length > remainingSlots) {
            alert(`You can only add up to 10 photos. Only the first ${remainingSlots} were added.`);
        }
        
        galleryFiles = [...galleryFiles, ...newFiles];
        renderGalleryPreviews();
    }
    // Reset input so same files can be selected again if removed
    input.value = '';
}

function removeGalleryPhoto(index) {
    galleryFiles.splice(index, 1);
    renderGalleryPreviews();
}

function renderGalleryPreviews() {
    const grid = document.getElementById('galleryGrid');
    // Keep only the first upload box
    const uploadBox = grid.firstElementChild;
    grid.innerHTML = '';
    grid.appendChild(uploadBox);
    
    // Render existing photos
    existingGalleryUrls.forEach((item, index) => {
        const previewBox = document.createElement('div');
        previewBox.className = 'preview-box';
        previewBox.innerHTML = `
            <img src="${item.url}">
            <div style="position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.5); color: white; font-size: 10px; text-align: center; padding: 2px;">Existing</div>
            <button type="button" class="preview-remove" onclick="removeExistingGalleryPhoto(${index})"><i class="fas fa-times"></i></button>
        `;
        grid.appendChild(previewBox);
    });

    galleryFiles.forEach((file, index) => {
        const reader = new FileReader();
        reader.onload = function(e) {
            const previewBox = document.createElement('div');
            previewBox.className = 'preview-box animate-up';
            previewBox.innerHTML = `
                <img src="${e.target.result}">
                <button type="button" class="preview-remove" onclick="removeGalleryPhoto(${index})"><i class="fas fa-times"></i></button>
            `;
            grid.appendChild(previewBox);
        }
        reader.readAsDataURL(file);
    });
}

function removeExistingGalleryPhoto(index) {
    const removedItem = existingGalleryUrls.splice(index, 1)[0];
    deletedGalleryIds.push(removedItem.id);
    renderGalleryPreviews();
}

async function submitPortfolio(e) {
    e.preventDefault();
    
    const form = document.getElementById('portfolioForm');
    if (!isPortfolioFormValid()) {
        form.reportValidity();
        if (!hasExistingCoverPhoto && !coverPhotoFile) {
            alert("A cover photo is required.");
        }
        return;
    }
    
    const submitBtn = document.getElementById('submitPortfolioBtn');
    portfolioSaving = true;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    
    const formData = new FormData();
    formData.append('title', form.title.value);
    const selectedEventType = document.getElementById('portfolioEventTypeInput').value;
    const customEventType = document.getElementById('portfolioCustomEventTypeInput').value.trim();
    formData.append('event_type', selectedEventType === 'Other' ? customEventType : selectedEventType);
    formData.append('description', form.description.value);
    
    if (form.location && form.location.value) formData.append('location', form.location.value);
    if (form.booking_id && form.booking_id.value) formData.append('booking_id', form.booking_id.value);
    
    // Add is_featured checkbox
    const isFeatured = form.querySelector('input[name="is_featured"]').checked;
    formData.append('is_featured', isFeatured);
    
    // Process Highlights from Tagify
    if (highlightsTagify && highlightsTagify.value.length > 0) {
        const highlightsStr = highlightsTagify.value.map(t => t.value).join(',');
        formData.append('highlights', highlightsStr);
    }
    
    if (coverPhotoFile) formData.append('cover_photo', coverPhotoFile);
    
    galleryFiles.forEach(file => {
        formData.append('additional_photos', file);
    });
    
    if (deletedGalleryIds.length > 0) {
        formData.append('deleted_photos', deletedGalleryIds.join(','));
    }
    
    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            window.location.reload();
        } else {
            alert(result.detail || "An error occurred while saving the portfolio.");
        }
    } catch (error) {
        console.error("Error:", error);
        alert("A network error occurred. Please try again.");
    } finally {
        portfolioSaving = false;
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Save Portfolio';
        updatePortfolioSubmitState();
    }
}

async function archivePortfolio(id) {
    if (!confirm("Are you sure you want to archive this portfolio entry? It will be moved to the archives page.")) return;
    
    try {
        const response = await fetch(`/caterer/portfolio/${id}`, { method: 'DELETE' });
        const result = await response.json();
        if (response.ok) {
            document.getElementById(`portfolio-${id}`).remove();
        } else {
            alert(result.detail || "Error archiving portfolio.");
        }
    } catch(e) {
        alert("Network error.");
    }
}

function editPortfolio(btn) {
    const id = btn.dataset.id;
    const title = btn.dataset.title;
    const eventType = btn.dataset.eventType;
    const description = btn.dataset.description;
    const location = btn.dataset.location;
    const eventDate = btn.dataset.eventDate;
    const highlights = btn.dataset.highlights;
    const bookingId = btn.dataset.bookingId;
    const isFeatured = btn.dataset.isFeatured === 'true';
    const coverUrl = btn.dataset.coverUrl;
    
    existingGalleryUrls = [];
    deletedGalleryIds = [];
    const card = btn.closest('.portfolio-card');
    if (card) {
        const hiddenGallery = card.querySelector('.hidden-gallery-data');
        if (hiddenGallery) {
            const imgs = hiddenGallery.querySelectorAll('img');
            imgs.forEach(img => {
                if (img.src) existingGalleryUrls.push({ id: img.dataset.id, url: img.src });
            });
        }
    }

    const form = document.getElementById('portfolioForm');
    form.action = `/caterer/portfolio/${id}/update`;
    document.getElementById('portfolioIdInput').value = id;
    
    form.title.value = title;
    const eventTypeSelect = document.getElementById('portfolioEventTypeInput');
    const customEventTypeInput = document.getElementById('portfolioCustomEventTypeInput');
    const predefinedEventType = Array.from(eventTypeSelect.options).some(option => option.value === eventType && option.value !== 'Other');
    eventTypeSelect.value = predefinedEventType ? eventType : 'Other';
    customEventTypeInput.value = predefinedEventType ? '' : eventType;
    togglePortfolioCustomEventType();
    form.description.value = description;
    if (form.location) form.location.value = location;
    if (form.booking_id) form.booking_id.value = bookingId;
    form.querySelector('input[name="is_featured"]').checked = isFeatured;

    if (highlightsTagify) {
        highlightsTagify.removeAllTags();
        if (highlights) {
            highlightsTagify.addTags(highlights.split(','));
        }
    }

    // Display cover photo if it exists
    if (coverUrl) {
        hasExistingCoverPhoto = true;
        document.getElementById('coverImg').src = coverUrl;
        document.getElementById('coverImg').style.display = 'block';
        document.getElementById('coverPlaceholder').style.display = 'none';
    } else {
        hasExistingCoverPhoto = false;
        document.getElementById('coverImg').style.display = 'none';
        document.getElementById('coverPlaceholder').style.display = 'flex';
    }

    // Display gallery photos
    renderGalleryPreviews();

    document.querySelector('#portfolioModal .occ-modal-title').innerText = 'Edit Portfolio Entry';
    document.getElementById('portfolioModal').classList.add('active');
    document.body.style.overflow = 'hidden';
    updatePortfolioSubmitState();
}

function filterPortfolios(query) {
    const q = (query || '').toLowerCase().trim();
    const cards = document.querySelectorAll('.portfolio-card');
    let visibleCount = 0;

    cards.forEach(card => {
        const title = (card.querySelector('.portfolio-title')?.innerText || '').toLowerCase();
        const type = (card.querySelector('.portfolio-type')?.innerText || '').toLowerCase();
        const desc = (card.querySelector('.portfolio-desc')?.innerText || '').toLowerCase();
        const meta = (card.querySelector('.portfolio-meta')?.innerText || '').toLowerCase();

        if (!q || title.includes(q) || type.includes(q) || desc.includes(q) || meta.includes(q)) {
            card.style.display = '';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });

    let emptySearch = document.getElementById('portfolioSearchEmpty');
    const grid = document.querySelector('.portfolio-grid');
    if (cards.length > 0 && grid) {
        if (visibleCount === 0 && q) {
            if (!emptySearch) {
                emptySearch = document.createElement('div');
                emptySearch.id = 'portfolioSearchEmpty';
                emptySearch.className = 'packages-empty-pro text-center py-5';
                emptySearch.style.gridColumn = '1 / -1';
                emptySearch.style.background = 'white';
                emptySearch.style.borderRadius = 'var(--border-radius, 1.5rem)';
                emptySearch.style.border = '2px dashed #e2e8f0';
                emptySearch.style.marginTop = '1rem';
                emptySearch.innerHTML = `
                    <div style="font-size: 2.5rem; color: #94a3b8; margin-bottom: 0.5rem;"><i class="fas fa-search"></i></div>
                    <h3 style="color: #1e293b; font-weight: 700;">No matching portfolio items</h3>
                    <p style="color: #64748b; font-size: 0.9rem;">No results found for "${q}".</p>
                `;
                grid.appendChild(emptySearch);
            } else {
                emptySearch.style.display = 'block';
                emptySearch.querySelector('p').innerText = `No results found for "${q}".`;
            }
        } else if (emptySearch) {
            emptySearch.style.display = 'none';
        }
    }
}

// Listen to header globalSearch event
window.addEventListener('globalSearch', function(e) {
    filterPortfolios(e.detail ? e.detail.value : '');
});

async function togglePortfolioVisibility(id) {
    try {
        const response = await fetch(`/caterer/portfolio/${id}/toggle-visibility`, { method: 'POST' });
        if (response.ok) {
            window.location.reload();
        }
    } catch(e) {
        alert("Network error.");
    }
}

async function togglePortfolioFeature(id) {
    try {
        const response = await fetch(`/caterer/portfolio/${id}/toggle-feature`, { method: 'POST' });
        if (response.ok) {
            window.location.reload();
        }
    } catch(e) {
        alert("Network error.");
    }
}
