/**
 * MCP Benchmark Dashboard - Main Application Logic
 * 
 * Handles:
 * - User interactions
 * - API calls to backend
 * - UI updates
 * - Results display
 */

// Define API base URL for all endpoint calls
const API_BASE = '';

// Store current query results for comparison
let currentQueryResults = {
    query: '',
    traditional: null,
    codeExecution: null
};

// Cache DOM elements for main controls
const elements = {
    queryInput: document.getElementById('queryInput'),
    btnTraditional: document.getElementById('btnTraditional'),
    btnCodeExecution: document.getElementById('btnCodeExecution'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    loadingText: document.getElementById('loadingText')
};

// Cache DOM elements for Traditional MCP results display
const traditionalElements = {
    status: document.getElementById('traditionalStatus'),
    time: document.getElementById('traditionalTime'),
    calls: document.getElementById('traditionalCalls'),
    tokens: document.getElementById('traditionalTokens'),
    promptTokens: document.getElementById('traditionalPromptTokens'),
    completionTokens: document.getElementById('traditionalCompletionTokens'),
    output: document.getElementById('traditionalOutput')
};

// Cache DOM elements for Code Execution MCP results display
const codeExecElements = {
    status: document.getElementById('codeExecStatus'),
    time: document.getElementById('codeExecTime'),
    calls: document.getElementById('codeExecCalls'),
    tokens: document.getElementById('codeExecTokens'),
    promptTokens: document.getElementById('codeExecPromptTokens'),
    completionTokens: document.getElementById('codeExecCompletionTokens'),
    output: document.getElementById('codeExecOutput')
};

/**
 * Initialize event listeners for user interactions
 */
function initializeEventListeners() {
    // Attach click handler for Traditional MCP button
    elements.btnTraditional.addEventListener('click', () => runBenchmark('traditional'));
    
    // Attach click handler for Code Execution MCP button
    elements.btnCodeExecution.addEventListener('click', () => runBenchmark('code-execution'));
}

/**
 * Show loading overlay with custom message
 * @param {string} message - Loading message to display
 */
function showLoading(message = 'Processing...') {
    // Set loading text
    elements.loadingText.textContent = message;
    
    // Show overlay by adding active class
    elements.loadingOverlay.classList.add('active');
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    // Hide overlay by removing active class
    elements.loadingOverlay.classList.remove('active');
}

/**
 * Disable all action buttons during benchmark execution
 */
function disableButtons() {
    // Disable Traditional MCP button
    elements.btnTraditional.disabled = true;
    
    // Disable Code Execution MCP button
    elements.btnCodeExecution.disabled = true;
}

/**
 * Enable all action buttons after benchmark completion
 */
function enableButtons() {
    // Enable Traditional MCP button
    elements.btnTraditional.disabled = false;
    
    // Enable Code Execution MCP button
    elements.btnCodeExecution.disabled = false;
}

/**
 * Update status badge with new status and styling
 * @param {HTMLElement} statusElement - Status badge element
 * @param {string} status - Status text
 * @param {string} className - CSS class for styling
 */
function updateStatus(statusElement, status, className) {
    // Set status text
    statusElement.textContent = status;
    
    // Apply CSS class for styling
    statusElement.className = `status-badge ${className}`;
}

/**
 * Reset result display to initial state
 * @param {object} uiElements - UI elements object for specific approach
 */
function resetResultDisplay(uiElements) {
    // Reset all metric displays to placeholder
    uiElements.time.textContent = '--';
    uiElements.calls.textContent = '--';
    uiElements.tokens.textContent = '--';
    uiElements.promptTokens.textContent = '--';
    uiElements.completionTokens.textContent = '--';
    
    // Reset output display
    uiElements.output.textContent = 'Waiting for execution...';
}

/**
 * Display benchmark result in UI
 * @param {object} result - Benchmark result data
 * @param {object} uiElements - UI elements object for specific approach
 */
function displayResult(result, uiElements) {
    // Extract benchmark data from result
    const benchmark = result.result;
    
    // Animate execution time (with 's' suffix)
    animateNumber(uiElements.time, benchmark.time, 1200, 's');
    
    // Animate number of LLM calls
    animateNumber(uiElements.calls, benchmark.llm_calls.length, 800);
    
    // Animate total tokens used
    animateNumber(uiElements.tokens, benchmark.total_tokens.total_tokens, 1500);
    
    // Animate prompt tokens
    animateNumber(uiElements.promptTokens, benchmark.total_tokens.prompt_tokens, 1000);
    
    // Animate completion tokens
    animateNumber(uiElements.completionTokens, benchmark.total_tokens.completion_tokens, 1000);
    
    // Display final output or fallback
    uiElements.output.textContent = benchmark.final_output || 'No output';
    
    // Update status based on success
    if (benchmark.success) {
        updateStatus(uiElements.status, 'Complete', 'complete');
    } else {
        updateStatus(uiElements.status, 'Error', 'error');
        uiElements.output.textContent = benchmark.error || 'Execution failed';
    }
}

/**
 * Run benchmark for specified approach
 * @param {string} approach - 'traditional' or 'code-execution'
 */
async function runBenchmark(approach) {
    // Get query text from input
    const query = elements.queryInput.value.trim();
    
    // Validate query is not empty
    if (!query) {
        alert('Please enter a query');
        return;
    }
    
    // Store current query
    currentQueryResults.query = query;
    
    // Determine which approach is being run
    const isTraditional = approach === 'traditional';
    const uiElements = isTraditional ? traditionalElements : codeExecElements;
    const approachName = isTraditional ? 'Traditional MCP' : 'Code Execution MCP';
    
    // Map approach to endpoint name
    const endpointMap = {
        'traditional': 'traditional-mcp',
        'code-execution': 'code-execution-mcp'
    };
    const endpoint = `${API_BASE}/${endpointMap[approach]}`;
    
    try {
        // Disable buttons and show loading
        disableButtons();
        showLoading(`Running ${approachName} benchmark...`);
        
        // Update status to running
        updateStatus(uiElements.status, 'Running...', 'running');
        resetResultDisplay(uiElements);
        
        // Make API call to run benchmark
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });
        
        // Check if response is successful
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Benchmark failed');
        }
        
        // Parse response JSON
        const result = await response.json();
        
        // Store result for comparison
        if (isTraditional) {
            currentQueryResults.traditional = result.result;
        } else {
            currentQueryResults.codeExecution = result.result;
        }
        
        // Display results in UI
        displayResult(result, uiElements);
        
        // Show the specific result card that was executed
        const cardId = isTraditional ? 'traditionalResult' : 'codeExecResult';
        document.getElementById(cardId).classList.add('visible');
        
        // Show results section with animation
        document.querySelector('.results-section').classList.add('visible');
        
        // Log result to console
        console.log(`${approachName} Result:`, result);
        
        // Update comparison if both results available
        if (currentQueryResults.traditional && currentQueryResults.codeExecution) {
            updateCurrentComparison();
        }
        
    } catch (error) {
        // Handle errors
        console.error(`${approachName} Error:`, error);
        updateStatus(uiElements.status, 'Error', 'error');
        uiElements.output.textContent = `Error: ${error.message}`;
        alert(`Error running ${approachName}: ${error.message}`);
    } finally {
        // Always hide loading and enable buttons
        hideLoading();
        enableButtons();
    }
}

/**
 * Update comparison section with current query results
 */
function updateCurrentComparison() {
    // Show comparison section with animation
    document.querySelector('.comparison-section').classList.add('visible');
    
    // Update comparison table with current results
    displayCurrentComparisonTable();
    
    // Update comparison chart with current results
    updateCurrentComparisonChart();
    
    // Compare and highlight the winner
    compareAndHighlightWinner();
}

/**
 * Animate number from 0 to target value with easing
 * @param {HTMLElement} element - Element to update
 * @param {number} target - Target number
 * @param {number} duration - Animation duration in milliseconds
 * @param {string} suffix - Optional suffix (e.g., 's', 'ms')
 */
function animateNumber(element, target, duration = 1000, suffix = '') {
    // Parse target if it's a string
    const targetValue = typeof target === 'string' ? parseFloat(target) : target;
    
    // Skip animation if target is invalid
    if (isNaN(targetValue)) {
        element.textContent = target + suffix;
        return;
    }
    
    // Animation start time
    const startTime = performance.now();
    const startValue = 0;
    
    // Easing function (ease-out cubic)
    const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
    
    // Animation frame function
    function animate(currentTime) {
        // Calculate progress (0 to 1)
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Apply easing
        const easedProgress = easeOutCubic(progress);
        
        // Calculate current value
        const currentValue = startValue + (targetValue - startValue) * easedProgress;
        
        // Update element text with proper formatting
        if (targetValue % 1 === 0) {
            // Integer display
            element.textContent = Math.floor(currentValue) + suffix;
        } else {
            // Decimal display (preserve original decimal places)
            const decimalPlaces = target.toString().split('.')[1]?.length || 2;
            element.textContent = currentValue.toFixed(decimalPlaces) + suffix;
        }
        
        // Continue animation if not complete
        if (progress < 1) {
            requestAnimationFrame(animate);
        }
    }
    
    // Start animation
    requestAnimationFrame(animate);
}

/**
 * Compare both benchmark results and highlight the winner
 */
function compareAndHighlightWinner() {
    // Get both result objects
    const traditional = currentQueryResults.traditional;
    const codeExec = currentQueryResults.codeExecution;
    
    // Exit if both results aren't available
    if (!traditional || !codeExec) {
        return;
    }
    
    // Get card elements
    const traditionalCard = document.getElementById('traditionalResult');
    const codeExecCard = document.getElementById('codeExecResult');
    
    // Remove existing winner classes
    traditionalCard.classList.remove('winner', 'loser');
    codeExecCard.classList.remove('winner', 'loser');
    
    // Remove existing improvement stats
    const existingStats = document.querySelectorAll('.improvement-stats');
    existingStats.forEach(stats => stats.remove());
    
    // Compare execution times
    const traditionalTime = traditional.time;
    const codeExecTime = codeExec.time;
    
    // Calculate time difference and percentage
    const timeDiff = Math.abs(traditionalTime - codeExecTime);
    const timePercentDiff = ((timeDiff / Math.max(traditionalTime, codeExecTime)) * 100).toFixed(1);
    
    // Compare token usage
    const traditionalTokens = extractTotalTokens(traditional);
    const codeExecTokens = extractTotalTokens(codeExec);
    
    // Calculate token difference and percentage
    const tokenDiff = Math.abs(traditionalTokens - codeExecTokens);
    const tokenPercentDiff = ((tokenDiff / Math.max(traditionalTokens, codeExecTokens)) * 100).toFixed(1);
    
    // Normalize scores (0-1 range) for fair comparison
    const maxTime = Math.max(traditionalTime, codeExecTime);
    const maxTokens = Math.max(traditionalTokens, codeExecTokens);
    
    // Calculate normalized scores (lower is better)
    const traditionalTimeScore = traditionalTime / maxTime;
    const codeExecTimeScore = codeExecTime / maxTime;
    const traditionalTokenScore = traditionalTokens / maxTokens;
    const codeExecTokenScore = codeExecTokens / maxTokens;
    
    // Calculate combined scores with equal weighting (50% time + 50% tokens)
    const traditionalCombinedScore = (traditionalTimeScore * 0.5) + (traditionalTokenScore * 0.5);
    const codeExecCombinedScore = (codeExecTimeScore * 0.5) + (codeExecTokenScore * 0.5);
    
    // Determine overall winner based on combined score (lower is better)
    const overallWinner = traditionalCombinedScore < codeExecCombinedScore ? 'traditional' : 'codeExec';
    const winnerCard = overallWinner === 'traditional' ? traditionalCard : codeExecCard;
    const loserCard = overallWinner === 'traditional' ? codeExecCard : traditionalCard;
    
    // Determine which metrics the winner excels at
    const timeWinner = traditionalTime < codeExecTime ? 'traditional' : 'codeExec';
    const tokenWinner = traditionalTokens < codeExecTokens ? 'traditional' : 'codeExec';
    
    // Build improvement text based on winner's strengths
    let improvementText = '';
    
    if (timeWinner === overallWinner && tokenWinner === overallWinner) {
        // Winner is better in both metrics
        improvementText = `${timePercentDiff}% Faster & ${tokenPercentDiff}% Fewer Tokens`;
    } else if (timeWinner === overallWinner) {
        // Winner is faster but uses more tokens
        improvementText = `${timePercentDiff}% Faster`;
    } else if (tokenWinner === overallWinner) {
        // Winner uses fewer tokens but is slower
        improvementText = `${tokenPercentDiff}% Fewer Tokens`;
    } else {
        // Winner by combined score
        improvementText = `Better Overall Performance`;
    }
    
    // Add winner/loser classes
    winnerCard.classList.add('winner');
    loserCard.classList.add('loser');
    
    // Create improvement stats element (below title)
    const improvementStats = document.createElement('div');
    improvementStats.className = 'improvement-stats';
    improvementStats.innerHTML = `${improvementText}`;
    
    // Insert improvement stats after card header
    const cardHeader = winnerCard.querySelector('.card-header');
    cardHeader.insertAdjacentElement('afterend', improvementStats);
    
    // Log comparison results
    console.log('Benchmark Comparison:', {
        timeWinner,
        timeDifference: `${timePercentDiff}%`,
        tokenWinner,
        tokenDifference: `${tokenPercentDiff}%`,
        overallWinner
    });
}

/**
 * Display comparison table for current query only
 */
function displayCurrentComparisonTable() {
    // Get table body element
    const tbody = document.getElementById('comparisonTableBody');
    tbody.innerHTML = '';
    
    // Format timestamp
    const now = new Date();
    const formattedDate = now.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    
    // Add Traditional MCP row
    if (currentQueryResults.traditional) {
        const row1 = document.createElement('tr');
        row1.innerHTML = `
            <td>${truncateText(currentQueryResults.query, 50)}</td>
            <td>Traditional MCP</td>
            <td>${currentQueryResults.traditional.time.toFixed(2)}s</td>
            <td>${extractTotalTokens(currentQueryResults.traditional).toLocaleString()}</td>
            <td>${currentQueryResults.traditional.llm_calls?.length || 0}</td>
            <td>${currentQueryResults.traditional.success ? '✅' : '❌'}</td>
            <td>${formattedDate}</td>
        `;
        tbody.appendChild(row1);
    }
    
    // Add Code Execution MCP row
    if (currentQueryResults.codeExecution) {
        const row2 = document.createElement('tr');
        row2.innerHTML = `
            <td>${truncateText(currentQueryResults.query, 50)}</td>
            <td>Code Execution MCP</td>
            <td>${currentQueryResults.codeExecution.time.toFixed(2)}s</td>
            <td>${extractTotalTokens(currentQueryResults.codeExecution).toLocaleString()}</td>
            <td>${currentQueryResults.codeExecution.llm_calls?.length || 0}</td>
            <td>${currentQueryResults.codeExecution.success ? '✅' : '❌'}</td>
            <td>${formattedDate}</td>
        `;
        tbody.appendChild(row2);
    }
}

/**
 * Extract total tokens from result data handling different formats
 * @param {object} result - Result object containing token information
 * @returns {number} Total token count
 */
function extractTotalTokens(result) {
    // Check if tokens object exists
    if (result.tokens) {
        // Try total_tokens first (Code Execution MCP format)
        // Fall back to total (Traditional MCP format)
        return result.tokens.total_tokens || result.tokens.total || 0;
    }
    
    // Check if total_tokens exists at top level
    if (result.total_tokens) {
        return result.total_tokens.total_tokens || 0;
    }
    
    // Return 0 if no token data found
    return 0;
}

/**
 * Truncate text to specified length
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
function truncateText(text, maxLength) {
    // Return original if within limit
    if (text.length <= maxLength) return text;
    
    // Truncate and add ellipsis
    return text.substring(0, maxLength) + '...';
}

/**
 * Initialize theme toggle functionality
 */
function initializeThemeToggle() {
    // Get theme toggle button
    const themeToggle = document.getElementById('themeToggle');
    
    // Exit if button not found
    if (!themeToggle) {
        return;
    }
    
    // Load saved theme from localStorage or default to dark
    const savedTheme = localStorage.getItem('theme') || 'dark';
    
    // Apply saved theme to document
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    // Add click event listener to toggle theme
    themeToggle.addEventListener('click', () => {
        // Get current theme
        const currentTheme = document.documentElement.getAttribute('data-theme');
        
        // Toggle between dark and light
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        // Apply new theme
        document.documentElement.setAttribute('data-theme', newTheme);
        
        // Save to localStorage for persistence
        localStorage.setItem('theme', newTheme);
        
        // Log theme change
        console.log(`Theme changed to: ${newTheme}`);
    });
}

/**
 * Export current benchmark results as CSV
 */
function exportResultsAsCSV() {
    // Check if both results are available
    if (!currentQueryResults.traditional || !currentQueryResults.codeExecution) {
        alert('Please run both benchmarks before exporting');
        return;
    }
    
    // Get current timestamp for filename
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
    
    // Prepare CSV data with headers
    const csvData = [
        ['Metric', 'Traditional MCP', 'Code Execution MCP', 'Difference'],
        ['Query', currentQueryResults.query, currentQueryResults.query, '-'],
        [
            'Execution Time (s)',
            currentQueryResults.traditional.time,
            currentQueryResults.codeExecution.time,
            (currentQueryResults.traditional.time - currentQueryResults.codeExecution.time).toFixed(2)
        ],
        [
            'LLM Calls',
            currentQueryResults.traditional.llm_calls.length,
            currentQueryResults.codeExecution.llm_calls.length,
            currentQueryResults.traditional.llm_calls.length - currentQueryResults.codeExecution.llm_calls.length
        ],
        [
            'Total Tokens',
            extractTotalTokens(currentQueryResults.traditional),
            extractTotalTokens(currentQueryResults.codeExecution),
            extractTotalTokens(currentQueryResults.traditional) - extractTotalTokens(currentQueryResults.codeExecution)
        ],
        [
            'Prompt Tokens',
            currentQueryResults.traditional.total_tokens.prompt_tokens,
            currentQueryResults.codeExecution.total_tokens.prompt_tokens,
            currentQueryResults.traditional.total_tokens.prompt_tokens - currentQueryResults.codeExecution.total_tokens.prompt_tokens
        ],
        [
            'Completion Tokens',
            currentQueryResults.traditional.total_tokens.completion_tokens,
            currentQueryResults.codeExecution.total_tokens.completion_tokens,
            currentQueryResults.traditional.total_tokens.completion_tokens - currentQueryResults.codeExecution.total_tokens.completion_tokens
        ],
        ['Success', currentQueryResults.traditional.success, currentQueryResults.codeExecution.success, '-']
    ];
    
    // Convert array to CSV string
    const csvContent = csvData.map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
    
    // Create blob from CSV content
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    
    // Create download link
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    // Set link attributes
    link.setAttribute('href', url);
    link.setAttribute('download', `mcp-benchmark-comparison-${timestamp}.csv`);
    link.style.visibility = 'hidden';
    
    // Trigger download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Log export action
    console.log('Results exported as CSV');
}

/**
 * Initialize export button functionality
 */
function initializeExportButton() {
    // Get export button
    const exportBtn = document.getElementById('exportBtn');
    
    // Exit if button not found
    if (!exportBtn) {
        return;
    }
    
    // Add click event listener to export results
    exportBtn.addEventListener('click', exportResultsAsCSV);
}

/**
 * =====================================================================
 * MULTI-TASK MODE FUNCTIONALITY
 * =====================================================================
 */

let taskCounter = 0;
let multiTaskResults = null;
let multiTimeChart = null;
let multiTokenChart = null;

/**
 * Initialize multi-task mode event listeners
 */
function initializeMultiTaskMode() {
    // Initialize judge option visibility based on default selection (both)
    const judgeOptionContainer = document.getElementById('judgeOptionContainer');
    if (judgeOptionContainer) {
        // Show by default since "both" includes CE
        judgeOptionContainer.style.display = 'block';
    }
    console.log('Initializing multi-task mode...');
    
    const singleMode = document.getElementById('singleTaskMode');
    const multiMode = document.getElementById('multiTaskMode');
    const toggleBtns = document.querySelectorAll('.mode-toggle-btn');
    const addTaskBtn = document.getElementById('addTaskBtn');
    const runAllTasksBtn = document.getElementById('runAllTasksBtn');
    const clearTasksBtn = document.getElementById('clearTasksBtn');
    
    console.log('Found elements:', {
        singleMode: !!singleMode,
        multiMode: !!multiMode,
        toggleBtnsCount: toggleBtns.length,
        addTaskBtn: !!addTaskBtn,
        runAllTasksBtn: !!runAllTasksBtn,
        clearTasksBtn: !!clearTasksBtn
    });
    
    if (!singleMode || !multiMode) {
        console.error('Mode containers not found!');
        return;
    }
    
    if (toggleBtns.length === 0) {
        console.error('Toggle buttons not found!');
        return;
    }
    
    // Mode toggle functionality
    toggleBtns.forEach((btn, index) => {
        console.log(`Setting up toggle button ${index}:`, btn.dataset.mode);
        btn.addEventListener('click', (e) => {
            console.log('Toggle clicked!', btn.dataset.mode);
            const mode = btn.dataset.mode;
            
            // Update button states
            toggleBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Show/hide sections
            if (mode === 'single') {
                console.log('Switching to single mode');
                singleMode.style.display = 'block';
                multiMode.style.display = 'none';
            } else {
                console.log('Switching to multiple mode');
                singleMode.style.display = 'none';
                multiMode.style.display = 'block';
            }
        });
    });
    
    // Approach toggle functionality (CE, Traditional, or Both)
    const approachToggleBtns = document.querySelectorAll('.approach-toggle-btn');
    if (approachToggleBtns.length > 0) {
        approachToggleBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // Update button states
                approachToggleBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Update selected approach
                selectedApproach = btn.dataset.approach;
                console.log('Selected approach:', selectedApproach);
                
                // Show/hide judge option based on approach selection
                const judgeOptionContainer = document.getElementById('judgeOptionContainer');
                if (judgeOptionContainer) {
                    // Show judge option only when CE is selected (either "code_execution" or "both")
                    if (selectedApproach === 'code_execution' || selectedApproach === 'both') {
                        judgeOptionContainer.style.display = 'block';
                    } else {
                        judgeOptionContainer.style.display = 'none';
                        // Uncheck the checkbox when hiding
                        const useJudgeCheckbox = document.getElementById('useJudgeCheckbox');
                        if (useJudgeCheckbox) {
                            useJudgeCheckbox.checked = false;
                        }
                    }
                }
                
                // Update UI visibility based on selection (if results are displayed)
                const resultsSection = document.getElementById('multiTaskResults');
                if (resultsSection && resultsSection.style.display === 'block') {
                    updateResultsVisibility(selectedApproach);
                    // Re-render charts if they exist
                    if (multiTaskResults) {
                        displayMultiTaskCharts(multiTaskResults);
                    }
                }
            });
        });
    }
    
    // Add task button
    if (addTaskBtn) {
        addTaskBtn.addEventListener('click', addTaskItem);
    }
    
    // Upload tasks button
    const uploadTasksBtn = document.getElementById('uploadTasksBtn');
    const uploadTasksFile = document.getElementById('uploadTasksFile');
    if (uploadTasksBtn && uploadTasksFile) {
        uploadTasksBtn.addEventListener('click', () => uploadTasksFile.click());
        uploadTasksFile.addEventListener('change', handleTasksFileUpload);
    }
    
    // Run all tasks button
    if (runAllTasksBtn) {
        runAllTasksBtn.addEventListener('click', runAllTasks);
    }
    
    // Clear tasks button
    if (clearTasksBtn) {
        clearTasksBtn.addEventListener('click', clearAllTasks);
    }
    
    // Download results button (will be visible after running tasks)
    const downloadBtn = document.getElementById('downloadResultsBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadResults);
    }
    
    // Add initial task
    addTaskItem();
    
    console.log('Multi-task mode initialization complete');
}

/**
 * Add a new task input item
 */
function addTaskItem() {
    taskCounter++;
    const tasksList = document.getElementById('tasksList');
    
    const taskItem = document.createElement('div');
    taskItem.className = 'task-item';
    taskItem.dataset.taskId = taskCounter;
    
    taskItem.innerHTML = `
        <div class="task-item-content">
            <label for="task-id-${taskCounter}" class="task-label">Task ID:</label>
            <input 
                type="text" 
                id="task-id-${taskCounter}"
                name="task-id-${taskCounter}"
                placeholder="Task ID (e.g., task_${taskCounter})" 
                class="task-id-input"
                value="task_${taskCounter}"
            />
            <label for="task-query-${taskCounter}" class="task-label">Query:</label>
            <textarea 
                id="task-query-${taskCounter}"
                name="task-query-${taskCounter}"
                placeholder="Enter your query (e.g., Calculate total revenue in Sales_Records.csv)"
                class="task-query-input"
                rows="2"
            ></textarea>
        </div>
        <button class="task-item-remove" onclick="removeTaskItem(${taskCounter})">✕</button>
    `;
    
    tasksList.appendChild(taskItem);
}

/**
 * Remove a task item
 */
function removeTaskItem(taskId) {
    const taskItem = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
    if (taskItem) {
        taskItem.remove();
    }
    
    // If no tasks left, show message
    const tasksList = document.getElementById('tasksList');
    if (tasksList.children.length === 0) {
        tasksList.innerHTML = '<div class="empty-tasks-message">No tasks added. Click "Add Task" to begin.</div>';
    }
}

/**
 * Clear all tasks
 */
function clearAllTasks() {
    const tasksList = document.getElementById('tasksList');
    tasksList.innerHTML = '<div class="empty-tasks-message">No tasks added. Click "Add Task" to begin.</div>';
    document.getElementById('multiTaskResults').style.display = 'none';
    taskCounter = 0;
}

/**
 * Handle tasks file upload
 */
function handleTasksFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    console.log('Uploading tasks file:', file.name);
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const tasks = JSON.parse(e.target.result);
            loadTasksFromJSON(tasks);
            
            // Reset the file input so the same file can be uploaded again
            event.target.value = '';
        } catch (error) {
            console.error('Error parsing tasks file:', error);
            alert('Error parsing tasks file. Please ensure it is valid JSON.\n\n' + error.message);
        }
    };
    
    reader.onerror = function() {
        console.error('Error reading file');
        alert('Error reading file. Please try again.');
    };
    
    reader.readAsText(file);
}

/**
 * Load tasks from JSON data
 */
function loadTasksFromJSON(tasks) {
    console.log('Loading tasks from JSON:', tasks);
    
    // Validate tasks
    if (!Array.isArray(tasks)) {
        alert('Invalid tasks format. Expected an array of tasks.');
        return;
    }
    
    if (tasks.length === 0) {
        alert('No tasks found in the file.');
        return;
    }
    
    // Clear existing tasks
    clearAllTasks();
    
    // Add each task
    const tasksList = document.getElementById('tasksList');
    tasksList.innerHTML = ''; // Clear the empty message
    
    tasks.forEach((task, index) => {
        taskCounter++;
        
        const taskItem = document.createElement('div');
        taskItem.className = 'task-item';
        taskItem.dataset.taskId = taskCounter;
        
        // Use task data or defaults
        const taskId = task.task_id || `task_${taskCounter}`;
        const userQuery = task.user_query || '';
        const expectedBehaviour = task.expected_behaviour || '';
        const expectedOutput = task.expected_output || '';
        
        taskItem.innerHTML = `
            <div class="task-item-content">
                <label for="task-id-${taskCounter}" class="task-label">Task ID:</label>
                <input 
                    type="text" 
                    id="task-id-${taskCounter}"
                    name="task-id-${taskCounter}"
                    placeholder="Task ID (e.g., task_${taskCounter})" 
                    class="task-id-input"
                    value="${escapeHtml(taskId)}"
                />
                <label for="task-query-${taskCounter}" class="task-label">Query:</label>
                <textarea 
                    id="task-query-${taskCounter}"
                    name="task-query-${taskCounter}"
                    placeholder="Enter your query (e.g., Calculate total revenue in Sales_Records.csv)"
                    class="task-query-input"
                    rows="2"
                >${escapeHtml(userQuery)}</textarea>
                ${expectedBehaviour || expectedOutput ? `
                <details class="task-details">
                    <summary>Task Baselines</summary>
                    <div class="task-details-content">
                        ${expectedBehaviour ? `
                        <div class="task-detail-field">
                            <label for="task-expected-behaviour-${taskCounter}">Expected Behaviour:</label>
                            <textarea id="task-expected-behaviour-${taskCounter}" name="task-expected-behaviour-${taskCounter}" class="task-expected-behaviour" rows="2" readonly>${escapeHtml(expectedBehaviour)}</textarea>
                        </div>
                        ` : ''}
                        ${expectedOutput ? `
                        <div class="task-detail-field">
                            <label for="task-expected-output-${taskCounter}">Expected Output:</label>
                            <textarea id="task-expected-output-${taskCounter}" name="task-expected-output-${taskCounter}" class="task-expected-output" rows="2" readonly>${escapeHtml(expectedOutput)}</textarea>
                        </div>
                        ` : ''}
                    </div>
                </details>
                ` : ''}
            </div>
            <button class="task-item-remove" onclick="removeTaskItem(${taskCounter})">✕</button>
        `;
        
        tasksList.appendChild(taskItem);
    });
    
    console.log(`Loaded ${tasks.length} tasks successfully`);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format message content in a human-readable way
 */
function formatMessageContent(message) {
    // Handle string messages
    if (typeof message === 'string') {
        return `<pre>${escapeHtml(message)}</pre>`;
    }
    
    // Handle object messages
    if (typeof message === 'object' && message !== null) {
        let html = '';
        
        // Show role if present
        if (message.role) {
            const roleLabel = message.role === 'user' ? '👤 User' : 
                             message.role === 'assistant' ? '🤖 Assistant' : 
                             message.role === 'system' ? '⚙️ System' : message.role;
            html += `<div class="message-role"><strong>${roleLabel}</strong></div>`;
        }
        
        // Handle content field
        if (message.content) {
            const content = typeof message.content === 'string' ? message.content : JSON.stringify(message.content);
            
            // Try to parse if it's JSON string (for Code Execution MCP responses)
            try {
                const parsed = JSON.parse(content);
                
                // Format structured response (status, code, reasoning)
                if (parsed.status || parsed.code || parsed.reasoning) {
                    if (parsed.status) {
                        const statusIcon = parsed.status === 'done' ? '✅' : 
                                          parsed.status === 'exploring' ? '🔍' : '⏳';
                        html += `<div class="message-field"><strong>${statusIcon} Status:</strong> ${escapeHtml(parsed.status)}</div>`;
                    }
                    
                    if (parsed.reasoning) {
                        html += `<div class="message-field"><strong>💭 Reasoning:</strong><br><pre class="reasoning-text">${escapeHtml(parsed.reasoning)}</pre></div>`;
                    }
                    
                    if (parsed.code) {
                        html += `<div class="message-field"><strong>📝 Generated Code:</strong><br><pre class="code-block">${escapeHtml(parsed.code)}</pre></div>`;
                    }
                } else {
                    // Generic JSON formatting
                    html += `<pre>${escapeHtml(content)}</pre>`;
                }
            } catch (e) {
                // Not JSON, display as plain text
                html += `<pre>${escapeHtml(content)}</pre>`;
            }
        }
        
        return html || `<pre>${escapeHtml(JSON.stringify(message, null, 2))}</pre>`;
    }
    
    return '<p class="no-data">No content</p>';
}

/**
 * Collect all tasks from the UI
 */
function collectTasks() {
    const taskItems = document.querySelectorAll('.task-item');
    const tasks = [];
    
    taskItems.forEach(item => {
        const taskId = item.querySelector('.task-id-input').value.trim();
        const userQuery = item.querySelector('.task-query-input').value.trim();
        
        if (taskId && userQuery) {
            tasks.push({
                task_id: taskId,
                user_query: userQuery,
                expected_behaviour: '',
                expected_output: ''
            });
        }
    });
    
    return tasks;
}

/**
 * Run all tasks
 */
async function runAllTasks() {
    const tasks = collectTasks();
    
    if (tasks.length === 0) {
        alert('Please add at least one task with both ID and query filled in.');
        return;
    }
    
    const maxTurns = parseInt(document.getElementById('maxTurns').value) || 3;
    
    // Get selected approach
    const approachBtns = document.querySelectorAll('.approach-toggle-btn');
    let selectedApproachValue = 'both';
    approachBtns.forEach(btn => {
        if (btn.classList.contains('active')) {
            selectedApproachValue = btn.dataset.approach;
        }
    });
    
    // Get use_judge checkbox value (only relevant for CE)
    const useJudgeCheckbox = document.getElementById('useJudgeCheckbox');
    const useJudge = useJudgeCheckbox ? useJudgeCheckbox.checked : false;
    
    showLoading(`Running ${tasks.length} benchmark tasks...`);
    disableButtons();
    document.getElementById('runAllTasksBtn').disabled = true;
    document.getElementById('clearTasksBtn').disabled = true;
    
    try {
        const response = await fetch(`${API_BASE}/api/benchmarks/run-multiple`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tasks: tasks,
                max_turns: maxTurns,
                approaches: selectedApproachValue === 'both' ? ['code_execution', 'traditional'] : 
                           selectedApproachValue === 'code_execution' ? ['code_execution'] : 
                           ['traditional'],
                use_judge: useJudge
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        multiTaskResults = data;
        selectedApproach = selectedApproachValue; // Store the selected approach
        
        displayMultiTaskResults(data);
        updateResultsVisibility(selectedApproach);
        
    } catch (error) {
        console.error('Error running multi-task benchmark:', error);
        alert(`Failed to run benchmarks: ${error.message}`);
    } finally {
        hideLoading();
        enableButtons();
        document.getElementById('runAllTasksBtn').disabled = false;
        document.getElementById('clearTasksBtn').disabled = false;
    }
}

/**
 * Display multi-task results
 */
function displayMultiTaskResults(data) {
    console.log('Displaying multi-task results:', data);
    
    const resultsSection = document.getElementById('multiTaskResults');
    if (!resultsSection) {
        console.error('Results section not found!');
        return;
    }
    
    resultsSection.style.display = 'block';
    
    // Display summary
    console.log('Displaying summary...');
    displaySummary(data.summary);
    
    // Display charts
    console.log('Displaying charts...');
    displayMultiTaskCharts(data);
    
    // Display detailed results
    console.log('Displaying detailed results...');
    displayDetailedResults(data.results);
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    console.log('Results display complete');
}

/**
 * Download results as JSON
 */
function downloadResults() {
    if (!multiTaskResults) {
        alert('No results to download');
        return;
    }
    
    const dataStr = JSON.stringify(multiTaskResults, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `benchmark_results_${new Date().toISOString().replace(/:/g, '-').split('.')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    console.log('Results downloaded');
}

/**
 * Update results visibility based on selected approach
 */
function updateResultsVisibility(approach) {
    console.log('Updating results visibility for approach:', approach);
    
    // Find all elements with data-approach attribute
    const codeExecElements = document.querySelectorAll('[data-approach="code_execution"]');
    const traditionalElements = document.querySelectorAll('[data-approach="traditional"]');
    const bothElements = document.querySelectorAll('[data-approach="both"]');
    
    if (approach === 'both') {
        // Show both
        codeExecElements.forEach(el => el.style.display = '');
        traditionalElements.forEach(el => el.style.display = '');
        bothElements.forEach(el => el.style.display = ''); // Show comparison elements
    } else if (approach === 'code_execution') {
        // Show only CE, hide Traditional
        codeExecElements.forEach(el => el.style.display = '');
        traditionalElements.forEach(el => el.style.display = 'none');
        bothElements.forEach(el => el.style.display = ''); // Charts still show (with one dataset)
    } else if (approach === 'traditional') {
        // Show only Traditional, hide CE
        codeExecElements.forEach(el => el.style.display = 'none');
        traditionalElements.forEach(el => el.style.display = '');
        bothElements.forEach(el => el.style.display = ''); // Charts still show (with one dataset)
    }
}

/**
 * Display summary cards
 */
function displaySummary(summary) {
    const summaryGrid = document.getElementById('summaryGrid');
    
    const showCodeExec = selectedApproach === 'both' || selectedApproach === 'code_execution';
    const showTraditional = selectedApproach === 'both' || selectedApproach === 'traditional';
    const showComparison = selectedApproach === 'both';
    
    let summaryHTML = `
        <div class="summary-card">
            <h4>Total Tasks</h4>
            <div class="value">${summary.total_tasks}</div>
        </div>
    `;
    
    if (showCodeExec) {
        summaryHTML += `
            <div class="summary-card" data-approach="code_execution">
                <h4>Avg Time (Code Exec)</h4>
                <div class="value">${summary.avg_code_exec_time}s</div>
                ${showComparison ? `<div class="subtext">vs ${summary.avg_traditional_time}s</div>` : ''}
            </div>
        `;
    }
    
    if (showTraditional) {
        summaryHTML += `
            <div class="summary-card" data-approach="traditional">
                <h4>Avg Time (Traditional)</h4>
                <div class="value">${summary.avg_traditional_time}s</div>
                ${showComparison ? `<div class="subtext">vs ${summary.avg_code_exec_time}s</div>` : ''}
            </div>
        `;
    }
    
    if (showComparison) {
        summaryHTML += `
            <div class="summary-card">
                <h4>Time Improvement</h4>
                <div class="value">${summary.time_improvement}%</div>
                <div class="subtext">${summary.time_improvement > 0 ? 'Faster' : 'Slower'}</div>
            </div>
        `;
    }
    
    if (showCodeExec) {
        summaryHTML += `
            <div class="summary-card" data-approach="code_execution">
                <h4>Avg Tokens (Code Exec)</h4>
                <div class="value">${summary.avg_code_exec_tokens}</div>
                ${showComparison ? `<div class="subtext">vs ${summary.avg_traditional_tokens}</div>` : ''}
            </div>
        `;
    }
    
    if (showTraditional) {
        summaryHTML += `
            <div class="summary-card" data-approach="traditional">
                <h4>Avg Tokens (Traditional)</h4>
                <div class="value">${summary.avg_traditional_tokens}</div>
                ${showComparison ? `<div class="subtext">vs ${summary.avg_code_exec_tokens}</div>` : ''}
            </div>
        `;
    }
    
    if (showComparison) {
        summaryHTML += `
            <div class="summary-card">
                <h4>Token Reduction</h4>
                <div class="value">${summary.token_reduction}%</div>
                <div class="subtext">${summary.token_reduction > 0 ? 'Less' : 'More'}</div>
            </div>
        `;
    }
    
    if (showCodeExec) {
        summaryHTML += `
            <div class="summary-card" data-approach="code_execution">
                <h4>Success Rate (CE)</h4>
                <div class="value">${summary.code_exec_successes}/${summary.total_tasks}</div>
            </div>
        `;
    }
    
    if (showTraditional) {
        summaryHTML += `
            <div class="summary-card" data-approach="traditional">
                <h4>Success Rate (Traditional)</h4>
                <div class="value">${summary.traditional_successes}/${summary.total_tasks}</div>
            </div>
        `;
    }
    
    summaryGrid.innerHTML = summaryHTML;
}

/**
 * Display multi-task charts
 */
function displayMultiTaskCharts(data) {
    // Destroy existing charts if they exist
    if (multiTimeChart) {
        multiTimeChart.destroy();
    }
    if (multiTokenChart) {
        multiTokenChart.destroy();
    }
    
    // Time comparison chart
    const timeCanvas = document.getElementById('multiTimeChart');
    if (!timeCanvas) {
        console.error('Time chart canvas not found!');
        return;
    }
    
    const timeCtx = timeCanvas.getContext('2d');
    const timeLabels = data.results.map(r => r.task_id || r.user_query?.substring(0, 20) || `Task ${data.results.indexOf(r) + 1}`);
    const codeExecTimes = data.results.map(r => r.comparison?.code_exec_time || 0);
    const traditionalTimes = data.results.map(r => r.comparison?.traditional_time || 0);
    
    // Determine which approaches to show based on selected approach
    const showCodeExec = selectedApproach === 'both' || selectedApproach === 'code_execution';
    const showTraditional = selectedApproach === 'both' || selectedApproach === 'traditional';
    
    console.log('Creating time chart with data:', { timeLabels, codeExecTimes, traditionalTimes });
    
    const datasets = [];
    if (showCodeExec) {
        datasets.push({
            label: 'Code Execution MCP',
            data: codeExecTimes,
            backgroundColor: 'rgba(0, 255, 136, 0.7)',
            borderColor: 'rgba(0, 255, 136, 1)',
            borderWidth: 2
        });
    }
    if (showTraditional) {
        datasets.push({
            label: 'Traditional MCP',
            data: traditionalTimes,
            backgroundColor: 'rgba(233, 69, 96, 0.7)',
            borderColor: 'rgba(233, 69, 96, 1)',
            borderWidth: 2
        });
    }
    
    multiTimeChart = new Chart(timeCtx, {
        type: 'bar',
        data: {
            labels: timeLabels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Time (seconds)',
                        color: '#eeeeee'
                    },
                    ticks: { color: '#aaaaaa' },
                    grid: { color: '#333333' }
                },
                x: {
                    ticks: { color: '#aaaaaa' },
                    grid: { color: '#333333' }
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#eeeeee' }
                }
            }
        }
    });
    
    // Token comparison chart
    const tokenCanvas = document.getElementById('multiTokenChart');
    if (!tokenCanvas) {
        console.error('Token chart canvas not found!');
        return;
    }
    
    const tokenCtx = tokenCanvas.getContext('2d');
    const codeExecTokens = data.results.map(r => r.comparison?.code_exec_total_tokens || 0);
    const traditionalTokens = data.results.map(r => r.comparison?.traditional_total_tokens || 0);
    
    // Use the same show flags from time chart
    console.log('Creating token chart with data:', { codeExecTokens, traditionalTokens });
    
    const tokenDatasets = [];
    if (showCodeExec) {
        tokenDatasets.push({
            label: 'Code Execution MCP',
            data: codeExecTokens,
            backgroundColor: 'rgba(0, 255, 136, 0.7)',
            borderColor: 'rgba(0, 255, 136, 1)',
            borderWidth: 2
        });
    }
    if (showTraditional) {
        tokenDatasets.push({
            label: 'Traditional MCP',
            data: traditionalTokens,
            backgroundColor: 'rgba(233, 69, 96, 0.7)',
            borderColor: 'rgba(233, 69, 96, 1)',
            borderWidth: 2
        });
    }
    
    multiTokenChart = new Chart(tokenCtx, {
        type: 'bar',
        data: {
            labels: timeLabels,
            datasets: tokenDatasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Tokens',
                        color: '#eeeeee'
                    },
                    ticks: { color: '#aaaaaa' },
                    grid: { color: '#333333' }
                },
                x: {
                    ticks: { color: '#aaaaaa' },
                    grid: { color: '#333333' }
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#eeeeee' }
                }
            }
        }
    });
}

/**
 * Display detailed results list
 */
function displayDetailedResults(results) {
    const detailedList = document.getElementById('detailedResultsList');
    
    if (!detailedList) {
        console.error('Detailed results list element not found!');
        return;
    }
    
    console.log('Displaying', results.length, 'detailed results');
    
    if (results.length === 0) {
        detailedList.innerHTML = '<p class="no-results">No results to display</p>';
        return;
    }
    
    detailedList.innerHTML = results.map((result, index) => {
        const codeExecSuccess = result.comparison?.code_exec_success;
        const traditionalSuccess = result.comparison?.traditional_success;
        const timeDiff = result.comparison?.time_diff || 0;
        const tokenDiff = result.comparison?.tokens_diff || 0;
        
        // Format LLM calls with turn details
        const formatLLMCalls = (calls, turnDetails) => {
            if (!calls || calls.length === 0) return '<p class="no-data">No LLM calls</p>';
            
            // Debug logging
            console.log('formatLLMCalls called with:');
            console.log('calls:', calls);
            console.log('turnDetails:', turnDetails);
            
            return calls.map((call, callIndex) => {
                // Find turn by matching call_number with turn_number, or by array index as fallback
                let turn = null;
                if (turnDetails) {
                    turn = turnDetails.find(t => t.turn_number === call.call_number);
                    // Fallback to array index if not found by turn_number
                    if (!turn && turnDetails[callIndex]) {
                        turn = turnDetails[callIndex];
                    }
                }
                console.log(`Turn ${callIndex} (call_number: ${call.call_number}):`, turn);
                console.log(`Turn ${callIndex} judge_turns:`, turn?.judge_turns);
                if (turn?.judge_turns) {
                    console.log(`Found ${turn.judge_turns.length} judge turns for turn ${call.call_number}`);
                } else {
                    console.log(`No judge_turns found for turn ${call.call_number}. Turn details keys:`, turn ? Object.keys(turn) : 'turn is null');
                }
                
                // Check if we have any meaningful details
                const hasRequest = turn && turn.llm_request && (
                    typeof turn.llm_request === 'string' || 
                    (turn.llm_request.content && turn.llm_request.content !== "No detailed trace available")
                );
                const hasResponse = turn && turn.llm_response && (
                    typeof turn.llm_response === 'string' || 
                    (turn.llm_response.content && turn.llm_response.content !== "No detailed trace available")
                );
                const hasExecution = turn && turn.execution_result;
                const hasJudgeTurns = turn && turn.judge_turns && turn.judge_turns.length > 0;
                const hasDetails = hasRequest || hasResponse || hasExecution || hasJudgeTurns;
                
                return `
                    <details class="llm-call-details">
                        <summary class="llm-call-summary">
                            <span class="summary-arrow">▶</span>
                            <span class="call-number">Turn ${call.call_number}</span>
                            <span class="call-latency">${call.latency?.toFixed(2) || 'N/A'}s</span>
                            <span class="call-tokens">${call.tokens?.total_tokens || 0} tokens</span>
                            ${hasJudgeTurns ? `<span class="judge-indicator">🔍 Judge</span>` : ''}
                            <span class="call-breakdown">
                                (${call.tokens?.prompt_tokens || 0} prompt + ${call.tokens?.completion_tokens || 0} completion)
                            </span>
                        </summary>
                        ${hasDetails ? `
                        <div class="llm-call-content">
                            ${hasRequest ? `
                            <div class="llm-message llm-request">
                                <h8>📤 Request to LLM:</h8>
                                <div class="message-content">${formatMessageContent(turn.llm_request)}</div>
                            </div>
                            ` : ''}
                            
                            ${hasResponse ? `
                            <div class="llm-message llm-response">
                                <h8>🤖 LLM Response:</h8>
                                <div class="message-content">${formatMessageContent(turn.llm_response)}</div>
                            </div>
                            ` : ''}
                            
                            ${hasExecution ? `
                            <div class="llm-message llm-execution">
                                <h8>⚙️ Execution Result:</h8>
                                <pre class="message-content">${escapeHtml(turn.execution_result)}</pre>
                            </div>
                            ` : ''}
                            
                            ${hasJudgeTurns ? `
                            <div class="judge-turns-section">
                                <details class="judge-turns-details">
                                    <summary class="judge-turns-summary">
                                        <span class="summary-arrow">▶</span>
                                        <span class="judge-turns-label">🔍 LLM Judge </span>
                                    </summary>
                                    <div class="judge-turns-content">
                                        ${turn.judge_turns.map((judgeTurn, jtIndex) => {
                                            const preVerdict = judgeTurn.pre_execution && judgeTurn.pre_execution.verdict;
                                            const postVerdict = judgeTurn.post_execution && judgeTurn.post_execution.verdict;
                                            const verdictClass = (v) => v ? 'verdict-' + String(v).toLowerCase().replace(/_/g, '-') : '';
                                            return `
                                                <div class="judge-turn-item">
                                                    <div class="judge-turn-header">
                                                        <span class="judge-turn-number">Iteration ${judgeTurn.iteration}</span>
                                                        ${judgeTurn.turn_time ? `<span class="judge-turn-time">${judgeTurn.turn_time.toFixed(2)}s</span>` : ''}
                                                    </div>
                                                    <div class="judge-turn-details">
                                                        ${judgeTurn.pre_execution && Object.keys(judgeTurn.pre_execution).length > 0 ? `
                                                        <div class="judge-phase pre-execution">
                                                            <strong>Pre-Execution Judge:</strong>
                                                            <div class="judge-result">
                                                                <span class="judge-status-badge ${judgeTurn.pre_execution.status ? 'passed' : 'failed'}">
                                                                    ${judgeTurn.pre_execution.status ? '✓ Passed' : '✗ Fail'}
                                                                </span>
                                                                ${!judgeTurn.pre_execution.status && preVerdict ? `<div class="judge-verdict-line"><strong>Verdict:</strong> <span class="judge-verdict ${verdictClass(preVerdict)}">${escapeHtml(preVerdict)}</span></div>` : ''}
                                                                <div class="judge-reasoning">${escapeHtml(judgeTurn.pre_execution.reasoning || '')}</div>
                                                                ${judgeTurn.pre_execution.tokens ? `
                                                                <div class="judge-tokens">Tokens: ${judgeTurn.pre_execution.tokens.total_tokens || 0}</div>
                                                                ` : ''}
                                                            </div>
                                                        </div>
                                                        ` : ''}
                                                        
                                                        ${judgeTurn.code_generation ? `
                                                        <div class="judge-phase code-generation">
                                                            <strong>Code Generation (after judge feedback):</strong>
                                                            <div class="code-generation-content">
                                                                ${judgeTurn.code_generation.reasoning ? `
                                                                <div class="code-reasoning">Reasoning: ${escapeHtml(judgeTurn.code_generation.reasoning)}</div>
                                                                ` : ''}
                                                                ${judgeTurn.code_generation.code ? `
                                                                <details class="code-details">
                                                                    <summary>Generated Code</summary>
                                                                    <pre class="code-block">${escapeHtml(judgeTurn.code_generation.code)}</pre>
                                                                </details>
                                                                ` : ''}
                                                                ${judgeTurn.code_generation.tokens ? `
                                                                <div class="code-tokens">Tokens: ${judgeTurn.code_generation.tokens.total_tokens || 0}</div>
                                                                ` : ''}
                                                            </div>
                                                        </div>
                                                        ` : ''}
                                                        
                                                        ${judgeTurn.execution ? `
                                                        <div class="judge-phase execution">
                                                            <strong>Code Execution:</strong>
                                                            <div class="execution-result">
                                                                <span class="execution-status-badge ${judgeTurn.execution.success ? 'success' : 'error'}">
                                                                    ${judgeTurn.execution.success ? '✓ Success' : '✗ Failed'}
                                                                </span>
                                                                ${judgeTurn.execution.output ? `
                                                                <details class="execution-output-details">
                                                                    <summary>Output</summary>
                                                                    <pre class="execution-output">${escapeHtml(judgeTurn.execution.output)}</pre>
                                                                </details>
                                                                ` : ''}
                                                                ${judgeTurn.execution.error ? `
                                                                <div class="execution-error">Error: ${escapeHtml(judgeTurn.execution.error)}</div>
                                                                ` : ''}
                                                            </div>
                                                        </div>
                                                        ` : ''}
                                                        
                                                        ${judgeTurn.post_execution && Object.keys(judgeTurn.post_execution).length > 0 ? `
                                                        <div class="judge-phase post-execution">
                                                            <strong>Post-Execution Judge:</strong>
                                                            <div class="judge-result">
                                                                <span class="judge-status-badge ${judgeTurn.post_execution.status ? 'passed' : 'failed'}">
                                                                    ${judgeTurn.post_execution.status ? '✓ Passed' : '✗ Fail'}
                                                                </span>
                                                                ${!judgeTurn.post_execution.status && postVerdict ? `<div class="judge-verdict-line"><strong>Verdict:</strong> <span class="judge-verdict ${verdictClass(postVerdict)}">${escapeHtml(postVerdict)}</span></div>` : ''}
                                                                <div class="judge-reasoning">${escapeHtml(judgeTurn.post_execution.reasoning || '')}</div>
                                                                ${judgeTurn.post_execution.tokens ? `
                                                                <div class="judge-tokens">Tokens: ${judgeTurn.post_execution.tokens.total_tokens || 0}</div>
                                                                ` : ''}
                                                            </div>
                                                        </div>
                                                        ` : ''}
                                                        
                                                        ${judgeTurn.error ? `
                                                        <div class="judge-error">Error: ${escapeHtml(judgeTurn.error)}</div>
                                                        ` : ''}
                                                    </div>
                                                </div>
                                            `;
                                        }).join('')}
                                    </div>
                                </details>
                            </div>
                            ` : ''}
                        </div>
                        ` : hasJudgeTurns ? `
                        <div class="llm-call-content">
                            ${hasJudgeTurns ? `
                            <div class="judge-turns-section">
                                <details class="judge-turns-details">
                                    <summary class="judge-turns-summary">
                                        <span class="summary-arrow">▶</span>
                                        <span class="judge-turns-label">🔍 LLM Judge Inner </span>
                                    </summary>
                                    <div class="judge-turns-content">
                                        ${turn.judge_turns.map((judgeTurn, jtIndex) => {
                                            const preVerdict = judgeTurn.pre_execution && judgeTurn.pre_execution.verdict;
                                            const postVerdict = judgeTurn.post_execution && judgeTurn.post_execution.verdict;
                                            const verdictClass = (v) => v ? 'verdict-' + String(v).toLowerCase().replace(/_/g, '-') : '';
                                            return `
                                                <div class="judge-turn-item">
                                                    <div class="judge-turn-header">
                                                        <span class="judge-turn-number">Iteration ${judgeTurn.iteration}</span>
                                                        ${judgeTurn.turn_time ? `<span class="judge-turn-time">${judgeTurn.turn_time.toFixed(2)}s</span>` : ''}
                                                    </div>
                                                    <div class="judge-turn-details">
                                                        ${judgeTurn.pre_execution && Object.keys(judgeTurn.pre_execution).length > 0 ? `
                                                        <div class="judge-phase pre-execution">
                                                            <strong>Pre-Execution Judge:</strong>
                                                            <div class="judge-result">
                                                                <span class="judge-status-badge ${judgeTurn.pre_execution.status ? 'passed' : 'failed'}">
                                                                    ${judgeTurn.pre_execution.status ? '✓ Passed' : '✗ Fail'}
                                                                </span>
                                                                ${!judgeTurn.pre_execution.status && preVerdict ? `<div class="judge-verdict-line"><strong>Verdict:</strong> <span class="judge-verdict ${verdictClass(preVerdict)}">${escapeHtml(preVerdict)}</span></div>` : ''}
                                                                <div class="judge-reasoning">${escapeHtml(judgeTurn.pre_execution.reasoning || '')}</div>
                                                                ${judgeTurn.pre_execution.tokens ? `
                                                                <div class="judge-tokens">Tokens: ${judgeTurn.pre_execution.tokens.total_tokens || 0}</div>
                                                                ` : ''}
                                                            </div>
                                                        </div>
                                                        ` : ''}
                                                        
                                                        ${judgeTurn.code_generation ? `
                                                        <div class="judge-phase code-generation">
                                                            <strong>Code Generation (after judge feedback):</strong>
                                                            <div class="code-generation-content">
                                                                ${judgeTurn.code_generation.reasoning ? `
                                                                <div class="code-reasoning">Reasoning: ${escapeHtml(judgeTurn.code_generation.reasoning)}</div>
                                                                ` : ''}
                                                                ${judgeTurn.code_generation.code ? `
                                                                <details class="code-details">
                                                                    <summary>Generated Code</summary>
                                                                    <pre class="code-block">${escapeHtml(judgeTurn.code_generation.code)}</pre>
                                                                </details>
                                                                ` : ''}
                                                                ${judgeTurn.code_generation.tokens ? `
                                                                <div class="code-tokens">Tokens: ${judgeTurn.code_generation.tokens.total_tokens || 0}</div>
                                                                ` : ''}
                                                            </div>
                                                        </div>
                                                        ` : ''}
                                                        
                                                        ${judgeTurn.execution ? `
                                                        <div class="judge-phase execution">
                                                            <strong>Code Execution:</strong>
                                                            <div class="execution-result">
                                                                <span class="execution-status-badge ${judgeTurn.execution.success ? 'success' : 'error'}">
                                                                    ${judgeTurn.execution.success ? '✓ Success' : '✗ Failed'}
                                                                </span>
                                                                ${judgeTurn.execution.output ? `
                                                                <details class="execution-output-details">
                                                                    <summary>Output</summary>
                                                                    <pre class="execution-output">${escapeHtml(judgeTurn.execution.output)}</pre>
                                                                </details>
                                                                ` : ''}
                                                                ${judgeTurn.execution.error ? `
                                                                <div class="execution-error">Error: ${escapeHtml(judgeTurn.execution.error)}</div>
                                                                ` : ''}
                                                            </div>
                                                        </div>
                                                        ` : ''}
                                                        
                                                        ${judgeTurn.post_execution && Object.keys(judgeTurn.post_execution).length > 0 ? `
                                                        <div class="judge-phase post-execution">
                                                            <strong>Post-Execution Judge:</strong>
                                                            <div class="judge-result">
                                                                <span class="judge-status-badge ${judgeTurn.post_execution.status ? 'passed' : 'failed'}">
                                                                    ${judgeTurn.post_execution.status ? '✓ Passed' : '✗ Fail'}
                                                                </span>
                                                                ${!judgeTurn.post_execution.status && postVerdict ? `<div class="judge-verdict-line"><strong>Verdict:</strong> <span class="judge-verdict ${verdictClass(postVerdict)}">${escapeHtml(postVerdict)}</span></div>` : ''}
                                                                <div class="judge-reasoning">${escapeHtml(judgeTurn.post_execution.reasoning || '')}</div>
                                                                ${judgeTurn.post_execution.tokens ? `
                                                                <div class="judge-tokens">Tokens: ${judgeTurn.post_execution.tokens.total_tokens || 0}</div>
                                                                ` : ''}
                                                            </div>
                                                        </div>
                                                        ` : ''}
                                                        
                                                        ${judgeTurn.error ? `
                                                        <div class="judge-error">Error: ${escapeHtml(judgeTurn.error)}</div>
                                                        ` : ''}
                                                    </div>
                                                </div>
                                            `;
                                        }).join('')}
                                    </div>
                                </details>
                            </div>
                            ` : ''}
                        </div>
                        ` : '<p class="no-details">No detailed trace available</p>'}
                    </details>
                `;
            }).join('');
        };
        
        return `
        <div class="result-item">
            <div class="result-item-header">
                <div>
                    <h5>
                        <span class="result-number">#${index + 1}</span>
                        ${result.task_id}: ${result.user_query}
                    </h5>
                    <div class="status-badges">
                        <span class="status-badge ${codeExecSuccess ? 'success' : 'error'}" data-approach="code_execution">
                            Code Exec: ${codeExecSuccess ? '✓ Success' : '✗ Failed'}
                        </span>
                        <span class="status-badge ${traditionalSuccess ? 'success' : 'error'}" data-approach="traditional">
                            Traditional: ${traditionalSuccess ? '✓ Success' : '✗ Failed'}
                        </span>
                    </div>
                </div>
                <span class="result-timestamp">${new Date(result.timestamp).toLocaleString()}</span>
            </div>
            
            <!-- Quick Metrics Summary -->
            <div class="result-item-metrics">
                <div class="result-metric" data-approach="code_execution">
                    <span class="result-metric-label">⚡ Code Exec Time</span>
                    <span class="result-metric-value highlight-green">${result.comparison?.code_exec_time?.toFixed(2) || 'N/A'}s</span>
                </div>
                <div class="result-metric" data-approach="traditional">
                    <span class="result-metric-label">🔧 Traditional Time</span>
                    <span class="result-metric-value highlight-red">${result.comparison?.traditional_time?.toFixed(2) || 'N/A'}s</span>
                </div>
                ${(selectedApproach === 'both') ? `
                <div class="result-metric">
                    <span class="result-metric-label">📊 Time Difference</span>
                    <span class="result-metric-value ${timeDiff < 0 ? 'highlight-green' : 'highlight-red'}">
                        ${timeDiff > 0 ? '+' : ''}${timeDiff.toFixed(2)}s
                        ${timeDiff < 0 ? '(Faster ⚡)' : '(Slower 🐌)'}
                    </span>
                </div>
                ` : ''}
                <div class="result-metric" data-approach="code_execution">
                    <span class="result-metric-label">⚡ Code Exec Tokens</span>
                    <span class="result-metric-value highlight-green">${result.comparison?.code_exec_total_tokens || 0}</span>
                </div>
                <div class="result-metric" data-approach="traditional">
                    <span class="result-metric-label">🔧 Traditional Tokens</span>
                    <span class="result-metric-value highlight-red">${result.comparison?.traditional_total_tokens || 0}</span>
                </div>
                <div class="result-metric" data-approach="code_execution">
                    <span class="result-metric-label">⚡ Code Exec Turns </span>
                    <span class="result-metric-value">${result.comparison?.code_exec_llm_calls || 0}</span>
                </div>
                <div class="result-metric" data-approach="traditional">
                    <span class="result-metric-label">🔧 Traditional Calls</span>
                    <span class="result-metric-value">${result.comparison?.traditional_llm_calls || 0}</span>
                </div>
            </div>
            
            <!-- Collapsible Detailed Results -->
            <details class="result-details">
                <summary class="result-details-summary">
                    <span class="summary-icon">▶</span>
                    View Full Results & Outputs
                </summary>
                <div class="result-details-content">
                    <!-- Code Execution MCP Results -->
                    <div class="approach-results code-exec-results" data-section="code-exec" data-approach="code_execution">
                        <div class="approach-header">
                            <h6 class="approach-title">⚡ Code Execution MCP</h6>
                            <button class="collapse-btn" onclick="toggleApproachSection(event, 'code-exec')" title="Collapse this section">
                                <span class="collapse-icon">◀</span>
                            </button>
                        </div>
                        
                        <div class="approach-content">
                        <div class="output-section">
                            <h7>Output:</h7>
                            <pre class="output-box">${result.code_execution_mcp?.output || result.code_execution_mcp?.error || 'No output'}</pre>
                        </div>
                        
                        <div class="llm-calls-section">
                            <h7>LLM Calls (${result.code_execution_mcp?.llm_calls?.length || 0}):</h7>
                            <div class="llm-calls-list">
                                ${(() => {
                                    const turnDetails = result.code_execution_mcp?.turn_details;
                                    console.log('Code Exec turn_details:', turnDetails);
                                    console.log('Code Exec llm_calls:', result.code_execution_mcp?.llm_calls);
                                    if (turnDetails) {
                                        turnDetails.forEach((turn, idx) => {
                                            console.log(`Turn ${idx} (turn_number: ${turn.turn_number}) has judge_turns:`, turn.judge_turns);
                                            if (turn.judge_turns) {
                                                console.log(`  Judge turns count: ${turn.judge_turns.length}`);
                                                turn.judge_turns.forEach((jt, jtIdx) => {
                                                    console.log(`    Judge turn ${jtIdx}: status=${jt.status}, iteration=${jt.iteration}`);
                                                });
                                            }
                                        });
                                    }
                                    return formatLLMCalls(result.code_execution_mcp?.llm_calls, turnDetails);
                                })()}
                            </div>
                            <div class="total-tokens">
                                Total: ${result.code_execution_mcp?.tokens?.total_tokens || 0} tokens
                                (${result.code_execution_mcp?.tokens?.prompt_tokens || 0} prompt + 
                                ${result.code_execution_mcp?.tokens?.completion_tokens || 0} completion)
                            </div>
                        </div>
                        </div>
                    </div>
                    
                    <!-- Traditional MCP Results -->
                    <div class="approach-results traditional-results" data-section="traditional" data-approach="traditional">
                        <div class="approach-header">
                            <h6 class="approach-title">🔧 Traditional MCP</h6>
                            <button class="collapse-btn" onclick="toggleApproachSection(event, 'traditional')" title="Collapse this section">
                                <span class="collapse-icon">◀</span>
                            </button>
                        </div>
                        
                        <div class="approach-content">
                        <div class="output-section">
                            <h7>Output:</h7>
                            <pre class="output-box">${result.traditional_mcp?.output || result.traditional_mcp?.error || 'No output'}</pre>
                        </div>
                        
                        <div class="llm-calls-section">
                            <h7>LLM Calls (${result.traditional_mcp?.llm_calls?.length || 0}):</h7>
                            <div class="llm-calls-list">
                                ${formatLLMCalls(result.traditional_mcp?.llm_calls, result.traditional_mcp?.turn_details)}
                            </div>
                            <div class="total-tokens">
                                Total: ${result.traditional_mcp?.tokens?.total_tokens || 0} tokens
                                (${result.traditional_mcp?.tokens?.prompt_tokens || 0} prompt + 
                                ${result.traditional_mcp?.tokens?.completion_tokens || 0} completion)
                            </div>
                        </div>
                        </div>
                    </div>
                </div>
            </details>
        </div>
        `;
    }).join('');
}

/**
 * Toggle collapse/expand for approach sections
 */
function toggleApproachSection(event, sectionType) {
    event.stopPropagation(); // Prevent details toggle
    
    // Find the parent result-details-content container
    const button = event.target.closest('.collapse-btn');
    const detailsContent = button.closest('.result-details-content');
    
    // Get both sections
    const codeExecSection = detailsContent.querySelector('[data-section="code-exec"]');
    const traditionalSection = detailsContent.querySelector('[data-section="traditional"]');
    
    // Determine which section to toggle
    const targetSection = sectionType === 'code-exec' ? codeExecSection : traditionalSection;
    const otherSection = sectionType === 'code-exec' ? traditionalSection : codeExecSection;
    
    // Check current state
    const isCollapsed = targetSection.classList.contains('collapsed');
    
    if (isCollapsed) {
        // Expand this section, restore both to 50%
        targetSection.classList.remove('collapsed');
        otherSection.classList.remove('expanded');
        
        // Update both buttons
        const targetBtn = targetSection.querySelector('.collapse-icon');
        const otherBtn = otherSection.querySelector('.collapse-icon');
        targetBtn.textContent = '◀';
        otherBtn.textContent = '◀';
    } else {
        // Collapse this section, expand the other
        targetSection.classList.add('collapsed');
        otherSection.classList.add('expanded');
        
        // Update both buttons
        const targetBtn = targetSection.querySelector('.collapse-icon');
        const otherBtn = otherSection.querySelector('.collapse-icon');
        targetBtn.textContent = '▶';
        otherBtn.textContent = '◀';
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Set up event listeners
    initializeEventListeners();
    
    // Initialize export button
    initializeExportButton();
    
    // Initialize multi-task mode
    initializeMultiTaskMode();
});
