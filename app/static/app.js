async function fetchJSON(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json();
}

function formatDate(epochSeconds) {
  if (!epochSeconds) {
    return "";
  }
  const date = new Date(epochSeconds * 1000);
  return date.toLocaleString();
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

function createTag(label) {
  const tag = document.createElement("span");
  tag.className = "tag";
  tag.textContent = label;
  return tag;
}

function renderCapabilityReport(container, report) {
  if (!container) {
    return;
  }
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

function renderCustomSkills(container, customSkills) {
  if (!container) {
    return;
  }
  if (!customSkills || !customSkills.length) {
    container.textContent = "";
    return;
  }
  const lines = ["自定义Skill提示："];
  customSkills.forEach((skill) => {
    lines.push(`- ${skill.name}: ${skill.description || "自定义Skill"}`);
  });
  container.textContent = lines.join("\n");
}

function renderEvidence(container, evidenceChain) {
  if (!container) {
    return;
  }
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
  if (!container) {
    return;
  }
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

function renderSummaryCards(container, summaryText) {
  if (!container) {
    return;
  }
  container.innerHTML = "";
  if (!summaryText) {
    return;
  }
  const lines = summaryText
    .split("\n")
    .map((line) => line.replace(/^[-*\d\.\s]+/, "").trim())
    .filter((line) => line.length > 0);
  lines.slice(0, 6).forEach((line) => {
    const card = document.createElement("div");
    card.className = "card";
    const text = document.createElement("p");
    text.textContent = line;
    card.appendChild(text);
    container.appendChild(card);
  });
}

function renderBulletList(container, text) {
  if (!container) {
    return;
  }
  container.innerHTML = "";
  if (!text) {
    container.textContent = "";
    return;
  }
  const lines = text
    .split("\n")
    .map((line) => line.replace(/^[-*\d\.\s]+/, "").trim())
    .filter((line) => line.length > 0);
  const list = document.createElement("ul");
  list.className = "bullet-list";
  lines.forEach((line) => {
    const item = document.createElement("li");
    item.textContent = line;
    list.appendChild(item);
  });
  container.appendChild(list);
}

function renderViewpoints(container, comparison) {
  if (!container) {
    return;
  }
  container.innerHTML = "";
  if (!comparison || !comparison.common_keywords) {
    container.textContent = "暂无关键词热点。";
    return;
  }
  comparison.common_keywords.forEach((keyword) => {
    container.appendChild(createTag(keyword));
  });
}

function renderTrending(container, trend) {
  if (!container) {
    return;
  }
  container.innerHTML = "";
  if (!trend || !trend.trending_keywords) {
    container.textContent = "";
    return;
  }
  trend.trending_keywords.forEach((keyword) => {
    container.appendChild(createTag(keyword));
  });
}

function renderOutline(container, outline) {
  if (!container) {
    return;
  }
  if (!outline || !outline.outline) {
    container.textContent = "";
    return;
  }
  const lines = ["报告大纲：", ...outline.outline];
  if (outline.contributors && outline.contributors.length) {
    lines.push(`贡献Agent：${outline.contributors.join("、")}`);
  }
  container.textContent = lines.join("\n");
}

function renderVerificationPlan(container, plan) {
  if (!container) {
    return;
  }
  if (!plan || !plan.plan) {
    container.textContent = "";
    return;
  }
  const lines = ["验证计划：", ...plan.plan];
  container.textContent = lines.join("\n");
}

function renderSourceCollection(container, collection) {
  if (!container) {
    return;
  }
  if (!collection) {
    container.textContent = "";
    return;
  }
  const lines = ["洞察源采集建议："];
  if (collection.recommended_sources) {
    collection.recommended_sources.forEach((item) => lines.push(`- ${item}`));
  }
  if (collection.source_type_counts) {
    lines.push("当前证据来源分布：");
    Object.keys(collection.source_type_counts).forEach((key) => {
      lines.push(`- ${key}: ${collection.source_type_counts[key]}`);
    });
  }
  container.textContent = lines.join("\n");
}

function renderChart(container, config) {
  if (!container || !window.Chart || !(container instanceof HTMLCanvasElement)) {
    return false;
  }
  if (container.__chart) {
    container.__chart.destroy();
  }
  container.__chart = new window.Chart(container, config);
  return true;
}

function renderBarChart(container, labels, values) {
  if (!container) {
    return;
  }
  if (!labels.length) {
    container.textContent = "暂无数据";
    return;
  }
  if (container instanceof HTMLCanvasElement && !window.Chart) {
    const parent = container.parentElement;
    if (parent) {
      parent.textContent = "图表库未加载，无法绘制。";
    }
    return;
  }
  if (renderChart(container, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "数量",
          data: values,
          backgroundColor: "rgba(56, 189, 248, 0.7)",
          borderColor: "rgba(14, 116, 144, 1)",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 } },
      },
    },
  })) {
    return;
  }
  container.innerHTML = "";
  const max = Math.max(...values, 1);
  labels.forEach((label, index) => {
    const row = document.createElement("div");
    row.className = "chart-row";
    const caption = document.createElement("div");
    caption.className = "chart-label";
    caption.textContent = label;
    const barWrap = document.createElement("div");
    barWrap.className = "chart-bar-wrap";
    const bar = document.createElement("div");
    bar.className = "chart-bar";
    bar.style.width = `${(values[index] / max) * 100}%`;
    const value = document.createElement("span");
    value.className = "chart-value";
    value.textContent = String(values[index]);
    barWrap.appendChild(bar);
    barWrap.appendChild(value);
    row.appendChild(caption);
    row.appendChild(barWrap);
    container.appendChild(row);
  });
}

function renderPieChart(container, labels, values) {
  if (!container) {
    return;
  }
  if (!labels.length) {
    container.textContent = "暂无数据";
    return;
  }
  if (container instanceof HTMLCanvasElement && !window.Chart) {
    const parent = container.parentElement;
    if (parent) {
      parent.textContent = "图表库未加载，无法绘制。";
    }
    return;
  }
  renderChart(container, {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: [
            "rgba(59, 130, 246, 0.7)",
            "rgba(34, 197, 94, 0.7)",
            "rgba(251, 191, 36, 0.7)",
            "rgba(248, 113, 113, 0.7)",
            "rgba(167, 139, 250, 0.7)",
          ],
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "bottom" },
      },
    },
  });
}

function renderHistoryTable(container, items) {
  if (!container) {
    return;
  }
  if (!items || !items.length) {
    container.textContent = "暂无历史任务。";
    return;
  }
  const header = `
    <div class="table-row table-header">
      <div>时间</div>
      <div>领域</div>
      <div>目标</div>
      <div>LLM</div>
      <div>摘要</div>
      <div>操作</div>
    </div>
  `;
  const rows = items
    .map(
      (item) => `
      <div class="table-row">
        <div>${formatDate(item.created_at)}</div>
        <div>${item.domain_name || item.domain_id}</div>
        <div>${item.objective}</div>
        <div>${item.llm_mode}</div>
        <div>${item.summary_line}</div>
        <div><a href="/ui/report/${item.task_id}" target="_blank">打开报告</a></div>
      </div>
    `
    )
    .join("");
  container.innerHTML = header + rows;
}

function renderSimpleTable(container, headers, rows) {
  if (!container) {
    return;
  }
  if (!rows.length) {
    container.textContent = "暂无记录。";
    return;
  }
  const headerCells = headers.map((h) => `<div>${h}</div>`).join("");
  const header = `<div class="table-row table-header">${headerCells}</div>`;
  const body = rows
    .map((row) => {
      const cells = row.map((value) => `<div>${value}</div>`).join("");
      return `<div class="table-row">${cells}</div>`;
    })
    .join("");
  container.innerHTML = header + body;
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
    option.textContent = domain.origin === "custom" ? `${domain.name}（自定义）` : domain.name;
    domainSelect.appendChild(option);
  });

  function renderAgents(defaults, domainId) {
    agentsContainer.innerHTML = "";
    agents
      .filter((agent) => !agent.domain_id || agent.domain_id === domainId)
      .forEach((agent) => {
        const checked = defaults.includes(agent.agent_id);
        const originLabel = agent.origin === "custom" ? "【自定义】" : "";
        const categoryLabel = agent.category ? `(${agent.category})` : "";
        agentsContainer.appendChild(
          createCheckbox(
            agent.agent_id,
            `${originLabel}${agent.name}${categoryLabel} - ${agent.focus}`,
            "agents",
            checked
          )
        );
      });
  }

  function renderSkills(defaults) {
    skillsContainer.innerHTML = "";
    skills.forEach((skill) => {
      const checked = defaults.includes(skill.skill_id);
      const originLabel = skill.origin === "custom" ? "【自定义】" : "";
      const categoryLabel = skill.category ? `(${skill.category})` : "";
      skillsContainer.appendChild(
        createCheckbox(skill.skill_id, `${originLabel}${skill.name}${categoryLabel}`, "skills", checked)
      );
    });
  }

  function updateDefaults() {
    const domainId = domainSelect.value;
    const domain = domains.find((item) => item.domain_id === domainId);
    let defaultAgents = domain ? domain.default_agents : [];
    if ((!defaultAgents || !defaultAgents.length) && domain && domain.origin === "custom") {
      defaultAgents = agents
        .filter((agent) => agent.domain_id === domain.domain_id)
        .map((agent) => agent.agent_id);
    }
    const defaultSkills = domain ? domain.default_skills : [];
    renderAgents(defaultAgents || [], domainId);
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
      renderEvidence(resultEvidence, (response.skill_outputs || {}).evidence_chain);
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
  const reportObjective = document.getElementById("reportObjective");
  const reportDate = document.getElementById("reportDate");
  const reportSummary = document.getElementById("reportSummary");
  const reportSummaryCards = document.getElementById("reportSummaryCards");
  const reportOutline = document.getElementById("reportOutline");
  const reportViewpoints = document.getElementById("reportViewpoints");
  const reportComparison = document.getElementById("reportComparison");
  const reportTrendInsight = document.getElementById("reportTrendInsight");
  const reportCapabilityChart = document.getElementById("reportCapabilityChart");
  const reportCapabilities = document.getElementById("reportCapabilities");
  const reportCustomSkills = document.getElementById("reportCustomSkills");
  const reportVerificationPlan = document.getElementById("reportVerificationPlan");
  const reportEvidenceChart = document.getElementById("reportEvidenceChart");
  const reportAgents = document.getElementById("reportAgents");
  const reportEvidence = document.getElementById("reportEvidence");
  const reportSourceCollection = document.getElementById("reportSourceCollection");
  const reportSourceChart = document.getElementById("reportSourceChart");

  try {
    const response = await fetchJSON(`/api/insights/${window.__REPORT_TASK_ID__}`);
    const skillOutputs = response.skill_outputs || {};
    reportMeta.textContent = `领域：${response.domain.name} | LLM模式：${response.llm_mode}`;
    reportObjective.textContent = response.objective || "洞察目标";
    reportDate.textContent = response.created_at ? `生成时间：${formatDate(response.created_at)}` : "";
    renderBulletList(reportSummary, response.insight_summary || "");
    renderSummaryCards(reportSummaryCards, response.insight_summary || "");
    renderOutline(reportOutline, skillOutputs.report_outline);

    if (skillOutputs.trend_synthesis && skillOutputs.trend_synthesis.trending_keywords) {
      renderTrending(reportViewpoints, skillOutputs.trend_synthesis);
      reportTrendInsight.textContent = skillOutputs.trend_synthesis.insight || "";
    } else {
      renderViewpoints(reportViewpoints, skillOutputs.comparison);
    }
    reportComparison.textContent = skillOutputs.comparison
      ? skillOutputs.comparison.observation
      : "暂无对比分析。";

    renderCapabilityReport(reportCapabilities, response.capability_report);
    renderCustomSkills(reportCustomSkills, skillOutputs.custom_skills);
    renderVerificationPlan(reportVerificationPlan, skillOutputs.verification_plan);

    const capabilityCounts = { 高: 0, 中: 0, 低: 0 };
    (response.capability_report.capabilities || []).forEach((cap) => {
      if (capabilityCounts[cap.maturity] !== undefined) {
        capabilityCounts[cap.maturity] += 1;
      }
    });
    renderBarChart(reportCapabilityChart, ["高", "中", "低"], [
      capabilityCounts["高"],
      capabilityCounts["中"],
      capabilityCounts["低"],
    ]);

    const evidenceChain = skillOutputs.evidence_chain || {};
    const agentNames = Object.keys(evidenceChain);
    const evidenceCounts = agentNames.map((name) => evidenceChain[name].length || 0);
    renderBarChart(reportEvidenceChart, agentNames, evidenceCounts);

    renderAgentResults(reportAgents, response.agent_results);
    renderEvidence(reportEvidence, evidenceChain);
    renderSourceCollection(reportSourceCollection, skillOutputs.source_collection);

    if (skillOutputs.source_collection && skillOutputs.source_collection.source_type_counts) {
      const sourceTypes = Object.keys(skillOutputs.source_collection.source_type_counts);
      const sourceCounts = sourceTypes.map(
        (key) => skillOutputs.source_collection.source_type_counts[key]
      );
      renderPieChart(reportSourceChart, sourceTypes, sourceCounts);
    }
  } catch (error) {
    if (reportSummary) {
      reportSummary.textContent = `加载失败：${error.message}`;
    }
  }
}

async function initHistoryPage() {
  const historyTable = document.getElementById("historyTable");
  if (!historyTable) {
    return;
  }
  try {
    const response = await fetchJSON("/api/tasks?limit=50");
    renderHistoryTable(historyTable, response.items || []);
  } catch (error) {
    historyTable.textContent = `加载失败：${error.message}`;
  }
}

async function initConfigPage() {
  const message = document.getElementById("configMessage");
  if (!message) {
    return;
  }

  const domainNameInput = document.getElementById("domainNameInput");
  const domainIdInput = document.getElementById("domainIdInput");
  const domainDescInput = document.getElementById("domainDescInput");
  const createDomainBtn = document.getElementById("createDomainBtn");
  const domainList = document.getElementById("domainList");

  const skillNameInput = document.getElementById("skillNameInput");
  const skillIdInput = document.getElementById("skillIdInput");
  const skillDescInput = document.getElementById("skillDescInput");
  const skillCategoryInput = document.getElementById("skillCategoryInput");
  const skillModeSelect = document.getElementById("skillModeSelect");
  const skillInputFields = document.getElementById("skillInputFields");
  const skillOutputFields = document.getElementById("skillOutputFields");
  const skillPromptTemplate = document.getElementById("skillPromptTemplate");
  const skillTagsInput = document.getElementById("skillTagsInput");
  const skillExampleOutput = document.getElementById("skillExampleOutput");
  const createSkillBtn = document.getElementById("createSkillBtn");
  const skillList = document.getElementById("skillList");

  const agentNameInput = document.getElementById("agentNameInput");
  const agentFocusInput = document.getElementById("agentFocusInput");
  const agentDescInput = document.getElementById("agentDescInput");
  const agentQueryInput = document.getElementById("agentQueryInput");
  const agentDomainSelect = document.getElementById("agentDomainSelect");
  const agentIdInput = document.getElementById("agentIdInput");
  const agentSkillSelect = document.getElementById("agentSkillSelect");
  const agentCategorySelect = document.getElementById("agentCategorySelect");
  const createAgentBtn = document.getElementById("createAgentBtn");
  const agentList = document.getElementById("agentList");

  const docDomainSelect = document.getElementById("docDomainSelect");
  const docSourceTypeInput = document.getElementById("docSourceTypeInput");
  const docTitleInput = document.getElementById("docTitleInput");
  const docSourceInput = document.getElementById("docSourceInput");
  const docContentInput = document.getElementById("docContentInput");
  const createDocBtn = document.getElementById("createDocBtn");
  const docList = document.getElementById("docList");

  let meta = await fetchJSON("/api/meta");
  let domains = meta.domains || [];
  let skills = meta.skills || [];

  function populateDomainSelect(select) {
    select.innerHTML = "";
    domains.forEach((domain) => {
      const option = document.createElement("option");
      option.value = domain.domain_id;
      option.textContent = domain.origin === "custom" ? `${domain.name}（自定义）` : domain.name;
      select.appendChild(option);
    });
  }

  function populateSkillCheckboxes() {
    agentSkillSelect.innerHTML = "";
    skills.forEach((skill) => {
      const label = skill.origin === "custom" ? `【自定义】${skill.name}` : skill.name;
      agentSkillSelect.appendChild(createCheckbox(skill.skill_id, label, "agentSkills", false));
    });
  }

  async function refreshMeta() {
    meta = await fetchJSON("/api/meta");
    domains = meta.domains || [];
    skills = meta.skills || [];
    populateDomainSelect(agentDomainSelect);
    populateDomainSelect(docDomainSelect);
    populateSkillCheckboxes();
  }

  function showMessage(text) {
    message.textContent = text;
    setTimeout(() => {
      message.textContent = "";
    }, 3000);
  }

  async function refreshLists() {
    const [domainResp, skillResp, agentResp, docResp] = await Promise.all([
      fetchJSON("/api/config/domains"),
      fetchJSON("/api/config/skills"),
      fetchJSON("/api/config/agents"),
      fetchJSON("/api/config/documents"),
    ]);

    renderSimpleTable(
      domainList,
      ["领域ID", "名称", "描述", "创建时间"],
      (domainResp.items || []).map((item) => [
        item.domain_id,
        item.name,
        item.description,
        formatDate(item.created_at),
      ])
    );

    renderSimpleTable(
      skillList,
      ["Skill ID", "名称", "类别", "模式", "标签", "描述"],
      (skillResp.items || []).map((item) => [
        item.skill_id,
        item.name,
        item.category || "-",
        item.mode || "-",
        (item.tags || []).join(", "),
        item.description || "",
      ])
    );

    renderSimpleTable(
      agentList,
      ["Agent ID", "名称", "类型", "关注点", "领域", "Skill", "创建时间"],
      (agentResp.items || []).map((item) => [
        item.agent_id,
        item.name,
        item.category || "-",
        item.focus,
        item.domain_id || "-",
        (item.skill_ids || []).join(", "),
        formatDate(item.created_at),
      ])
    );

    renderSimpleTable(
      docList,
      ["文档ID", "领域", "标题", "来源类型", "创建时间"],
      (docResp.items || []).map((item) => [
        item.doc_id,
        item.domain_id,
        item.title,
        item.source_type,
        formatDate(item.created_at),
      ])
    );
  }

  populateDomainSelect(agentDomainSelect);
  populateDomainSelect(docDomainSelect);
  populateSkillCheckboxes();
  await refreshLists();

  createDomainBtn.addEventListener("click", async () => {
    try {
      const payload = {
        name: domainNameInput.value.trim(),
        description: domainDescInput.value.trim(),
        domain_id: domainIdInput.value.trim() || undefined,
      };
      await fetchJSON("/api/config/domains", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      domainNameInput.value = "";
      domainIdInput.value = "";
      domainDescInput.value = "";
      showMessage("自定义领域已创建");
      await refreshMeta();
      await refreshLists();
    } catch (error) {
      showMessage(`创建领域失败：${error.message}`);
    }
  });

  createSkillBtn.addEventListener("click", async () => {
    try {
      const payload = {
        name: skillNameInput.value.trim(),
        description: skillDescInput.value.trim(),
        skill_id: skillIdInput.value.trim() || undefined,
        category: skillCategoryInput.value.trim(),
        mode: skillModeSelect.value,
        input_fields: skillInputFields.value
          .split(",")
          .map((item) => item.trim())
          .filter((item) => item.length),
        output_fields: skillOutputFields.value
          .split(",")
          .map((item) => item.trim())
          .filter((item) => item.length),
        prompt_template: skillPromptTemplate.value.trim(),
        tags: skillTagsInput.value
          .split(",")
          .map((item) => item.trim())
          .filter((item) => item.length),
        example_output: skillExampleOutput.value.trim(),
      };
      await fetchJSON("/api/config/skills", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      skillNameInput.value = "";
      skillIdInput.value = "";
      skillDescInput.value = "";
      skillCategoryInput.value = "";
      skillModeSelect.value = "";
      skillInputFields.value = "";
      skillOutputFields.value = "";
      skillPromptTemplate.value = "";
      skillTagsInput.value = "";
      skillExampleOutput.value = "";
      showMessage("自定义Skill已创建");
      await refreshMeta();
      await refreshLists();
    } catch (error) {
      showMessage(`创建Skill失败：${error.message}`);
    }
  });

  createAgentBtn.addEventListener("click", async () => {
    try {
      const selectedSkills = Array.from(
        document.querySelectorAll("input[name='agentSkills']:checked")
      ).map((input) => input.value);
      const payload = {
        name: agentNameInput.value.trim(),
        focus: agentFocusInput.value.trim(),
        description: agentDescInput.value.trim(),
        default_query: agentQueryInput.value.trim(),
        domain_id: agentDomainSelect.value,
        agent_id: agentIdInput.value.trim() || undefined,
        category: agentCategorySelect.value || "",
        skill_ids: selectedSkills,
      };
      await fetchJSON("/api/config/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      agentNameInput.value = "";
      agentFocusInput.value = "";
      agentDescInput.value = "";
      agentQueryInput.value = "";
      agentIdInput.value = "";
      agentCategorySelect.value = "";
      Array.from(document.querySelectorAll("input[name='agentSkills']")).forEach((el) => {
        el.checked = false;
      });
      showMessage("自定义Agent已创建");
      await refreshMeta();
      await refreshLists();
    } catch (error) {
      showMessage(`创建Agent失败：${error.message}`);
    }
  });

  createDocBtn.addEventListener("click", async () => {
    try {
      const payload = {
        domain_id: docDomainSelect.value,
        title: docTitleInput.value.trim(),
        source: docSourceInput.value.trim(),
        source_type: docSourceTypeInput.value.trim() || "custom",
        content: docContentInput.value.trim(),
      };
      await fetchJSON("/api/config/documents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      docTitleInput.value = "";
      docSourceInput.value = "";
      docSourceTypeInput.value = "";
      docContentInput.value = "";
      showMessage("RAG文档已保存");
      await refreshLists();
    } catch (error) {
      showMessage(`保存文档失败：${error.message}`);
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initInsightPage();
  initReportPage();
  initHistoryPage();
  initConfigPage();
});
