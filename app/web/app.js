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
    }),
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
    }),
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
    }),
  );
});

document.querySelector("#reviewButton").addEventListener("click", (event) => {
  withButton(event.currentTarget, reviewOutput, () =>
    requestJson("/codebase/review-diff", {
      method: "POST",
      body: JSON.stringify({
        repository_path: document.querySelector("#reviewRepo").value,
      }),
    }),
  );
});

document.querySelector("#loadEvalButton").addEventListener("click", (event) => {
  withButton(event.currentTarget, evalOutput, () => requestJson("/evals/latest-report"));
});

checkHealth();
