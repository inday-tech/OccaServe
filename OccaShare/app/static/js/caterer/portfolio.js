// caterer/portfolio.js

let coverPhotoFile = null;
let galleryFiles = [];
let existingGalleryUrls = [];
let deletedGalleryIds = [];
let highlightsTagify = null;

document.addEventListener("DOMContentLoaded", () => {
    // Initialize Tagify for highlights
    const highlightsInput = document.getElementById('highlightsInput');
    if (highlightsInput) {
        highlightsTagify = new Tagify(highlightsInput, {
            maxTags: 8,
            dropdown: {
                maxItems: 20,
                classname: "tags-look",
                enabled: 0,
                closeOnSelect: false
            }
        });
    }
});

function openPortfolioModal() {
    const form = document.getElementById('portfolioForm');
    form.action = '/caterer/portfolio/create';
    document.getElementById('portfolioIdInput').value = '';
    document.querySelector('#portfolioModal .occ-modal-title').innerText = 'Add Portfolio Entry';
    document.getElementById('portfolioModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closePortfolioModal() {
    document.getElementById('portfolioModal').classList.remove('active');
    document.body.style.overflow = '';
    
    // Reset Form
    document.getElementById('portfolioForm').reset();
    if(highlightsTagify) highlightsTagify.removeAllTags();
    
    // Reset previews
    coverPhotoFile = null;
    document.getElementById('coverImg').style.display = 'none';
    document.getElementById('coverImg').src = '';
    document.getElementById('coverPlaceholder').style.display = 'flex';
    
    galleryFiles = [];
    existingGalleryUrls = [];
    deletedGalleryIds = [];
    renderGalleryPreviews();
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
    const isEdit = form.action.includes('/update');
    
    if (!isEdit && !coverPhotoFile) {
        alert("A cover photo is required.");
        return;
    }
    
    const submitBtn = document.getElementById('submitPortfolioBtn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    
    const formData = new FormData();
    formData.append('title', form.title.value);
    formData.append('event_type', form.event_type.value);
    formData.append('description', form.description.value);
    
    if (form.location.value) formData.append('location', form.location.value);
    if (form.event_date.value) formData.append('event_date', form.event_date.value);
    if (form.booking_id.value) formData.append('booking_id', form.booking_id.value);
    
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
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Save Portfolio';
        }
    } catch (error) {
        console.error("Error:", error);
        alert("A network error occurred. Please try again.");
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Save Portfolio';
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
    form.event_type.value = eventType;
    form.description.value = description;
    form.location.value = location;
    form.event_date.value = eventDate;
    form.booking_id.value = bookingId;
    form.querySelector('input[name="is_featured"]').checked = isFeatured;

    if (highlightsTagify) {
        highlightsTagify.removeAllTags();
        if (highlights) {
            highlightsTagify.addTags(highlights.split(','));
        }
    }

    // Display cover photo if it exists
    if (coverUrl) {
        document.getElementById('coverImg').src = coverUrl;
        document.getElementById('coverImg').style.display = 'block';
        document.getElementById('coverPlaceholder').style.display = 'none';
    } else {
        document.getElementById('coverImg').style.display = 'none';
        document.getElementById('coverPlaceholder').style.display = 'flex';
    }

    // Display gallery photos
    renderGalleryPreviews();

    document.querySelector('#portfolioModal .occ-modal-title').innerText = 'Edit Portfolio Entry';
    document.getElementById('portfolioModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

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
