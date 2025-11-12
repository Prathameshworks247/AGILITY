from __future__ import annotations

import os
from typing import Optional, Dict, Any, List
import httpx

from fastapi import FastAPI, HTTPException, Query, Header
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


class SnapshotPayload(BaseModel):
    taskId: str
    developerId: Optional[str] = None
    languageId: str
    filePath: str
    content: str
    diff: Optional[str] = None
    branch: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    sentAt: Optional[str] = None


class SnapshotResponse(BaseModel):
    acknowledgementId: str
    receivedAt: str
    message: str


class TaskReviewPayload(BaseModel):
    taskId: str
    status: str  # PASS, WARN, FAIL
    summary: str
    findings: List[Dict[str, Any]]
    developerId: Optional[str] = None


app = FastAPI(title="AGILITY AI Summarizer & Reviewer", version="0.1.0")

# Configuration for Next.js backend
NEXTJS_API_URL = os.getenv("NEXTJS_API_URL", "http://localhost:3000/api/task-reviews")
NEXTJS_SERVICE_TOKEN = os.getenv("NEXTJS_SERVICE_TOKEN")


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


@app.post("/v1/snapshots", response_model=SnapshotResponse)
async def receive_snapshot(
    snapshot: SnapshotPayload,
    authorization: Optional[str] = Header(None)
):
    """
    Receives code snapshots from VS Code extension, performs AI review,
    and forwards results to Next.js backend.
    """
    try:
        import uuid
        from datetime import datetime
        
        # Generate acknowledgement
        ack_id = str(uuid.uuid4())
        received_at = datetime.utcnow().isoformat() + "Z"
        
        if not snapshot.developerId:
            raise HTTPException(
                status_code=400,
                detail="developerId missing. Configure agilityAI.developerId in the VS Code extension settings.",
            )

        # Perform AI code review
        gemini = _get_gemini()
        
        # Use diff if available, otherwise use full content
        code_to_review = snapshot.diff if snapshot.diff else snapshot.content
        
        if not code_to_review or len(code_to_review.strip()) == 0:
            # No changes to review
            review_result = "No code changes detected."
            status = "PASS"
            findings = []
        else:
            # Get AI review
            review_result = gemini.review_code(code_to_review)
            
            # Parse review result to determine status and extract findings
            status, findings = _parse_review_result(review_result, snapshot.filePath)
        
        # Prepare summary
        summary = f"Code review for {snapshot.filePath}"
        if snapshot.branch:
            summary += f" on branch {snapshot.branch}"
        
        # Forward to Next.js backend
        await _forward_review_to_nextjs(
            task_id=snapshot.taskId,
            status=status,
            summary=review_result[:500],  # First 500 chars as summary
            findings=findings,
            developer_id=snapshot.developerId,
            authorization=authorization
        )
        
        return SnapshotResponse(
            acknowledgementId=ack_id,
            receivedAt=received_at,
            message=f"Snapshot received and reviewed. Status: {status}"
        )
        
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process snapshot: {str(exc)}")


def _parse_review_result(review_text: str, file_path: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    Parse AI review text to determine status (PASS/WARN/FAIL) and extract findings.
    """
    findings = []
    review_lower = review_text.lower()
    
    # Simple heuristic: look for severity keywords
    has_blocker = "blocker" in review_lower
    has_high = "high" in review_lower or "critical" in review_lower
    has_medium = "medium" in review_lower
    has_security = "security" in review_lower
    has_bug = "bug" in review_lower
    
    # Determine status
    if has_blocker or (has_security and has_high):
        status = "FAIL"
    elif has_high or has_medium or has_bug:
        status = "WARN"
    else:
        status = "PASS"
    
    # Extract findings (simple split by sections)
    sections = ["bugs", "security", "performance", "maintainability", "testing", "style"]
    for section in sections:
        if section in review_lower:
            # Try to extract content for this section
            start_idx = review_lower.find(section)
            # Find next section or end
            end_idx = len(review_text)
            for other_section in sections:
                if other_section != section:
                    other_idx = review_lower.find(other_section, start_idx + len(section))
                    if other_idx > start_idx and other_idx < end_idx:
                        end_idx = other_idx
            
            section_content = review_text[start_idx:end_idx].strip()
            if section_content and "none" not in section_content.lower()[:100]:
                findings.append({
                    "category": section.capitalize(),
                    "severity": "medium",
                    "file": file_path,
                    "message": section_content[:300]  # Truncate long messages
                })
    
    # If no specific findings but review has content, add general finding
    if not findings and len(review_text) > 50:
        findings.append({
            "category": "General",
            "severity": "low",
            "file": file_path,
            "message": review_text[:300]
        })
    
    return status, findings


async def _forward_review_to_nextjs(
    task_id: str,
    status: str,
    summary: str,
    findings: List[Dict[str, Any]],
    developer_id: Optional[str] = None,
    authorization: Optional[str] = None
):
    """
    Forward the review results to Next.js backend API.
    """
    try:
        headers = {"Content-Type": "application/json"}
        if NEXTJS_SERVICE_TOKEN:
            headers["Authorization"] = f"Bearer {NEXTJS_SERVICE_TOKEN}"
        elif authorization:
            headers["Authorization"] = authorization
        
        payload = TaskReviewPayload(
            taskId=task_id,
            status=status,
            summary=summary,
            findings=findings,
            developerId=developer_id
        )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                NEXTJS_API_URL,
                json=payload.model_dump(),
                headers=headers
            )
            
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Next.js API returned error: {response.text}"
                )
                
    except httpx.RequestError as exc:
        # Log but don't fail the snapshot receipt
        print(f"Warning: Failed to forward review to Next.js: {exc}")
    except Exception as exc:
        print(f"Warning: Unexpected error forwarding to Next.js: {exc}")
