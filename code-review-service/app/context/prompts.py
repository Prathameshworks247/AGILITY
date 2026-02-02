"""
Prompt templates for the LLM review: system prompt and structured user prompt
with repository context, change summary, and relevant surrounding code.
"""

from __future__ import annotations

from typing import Sequence

from app.models import ReviewUnit


SYSTEM_PROMPT = """You are an expert code reviewer. Your task is to review code changes in a pull request with full awareness of their impact.

You will be given:
1. A short repository context (if any).
2. A structured summary of what semantically changed (added/removed/modified symbols, with descriptors like signature_change).
3. Relevant surrounding code: the changed symbol and structurally dependent code (callers, callees, tests) retrieved via a repository graph.

Use this graph-based context to reason about indirect impacts that flat retrieval often misses: broken callers, missing test updates, contract violations, and performance or security implications. Focus on correctness, security, performance, style, and test coverage. For each finding, suggest a concrete fix when applicable."""


def build_user_prompt(
    repo_context: str,
    change_summary_bullets: Sequence[str],
    relevant_code_snippets: str,
    instructions_override: str | None = None,
) -> str:
    """
    Build the user (or assistant) prompt with repository context, change summary,
    and relevant surrounding code. Optionally append custom instructions.
    """
    sections = []
    if repo_context.strip():
        sections.append("## Repository context\n\n" + repo_context.strip())
    sections.append("## Change summary\n\n" + "\n".join(f"- {b}" for b in change_summary_bullets))
    sections.append("## Relevant surrounding code\n\n" + (relevant_code_snippets.strip() or "(none)"))
    if instructions_override:
        sections.append("## Additional instructions\n\n" + instructions_override.strip())
    return "\n\n".join(sections)


def format_review_unit_for_prompt(unit: ReviewUnit, context_snippets: dict[str, str]) -> str:
    """
    Format a single ReviewUnit into the "Relevant surrounding code" section:
    changed symbol snippet (before/after) plus context node snippets with labels.
    """
    parts = []
    if unit.before_snippet or unit.after_snippet:
        parts.append("### Changed symbol")
        if unit.before_snippet:
            parts.append("**Before:**\n```\n" + unit.before_snippet.strip() + "\n```")
        if unit.after_snippet:
            parts.append("**After:**\n```\n" + unit.after_snippet.strip() + "\n```")
    for nid in unit.context_node_ids:
        snip = context_snippets.get(nid, "").strip()
        if snip:
            parts.append(f"### Context: {nid}\n```\n{snip}\n```")
    return "\n\n".join(parts)


def change_summary_bullets_for_unit(unit: ReviewUnit) -> list[str]:
    """Produce bullet points for the change summary from a ReviewUnit."""
    sc = unit.symbol_change
    bullets = [f"{sc.file_path} :: {sc.symbol_name} ({sc.kind.value}): {sc.change_type.value}"]
    if sc.descriptors:
        bullets.append("Descriptors: " + ", ".join(sc.descriptors))
    return bullets
