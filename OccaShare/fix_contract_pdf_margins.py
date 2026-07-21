import re

filepath = r'c:\OccaServe\OccaShare\templates\shared\contract_content_partial.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_js = """
<script>
    function downloadContractPDF() {
        const originalElement = document.querySelector('.contract-paper');
        const parentContainer = document.querySelector('.contract-paper-container');
        const refNo = "{% if booking.document_type == 'invoice' %}ORD-{% else %}BK-{% endif %}{{ booking.id }}";
        
        // Show loading state
        const btn = document.querySelector('.pdf-action-bar button');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating PDF...';
        btn.disabled = true;

        // Save original styles
        const originalWidth = originalElement.style.width;
        const originalMaxWidth = originalElement.style.maxWidth;
        const originalMargin = originalElement.style.margin;
        const originalPadding = originalElement.style.padding;
        const originalBoxShadow = originalElement.style.boxShadow;
        
        const originalParentDisplay = parentContainer ? parentContainer.style.display : '';
        const originalParentPadding = parentContainer ? parentContainer.style.padding : '';
        const originalParentJustify = parentContainer ? parentContainer.style.justifyContent : '';
        
        // Lock parent container to top-left to avoid window-offset bugs in html2canvas
        if(parentContainer) {
            parentContainer.style.display = 'block';
            parentContainer.style.padding = '0';
            parentContainer.style.justifyContent = 'flex-start';
        }
        
        // Remove padding so PDF margins are perfectly handled by jsPDF alone (1 inch)
        // Set width to a fixed 800px so it scales perfectly on Letter size
        originalElement.style.width = '800px';
        originalElement.style.maxWidth = '800px';
        originalElement.style.margin = '0';
        originalElement.style.padding = '0'; // Remove double-margin
        originalElement.style.boxShadow = 'none';

        // 1 inch = 96 pixels at standard resolution. We want EXACTLY 1 inch margin all around.
        const opt = {
            margin:       1, // Exactly 1 inch on all sides (Top, Left, Bottom, Right)
            filename:     `OccaServe_${refNo}_Document.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            pagebreak:    { mode: ['css', 'legacy'] }, // Prevent cutting elements
            html2canvas:  { 
                scale: 2, 
                useCORS: true, 
                logging: false,
                letterRendering: true,
                windowWidth: 800
            },
            jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
        };

        html2pdf().set(opt).from(originalElement).save().then(() => {
            // Restore original styles
            originalElement.style.width = originalWidth;
            originalElement.style.maxWidth = originalMaxWidth;
            originalElement.style.margin = originalMargin;
            originalElement.style.padding = originalPadding;
            originalElement.style.boxShadow = originalBoxShadow;
            
            if(parentContainer) {
                parentContainer.style.display = originalParentDisplay;
                parentContainer.style.padding = originalParentPadding;
                parentContainer.style.justifyContent = originalParentJustify;
            }
            
            btn.innerHTML = originalText;
            btn.disabled = false;
        }).catch(err => {
            console.error("PDF Generation Error:", err);
            originalElement.style.width = originalWidth;
            originalElement.style.maxWidth = originalMaxWidth;
            originalElement.style.margin = originalMargin;
            originalElement.style.padding = originalPadding;
            originalElement.style.boxShadow = originalBoxShadow;
            
            if(parentContainer) {
                parentContainer.style.display = originalParentDisplay;
                parentContainer.style.padding = originalParentPadding;
                parentContainer.style.justifyContent = originalParentJustify;
            }
            
            btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
            btn.disabled = false;
        });
    }
</script>
"""

content = re.sub(r'<script>\s*function downloadContractPDF\(\).*?</script>', new_js, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated Contract PDF margins to 1 inch!")
