/**
 * Enterprise GenAI Strategy Engine — Client Controller
 * BCG Executive Web Application
 */

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initTelemetry();
  initCharts();
  initChatAssistant();
  initFinancialTools();
  initComparisonTool();
  initComplianceTool();
  initDocumentLibrary();
  initEvaluationHarness();
});

// Global state
let currentDocuments = [];
let peersData = [];
let peerMetricChart = null;

// ---------------- 1. NAVIGATION CONTROLLER ----------------
function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const panels = document.querySelectorAll('.view-panel');

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetView = item.dataset.view;

      navItems.forEach(n => n.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));

      item.classList.add('active');
      const activePanel = document.getElementById(`view-${targetView}`);
      if (activePanel) {
        activePanel.classList.add('active');
      }

      // Refresh charts when entering dashboard or financial
      if (targetView === 'dashboard' || targetView === 'financial') {
        setTimeout(renderPeerMetricChart, 100);
      }
    });
  });

  // Financial Subtabs
  const subtabBtns = document.querySelectorAll('.tab-btn');
  subtabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      subtabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const targetSub = btn.dataset.subtab;
      document.querySelectorAll('.subtab-panel').forEach(p => p.style.display = 'none');
      const targetP = document.getElementById(targetSub);
      if (targetP) targetP.style.display = 'block';

      if (targetSub === 'subtab-fin-peer') setTimeout(renderPeerMetricChart, 100);
      if (targetSub === 'subtab-fin-waterfall') setTimeout(renderWaterfallChart, 100);
    });
  });
}

// ---------------- 2. TELEMETRY & DOCUMENT LOADER ----------------
async function initTelemetry() {
  try {
    const [statsRes, docsRes] = await Promise.all([
      fetch('/api/stats'),
      fetch('/api/documents')
    ]);

    const stats = await statsRes.json();
    const docs = await docsRes.json();
    currentDocuments = docs;

    // Update Telemetry Cards
    document.getElementById('stat-docs').innerText = stats.total_documents;
    document.getElementById('stat-chunks').innerText = stats.total_chunks;
    document.getElementById('stat-latency').innerText = `${stats.avg_latency_ms} ms`;
    document.getElementById('stat-model').innerText = stats.active_model.includes('Offline') ? 'Grounded AI' : stats.active_model.substring(0, 16);

    // Populate Dashboard Docs Table
    const tableBody = document.getElementById('dashboard-docs-table');
    tableBody.innerHTML = '';
    docs.forEach(d => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td><strong>📄 ${escapeHtml(d.file_name)}</strong></td>
        <td><span style="font-family: var(--font-mono); color: var(--bcg-emerald-light);">${d.file_type.toUpperCase()}</span></td>
        <td>${(d.file_size_bytes / 1024).toFixed(1)} KB</td>
        <td>${d.sections_count}</td>
        <td>${d.tables_count}</td>
        <td>${d.ingested_at.substring(0, 10)}</td>
      `;
      tableBody.appendChild(row);
    });

    // Populate Comparison Selects
    populateComparisonSelects(docs);
    // Populate Library Table
    populateLibraryTable(docs);

  } catch (err) {
    console.error('Failed to load telemetry:', err);
  }
}

// ---------------- 3. INTERACTIVE CHARTS (CHART.JS) ----------------
async function initCharts() {
  try {
    const res = await fetch('/api/financial/peers');
    peersData = await res.json();

    renderDashboardPeerChart();
    renderPeerMetricChart();
    renderWaterfallChart();

    // Listen to metric select dropdown change
    document.getElementById('peer-metric-select').addEventListener('change', renderPeerMetricChart);

  } catch (err) {
    console.error('Failed to load peer financial data:', err);
  }
}

function renderDashboardPeerChart() {
  const ctx = document.getElementById('chart-peers-overview');
  if (!ctx || !peersData.length) return;

  const fy24Peers = peersData.filter(d => d.Fiscal_Year === 'FY2024');
  const labels = fy24Peers.map(d => d.Company);
  const operatingMargins = fy24Peers.map(d => d.Operating_Margin_Pct);

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'FY2024 Operating Margin (%)',
        data: operatingMargins,
        backgroundColor: ['#00A35C', '#10B981', '#34D399', '#38BDF8', '#60A5FA'],
        borderRadius: 8,
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#94A3B8', font: { family: 'Plus Jakarta Sans' } } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94A3B8' } },
        y: { 
          grid: { color: 'rgba(255,255,255,0.06)' }, 
          ticks: { color: '#94A3B8', callback: v => v + '%' } 
        }
      }
    }
  });
}

function renderPeerMetricChart() {
  const ctx = document.getElementById('chart-peer-metric');
  if (!ctx || !peersData.length) return;

  const selectedMetric = document.getElementById('peer-metric-select').value;
  const fy24Peers = peersData.filter(d => d.Fiscal_Year === 'FY2024');
  const labels = fy24Peers.map(d => d.Company);
  const metricValues = fy24Peers.map(d => d[selectedMetric]);

  if (peerMetricChart) {
    peerMetricChart.destroy();
  }

  peerMetricChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: selectedMetric.replace(/_/g, ' '),
        data: metricValues,
        backgroundColor: 'rgba(0, 163, 92, 0.75)',
        borderColor: '#34D399',
        borderWidth: 1,
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#94A3B8', font: { family: 'Plus Jakarta Sans' } } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94A3B8' } },
        y: { grid: { color: 'rgba(255,255,255,0.06)' }, ticks: { color: '#94A3B8' } }
      }
    }
  });
}

function renderWaterfallChart() {
  const ctx = document.getElementById('chart-waterfall');
  if (!ctx) return;

  // Microsoft FY24 Bridge
  const labels = ['Total Revenue', 'Cost of Sales', 'Gross Profit', 'R&D', 'Sales & Mktg', 'G&A', 'Operating Income'];
  const values = [245.1, -75.3, 169.8, -29.5, -24.4, -6.5, 109.4];
  const bgColors = values.map((v, i) => {
    if (i === 0 || i === 2 || i === 6) return '#38BDF8';
    return v < 0 ? '#F43F5E' : '#00A35C';
  });

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Amount ($ Billions)',
        data: values,
        backgroundColor: bgColors,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94A3B8' } },
        y: { grid: { color: 'rgba(255,255,255,0.06)' }, ticks: { color: '#94A3B8', callback: v => '$' + v + 'B' } }
      }
    }
  });
}

// ---------------- 4. STRATEGIC KNOWLEDGE ASSISTANT ----------------
function initChatAssistant() {
  const sendBtn = document.getElementById('btn-send-query');
  const input = document.getElementById('chat-query-input');
  const personaSelect = document.getElementById('chat-persona-select');
  const clearBtn = document.getElementById('btn-clear-chat');

  // Quick Prompt buttons
  document.querySelectorAll('.quick-prompt').forEach(btn => {
    btn.addEventListener('click', () => {
      input.value = btn.dataset.query;
      sendQuery();
    });
  });

  sendBtn.addEventListener('click', sendQuery);
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendQuery();
  });

  clearBtn.addEventListener('click', () => {
    document.getElementById('chat-messages-container').innerHTML = `
      <div class="chat-bubble assistant">
        <strong style="color: #4ADE80;">Session Reset:</strong> Ready for new strategic enterprise inquiry.
      </div>
    `;
    document.getElementById('citations-container').innerHTML = `
      <div style="color: var(--text-dim); font-size: 0.85rem; font-style: italic; text-align: center; padding: 2rem;">
        Citations will render here after query execution.
      </div>
    `;
    document.getElementById('citations-count-badge').innerText = '0 Citations';
  });

  async function sendQuery() {
    const query = input.value.trim();
    if (!query) return;

    const persona = personaSelect.value;
    input.value = '';

    // Append User Message
    appendMessage(query, 'user');

    // Append Loading State
    const loadingId = 'loading-' + Date.now();
    appendMessage('<div style="display: flex; align-items: center; gap: 0.5rem;"><div style="width: 12px; height: 12px; border: 2px solid #34D399; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite;"></div> Synthesizing evidence across SEC 10-K filings...</div>', 'assistant', loadingId);

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, persona: persona })
      });

      const data = await res.json();
      removeElement(loadingId);

      // Render Assistant Answer
      appendMessage(formatMarkdown(data.answer), 'assistant');

      // Render Citations
      renderCitations(data.citations);

    } catch (err) {
      removeElement(loadingId);
      appendMessage('❌ Failed to retrieve answer: ' + err.message, 'assistant');
    }
  }

  function appendMessage(html, role, id = null) {
    const container = document.getElementById('chat-messages-container');
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;
    if (id) bubble.id = id;
    bubble.innerHTML = html;
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
  }

  function removeElement(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function renderCitations(citations) {
    const container = document.getElementById('citations-container');
    const badge = document.getElementById('citations-count-badge');
    badge.innerText = `${citations.length} Citations`;

    if (!citations || !citations.length) {
      container.innerHTML = '<div style="color: var(--text-dim); padding: 1.5rem;">No citations found.</div>';
      return;
    }

    container.innerHTML = '';
    citations.forEach(c => {
      const card = document.createElement('div');
      card.className = 'citation-card';
      card.innerHTML = `
        <span class="citation-badge">[Source ${c.id}] ${escapeHtml(c.document_name)}</span>
        <div style="font-size: 0.84rem; color: #E2E8F0; line-height: 1.5; margin-top: 0.35rem;">
          "${escapeHtml(c.snippet)}"
        </div>
        <div style="font-size: 0.75rem; color: var(--bcg-emerald-light); margin-top: 0.4rem; font-weight: 600;">
          Relevance Score: ${c.relevance_score}
        </div>
      `;
      container.appendChild(card);
    });
  }
}

// ---------------- 5. FINANCIAL TOOLS & SIMULATOR ----------------
function initFinancialTools() {
  const costSlider = document.getElementById('val-cost-slider');
  const multSlider = document.getElementById('val-multiple-slider');
  const ebitdaInput = document.getElementById('val-base-ebitda');

  costSlider.addEventListener('input', updateValuationSimulator);
  multSlider.addEventListener('input', updateValuationSimulator);
  ebitdaInput.addEventListener('input', updateValuationSimulator);

  async function updateValuationSimulator() {
    const baseEbitda = parseFloat(ebitdaInput.value) || 100.0;
    const costOutPct = parseFloat(costSlider.value) || 0.0;
    const multiple = parseFloat(multSlider.value) || 20.0;

    document.getElementById('val-cost-label').innerText = `${costOutPct}%`;
    document.getElementById('val-multiple-label').innerText = `${multiple}x`;

    const res = await fetch('/api/financial/valuation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ base_ebitda: baseEbitda, cost_out_pct: costOutPct, multiple: multiple })
    });
    const d = await res.json();

    document.getElementById('res-val-base').innerText = `$${d.implied_ev_base.toLocaleString()} B`;
    document.getElementById('res-val-adjusted').innerText = `$${d.implied_ev_adjusted.toLocaleString()} B`;
    document.getElementById('res-val-unlocked').innerText = `+ $${d.value_unlocked.toLocaleString()} B Created`;
    document.getElementById('val-insight-text').innerHTML = `
      A <strong>${costOutPct}%</strong> efficiency capture generates <strong>+$${d.incremental_ebitda}B</strong> in recurring annual EBITDA, unlocking <strong>+$${d.value_unlocked} Billion</strong> in market equity capitalization at a ${multiple}x multiple.
    `;
  }

  // Growth Calc
  document.getElementById('btn-calc-growth').addEventListener('click', async () => {
    const p1 = parseFloat(document.getElementById('math-p1-val').value);
    const p2 = parseFloat(document.getElementById('math-p2-val').value);

    const res = await fetch('/api/financial/growth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ base_val: p1, current_val: p2, metric_name: 'Revenue' })
    });
    const d = await res.json();

    document.getElementById('growth-result-box').style.display = 'block';
    document.getElementById('res-math-p1').innerText = `$${d.value_1.toLocaleString()}M`;
    document.getElementById('res-math-p2').innerText = `$${d.value_2.toLocaleString()}M`;
    document.getElementById('res-math-pct').innerText = `${d.percentage_change > 0 ? '+' : ''}${d.percentage_change.toFixed(2)}%`;
    document.getElementById('res-math-abs').innerText = `${d.absolute_change > 0 ? '+' : ''}$${d.absolute_change.toLocaleString()}M`;
  });
}

// ---------------- 6. COMPARISON MATRIX ----------------
function populateComparisonSelects(docs) {
  const sel1 = document.getElementById('comp-doc-1');
  const sel2 = document.getElementById('comp-doc-2');
  if (!sel1 || !sel2) return;

  sel1.innerHTML = '';
  sel2.innerHTML = '';

  docs.forEach((d, idx) => {
    const opt1 = new Option(d.file_name, d.document_id);
    const opt2 = new Option(d.file_name, d.document_id);
    sel1.add(opt1);
    sel2.add(opt2);
  });

  if (docs.length > 1) {
    sel2.selectedIndex = 1;
  }
}

function initComparisonTool() {
  const btn = document.getElementById('btn-run-comparison');
  btn.addEventListener('click', async () => {
    const doc1 = document.getElementById('comp-doc-1').value;
    const doc2 = document.getElementById('comp-doc-2').value;
    const focus = document.getElementById('comp-focus').value;

    btn.innerText = 'Analyzing Filings...';
    btn.disabled = true;

    try {
      const res = await fetch('/api/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_id_1: doc1, doc_id_2: doc2, focus_aspect: focus })
      });
      const data = await res.json();

      document.getElementById('comparison-result-card').style.display = 'block';
      document.getElementById('comparison-report-body').innerHTML = formatMarkdown(data.report);

    } catch (err) {
      alert('Failed to generate comparison: ' + err.message);
    } finally {
      btn.innerText = 'Generate Matrix';
      btn.disabled = false;
    }
  });
}

// ---------------- 7. COMPLIANCE SCANNER ----------------
function initComplianceTool() {
  const btn = document.getElementById('btn-run-compliance');
  btn.addEventListener('click', async () => {
    const topic = document.getElementById('compliance-query-input').value;
    btn.innerText = 'Auditing...';
    btn.disabled = true;

    try {
      const res = await fetch('/api/compliance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ compliance_topic: topic })
      });
      const data = await res.json();

      document.getElementById('compliance-result-card').style.display = 'block';
      document.getElementById('compliance-report-body').innerHTML = formatMarkdown(data.report);

    } catch (err) {
      alert('Audit scan failed: ' + err.message);
    } finally {
      btn.innerText = 'Execute Audit';
      btn.disabled = false;
    }
  });
}

// ---------------- 8. DOCUMENT LIBRARY ----------------
function populateLibraryTable(docs) {
  const tableBody = document.getElementById('library-docs-table');
  if (!tableBody) return;
  tableBody.innerHTML = '';

  docs.forEach(d => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><strong>📄 ${escapeHtml(d.file_name)}</strong></td>
      <td><span style="font-family: var(--font-mono); color: var(--bcg-emerald-light);">${d.file_type.toUpperCase()}</span></td>
      <td>${(d.file_size_bytes / 1024).toFixed(1)} KB</td>
      <td><code>${d.content_hash.substring(0, 16)}...</code></td>
      <td>${d.sections_count} sections</td>
      <td>
        <button class="btn-outline" onclick="deleteDocument('${d.document_id}')" style="color: #F43F5E; border-color: rgba(244,63,94,0.3);">
          Delete
        </button>
      </td>
    `;
    tableBody.appendChild(row);
  });
}

window.deleteDocument = async function(docId) {
  if (!confirm('Are you sure you want to purge this document from the vector store?')) return;
  try {
    const res = await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
    if (res.ok) {
      initTelemetry();
    }
  } catch (err) {
    alert('Deletion failed: ' + err.message);
  }
};

function initDocumentLibrary() {
  const uploadBtn = document.getElementById('btn-upload-file');
  const fileInput = document.getElementById('upload-file-input');
  const strategySelect = document.getElementById('upload-strategy-select');
  const alertBox = document.getElementById('upload-status-alert');

  uploadBtn.addEventListener('click', async () => {
    if (!fileInput.files.length) {
      alert('Please select a file to upload.');
      return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('chunk_strategy', strategySelect.value);

    uploadBtn.innerText = 'Uploading & Indexing...';
    uploadBtn.disabled = true;

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      alertBox.style.display = 'block';
      if (data.success) {
        alertBox.style.background = 'rgba(0, 163, 92, 0.15)';
        alertBox.style.border = '1px solid #00A35C';
        alertBox.style.color = '#86EFAC';
        alertBox.innerHTML = `✅ Successfully indexed <strong>${escapeHtml(data.file_name)}</strong> with ${data.chunks_indexed} chunks!`;
        initTelemetry();
      } else {
        alertBox.style.background = 'rgba(244, 63, 94, 0.15)';
        alertBox.style.border = '1px solid #F43F5E';
        alertBox.style.color = '#FDA4AF';
        alertBox.innerHTML = `❌ Ingestion failed: ${escapeHtml(data.error || 'Unknown error')}`;
      }
    } catch (err) {
      alert('Upload error: ' + err.message);
    } finally {
      uploadBtn.innerText = 'Upload & Index';
      uploadBtn.disabled = false;
    }
  });
}

// ---------------- 9. RAG EVALUATION HARNESS ----------------
function initEvaluationHarness() {
  const btn = document.getElementById('btn-run-eval');
  btn.addEventListener('click', async () => {
    btn.innerText = 'Running Benchmark Suite...';
    btn.disabled = true;

    try {
      const res = await fetch('/api/evaluation/run', { method: 'POST' });
      const d = await res.json();

      document.getElementById('eval-scorecard').style.display = 'block';
      document.getElementById('eval-pass-rate').innerText = `${d.pass_rate_pct.toFixed(1)}%`;
      document.getElementById('eval-precision').innerText = `${(d.avg_context_precision * 100).toFixed(1)}%`;
      document.getElementById('eval-faithfulness').innerText = `${(d.avg_faithfulness * 100).toFixed(1)}%`;
      document.getElementById('eval-latency').innerText = `${d.avg_latency_ms.toFixed(0)} ms`;

      const tbody = document.getElementById('eval-cases-table');
      tbody.innerHTML = '';
      d.cases.forEach(c => {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td><strong>${c.case_id}</strong></td>
          <td style="max-width: 300px;">${escapeHtml(c.query)}</td>
          <td><span style="font-size: 0.75rem; text-transform: uppercase;">${c.category}</span></td>
          <td style="color: ${c.passed ? '#4ADE80' : '#F43F5E'}; font-weight: 700;">${c.passed ? '✅ Pass' : '❌ Fail'}</td>
          <td>${(c.context_precision * 100).toFixed(0)}%</td>
          <td>${(c.context_recall * 100).toFixed(0)}%</td>
          <td>${c.latency_ms.toFixed(0)} ms</td>
        `;
        tbody.appendChild(row);
      });

    } catch (err) {
      alert('Evaluation failed: ' + err.message);
    } finally {
      btn.innerText = 'Run Benchmark Suite';
      btn.disabled = false;
    }
  });
}

// ---------------- UTILS ----------------
function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatMarkdown(text) {
  if (!text) return '';
  // Basic markdown formatting: bold, headers, bullet points, citations
  let out = escapeHtml(text);
  out = out.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/### (.*?)\n/g, '<h4 style="color: #86EFAC; margin: 0.8rem 0 0.4rem 0;">$1</h4>');
  out = out.replace(/## (.*?)\n/g, '<h3 style="color: #FFFFFF; margin: 1rem 0 0.5rem 0;">$1</h3>');
  out = out.replace(/\[SOURCE (\d+)\]/gi, '<span class="citation-badge">[Source $1]</span>');
  out = out.replace(/\n- (.*?)(?=\n|$)/g, '<li style="margin-left: 1.25rem; margin-bottom: 0.35rem;">$1</li>');
  out = out.replace(/\n\n/g, '<br><br>');
  return out;
}
