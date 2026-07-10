const healthStatus = document.querySelector("#healthStatus");
const statusDot = document.querySelector(".status-dot");

const taskInput = document.querySelector("#taskInput");
const taskSession = document.querySelector("#taskSession");
const taskOutput = document.querySelector("#taskOutput");

const questionInput = document.querySelector("#questionInput");
const documentPath = document.querySelector("#documentPath");
const documentSession = document.querySelector("#documentSession");
const documentOutput = document.querySelector("#documentOutput");

const sessionId = document.querySelector("#sessionId");
const noteInput = document.querySelector("#noteInput");
const sessionOutput = document.querySelector("#sessionOutput");
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

document.querySelector("#runTaskButton").addEventListener("click", (event) => {
  withButton(event.currentTarget, taskOutput, () =>
    requestJson("/tasks/run", {
      method: "POST",
      body: JSON.stringify({
        task: taskInput.value,
        metadata: { session_id: taskSession.value },
      }),
    }),
  );
});

document.querySelector("#askDocumentButton").addEventListener("click", (event) => {
  withButton(event.currentTarget, documentOutput, () =>
    requestJson("/documents/ask", {
      method: "POST",
      body: JSON.stringify({
        question: questionInput.value,
        path: documentPath.value,
        session_id: documentSession.value,
      }),
    }),
  );
});

document.querySelector("#loadSessionButton").addEventListener("click", (event) => {
  withButton(event.currentTarget, sessionOutput, () => requestJson(`/sessions/${sessionId.value}`));
});

document.querySelector("#appendNoteButton").addEventListener("click", (event) => {
  withButton(event.currentTarget, sessionOutput, () =>
    requestJson(`/sessions/${sessionId.value}/notes`, {
      method: "POST",
      body: JSON.stringify({
        content: noteInput.value,
        metadata: { source: "web" },
      }),
    }),
  );
});

document.querySelector("#loadEvalButton").addEventListener("click", (event) => {
  withButton(event.currentTarget, evalOutput, () => requestJson("/evals/latest-report"));
});

checkHealth();
