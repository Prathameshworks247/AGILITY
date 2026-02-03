"""
Prompt templates for the LLM review: structured format with header, checklist,
inline comments, and summary. Uses batched review (one call) for conciseness.
"""

from __future__ import annotations

from typing import Sequence

from app.models import ReviewUnit


SYSTEM_PROMPT = """You are an expert code reviewer. Produce a concise, structured review.

## Output format (strict)

### 1. Review Header
- **Title:** One short line describing the change
- **Purpose:** What problem this solves (1-2 sentences)
- **Scope:** Bullet list of files/modules touched
- **Risk:** Low / Medium / High (one word)

### 2. Checklist (brief)
For each category, write 1 line or "OK" if fine:
- **Functionality:** Correctness, edge cases, backward compatibility
- **Design:** Right patterns, not over/under-engineered
- **Code Quality:** Readability, no duplication, no dead code
- **Performance:** Unnecessary loops/DB/API calls?
- **Security:** Input validation, auth, no hardcoded secrets
- **Testing:** Tests added/updated, meaningful coverage?
- **Documentation:** Comments/README where needed?

### 3. Inline comments (Observation → Impact → Suggestion)
For each issue found, use format:
- **[Nit|Suggestion|Issue|Blocking]** `file:line` — Observation. Impact. Suggestion.
Only include actual issues; skip categories with none.

### 4. Summary
- **Overall:** 1-2 sentences
- **Decision:** ✅ Approved | 🔄 Approved with nits | 🛑 Changes requested
- **Requested changes:** Bullet list if any, else "None"

Keep the review SHORT. Focus on high-impact issues. Do not repeat the same feedback across multiple symbols. Group related changes. Omit empty sections."""


def build_user_prompt(
    repo_context: str,
    change_summary_bullets: Sequence[str],
    relevant_code_snippets: str,
    instructions_override: str | None = None,
) -> str:
    """Legacy: per-unit prompt (kept for compatibility)."""
    sections = []
    if repo_context.strip():
        sections.append("## Repository context\n\n" + repo_context.strip())
    sections.append("## Change summary\n\n" + "\n".join(f"- {b}" for b in change_summary_bullets))
    sections.append("## Relevant surrounding code\n\n" + (relevant_code_snippets.strip() or "(none)"))
    if instructions_override:
        sections.append("## Additional instructions\n\n" + instructions_override.strip())
    return "\n\n".join(sections)


def build_batched_prompt(
    scope_files: list[str],
    symbol_summary: list[str],
    import_graph: str,
    code_diffs: str,
    max_diff_lines: int = 150,
) -> str:
    """Build one consolidated prompt for batched review."""
    parts = []
    parts.append("## Scope (files/modules touched)\n")
    parts.append("\n".join(f"- {f}" for f in scope_files[:20]))  # cap files
    parts.append("\n\n## Symbol-level changes\n")
    parts.append("\n".join(f"- {s}" for s in symbol_summary[:50]))  # cap symbols
    if import_graph.strip():
        parts.append("\n\n## Import / dependency relationships\n")
        parts.append(import_graph.strip())
    parts.append("\n\n## Code diffs (key changes)\n")
    # Truncate if too long
    if len(code_diffs) > max_diff_lines * 40:  # ~40 chars/line
        code_diffs = code_diffs[: max_diff_lines * 40] + "\n\n[... truncated for length ...]"
    parts.append(code_diffs.strip() or "(no diffs)")
    return "\n".join(parts)


def format_review_unit_for_prompt(unit: ReviewUnit, context_snippets: dict[str, str]) -> str:
    """Legacy: format single ReviewUnit (kept for compatibility)."""
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
    """Legacy: bullets for single unit."""
    sc = unit.symbol_change
    bullets = [f"{sc.file_path} :: {sc.symbol_name} ({sc.kind.value}): {sc.change_type.value}"]
    if sc.descriptors:
        bullets.append("Descriptors: " + ", ".join(sc.descriptors))
    return bullets
