const state = { code: null, lastRunId: null, approvalRole: null };

function byId(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed: ${response.status}`);
  return body;
}

function setText(id, value) {
  byId(id).textContent = value ?? "-";
}

function clearStats(message = "Create a link first") {
  setText("statEndpoint", "-");
  setText("statClicks", "-");
  setText("statOutcome", message);
  setText("statLast", "-");
}

function renderLink(link) {
  state.code = link.code;
  byId("linkResult").innerHTML = `
    Short link: <a href="${link.short_url}" target="_blank" rel="noreferrer">${escapeHtml(link.short_url)}</a>
  `;
  setText("statEndpoint", link.short_url);
  setText("statClicks", link.clicks);
  setText("statOutcome", "No visits yet");
  setText("statLast", "No visits yet");
}

async function refreshStats() {
  if (!state.code) {
    clearStats();
    return;
  }
  try {
    const stats = await request(`/api/links/${state.code}/stats`);
    setText("statEndpoint", stats.short_url);
    setText("statClicks", stats.clicks);
    setText("statOutcome", stats.last_outcome || "No visits yet");
    setText("statLast", stats.last_accessed_at || "No visits yet");
  } catch (error) {
    clearStats(error.message);
  }
}

byId("linkForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const expiresValue = byId("expiresAt").value;
  const maxClicks = byId("maxClicks").value;
  try {
    const link = await request("/api/links", {
      method: "POST",
      body: JSON.stringify({
        target_url: byId("targetUrl").value,
        custom_endpoint: byId("customEndpoint").value.trim() || null,
        expires_at: expiresValue ? new Date(expiresValue).toISOString() : null,
        max_clicks: maxClicks ? Number(maxClicks) : null,
      }),
    });
    renderLink(link);
  } catch (error) {
    byId("linkResult").innerHTML = `<span class="error">${escapeHtml(error.message)}</span>`;
  }
});

byId("refreshStats").addEventListener("click", refreshStats);

function listItems(items, renderer) {
  return items.map(renderer).join("");
}

function renderEvidence(evidence) {
  state.lastRunId = evidence.run_id;
  const statusClass = evidence.status === "reviewable_outcome_ready" ? "status-ready" : "status-waiting";
  byId("evidence").innerHTML = `
    <p class="eyebrow">${escapeHtml(evidence.scenario)} scenario</p>
    <h2>${escapeHtml(evidence.title)}</h2>
    <p class="${statusClass}">Status: ${escapeHtml(evidence.status)}</p>
    <p><strong>Approval:</strong> ${escapeHtml(evidence.approval_role || "Not approved")}</p>
    <p><strong>Scope:</strong> ${escapeHtml(evidence.scope_assessment?.status || "not assessed")} - ${escapeHtml(evidence.scope_assessment?.decision || "")}</p>

    <div class="evidence-section">
      <h4>Requirement understanding</h4>
      <p><strong>Submitted:</strong> ${escapeHtml(evidence.submitted_requirement)}</p>
      <p><strong>Normalized:</strong> ${escapeHtml(evidence.normalized_problem)}</p>
      ${evidence.ambiguity_notes.length ? `<pre>${escapeHtml(evidence.ambiguity_notes.join("\n"))}</pre>` : ""}
    </div>

    <div class="evidence-section">
      <h4>Task decomposition</h4>
      <ul class="task-list">
        ${listItems(evidence.task_decomposition, (task) => `<li><span>${escapeHtml(task.id)} depends on ${escapeHtml(JSON.stringify(task.depends_on))}</span>${escapeHtml(task.task)}</li>`)}
      </ul>
    </div>

    <div class="evidence-section">
      <h4>Codebase reasoning</h4>
      <p>${escapeHtml(evidence.codebase_reasoning.data_flow)}</p>
      <div class="artifact-row">${listItems(evidence.codebase_reasoning.impacted_components, (item) => `<span>${escapeHtml(item)}</span>`)}</div>
    </div>

    <div class="evidence-section">
      <h4>AI assistance traceability</h4>
      <ul class="trace-list">
        ${listItems(evidence.ai_assisted_execution, (item) => `<li><span>${escapeHtml(item.task)} · ${escapeHtml(item.engineer_action)}</span><strong>Prompt intent:</strong> ${escapeHtml(item.prompt_intent)}<br><strong>AI suggestion:</strong> ${escapeHtml(item.ai_suggestion)}<br><strong>Engineer rationale:</strong> ${escapeHtml(item.rationale)}</li>`)}
      </ul>
    </div>

    <div class="evidence-section">
      <h4>Quality gates</h4>
      <ul class="gate-list">
        ${listItems(evidence.quality_gates, (gate) => `<li><span>${escapeHtml(gate.status)}</span><strong>${escapeHtml(gate.name)}</strong>: ${escapeHtml(gate.evidence)}</li>`)}
      </ul>
    </div>

    <div class="evidence-section">
      <h4>Compliance matrix</h4>
      <ul class="gate-list">
        ${listItems(evidence.compliance_matrix || [], (item) => `<li><span>${escapeHtml(item.status)}</span><strong>${escapeHtml(item.requirement)}</strong>: ${escapeHtml(item.coverage)}</li>`)}
      </ul>
    </div>

    <div class="evidence-section">
      <h4>Risks, assumptions, limitations</h4>
      <pre>${escapeHtml(JSON.stringify({ risks: evidence.risks, assumptions: evidence.assumptions, limitations: evidence.limitations }, null, 2))}</pre>
    </div>

    <div class="evidence-section">
      <h4>Final engineering summary</h4>
      <p>${escapeHtml(evidence.final_summary)}</p>
      <div class="badge-row"><a class="badge" href="/engineering/runs/${evidence.run_id}/summary.md">Download summary.md</a><a class="badge" href="/engineering/runs/${evidence.run_id}">JSON evidence</a></div>
    </div>
  `;
}

async function runEngineering() {
  const evidencePanel = byId("evidence");
  evidencePanel.innerHTML = "<p>Generating engineer-led AI assistance evidence...</p>";
  try {
    const evidence = await request("/engineering/execute", {
      method: "POST",
      body: JSON.stringify({
        scenario: byId("scenario").value,
        requirement: byId("requirement").value,
        engineer_notes: byId("engineerNotes").value,
        engineer_signoff: Boolean(state.approvalRole),
        approval_role: state.approvalRole,
      }),
    });
    renderEvidence(evidence);
  } catch (error) {
    evidencePanel.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
  }
}

byId("runEngineering").addEventListener("click", () => {
  state.approvalRole = null;
  byId("approvalNote").textContent = "Generated without approval. Use approval buttons to sign off.";
  runEngineering();
});

byId("scenario").addEventListener("change", (event) => {
  const scenario = event.target.value;
  const requirements = {
    greenfield: "Build a URL shortener service from scratch with create, redirect, analytics, expiry, max-click limits, tests, and documentation.",
    brownfield: "Enhance the existing shortener with expiry and max-click controls while preserving create, redirect, and analytics behavior.",
    ambiguous: "Make links safer and smarter for advisors without making the product complicated.",
  };
  byId("requirement").value = requirements[scenario];
  state.approvalRole = null;
  byId("approvalNote").textContent = "No approval recorded yet.";
});

function approveAs(role) {
  state.approvalRole = role;
  byId("approvalNote").textContent = `${role} approval recorded. Generating approved engineering outcome...`;
  runEngineering();
}

byId("engineerApprove").addEventListener("click", () => approveAs("Engineer"));
byId("businessApprove").addEventListener("click", () => approveAs("Business"));

clearStats();
