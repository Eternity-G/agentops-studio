const healthStatus = document.querySelector("#healthStatus");
const statusDot = document.querySelector(".status-dot");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function inlineMarkdown(value) {
  return escapeHtml(value)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function parseTableRow(line) {
  let content = line.trim();
  if (content.startsWith("|")) {
    content = content.slice(1);
  }
  if (content.endsWith("|")) {
    content = content.slice(0, -1);
  }

  const cells = [];
  let cell = "";
  let escaped = false;
  let inCode = false;

  for (const character of content) {
    if (escaped) {
      cell += character;
      escaped = false;
      continue;
    }
    if (character === "\\") {
      escaped = true;
      continue;
    }
    if (character === "`") {
      inCode = !inCode;
      cell += character;
      continue;
    }
    if (character === "|" && !inCode) {
      cells.push(cell.trim());
      cell = "";
      continue;
    }
    cell += character;
  }
  if (escaped) {
    cell += "\\";
  }
  cells.push(cell.trim());
  return cells;
}

function tableAlignments(separatorLine) {
  const separatorCells = parseTableRow(separatorLine);
  if (
    separatorCells.length === 0 ||
    !separatorCells.every((cell) => /^:?-{3,}:?$/.test(cell.replaceAll(" ", "")))
  ) {
    return null;
  }
  return separatorCells.map((cell) => {
    const normalized = cell.replaceAll(" ", "");
    if (normalized.startsWith(":") && normalized.endsWith(":")) {
      return "center";
    }
    if (normalized.endsWith(":")) {
      return "right";
    }
    return "left";
  });
}

function renderTableCell(tag, value, alignment) {
  return `<${tag} style="text-align: ${alignment}">${inlineMarkdown(value)}</${tag}>`;
}

function markdownToHtml(markdown) {
  const lines = String(markdown || "").split(/\r?\n/);
  const html = [];
  let inList = false;
  let inCode = false;
  let paragraph = [];

  function flushParagraph() {
    if (paragraph.length > 0) {
      html.push(`<p>${paragraph.map(inlineMarkdown).join(" ")}</p>`);
      paragraph = [];
    }
  }

  function closeList() {
    if (inList) {
      html.push("</ul>");
      inList = false;
    }
  }

  for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
    const line = lines[lineIndex];
    const trimmed = line.trimEnd();
    if (trimmed.startsWith("```")) {
      flushParagraph();
      closeList();
      if (inCode) {
        html.push("</code></pre>");
        inCode = false;
      } else {
        html.push("<pre><code>");
        inCode = true;
      }
      continue;
    }

    if (inCode) {
      html.push(`${escapeHtml(line)}\n`);
      continue;
    }

    if (!trimmed.trim()) {
      flushParagraph();
      closeList();
      continue;
    }

    const nextLine = lines[lineIndex + 1];
    const alignments = nextLine === undefined ? null : tableAlignments(nextLine);
    const headerCells = trimmed.includes("|") ? parseTableRow(trimmed) : [];
    if (alignments && headerCells.length === alignments.length) {
      flushParagraph();
      closeList();
      html.push('<div class="table-scroll"><table>');
      html.push(
        `<thead><tr>${headerCells
          .map((cell, index) => renderTableCell("th", cell, alignments[index]))
          .join("")}</tr></thead>`,
      );

      const bodyRows = [];
      lineIndex += 2;
      while (lineIndex < lines.length) {
        const rowLine = lines[lineIndex];
        if (!rowLine.trim() || !rowLine.includes("|")) {
          lineIndex -= 1;
          break;
        }
        const rowCells = parseTableRow(rowLine);
        while (rowCells.length < alignments.length) {
          rowCells.push("");
        }
        bodyRows.push(
          `<tr>${rowCells
            .slice(0, alignments.length)
            .map((cell, index) => renderTableCell("td", cell, alignments[index]))
            .join("")}</tr>`,
        );
        lineIndex += 1;
      }
      if (lineIndex >= lines.length) {
        lineIndex = lines.length;
      }
      html.push(`<tbody>${bodyRows.join("")}</tbody></table></div>`);
      continue;
    }

    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      closeList();
      const level = heading[1].length;
      html.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }

    const bullet = trimmed.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${inlineMarkdown(bullet[1])}</li>`);
      continue;
    }

    paragraph.push(trimmed);
  }

  flushParagraph();
  closeList();
  if (inCode) {
    html.push("</code></pre>");
  }
  return html.join("\n");
}

function renderMarkdown(target, markdown) {
  target.classList.remove("empty");
  target.innerHTML = markdownToHtml(markdown);
}

function renderLoading(target, text = "运行中，请稍候...") {
  target.classList.remove("empty");
  target.innerHTML = `<p>${escapeHtml(text)}</p>`;
}

function renderError(target, error) {
  target.classList.remove("empty");
  target.innerHTML = `<p class="error-text">${escapeHtml(error.message || error)}</p>`;
}

function listText(items) {
  if (!items || items.length === 0) {
    return "无";
  }
  return items.join("、");
}

function evidenceMarkdown(items, limit = 8) {
  const evidence = (items || []).slice(0, limit);
  if (evidence.length === 0) {
    return "- 无";
  }
  return evidence
    .map((item) => `- \`${item.file_path}:${item.line_start}-${item.line_end}\`\n\n\`\`\`text\n${item.quote}\n\`\`\``)
    .join("\n\n");
}

function formatCodebaseAnswer(answer) {
  return [
    "# 代码问答结果",
    "",
    `## 问题`,
    answer.question,
    "",
    "## 回答",
    answer.answer,
    "",
    "## 搜索词",
    listText(answer.searched_terms),
    "",
    "## 证据",
    evidenceMarkdown(answer.evidence),
    "",
    "## 风险提示",
    listText(answer.risk_notes),
  ].join("\n");
}

function formatImpact(report) {
  return [
    "# 影响分析报告",
    "",
    `目标文件：\`${report.target_path}\``,
    "",
    "## 可能影响区域",
    listText(report.likely_impacted_areas),
    "",
    "## 测试建议",
    listText(report.test_suggestions),
    "",
    "## 引用证据",
    evidenceMarkdown(report.referenced_by),
  ].join("\n");
}

function formatReview(report) {
  return [
    "# Diff Review 报告",
    "",
    report.summary,
    "",
    "## 变更文件",
    listText(report.changed_files),
    "",
    "## 风险点",
    listText(report.risk_notes),
    "",
    "## 测试建议",
    listText(report.test_suggestions),
    "",
    "## 证据",
    evidenceMarkdown(report.evidence),
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
    throw new Error(typeof body === "string" ? body : JSON.stringify(body, null, 2));
  }
  return body;
}

async function withForm(form, target, action) {
  const button = form.querySelector("button[type='submit']");
  button.disabled = true;
  renderLoading(target);
  try {
    renderMarkdown(target, await action());
  } catch (error) {
    renderError(target, error);
  } finally {
    button.disabled = false;
  }
}

async function checkHealth() {
  if (!healthStatus || !statusDot) {
    return;
  }
  try {
    const body = await requestJson("/health");
    healthStatus.textContent = `${body.app_name} · ${body.status}`;
    statusDot.classList.add("ok");
  } catch {
    healthStatus.textContent = "服务不可用";
    statusDot.classList.remove("ok");
  }
}

function bindOverviewPage() {
  const form = document.querySelector("#overviewForm");
  if (!form) {
    return;
  }
  const output = document.querySelector("#overviewOutput");
  const source = document.querySelector("#overviewSource");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    withForm(form, output, async () => {
      const body = await requestJson("/codebase/overview", {
        method: "POST",
        body: JSON.stringify({ repository_path: document.querySelector("#overviewRepo").value }),
      });
      source.textContent = body.analysis_source === "deepseek" ? "DeepSeek 生成" : "静态 fallback";
      return body.report;
    });
  });
}

function bindAskPage() {
  const form = document.querySelector("#askForm");
  if (!form) {
    return;
  }
  const output = document.querySelector("#askOutput");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    withForm(form, output, async () => {
      const body = await requestJson("/codebase/ask", {
        method: "POST",
        body: JSON.stringify({
          repository_path: document.querySelector("#askRepo").value,
          question: document.querySelector("#codeQuestion").value,
        }),
      });
      return formatCodebaseAnswer(body);
    });
  });
}

function bindImpactPage() {
  const form = document.querySelector("#impactForm");
  if (!form) {
    return;
  }
  const output = document.querySelector("#impactOutput");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    withForm(form, output, async () => {
      const body = await requestJson("/codebase/impact", {
        method: "POST",
        body: JSON.stringify({
          repository_path: document.querySelector("#impactRepo").value,
          target_path: document.querySelector("#impactPath").value,
        }),
      });
      return formatImpact(body);
    });
  });
}

function bindReviewPage() {
  const form = document.querySelector("#reviewForm");
  if (!form) {
    return;
  }
  const output = document.querySelector("#reviewOutput");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    withForm(form, output, async () => {
      const body = await requestJson("/codebase/review-diff", {
        method: "POST",
        body: JSON.stringify({ repository_path: document.querySelector("#reviewRepo").value }),
      });
      return formatReview(body);
    });
  });
}

function bindEvalPage() {
  const form = document.querySelector("#evalForm");
  if (!form) {
    return;
  }
  const output = document.querySelector("#evalOutput");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    withForm(form, output, () => requestJson("/evals/latest-report"));
  });
}

checkHealth();
bindOverviewPage();
bindAskPage();
bindImpactPage();
bindReviewPage();
bindEvalPage();
