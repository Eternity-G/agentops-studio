"""Minimal Markdown question-answer chain.

第 14 步先实现一个不依赖向量数据库的文档问答链路：

    question + markdown path -> read markdown -> retrieve excerpt -> structured answer

它不是完整 RAG，只是 RAG 的最小可观测版本。后续可以把当前的简单片段选择
替换成 chunk、embedding、rerank 和真实模型生成。
"""

from __future__ import annotations

import re

from app.schemas import DocumentQuestionAnswer, DocumentQuestionInput, Evidence, LongText
from app.schemas import StepStatus
from app.tools.markdown import ReadMarkdownTool


class MarkdownQuestionAnswerer:
    """Answer questions from one local Markdown file."""

    def __init__(self, reader: ReadMarkdownTool | None = None, excerpt_chars: int = 500) -> None:
        if excerpt_chars <= 0:
            raise ValueError("excerpt_chars must be positive")

        self._reader = reader or ReadMarkdownTool()
        self._excerpt_chars = excerpt_chars

    def answer(self, question_input: DocumentQuestionInput) -> DocumentQuestionAnswer:
        """Read a Markdown document and return a grounded answer."""

        read_result = self._reader.read(question_input.path)
        if read_result.status == StepStatus.FAILED:
            message = f"无法读取文档：{read_result.error}"
            return DocumentQuestionAnswer(
                question=question_input.question,
                answer=message,
                source_path=question_input.path,
                excerpt=None,
                completed=False,
                evidence=[],
            )

        content = self._extract_content(read_result.output)
        excerpt = self._select_excerpt(content=content, question=question_input.question)
        answer = self._build_answer(
            question=question_input.question,
            source_path=question_input.path,
            excerpt=excerpt,
        )

        return DocumentQuestionAnswer(
            question=question_input.question,
            answer=answer,
            source_path=question_input.path,
            excerpt=excerpt,
            completed=True,
            evidence=[
                Evidence(
                    title=f"Markdown 文档：{question_input.path}",
                    source=question_input.path,
                    quote=excerpt,
                )
            ],
        )

    def _extract_content(self, tool_output: str) -> str:
        """Remove ReadMarkdownTool metadata header from its output."""

        _, separator, content = tool_output.partition("\n\n")
        return content if separator else tool_output

    def _select_excerpt(self, *, content: str, question: str) -> LongText:
        """Select a small relevant excerpt with deterministic keyword scoring."""

        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", content) if paragraph.strip()]
        if not paragraphs:
            return "文档为空，未找到可引用内容。"

        keywords = self._extract_keywords(question)
        scored: list[tuple[int, int, str]] = []
        for index, paragraph in enumerate(paragraphs):
            lowered = paragraph.lower()
            score = sum(1 for keyword in keywords if keyword in lowered)
            scored.append((score, -index, paragraph))

        best_score, _, best_paragraph = max(scored, key=lambda item: (item[0], item[1]))
        if best_score == 0:
            best_paragraph = paragraphs[0]

        return best_paragraph[: self._excerpt_chars]

    def _extract_keywords(self, question: str) -> list[str]:
        """Extract simple keywords from English words and Chinese character groups."""

        lowered = question.lower()
        english_words = re.findall(r"[a-z0-9_]{2,}", lowered)
        chinese_groups = re.findall(r"[\u4e00-\u9fff]{2,}", lowered)
        return english_words + chinese_groups

    def _build_answer(self, *, question: str, source_path: str, excerpt: str) -> LongText:
        """Build a deterministic answer grounded in the selected excerpt."""

        return (
            f"根据 `{source_path}` 中的内容，问题“{question}”的相关依据是："
            f"{excerpt}"
        )
