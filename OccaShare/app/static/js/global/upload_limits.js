document.addEventListener('change', event => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || input.type !== 'file') return;

    const maxSizeMb = Number(window.MAX_UPLOAD_SIZE_MB) || 5;
    const maxSizeBytes = maxSizeMb * 1024 * 1024;
    const oversizedFile = Array.from(input.files || []).find(file => file.size > maxSizeBytes);
    if (!oversizedFile) return;

    window.alert(`${oversizedFile.name} exceeds the maximum upload file size of ${maxSizeMb} MB.`);
    input.value = '';
}, true);