from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from .gemini_client import GeminiService
from .git_utils import (
    get_latest_commit_hash,
    get_commit_message,
    get_changed_files,
    get_diff_for_commit,
    get_diff_against_base,
)


class SummaryResponse(BaseModel):
    summary: str
    commit: str


class ReviewResponse(BaseModel):
    review: str
    base_ref: Optional[str] = None


app = FastAPI(title="AGILITY AI Summarizer & Reviewer", version="0.1.0")


def _get_gemini() -> GeminiService:
    try:
        return GeminiService()
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/summary", response_model=SummaryResponse)
def summarize(commit: Optional[str] = Query(default=None, description="Commit hash to summarize. Defaults to HEAD.")):
    try:
        commit_hash = commit or get_latest_commit_hash()
        commit_text = get_commit_message(commit_hash)
        changed_files = get_changed_files(commit_hash)
        diff_text = get_diff_for_commit(commit_hash)
        gemini = _get_gemini()
        summary_text = gemini.summarize_commit(commit_text, diff_text, changed_files)
        return SummaryResponse(summary=summary_text, commit=commit_hash)
    except RuntimeError as rexc:
        raise HTTPException(status_code=400, detail=str(rexc))


@app.get("/code-review", response_model=ReviewResponse)
def code_review(base_ref: Optional[str] = Query(default=None, description="Base ref for PR diff, e.g., origin/main. If omitted, review latest commit.")):
    try:
        gemini = _get_gemini()
        if base_ref:
            diff_text, _files = get_diff_against_base(base_ref)
            review_text = gemini.review_code(diff_text)
            return ReviewResponse(review=review_text, base_ref=base_ref)
        else:
            commit_hash = get_latest_commit_hash()
            diff_text = get_diff_for_commit(commit_hash)
            review_text = gemini.review_code(diff_text)
            return ReviewResponse(review=review_text)
    except RuntimeError as rexc:
        raise HTTPException(status_code=400, detail=str(rexc))


@app.get("/")
def root():
    return {"ok": True, "service": app.title, "version": app.version}
