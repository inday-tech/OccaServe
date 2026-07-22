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

        // Temporarily modify the original element AND its parent to strip any offsets/margins
        // html2canvas captures based on viewport offset, so centering in DOM causes left-margin in PDF.
        const originalWidth = originalElement.style.width;
        const originalMargin = originalElement.style.margin;
        const originalBoxShadow = originalElement.style.boxShadow;
        
        const originalParentDisplay = parentContainer ? parentContainer.style.display : '';
        const originalParentPadding = parentContainer ? parentContainer.style.padding : '';
        const originalParentJustify = parentContainer ? parentContainer.style.justifyContent : '';
        
        if(parentContainer) {
            parentContainer.style.display = 'block';
            parentContainer.style.padding = '0';
            parentContainer.style.justifyContent = 'flex-start';
        }
        
        // Force fixed width for A4/Letter size translation and remove margins
        originalElement.style.width = '800px';
        originalElement.style.margin = '0';
        originalElement.style.boxShadow = 'none';

        const opt = {
            margin:       [0.5, 0.5, 0.5, 0.5], // Top, Left, Bottom, Right
            filename:     `OccaServe_${refNo}_Document.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            pagebreak:    { mode: ['css', 'legacy'] },
            html2canvas:  { 
                scale: 2, 
                useCORS: true, 
                logging: false,
                letterRendering: true,
                windowWidth: 800 // explicitly constrain html2canvas bounds
            },
            jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
        };

        html2pdf().set(opt).from(originalElement).save().then(() => {
            // Restore original styles
            originalElement.style.width = originalWidth;
            originalElement.style.margin = originalMargin;
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
            originalElement.style.margin = originalMargin;
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

print("Updated Contract PDF alignment logic!")
