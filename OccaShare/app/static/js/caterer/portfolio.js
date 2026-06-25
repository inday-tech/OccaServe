// caterer/portfolio.js

let coverPhotoFile = null;
let galleryFiles = [];
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

async function submitPortfolio(e) {
    e.preventDefault();
    
    if (!coverPhotoFile) {
        alert("A cover photo is required.");
        return;
    }
    
    const form = document.getElementById('portfolioForm');
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
    
    formData.append('cover_photo', coverPhotoFile);
    
    galleryFiles.forEach(file => {
        formData.append('additional_photos', file);
    });
    
    try {
        const response = await fetch('/caterer/portfolio/create', {
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

async function deletePortfolio(id) {
    if (!confirm("Are you sure you want to delete this portfolio entry? This cannot be undone.")) return;
    
    try {
        const response = await fetch(`/caterer/portfolio/${id}`, { method: 'DELETE' });
        const result = await response.json();
        if (response.ok) {
            document.getElementById(`portfolio-${id}`).remove();
        } else {
            alert(result.detail || "Error deleting portfolio.");
        }
    } catch(e) {
        alert("Network error.");
    }
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
