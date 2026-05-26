/**
 * MCP Benchmark Dashboard - Chart Visualization
 * 
 * Handles Chart.js visualization for benchmark comparison
 */

// Store chart instance globally to allow updates
let comparisonChart = null;

/**
 * Update comparison chart with current query results
 */
function updateCurrentComparisonChart() {
    // Get chart canvas element
    const ctx = document.getElementById('comparisonChart');
    
    // Exit if canvas not found
    if (!ctx) {
        console.error('Chart canvas not found');
        return;
    }
    
    // Get current results from global variable
    const traditional = currentQueryResults.traditional;
    const codeExec = currentQueryResults.codeExecution;
    
    // Exit if both results not available
    if (!traditional || !codeExec) {
        return;
    }
    
    // Extract metrics from current query results
    const traditionalTime = traditional.time;
    const codeExecTime = codeExec.time;
    
    const traditionalTokens = extractTotalTokensForChart(traditional);
    const codeExecTokens = extractTotalTokensForChart(codeExec);
    
    const traditionalCalls = traditional.llm_calls?.length || 0;
    const codeExecCalls = codeExec.llm_calls?.length || 0;
    
    // Prepare chart data structure for current query
    const chartData = {
        // Define chart labels
        labels: ['Execution Time (s)', 'Total Tokens (÷100)', 'LLM Calls'],
        
        // Define datasets for both approaches
        datasets: [
            {
                label: 'Traditional MCP',
                data: [
                    traditionalTime.toFixed(2),
                    (traditionalTokens / 100).toFixed(2),
                    traditionalCalls
                ],
                backgroundColor: 'rgba(233, 69, 96, 0.6)',
                borderColor: 'rgba(233, 69, 96, 1)',
                borderWidth: 2
            },
            {
                label: 'Code Execution MCP',
                data: [
                    codeExecTime.toFixed(2),
                    (codeExecTokens / 100).toFixed(2),
                    codeExecCalls
                ],
                backgroundColor: 'rgba(0, 255, 136, 0.6)',
                borderColor: 'rgba(0, 255, 136, 1)',
                borderWidth: 2
            }
        ]
    };
    
    // Configure chart options
    const config = {
        type: 'bar',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Current Query Performance Comparison',
                    color: '#eeeeee',
                    font: {
                        size: 18,
                        weight: 'bold'
                    }
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#eeeeee',
                        font: {
                            size: 14
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    titleColor: '#eeeeee',
                    bodyColor: '#eeeeee',
                    borderColor: '#00ff88',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            // Initialize label with dataset name
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            
                            // Format value based on metric type
                            if (context.label === 'Total Tokens (÷100)') {
                                label += (context.parsed.y * 100).toFixed(0) + ' tokens';
                            } else if (context.label === 'Execution Time (s)') {
                                label += context.parsed.y + 's';
                            } else {
                                label += context.parsed.y + ' calls';
                            }
                            
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#aaaaaa',
                        font: {
                            size: 12
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: '#aaaaaa',
                        font: {
                            size: 12
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    };
    
    // Destroy existing chart if it exists
    if (comparisonChart) {
        comparisonChart.destroy();
    }
    
    // Create new chart instance
    comparisonChart = new Chart(ctx, config);
}

/**
 * Extract total tokens from result data handling different formats
 * Helper function for chart calculations
 * @param {object} result - Result object containing token information
 * @returns {number} Total token count
 */
function extractTotalTokensForChart(result) {
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
