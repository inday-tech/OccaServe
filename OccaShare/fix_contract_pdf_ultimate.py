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
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Preparing...';
        btn.disabled = true;

        // 1. Create a beautiful full-screen loading overlay to hide the DOM manipulation
        const overlay = document.createElement('div');
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100vw';
        overlay.style.height = '100vh';
        overlay.style.background = '#f8fafc';
        overlay.style.zIndex = '9999999';
        overlay.style.display = 'flex';
        overlay.style.flexDirection = 'column';
        overlay.style.alignItems = 'center';
        overlay.style.justifyContent = 'center';
        overlay.innerHTML = '<i class="fas fa-file-pdf fa-3x" style="color:#ef4444; margin-bottom:1rem;"></i><h3 style="font-family:Poppins,sans-serif;color:#0f172a; margin:0;">Generating Official PDF</h3><p style="font-family:Poppins,sans-serif;color:#64748b; font-size:0.85rem;">Please wait a moment...</p>';
        document.body.appendChild(overlay);

        // 2. Save original DOM state
        const parent = originalElement.parentNode;
        const nextSibling = originalElement.nextSibling;
        const oldPos = originalElement.style.position;
        const oldTop = originalElement.style.top;
        const oldLeft = originalElement.style.left;
        const oldMargin = originalElement.style.margin;
        const oldZIndex = originalElement.style.zIndex;

        // 3. Move element directly to body to ESCAPE the sidebar and grid layouts!
        document.body.appendChild(originalElement);
        
        // 4. Force it to exact 0,0 coordinates so html2canvas captures it perfectly centered
        originalElement.style.position = 'absolute';
        originalElement.style.top = '0';
        originalElement.style.left = '0';
        originalElement.style.margin = '0';
        originalElement.style.zIndex = '9999998'; // Behind the overlay

        // 5. Allow browser 100ms to repaint the DOM in its new location before capturing
        setTimeout(() => {
            const opt = {
                margin:       0.5, // Exactly 0.5 inches on all sides!
                filename:     `OccaServe_${refNo}_Document.pdf`,
                image:        { type: 'jpeg', quality: 0.98 },
                pagebreak:    { mode: ['css', 'legacy'] },
                html2canvas:  { 
                    scale: 2, 
                    useCORS: true, 
                    logging: false,
                    letterRendering: true,
                    // We don't need x/y crop anymore because it's guaranteed at 0,0
                },
                jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
            };

            html2pdf().set(opt).from(originalElement).save().then(() => {
                // 6. Restore everything exactly as it was
                originalElement.style.position = oldPos;
                originalElement.style.top = oldTop;
                originalElement.style.left = oldLeft;
                originalElement.style.margin = oldMargin;
                originalElement.style.zIndex = oldZIndex;
                
                if (nextSibling) {
                    parent.insertBefore(originalElement, nextSibling);
                } else {
                    parent.appendChild(originalElement);
                }
                
                document.body.removeChild(overlay);
                btn.innerHTML = originalText;
                btn.disabled = false;
            }).catch(err => {
                console.error("PDF Generation Error:", err);
                // Restore on error too
                originalElement.style.position = oldPos;
                originalElement.style.top = oldTop;
                originalElement.style.left = oldLeft;
                originalElement.style.margin = oldMargin;
                originalElement.style.zIndex = oldZIndex;
                if (nextSibling) parent.insertBefore(originalElement, nextSibling);
                else parent.appendChild(originalElement);
                
                document.body.removeChild(overlay);
                btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
                btn.disabled = false;
            });
        }, 150); // 150ms delay for flawless rendering
    }
</script>
"""

content = re.sub(r'<script>\s*function downloadContractPDF\(\).*?</script>', new_js, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied Ultimate PDF Fix!")
