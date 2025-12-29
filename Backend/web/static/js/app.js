// API Configuration
const API_BASE_URL = '/api/v1';
let API_KEY = localStorage.getItem('apiKey') || '';
let currentFilter = 'all';
let refreshInterval = null;

// Initialize app on page load
document.addEventListener('DOMContentLoaded', () => {
    if (API_KEY) {
        showDashboard();
        loadJobs();
        startAutoRefresh();
    }

    // Form submission
    document.getElementById('jobForm').addEventListener('submit', submitJob);
});

// Save API Key
function saveApiKey() {
    const apiKey = document.getElementById('apiKeyInput').value.trim();
    if (!apiKey) {
        showToast('Error', 'Please enter an API key', 'danger');
        return;
    }

    API_KEY = apiKey;
    localStorage.setItem('apiKey', apiKey);
    showDashboard();
    loadJobs();
    startAutoRefresh();
    showToast('Success', 'API key saved successfully', 'success');
}

// Clear API Key
function clearApiKey() {
    if (confirm('Are you sure you want to clear your API key?')) {
        API_KEY = '';
        localStorage.removeItem('apiKey');
        stopAutoRefresh();
        document.getElementById('apiKeySection').style.display = 'block';
        document.getElementById('mainDashboard').style.display = 'none';
        showToast('Info', 'API key cleared', 'info');
    }
}

// Show Dashboard
function showDashboard() {
    document.getElementById('apiKeySection').style.display = 'none';
    document.getElementById('mainDashboard').style.display = 'block';
}

// API Request Helper
async function apiRequest(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': API_KEY
        }
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);

        if (!response.ok) {
            if (response.status === 401) {
                showToast('Error', 'Invalid API key. Please check your credentials.', 'danger');
                clearApiKey();
                throw new Error('Unauthorized');
            }
            const error = await response.json();
            throw new Error(error.detail || 'Request failed');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Submit New Job
async function submitJob(e) {
    e.preventDefault();

    const url = document.getElementById('urlInput').value.trim();
    const rename = document.getElementById('renameInput').value.trim();

    const jobData = { url };
    if (rename) {
        jobData.rename_to = rename;
    }

    try {
        const result = await apiRequest('/jobs', 'POST', jobData);
        showToast('Success', `Job created: ${result.filename}`, 'success');

        // Reset form
        document.getElementById('jobForm').reset();

        // Reload jobs
        loadJobs();
    } catch (error) {
        showToast('Error', error.message, 'danger');
    }
}

// Load Jobs
async function loadJobs() {
    try {
        const data = await apiRequest('/jobs?limit=50');
        displayJobs(data.jobs);
        updateStatistics(data.jobs);
    } catch (error) {
        console.error('Failed to load jobs:', error);
        document.getElementById('jobsTableBody').innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-danger">
                    <i class="bi bi-exclamation-triangle"></i> Failed to load jobs
                </td>
            </tr>
        `;
    }
}

// Display Jobs in Table
function displayJobs(jobs) {
    const tbody = document.getElementById('jobsTableBody');

    // Filter jobs based on current filter
    let filteredJobs = jobs;
    if (currentFilter !== 'all') {
        filteredJobs = jobs.filter(job => job.status.toLowerCase() === currentFilter);
    }

    if (filteredJobs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-muted">
                    <i class="bi bi-inbox"></i> No jobs found
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filteredJobs.map(job => `
        <tr>
            <td>${getStatusBadge(job.status)}</td>
            <td>
                <div class="text-truncate" style="max-width: 300px;" title="${job.filename}">
                    <i class="bi bi-file-earmark"></i> ${job.filename}
                </div>
                ${job.error ? `<small class="text-danger">${job.error}</small>` : ''}
            </td>
            <td>
                <small>${formatDate(job.created_at)}</small>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-info" onclick="viewJobDetails('${job.id}')" title="View Details">
                    <i class="bi bi-eye"></i>
                </button>
                ${['pending', 'downloading', 'uploading'].includes(job.status.toLowerCase()) ? `
                    <button class="btn btn-sm btn-outline-danger" onclick="cancelJob('${job.id}')" title="Cancel">
                        <i class="bi bi-x-circle"></i>
                    </button>
                ` : ''}
                <button class="btn btn-sm btn-outline-secondary" onclick="deleteJob('${job.id}')" title="Delete from list">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// Get Status Badge
function getStatusBadge(status) {
    const badges = {
        'pending': '<span class="badge bg-warning text-dark"><i class="bi bi-clock"></i> Pending</span>',
        'downloading': '<span class="badge bg-info"><i class="bi bi-download"></i> Downloading</span>',
        'uploading': '<span class="badge bg-primary"><i class="bi bi-upload"></i> Uploading</span>',
        'completed': '<span class="badge bg-success"><i class="bi bi-check-circle"></i> Completed</span>',
        'failed': '<span class="badge bg-danger"><i class="bi bi-x-circle"></i> Failed</span>'
    };
    return badges[status.toLowerCase()] || `<span class="badge bg-secondary">${status}</span>`;
}

// Format Date
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000); // seconds

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;

    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Update Statistics
function updateStatistics(jobs) {
    const stats = {
        total: jobs.length,
        running: jobs.filter(j => ['downloading', 'uploading'].includes(j.status.toLowerCase())).length,
        completed: jobs.filter(j => j.status.toLowerCase() === 'completed').length,
        failed: jobs.filter(j => j.status.toLowerCase() === 'failed').length
    };

    document.getElementById('statTotal').textContent = stats.total;
    document.getElementById('statRunning').textContent = stats.running;
    document.getElementById('statCompleted').textContent = stats.completed;
    document.getElementById('statFailed').textContent = stats.failed;
}

// View Job Details
async function viewJobDetails(jobId) {
    try {
        const job = await apiRequest(`/jobs/${jobId}`);

        const details = `
            <strong>Job ID:</strong> ${job.id}<br>
            <strong>Status:</strong> ${job.status}<br>
            <strong>URL:</strong> ${job.url}<br>
            <strong>Filename:</strong> ${job.filename}<br>
            <strong>Created:</strong> ${new Date(job.created_at).toLocaleString()}<br>
            ${job.completed_at ? `<strong>Completed:</strong> ${new Date(job.completed_at).toLocaleString()}<br>` : ''}
            ${job.error ? `<strong>Error:</strong> <span class="text-danger">${job.error}</span>` : ''}
        `;

        showToast('Job Details', details, 'info', 5000);
    } catch (error) {
        showToast('Error', 'Failed to load job details', 'danger');
    }
}

// Cancel Job
async function cancelJob(jobId) {
    if (!confirm('Are you sure you want to cancel this job?')) return;

    try {
        await apiRequest(`/jobs/${jobId}`, 'DELETE');
        showToast('Success', 'Job cancelled', 'warning');
        loadJobs();
    } catch (error) {
        showToast('Error', error.message, 'danger');
    }
}

// Delete Job (remove from display)
async function deleteJob(jobId) {
    if (!confirm('Are you sure you want to delete this job from the list?')) return;

    try {
        // Try to delete from backend
        await apiRequest(`/jobs/${jobId}`, 'DELETE');
        showToast('Success', 'Job deleted', 'info');
        loadJobs();
    } catch (error) {
        // If backend deletion fails, just hide it from UI
        const row = document.querySelector(`button[onclick="deleteJob('${jobId}')"]`)?.closest('tr');
        if (row) {
            row.remove();
            showToast('Info', 'Job removed from display', 'info');
        } else {
            showToast('Error', error.message, 'danger');
        }
    }
}

// Set Filter
function setFilter(filter) {
    currentFilter = filter;

    // Update button states
    document.querySelectorAll('[data-filter]').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.filter === filter) {
            btn.classList.add('active');
        }
    });

    loadJobs();
}

// Auto-refresh
function startAutoRefresh() {
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(() => {
        loadJobs();
    }, 5000); // Refresh every 5 seconds
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// Show Toast Notification
function showToast(title, message, type = 'info', duration = 3000) {
    const toast = document.getElementById('toast');
    const toastTitle = document.getElementById('toastTitle');
    const toastMessage = document.getElementById('toastMessage');

    // Set colors based on type
    const colors = {
        'success': 'bg-success text-white',
        'danger': 'bg-danger text-white',
        'warning': 'bg-warning text-dark',
        'info': 'bg-info text-white'
    };

    toast.className = `toast ${colors[type] || ''}`;
    toastTitle.textContent = title;
    toastMessage.innerHTML = message;

    const bsToast = new bootstrap.Toast(toast, { delay: duration });
    bsToast.show();
}
