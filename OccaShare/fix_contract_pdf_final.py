import re

filepath = r'c:\OccaServe\OccaShare\templates\shared\contract_content_partial.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace watermark CSS to remove position: absolute which causes html2canvas page break bugs
watermark_css_old = r"""    \.verified-seal-watermark \{
        position: absolute;
        bottom: 40px;
        right: 40px;"""

watermark_css_new = """    .verified-seal-watermark {
        float: right;
        margin-top: -120px;
        margin-right: 20px;"""

content = re.sub(watermark_css_old, watermark_css_new, content)

# Replace the downloadContractPDF function
new_js = """
<script>
    function downloadContractPDF() {
        const originalElement = document.querySelector('.contract-paper');
        const refNo = "{% if booking.document_type == 'invoice' %}ORD-{% else %}BK-{% endif %}{{ booking.id }}";
        
        const btn = document.querySelector('.pdf-action-bar button');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating PDF...';
        btn.disabled = true;

        // Save original DOM state
        const parent = originalElement.parentNode;
        const nextSibling = originalElement.nextSibling;
        const oldPos = originalElement.style.position;
        const oldTop = originalElement.style.top;
        const oldLeft = originalElement.style.left;
        const oldMargin = originalElement.style.margin;
        const oldZIndex = originalElement.style.zIndex;
        const oldPadding = originalElement.style.padding;
        const oldWidth = originalElement.style.width;

        // Move to body to completely escape any scrolling offsets, navbar offsets, or flexbox layouts!
        document.body.appendChild(originalElement);
        
        // Force to top-left of the document. No overlay! It will flash for 150ms but guarantees 100% render.
        originalElement.style.position = 'absolute';
        originalElement.style.top = '0';
        originalElement.style.left = '0';
        originalElement.style.margin = '0';
        originalElement.style.padding = '48px'; // Exactly 0.5 inches margin
        originalElement.style.width = '816px'; // A4 Width
        originalElement.style.zIndex = '9999999'; 

        // Wait 150ms for the browser to paint the new DOM location and load signature images
        setTimeout(() => {
            const opt = {
                margin:       0, // We handle margin via the 48px padding for perfect stability
                filename:     `OccaServe_${refNo}_Document.pdf`,
                image:        { type: 'jpeg', quality: 0.98 },
                pagebreak:    { mode: ['css', 'legacy'] }, // Prevents cutting elements in half
                html2canvas:  { 
                    scale: 2, 
                    useCORS: true, 
                    allowTaint: true, // Fixes missing signatures if they are tainted
                    logging: false,
                    letterRendering: true
                },
                jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
            };

            html2pdf().set(opt).from(originalElement).save().then(() => {
                // Restore original state
                originalElement.style.position = oldPos;
                originalElement.style.top = oldTop;
                originalElement.style.left = oldLeft;
                originalElement.style.margin = oldMargin;
                originalElement.style.padding = oldPadding;
                originalElement.style.width = oldWidth;
                originalElement.style.zIndex = oldZIndex;
                
                if (nextSibling) {
                    parent.insertBefore(originalElement, nextSibling);
                } else {
                    parent.appendChild(originalElement);
                }
                
                btn.innerHTML = originalText;
                btn.disabled = false;
            }).catch(err => {
                console.error("PDF Generation Error:", err);
                originalElement.style.position = oldPos;
                originalElement.style.top = oldTop;
                originalElement.style.left = oldLeft;
                originalElement.style.margin = oldMargin;
                originalElement.style.padding = oldPadding;
                originalElement.style.width = oldWidth;
                originalElement.style.zIndex = oldZIndex;
                if (nextSibling) parent.insertBefore(originalElement, nextSibling);
                else parent.appendChild(originalElement);
                
                btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
                btn.disabled = false;
            });
        }, 150);
    }
</script>
"""

content = re.sub(r'<script>\s*function downloadContractPDF\(\).*?</script>', new_js, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied watermark and exact DOM alignment fixes!")
