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




