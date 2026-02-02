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

function renderDynamicSlides(container, sections, objective) {
  if (!container) {
    return;
  }
  container.innerHTML = "";
  if (!sections || !sections.length) {
    return;
  }
  const buildSlide = (title, bullets, extra, instruction) => {
    const slide = document.createElement("div");
    slide.className = "slide";
    const header = document.createElement("div");
    header.className = "slide-header";
    const heading = document.createElement("h3");
    heading.textContent = title;
    header.appendChild(heading);
    slide.appendChild(header);
    const content = document.createElement("div");
    content.className = "slide-content";
    if (instruction) {
      const note = document.createElement("div");
      note.className = "meta";
      note.textContent = instruction;
      content.appendChild(note);
    }
    const list = document.createElement("ul");
    list.className = "bullet-list";
    (bullets || []).forEach((bullet) => {
      const item = document.createElement("li");
      item.textContent = bullet;
      list.appendChild(item);
    });
    content.appendChild(list);
    if (extra) {
      const extraBlock = document.createElement("div");
      extraBlock.className = "output";
      extraBlock.textContent = extra;
      content.appendChild(extraBlock);
    }
    slide.appendChild(content);
    return slide;
  };

  sections.forEach((section, index) => {
    const title = section.title || `PPT页面 ${index + 1}`;
    const bullets = section.bullets || [];
    const viewpoint = section.viewpoint ? `启示观点：${section.viewpoint}` : "";
    container.appendChild(buildSlide(title, bullets, viewpoint, section.instruction));
  });
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
        <div>
          <a href="/ui/report/${item.task_id}" target="_blank">打开报告</a>
          <button class="button action danger" data-action="delete" data-id="${item.task_id}">删除</button>
        </div>
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

function renderConfigTable(container, headers, rows) {
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
  const reportTemplateSelect = document.getElementById("reportTemplateSelect");

  const resultMeta = document.getElementById("resultMeta");
  const resultSummary = document.getElementById("resultSummary");
  const resultCapabilities = document.getElementById("resultCapabilities");
  const resultEvidence = document.getElementById("resultEvidence");
  const insightFlow = document.getElementById("insightFlow");
  const artifactDescriptions = document.getElementById("artifactDescriptions");

  let meta = await fetchJSON("/api/meta");
  let domains = meta.domains || [];
  let agents = meta.agents || [];
  let skills = meta.skills || [];
  let templates = meta.report_templates || [];

  domains.forEach((domain) => {
    const option = document.createElement("option");
    option.value = domain.domain_id;
    option.textContent = domain.origin === "custom" ? `${domain.name}（自定义）` : domain.name;
    domainSelect.appendChild(option);
  });

  if (reportTemplateSelect) {
    templates.forEach((tpl) => {
      const option = document.createElement("option");
      option.value = tpl.template_id;
      option.textContent = tpl.name;
      reportTemplateSelect.appendChild(option);
    });
  }

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

  function renderFlow(flowItems) {
    if (!insightFlow) {
      return;
    }
    insightFlow.innerHTML = "";
    const items =
      flowItems ||
      [
        {
          step: "任务定义",
          description: "明确洞察目标与范围",
          outputs: ["洞察配置"],
        },
        {
          step: "RAG检索",
          description: "召回多源证据",
          outputs: ["证据候选"],
        },
        {
          step: "Agent洞察",
          description: "分角色分析",
          outputs: ["Agent洞察"],
        },
        {
          step: "Skill处理",
          description: "趋势/对比/验证",
          outputs: ["能力产物"],
        },
        {
          step: "汇总与报告",
          description: "产出总结与PPT",
          outputs: ["洞察报告"],
        },
      ];
    items.forEach((item) => {
      const card = document.createElement("div");
      card.className = "flow-card";
      const title = document.createElement("h4");
      title.textContent = item.step;
      const desc = document.createElement("p");
      desc.textContent = item.description || "";
      const output = document.createElement("p");
      output.className = "meta";
      output.textContent = `输出：${(item.outputs || []).join(" / ")}`;
      card.appendChild(title);
      card.appendChild(desc);
      card.appendChild(output);
      insightFlow.appendChild(card);
    });
  }

  function renderArtifactDescriptions(descriptions) {
    if (!artifactDescriptions) {
      return;
    }
    const lines = [];
    const items =
      descriptions || {
        insight_summary: "洞察总结：关键结论与趋势。",
        capability_report: "能力识别与验证报告：安全能力与验证方法。",
        evidence_chain: "证据链：结论对应的文档证据。",
        agent_results: "Agent洞察：分主题分析输出。",
      };
    Object.keys(items).forEach((key) => {
      lines.push(`${key}: ${items[key]}`);
    });
    artifactDescriptions.textContent = lines.join("\n");
  }

  renderFlow();
  renderArtifactDescriptions();

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
        report_template_id: reportTemplateSelect ? reportTemplateSelect.value : undefined,
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
      renderFlow(response.insight_flow);
      renderArtifactDescriptions(response.artifact_descriptions);
    } catch (error) {
      resultSummary.textContent = `发生错误：${error.message}`;
    } finally {
      runButton.disabled = false;
      runButton.textContent = "运行洞察";
    }
  });
}

async function initQuickInsightPage() {
  const quickPrompt = document.getElementById("quickPromptText");
  if (!quickPrompt) {
    return;
  }
  const quickRunBtn = document.getElementById("quickRunBtn");
  const quickResultMeta = document.getElementById("quickResultMeta");
  const quickResultSummary = document.getElementById("quickResultSummary");

  quickRunBtn.addEventListener("click", async () => {
    quickRunBtn.disabled = true;
    quickRunBtn.textContent = "生成中...";
    quickResultMeta.textContent = "";
    quickResultSummary.textContent = "";
    try {
      const payload = {
        prompt: quickPrompt.value.trim(),
      };
      const response = await fetchJSON("/api/quick-insights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      quickResultMeta.innerHTML = `报告ID：${response.report_id} | <a href="/ui/quick-report/${response.report_id}" target="_blank">打开报告</a>`;
      quickResultSummary.textContent = response.summary || "已生成报告。";
    } catch (error) {
      quickResultSummary.textContent = `生成失败：${error.message}`;
    } finally {
      quickRunBtn.disabled = false;
      quickRunBtn.textContent = "生成洞察报告";
    }
  });
}

async function initQuickReportsPage() {
  const table = document.getElementById("quickReportTable");
  if (!table) {
    return;
  }
  const renderTable = (items) => {
    if (!items || !items.length) {
      table.textContent = "暂无报告。";
      return;
    }
    const header = `
      <div class="table-row table-header">
        <div>时间</div>
        <div>标题</div>
        <div>摘要</div>
        <div>操作</div>
      </div>
    `;
    const rows = items
      .map(
        (item) => `
        <div class="table-row">
          <div>${formatDate(item.created_at)}</div>
          <div>${item.title || "-"}</div>
          <div>${item.summary_line || ""}</div>
          <div>
            <a href="/ui/quick-report/${item.report_id}" target="_blank">查看</a>
            <button class="button action danger" data-action="delete" data-id="${item.report_id}">删除</button>
          </div>
        </div>
      `
      )
      .join("");
    table.innerHTML = header + rows;
  };

  const refresh = async () => {
    const response = await fetchJSON("/api/quick-insights?limit=50");
    renderTable(response.items || []);
  };

  table.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action='delete']");
    if (!button) {
      return;
    }
    if (!confirm("确认删除该报告？")) {
      return;
    }
    const reportId = button.dataset.id;
    await fetchJSON(`/api/quick-insights/${reportId}`, { method: "DELETE" });
    await refresh();
  });

  await refresh();
}

async function initQuickReportPage() {
  if (!window.__QUICK_REPORT_ID__) {
    return;
  }
  const quickFrame = document.getElementById("quickHtmlFrame");
  const quickEditToggle = document.getElementById("quickEditToggle");
  const quickEditPanel = document.getElementById("quickEditPanel");
  const quickEditPrompt = document.getElementById("quickEditPrompt");
  const quickEditHtml = document.getElementById("quickEditHtml");
  const quickEditSave = document.getElementById("quickEditSave");
  let currentReport = null;
  try {
    const response = await fetchJSON(`/api/quick-insights/${window.__QUICK_REPORT_ID__}`);
    currentReport = response;
    if (quickFrame) {
      quickFrame.srcdoc = response.html_content || "";
    }
    if (quickEditHtml) {
      if (quickEditPrompt) {
        quickEditPrompt.value = response.prompt || "";
      }
      quickEditHtml.value = response.html_content || "";
    }
  } catch (error) {
    if (quickFrame) {
      quickFrame.srcdoc = `加载失败：${error.message}`;
    }
  }

  if (quickEditToggle && quickEditPanel) {
    quickEditToggle.addEventListener("click", () => {
      const isHidden = quickEditPanel.style.display === "none";
      quickEditPanel.style.display = isHidden ? "block" : "none";
    });
  }

  if (quickEditSave) {
    quickEditSave.addEventListener("click", async () => {
      try {
        const payload = {
          html_content: quickEditHtml.value.trim(),
        };
        const response = await fetchJSON(`/api/quick-insights/${window.__QUICK_REPORT_ID__}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        currentReport = response;
        if (quickFrame) {
          quickFrame.srcdoc = response.html_content || "";
        }
        quickEditHtml.value = response.html_content || "";
      } catch (error) {
        alert(`保存失败：${error.message}`);
      }
    });
  }
}

async function initReportPage() {
  if (!window.__REPORT_TASK_ID__) {
    return;
  }
  const dynamicSlides = document.getElementById("dynamicSlides");
  const defaultSlides = document.getElementById("defaultSlides");
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
    if (response.report_sections && response.report_sections.length) {
      renderDynamicSlides(dynamicSlides, response.report_sections, response.objective);
      if (defaultSlides) {
        defaultSlides.style.display = "none";
      }
    }
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
    historyTable.addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-action='delete']");
      if (!button) {
        return;
      }
      if (!confirm("确认删除该历史记录？")) {
        return;
      }
      const taskId = button.dataset.id;
      try {
        await fetchJSON(`/api/tasks/${taskId}`, { method: "DELETE" });
        const refresh = await fetchJSON("/api/tasks?limit=50");
        renderHistoryTable(historyTable, refresh.items || []);
      } catch (error) {
        historyTable.textContent = `删除失败：${error.message}`;
      }
    });
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
  const domainDefaultAgents = document.getElementById("domainDefaultAgents");
  const domainDefaultSkills = document.getElementById("domainDefaultSkills");
  const createDomainBtn = document.getElementById("createDomainBtn");
  const cancelDomainBtn = document.getElementById("cancelDomainBtn");
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
  const cancelSkillBtn = document.getElementById("cancelSkillBtn");
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
  const cancelAgentBtn = document.getElementById("cancelAgentBtn");
  const agentList = document.getElementById("agentList");

  const templateNameInput = document.getElementById("templateNameInput");
  const templateIdInput = document.getElementById("templateIdInput");
  const templateDescInput = document.getElementById("templateDescInput");
  const templateSectionsInput = document.getElementById("templateSectionsInput");
  const createTemplateBtn = document.getElementById("createTemplateBtn");
  const cancelTemplateBtn = document.getElementById("cancelTemplateBtn");
  const templateList = document.getElementById("templateList");

  const crawlerNameInput = document.getElementById("crawlerNameInput");
  const crawlerDomainSelect = document.getElementById("crawlerDomainSelect");
  const crawlerUrlInput = document.getElementById("crawlerUrlInput");
  const crawlerSourceTypeInput = document.getElementById("crawlerSourceTypeInput");
  const crawlerIntervalInput = document.getElementById("crawlerIntervalInput");
  const crawlerEnabledInput = document.getElementById("crawlerEnabledInput");
  const crawlerDescInput = document.getElementById("crawlerDescInput");
  const createCrawlerBtn = document.getElementById("createCrawlerBtn");
  const cancelCrawlerBtn = document.getElementById("cancelCrawlerBtn");
  const runAllCrawlerBtn = document.getElementById("runAllCrawlerBtn");
  const crawlerList = document.getElementById("crawlerList");

  const docDomainSelect = document.getElementById("docDomainSelect");
  const docSourceTypeInput = document.getElementById("docSourceTypeInput");
  const docTitleInput = document.getElementById("docTitleInput");
  const docSourceInput = document.getElementById("docSourceInput");
  const docContentInput = document.getElementById("docContentInput");
  const createDocBtn = document.getElementById("createDocBtn");
  const cancelDocBtn = document.getElementById("cancelDocBtn");
  const docList = document.getElementById("docList");
  const uploadDomainSelect = document.getElementById("uploadDomainSelect");
  const uploadSourceTypeInput = document.getElementById("uploadSourceTypeInput");
  const uploadSourceInput = document.getElementById("uploadSourceInput");
  const uploadTitleInput = document.getElementById("uploadTitleInput");
  const uploadFileInput = document.getElementById("uploadFileInput");
  const uploadDocBtn = document.getElementById("uploadDocBtn");

  let editingDomainId = null;
  let editingSkillId = null;
  let editingAgentId = null;
  let editingDocId = null;
  let editingTemplateId = null;
  let editingCrawlerId = null;
  const configState = { domains: [], skills: [], agents: [], documents: [], templates: [], crawlers: [] };

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
    populateDomainSelect(crawlerDomainSelect);
    populateDomainSelect(uploadDomainSelect);
    populateSkillCheckboxes();
  }

  function showMessage(text) {
    message.textContent = text;
    setTimeout(() => {
      message.textContent = "";
    }, 3000);
  }

  function resetDomainForm() {
    editingDomainId = null;
    domainNameInput.value = "";
    domainIdInput.value = "";
    domainIdInput.disabled = false;
    domainDescInput.value = "";
    domainDefaultAgents.value = "";
    domainDefaultSkills.value = "";
    createDomainBtn.textContent = "创建领域";
  }

  function startEditDomain(item) {
    editingDomainId = item.domain_id;
    domainNameInput.value = item.name || "";
    domainIdInput.value = item.domain_id;
    domainIdInput.disabled = true;
    domainDescInput.value = item.description || "";
    domainDefaultAgents.value = (item.default_agents || []).join(", ");
    domainDefaultSkills.value = (item.default_skills || []).join(", ");
    createDomainBtn.textContent = "保存修改";
  }

  function resetSkillForm() {
    editingSkillId = null;
    skillNameInput.value = "";
    skillIdInput.value = "";
    skillIdInput.disabled = false;
    skillDescInput.value = "";
    skillCategoryInput.value = "";
    skillModeSelect.value = "";
    skillInputFields.value = "";
    skillOutputFields.value = "";
    skillPromptTemplate.value = "";
    skillTagsInput.value = "";
    skillExampleOutput.value = "";
    createSkillBtn.textContent = "创建Skill";
  }

  function startEditSkill(item) {
    editingSkillId = item.skill_id;
    skillNameInput.value = item.name || "";
    skillIdInput.value = item.skill_id;
    skillIdInput.disabled = true;
    skillDescInput.value = item.description || "";
    skillCategoryInput.value = item.category || "";
    skillModeSelect.value = item.mode || "";
    skillInputFields.value = (item.input_fields || []).join(", ");
    skillOutputFields.value = (item.output_fields || []).join(", ");
    skillPromptTemplate.value = item.prompt_template || "";
    skillTagsInput.value = (item.tags || []).join(", ");
    skillExampleOutput.value = item.example_output || "";
    createSkillBtn.textContent = "保存修改";
  }

  function resetAgentForm() {
    editingAgentId = null;
    agentNameInput.value = "";
    agentFocusInput.value = "";
    agentDescInput.value = "";
    agentQueryInput.value = "";
    agentIdInput.value = "";
    agentIdInput.disabled = false;
    agentCategorySelect.value = "";
    Array.from(document.querySelectorAll("input[name='agentSkills']")).forEach((el) => {
      el.checked = false;
    });
    createAgentBtn.textContent = "创建Agent";
  }

  function startEditAgent(item) {
    editingAgentId = item.agent_id;
    agentNameInput.value = item.name || "";
    agentFocusInput.value = item.focus || "";
    agentDescInput.value = item.description || "";
    agentQueryInput.value = item.default_query || "";
    agentDomainSelect.value = item.domain_id || agentDomainSelect.value;
    agentIdInput.value = item.agent_id;
    agentIdInput.disabled = true;
    agentCategorySelect.value = item.category || "";
    Array.from(document.querySelectorAll("input[name='agentSkills']")).forEach((el) => {
      el.checked = (item.skill_ids || []).includes(el.value);
    });
    createAgentBtn.textContent = "保存修改";
  }

  function resetDocForm() {
    editingDocId = null;
    docTitleInput.value = "";
    docSourceInput.value = "";
    docSourceTypeInput.value = "";
    docContentInput.value = "";
    createDocBtn.textContent = "保存RAG文档";
  }

  function startEditDoc(item) {
    editingDocId = item.doc_id;
    docDomainSelect.value = item.domain_id || docDomainSelect.value;
    docTitleInput.value = item.title || "";
    docSourceInput.value = item.source || "";
    docSourceTypeInput.value = item.source_type || "";
    docContentInput.value = item.content || "";
    createDocBtn.textContent = "保存修改";
  }

  function resetTemplateForm() {
    editingTemplateId = null;
    templateNameInput.value = "";
    templateIdInput.value = "";
    templateIdInput.disabled = false;
    templateDescInput.value = "";
    templateSectionsInput.value = "";
    createTemplateBtn.textContent = "保存模板";
  }

  function startEditTemplate(item) {
    editingTemplateId = item.template_id;
    templateNameInput.value = item.name || "";
    templateIdInput.value = item.template_id;
    templateIdInput.disabled = true;
    templateDescInput.value = item.description || "";
    templateSectionsInput.value = JSON.stringify(item.sections || [], null, 2);
    createTemplateBtn.textContent = "保存修改";
  }

  function resetCrawlerForm() {
    editingCrawlerId = null;
    crawlerNameInput.value = "";
    crawlerUrlInput.value = "";
    crawlerSourceTypeInput.value = "";
    crawlerIntervalInput.value = "1440";
    crawlerEnabledInput.checked = true;
    crawlerDescInput.value = "";
    createCrawlerBtn.textContent = "保存来源";
  }

  function startEditCrawler(item) {
    editingCrawlerId = item.source_id;
    crawlerNameInput.value = item.name || "";
    crawlerDomainSelect.value = item.domain_id || crawlerDomainSelect.value;
    crawlerUrlInput.value = item.url || "";
    crawlerSourceTypeInput.value = item.source_type || "";
    crawlerIntervalInput.value = String(item.interval_minutes || 1440);
    crawlerEnabledInput.checked = Boolean(item.enabled);
    crawlerDescInput.value = item.description || "";
    createCrawlerBtn.textContent = "保存修改";
  }

  async function refreshLists() {
    const [domainResp, skillResp, agentResp, docResp, templateResp, crawlerResp] = await Promise.all([
      fetchJSON("/api/config/domains/all"),
      fetchJSON("/api/config/skills/all"),
      fetchJSON("/api/config/agents/all"),
      fetchJSON("/api/config/documents/all"),
      fetchJSON("/api/config/report-templates/all"),
      fetchJSON("/api/config/crawlers"),
    ]);

    configState.domains = domainResp.items || [];
    configState.skills = skillResp.items || [];
    configState.agents = agentResp.items || [];
    configState.documents = docResp.items || [];
    configState.templates = templateResp.items || [];
    configState.crawlers = crawlerResp.items || [];

    const renderActions = (type, id, disabled) => {
      const edit = `<button class="button action" data-action="edit" data-type="${type}" data-id="${id}">编辑</button>`;
      const remove = `<button class="button action danger" data-action="delete" data-type="${type}" data-id="${id}">删除</button>`;
      const enable = `<button class="button action" data-action="enable" data-type="${type}" data-id="${id}">启用</button>`;
      return disabled ? `${edit} ${enable}` : `${edit} ${remove}`;
    };

    renderConfigTable(
      domainList,
      ["领域ID", "名称", "描述", "默认Agent", "默认Skill", "来源", "状态", "操作"],
      configState.domains.map((item) => [
        item.domain_id,
        item.name,
        item.description || "",
        (item.default_agents || []).join(", "),
        (item.default_skills || []).join(", "),
        item.origin === "builtin" ? "内置" : "自定义",
        item.disabled ? "已禁用" : "启用中",
        renderActions("domain", item.domain_id, item.disabled),
      ])
    );

    renderConfigTable(
      skillList,
      ["Skill ID", "名称", "类别", "模式", "标签", "来源", "状态", "操作"],
      configState.skills.map((item) => [
        item.skill_id,
        item.name,
        item.category || "-",
        item.mode || "-",
        (item.tags || []).join(", "),
        item.origin === "builtin" ? "内置" : "自定义",
        item.disabled ? "已禁用" : "启用中",
        renderActions("skill", item.skill_id, item.disabled),
      ])
    );

    renderConfigTable(
      agentList,
      ["Agent ID", "名称", "类型", "领域", "Skill", "来源", "状态", "操作"],
      configState.agents.map((item) => [
        item.agent_id,
        item.name,
        item.category || "-",
        item.domain_id || "-",
        (item.skill_ids || []).join(", "),
        item.origin === "builtin" ? "内置" : "自定义",
        item.disabled ? "已禁用" : "启用中",
        renderActions("agent", item.agent_id, item.disabled),
      ])
    );

    renderConfigTable(
      docList,
      ["文档ID", "领域", "标题", "来源类型", "来源", "来源渠道", "状态", "操作"],
      configState.documents.map((item) => [
        item.doc_id,
        item.domain_id,
        item.title,
        item.source_type,
        item.source || "-",
        item.origin === "builtin" ? "内置" : "自定义",
        item.disabled ? "已禁用" : "启用中",
        renderActions("document", item.doc_id, item.disabled),
      ])
    );

    renderConfigTable(
      templateList,
      ["模板ID", "名称", "描述", "来源", "状态", "操作"],
      configState.templates.map((item) => [
        item.template_id,
        item.name,
        item.description || "",
        item.origin === "builtin" ? "内置" : "自定义",
        item.disabled ? "已禁用" : "启用中",
        renderActions("report-template", item.template_id, item.disabled),
      ])
    );

    renderConfigTable(
      crawlerList,
      ["来源ID", "名称", "领域", "频率(分钟)", "启用", "最近状态", "操作"],
      configState.crawlers.map((item) => [
        item.source_id,
        item.name,
        item.domain_id,
        item.interval_minutes,
        item.enabled ? "是" : "否",
        item.status || "-",
        `<button class="button action" data-action="edit" data-type="crawler" data-id="${item.source_id}">编辑</button>
         <button class="button action" data-action="run" data-type="crawler" data-id="${item.source_id}">立即抓取</button>
         <button class="button action danger" data-action="delete" data-type="crawler" data-id="${item.source_id}">删除</button>`,
      ])
    );
  }

  populateDomainSelect(agentDomainSelect);
  populateDomainSelect(docDomainSelect);
  populateDomainSelect(crawlerDomainSelect);
  populateDomainSelect(uploadDomainSelect);
  populateSkillCheckboxes();
  await refreshLists();

  async function handleAction(type, action, id) {
    try {
      if (action === "edit") {
        if (type === "domain") {
          const item = configState.domains.find((d) => d.domain_id === id);
          if (item) startEditDomain(item);
        }
        if (type === "skill") {
          const item = configState.skills.find((s) => s.skill_id === id);
          if (item) startEditSkill(item);
        }
        if (type === "agent") {
          const item = configState.agents.find((a) => a.agent_id === id);
          if (item) startEditAgent(item);
        }
        if (type === "document") {
          const item = configState.documents.find((d) => d.doc_id === id);
          if (item) startEditDoc(item);
        }
        if (type === "report-template") {
          const item = configState.templates.find((t) => t.template_id === id);
          if (item) startEditTemplate(item);
        }
        if (type === "crawler") {
          const item = configState.crawlers.find((c) => c.source_id === id);
          if (item) startEditCrawler(item);
        }
        return;
      }
      if (action === "run" && type === "crawler") {
        await fetchJSON(`/api/config/crawlers/${id}/run`, { method: "POST" });
        await refreshLists();
        showMessage("已触发抓取");
        return;
      }
      if (action === "delete") {
        if (!confirm("确认删除/禁用该条目？")) {
          return;
        }
        await fetchJSON(`/api/config/${type}s/${id}`, { method: "DELETE" });
        await refreshMeta();
        await refreshLists();
        showMessage("已删除/禁用");
        return;
      }
      if (action === "enable") {
        await fetchJSON(`/api/config/${type}s/${id}/enable`, { method: "POST" });
        await refreshMeta();
        await refreshLists();
        showMessage("已启用");
      }
    } catch (error) {
      showMessage(`操作失败：${error.message}`);
    }
  }

  function bindActionHandlers(container, type) {
    container.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-action]");
      if (!button) {
        return;
      }
      const action = button.dataset.action;
      const id = button.dataset.id;
      handleAction(type, action, id);
    });
  }

  bindActionHandlers(domainList, "domain");
  bindActionHandlers(skillList, "skill");
  bindActionHandlers(agentList, "agent");
  bindActionHandlers(docList, "document");
  bindActionHandlers(templateList, "report-template");
  bindActionHandlers(crawlerList, "crawler");

  createDomainBtn.addEventListener("click", async () => {
    try {
      const payload = {
        name: domainNameInput.value.trim(),
        description: domainDescInput.value.trim(),
        domain_id: domainIdInput.value.trim() || undefined,
        default_agents: domainDefaultAgents.value
          .split(",")
          .map((item) => item.trim())
          .filter((item) => item.length),
        default_skills: domainDefaultSkills.value
          .split(",")
          .map((item) => item.trim())
          .filter((item) => item.length),
      };
      if (editingDomainId) {
        await fetchJSON(`/api/config/domains/${editingDomainId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showMessage("领域已更新");
        resetDomainForm();
      } else {
        await fetchJSON("/api/config/domains", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showMessage("自定义领域已创建");
        resetDomainForm();
      }
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
      if (editingSkillId) {
        await fetchJSON(`/api/config/skills/${editingSkillId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showMessage("Skill已更新");
        resetSkillForm();
      } else {
        await fetchJSON("/api/config/skills", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showMessage("自定义Skill已创建");
        resetSkillForm();
      }
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
      if (editingAgentId) {
        await fetchJSON(`/api/config/agents/${editingAgentId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showMessage("Agent已更新");
        resetAgentForm();
      } else {
        await fetchJSON("/api/config/agents", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showMessage("自定义Agent已创建");
        resetAgentForm();
      }
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
      if (editingDocId) {
        await fetchJSON(`/api/config/documents/${editingDocId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showMessage("RAG文档已更新");
        resetDocForm();
      } else {
        await fetchJSON("/api/config/documents", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showMessage("RAG文档已保存");
        resetDocForm();
      }
      await refreshLists();
    } catch (error) {
      showMessage(`保存文档失败：${error.message}`);
    }
  });

  if (uploadDocBtn) {
    uploadDocBtn.addEventListener("click", async () => {
      try {
        if (!uploadFileInput.files || !uploadFileInput.files.length) {
          showMessage("请选择文件");
          return;
        }
        const formData = new FormData();
        formData.append("domain_id", uploadDomainSelect.value);
        formData.append("source_type", uploadSourceTypeInput.value.trim() || "upload");
        formData.append("source", uploadSourceInput.value.trim());
        formData.append("title", uploadTitleInput.value.trim());
        formData.append("file", uploadFileInput.files[0]);
        const response = await fetch("/api/config/documents/upload", {
          method: "POST",
          body: formData,
        });
        if (!response.ok) {
          const text = await response.text();
          throw new Error(text || "上传失败");
        }
        showMessage("文件已上传并向量化");
        uploadSourceTypeInput.value = "";
        uploadSourceInput.value = "";
        uploadTitleInput.value = "";
        uploadFileInput.value = "";
        await refreshLists();
      } catch (error) {
        showMessage(`上传失败：${error.message}`);
      }
    });
  }

  createTemplateBtn.addEventListener("click", async () => {
    try {
      const sections = templateSectionsInput.value.trim()
        ? JSON.parse(templateSectionsInput.value.trim())
        : [];
      const payload = {
        name: templateNameInput.value.trim(),
        description: templateDescInput.value.trim(),
        template_id: templateIdInput.value.trim() || undefined,
        sections,
      };
      if (editingTemplateId) {
        await fetchJSON(`/api/config/report-templates/${editingTemplateId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showMessage("模板已更新");
        resetTemplateForm();
      } else {
        await fetchJSON("/api/config/report-templates", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showMessage("模板已创建");
        resetTemplateForm();
      }
      await refreshMeta();
      await refreshLists();
    } catch (error) {
      showMessage(`保存模板失败：${error.message}`);
    }
  });

  createCrawlerBtn.addEventListener("click", async () => {
    try {
      const payload = {
        name: crawlerNameInput.value.trim(),
        domain_id: crawlerDomainSelect.value,
        url: crawlerUrlInput.value.trim(),
        source_type: crawlerSourceTypeInput.value.trim() || "crawler",
        interval_minutes: Number(crawlerIntervalInput.value) || 1440,
        enabled: Boolean(crawlerEnabledInput.checked),
        description: crawlerDescInput.value.trim(),
      };
      if (editingCrawlerId) {
        await fetchJSON(`/api/config/crawlers/${editingCrawlerId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showMessage("来源已更新");
        resetCrawlerForm();
      } else {
        await fetchJSON("/api/config/crawlers", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showMessage("来源已创建");
        resetCrawlerForm();
      }
      await refreshLists();
    } catch (error) {
      showMessage(`保存来源失败：${error.message}`);
    }
  });

  runAllCrawlerBtn.addEventListener("click", async () => {
    try {
      await fetchJSON("/api/config/crawlers/run_all", { method: "POST" });
      showMessage("已触发全部抓取");
      await refreshLists();
    } catch (error) {
      showMessage(`触发失败：${error.message}`);
    }
  });

  cancelDomainBtn.addEventListener("click", () => resetDomainForm());
  cancelSkillBtn.addEventListener("click", () => resetSkillForm());
  cancelAgentBtn.addEventListener("click", () => resetAgentForm());
  cancelDocBtn.addEventListener("click", () => resetDocForm());
  cancelTemplateBtn.addEventListener("click", () => resetTemplateForm());
  cancelCrawlerBtn.addEventListener("click", () => resetCrawlerForm());

  const tabButtons = document.querySelectorAll(".tab-button");
  const tabContents = document.querySelectorAll(".tab-content");
  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.tab;
      tabButtons.forEach((btn) => btn.classList.remove("active"));
      button.classList.add("active");
      tabContents.forEach((content) => {
        content.classList.toggle("active", content.id === target);
      });
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initInsightPage();
  initReportPage();
  initHistoryPage();
  initConfigPage();
  initQuickInsightPage();
  initQuickReportsPage();
  initQuickReportPage();
});
