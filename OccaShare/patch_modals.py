import re

modal_css = """
    /* Modal Polyfill */
    .occ-modal-overlay {
        display: none;
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(15, 23, 42, 0.4) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px);
        z-index: 9999;
        align-items: center;
        justify-content: center;
        padding: 1rem;
    }
    .occ-modal-overlay.active {
        display: flex !important;
    }
    .occ-modal-box {
        background: white;
        border-radius: 1.25rem;
        width: 100%;
        max-width: 500px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        animation: modalSlideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        overflow: hidden;
    }
    .occ-modal-header {
        padding: 1.5rem;
        border-bottom: 1px solid #f1f5f9;
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        background: white;
    }
    .occ-modal-title { font-size: 1.25rem; font-weight: 800; margin: 0 0 0.25rem 0; color: #0f172a; }
    .occ-modal-subtitle { font-size: 0.85rem; color: #94a3b8; font-weight: 500; }
    .occ-modal-close { background: none; border: none; font-size: 1.25rem; color: #94a3b8; cursor: pointer; transition: color 0.2s; padding: 0; }
    .occ-modal-close:hover { color: #ef4444; }
    .occ-modal-body { padding: 1.5rem; background: white; }
    .occ-form-grid { display: flex; flex-direction: column; gap: 1.25rem; }
    .occ-form-label { font-size: 0.75rem; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; display: block; }
    .occ-form-input { width: 100%; padding: 0.85rem 1rem; border: 1.5px solid #e2e8f0; border-radius: 0.75rem; font-size: 0.95rem; font-family: 'Poppins', sans-serif; transition: all 0.3s; background: white; color: #0f172a;}
    .occ-form-input:focus { outline: none; border-color: #f97316; box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.1); }
    .occ-modal-footer { padding: 1.25rem 1.5rem; border-top: 1px solid #f1f5f9; display: flex; justify-content: flex-end; gap: 1rem; background: #f8fafc; }
    
    @keyframes modalSlideUp {
        from { transform: translateY(20px) scale(0.95); opacity: 0; }
        to { transform: translateY(0) scale(1); opacity: 1; }
    }
"""

def inject_css(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Inject before </style> in extra_css block
    if '</style>' in content:
        content = content.replace('</style>', modal_css + '\n</style>', 1)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

inject_css('templates/customer/profile.html')
inject_css('templates/admin/settings.html')
print("CSS injected successfully")
