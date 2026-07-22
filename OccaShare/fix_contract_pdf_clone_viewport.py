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

        // 1. Create a flawless clone of the contract
        const clonedElement = originalElement.cloneNode(true);
        
        // 2. Position it exactly on the current screen so html2canvas doesn't think it's invisible/off-screen!
        // This was the main cause of the "blank page" bugs!
        clonedElement.style.position = 'absolute';
        clonedElement.style.top = window.scrollY + 'px'; // Start exactly where the user is looking
        clonedElement.style.left = '0'; // Snap to the far left to avoid sidebar offset bugs!
        clonedElement.style.width = '816px'; // Perfect A4 Width
        clonedElement.style.maxWidth = '816px';
        clonedElement.style.margin = '0';
        clonedElement.style.padding = '48px'; // EXACTLY 0.5 inch margins!
        clonedElement.style.boxShadow = 'none';
        clonedElement.style.zIndex = '999999'; // Put it on top so it doesn't get covered by anything
        clonedElement.style.backgroundColor = '#ffffff';

        // Add to document
        document.body.appendChild(clonedElement);

        // Allow 200ms for images (signatures) inside the clone to fully render and layout to settle
        setTimeout(() => {
            const opt = {
                margin:       0, // Margin is handled perfectly by the 48px padding
                filename:     `OccaServe_${refNo}_Document.pdf`,
                image:        { type: 'jpeg', quality: 0.98 },
                pagebreak:    { mode: ['css', 'legacy'] },
                html2canvas:  { 
                    scale: 2, 
                    useCORS: true, // Fixes missing signatures!
                    logging: false,
                    letterRendering: true
                },
                jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
            };

            html2pdf().set(opt).from(clonedElement).save().then(() => {
                // Remove the clone once done
                document.body.removeChild(clonedElement);
                btn.innerHTML = originalText;
                btn.disabled = false;
            }).catch(err => {
                console.error("PDF Generation Error:", err);
                if(document.body.contains(clonedElement)) {
                    document.body.removeChild(clonedElement);
                }
                btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
                btn.disabled = false;
            });
        }, 200);
    }
</script>
"""

content = re.sub(r'<script>\s*function downloadContractPDF\(\).*?</script>', new_js, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied foolproof viewport cloning PDF fix!")
