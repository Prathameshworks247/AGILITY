"""
Review orchestrator: take review units, build prompts, dispatch to LLM,
aggregate findings into PR-level summary and per-unit findings.
"""

from __future__ import annotations

import re
from typing import Sequence

from app.models import ReviewFinding, ReviewUnit
from app.context.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
    change_summary_bullets_for_unit,
    format_review_unit_for_prompt,
)
from app.context.assembler import ContextAssembler
from app.graph.store import GraphStore
from app.llm.client import LLMClient, get_llm_client


def _parse_findings_from_response(response: str, default_file: str = "", default_symbol: str = "") -> list[ReviewFinding]:
    """
    Heuristic parse of LLM response into ReviewFinding list.
    Looks for severity/category keywords and line references.
    """
    findings: list[ReviewFinding] = []
    severity_map = {"error": "error", "warning": "warn", "warn": "warn", "info": "info", "suggestion": "info"}
    category_map = {"correctness": "correctness", "security": "security", "performance": "performance", "style": "style", "test": "correctness"}
    blocks = re.split(r"\n(?=#{1,3}\s|\*\*|-\s*(?:Error|Warning|Info|Suggestion))", response, flags=re.IGNORECASE)
    for block in blocks:
        block = block.strip()
        if not block or len(block) < 10:
            continue
        severity = "info"
        category = "style"
        for word, sev in severity_map.items():
            if word in block.lower()[:200]:
                severity = sev
                break
        for word, cat in category_map.items():
            if word in block.lower()[:200]:
                category = cat
                break
        # Line reference like "line 42" or "L42"
        line_num = None
        for m in re.finditer(r"(?:line|L)\s*(\d+)", block, re.IGNORECASE):
            line_num = int(m.group(1))
            break
        message = block[:500].strip()
        findings.append(
            ReviewFinding(
                severity=severity,
                category=category,
                location_file=default_file,
                location_line_start=line_num,
                location_line_end=line_num,
                symbol=default_symbol or None,
                message=message,
                suggested_fix=None,
            )
        )
    if not findings and response.strip():
        findings.append(
            ReviewFinding(
                severity="info",
                category="style",
                location_file=default_file,
                message=response[:500].strip(),
            )
        )
    return findings


class ReviewOrchestrator:
    """Takes review units, builds prompts, calls LLM, aggregates findings."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        store: GraphStore | None = None,
        assembler: ContextAssembler | None = None,
    ) -> None:
        self.llm = llm_client or get_llm_client()
        self.store = store
        self.assembler = assembler

    async def run(
        self,
        units: Sequence[ReviewUnit],
        repo_context: str = "",
        stream: bool = False,
    ) -> tuple[str, list[ReviewFinding]]:
        """
        Run LLM review for each unit (or batch), aggregate into one summary
        and a flat list of findings. Returns (summary, findings).
        """
        all_findings: list[ReviewFinding] = []
        summaries: list[str] = []
        for unit in units:
            bullets = change_summary_bullets_for_unit(unit)
            context_snippets = {}
            if self.store and self.assembler:
                for nid in unit.context_node_ids:
                    context_snippets[nid] = self.assembler.load_snippet_for_node(self.store, nid)
            relevant_code = format_review_unit_for_prompt(unit, context_snippets)
            user_prompt = build_user_prompt(repo_context, bullets, relevant_code)
            if stream:
                chunk_acc = []
                async for chunk in self.llm.complete_stream(SYSTEM_PROMPT, user_prompt):
                    chunk_acc.append(chunk)
                response = "".join(chunk_acc)
            else:
                response = await self.llm.complete(SYSTEM_PROMPT, user_prompt)
            summaries.append(response)
            findings = _parse_findings_from_response(
                response,
                default_file=unit.symbol_change.file_path,
                default_symbol=unit.symbol_change.symbol_name,
            )
            all_findings.extend(findings)
        summary = "\n\n---\n\n".join(summaries) if summaries else "No review output."
        return summary, all_findings
