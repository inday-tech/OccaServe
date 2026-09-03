with open('app/static/css/caterer/calendar.css', 'r', encoding='utf-8') as f:
    content = f.read()

modal_css = '''
/* ==== Modal Overlay (used for addScheduleModal, etc.) ==== */
.modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 9999;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 1rem;
}

.modal-overlay.active,
.modal-overlay[style*="flex"] {
    display: flex !important;
}

.modal-content {
    background: #fff;
    border-radius: 16px;
    width: 100%;
    max-width: 520px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
    overflow: hidden;
    animation: modalPop 0.25s ease;
}

@keyframes modalPop {
    from { transform: scale(0.9); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.25rem 1.5rem;
    border-bottom: 1px solid #e2e8f0;
    background: #f8fafc;
}

.modal-header h3 {
    font-size: 1.1rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0;
}

.modal-close {
    background: none;
    border: none;
    color: #64748b;
    font-size: 1.1rem;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 6px;
    transition: background 0.2s;
}
.modal-close:hover {
    background: #f1f5f9;
    color: #0f172a;
}

/* ==== Availability Settings Modal ==== */
#availabilitySettingsModal .modal-content {
    max-width: 550px;
}
'''

if '.modal-overlay' not in content:
    content += '\n' + modal_css

with open('app/static/css/caterer/calendar.css', 'w', encoding='utf-8') as f:
    f.write(content)
print("Added modal CSS")
