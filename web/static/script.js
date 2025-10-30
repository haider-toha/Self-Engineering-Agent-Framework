// Self-Engineering Agent Framework - Frontend JavaScript

// Initialize Socket.IO connection
const socket = io();

// DOM Elements
const queryForm = document.getElementById('query-form');
const userPrompt = document.getElementById('user-prompt');
const submitBtn = document.getElementById('submit-btn');
const btnText = document.getElementById('btn-text');
const btnLoader = document.getElementById('btn-loader');
const activityLog = document.getElementById('activity-log');
const responseContainer = document.getElementById('response-container');
const toolsList = document.getElementById('tools-list');
const toolCount = document.getElementById('tool-count');
const statusIndicator = document.getElementById('status');
const startSessionBtn = document.getElementById('start-session-btn');
const resetSessionBtn = document.getElementById('reset-session-btn');
const sessionIdDisplay = document.getElementById('session-id-display');
const conversationHistory = document.getElementById('conversation-history');

// State
let isProcessing = false;
let currentSessionId = null;
let isSessionInitializing = false;
let currentWorkflow = null;
let progressSummary = {
    stage: 'idle',
    progress: 0,
    totalSteps: 0,
    currentStep: 0,
    startTime: null
};

// Socket.IO Event Handlers
socket.on('connect', () => {
    console.log('Connected to agent');
    updateStatus('Connected', 'success');
    loadTools();
    updateSessionDisplay();
    if (currentSessionId) {
        fetchSessionMessages(currentSessionId);
    }
});

socket.on('disconnect', () => {
    console.log('Disconnected from agent');
    updateStatus('Disconnected', 'error');
});

socket.on('tool_count', (data) => {
    toolCount.textContent = data.count;
});

socket.on('agent_event', (data) => {
    handleAgentEvent(data.event_type, data.data);
});

socket.on('query_complete', (data) => {
    isProcessing = false;
    updateButtonState();
    
    if (data.session_id) {
        currentSessionId = data.session_id;
        updateSessionDisplay();
    }

    if (data.success) {
        displayResponse(data.response, data.metadata);
        addLog('success', '✓ Request completed successfully');
        updateStatus('Ready', 'success');
    } else {
        displayError(data.response);
        addLog('error', '✗ Request failed');
        updateStatus('Error', 'error');
    }
    
    // Reload tools list
    loadTools();
});

socket.on('error', (data) => {
    isProcessing = false;
    updateButtonState();
    addLog('error', `Error: ${data.message}`);
    updateStatus('Error', 'error');
});

socket.on('session_memory', (data) => {
    if (!data || !data.session_id) {
        return;
    }

    if (data.session_id !== currentSessionId) {
        return;
    }

    renderConversationHistory(data.messages || []);
});

// Form Submission
queryForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const prompt = userPrompt.value.trim();
    
    if (!prompt) {
        return;
    }
    
    if (!currentSessionId) {
        addLog('warning', 'Start a session before sending a query.');
        updateStatus('Session required', 'warning');
        return;
    }

    if (isProcessing) {
        return;
    }
    
    // Clear previous response
    responseContainer.innerHTML = '<p class="placeholder">Processing...</p>';
    
    // Clear activity log and initialize progress
    activityLog.innerHTML = '';
    initializeProgressSummary(prompt);
    
    // Send query
    socket.emit('query', { prompt: prompt, session_id: currentSessionId });
    
    // Update UI
    isProcessing = true;
    updateButtonState();
    updateStatus('Processing', 'warning');
    
    addLog('info', `Query: ${prompt}`);
});

// Example button clicks
document.querySelectorAll('.example-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        userPrompt.value = btn.getAttribute('data-prompt');
        userPrompt.focus();
    });
});

if (startSessionBtn) {
    startSessionBtn.addEventListener('click', () => {
        if (isSessionInitializing) {
            return;
        }
        startNewSession();
    });
}

if (resetSessionBtn) {
    resetSessionBtn.addEventListener('click', () => {
        if (!currentSessionId) {
            return;
        }
        resetSession();
    });
}

// Event Handlers
function handleAgentEvent(eventType, data) {
    console.log('Agent event:', eventType, data);
    
    switch (eventType) {
        case 'orphans_cleaned':
            addLog('info', `Found and removed ${data.count} orphaned tool(s) from the database.`);
            break;
            
        case 'searching':
            updateProgressSummary('searching');
            addLog('info', 'Searching for existing capability...');
            break;
            
        case 'tool_found':
            addLog('success', `Found tool: ${data.tool_name} (similarity: ${(data.similarity * 100).toFixed(1)}%)`);
            break;
            
        case 'tool_mismatch':
            addLog('warning', `Tool mismatch: ${data.tool_name} - ${data.error}`);
            break;
            
        case 'no_tool_found':
            addLog('warning', 'No matching tool found');
            break;
            
        case 'entering_synthesis_mode':
            updateProgressSummary('synthesizing', 0, 5);
            addLog('warning', 'Entering synthesis mode - creating new capability...');
            break;
            
        case 'synthesis_step':
            handleSynthesisStep(data);
            break;
            
        case 'synthesis_successful':
            addLog('success', `Successfully synthesized: ${data.tool_name}`);
            break;
            
        case 'synthesis_failed':
            addLog('error', `Synthesis failed at ${data.step}: ${data.error}`);
            break;
            
        case 'executing':
            updateProgressSummary('executing');
            addLog('info', `Executing tool: ${data.tool_name}`);
            break;
            
        case 'execution_complete':
            addLog('success', `Execution complete: ${data.result}`);
            break;
            
        case 'execution_failed':
            addLog('error', `Execution failed: ${data.error}`);
            break;
            
        case 'synthesizing_response':
            updateProgressSummary('responding');
            addLog('info', 'Generating response...');
            break;
            
        case 'complete':
            updateProgressSummary('complete', 1, 1);
            addLog('success', 'Request complete.');
            break;
            
        case 'error':
            addLog('error', `Error: ${data.error}`);
            break;
        
        // Workflow & Composition Events
        case 'planning_query':
            addLog('info', 'Analyzing query complexity and planning execution strategy...');
            break;
        
        case 'plan_complete':
            addLog('success', `Strategy selected: ${data.strategy}`);
            if (data.reasoning) {
                addLog('info', `Reasoning: ${data.reasoning}`);
            }
            break;
        
        case 'using_composite_tool':
            addLog('success', `Using composite tool: ${data.tool_name}`);
            addLog('info', `   Components: ${data.component_tools.join(' → ')}`);
            break;
        
        case 'using_workflow_pattern':
            addLog('success', `Using workflow pattern: ${data.pattern_name}`);
            addLog('info', `   Sequence: ${data.tool_sequence.join(' → ')}`);
            break;
        
        case 'multi_tool_workflow':
            addLog('info', `Multi-tool workflow detected: ${data.num_tasks} steps`);
            break;
        
        case 'workflow_start':
            addLog('info', `Starting workflow with ${data.total_steps} step(s)`);
            data.tasks.forEach((task, idx) => {
                addLog('info', `   ${idx + 1}. ${task}`);
            });
            break;
        
        case 'workflow_step':
            addLog('info', `Step ${data.step}/${data.total}: ${data.task}`);
            break;
        
        case 'workflow_step_tool_found':
            addLog('success', `   Found: ${data.tool_name} (${(data.similarity * 100).toFixed(1)}% match)`);
            break;
        
        case 'workflow_step_executing':
            addLog('info', `   Executing: ${data.tool_name}`);
            break;
        
        case 'workflow_step_complete':
            // Truncate long results for better readability
            let result = data.result;
            if (typeof result === 'string' && result.length > 200) {
                result = result.substring(0, 200) + '...';
            }
            addLog('success', `   Step complete: ${result}`);
            break;
        
        case 'workflow_step_failed':
            addLog('error', `   Step failed: ${data.error}`);
            break;
        
        case 'workflow_step_needs_synthesis':
            addLog('warning', `   Step ${data.step} needs new tool creation`);
            break;
        
        case 'workflow_complete':
            addLog('success', `Workflow complete! ${data.total_steps} steps executed`);
            addLog('info', `   Tool sequence: ${data.tool_sequence.join(' → ')}`);
            break;
        
        case 'pattern_execution_start':
            addLog('info', `Executing pattern: ${data.pattern_name}`);
            break;
        
        case 'pattern_step':
            addLog('info', `   Step ${data.step}/${data.total}: ${data.tool_name}`);
            break;
        
        case 'pattern_step_complete':
            addLog('success', `   ✓ ${data.tool_name}: ${data.result}`);
            break;
        
        case 'pattern_execution_complete':
            addLog('success', `Pattern complete: ${data.pattern_name}`);
            break;
        
        case 'workflow_needs_synthesis':
            addLog('warning', `Workflow requires new tool at step ${data.step_failed}`);
            break;
        
        case 'workflow_step_synthesizing':
            addLog('info', `Creating new tool for step ${data.step}: ${data.task}`);
            break;
        
        case 'workflow_retry':
            addLog('success', `Retrying workflow - ${data.reason}`);
            break;
    }
}

// Session Management ------------------------------------------------------
const defaultPromptPlaceholder = userPrompt ? userPrompt.getAttribute('placeholder') : '';

function setFormEnabled(enabled) {
    if (!userPrompt || !submitBtn) {
        return;
    }

    userPrompt.disabled = !enabled;
    submitBtn.disabled = !enabled || isProcessing;

    if (!enabled) {
        userPrompt.value = '';
        userPrompt.setAttribute('placeholder', 'Start a session to send a request');
    } else {
        userPrompt.setAttribute('placeholder', defaultPromptPlaceholder);
        userPrompt.focus();
    }
}

function updateSessionDisplay() {
    if (sessionIdDisplay) {
        sessionIdDisplay.textContent = currentSessionId || 'Not started';
        sessionIdDisplay.classList.toggle('active', Boolean(currentSessionId));
    }

    if (resetSessionBtn) {
        resetSessionBtn.disabled = !currentSessionId;
    }

    if (startSessionBtn) {
        startSessionBtn.disabled = isSessionInitializing;
        startSessionBtn.textContent = isSessionInitializing ? 'Creating...' : (currentSessionId ? 'Start Fresh Session' : 'Start New Session');
    }

    if (!currentSessionId || isSessionInitializing) {
        setFormEnabled(false);
    } else if (!isProcessing) {
        setFormEnabled(true);
    }

    updateButtonState();
}

async function startNewSession() {
    if (isSessionInitializing) {
        return;
    }

    try {
        isSessionInitializing = true;
        updateSessionDisplay();
        updateStatus('Starting session…', 'info');

        const response = await fetch('/api/session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to create session');
        }

        currentSessionId = data.session_id;
        addLog('success', `New session started: ${currentSessionId}`);
        updateStatus('Session ready', 'success');
        renderConversationHistory([]);
        await fetchSessionMessages(currentSessionId);
    } catch (error) {
        console.error('Failed to start session:', error);
        addLog('error', `Session error: ${error.message}`);
        updateStatus('Session error', 'error');
    } finally {
        isSessionInitializing = false;
        updateSessionDisplay();
    }
}

function resetSession() {
    currentSessionId = null;
    renderConversationHistory([]);
    updateSessionDisplay();
    updateStatus('Session reset', 'warning');
    addLog('warning', 'Session reset. Start a new session to continue.');
}

async function fetchSessionMessages(sessionId) {
    if (!sessionId) {
        renderConversationHistory([]);
        return;
    }

    try {
        const response = await fetch(`/api/session/${sessionId}/messages?limit=10`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to fetch session messages');
        }

        renderConversationHistory(data.messages || []);
    } catch (error) {
        console.error('Failed to load session messages:', error);
        renderConversationHistory([]);
    }
}

function renderConversationHistory(messages) {
    if (!conversationHistory) {
        return;
    }

    if (!messages || messages.length === 0) {
        const placeholderText = currentSessionId ? 'No messages yet. Submit a prompt to build session memory.' : 'Start a session to enable memory.';
        conversationHistory.innerHTML = `<p class="placeholder">${placeholderText}</p>`;
        return;
    }

    conversationHistory.innerHTML = '';

    messages.forEach((message) => {
        const wrapper = document.createElement('div');
        const role = message.role === 'user' ? 'user' : 'assistant';
        wrapper.className = `conversation-message ${role}`;

        const roleLabel = role === 'user' ? 'You' : 'Agent';
        wrapper.innerHTML = `
            <span class="message-role">${roleLabel}</span>
            <p class="message-content">${escapeHtml(message.content || '')}</p>
        `;

        conversationHistory.appendChild(wrapper);
    });

    conversationHistory.scrollTop = conversationHistory.scrollHeight;
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

updateSessionDisplay();
renderConversationHistory([]);

function handleSynthesisStep(data) {
    const stepNames = {
        'specification': 'Generating function specification',
        'tests': 'Generating test suite',
        'implementation': 'Implementing function',
        'verification': 'Verifying in sandbox',
        'registration': 'Registering new tool'
    };
    
    const stepOrder = ['specification', 'tests', 'implementation', 'verification', 'registration'];
    const stepNumber = stepOrder.indexOf(data.step) + 1;
    
    const stepName = stepNames[data.step] || data.step;
    
    if (data.status === 'in_progress') {
        updateProgressSummary('synthesizing', stepNumber - 1, 5);
        addLog('info', `${stepName}...`, true);
    } else if (data.status === 'complete') {
        updateProgressSummary('synthesizing', stepNumber, 5);
        addLog('success', `${stepName} complete`, true);
    } else if (data.status === 'failed') {
        updateProgressSummary('error');
        addLog('error', `${stepName} failed: ${data.error}`, true);
    }
}

// UI Update Functions
function initializeProgressSummary(query) {
    progressSummary = {
        stage: 'starting',
        progress: 0,
        totalSteps: 0,
        currentStep: 0,
        startTime: new Date()
    };
    
    const summaryCard = document.createElement('div');
    summaryCard.id = 'progress-summary';
    summaryCard.className = 'progress-summary';
    summaryCard.innerHTML = `
        <div class="progress-header">
            <div class="progress-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/>
                </svg>
            </div>
            <div class="progress-info">
                <div class="progress-title">Processing Query</div>
                <div class="progress-subtitle">${query}</div>
            </div>
            <div class="progress-status">
                <div class="progress-stage">Initializing...</div>
            </div>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: 0%"></div>
        </div>
    `;
    
    activityLog.appendChild(summaryCard);
}

function updateProgressSummary(stage, step = null, total = null) {
    const summary = document.getElementById('progress-summary');
    if (!summary) return;
    
    if (step !== null) progressSummary.currentStep = step;
    if (total !== null) progressSummary.totalSteps = total;
    
    const progress = progressSummary.totalSteps > 0 ? 
        (progressSummary.currentStep / progressSummary.totalSteps) * 100 : 0;
    
    const stageIcon = {
        'starting': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/></svg>',
        'searching': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>',
        'synthesizing': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>',
        'executing': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 6v6m5.2-14.8l-4.2 4.2m-1.8 1.8l-4.2 4.2M23 12h-6m-6 0H5m14.8 5.2l-4.2-4.2m-1.8-1.8l-4.2-4.2"/></svg>',
        'responding': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
        'complete': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        'error': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
    };
    
    const stageText = {
        'starting': 'Initializing...',
        'searching': 'Searching for tools...',
        'synthesizing': 'Creating new capability...',
        'executing': 'Executing tool...',
        'responding': 'Generating response...',
        'complete': 'Complete!',
        'error': 'Error occurred'
    };
    
    summary.querySelector('.progress-icon').innerHTML = stageIcon[stage] || stageIcon['executing'];
    summary.querySelector('.progress-stage').textContent = stageText[stage] || stage;
    summary.querySelector('.progress-fill').style.width = `${progress}%`;
    
    progressSummary.stage = stage;
    progressSummary.progress = progress;
}

function addLog(type, message, grouped = false) {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type} ${grouped ? 'grouped' : ''}`;
    
    // Add better icons for different log types
    const typeIcons = {
        'info': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
        'success': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        'warning': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        'error': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
    };
    
    entry.innerHTML = `
        <div class="log-content">
            <div class="log-header">
                <span class="log-icon">${typeIcons[type] || typeIcons['info']}</span>
            </div>
            <div class="log-message">${message}</div>
        </div>
    `;
    
    activityLog.appendChild(entry);
    activityLog.scrollTop = activityLog.scrollHeight;
}

function displayResponse(response, metadata) {
    const isSynthesized = metadata.synthesized;
    const toolName = metadata.tool_name;
    
    // Enhanced response with better formatting
    const formattedResponse = formatResponse(response);
    
    responseContainer.innerHTML = `
        <div class="response-content">
            <div class="response-header">
                <div class="response-title">
                    <span class="response-icon">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                        </svg>
                    </span>
                    <span>Response</span>
                </div>
                <div class="response-actions">
                    <button class="copy-btn" onclick="copyResponse()" title="Copy response">
                        <span class="copy-icon">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                            </svg>
                        </span>
                        Copy
                    </button>
                </div>
            </div>
            <div class="response-body">
                ${formattedResponse}
            </div>
            ${metadata ? `
                <div class="response-meta">
                    <div class="meta-item">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
                        </svg>
                        <strong>Tool:</strong> ${toolName} 
                        <span class="badge ${isSynthesized ? 'new' : 'existing'}">
                            ${isSynthesized ? 'NEW' : 'EXISTING'}
                        </span>
                    </div>
                    ${metadata.execution_time ? `
                        <div class="meta-item">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="12" cy="12" r="10"/>
                                <polyline points="12 6 12 12 16 14"/>
                            </svg>
                            <strong>Execution Time:</strong> ${metadata.execution_time}ms
                        </div>
                    ` : ''}
                </div>
            ` : ''}
        </div>
    `;
}

function formatResponse(response) {
    // Handle different response formats
    if (typeof response !== 'string') {
        response = JSON.stringify(response, null, 2);
    }
    
    // Convert markdown-style formatting
    let formatted = response
        // Bold text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Code blocks
        .replace(/```([\s\S]*?)```/g, '<pre class="code-block"><code>$1</code></pre>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
        // Lists
        .replace(/^- (.+)$/gm, '<li>$1</li>');
    
    // Wrap lists in ul tags
    if (formatted.includes('<li>')) {
        formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul class="response-list">$1</ul>');
    }
    
    // Handle percentage data (like the profit margins example)
    formatted = formatted.replace(/(\d+\.\d+%)/g, '<span class="percentage">$1</span>');
    
    // Handle product names or items in quotes
    formatted = formatted.replace(/"([^"]+)"/g, '<span class="quoted-text">"$1"</span>');
    
    return `<div class="formatted-response">${formatted}</div>`;
}

function copyResponse() {
    const responseText = responseContainer.querySelector('.response-body').textContent;
    navigator.clipboard.writeText(responseText).then(() => {
        const copyBtn = responseContainer.querySelector('.copy-btn');
        const originalText = copyBtn.innerHTML;
        copyBtn.innerHTML = `
            <span class="copy-icon">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"/>
                </svg>
            </span>
            Copied!`;
        copyBtn.classList.add('copied');
        
        setTimeout(() => {
            copyBtn.innerHTML = originalText;
            copyBtn.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy response:', err);
    });
}

function displayError(errorMessage) {
    responseContainer.innerHTML = `
        <div class="response-content" style="color: var(--danger-color);">
            <p><strong>Error:</strong> ${errorMessage}</p>
        </div>
    `;
}

function updateButtonState() {
    if (!submitBtn || !btnText || !btnLoader) {
        return;
    }

    const disableSubmit = isProcessing || !currentSessionId || isSessionInitializing;

    submitBtn.disabled = disableSubmit;

    if (isProcessing) {
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline-block';
    } else {
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
    }
}

function updateStatus(text, type) {
    statusIndicator.textContent = text;
    statusIndicator.className = 'stat-value status-indicator';
    
    if (type === 'success') {
        statusIndicator.style.color = 'var(--success-color)';
    } else if (type === 'error') {
        statusIndicator.style.color = 'var(--danger-color)';
    } else if (type === 'warning') {
        statusIndicator.style.color = 'var(--warning-color)';
    } else {
        statusIndicator.style.color = 'var(--info-color)';
    }
}

function formatTimestamp(timestamp) {
    if (!timestamp) {
        return 'Unknown';
    }
    
    // Try to parse the timestamp
    const date = new Date(timestamp);
    
    // Check if the date is valid
    if (isNaN(date.getTime())) {
        // If timestamp is a number (Unix timestamp in seconds), convert to milliseconds
        if (!isNaN(timestamp)) {
            const dateFromNumber = new Date(timestamp * 1000);
            if (!isNaN(dateFromNumber.getTime())) {
                return dateFromNumber.toLocaleString();
            }
        }
        return 'Unknown';
    }
    
    return date.toLocaleString();
}

function loadTools() {
    fetch('/api/tools')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayTools(data.tools);
            } else {
                toolsList.innerHTML = '<p class="placeholder">Failed to load tools</p>';
            }
        })
        .catch(error => {
            console.error('Error loading tools:', error);
            toolsList.innerHTML = '<p class="placeholder">Error loading tools</p>';
        });
}

function displayTools(tools) {
    if (tools.length === 0) {
        toolsList.innerHTML = '<p class="placeholder">No tools available. Ask the agent to perform a task to generate one.</p>';
        return;
    }
    
    toolsList.innerHTML = tools.map(tool => {
        const timestamp = formatTimestamp(tool.timestamp);
        const description = tool.docstring.split('\n')[0] || 'No description';
        
        return `
            <div class="tool-card" data-tool-name="${tool.name}">
                <div class="tool-name">${tool.name}</div>
                <div class="tool-description">${description}</div>
                <div class="tool-timestamp">Created: ${timestamp}</div>
            </div>
        `;
    }).join('');
    
    // Add click event listeners to tool cards
    document.querySelectorAll('.tool-card').forEach(card => {
        card.addEventListener('click', () => {
            const toolName = card.getAttribute('data-tool-name');
            showToolDetails(toolName);
        });
    });
}

// Modal functionality
function showToolDetails(toolName) {
    fetch(`/api/tools/${toolName}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                populateModal(data.tool);
                document.getElementById('tool-modal').style.display = 'block';
            } else {
                console.error('Failed to load tool details:', data.error);
            }
        })
        .catch(error => {
            console.error('Error loading tool details:', error);
        });
}

function populateModal(tool) {
    document.getElementById('modal-tool-name').textContent = tool.name;
    document.getElementById('modal-tool-description').textContent = tool.docstring;
    document.getElementById('modal-tool-timestamp').textContent = formatTimestamp(tool.timestamp);
    document.getElementById('modal-tool-filepath').textContent = tool.file_path;
    document.getElementById('modal-tool-code').textContent = tool.code;
    document.getElementById('modal-test-code').textContent = tool.test_code;
}

function closeModal() {
    document.getElementById('tool-modal').style.display = 'none';
}

// Initialize modal event listeners
document.addEventListener('DOMContentLoaded', () => {
    console.log('Self-Engineering Agent Framework - Frontend Initialized');
    loadTools();
    
    // Modal close functionality
    document.getElementById('modal-close').addEventListener('click', closeModal);
    
    // Close modal when clicking outside
    window.addEventListener('click', (event) => {
        const modal = document.getElementById('tool-modal');
        if (event.target === modal) {
            closeModal();
        }
    });
    
    // Close modal with Escape key
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeModal();
        }
    });
});

