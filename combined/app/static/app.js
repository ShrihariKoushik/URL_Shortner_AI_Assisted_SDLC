const state = { slug: "schwab-demo", runId: null, waitingNode: null };
const displayDomain = "https://short.demo";
const nodes = [...document.querySelectorAll(".node")];

function setText(id, value) {
  document.getElementById(id).textContent = value ?? "-";
}

function showLinkResult(slug) {
  const box = document.getElementById("shortenResult");
  box.classList.remove("error");
  box.innerHTML = `
    <span class="result-label">Short link</span>
    <a class="short-link" href="/${slug}" target="_blank" rel="noreferrer">${displayDomain}/${slug}</a>
    <span class="result-note">Opens through this local demo app.</span>
  `;
}
function showResult(message, isError = false) {
  const box = document.getElementById("shortenResult");
  box.textContent = message;
  box.classList.toggle("error", isError);
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

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function refreshStats() {
  try {
    const stats = await request(`/stats/${state.slug}`);
    setText("statSlug", `${displayDomain}/${stats.slug}`);
    setText("statClicks", stats.clicks);
    setText("statLast", stats.last_accessed_at || "Not opened yet");
  } catch (error) {
    setText("statSlug", state.slug ? `${displayDomain}/${state.slug}` : "-");
    setText("statClicks", "-");
    setText("statLast", error.message);
  }
}

function resetDag(scenario) {
  document.body.dataset.scenario = scenario;
  nodes.forEach((node) => {
    node.classList.remove("passed", "waiting", "failed");
  });
}

function renderRun(run) {
  state.runId = run.run_id;
  state.waitingNode = null;
  const context = run.context;
  const statuses = context.node_status || {};
  nodes.forEach((node) => {
    const status = statuses[node.dataset.node];
    node.classList.toggle("passed", status === "passed");
    node.classList.toggle("waiting", status === "waiting_for_approval");
    node.classList.toggle("failed", status === "failed" || status === "rolled_back");
    if (status === "waiting_for_approval") state.waitingNode = node.dataset.node;
  });

  const waiting = run.status === "waiting_for_approval";
  setText("runStatus", waiting ? `Waiting for approval: ${state.waitingNode}` : `Status: ${run.status}`);
  document.getElementById("approveRelease").classList.toggle("hidden", !waiting);
  const reportLink = document.getElementById("downloadSdlc");
  const jsonLink = document.getElementById("downloadSdlcJson");
  if (reportLink && jsonLink && run.run_id) {
    reportLink.href = `/agent/runs/${run.run_id}/report`;
    jsonLink.href = `/agent/runs/${run.run_id}/report.json`;
    reportLink.classList.remove("hidden");
    jsonLink.classList.remove("hidden");
  }

  const metrics = context.metrics || {};
  setText("metricSuccess", metrics.success_rate === undefined ? "-" : `${Math.round(metrics.success_rate * 100)}%`);
  setText("metricRetries", metrics.retry_count);
  setText("metricFallbacks", metrics.fallback_count);
  setText("metricRollbacks", metrics.rollback_count);
  setText("metricLatency", metrics.end_to_end_latency_seconds ? `${metrics.end_to_end_latency_seconds}s` : "-");
}

document.getElementById("shortenForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const target = document.getElementById("targetUrl").value;
  const slug = document.getElementById("customSlug").value.trim();
  try {
    const created = await request("/shorten", {
      method: "POST",
      body: JSON.stringify({ url: target, custom_slug: slug || null }),
    });
    state.slug = created.slug;
    showLinkResult(created.slug);
    await refreshStats();
  } catch (error) {
    state.slug = slug;
    showResult(error.message, true);
    await refreshStats();
  }
});

document.getElementById("refreshStats").addEventListener("click", refreshStats);

document.getElementById("runWorkflow").addEventListener("click", async () => {
  const scenario = document.getElementById("scenarioSelect").value;
  const autoApprove = document.getElementById("autoApprove").checked;
  resetDag(scenario);
  setText("runStatus", "Running workflow...");
  const run = await request(`/agent/scenarios/${scenario}/run`, {
    method: "POST",
    body: JSON.stringify({ auto_approve: autoApprove }),
  });
  renderRun(run);
});

document.getElementById("approveRelease").addEventListener("click", async () => {
  if (!state.runId || !state.waitingNode) return;
  const run = await request(`/agent/runs/${state.runId}/approve/${state.waitingNode}`, {
    method: "POST",
    body: JSON.stringify({ approved: true, approver: "business-reviewer", comment: "Approved from demo console" }),
  });
  renderRun(run);
});

document.getElementById("scenarioSelect").addEventListener("change", (event) => resetDag(event.target.value));
resetDag("greenfield");
refreshStats();





const scenarioProof = {
  greenfield: {
    title: "Greenfield: new build workflow",
    proves: "Takes a clear new requirement through requirements, architecture, implementation, tests, security, docs, and release governance.",
    watch: "Look for normal SDLC flow and release approval readiness.",
  },
  brownfield: {
    title: "Brownfield: existing system enhancement",
    proves: "Adds impact analysis before architecture so reviewers can see affected modules and data flow risk.",
    watch: "Look for impact_analysis plus preservation of existing URL shortener behavior.",
  },
  ambiguous: {
    title: "Ambiguous: clarification before execution",
    proves: "Pauses for clarification when scope is vague, before architecture proceeds.",
    watch: "Look for clarification waiting for approval when auto approve is off.",
  },
};

function statusClass(status) {
  if (status === "passed") return "ok";
  if (status === "waiting_for_approval") return "wait";
  if (status === "failed" || status === "rolled_back") return "bad";
  return "neutral";
}

function renderScenarioOutput(run, scenario) {
  const output = document.getElementById("scenarioOutput");
  const context = run.context || {};
  const metrics = context.metrics || {};
  const statuses = context.node_status || {};
  const proof = scenarioProof[scenario];
  const stageRows = Object.entries(statuses)
    .map(([node, status]) => `<li><span>${node}</span><strong class="${statusClass(status)}">${status}</strong></li>`)
    .join("");
  const waitingNode = Object.entries(statuses).find(([, status]) => status === "waiting_for_approval")?.[0];
  const approveButton = waitingNode
    ? `<button type="button" class="secondary" id="scenarioApprove" data-run-id="${run.run_id}" data-node-id="${waitingNode}" data-scenario="${scenario}">Approve ${waitingNode}</button>`
    : "";
  output.innerHTML = `
    <div class="scenario-proof">
      <h4>${proof.title}</h4>
      <p>${proof.proves}</p>
      <p><strong>Submitted requirement:</strong> ${escapeHtml(context.change_request || "Default scenario requirement")}</p>
      <p><strong>Normalized by requirements agent:</strong> ${escapeHtml(context.normalized_requirement || "Pending")}</p>
      <p><strong>Evaluator should watch:</strong> ${proof.watch}</p>
      <p><strong>Run status:</strong> ${run.status}</p>
    </div>
    <ul class="stage-list">${stageRows}</ul>
    <div class="scenario-metrics">
      <span>Success: ${metrics.success_rate === undefined ? "pending" : Math.round(metrics.success_rate * 100) + "%"}</span>
      <span>Retries: ${metrics.retry_count ?? 0}</span>
      <span>Fallbacks: ${metrics.fallback_count ?? 0}</span>
      <span>Rollbacks: ${metrics.rollback_count ?? 0}</span>
      <span>Latency: ${metrics.end_to_end_latency_seconds ?? 0}s</span>
    </div>
    <div class="scenario-links">
      ${approveButton}
      <a href="/agent/runs/${run.run_id}/report">Download this run PDF</a>
      <a href="/agent/runs/${run.run_id}/report.json">Download JSON evidence</a>
      <a href="/reports/analysis/${scenario}">Download ${scenario} evaluator PDF</a>
    </div>
  `;
  const approve = document.getElementById("scenarioApprove");
  if (approve) {
    approve.addEventListener("click", async () => {
      const approved = await request(`/agent/runs/${approve.dataset.runId}/approve/${approve.dataset.nodeId}`, {
        method: "POST",
        body: JSON.stringify({
          approved: true,
          approver: "scenario-lab-reviewer",
          comment: "Approved from Scenario Test Lab",
        }),
      });
      renderScenarioOutput(approved, approve.dataset.scenario);
      renderRun(approved);
    });
  }
}

async function runScenarioLab(scenario) {
  const output = document.getElementById("scenarioOutput");
  const autoApprove = document.getElementById("scenarioAutoApprove").checked;
  const requirement = document.getElementById("scenarioRequirement").value.trim();
  output.innerHTML = `<p>Running ${scenario} scenario against /agent/scenarios/${scenario}/run...</p>`;
  resetDag(scenario);
  const run = await request(`/agent/scenarios/${scenario}/run`, {
    method: "POST",
    body: JSON.stringify({ auto_approve: autoApprove, change_request: requirement || null }),
  });
  renderScenarioOutput(run, scenario);
  renderRun(run);
}

document.querySelectorAll("[data-scenario-run]").forEach((button) => {
  button.addEventListener("click", () => runScenarioLab(button.dataset.scenarioRun));
});

function renderExecutionResult(result) {
  const output = document.getElementById("executionOutput");
  const tasks = (result.tasks || [])
    .map((task) => `<li><span>${escapeHtml(task.id)} · ${escapeHtml(task.stage)}</span><strong>${escapeHtml(task.task)}</strong></li>`)
    .join("");
  const files = (result.impacted_files || []).map((file) => `<span>${escapeHtml(file)}</span>`).join("");
  const validation = result.validation || {};
  const metrics = result.metrics || {};
  const approval = result.approval || {};
  output.innerHTML = `
    <div class="scenario-proof">
      <h4>${escapeHtml(result.title || "Engineering change execution")}</h4>
      <p><strong>Submitted requirement:</strong> ${escapeHtml(result.requirement)}</p>
      <p><strong>Normalized requirement:</strong> ${escapeHtml(result.normalized_requirement)}</p>
      <p><strong>Classification:</strong> ${escapeHtml(result.classification)} · <strong>Status:</strong> ${escapeHtml(result.status)}</p>
      <p><strong>Approval checkpoint:</strong> ${approval.required ? "waiting before code patch" : "approved and executed"}</p>
    </div>
    <h4>Generated task decomposition</h4>
    <ul class="stage-list execution-tasks">${tasks}</ul>
    <h4>Impacted files and data flow</h4>
    <div class="file-pills">${files}</div>
    <h4>Patch generated by implementation stage</h4>
    <pre class="diff-box">${escapeHtml(result.patch?.diff || "Patch is waiting for approval. Turn on Approve code change and run again to apply it.")}</pre>
    <h4>Validation result</h4>
    <div class="scenario-metrics">
      <span>Tests: ${validation.passed ? "passed" : "not passed"}</span>
      <span>Return code: ${validation.returncode ?? "not run"}</span>
      <span>Success: ${Math.round((metrics.success_rate || 0) * 100)}%</span>
      <span>Latency: ${metrics.end_to_end_latency_seconds || 0}s</span>
    </div>
    <pre class="test-output">${escapeHtml((validation.stdout || validation.stderr || "Tests are waiting for approval.").trim())}</pre>
  `;
}

async function executeRequirementChange() {
  const output = document.getElementById("executionOutput");
  const requirement = document.getElementById("executeRequirement").value.trim();
  const autoApprove = document.getElementById("executeAutoApprove").checked;
  if (!requirement) {
    output.innerHTML = `<p class="error-text">Enter a requirement before running execution.</p>`;
    return;
  }
  output.innerHTML = `<p>Executing governed change path: understand requirement, decompose tasks, apply patch, run tests...</p>`;
  const result = await request("/agent/execute-change", {
    method: "POST",
    body: JSON.stringify({ requirement, auto_approve: autoApprove }),
  });
  renderExecutionResult(result);
}

const executeButton = document.getElementById("executeChange");
if (executeButton) {
  executeButton.addEventListener("click", executeRequirementChange);
}
