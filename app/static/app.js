let selectedCompanyId = null;
let isPipelineRunning = false;
let pollingInterval = null;

// On Load
document.addEventListener("DOMContentLoaded", () => {
    fetchCompanies();
    fetchSequences();
    loadAnalytics();
    
    // Bind Submit Forms
    document.getElementById("create-company-form").addEventListener("submit", addCompany);
    document.getElementById("create-sequence-form").addEventListener("submit", createSequence);
    document.getElementById("btn-run-pipeline").onclick = triggerPipeline;
    document.getElementById("btn-copy-email").onclick = copyEmailToClipboard;
    document.getElementById("btn-send-email").onclick = sendEmailViaGmail;

    // Dropdown selection change
    document.getElementById("pipeline-company-select").addEventListener("change", (e) => {
        if (e.target.value) {
            const opt = e.target.options[e.target.selectedIndex];
            selectCompany(parseInt(e.target.value), opt.text.split(" (")[0]);
        }
    });

});

// Helper to get company brand color and logo favicon
function getCompanyStyles(domain) {
    const d = domain.toLowerCase();
    
    // Default fallback styles
    let color = "#71717a"; // Neutral zinc grey
    let logoUrl = `https://www.google.com/s2/favicons?sz=64&domain=${domain}`;
    
    if (d.includes("stripe")) {
        color = "#635bff"; // Stripe Violet
    } else if (d.includes("razorpay")) {
        color = "#0b72e7"; // Razorpay Blue
    } else if (d.includes("google")) {
        color = "#ea4335"; // Google Red
    } else if (d.includes("github")) {
        color = "#24292e"; // GitHub Charcoal
    } else if (d.includes("apple")) {
        color = "#1c1c1e"; // Apple black
    } else {
        // Deterministic brand color generator based on domain string hash
        let hash = 0;
        for (let i = 0; i < d.length; i++) {
            hash = d.charCodeAt(i) + ((hash << 5) - hash);
        }
        const hue = Math.abs(hash) % 360;
        color = `hsl(${hue}, 60%, 40%)`;
    }
    
    return { color, logoUrl };
}

// Fetch all registered companies
async function fetchCompanies() {
    try {
        const response = await fetch("/api/v1/companies");
        const companies = await response.json();
        
        const listContainer = document.getElementById("company-list");
        const selectContainer = document.getElementById("pipeline-company-select");
        
        // Reset list and select dropdown
        listContainer.innerHTML = "";
        selectContainer.innerHTML = '<option value="">-- Select Company --</option>';
        
        if (companies.length === 0) {
            listContainer.innerHTML = '<div class="empty-state">No companies registered yet.</div>';
            return;
        }
        
        companies.forEach(company => {
            const brand = getCompanyStyles(company.domain);
            
            // Render in Directory List
            const item = document.createElement("div");
            item.className = "company-item";
            item.setAttribute("data-id", company.id);
            if (selectedCompanyId === company.id) {
                item.className += " selected";
                // Color grading selection bar accent
                item.style.borderLeft = `3px solid ${brand.color}`;
            }
            item.onclick = () => selectCompany(company.id, company.name);
            item.innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0;">
                    <div class="company-logo-frame" style="width: 28px; height: 28px; border-radius: 6px; background: rgba(0,0,0,0.03); border: 1px solid rgba(0,0,0,0.06); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                        <img src="${brand.logoUrl}" style="width: 16px; height: 16px; object-fit: contain;" onerror="this.src='https://www.google.com/s2/favicons?sz=64&domain=example.com'">
                    </div>
                    <div style="display: flex; flex-direction: column; justify-content: center; min-width: 0; overflow: hidden;">
                        <strong style="font-size: 13px; font-weight: 600; color: var(--text-primary); line-height: 1.2; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${company.name}</strong> 
                        <small style="color: var(--text-secondary); display: block; font-size: 11px; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px;">${company.domain}</small>
                    </div>
                </div>
            `;
            listContainer.appendChild(item);
            
            // Add to Selector Dropdown
            const option = document.createElement("option");
            option.value = company.id;
            option.textContent = `${company.name} (${company.domain})`;
            selectContainer.appendChild(option);
        });
        
        if (selectedCompanyId) {
            selectContainer.value = selectedCompanyId;
        }
    } catch (err) {
        console.error("Failed to fetch companies:", err);
    }
}

// Register a new company record
async function addCompany(event) {
    event.preventDefault();
    const nameInput = document.getElementById("company-name");
    const domainInput = document.getElementById("company-domain");
    
    try {
        const response = await fetch("/api/v1/companies", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name: nameInput.value.strip ? nameInput.value.strip() : nameInput.value,
                domain: domainInput.value.strip ? domainInput.value.strip() : domainInput.value
            })
        });
        
        if (response.ok) {
            const newCompany = await response.json();
            selectedCompanyId = newCompany.id;
            nameInput.value = "";
            domainInput.value = "";
            await fetchCompanies();
            selectCompany(newCompany.id);
        } else {
            const errData = await response.json();
            alert(`Error: ${errData.detail || 'Failed to add company'}`);
        }
    } catch (err) {
        console.error("Failed to add company:", err);
    }
}

// Select a company from directory list
function selectCompany(companyId, companyName = "") {
    selectedCompanyId = companyId;
    
    // Highlight list items
    const items = document.querySelectorAll("#company-list .company-item");
    const selectDropdown = document.getElementById("pipeline-company-select");
    
    selectDropdown.value = companyId;
    
    items.forEach(item => {
        const itemId = parseInt(item.getAttribute("data-id"));
        if (itemId === companyId) {
            item.classList.add("selected");
            const domain = item.querySelector("small").textContent;
            const brand = getCompanyStyles(domain);
            item.style.borderLeft = `3px solid ${brand.color}`;
        } else {
            item.classList.remove("selected");
            item.style.borderLeft = "";
        }
    });
    
    // Toggle sources panel
    const sourcesSec = document.getElementById("company-sources-section");
    if (sourcesSec) {
        sourcesSec.style.display = "block";
        document.getElementById("source-company-name").textContent = companyName || `Company #${companyId}`;
        const sourceForm = document.getElementById("add-source-form");
        sourceForm.onsubmit = (e) => addCompanySource(e, companyId);
        fetchCompanySources(companyId);
    }
    
    // Fetch and populate results if they exist in DB
    fetchResults(companyId);
    fetchCompanySequenceTimeline(companyId);
}

// Trigger enrichment pipeline
async function triggerPipeline() {
    const companySelect = document.getElementById("pipeline-company-select");
    const objectiveInput = document.getElementById("outreach-objective");
    const connectorSelect = document.getElementById("pipeline-connector");
    const draftOnlyCheckbox = document.getElementById("pipeline-draft-only");
    
    const companyId = companySelect.value;
    if (!companyId) {
        alert("Please select a target company first.");
        return;
    }
    
    if (isPipelineRunning) return;
    isPipelineRunning = true;
    
    // Gather Additional URLs
    const additionalUrlElements = document.querySelectorAll(".additional-url");
    const additionalUrls = [];
    additionalUrlElements.forEach(el => {
        if (el.value.trim()) {
            additionalUrls.push(el.value.trim());
        }
    });

    const statusBadge = document.getElementById("pipeline-status-badge");
    const loaderRing = document.getElementById("pipeline-loader");
    const runBtn = document.getElementById("btn-run-pipeline");
    const auditLog = document.getElementById("audit-log-container");
    
    statusBadge.className = "status-badge status-running";
    statusBadge.textContent = "Processing";
    loaderRing.style.display = "block";
    runBtn.disabled = true;
    runBtn.textContent = "Processing pipeline...";
    auditLog.innerHTML = `<div class="log-line system-log">Enrichment pipeline dispatched...</div>`;
    
    const sequenceSelect = document.getElementById("pipeline-sequence-select");
    const contactEmailInput = document.getElementById("pipeline-contact-email");
    const sequenceId = sequenceSelect.value ? parseInt(sequenceSelect.value) : null;
    const contactEmail = contactEmailInput.value.trim() || null;

    try {
        const response = await fetch(`/api/v1/companies/${companyId}/enrich?connector=${connectorSelect.value}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                draft_only: draftOnlyCheckbox.checked,
                outreach_objective: objectiveInput.value || "Introduce our solutions",
                additional_urls: additionalUrls,
                sequence_id: sequenceId,
                contact_email: contactEmail
            })
        });
        
        if (response.ok) {
            // Start Polling logs
            startPollingLogs(companyId);
        } else {
            const errData = await response.json();
            auditLog.innerHTML += `<div class="log-line error-log">Trigger failed: ${errData.detail || 'Server error'}</div>`;
            resetPipelineStatus(false);
        }
    } catch (err) {
        auditLog.innerHTML += `<div class="log-line error-log">Network error: ${err.message}</div>`;
        resetPipelineStatus(false);
    }
}

// Start polling execution audit history
function startPollingLogs(companyId) {
    if (pollingInterval) clearInterval(pollingInterval);
    const runStartTime = Date.now();
    
    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/v1/companies/${companyId}/audit`);
            const logs = await response.json();
            
            const logDisplay = document.getElementById("audit-log-container");
            logDisplay.innerHTML = "";
            
            let isCompleted = false;
            let isFailed = false;
            
            logs.forEach(log => {
                const logTime = new Date(log.timestamp).getTime();
                // 5 second buffer to make sure we capture the start event
                const isNewLog = logTime >= (runStartTime - 5000);
                
                const line = document.createElement("div");
                line.className = "log-line";
                if (log.status === "failed") {
                    line.className += " error-log";
                    if (isNewLog) {
                        // Only fail current run on fatal pipeline steps
                        const fatalActions = ["pipeline_completed", "enrichment_started", "enriched", "ai_analysis_started", "ai_analyzed", "email_drafting_started", "email_drafted"];
                        if (fatalActions.includes(log.action)) {
                            isFailed = true;
                        }
                    }
                } else if (log.action.startsWith("pipeline_")) {
                    line.className += " system-log";
                }
                
                const time = new Date(log.timestamp).toLocaleTimeString();
                let detailText = "";
                if (log.details && Object.keys(log.details).length > 0) {
                    detailText = ` (${JSON.stringify(log.details)})`;
                }
                line.textContent = `[${time}] ${log.action.toUpperCase()}: ${log.status.toUpperCase()}${detailText}`;
                logDisplay.appendChild(line);
                
                if (isNewLog && log.action === "pipeline_completed" && log.status === "success") {
                    isCompleted = true;
                }
            });
            
            // Auto scroll to bottom
            logDisplay.scrollTop = logDisplay.scrollHeight;
            
            if (isCompleted) {
                clearInterval(pollingInterval);
                resetPipelineStatus(true);
                fetchResults(companyId);
                fetchCompanySequenceTimeline(companyId);
                loadAnalytics();
                fetchCompanies();
            } else if (isFailed) {
                clearInterval(pollingInterval);
                resetPipelineStatus(false);
                fetchCompanySequenceTimeline(companyId);
                loadAnalytics();
            }
        } catch (err) {
            console.error("Error polling logs:", err);
        }
    }, 2000);
}

// Reset trigger buttons and loader ring state
function resetPipelineStatus(success) {
    isPipelineRunning = false;
    const statusBadge = document.getElementById("pipeline-status-badge");
    const loaderRing = document.getElementById("pipeline-loader");
    const runBtn = document.getElementById("btn-run-pipeline");
    
    loaderRing.style.display = "none";
    runBtn.disabled = false;
    runBtn.textContent = "Run Workflow Engine";
    
    if (success) {
        statusBadge.className = "status-badge status-success";
        statusBadge.textContent = "Success";
    } else {
        statusBadge.className = "status-badge status-failed";
        statusBadge.textContent = "Failed";
    }
}

// Fetch results (analysis & email draft)
async function fetchResults(companyId) {
    try {
        const response = await fetch(`/api/v1/companies/${companyId}/results`);
        const data = await response.json();
        
        const subjectInput = document.getElementById("result-email-subject");
        const bodyTextarea = document.getElementById("result-email-body");
        const ctaInput = document.getElementById("result-email-cta");
        
        const summaryText = document.getElementById("result-summary");
        const painPointsList = document.getElementById("result-pain-points");
        const buyingSignalsList = document.getElementById("result-buying-signals");
        const contextText = document.getElementById("result-outreach-context");
        
        // Reset fields
        subjectInput.value = "";
        bodyTextarea.value = "";
        ctaInput.value = "";
        summaryText.textContent = "Run enrichment to view insights.";
        painPointsList.innerHTML = "";
        buyingSignalsList.innerHTML = "";
        contextText.textContent = "";
        
        // Populate Email Outreach
        if (data.email) {
            subjectInput.value = data.email.subject || "";
            bodyTextarea.value = data.email.body || "";
            ctaInput.value = data.email.cta || "";
            
            const sendBtn = document.getElementById("btn-send-email");
            if (data.email.status === "sent") {
                sendBtn.textContent = "Sent ✓";
                sendBtn.disabled = true;
                sendBtn.style.background = "var(--success-color)";
            } else if (data.email.status === "failed") {
                sendBtn.textContent = "Retry Send (Failed)";
                sendBtn.disabled = false;
                sendBtn.style.background = "var(--error-color)";
            } else {
                sendBtn.textContent = "Send via Gmail";
                sendBtn.disabled = false;
                sendBtn.style.background = "";
            }
        }
        
        // Populate Insights
        if (data.analysis) {
            summaryText.textContent = data.analysis.summary || "";
            contextText.textContent = data.analysis.outreach_context || "";
            
            const painPoints = data.analysis.pain_points || [];
            painPoints.forEach(pt => {
                const li = document.createElement("li");
                li.textContent = pt;
                painPointsList.appendChild(li);
            });
            
            const signals = data.analysis.buying_signals || [];
            signals.forEach(sig => {
                const li = document.createElement("li");
                li.textContent = sig;
                buyingSignalsList.appendChild(li);
            });
        }
    } catch (err) {
        console.error("Failed to fetch results:", err);
    }
}

// Load footer analytics statistics
async function loadAnalytics() {
    try {
        const response = await fetch("/api/v1/analytics");
        const analytics = await response.json();
        
        document.getElementById("metric-processed").textContent = analytics.companies_processed || 0;
        document.getElementById("metric-success").textContent = analytics.successful_enrichments || 0;
        document.getElementById("metric-failed").textContent = analytics.failed_enrichments || 0;
        document.getElementById("metric-emails").textContent = analytics.emails_generated || 0;
        document.getElementById("metric-latency").textContent = `${(analytics.average_processing_time_seconds || 0).toFixed(1)}s`;
    } catch (err) {
        console.error("Failed to load analytics:", err);
    }
}

// Copy draft email copy to clipboard
function copyEmailToClipboard() {
    const subject = document.getElementById("result-email-subject").value;
    const body = document.getElementById("result-email-body").value;
    const cta = document.getElementById("result-email-cta").value;
    
    if (!body) {
        alert("No email copy to copy.");
        return;
    }
    
    const formattedText = `Subject: ${subject}\n\n${body}`;
    navigator.clipboard.writeText(formattedText)
        .then(() => alert("Email draft copied to clipboard!"))
        .catch(err => console.error("Clipboard copy failed:", err));
}

// Send current draft via Gmail SMTP
async function sendEmailViaGmail() {
    if (!selectedCompanyId) return;
    
    const sendBtn = document.getElementById("btn-send-email");
    sendBtn.disabled = true;
    sendBtn.textContent = "Sending...";
    
    try {
        // Trigger direct pipeline with draft_only=false
        const companySelect = document.getElementById("pipeline-company-select");
        const objectiveInput = document.getElementById("outreach-objective");
        const connectorSelect = document.getElementById("pipeline-connector");
        
        const response = await fetch(`/api/v1/companies/${selectedCompanyId}/enrich?connector=${connectorSelect.value}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                draft_only: false,
                outreach_objective: objectiveInput.value || "Introduce our solutions"
            })
        });
        
        if (response.ok) {
            // Poll logs to show dispatch status
            startPollingLogs(selectedCompanyId);
        } else {
            alert("Failed to initiate SMTP delivery.");
            sendBtn.disabled = false;
            sendBtn.textContent = "Send via Gmail";
        }
    } catch (err) {
        console.error(err);
        sendBtn.disabled = false;
        sendBtn.textContent = "Send via Gmail";
    }
}

// Additional URL dynamic input controls
function addUrlRow() {
    const list = document.getElementById("additional-urls-list");
    const row = document.createElement("div");
    row.className = "url-input-row";
    row.innerHTML = `
        <input type="url" class="additional-url" placeholder="https://stripe.com/blog/example-post">
        <button type="button" class="btn-remove-url" onclick="removeUrlRow(this)">×</button>
    `;
    list.appendChild(row);
}

function removeUrlRow(btn) {
    btn.parentElement.remove();
}

// Tabs switcher controller
function switchTab(tabId) {
    const activeBtn = event.currentTarget;
    const card = activeBtn.closest(".glass-card");
    const tabButtons = card.querySelectorAll(".tab-btn");
    const tabContents = card.querySelectorAll(".tab-content");
    
    tabButtons.forEach(btn => btn.classList.remove("active"));
    tabContents.forEach(content => content.classList.remove("active"));
    
    // Activate target
    activeBtn.classList.add("active");
    document.getElementById(tabId).classList.add("active");
}

// Sources CRUD helper integrations
async function fetchCompanySources(companyId) {
    try {
        const response = await fetch(`/api/v1/companies/${companyId}/sources`);
        const sources = await response.json();
        
        const list = document.getElementById("saved-sources-list");
        list.innerHTML = "";
        
        if (sources.length === 0) {
            list.innerHTML = '<div class="empty-state">No custom sources saved yet.</div>';
            return;
        }
        
        sources.forEach(src => {
            const item = document.createElement("div");
            item.className = "source-item";
            item.style.cursor = "default";
            item.innerHTML = `
                <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 80%;">
                    <a href="${src.url}" target="_blank" style="color: #4f46e5; font-size: 0.8rem; text-decoration: none;">${src.url}</a>
                </div>
                <button type="button" class="btn-remove-url" onclick="deleteCompanySource(${src.id}, ${companyId})" style="padding: 0; font-size: 1.2rem;">×</button>
            `;
            list.appendChild(item);
        });
    } catch (err) {
        console.error("Failed to fetch sources:", err);
    }
}

async function addCompanySource(event, companyId) {
    event.preventDefault();
    const input = document.getElementById("source-url");
    const url = input.value.trim();
    if (!url) return;
    
    try {
        const response = await fetch(`/api/v1/companies/${companyId}/sources`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: url })
        });
        
        if (response.ok) {
            input.value = "";
            fetchCompanySources(companyId);
        } else {
            const err = await response.json();
            alert(err.detail || "Failed to add source");
        }
    } catch (err) {
        console.error(err);
    }
}

async function deleteCompanySource(sourceId, companyId) {
    if (!confirm("Are you sure you want to remove this source?")) return;
    
    try {
        const response = await fetch(`/api/v1/companies/sources/${sourceId}`, {
            method: "DELETE"
        });
        
        if (response.ok) {
            fetchCompanySources(companyId);
        } else {
            alert("Failed to delete source");
        }
    } catch (err) {
        console.error(err);
    }
}

// -------------------- SEQUENCE WORKFLOWS UI --------------------

function switchDirectoryTab(tabId) {
    const tabButtons = [document.getElementById("tab-btn-companies"), document.getElementById("tab-btn-sequences")];
    const tabContents = [document.getElementById("companies-directory-tab"), document.getElementById("sequences-templates-tab")];
    
    tabButtons.forEach(btn => btn.classList.remove("active"));
    tabContents.forEach(content => {
        content.classList.remove("active");
        content.style.display = "none";
    });
    
    if (tabId === "companies-directory-tab") {
        document.getElementById("tab-btn-companies").classList.add("active");
        document.getElementById("companies-directory-tab").classList.add("active");
        document.getElementById("companies-directory-tab").style.display = "block";
    } else {
        document.getElementById("tab-btn-sequences").classList.add("active");
        document.getElementById("sequences-templates-tab").classList.add("active");
        document.getElementById("sequences-templates-tab").style.display = "block";
    }
}

function addFormStepRow() {
    const list = document.getElementById("sequence-form-steps-list");
    const count = list.querySelectorAll(".sequence-form-step-row").length + 1;
    
    const row = document.createElement("div");
    row.className = "sequence-form-step-row";
    row.style.display = "flex";
    row.style.gap = "0.4rem";
    row.style.alignItems = "center";
    row.style.background = "rgba(255,255,255,0.02)";
    row.style.padding = "0.4rem";
    row.style.borderRadius = "6px";
    row.innerHTML = `
        <span class="step-num-label" style="font-size: 0.75rem; font-weight: 600; min-width: 45px;">Step ${count}:</span>
        <input type="number" class="step-delay" placeholder="Days" value="3" min="0" style="width: 55px; padding: 0.25rem;" required>
        <input type="text" class="step-prompt" placeholder="Prompt template guidelines..." style="flex: 1; padding: 0.25rem;" required>
        <button type="button" class="btn-remove-url" onclick="this.parentElement.remove(); reindexFormSteps();" style="padding: 0; font-size: 1.1rem; min-width: 20px;">×</button>
    `;
    list.appendChild(row);
}

function reindexFormSteps() {
    const list = document.getElementById("sequence-form-steps-list");
    const rows = list.querySelectorAll(".sequence-form-step-row");
    rows.forEach((row, idx) => {
        row.querySelector(".step-num-label").textContent = `Step ${idx + 1}:`;
    });
}

async function fetchSequences() {
    try {
        const response = await fetch("/api/v1/sequences");
        const sequences = await response.json();
        
        const list = document.getElementById("sequence-list");
        const select = document.getElementById("pipeline-sequence-select");
        
        list.innerHTML = "";
        select.innerHTML = '<option value="">-- No Sequence (One-Shot Outreach) --</option>';
        
        if (sequences.length === 0) {
            list.innerHTML = '<div class="empty-state">No sequences created yet.</div>';
            return;
        }
        
        sequences.forEach(seq => {
            // Render list template
            const item = document.createElement("div");
            item.className = "company-item";
            item.style.cursor = "default";
            item.innerHTML = `
                <div>
                    <strong>${seq.name}</strong>
                    <small style="color: var(--text-secondary); display:block;">${seq.steps.length} Steps • ${seq.description || 'No description'}</small>
                </div>
                <button type="button" class="btn-remove-url" onclick="deleteSequenceTemplate(${seq.id})" style="padding: 0; font-size: 1.2rem;">×</button>
            `;
            list.appendChild(item);
            
            // Add to dropdown select
            const opt = document.createElement("option");
            opt.value = seq.id;
            opt.textContent = `${seq.name} (${seq.steps.length} steps)`;
            select.appendChild(opt);
        });
    } catch (err) {
        console.error("Failed to fetch sequences:", err);
    }
}

async function createSequence(event) {
    event.preventDefault();
    const name = document.getElementById("sequence-name").value.trim();
    const objective = document.getElementById("sequence-objective").value.trim();
    const desc = document.getElementById("sequence-desc").value.trim();
    
    const stepRows = document.querySelectorAll(".sequence-form-step-row");
    const steps = [];
    stepRows.forEach((row, idx) => {
        const delay = parseInt(row.querySelector(".step-delay").value);
        const prompt = row.querySelector(".step-prompt").value.trim();
        steps.push({
            step_number: idx + 1,
            delay_days: delay,
            channel: "email",
            prompt_template: prompt,
            auto_send: true
        });
    });
    
    try {
        const response = await fetch("/api/v1/sequences", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name: name,
                description: desc,
                default_objective: objective,
                is_active: true,
                steps: steps
            })
        });
        
        if (response.ok) {
            document.getElementById("sequence-name").value = "";
            document.getElementById("sequence-objective").value = "";
            document.getElementById("sequence-desc").value = "";
            // Reset to step 1
            const list = document.getElementById("sequence-form-steps-list");
            list.innerHTML = `
                <div class="sequence-form-step-row" style="display: flex; gap: 0.4rem; align-items: center; background: rgba(255,255,255,0.02); padding: 0.4rem; border-radius: 6px;">
                    <span class="step-num-label" style="font-size: 0.75rem; font-weight: 600; min-width: 45px;">Step 1:</span>
                    <input type="number" class="step-delay" placeholder="Days" value="0" min="0" style="width: 55px; padding: 0.25rem;" required>
                    <input type="text" class="step-prompt" placeholder="Prompt template guidelines..." style="flex: 1; padding: 0.25rem;" required value="Write the initial personalized cold outreach email. Reference a specific pain point.">
                    <button type="button" class="btn-remove-url" onclick="this.parentElement.remove(); reindexFormSteps();" style="padding: 0; font-size: 1.1rem; min-width: 20px;">×</button>
                </div>
            `;
            await fetchSequences();
            alert("Sequence template created successfully!");
        } else {
            const err = await response.json();
            alert("Failed to create sequence: " + (err.detail || "Server error"));
        }
    } catch (err) {
        console.error(err);
    }
}

async function deleteSequenceTemplate(seqId) {
    if (!confirm("Are you sure you want to delete this sequence template?")) return;
    
    try {
        const response = await fetch(`/api/v1/sequences/${seqId}`, {
            method: "DELETE"
        });
        if (response.ok) {
            fetchSequences();
        } else {
            alert("Failed to delete sequence template.");
        }
    } catch (err) {
        console.error(err);
    }
}

async function fetchCompanySequenceTimeline(companyId) {
    const statusBadge = document.getElementById("enrollment-status-badge");
    const contactSpan = document.getElementById("enrollment-contact-email");
    const container = document.getElementById("sequence-timeline-container");
    
    const pauseBtn = document.getElementById("btn-pause-enrollment");
    const resumeBtn = document.getElementById("btn-resume-enrollment");
    const cancelBtn = document.getElementById("btn-cancel-enrollment");
    
    // Hide actions initially
    pauseBtn.style.display = "none";
    resumeBtn.style.display = "none";
    cancelBtn.style.display = "none";
    
    try {
        const response = await fetch(`/api/v1/companies/${companyId}/enrollments`);
        const enrollments = await response.json();
        
        if (!enrollments || enrollments.length === 0) {
            statusBadge.className = "status-badge status-idle";
            statusBadge.textContent = "Not Enrolled";
            contactSpan.textContent = "-";
            container.innerHTML = '<div class="empty-state">Not enrolled in any outreach sequence workflow. Use "Pipeline Run Configuration" above to enroll.</div>';
            return;
        }
        
        // Find latest enrollment
        const latest = enrollments[0];
        statusBadge.textContent = latest.status.toUpperCase();
        contactSpan.textContent = latest.contact_email;
        
        // Set badge class
        if (latest.status === "active") {
            statusBadge.className = "status-badge status-running";
            pauseBtn.style.display = "block";
            pauseBtn.onclick = () => pauseEnrollment(latest.id, companyId);
            cancelBtn.style.display = "block";
            cancelBtn.onclick = () => cancelEnrollment(latest.id, companyId);
        } else if (latest.status === "paused") {
            statusBadge.className = "status-badge status-idle";
            resumeBtn.style.display = "block";
            resumeBtn.onclick = () => resumeEnrollment(latest.id, companyId);
            cancelBtn.style.display = "block";
            cancelBtn.onclick = () => cancelEnrollment(latest.id, companyId);
        } else if (latest.status === "replied") {
            statusBadge.className = "status-badge status-running";
            statusBadge.style.background = "#f59e0b"; // orange color for replied
        } else if (latest.status === "completed") {
            statusBadge.className = "status-badge status-success";
        } else if (latest.status === "cancelled") {
            statusBadge.className = "status-badge status-failed";
        }
        
        // Build chronological list of events
        const events = [];
        if (latest.messages) {
            latest.messages.forEach(msg => {
                const date = msg.sent_at || msg.scheduled_at || msg.created_at;
                events.push({
                    type: "message",
                    date: new Date(date),
                    data: msg
                });
            });
        }
        if (latest.reply_events) {
            latest.reply_events.forEach(reply => {
                events.push({
                    type: "reply",
                    date: new Date(reply.detected_at),
                    data: reply
                });
            });
        }
        
        // Sort chronologically
        events.sort((a, b) => a.date - b.date);
        
        container.innerHTML = "";
        if (events.length === 0) {
            container.innerHTML = '<div class="empty-state">Enrollment created. Waiting for outreach message initialization...</div>';
            return;
        }
        
        events.forEach(event => {
            const item = document.createElement("div");
            if (event.type === "message") {
                const msg = event.data;
                item.className = `timeline-item ${msg.status.toLowerCase()}`;
                
                let actionBtnText = "";
                if (msg.status === "draft" || msg.status === "failed") {
                    actionBtnText = `<div class="timeline-item-actions"><button class="btn-primary" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;" onclick="sendMessageDirect(${msg.id}, ${companyId}, this)">Send Now</button></div>`;
                }
                
                const timeStr = event.date.toLocaleString();
                const title = `Step ${msg.step_number}: ${msg.status.toUpperCase()}`;
                const detailText = msg.subject ? `Subject: ${msg.subject}\n\n${msg.body}` : `Content pending LLM generation...`;
                
                item.innerHTML = `
                    <div class="timeline-item-header">
                        <span class="timeline-item-title">${title}</span>
                        <span class="timeline-item-date">${timeStr}</span>
                    </div>
                    <div class="timeline-item-body">${detailText}</div>
                    ${actionBtnText}
                `;
            } else {
                const rep = event.data;
                item.className = "timeline-item reply";
                const timeStr = event.date.toLocaleString();
                item.innerHTML = `
                    <div class="timeline-item-header">
                        <span class="timeline-item-title" style="color: #f59e0b;">Prospect Reply Received</span>
                        <span class="timeline-item-date">${timeStr}</span>
                    </div>
                    <div class="timeline-item-body" style="border-left: 2px solid #f59e0b; background: rgba(245,158,11,0.05);">
                        <strong>From:</strong> ${rep.from_email}<br>
                        <strong>Subject:</strong> ${rep.subject}<br><br>
                        "${rep.snippet}"
                    </div>
                `;
            }
            container.appendChild(item);
        });
    } catch (err) {
        console.error("Failed to load sequence timeline:", err);
    }
}

async function pauseEnrollment(enrollmentId, companyId) {
    if (!confirm("Are you sure you want to pause this sequence?")) return;
    try {
        const response = await fetch(`/api/v1/enrollments/${enrollmentId}/pause`, { method: "POST" });
        if (response.ok) {
            fetchCompanySequenceTimeline(companyId);
        } else {
            alert("Failed to pause sequence.");
        }
    } catch (err) {
        console.error(err);
    }
}

async function resumeEnrollment(enrollmentId, companyId) {
    try {
        const response = await fetch(`/api/v1/enrollments/${enrollmentId}/resume`, { method: "POST" });
        if (response.ok) {
            fetchCompanySequenceTimeline(companyId);
        } else {
            alert("Failed to resume sequence.");
        }
    } catch (err) {
        console.error(err);
    }
}

async function cancelEnrollment(enrollmentId, companyId) {
    if (!confirm("Are you sure you want to cancel this sequence enrollment? This will revoke pending tasks.")) return;
    try {
        const response = await fetch(`/api/v1/enrollments/${enrollmentId}/cancel`, { method: "POST" });
        if (response.ok) {
            fetchCompanySequenceTimeline(companyId);
        } else {
            alert("Failed to cancel sequence.");
        }
    } catch (err) {
        console.error(err);
    }
}

async function sendMessageDirect(messageId, companyId, btnElement) {
    btnElement.disabled = true;
    btnElement.textContent = "Sending...";
    
    try {
        const response = await fetch(`/api/v1/messages/${messageId}/send`, { method: "POST" });
        if (response.ok) {
            alert("Email sent successfully!");
            fetchCompanySequenceTimeline(companyId);
        } else {
            const err = await response.json();
            alert("Failed to send: " + (err.detail || "Server error"));
            btnElement.disabled = false;
            btnElement.textContent = "Send Now";
        }
    } catch (err) {
        console.error(err);
        btnElement.disabled = false;
        btnElement.textContent = "Send Now";
    }
}




