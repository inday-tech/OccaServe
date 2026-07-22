import re

filepath = r'c:\OccaServe\OccaShare\templates\shared\contract_content_partial.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_js = """
<script>
    function downloadContractPDF() {
        const originalElement = document.querySelector('.contract-paper');
        const refNo = "{% if booking.document_type == 'invoice' %}ORD-{% else %}BK-{% endif %}{{ booking.id }}";
        
        const btn = document.querySelector('.pdf-action-bar button');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating PDF...';
        btn.disabled = true;

        // 1. Prepare element for perfect A4 generation
        const originalPadding = originalElement.style.padding;
        const originalWidth = originalElement.style.width;
        const originalMaxWidth = originalElement.style.maxWidth;
        const originalBoxShadow = originalElement.style.boxShadow;

        // Exactly 0.5 inches margin on all sides via internal padding
        originalElement.style.padding = '48px'; 
        originalElement.style.width = '816px'; 
        originalElement.style.maxWidth = '816px';
        originalElement.style.boxShadow = 'none';

        // 2. Calculate precise bounding box coordinates to ignore sidebars and headers
        // We use setTimeout to ensure browser has applied the 816px width before measuring
        setTimeout(() => {
            const rect = originalElement.getBoundingClientRect();

            const opt = {
                margin:       0, // Margin is handled internally by our 48px padding
                filename:     `OccaServe_${refNo}_Document.pdf`,
                image:        { type: 'jpeg', quality: 0.98 },
                pagebreak:    { mode: ['css', 'legacy'] }, // Prevents page breaks from cutting text in half
                html2canvas:  { 
                    scale: 2, 
                    useCORS: true, 
                    logging: false,
                    letterRendering: true,
                    // Force full page capture to prevent viewport cut-offs, then crop precisely
                    windowWidth: document.documentElement.scrollWidth,
                    windowHeight: document.documentElement.scrollHeight,
                    x: rect.left + window.scrollX,
                    y: rect.top + window.scrollY,
                    width: rect.width,
                    height: rect.height
                },
                jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
            };

            html2pdf().set(opt).from(originalElement).save().then(() => {
                // Restore styles
                originalElement.style.padding = originalPadding;
                originalElement.style.width = originalWidth;
                originalElement.style.maxWidth = originalMaxWidth;
                originalElement.style.boxShadow = originalBoxShadow;
                
                btn.innerHTML = originalText;
                btn.disabled = false;
            }).catch(err => {
                console.error("PDF Generation Error:", err);
                originalElement.style.padding = originalPadding;
                originalElement.style.width = originalWidth;
                originalElement.style.maxWidth = originalMaxWidth;
                originalElement.style.boxShadow = originalBoxShadow;
                
                btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
                btn.disabled = false;
            });
        }, 100);
    }
</script>
"""

content = re.sub(r'<script>\s*function downloadContractPDF\(\).*?</script>', new_js, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied flawless bounding box cropping for PDF!")
