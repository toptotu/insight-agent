async function fetchJSON(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json();
}

function createCheckbox(id, label, groupName, checked) {
  const wrapper = document.createElement("label");
  wrapper.className = "checkbox-inline";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.value = id;
  input.name = groupName;
  input.checked = checked;
  const span = document.createElement("span");
  span.textContent = label;
  wrapper.appendChild(input);
  wrapper.appendChild(span);
  return wrapper;
}

function renderCapabilityReport(container, report) {
  if (!report || !report.capabilities) {
    container.textContent = "未生成能力识别报告。";
    return;
  }
  const lines = [];
  lines.push(report.summary || "能力识别报告");
  report.capabilities.forEach((cap) => {
    lines.push(`- 能力：${cap.name}`);
    lines.push(`  成熟度：${cap.maturity}`);
    if (cap.evidence_titles && cap.evidence_titles.length) {
      lines.push(`  证据：${cap.evidence_titles.join("；")}`);
    }
    if (cap.verification_methods && cap.verification_methods.length) {
      lines.push(`  验证方法：${cap.verification_methods.join("；")}`);
    }
  });
  container.textContent = lines.join("\n");
}

function renderEvidence(container, evidenceChain) {
  if (!evidenceChain) {
    container.textContent = "未生成证据链。";
    return;
  }
  const lines = [];
  Object.keys(evidenceChain).forEach((agentName) => {
    lines.push(`【${agentName}】`);
    evidenceChain[agentName].forEach((item) => {
      lines.push(`- ${item.title} (${item.source})`);
    });
  });
  container.textContent = lines.join("\n");
}

function renderAgentResults(container, agentResults) {
  if (!agentResults || !agentResults.length) {
    container.textContent = "暂无Agent结果。";
    return;
  }
  const lines = [];
  agentResults.forEach((agent) => {
    lines.push(`【${agent.agent_name}】`);
    lines.push(agent.summary);
    lines.push("");
  });
  container.textContent = lines.join("\n");
}

async function initInsightPage() {
  const domainSelect = document.getElementById("domainSelect");
  if (!domainSelect) {
    return;
  }

  const agentsContainer = document.getElementById("agentsContainer");
  const skillsContainer = document.getElementById("skillsContainer");
  const runButton = document.getElementById("runInsightBtn");
  const objectiveInput = document.getElementById("objectiveInput");
  const topKInput = document.getElementById("topKInput");
  const minScoreInput = document.getElementById("minScoreInput");
  const rerankInput = document.getElementById("rerankInput");

  const resultMeta = document.getElementById("resultMeta");
  const resultSummary = document.getElementById("resultSummary");
  const resultCapabilities = document.getElementById("resultCapabilities");
  const resultEvidence = document.getElementById("resultEvidence");

  let meta = await fetchJSON("/api/meta");
  let domains = meta.domains || [];
  let agents = meta.agents || [];
  let skills = meta.skills || [];

  domains.forEach((domain) => {
    const option = document.createElement("option");
    option.value = domain.domain_id;
    option.textContent = domain.name;
    domainSelect.appendChild(option);
  });

  function renderAgents(defaults) {
    agentsContainer.innerHTML = "";
    agents.forEach((agent) => {
      const checked = defaults.includes(agent.agent_id);
      agentsContainer.appendChild(
        createCheckbox(agent.agent_id, `${agent.name} - ${agent.focus}`, "agents", checked)
      );
    });
  }

  function renderSkills(defaults) {
    skillsContainer.innerHTML = "";
    skills.forEach((skill) => {
      const checked = defaults.includes(skill.skill_id);
      skillsContainer.appendChild(
        createCheckbox(skill.skill_id, `${skill.name}`, "skills", checked)
      );
    });
  }

  function updateDefaults() {
    const domainId = domainSelect.value;
    const domain = domains.find((item) => item.domain_id === domainId);
    const defaultAgents = domain ? domain.default_agents : [];
    const defaultSkills = domain ? domain.default_skills : [];
    renderAgents(defaultAgents || []);
    renderSkills(defaultSkills || []);
  }

  domainSelect.addEventListener("change", updateDefaults);
  updateDefaults();

  runButton.addEventListener("click", async () => {
    runButton.disabled = true;
    runButton.textContent = "运行中...";
    resultMeta.textContent = "";
    resultSummary.textContent = "";
    resultCapabilities.textContent = "";
    resultEvidence.textContent = "";

    try {
      const selectedAgents = Array.from(
        document.querySelectorAll("input[name='agents']:checked")
      ).map((input) => input.value);
      const selectedSkills = Array.from(
        document.querySelectorAll("input[name='skills']:checked")
      ).map((input) => input.value);

      const payload = {
        domain_id: domainSelect.value,
        objective: objectiveInput.value || "6G技术洞察与安全验证能力分析",
        agent_ids: selectedAgents,
        skill_ids: selectedSkills,
        rag_config: {
          top_k: Number(topKInput.value) || 5,
          min_score: Number(minScoreInput.value) || 0.1,
          enable_rerank: Boolean(rerankInput.checked),
        },
      };

      const response = await fetchJSON("/api/insights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      resultMeta.innerHTML = `任务ID：${response.task_id} | LLM模式：${response.llm_mode} | <a href="/ui/report/${response.task_id}" target="_blank">打开报告</a>`;
      resultSummary.textContent = response.insight_summary || "";
      renderCapabilityReport(resultCapabilities, response.capability_report);
      renderEvidence(resultEvidence, response.skill_outputs.evidence_chain);
    } catch (error) {
      resultSummary.textContent = `发生错误：${error.message}`;
    } finally {
      runButton.disabled = false;
      runButton.textContent = "运行洞察";
    }
  });
}

async function initReportPage() {
  if (!window.__REPORT_TASK_ID__) {
    return;
  }
  const reportMeta = document.getElementById("reportMeta");
  const reportSummary = document.getElementById("reportSummary");
  const reportCapabilities = document.getElementById("reportCapabilities");
  const reportAgents = document.getElementById("reportAgents");
  const reportEvidence = document.getElementById("reportEvidence");

  try {
    const response = await fetchJSON(`/api/insights/${window.__REPORT_TASK_ID__}`);
    reportMeta.textContent = `领域：${response.domain.name} | LLM模式：${response.llm_mode}`;
    reportSummary.textContent = response.insight_summary || "";
    renderCapabilityReport(reportCapabilities, response.capability_report);
    renderAgentResults(reportAgents, response.agent_results);
    renderEvidence(reportEvidence, response.skill_outputs.evidence_chain);
  } catch (error) {
    reportSummary.textContent = `加载失败：${error.message}`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initInsightPage();
  initReportPage();
});
