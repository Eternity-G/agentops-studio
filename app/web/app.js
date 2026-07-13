const healthStatus = document.querySelector("#healthStatus");
const statusDot = document.querySelector(".status-dot");

const summaryOutput = document.querySelector("#summaryOutput");
const askOutput = document.querySelector("#askOutput");
const impactOutput = document.querySelector("#impactOutput");
const reviewOutput = document.querySelector("#reviewOutput");
const evalOutput = document.querySelector("#evalOutput");

function pretty(value) {
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function listText(items) {
  if (!items || items.length === 0) {
    return "-";
  }
  return items.join("、");
}

function languageText(languages) {
  const entries = Object.entries(languages || {});
  if (entries.length === 0) {
    return "-";
  }
  return entries.map(([name, count]) => `${name}: ${count}`).join("\n");
}

function formatSummary(summary) {
  return [
    "仓库概览报告",
    "",
    `仓库路径：${summary.repository_path}`,
    `总文件数：${summary.total_files}`,
    `可分析文件数：${summary.analyzed_files}`,
    `估算代码行数：${summary.total_lines}`,
    "",
    "主要语言：",
    languageText(summary.languages),
    "",
    `顶层目录：${listText(summary.top_level_directories)}`,
    `关键文件：${listText((summary.key_files || []).slice(0, 12))}`,
    `前端信号：${listText(summary.frontend_signals)}`,
    `后端信号：${listText(summary.backend_signals)}`,
    "",
    "解读：",
    summary.analyzed_files === 0
      ? "没有找到可分析文件。请确认你输入的是具体仓库目录，例如 external-repos/novu，而不是 external-repos 这种容器目录。"
      : "系统已经完成静态扫描。下一步可以在代码问答里提问，例如“后端入口在哪里？”或“某个功能在哪里实现？”。",
  ].join("\n");
}

function formatCodebaseAnswer(answer) {
  const evidence = (answer.evidence || [])
    .slice(0, 6)
    .map((item) => `- ${item.file_path}:${item.line_start}-${item.line_end}\n${item.quote}`)
    .join("\n\n");
  return [
    "代码问答结果",
    "",
    `问题：${answer.question}`,
    "",
    "回答：",
    answer.answer,
    "",
    `搜索词：${listText(answer.searched_terms)}`,
    "",
    "证据：",
    evidence || "-",
    "",
    `风险提示：${listText(answer.risk_notes)}`,
  ].join("\n");
}

function formatImpact(report) {
  const references = (report.referenced_by || [])
    .slice(0, 8)
    .map((item) => `- ${item.file_path}:${item.line_start}-${item.line_end}\n${item.quote}`)
    .join("\n\n");
  return [
    "影响分析报告",
    "",
    `目标文件：${report.target_path}`,
    `可能影响区域：${listText(report.likely_impacted_areas)}`,
    `测试建议：${listText(report.test_suggestions)}`,
    "",
    "引用证据：",
    references || "-",
  ].join("\n");
}

function formatReview(report) {
  const evidence = (report.evidence || [])
    .slice(0, 6)
    .map((item) => `- ${item.file_path}:${item.line_start}-${item.line_end}\n${item.quote}`)
    .join("\n\n");
  return [
    "Diff Review 报告",
    "",
    report.summary,
    "",
    `变更文件：${listText(report.changed_files)}`,
    `风险点：${listText(report.risk_notes)}`,
    `测试建议：${listText(report.test_suggestions)}`,
    "",
    "证据：",
    evidence || "-",
  ].join("\n");
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw new Error(pretty(body));
  }
  return body;
}

async function withButton(button, target, action) {
  button.disabled = true;
  target.textContent = "运行中...";
  try {
    target.textContent = pretty(await action());
  } catch (error) {
    target.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function checkHealth() {
  try {
    const body = await requestJson("/health");
    healthStatus.textContent = `${body.app_name} · ${body.status}`;
    statusDot.classList.add("ok");
  } catch (error) {
    healthStatus.textContent = "服务不可用";
    statusDot.classList.remove("ok");
  }
}

document.querySelector("#loadSummaryButton").addEventListener("click", (event) => {
  withButton(event.currentTarget, summaryOutput, () =>
    requestJson("/codebase/summary", {
      method: "POST",
      body: JSON.stringify({
        repository_path: document.querySelector("#summaryRepo").value,
      }),
    }).then(formatSummary),
  );
});

document.querySelector("#askCodebaseButton").addEventListener("click", (event) => {
  withButton(event.currentTarget, askOutput, () =>
    requestJson("/codebase/ask", {
      method: "POST",
      body: JSON.stringify({
        repository_path: document.querySelector("#askRepo").value,
        question: document.querySelector("#codeQuestion").value,
      }),
    }).then(formatCodebaseAnswer),
  );
});

document.querySelector("#impactButton").addEventListener("click", (event) => {
  withButton(event.currentTarget, impactOutput, () =>
    requestJson("/codebase/impact", {
      method: "POST",
      body: JSON.stringify({
        repository_path: document.querySelector("#impactRepo").value,
        target_path: document.querySelector("#impactPath").value,
      }),
    }).then(formatImpact),
  );
});

document.querySelector("#reviewButton").addEventListener("click", (event) => {
  withButton(event.currentTarget, reviewOutput, () =>
    requestJson("/codebase/review-diff", {
      method: "POST",
      body: JSON.stringify({
        repository_path: document.querySelector("#reviewRepo").value,
      }),
    }).then(formatReview),
  );
});

document.querySelector("#loadEvalButton").addEventListener("click", (event) => {
  withButton(event.currentTarget, evalOutput, () => requestJson("/evals/latest-report"));
});

checkHealth();
