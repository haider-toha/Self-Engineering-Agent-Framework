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

// State
let isProcessing = false;
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

// Form Submission
queryForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const prompt = userPrompt.value.trim();
    
    if (!prompt) {
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
    socket.emit('query', { prompt: prompt });
    
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
            addLog('info', 'Generating natural language response...');
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
            // Skip this verbose message for cleaner logs
            break;
        
        case 'plan_complete':
            // Only log for complex strategies to reduce verbosity
            if (data.strategy !== 'single_tool') {
                addLog('success', `Execution plan: ${data.strategy} - ${data.reasoning}`);
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
            <div class="progress-icon">🚀</div>
            <div class="progress-info">
                <div class="progress-title">Processing Query</div>
                <div class="progress-subtitle">${query}</div>
            </div>
            <div class="progress-status">
                <div class="progress-stage">Initializing...</div>
                <div class="progress-time">Started ${new Date().toLocaleTimeString()}</div>
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
        'starting': '🚀',
        'searching': '🔍',
        'synthesizing': '🔨',
        'executing': '⚙️',
        'responding': '💬',
        'complete': '✅',
        'error': '❌'
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
    
    summary.querySelector('.progress-icon').textContent = stageIcon[stage] || '⚙️';
    summary.querySelector('.progress-stage').textContent = stageText[stage] || stage;
    summary.querySelector('.progress-fill').style.width = `${progress}%`;
    
    progressSummary.stage = stage;
    progressSummary.progress = progress;
}

function addLog(type, message, grouped = false) {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type} ${grouped ? 'grouped' : ''}`;
    
    const time = new Date().toLocaleTimeString();
    
    // Add better icons for different log types
    const typeIcons = {
        'info': '📝',
        'success': '✅',
        'warning': '⚠️',
        'error': '❌'
    };
    
    entry.innerHTML = `
        <div class="log-content">
            <div class="log-header">
                <span class="log-icon">${typeIcons[type] || '📝'}</span>
                <span class="log-time">${time}</span>
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
                    <span class="response-icon">🎆</span>
                    <span>Response</span>
                </div>
                <div class="response-actions">
                    <button class="copy-btn" onclick="copyResponse()" title="Copy response">
                        <span class="copy-icon">📋</span>
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
                        <strong>🔧 Tool:</strong> ${toolName} 
                        <span class="badge ${isSynthesized ? 'new' : 'existing'}">
                            ${isSynthesized ? 'NEW' : 'EXISTING'}
                        </span>
                    </div>
                    ${metadata.execution_time ? `
                        <div class="meta-item">
                            <strong>⏱️ Execution Time:</strong> ${metadata.execution_time}ms
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
        copyBtn.innerHTML = '<span class="copy-icon">✓</span> Copied!';
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
    if (isProcessing) {
        submitBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline-block';
    } else {
        submitBtn.disabled = false;
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
        const timestamp = new Date(tool.timestamp).toLocaleString();
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
    document.getElementById('modal-tool-timestamp').textContent = new Date(tool.timestamp).toLocaleString();
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

