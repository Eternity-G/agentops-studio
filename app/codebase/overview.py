"""Human-readable repository overview generation."""

from __future__ import annotations

import json
from pathlib import Path

from app.codebase.reader import CodeFileReader
from app.codebase.scanner import RepositoryScanner
from app.codebase.security import RepositorySecurity
from app.schemas import CodeEvidence, CodebaseOverview, CodebaseSummary


class CodebaseOverviewer:
    """Build a user-facing overview report for a repository."""

    def __init__(
        self,
        *,
        security: RepositorySecurity | None = None,
        scanner: RepositoryScanner | None = None,
        reader: CodeFileReader | None = None,
    ) -> None:
        self._security = security or RepositorySecurity()
        self._scanner = scanner or RepositoryScanner(self._security)
        self._reader = reader or CodeFileReader(self._security)

    def build(self, repository_path: str = ".") -> CodebaseOverview:
        """Build a structured and human-readable repository overview."""

        repository_root = self._security.resolve_repository(repository_path)
        summary = self._scanner.summarize(repository_root.as_posix())
        project_name = self._project_name(repository_root)
        project_type = self._project_type(summary)
        overview = self._overview_text(project_name=project_name, summary=summary)
        architecture = self._architecture_text(summary)
        main_modules = self._main_modules(summary)
        entry_points = self._entry_points(repository_root, summary)
        setup_hints = self._setup_hints(repository_root, summary)
        suggested_questions = self._suggested_questions(project_type)
        risk_notes = self._risk_notes(summary)
        report = self._render_report(
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
        """Infer project name from package metadata or directory name."""

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

        has_frontend = bool(summary.frontend_signals)
        has_backend = bool(summary.backend_signals)
        if "apps" in summary.top_level_directories and "packages" in summary.top_level_directories:
            return "企业级 monorepo / 全栈工程"
        if has_frontend and has_backend:
            return "前后端一体项目"
        if has_frontend:
            return "前端项目"
        if has_backend:
            return "后端服务项目"
        return "通用代码仓库"

    def _overview_text(self, *, project_name: str, summary: CodebaseSummary) -> str:
        """Create a high-level project explanation."""

        top_languages = "、".join(list(summary.languages.keys())[:4]) or "未知语言"
        return (
            f"{project_name} 是一个{self._project_type(summary)}。"
            f"当前扫描到 {summary.analyzed_files} 个可分析文件、约 {summary.total_lines} 行代码，"
            f"主要语言包括 {top_languages}。"
            "从目录和关键文件看，它更适合作为企业研发场景下的代码理解、功能定位、"
            "影响分析和 Review 对象，而不是简单脚本项目。"
        )

    def _architecture_text(self, summary: CodebaseSummary) -> str:
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
        if not parts:
            parts.append("当前仓库没有明显 monorepo 分层，需要进一步通过代码问答定位入口和核心模块。")
        return "\n".join(parts)

    def _main_modules(self, summary: CodebaseSummary) -> list[str]:
        """Return important modules for first reading."""

        preferred = [
            "apps",
            "app",
            "src",
            "backend",
            "frontend",
            "packages",
            "libs",
            "docs",
            "tests",
            "scripts",
        ]
        directories = set(summary.top_level_directories)
        modules = [directory for directory in preferred if directory in directories]
        modules.extend(directory for directory in summary.top_level_directories if directory not in modules)
        return modules[:20]

    def _entry_points(self, repository_root: Path, summary: CodebaseSummary) -> list[CodeEvidence]:
        """Read likely entry or configuration files as evidence."""

        candidates = [
            "README.md",
            "package.json",
            "pyproject.toml",
            "apps/api/src/app.module.ts",
            "apps/worker/src/app.module.ts",
            "app/api/routes.py",
            "app/agent.py",
        ]
        evidence: list[CodeEvidence] = []
        for file_path in candidates:
            if file_path in summary.key_files or (repository_root / file_path).exists():
                try:
                    evidence.append(self._reader.read(repository_root.as_posix(), file_path))
                except Exception:
                    continue
        return evidence[:10]

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
            hints.append("检测到 Docker 相关文件，可以查看 Dockerfile 或 docker/ 目录了解部署方式。")
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

        notes = ["概览基于静态扫描，真实运行链路仍需结合启动命令、测试和业务文档确认。"]
        if summary.analyzed_files >= 5000:
            notes.append("仓库规模较大，建议优先从入口文件、关键包和测试用例开始理解。")
        if "TypeScript" in summary.languages and "Python" not in summary.languages:
            notes.append("当前 TypeScript 主要通过关键词和文件证据分析，AST 级理解可后续接 Tree-sitter。")
        if summary.frontend_signals and summary.backend_signals:
            notes.append("仓库同时存在前端和后端信号，修改共享类型或配置时要注意跨端影响。")
        return notes[:10]

    def _render_report(
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
        """Render a Markdown-like report for the web page."""

        languages = "\n".join(f"- {name}: {count}" for name, count in summary.languages.items()) or "-"
        entries = "\n".join(
            f"- {item.file_path}:{item.line_start}-{item.line_end}" for item in entry_points
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
                "\n".join(f"- {module}" for module in main_modules) or "-",
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
