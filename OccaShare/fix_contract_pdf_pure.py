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

        // Scroll to top to prevent html2canvas scroll offset bugs
        window.scrollTo(0, 0);

        // Save original styling
        const originalPadding = originalElement.style.padding;
        const originalWidth = originalElement.style.width;
        const originalMaxWidth = originalElement.style.maxWidth;
        const originalBoxShadow = originalElement.style.boxShadow;

        // 1. Fix Margin to 0.5 inch: 
        // Instead of breaking the layout by removing padding, we SET the padding to exactly 0.5 inches (48px).
        // This ensures the internal text doesn't touch the borders and remains beautifully formatted!
        originalElement.style.padding = '48px';
        
        // 2. Lock the element width for perfect A4 scaling
        originalElement.style.width = '816px'; // 8.5 inches at 96 DPI
        originalElement.style.maxWidth = '816px';
        originalElement.style.boxShadow = 'none';

        const opt = {
            margin:       0, // We handle the margin entirely through the 48px padding!
            filename:     `OccaServe_${refNo}_Document.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            pagebreak:    { mode: ['css', 'legacy'] },
            html2canvas:  { 
                scale: 2, 
                useCORS: true, 
                logging: false,
                letterRendering: true
                // CRITICAL: NO windowWidth, NO x/y cropping! 
                // html2pdf automatically captures the exact bounding box of originalElement.
                // Forcing windowWidth is what caused the sidebar to get captured and the text to cut off!
            },
            jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
        };

        html2pdf().set(opt).from(originalElement).save().then(() => {
            // Restore immediately after capture
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
    }
</script>
"""

content = re.sub(r'<script>\s*function downloadContractPDF\(\).*?</script>', new_js, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied pure html2pdf fix!")
