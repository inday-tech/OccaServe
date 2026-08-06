import sys

def replace_lines(filename, start_line, end_line, new_content):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    start_idx = start_line - 1
    end_idx = end_line
    
    new_lines = new_content.splitlines(True)
    if not new_lines[-1].endswith('\n'):
        new_lines[-1] += '\n'
        
    lines[start_idx:end_idx] = new_lines
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(lines)

new_content = r'''<style>
    /* ─── Clean Booking Modal ─── */
    #bookingDetailModal .modal-b-container {
        max-width: 900px !important;
        width: 100% !important;
        border-radius: 12px;
        overflow: hidden;
        background: #ffffff;
        display: flex !important;
        flex-direction: column !important;
        max-height: 90vh !important;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
        margin: auto;
    }
    #bookingDetailModal .exec-header {
        position: relative;
        background: #ffffff;
        padding: 1.5rem;
        border-bottom: 1px solid #e2e8f0;
        flex-shrink: 0;
    }
    #bookingDetailModal .btn-close-modal {
        position: absolute;
        top: 1.25rem;
        right: 1.5rem;
        background: #f1f5f9;
        border: none;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #64748b;
        cursor: pointer;
        transition: all 0.2s;
    }
    #bookingDetailModal .btn-close-modal:hover {
        background: #e2e8f0;
        color: #0f172a;
    }
    #bookingDetailModal h2#modalBookingId {
        color: #0f172a;
        font-weight: 700;
        font-size: 1.25rem;
        margin: 0;
    }
    #bookingDetailModal .exec-tabs {
        display: flex;
        background: #f8fafc;
        border-bottom: 1px solid #e2e8f0;
        padding: 0 1rem;
        gap: 1rem;
        overflow-x: auto;
        flex-shrink: 0;
        scrollbar-width: thin;
    }
    #bookingDetailModal .mtab-btn-pro {
        padding: 0.85rem 0.5rem;
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        color: #64748b;
        font-weight: 600;
        font-size: 0.85rem;
        cursor: pointer;
        white-space: nowrap;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    #bookingDetailModal .mtab-btn-pro.active {
        color: var(--primary-color, #0f172a);
        border-bottom-color: var(--primary-color, #0f172a);
        font-weight: 700;
    }
    #bookingDetailModal .mtab-pane-pro {
        display: none;
        padding: 1.5rem;
        overflow-y: auto;
        flex: 1;
        background: #ffffff;
    }
    #bookingDetailModal .mtab-pane-pro.active {
        display: block;
    }
    #bookingDetailModal .exec-card {
        background: #ffffff;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
    }
    #bookingDetailModal .exec-title {
        font-size: 0.85rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    #bookingDetailModal .exec-grid-2 {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.25rem;
        margin-bottom: 1.25rem;
    }
    #bookingDetailModal #actionCenterWrapper {
        background: #f8fafc;
        border-top: 1px solid #e2e8f0;
        padding: 1rem 1.5rem;
        flex-shrink: 0;
        width: 100%;
        box-sizing: border-box;
    }
    .info-label {
        font-size: 0.75rem;
        color: #64748b;
        margin-bottom: 0.25rem;
        font-weight: 600;
    }
    .info-value {
        font-size: 0.95rem;
        color: #0f172a;
        font-weight: 500;
    }
    #bookingDetailModal .btn-footer-action {
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        border: 1px solid transparent;
        white-space: nowrap;
    }
    #bookingDetailModal .btn-status-confirm, #bookingDetailModal .btn-status-complete {
        background: var(--primary-color, #0f172a) !important;
        color: white !important;
    }
    #bookingDetailModal .btn-status-reject {
        background: #fee2e2 !important;
        color: #991b1b !important;
        border-color: #fecaca !important;
    }
    
    @media (max-width: 768px) {
        #bookingDetailModal .exec-grid-2 {
            grid-template-columns: 1fr;
        }
        #bookingDetailModal .exec-header {
            padding-right: 3rem; /* Make room for close button */
        }
        #bookingDetailModal .exec-tabs {
            padding: 0 0.5rem;
        }
        #bookingDetailModal .mtab-pane-pro {
            padding: 1rem;
        }
    }
    @media (max-width: 480px) {
        #bookingDetailModal .modal-b-container {
            border-radius: 12px 12px 0 0 !important;
            max-height: 95vh !important;
            margin-bottom: 0 !important;
            margin-top: auto !important;
        }
    }
</style>

<div id="bookingDetailModal" class="occ-modal-overlay">
    <div class="occ-modal-box modal-b-container occ-content-pop" style="padding: 0;">
        <!-- Header -->
        <div class="exec-header">
            <button onclick="bk_closeBookingDetailModal()" class="btn-close-modal" title="Close">
                <i class="fas fa-times"></i>
            </button>
            
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1.25rem; padding-right: 2.5rem; width: 100%;">
                <!-- Left Details -->
                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                    <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
                        <h2 id="modalBookingId" style="color: #0f172a; font-weight: 800; font-size: 1.3rem; margin: 0; letter-spacing: -0.02em;">Booking Details</h2>
                        <span id="modalStatus" style="padding: 4px 10px; border-radius: 50px; font-weight: 700; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em;" class="badge-status"></span>
                    </div>
                    <div style="font-size: 0.8rem; color: #64748b; display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;">
                        <span><i class="far fa-calendar-alt" style="margin-right: 4px;"></i> Created: <span id="modalBookedOn" style="font-weight: 700; color: #334155;"></span></span>
                        <span id="modalPaymentMethod" style="background: #f1f5f9; padding: 2px 8px; border-radius: 4px; font-weight: 700; color: #475569;"></span>
                        <span id="modalPaymentRef" style="display: none; background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px; font-weight: 700;"></span>
                    </div>
                </div>
                
                <!-- Right Details -->
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 0.75rem 1.25rem; border-radius: 8px; text-align: right; min-width: 140px;">
                    <div style="font-size: 0.65rem; color: #64748b; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em;">Total Amount</div>
                    <div id="modalTotalAmount" style="font-size: 1.35rem; font-weight: 800; color: #0f172a; line-height: 1.2; margin: 2px 0;">₱0.00</div>
                    <div id="modalPaymentStatus" style="font-size: 0.75rem; font-weight: 700; color: #64748b;"></div>
                </div>
            </div>
        </div>

        <!-- Tabs -->
        <div class="exec-tabs">
            <button class="mtab-btn-pro active" onclick="switchBookingTab('overview', this)"><i class="fas fa-info-circle"></i> Overview</button>
            <button class="mtab-btn-pro" onclick="switchBookingTab('operations', this)"><i class="fas fa-clipboard-list"></i> Operations</button>
            <button class="mtab-btn-pro" onclick="switchBookingTab('financials', this)"><i class="fas fa-wallet"></i> Financials</button>
            <button class="mtab-btn-pro" onclick="switchBookingTab('chat', this)"><i class="far fa-comments"></i> Chat</button>
        </div>

        <!-- Hidden Compatibility Panes -->
        <div id="btab-tasks" style="display: none;"></div>
        <div id="btab-verification" style="display: none;"></div>
        <div id="btab-food" style="display: none;"></div>
        <div id="btab-service" style="display: none;"></div>
        <div id="btab-equipment" style="display: none;"></div>
        <div id="btab-docs" style="display: none;"></div>

        <!-- Content Area -->
        <div style="flex: 1; overflow-y: auto;">
            <!-- 1. OVERVIEW -->
            <div id="btab-overview" class="mtab-pane-pro active">
                <div id="completedProfitSummary" style="display: none; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 1rem; margin-bottom: 1.25rem;">
                    <div style="font-size: 0.85rem; font-weight: 700; color: #166534; margin-bottom: 0.75rem;">
                        <i class="fas fa-chart-line"></i> Post-Event ROI
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 1rem;">
                        <div><div class="info-label">Revenue</div><div id="psRevenue" class="info-value" style="color: #064e3b; font-weight: 700;">₱0.00</div></div>
                        <div><div class="info-label">COGS</div><div id="psCost" class="info-value" style="color: #dc2626; font-weight: 700;">₱0.00</div></div>
                        <div><div class="info-label">Profit</div><div id="psProfit" class="info-value" style="color: #16a34a; font-weight: 700;">₱0.00</div></div>
                        <div><div class="info-label">Margin</div><div id="psMargin" class="info-value" style="color: #1d4ed8; font-weight: 700;">0%</div></div>
                    </div>
                </div>

                <div class="booking-stepper-pro" style="padding: 1.25rem; margin-bottom: 1.25rem;">
                    <div class="stepper-track-pro"></div>
                    <div class="stepper-steps-pro">
                        <div class="step-pro" data-step="pending"><div class="step-dot">1</div><span class="step-label">Pending</span></div>
                        <div class="step-pro" data-step="confirmed"><div class="step-dot">2</div><span class="step-label">Confirmed</span></div>
                        <div class="step-pro" data-step="preparing"><div class="step-dot">3</div><span class="step-label">Preparing</span></div>
                        <div class="step-pro" data-step="on_the_way"><div class="step-dot">4</div><span class="step-label">Transit</span></div>
                        <div class="step-pro" data-step="in_progress" id="stepperStepOngoing"><div class="step-dot">5</div><span class="step-label">Ongoing</span></div>
                        <div class="step-pro" data-step="completed" id="stepperStepCompleted"><div class="step-dot" id="stepperStepCompletedDot">6</div><span class="step-label">Done</span></div>
                    </div>
                </div>

                <div class="exec-grid-2">
                    <div class="exec-card" style="margin-bottom: 0;">
                        <div class="exec-title" style="border-bottom: 1px solid #f1f5f9; padding-bottom: 0.75rem; margin-bottom: 1rem;"><i class="far fa-address-card" style="color: var(--primary-color);"></i> Customer & Event Details</div>
                        
                        <div style="display: grid; grid-template-columns: 1fr; gap: 1rem;">
                            <div style="display: flex; align-items: flex-start; gap: 0.75rem;">
                                <div style="width: 36px; height: 36px; border-radius: 8px; background: #f1f5f9; display: flex; align-items: center; justify-content: center; color: #64748b; flex-shrink: 0;"><i class="fas fa-user"></i></div>
                                <div>
                                    <div class="info-label">Customer Name</div>
                                    <div id="modalCustomer" class="info-value" style="font-weight: 700; color: #0f172a;"></div>
                                    <div id="modalEmail" style="font-size: 0.8rem; color: #64748b; margin-top: 2px;"></div>
                                </div>
                            </div>
                            
                            <div style="display: flex; align-items: flex-start; gap: 0.75rem;">
                                <div style="width: 36px; height: 36px; border-radius: 8px; background: #f8fafc; border: 1px solid #e2e8f0; display: flex; align-items: center; justify-content: center; color: #64748b; flex-shrink: 0;"><i class="fas fa-calendar-day"></i></div>
                                <div>
                                    <div class="info-label" id="modalEventDetailsLabel">Event Name</div>
                                    <div id="modalEventName" class="info-value" style="font-weight: 700; color: #0f172a; margin-bottom: 4px;"></div>
                                    <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
                                        <span id="modalEventType" style="font-size: 0.7rem; background: #e2e8f0; padding: 2px 6px; border-radius: 4px; color: #475569; font-weight: 600;"></span>
                                        <span id="modalGuestCount" style="font-size: 0.7rem; background: #e2e8f0; padding: 2px 6px; border-radius: 4px; color: #475569; font-weight: 600;"></span>
                                    </div>
                                </div>
                            </div>

                            <div style="display: flex; align-items: flex-start; gap: 0.75rem;">
                                <div style="width: 36px; height: 36px; border-radius: 8px; background: #fdf2f8; display: flex; align-items: center; justify-content: center; color: #be185d; flex-shrink: 0;"><i class="fas fa-map-marker-alt"></i></div>
                                <div>
                                    <div class="info-label">Venue Location</div>
                                    <div id="modalVenue" class="info-value" style="font-size: 0.85rem; line-height: 1.4;"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="exec-card" style="margin-bottom: 0; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div class="exec-title" style="border-bottom: 1px solid #f1f5f9; padding-bottom: 0.75rem; margin-bottom: 1rem;"><i class="far fa-star" style="color: #f59e0b;"></i> Special Requests</div>
                            <div style="background: #fffbeb; border: 1px solid #fef3c7; border-radius: 6px; padding: 0.75rem; color: #92400e; font-size: 0.85rem; min-height: 60px;" id="modalRequests"></div>
                        </div>
                        <div style="margin-top: 1rem; border-top: 1px solid #f1f5f9; padding-top: 1rem;">
                            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 0.75rem; display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div class="info-label">Balance Due By</div>
                                    <div id="dueDateDisplaySection">
                                        <div id="modalDueDate" class="info-value" style="font-weight: 700;">Not Set</div>
                                    </div>
                                    <div id="dueDateBadgeContainer" style="margin-top: 2px;"></div>
                                </div>
                                <button onclick="toggleDueDateEdit()" id="btnEditDueDate" style="background: white; border: 1px solid #cbd5e1; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; cursor: pointer;">
                                    <i class="fas fa-edit"></i> Edit
                                </button>
                            </div>
                            <div id="dueDateEditSection" style="display: none; margin-top: 0.75rem;">
                                <input type="date" id="balanceDueDateInput" class="form-control" style="font-size: 0.85rem; padding: 0.5rem; margin-bottom: 0.5rem; width: 100%; box-sizing: border-box;">
                                <div style="display: flex; gap: 0.5rem; justify-content: flex-start;">
                                    <button onclick="saveDueDate()" class="btn-primary" style="padding: 0.4rem 1rem; font-size: 0.75rem; min-width: 80px;">Save</button>
                                    <button onclick="toggleDueDateEdit()" class="btn-secondary" style="padding: 0.4rem 1rem; font-size: 0.75rem; min-width: 80px;">Cancel</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="exec-card" style="padding: 0; overflow: hidden; margin-top: 1.25rem;">
                    <details id="modalMenuDetailsBlock" open>
                        <summary style="padding: 1rem 1.25rem; font-size: 0.9rem; font-weight: 600; color: #0f172a; cursor: pointer; background: #f8fafc; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                            <span id="menuBreakdownHeaderSpan"><i class="fas fa-utensils" style="margin-right: 8px; color: var(--primary-color);"></i> Menu & Inclusions</span>
                            <i class="fas fa-chevron-down text-muted"></i>
                        </summary>
                        <div id="modalMenuSection" style="padding: 1.25rem;">
                            <div id="modalMenuItems" class="modal-menu-container" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem;"></div>
                        </div>
                    </details>
                </div>

                <div class="exec-card" style="padding: 0; overflow: hidden; margin-top: 1.25rem; margin-bottom: 0;">
                    <details>
                        <summary style="padding: 1rem 1.25rem; font-size: 0.85rem; font-weight: 600; color: #475569; cursor: pointer; background: #f8fafc; display: flex; justify-content: space-between; align-items: center;">
                            <span><i class="fas fa-history" style="margin-right: 8px;"></i> Audit Trail</span>
                            <i class="fas fa-chevron-down"></i>
                        </summary>
                        <div style="padding: 1.25rem; border-top: 1px solid #e2e8f0;">
                            <div class="audit-timeline-pro" id="modalHistoryTimeline"></div>
                        </div>
                    </details>
                </div>
            </div>

            <!-- 2. OPERATIONS -->
            <div id="btab-operations" class="mtab-pane-pro">
                <div class="exec-grid-2">
                    <div class="exec-card" style="margin-bottom: 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                            <div class="exec-title" style="margin: 0;"><i class="fas fa-check-square" style="color: var(--primary-color);"></i> Checklist</div>
                            <button onclick="addNewCustomTask()" style="background: transparent; border: 1px solid #cbd5e1; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; cursor: pointer;"><i class="fas fa-plus"></i> Add Task</button>
                        </div>
                        <div id="modalChecklistSection">
                            <div style="margin-bottom: 1rem;">
                                <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #64748b; margin-bottom: 4px;">
                                    <span>Progress</span>
                                    <span id="checklistProgressText" style="font-weight: 700; color: #0f172a;">0%</span>
                                </div>
                                <div style="height: 6px; background: #e2e8f0; border-radius: 4px; overflow: hidden;">
                                    <div id="checklistProgressBar" style="height: 100%; width: 0%; background: var(--primary-color); transition: width 0.3s;"></div>
                                </div>
                            </div>
                            <div id="bookingTasksList" style="max-height: 250px; overflow-y: auto; display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem;"></div>
                            <div style="display: flex; gap: 0.5rem;">
                                <input type="text" id="newTaskInput" class="form-control" placeholder="Add a task..." style="font-size: 0.85rem;" onkeypress="if(event.key === 'Enter') { event.preventDefault(); addBookingTaskFromInput(); }">
                                <button type="button" class="btn-primary" onclick="addBookingTaskFromInput()" style="padding: 0 1rem;"><i class="fas fa-plus"></i></button>
                            </div>
                        </div>
                    </div>

                    <div class="exec-card" style="margin-bottom: 0; display: flex; flex-direction: column;">
                        <div class="exec-title"><i class="far fa-sticky-note" style="color: var(--primary-color);"></i> Internal Notes</div>
                        <p style="font-size: 0.8rem; color: #64748b; margin-bottom: 0.75rem;">Private notes for your team.</p>
                        <textarea id="modalCatererNotes" placeholder="Write instructions here..." style="flex: 1; min-height: 120px; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0.75rem; font-size: 0.85rem; resize: none; background: #f8fafc; font-family: inherit; width: 100%; box-sizing: border-box;"></textarea>
                        <div style="text-align: right; margin-top: 0.75rem;">
                            <button onclick="saveCatererNotes()" class="btn-primary" style="padding: 6px 16px; font-size: 0.8rem;">Save Notes</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 3. FINANCIALS -->
            <div id="btab-financials" class="mtab-pane-pro">
                <div class="exec-grid-2">
                    <div class="exec-card" style="margin-bottom: 0; display: flex; flex-direction: column;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                            <div class="exec-title" style="margin: 0;"><i class="fas fa-receipt" style="color: var(--primary-color);"></i> Receipts</div>
                            <button id="aiVerifyBtn" onclick="runAIScan()" style="background: #f0f9ff; color: #0284c7; border: 1px solid #bae6fd; padding: 4px 10px; font-size: 0.75rem; border-radius: 4px; cursor: pointer;"><i class="fas fa-robot"></i> AI Scan</button>
                        </div>
                        <div id="modalProofSection" style="flex: 1;">
                            <div id="modalProofContainer" style="background: #f8fafc; border: 1px dashed #cbd5e1; padding: 1rem; border-radius: 6px; display: flex; gap: 1rem; flex-wrap: wrap; justify-content: center; align-items: center; min-height: 100px;">
                                <span style="color: #94a3b8; font-size: 0.85rem;">No receipts uploaded.</span>
                            </div>
                        </div>
                        <div id="aiScanResults" style="display: none; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; margin-top: 1rem;">
                            <div style="background: #f8fafc; padding: 0.5rem 0.75rem; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight: 600; font-size: 0.75rem; color: #475569;">Audit Results</span>
                                <div id="aiConfidenceBadge"></div>
                            </div>
                            <div id="aiScanContent" style="padding: 0.75rem; font-size: 0.8rem;"></div>
                            <div id="aiScanFlags" style="padding: 0 0.75rem 0.75rem;"></div>
                        </div>
                    </div>

                    <div class="exec-card" style="margin-bottom: 0; display: flex; flex-direction: column;">
                        <div class="exec-title" id="titleMasterContract"><i class="fas fa-file-contract" style="color: var(--primary-color);"></i> Documents</div>
                        <p id="descMasterContract" style="font-size: 0.85rem; color: #64748b; margin-bottom: 1rem;">Agreements and verifications.</p>
                        <div style="display: flex; flex-direction: column; gap: 0.75rem; margin-top: auto;">
                            <button id="btnViewMasterContract" onclick="openContractModal(currentBookingId)" class="btn-primary" style="width: 100%;"><i class="fas fa-file-signature"></i> View Contract</button>
                            <button type="button" id="linkViewCustomerAudit" onclick="viewCustomerKyc(event)" class="btn-secondary" style="width: 100%;"><i class="far fa-id-card"></i> View KYC</button>
                        </div>
                    </div>
                </div>

                <div class="exec-card" style="margin-bottom: 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <div class="exec-title" style="margin: 0;"><i class="fas fa-calculator" style="color: var(--primary-color);"></i> Expense Tracker</div>
                    </div>
                    <form id="expenseTrackerForm" onsubmit="submitExpenses(event)">
                        <input type="hidden" id="expenseBookingId">
                        <input type="hidden" id="bookingTotalAmount" value="0">
                        
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 1rem; background: #f8fafc; padding: 1rem; border-radius: 6px; border: 1px solid #e2e8f0; margin-bottom: 1rem;">
                            <div><div class="info-label">Revenue</div><div id="modalBookingTotal" class="info-value" style="font-weight: 700;">₱0.00</div></div>
                            <div><div class="info-label">Est. Profit</div><div id="modalEstimateProfit" class="info-value" style="color: #10b981; font-weight: 700;">₱0.00</div></div>
                            <div><div class="info-label">Margin</div><div id="modalRoiPercent" class="info-value" style="display: flex; gap: 4px; align-items: center;"><span>0%</span><span id="roiTrendIcon"></span></div></div>
                        </div>

                        <div style="border: 1px solid #e2e8f0; border-radius: 6px; overflow-x: auto; margin-bottom: 1rem;">
                            <table class="table" style="width: 100%; border-collapse: collapse; margin-bottom: 0; table-layout: fixed;">
                                <thead style="background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                                    <tr>
                                        <th style="padding: 0.75rem; text-align: left; font-size: 0.75rem; color: #64748b; font-weight: 600;">Description</th>
                                        <th style="padding: 0.75rem; text-align: right; font-size: 0.75rem; color: #64748b; font-weight: 600; width: 35%;">Amount (₱)</th>
                                        <th style="padding: 0.75rem; width: 44px; text-align: center;"></th>
                                    </tr>
                                </thead>
                                <tbody id="actualExpenseRows"></tbody>
                            </table>
                        </div>
                        
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <button type="button" class="btn-secondary" style="padding: 4px 10px; font-size: 0.75rem;" onclick="addExpenseRow()"><i class="fas fa-plus"></i> Add Row</button>
                            <div style="text-align: right;">
                                <span class="info-label">Total Expenses:</span>
                                <span id="totalActualExpenseDisplay" style="font-size: 1.1rem; font-weight: 700; color: #dc2626; margin-left: 0.5rem;">₱0.00</span>
                            </div>
                        </div>

                        <div style="text-align: right; margin-top: 1.5rem; border-top: 1px solid #e2e8f0; padding-top: 1rem;">
                            <button type="submit" id="saveExpenseBtn" class="btn-primary"><i class="fas fa-save"></i> Save Expenses</button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- 4. CHAT -->
            <div id="btab-chat" class="mtab-pane-pro">
                <div class="exec-card" style="margin-bottom: 0; display: flex; flex-direction: column; height: 500px; padding: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.75rem; margin-bottom: 0.75rem;">
                        <div class="exec-title" style="margin: 0;"><i class="far fa-comments" style="color: var(--primary-color);"></i> Customer Chat</div>
                        <span style="font-size: 0.7rem; color: #10b981; background: #dcfce7; padding: 2px 8px; border-radius: 4px; font-weight: 600;">Active</span>
                    </div>
                    
                    <div id="modalChatMessages" style="flex: 1; overflow-y: auto; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;"></div>

                    <form id="modalChatForm" style="margin-top: 0.75rem; display: flex; gap: 0.5rem; align-items: center;">
                        <input type="hidden" id="chatBookingId" name="booking_id">
                        <textarea id="chatMessageInput" name="message" rows="1" placeholder="Type a message..." style="flex: 1; height: 44px; padding: 0.75rem; border: 1px solid #cbd5e1; border-radius: 6px; resize: none; outline: none; font-family: inherit; font-size: 0.85rem; box-sizing: border-box; line-height: 1.2;"></textarea>
                        <div style="display: flex; gap: 0.4rem; height: 44px;">
                            <label style="cursor: pointer; background: #f1f5f9; width: 44px; height: 44px; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #64748b; border: 1px solid #cbd5e1; margin: 0;">
                                <i class="fas fa-paperclip"></i>
                                <input type="file" id="chatAttachmentInput" name="attachment" style="display: none;">
                            </label>
                            <button type="submit" id="chatSubmitBtn" style="background: var(--primary-color); width: 44px; height: 44px; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: white; border: none; cursor: pointer; margin: 0;">
                                <i class="fas fa-paper-plane"></i>
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>

        <!-- Action Footer -->
        <div id="actionCenterWrapper">
            <div id="actionCenterHeader" onclick="window.toggleActionCenter()" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; cursor: pointer; user-select: none;">
                <div style="font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase;">Actions</div>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <div id="modalRiskAlert" style="display: none;"></div>
                    <button type="button" id="btnToggleActionCenter" onclick="event.stopPropagation(); window.toggleActionCenter();" style="background: transparent; border: 1px solid #cbd5e1; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; color: #64748b; cursor: pointer;">
                        <span id="actionCenterToggleText">Hide</span> <i id="actionCenterToggleIcon" class="fas fa-chevron-down"></i>
                    </button>
                </div>
            </div>
            <div id="bookingModalActionsTop" style="display: flex; gap: 0.5rem; flex-wrap: wrap; width: 100%;"></div>
        </div>
    </div>
</div>'''

replace_lines(r'c:\OccaServe\OccaShare\templates\caterer\bookings.html', 1197, 1817, new_content)
