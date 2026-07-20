"""Repository overview generation with bounded evidence and optional LLM synthesis."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from pathlib import Path

from app.codebase.reader import CodeFileReader
from app.codebase.scanner import RepositoryScanner
from app.codebase.security import RepositorySecurity
from app.providers.deepseek import DeepSeekProvider
from app.schemas import CodeEvidence, CodebaseOverview, CodebaseSummary
from app.settings import load_settings

OverviewLlmClient = Callable[[str, str], str]

ROOT_EVIDENCE_FILES = [
    "README.md",
    "AGENTS.md",
    "package.json",
    "pnpm-workspace.yaml",
    "turbo.json",
    "nx.json",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Dockerfile",
    "pyproject.toml",
]

ENTRY_CANDIDATES = [
    "apps/api/src/app.module.ts",
    "apps/api/src/main.ts",
    "apps/worker/src/app.module.ts",
    "apps/worker/src/main.ts",
    "apps/web/src/main.tsx",
    "apps/web/app/layout.tsx",
    "app/api/routes.py",
    "app/agent.py",
]


class CodebaseOverviewer:
    """Build a user-facing overview report for a repository.

    The class always performs deterministic static analysis first. When the
    local settings select DeepSeek and provide an API key, the static evidence
    is compressed into a bounded prompt and sent to the model for a deeper
    Markdown report. If the model is unavailable, the static report is returned
    so the feature remains usable and testable offline.
    """

    def __init__(
        self,
        *,
        security: RepositorySecurity | None = None,
        scanner: RepositoryScanner | None = None,
        reader: CodeFileReader | None = None,
        llm_client: OverviewLlmClient | None = None,
    ) -> None:
        self._security = security or RepositorySecurity()
        self._scanner = scanner or RepositoryScanner(self._security)
        self._reader = reader or CodeFileReader(self._security, max_chars=6000)
        self._llm_client = llm_client

    def build(self, repository_path: str = ".") -> CodebaseOverview:
        """Build a structured and human-readable repository overview."""

        repository_root = self._security.resolve_repository(repository_path)
        summary = self._scanner.summarize(repository_root.as_posix())
        project_name = self._project_name(repository_root)
        project_type = self._project_type(summary)
        main_modules = self._main_modules(repository_root, summary)
        entry_points = self._entry_points(repository_root, summary)
        setup_hints = self._setup_hints(repository_root, summary)
        suggested_questions = self._suggested_questions(project_type)
        risk_notes = self._risk_notes(summary)
        overview = self._overview_text(project_name=project_name, summary=summary)
        architecture = self._architecture_text(summary, main_modules)
        static_report = self._render_static_report(
            project_name=project_name,
            project_type=project_type,
            overview=overview,
            architecture=architecture,
            main_modules=main_modules,
            entry_points=entry_points,
            setup_hints=setup_hints,
            suggested_questions=suggested_questions,
            risk_notes=risk_notes,
            summary=summary,
        )

        analysis_source = "static"
        report = static_report
        llm_report = self._try_generate_llm_report(
            repository_root=repository_root,
            project_name=project_name,
            project_type=project_type,
            summary=summary,
            main_modules=main_modules,
            entry_points=entry_points,
            setup_hints=setup_hints,
        )
        if llm_report:
            analysis_source = "deepseek"
            report = llm_report
        else:
            risk_notes = [
                *risk_notes,
                "当前报告由静态分析生成；如需更深入的仓库语义概览，请在 .env 中启用 DeepSeek。",
            ][:10]
            report = self._render_static_report(
                project_name=project_name,
                project_type=project_type,
                overview=overview,
                architecture=architecture,
                main_modules=main_modules,
                entry_points=entry_points,
                setup_hints=setup_hints,
                suggested_questions=suggested_questions,
                risk_notes=risk_notes,
                summary=summary,
            )

        return CodebaseOverview(
            repository_path=repository_root.as_posix(),
            project_name=project_name,
            project_type=project_type,
            analysis_source=analysis_source,
            overview=overview,
            architecture=architecture,
            main_modules=main_modules,
            entry_points=entry_points,
            setup_hints=setup_hints,
            suggested_questions=suggested_questions,
            risk_notes=risk_notes,
            summary=summary,
            report=report,
        )

    def _project_name(self, repository_root: Path) -> str:
        """Infer project name from README, package metadata, or directory name."""

        readme_name = self._readme_title(repository_root)
        if readme_name:
            return readme_name

        package_json = repository_root / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8", errors="ignore"))
                name = data.get("name")
                if isinstance(name, str) and name.strip() and name.strip().lower() != "root":
                    return name.strip()[:200]
            except json.JSONDecodeError:
                pass

        pyproject = repository_root / "pyproject.toml"
        if pyproject.exists():
            for line in pyproject.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.strip().startswith("name"):
                    _, _, raw_name = line.partition("=")
                    name = raw_name.strip().strip("\"'")
                    if name:
                        return name[:200]

        return repository_root.name[:200]

    def _readme_title(self, repository_root: Path) -> str | None:
        """Infer a project name from README heading."""

        readme = repository_root / "README.md"
        if not readme.exists():
            return None
        for line in readme.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped.removeprefix("# ").strip()
                return title[:200] if title else None
        return None

    def _project_type(self, summary: CodebaseSummary) -> str:
        """Infer the project type from repository signals."""

        directories = set(summary.top_level_directories)
        has_frontend = bool(summary.frontend_signals)
        has_backend = bool(summary.backend_signals)
        if "apps" in directories and ("packages" in directories or "libs" in directories):
            return "企业级 monorepo / 全栈工程"
        if has_frontend and has_backend:
            return "前后端一体项目"
        if has_frontend:
            return "前端项目"
        if has_backend:
            return "后端服务项目"
        return "通用代码仓库"

    def _overview_text(self, *, project_name: str, summary: CodebaseSummary) -> str:
        """Create a short static project explanation."""

        top_languages = "、".join(list(summary.languages.keys())[:4]) or "未知语言"
        return (
            f"{project_name} 的静态扫描结果显示，这是一个{self._project_type(summary)}。"
            f"当前扫描到 {summary.analyzed_files} 个可分析文件、约 {summary.total_lines} 行代码，"
            f"主要语言包括 {top_languages}。"
            "静态概览只能说明仓库结构和技术信号，真实业务含义需要结合 README、配置文件和关键源码证据继续分析。"
        )

    def _architecture_text(self, summary: CodebaseSummary, main_modules: list[str]) -> str:
        """Create an architecture summary from directory signals."""

        parts: list[str] = []
        directories = set(summary.top_level_directories)
        if "apps" in directories:
            parts.append("`apps/` 通常承载可运行应用，例如 API、Worker、Web 或 Dashboard。")
        if "packages" in directories:
            parts.append("`packages/` 通常承载 SDK、共享包、框架适配或可复用模块。")
        if "libs" in directories:
            parts.append("`libs/` 通常承载跨应用共享的业务库、数据访问层或基础设施代码。")
        if "docs" in directories:
            parts.append("`docs/` 保存项目文档，可用于理解业务概念和开发流程。")
        if "docker" in directories or "Dockerfile" in summary.key_files:
            parts.append("仓库包含 Docker/部署相关文件，说明项目考虑了本地或容器化运行。")
        if main_modules:
            parts.append(f"建议优先阅读这些模块：{'、'.join(main_modules[:8])}。")
        if not parts:
            parts.append("当前仓库没有明显分层，需要通过代码问答进一步定位入口和核心模块。")
        return "\n".join(parts)

    def _main_modules(self, repository_root: Path, summary: CodebaseSummary) -> list[str]:
        """Return important modules for first reading."""

        modules: list[str] = []
        for parent in ("apps", "packages", "libs"):
            parent_path = repository_root / parent
            if parent_path.is_dir():
                for child in sorted(parent_path.iterdir(), key=lambda item: item.name.lower()):
                    if child.is_dir() and not self._security.is_ignored_dir(child):
                        modules.append(f"{parent}/{child.name}")

        preferred = ["apps", "app", "src", "backend", "frontend", "packages", "libs", "docs", "tests", "scripts"]
        directories = set(summary.top_level_directories)
        modules.extend(directory for directory in preferred if directory in directories)
        modules.extend(directory for directory in summary.top_level_directories if directory not in modules)

        unique_modules: list[str] = []
        for module in modules:
            if module not in unique_modules:
                unique_modules.append(module)
        return unique_modules[:20]

    def _entry_points(self, repository_root: Path, summary: CodebaseSummary) -> list[CodeEvidence]:
        """Read likely entry or configuration files as evidence."""

        candidates = [*ROOT_EVIDENCE_FILES, *ENTRY_CANDIDATES]
        for module in self._main_modules(repository_root, summary)[:12]:
            candidates.extend(
                [
                    f"{module}/README.md",
                    f"{module}/package.json",
                    f"{module}/src/main.ts",
                    f"{module}/src/index.ts",
                    f"{module}/src/app.module.ts",
                    f"{module}/index.ts",
                ]
            )

        evidence: list[CodeEvidence] = []
        seen: set[str] = set()
        for file_path in candidates:
            if file_path in seen:
                continue
            seen.add(file_path)
            if file_path in summary.key_files or (repository_root / file_path).exists():
                try:
                    evidence.append(self._reader.read(repository_root.as_posix(), file_path))
                except Exception:
                    continue
        return evidence[:18]

    def _setup_hints(self, repository_root: Path, summary: CodebaseSummary) -> list[str]:
        """Infer setup commands from common package files."""

        hints: list[str] = []
        if (repository_root / "package.json").exists():
            hints.append("检测到 package.json，通常需要先安装 Node 依赖，例如 pnpm install / npm install。")
        if (repository_root / "pnpm-lock.yaml").exists():
            hints.append("检测到 pnpm-lock.yaml，优先使用 pnpm 作为包管理器。")
        if (repository_root / "pyproject.toml").exists():
            hints.append("检测到 pyproject.toml，Python 项目可使用 python -m pip install -e .。")
        if (repository_root / "Dockerfile").exists() or "docker" in summary.top_level_directories:
            hints.append("检测到 Docker 相关文件，可查看 Dockerfile 或 docker/ 目录理解部署方式。")
        if not hints:
            hints.append("未识别到标准安装入口，建议先阅读 README.md 和关键配置文件。")
        return hints[:10]

    def _suggested_questions(self, project_type: str) -> list[str]:
        """Return next questions a developer can ask the Agent."""

        questions = [
            "这个项目的后端入口在哪里？",
            "这个项目的前端入口在哪里？",
            "核心业务模块有哪些？",
            "修改 package.json 会影响哪些服务？",
            "当前 git diff 有哪些风险？",
        ]
        if "monorepo" in project_type:
            questions.insert(0, "apps、packages、libs 分别承担什么职责？")
        return questions[:10]

    def _risk_notes(self, summary: CodebaseSummary) -> list[str]:
        """Return practical reading and maintenance notes."""

        notes = ["概览基于静态扫描和有限证据，真实运行链路仍需结合启动命令、测试和业务文档确认。"]
        if summary.analyzed_files >= 5000:
            notes.append("仓库规模较大，建议优先从入口文件、关键包和测试用例开始理解。")
        if "TypeScript" in summary.languages and "Python" not in summary.languages:
            notes.append("当前 TypeScript 深度理解仍以文件证据和模型综合为主，后续可接入 Tree-sitter 做 AST 级分析。")
        if summary.frontend_signals and summary.backend_signals:
            notes.append("仓库同时存在前端和后端信号，修改共享类型或配置时要注意跨端影响。")
        return notes[:10]

    def _try_generate_llm_report(
        self,
        *,
        repository_root: Path,
        project_name: str,
        project_type: str,
        summary: CodebaseSummary,
        main_modules: list[str],
        entry_points: list[CodeEvidence],
        setup_hints: list[str],
    ) -> str | None:
        """Generate a Markdown report with DeepSeek when available."""

        prompt = self._build_llm_prompt(
            repository_root=repository_root,
            project_name=project_name,
            project_type=project_type,
            summary=summary,
            main_modules=main_modules,
            entry_points=entry_points,
            setup_hints=setup_hints,
        )
        system_prompt = (
            "你是资深软件架构师和代码仓库理解 Agent。"
            "你必须基于用户提供的仓库证据写中文 Markdown 报告。"
            "不要泛泛而谈，不要编造未在证据中出现的技术或业务。"
            "每个关键判断都要引用具体文件路径。"
        )

        try:
            if self._llm_client is not None:
                return self._normalize_markdown(self._llm_client(system_prompt, prompt))

            settings = load_settings()
            if settings.model_provider.strip().lower() != "deepseek" or not settings.deepseek_api_key:
                return None

            provider = DeepSeekProvider(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                model=settings.default_model,
            )
            report = asyncio.run(provider.complete_text(system_prompt=system_prompt, user_prompt=prompt))
            return self._normalize_markdown(report)
        except Exception:
            return None

    def _build_llm_prompt(
        self,
        *,
        repository_root: Path,
        project_name: str,
        project_type: str,
        summary: CodebaseSummary,
        main_modules: list[str],
        entry_points: list[CodeEvidence],
        setup_hints: list[str],
    ) -> str:
        """Build a bounded evidence pack for the LLM."""

        module_inventory = self._module_inventory(repository_root, main_modules)
        evidence_text = "\n\n".join(
            f"### {item.file_path}:{item.line_start}-{item.line_end}\n```text\n{item.quote[:5000]}\n```"
            for item in entry_points
        )
        prompt = f"""
请基于下面的仓库证据，生成一份真正给开发者看的仓库理解报告。

报告必须包含这些章节：
1. 项目一句话定位
2. 这个项目解决什么问题
3. 核心用户和典型使用场景
4. 技术栈与工程形态
5. 主要模块职责
6. 关键运行链路推断
7. 如何继续阅读源码
8. 当前分析边界

写作要求：
- 输出 Markdown。
- 不要输出 JSON。
- 不要只重复文件数量。
- 对重要判断写出依据文件，例如 `README.md`、`package.json`、`apps/api/src/main.ts`。
- 如果证据不足，明确写“当前证据不足以判断”，不要编造。

仓库基础信息：
- 仓库路径：{repository_root.as_posix()}
- 项目名：{project_name}
- 静态项目类型：{project_type}
- 可分析文件数：{summary.analyzed_files}
- 估算代码行数：{summary.total_lines}
- 主要语言：{json.dumps(summary.languages, ensure_ascii=False)}
- 顶层目录：{", ".join(summary.top_level_directories)}
- 前端信号：{", ".join(summary.frontend_signals) or "无"}
- 后端信号：{", ".join(summary.backend_signals) or "无"}
- 运行线索：{"；".join(setup_hints)}

模块清单：
{module_inventory}

关键文件证据：
{evidence_text}
""".strip()
        return prompt[:55000]

    def _module_inventory(self, repository_root: Path, main_modules: list[str]) -> str:
        """Collect names and package scripts for important modules."""

        rows: list[str] = []
        for module in main_modules[:20]:
            module_path = repository_root / module
            if not module_path.exists() or not module_path.is_dir():
                continue
            package_json = module_path / "package.json"
            if package_json.exists():
                try:
                    data = json.loads(package_json.read_text(encoding="utf-8", errors="ignore"))
                    name = data.get("name") or module
                    scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
                    script_names = ", ".join(list(scripts.keys())[:8]) or "无"
                    rows.append(f"- `{module}`：package `{name}`，scripts: {script_names}")
                    continue
                except json.JSONDecodeError:
                    pass
            child_names = [
                child.name
                for child in sorted(module_path.iterdir(), key=lambda item: item.name.lower())[:12]
                if not self._security.is_ignored_dir(child)
            ]
            rows.append(f"- `{module}`：包含 {', '.join(child_names) if child_names else '暂无可见子项'}")
        return "\n".join(rows) or "- 暂无模块清单"

    def _normalize_markdown(self, report: str) -> str | None:
        """Normalize model output and reject empty responses."""

        cleaned = report.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned[:20000] if cleaned else None

    def _render_static_report(
        self,
        *,
        project_name: str,
        project_type: str,
        overview: str,
        architecture: str,
        main_modules: list[str],
        entry_points: list[CodeEvidence],
        setup_hints: list[str],
        suggested_questions: list[str],
        risk_notes: list[str],
        summary: CodebaseSummary,
    ) -> str:
        """Render a static Markdown report for offline fallback."""

        languages = "\n".join(f"- {name}: {count}" for name, count in summary.languages.items()) or "-"
        entries = "\n".join(
            f"- `{item.file_path}:{item.line_start}-{item.line_end}`" for item in entry_points
        ) or "-"
        return "\n".join(
            [
                f"# {project_name} 仓库理解报告",
                "",
                f"项目类型：{project_type}",
                "",
                "## 这个项目是做什么的",
                overview,
                "",
                "## 架构初步判断",
                architecture,
                "",
                "## 规模与技术栈",
                f"- 可分析文件数：{summary.analyzed_files}",
                f"- 估算代码行数：{summary.total_lines}",
                "- 主要语言：",
                languages,
                "",
                "## 重点目录",
                "\n".join(f"- `{module}`" for module in main_modules) or "-",
                "",
                "## 建议优先阅读的入口证据",
                entries,
                "",
                "## 运行/部署线索",
                "\n".join(f"- {hint}" for hint in setup_hints),
                "",
                "## 下一步可以问 Agent",
                "\n".join(f"- {question}" for question in suggested_questions),
                "",
                "## 风险提示",
                "\n".join(f"- {note}" for note in risk_notes),
            ]
        )
