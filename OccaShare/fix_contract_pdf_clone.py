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

        // Ensure html2canvas captures perfectly by creating a fixed overlay
        const wrapper = document.createElement('div');
        wrapper.style.position = 'fixed';
        wrapper.style.top = '0';
        wrapper.style.left = '0';
        wrapper.style.width = '816px'; // A4/Letter perfect width (8.5 inches at 96 DPI)
        wrapper.style.zIndex = '999999';
        wrapper.style.background = '#fff';
        wrapper.style.overflow = 'hidden';
        
        // Clone the document so we don't mess up the screen layout
        const clonedElement = originalElement.cloneNode(true);
        clonedElement.style.width = '100%';
        clonedElement.style.maxWidth = '100%';
        clonedElement.style.boxShadow = 'none';
        clonedElement.style.border = 'none';
        clonedElement.style.margin = '0';
        // DO NOT remove padding. Keep padding intact, but use a precise jsPDF margin!
        // We will just let html2pdf render the element as-is, but we configure it to have a perfect 0.5 inch margin in PDF.
        // But wait! If we leave the 60px padding, the PDF margin (0.5 inch = 48px) + 60px padding = huge space!
        // So we REDUCE the padding on the clone to just 10px so the layout doesn't break, and set PDF margin to 0.5 inches.
        clonedElement.style.padding = '10px 10px';
        
        wrapper.appendChild(clonedElement);
        document.body.appendChild(wrapper);

        const opt = {
            margin:       0.5, // EXACTLY 0.5 inches on Top, Left, Bottom, Right
            filename:     `OccaServe_${refNo}_Document.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            pagebreak:    { mode: ['css', 'legacy'] }, 
            html2canvas:  { 
                scale: 2, 
                useCORS: true, 
                logging: false,
                letterRendering: true,
                windowWidth: 816 // Explicitly lock canvas bounds to the wrapper
            },
            jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
        };

        html2pdf().set(opt).from(wrapper).save().then(() => {
            document.body.removeChild(wrapper);
            btn.innerHTML = originalText;
            btn.disabled = false;
        }).catch(err => {
            console.error("PDF Generation Error:", err);
            if (document.body.contains(wrapper)) document.body.removeChild(wrapper);
            btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
            btn.disabled = false;
        });
    }
</script>
"""

content = re.sub(r'<script>\s*function downloadContractPDF\(\).*?</script>', new_js, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated Contract PDF logic with isolated clone approach!")
