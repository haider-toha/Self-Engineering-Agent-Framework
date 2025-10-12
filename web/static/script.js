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
    
    // Clear activity log
    activityLog.innerHTML = '';
    
    // Send query
    socket.emit('query', { prompt: prompt });
    
    // Update UI
    isProcessing = true;
    updateButtonState();
    updateStatus('Processing', 'warning');
    
    addLog('info', `📝 Query: ${prompt}`);
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
            addLog('info', `🧹 Found and removed ${data.count} orphaned tool(s) from the database.`);
            break;
            
        case 'searching':
            addLog('info', '🔍 Searching for existing capability...');
            break;
            
        case 'tool_found':
            addLog('success', `✓ Found tool: ${data.tool_name} (similarity: ${(data.similarity * 100).toFixed(1)}%)`);
            break;
            
        case 'tool_mismatch':
            addLog('warning', `⚠ Tool mismatch: ${data.tool_name} - ${data.error}`);
            break;
            
        case 'no_tool_found':
            addLog('warning', '⚠ No matching tool found');
            break;
            
        case 'entering_synthesis_mode':
            addLog('warning', '🔧 Entering synthesis mode - creating new capability...');
            break;
            
        case 'synthesis_step':
            handleSynthesisStep(data);
            break;
            
        case 'synthesis_successful':
            addLog('success', `✓ Successfully synthesized: ${data.tool_name}`);
            break;
            
        case 'synthesis_failed':
            addLog('error', `✗ Synthesis failed at ${data.step}: ${data.error}`);
            break;
            
        case 'executing':
            addLog('info', `⚙️ Executing tool: ${data.tool_name}`);
            break;
            
        case 'execution_complete':
            addLog('success', `✓ Execution complete: ${data.result}`);
            break;
            
        case 'execution_failed':
            addLog('error', `✗ Execution failed: ${data.error}`);
            break;
            
        case 'synthesizing_response':
            addLog('info', '💬 Generating natural language response...');
            break;
            
        case 'complete':
            addLog('success', '✓ All done!');
            break;
            
        case 'error':
            addLog('error', `✗ Error: ${data.error}`);
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
    
    const stepName = stepNames[data.step] || data.step;
    
    if (data.status === 'in_progress') {
        addLog('info', `⏳ ${stepName}...`);
    } else if (data.status === 'complete') {
        addLog('success', `✓ ${stepName} complete`);
    } else if (data.status === 'failed') {
        addLog('error', `✗ ${stepName} failed: ${data.error}`);
    }
}

// UI Update Functions
function addLog(type, message) {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    
    const time = new Date().toLocaleTimeString();
    
    entry.innerHTML = `
        <span class="log-time">${time}</span>
        <span class="log-message">${message}</span>
    `;
    
    activityLog.appendChild(entry);
    activityLog.scrollTop = activityLog.scrollHeight;
}

function displayResponse(response, metadata) {
    const isSynthesized = metadata.synthesized;
    const toolName = metadata.tool_name;
    
    responseContainer.innerHTML = `
        <div class="response-content">
            <p>${response}</p>
            ${metadata ? `
                <div class="response-meta">
                    <strong>Tool:</strong> ${toolName} 
                    <span class="badge ${isSynthesized ? 'new' : 'existing'}">
                        ${isSynthesized ? 'NEW' : 'EXISTING'}
                    </span>
                </div>
            ` : ''}
        </div>
    `;
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
        toolsList.innerHTML = '<p class="placeholder">No tools available yet. Try asking the agent to do something!</p>';
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

