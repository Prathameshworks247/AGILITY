import os
from typing import Optional
import dotenv
import google.generativeai as genai

dotenv.load_dotenv()
class GeminiService:
    """Thin wrapper around Google Generative AI (Gemini) SDK."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash-exp") -> None:
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY is not set. Provide it via env var or constructor.")

        self.model_name = model_name
        genai.configure(api_key=key)
        self._model = genai.GenerativeModel(model_name)

    def generate(self, prompt: str, system_instruction: Optional[str] = None, max_output_tokens: int = 2048) -> str:
        parts = []
        if system_instruction:
            parts.append(system_instruction)
        parts.append(prompt)

        response = self._model.generate_content(parts, generation_config={"max_output_tokens": max_output_tokens})
        return (response.text or "").strip()

    def summarize_commit(self, commit_text: str, diff_text: str, changed_files: list[str]) -> str:
        system_msg = (
            "You are an expert software engineer. Provide concise, actionable outputs."
        )
        prompt = (
            "Summarize the latest commit. Keep it concise and useful for release notes.\n\n"
            "Required sections:\n"
            "- Title: one-line summary\n"
            "- Overview: 2-4 bullet points\n"
            "- Risk: low/medium/high with rationale\n"
            "- Affected areas: concise list\n\n"
            f"Commit message and body:\n<<<\n{commit_text}\n>>>\n\n"
            f"Changed files:\n{os.linesep.join(changed_files) if changed_files else 'None'}\n\n"
            f"Unified diff (truncated if long):\n<<<\n{diff_text}\n>>>\n"
        )
        return self.generate(prompt, system_instruction=system_msg)

    def review_code(self, diff_text: str) -> str:
        system_msg = (
            "You are a strict code reviewer. Be specific and practical."
        )
        prompt = (
            "Perform a code review of the provided unified diff.\n\n"
            "Return sections: Bugs, Security, Performance, Maintainability, Testing, Style.\n"
            "For each finding, include: Severity (blocker/high/medium/low), File, Line (if known), and Actionable suggestion.\n"
            "If N/A, say 'None'.\n\n"
            f"Diff to review:\n<<<\n{diff_text}\n>>>\n"
        )
        return self.generate(prompt, system_instruction=system_msg)


