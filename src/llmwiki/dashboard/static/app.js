let currentPage = 1;
const tracesPerPage = 10;
let expandedTraces = new Set(); // Track which trace_ids are expanded

async function updateStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        document.getElementById('stat-entities').textContent = data.entities;
        document.getElementById('stat-processed').textContent = data.processed;
        document.getElementById('stat-total').textContent = data.total_sources;
    } catch (e) {
        console.error("Failed to update stats", e);
    }
}

function toggleTrace(tid, element) {
    const item = element.parentElement;
    if (expandedTraces.has(tid)) {
        expandedTraces.delete(tid);
        item.classList.remove('expanded');
    } else {
        expandedTraces.add(tid);
        item.classList.add('expanded');
    }
}

async function updateLogs(page = 1) {
    try {
        const response = await fetch(`/api/logs?page=${page}&limit=${tracesPerPage}`);
        const data = await response.json();
        const container = document.getElementById('traces-container');
        
        container.innerHTML = '';

        if (!data.traces || data.traces.length === 0) {
            container.innerHTML = '<div class="info">No activity logs found.</div>';
            return;
        }

        data.traces.forEach(trace => {
            const item = document.createElement('div');
            const tid = trace.trace_id;
            
            // Re-apply expanded state if it was previously open
            item.className = 'trace-item' + (expandedTraces.has(tid) ? ' expanded' : '');
            
            const startTime = new Date(trace.start_time).toLocaleTimeString();
            const duration = trace.end_time ? 
                Math.round((new Date(trace.end_time) - new Date(trace.start_time)) / 1000) : 0;
            
            item.innerHTML = `
                <div class="trace-header" onclick="toggleTrace('${tid}', this)">
                    <span class="trace-type">${trace.task_type}</span>
                    <span class="trace-id">${tid}</span>
                    <span class="trace-time">${startTime} (${duration}s)</span>
                    <span class="toggle-icon">▼</span>
                </div>
                <div class="trace-logs">
                    ${trace.logs.map(log => `
                        <div class="log-line">
                            <span class="log-time">${new Date(log.timestamp).toLocaleTimeString()}</span>
                            <span class="log-cat">${log.category}</span>
                            <span class="log-lvl ${log.level.toLowerCase()}">${log.level}</span>
                            <span class="log-msg">${log.message}</span>
                        </div>
                    `).join('')}
                </div>
            `;
            container.appendChild(item);
        });

        // Update pagination UI
        const totalPages = Math.ceil(data.total_traces / tracesPerPage) || 1;
        document.getElementById('page-info').textContent = `Page ${data.page} of ${totalPages}`;
        document.getElementById('prev-page').disabled = (data.page <= 1);
        document.getElementById('next-page').disabled = (data.page >= totalPages);
        currentPage = data.page;

    } catch (e) {
        console.error("Failed to update logs", e);
    }
}

async function updateKnowledge() {
    try {
        const response = await fetch('/api/knowledge');
        const kmap = await response.json();
        const list = document.getElementById('knowledge-list');
        list.innerHTML = '';
        
        Object.keys(kmap).slice(0, 15).forEach(name => {
            const ent = kmap[name];
            const div = document.createElement('div');
            div.className = 'entity-item';
            div.innerHTML = `
                <h4>${name}</h4>
                <p>${ent.summary}</p>
            `;
            list.appendChild(div);
        });
    } catch (e) {
        console.error("Failed to update knowledge", e);
    }
}

// Event Listeners for Pagination
document.getElementById('prev-page').addEventListener('click', () => {
    if (currentPage > 1) updateLogs(currentPage - 1);
});

document.getElementById('next-page').addEventListener('click', () => {
    updateLogs(currentPage + 1);
});

// Initial update
updateStats();
updateLogs();
updateKnowledge();

// Poll for updates (only if on page 1)
setInterval(() => {
    updateStats();
    if (currentPage === 1) updateLogs(1);
}, 5000);

setInterval(updateKnowledge, 10000);
