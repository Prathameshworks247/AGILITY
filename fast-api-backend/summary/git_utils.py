from __future__ import annotations

import subprocess
from typing import List, Optional, Tuple


def _run_git_command(args: List[str], cwd: Optional[str] = None) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def get_latest_commit_hash(cwd: Optional[str] = None) -> str:
    return _run_git_command(["rev-parse", "HEAD"], cwd=cwd).strip()


def get_commit_message(commit_hash: str, cwd: Optional[str] = None) -> str:
    return _run_git_command(["show", "-s", "--format=%B", commit_hash], cwd=cwd).strip()


def get_changed_files(commit_hash: str, cwd: Optional[str] = None) -> List[str]:
    out = _run_git_command(["show", "--pretty=", "--name-only", commit_hash], cwd=cwd)
    files = [line.strip() for line in out.splitlines() if line.strip()]
    return files


def get_diff_for_commit(commit_hash: str, cwd: Optional[str] = None, max_bytes: int = 250_000) -> str:
    diff = _run_git_command(["show", commit_hash, "-U3", "--no-color"], cwd=cwd)
    if len(diff.encode("utf-8")) > max_bytes:
        # Truncate safely on bytes boundary
        encoded = diff.encode("utf-8")[:max_bytes]
        safe = encoded.decode("utf-8", errors="ignore")
        return safe + "\n... [truncated]"
    return diff


def get_diff_against_base(base_ref: str = "origin/main", cwd: Optional[str] = None, max_bytes: int = 250_000) -> Tuple[str, List[str]]:
    # Determine merge-base and produce diff for PR scenarios
    merge_base = _run_git_command(["merge-base", base_ref, "HEAD"], cwd=cwd).strip()
    files_out = _run_git_command(["diff", "--name-only", f"{merge_base}..HEAD"], cwd=cwd)
    files = [line.strip() for line in files_out.splitlines() if line.strip()]
    diff = _run_git_command(["diff", "-U3", f"{merge_base}..HEAD", "--no-color"], cwd=cwd)
    if len(diff.encode("utf-8")) > max_bytes:
        encoded = diff.encode("utf-8")[:max_bytes]
        safe = encoded.decode("utf-8", errors="ignore")
        diff = safe + "\n... [truncated]"
    return diff, files


