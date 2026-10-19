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
  initTCOSimulator();
  initScenarioMatrix();
  initGraphRAG();
  initVirtualCleanRoom();
  initTelemetryAndCache();
});

// Global state
let currentDocuments = [];
let peersData = [];
let peerMetricChart = null;
let lastStrategyResponse = null;


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
  const roleSelect = document.getElementById('chat-role-select');
  const clearBtn = document.getElementById('btn-clear-chat');
  const exportDeckBtn = document.getElementById('btn-export-last-deck');

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

  // PowerPoint Deck Export Handler
  if (exportDeckBtn) {
    exportDeckBtn.addEventListener('click', async () => {
      if (!lastStrategyResponse) return;
      exportDeckBtn.innerText = 'Generating Slide Deck...';
      exportDeckBtn.disabled = true;

      try {
        const resp = await fetch('/api/export/deck', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: "BCG X Strategy Briefing",
            subtitle: lastStrategyResponse.query,
            query: lastStrategyResponse.query,
            synthesis_text: lastStrategyResponse.answer
          })
        });

        if (!resp.ok) throw new Error("Deck generation failed");
        const blob = await resp.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `BCG_Executive_Briefing_${Date.now()}.pptx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
      } catch (err) {
        alert("Failed to export deck: " + err.message);
      } finally {
        exportDeckBtn.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          <span>Export Executive Deck (.pptx)</span>
        `;
        exportDeckBtn.disabled = false;
      }
    });
  }

  clearBtn.addEventListener('click', () => {
    lastStrategyResponse = null;
    if (exportDeckBtn) exportDeckBtn.style.display = 'none';
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

    const persona = personaSelect ? personaSelect.value : 'bcg_partner';
    const userRole = roleSelect ? roleSelect.value : 'STRATEGY_CONSULTANT';
    input.value = '';

    // Append User Message
    appendMessage(query, 'user');

    // Append Loading State
    const loadingId = 'loading-' + Date.now();
    appendMessage('<div style="display: flex; align-items: center; gap: 0.5rem;"><div style="width: 12px; height: 12px; border: 2px solid #34D399; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite;"></div> Synthesizing evidence across SEC 10-K filings with Agentic Critic Review...</div>', 'assistant', loadingId);

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          persona: persona,
          user_role: userRole
        })
      });

      const data = await res.json();
      removeElement(loadingId);

      lastStrategyResponse = { query: query, answer: data.answer, data: data };
      if (exportDeckBtn) exportDeckBtn.style.display = 'inline-flex';

      // Build Assistant HTML with Critic Audit Card and Telemetry
      let answerHtml = formatMarkdown(data.answer);

      // Render Critic Review Box
      if (data.critic_audit) {
        const ca = data.critic_audit;
        const statusClass = (ca.status || 'passed').toLowerCase();
        const latency = data.telemetry ? data.telemetry.total_latency_ms : 0;
        
        answerHtml += `
          <div class="critic-audit-box ${statusClass}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
              <span style="font-weight: 700; color: #86EFAC;">🛡️ BCG X Partner & Risk Review: ${escapeHtml(ca.status)}</span>
              <span class="telemetry-chip ${data.is_cache_hit ? 'cache-hit' : ''}">
                ${data.is_cache_hit ? '⚡ Semantic Cache Hit (' + (data.cache_similarity * 100).toFixed(0) + '% match)' : '⏱️ ' + latency + ' ms (Waterfall)'}
              </span>
            </div>
            <div style="font-size: 0.82rem; margin-bottom: 0.35rem;">
              <strong>Faithfulness:</strong> ${(ca.faithfulness_score * 100).toFixed(0)}% | 
              <strong>Numerical Precision:</strong> ${(ca.numerical_accuracy_score * 100).toFixed(0)}% | 
              <strong>Claims Audited:</strong> ${ca.total_claims_audited}
            </div>
            <div style="font-size: 0.82rem; color: #94A3B8; font-style: italic;">
              ${escapeHtml(ca.partner_recommendation)}
            </div>
          </div>
        `;
      }

      appendMessage(answerHtml, 'assistant');

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

// ---------------- 10. BCG 10-20-70 TCO SIMULATOR ----------------
function initTCOSimulator() {
  const empSlider = document.getElementById('tco-emp-slider');
  const qSlider = document.getElementById('tco-q-slider');
  const timeSlider = document.getElementById('tco-time-slider');
  const wageSlider = document.getElementById('tco-wage-slider');
  const budgetSlider = document.getElementById('tco-budget-slider');
  const recalcBtn = document.getElementById('btn-recalc-tco');

  if (!empSlider) return;

  const sliders = [empSlider, qSlider, timeSlider, wageSlider, budgetSlider];
  sliders.forEach(s => s && s.addEventListener('input', updateTCO));
  if (recalcBtn) recalcBtn.addEventListener('click', updateTCO);

  async function updateTCO() {
    const emp = parseInt(empSlider.value);
    const q = parseFloat(qSlider.value);
    const timeSaved = parseFloat(timeSlider.value);
    const wage = parseFloat(wageSlider.value);
    const budget = parseFloat(budgetSlider.value);

    document.getElementById('tco-emp-label').innerText = `${emp.toLocaleString()} users`;
    document.getElementById('tco-q-label').innerText = `${q.toFixed(1)} queries/day`;
    document.getElementById('tco-time-label').innerText = `${timeSaved} minutes`;
    document.getElementById('tco-wage-label').innerText = `$${wage} / hour`;
    document.getElementById('tco-budget-label').innerText = `$${(budget / 1000).toLocaleString()}K`;

    try {
      const res = await fetch('/api/tco/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_employees: emp,
          daily_queries_per_employee: q,
          minutes_saved_per_query: timeSaved,
          employee_hourly_cost: wage,
          total_transformation_budget: budget
        })
      });

      const d = await res.json();
      document.getElementById('tco-bcg-10').innerText = `$${(d.bcg_10_algorithms_budget / 1000).toFixed(0)}K`;
      document.getElementById('tco-bcg-20').innerText = `$${(d.bcg_20_tech_data_budget / 1000).toFixed(0)}K`;
      document.getElementById('tco-bcg-70').innerText = `$${(d.bcg_70_people_workflows_budget / 1000).toFixed(0)}K`;

      document.getElementById('tco-hours').innerText = `${Math.round(d.annual_hours_saved).toLocaleString()} hrs`;
      document.getElementById('tco-ebitda').innerText = `+$${(d.annual_net_ebitda_impact / 1000000).toFixed(1)}M`;
      document.getElementById('tco-payback').innerText = `${d.payback_period_months.toFixed(1)} Mos`;
      document.getElementById('tco-verdict-text').innerText = d.executive_verdict;
    } catch (err) {
      console.warn("TCO Simulation failed:", err);
    }
  }

  // Initial calculation
  setTimeout(updateTCO, 200);
}

// ---------------- 11. SCENARIO SENSITIVITY MATRIX ----------------
function initScenarioMatrix() {
  const btn = document.getElementById('btn-run-scenario-matrix');
  if (btn) btn.addEventListener('click', loadScenarioMatrix);

  async function loadScenarioMatrix() {
    try {
      const res = await fetch('/api/scenarios/sensitivity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_ebitda: 109.4,
          cost_savings_pcts: [2.0, 4.0, 6.0, 8.0, 10.0],
          multiples: [15.0, 18.0, 22.0, 26.0, 30.0]
        })
      });

      const d = await res.json();
      const tbody = document.getElementById('scenario-matrix-body');
      tbody.innerHTML = '';

      d.cost_reduction_steps_pct.forEach((step, rowIdx) => {
        const tr = document.createElement('tr');
        let rowHtml = `<td><strong>+${step.toFixed(1)}% Efficiency</strong></td>`;
        d.exit_multiples.forEach((m, colIdx) => {
          const val = d.matrix[rowIdx][colIdx];
          const delta = d.delta_value_matrix[rowIdx][colIdx];
          const isHigh = rowIdx >= 3 && colIdx >= 3;
          rowHtml += `
            <td class="sensitivity-cell ${isHigh ? 'highlight' : ''}">
              $${val.toFixed(1)}B
              <div style="font-size: 0.72rem; color: #86EFAC;">(+ $${delta.toFixed(1)}B)</div>
            </td>
          `;
        });
        tr.innerHTML = rowHtml;
        tbody.appendChild(tr);
      });
    } catch (err) {
      console.warn("Scenario Matrix load failed:", err);
    }
  }

  setTimeout(loadScenarioMatrix, 300);
}

// ---------------- 12. GRAPHRAG VALUE NETWORK ----------------
function initGraphRAG() {
  const refreshBtn = document.getElementById('btn-refresh-graph');
  const pathBtn = document.getElementById('btn-find-path');

  if (refreshBtn) refreshBtn.addEventListener('click', loadGraphData);
  if (pathBtn) pathBtn.addEventListener('click', findMultiHopPath);

  async function loadGraphData() {
    try {
      const res = await fetch('/api/graph/data');
      const d = await res.json();

      const corpBox = document.getElementById('graph-nodes-corporates');
      const suppBox = document.getElementById('graph-nodes-suppliers');
      const riskBox = document.getElementById('graph-nodes-risks');

      corpBox.innerHTML = '';
      suppBox.innerHTML = '';
      riskBox.innerHTML = '';

      d.nodes.forEach(n => {
        const span = document.createElement('div');
        span.className = 'network-node-badge';

        if (n.category === 'Enterprise' || n.category === 'Segment') {
          span.style.background = 'rgba(56, 189, 248, 0.15)';
          span.style.border = '1px solid rgba(56, 189, 248, 0.4)';
          span.style.color = '#38BDF8';
          span.innerHTML = `<strong>${escapeHtml(n.label)}</strong> <small>(${n.id})</small>`;
          corpBox.appendChild(span);
        } else if (n.category === 'Supplier' || n.category === 'Partner' || n.category === 'Technology') {
          span.style.background = 'rgba(245, 158, 11, 0.15)';
          span.style.border = '1px solid rgba(245, 158, 11, 0.4)';
          span.style.color = '#F59E0B';
          span.innerHTML = `<strong>${escapeHtml(n.label)}</strong> <small>(${n.category})</small>`;
          suppBox.appendChild(span);
        } else {
          span.style.background = 'rgba(244, 63, 94, 0.15)';
          span.style.border = '1px solid rgba(244, 63, 94, 0.4)';
          span.style.color = '#FDA4AF';
          span.innerHTML = `<strong>${escapeHtml(n.label)}</strong> <small>(${n.category})</small>`;
          riskBox.appendChild(span);
        }
      });
    } catch (err) {
      console.warn("Graph data load failed:", err);
    }
  }

  async function findMultiHopPath() {
    const src = document.getElementById('graph-source-select').value;
    const tgt = document.getElementById('graph-target-select').value;
    const resBox = document.getElementById('graph-path-result');
    const stepsBox = document.getElementById('graph-path-steps');

    try {
      const res = await fetch(`/api/graph/path?source=${encodeURIComponent(src)}&target=${encodeURIComponent(tgt)}`);
      const d = await res.json();

      resBox.style.display = 'block';
      if (d.paths && d.paths.length > 0) {
        const path = d.paths[0];
        let chain = `<strong>${src}</strong>`;
        path.forEach(step => {
          chain += ` &nbsp;──[<span style="color: #86EFAC;">${step.relation}</span>]──>&nbsp; <strong>${step.to}</strong>`;
        });
        stepsBox.innerHTML = chain;
      } else {
        stepsBox.innerHTML = `<span style="color: #94A3B8;">No direct path found under depth limit 4. Entities interact via market-level aggregate indices.</span>`;
      }
    } catch (err) {
      alert("Pathfinding error: " + err.message);
    }
  }

  setTimeout(loadGraphData, 400);
}

// ---------------- 13. VIRTUAL CLEAN ROOM (RBAC) ----------------
function initVirtualCleanRoom() {
  const btn = document.getElementById('btn-test-vdr-access');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    const role = document.getElementById('vdr-test-role-select').value;
    const resBox = document.getElementById('vdr-audit-results');
    const summary = document.getElementById('vdr-audit-summary');
    const accessible = document.getElementById('vdr-accessible-docs');

    resBox.style.display = 'block';

    const roleClearances = {
      'PUBLIC_ANALYST': ['PUBLIC_10K'],
      'STRATEGY_CONSULTANT': ['PUBLIC_10K', 'RESTRICTED_STRATEGY'],
      'MA_PARTNER_CLEANROOM': ['PUBLIC_10K', 'RESTRICTED_STRATEGY', 'CONFIDENTIAL_DEALROOM'],
      'COMPLIANCE_AUDITOR': ['PUBLIC_10K', 'RESTRICTED_STRATEGY', 'AUDIT_GOVERNANCE']
    };

    const allowed = roleClearances[role] || ['PUBLIC_10K'];
    summary.innerHTML = `Role <strong>${role}</strong> is authorized for clearance tiers: <span style="color: #34D399;">${allowed.join(', ')}</span>.`;

    let html = `<ul style="margin-left: 1.5rem; line-height: 1.8;">`;
    currentDocuments.forEach(doc => {
      const isConf = doc.file_name.toLowerCase().includes('clean') || doc.file_name.toLowerCase().includes('deal');
      const isPlaybook = doc.file_name.toLowerCase().includes('playbook') || doc.file_name.toLowerCase().includes('strategy');
      
      let docTier = 'PUBLIC_10K';
      if (isConf) docTier = 'CONFIDENTIAL_DEALROOM';
      else if (isPlaybook) docTier = 'RESTRICTED_STRATEGY';

      const hasAccess = allowed.includes(docTier);
      html += `
        <li>
          <strong>${escapeHtml(doc.file_name)}</strong> [${docTier}] — 
          <span style="color: ${hasAccess ? '#4ADE80' : '#F43F5E'}; font-weight: 700;">
            ${hasAccess ? '✓ Full Access Granted' : '✗ REDACTED / Clean Room Blocked'}
          </span>
        </li>
      `;
    });
    html += `</ul>`;
    accessible.innerHTML = html;
  });
}

// ---------------- 14. TELEMETRY & SEMANTIC CACHE ----------------
function initTelemetryAndCache() {
  const refreshBtn = document.getElementById('btn-refresh-cache-stats');
  const clearBtn = document.getElementById('btn-clear-cache');

  if (refreshBtn) refreshBtn.addEventListener('click', updateCacheStats);
  if (clearBtn) {
    clearBtn.addEventListener('click', async () => {
      await fetch('/api/cache/clear', { method: 'POST' });
      alert("Semantic Cache purged.");
      updateCacheStats();
    });
  }

  async function updateCacheStats() {
    try {
      const res = await fetch('/api/cache/stats');
      const d = await res.json();

      document.getElementById('cache-hit-rate').innerText = `${d.hit_rate_pct.toFixed(1)}%`;
      document.getElementById('cache-total-entries').innerText = d.total_entries;
      document.getElementById('cache-tokens-saved').innerText = `${d.estimated_tokens_saved.toLocaleString()} tokens`;
      document.getElementById('cache-cost-saved').innerText = `$${d.estimated_cost_saved_usd.toFixed(4)}`;
    } catch (err) {
      console.warn("Failed to fetch cache stats:", err);
    }
  }

  setTimeout(updateCacheStats, 500);
}

