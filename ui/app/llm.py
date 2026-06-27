from dataclasses import dataclass


@dataclass(frozen=True)
class LlmDecision:
    summary: str
    assumptions: list[str]
    risks: list[str]


class LlmClient:
    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def analyze_requirement(self, prompt: str) -> LlmDecision:
        if not self.api_key:
            return LlmDecision(
                summary=f"Deterministic analysis for: {prompt[:160]}",
                assumptions=[
                    "The system must be runnable without external services.",
                    "Human approval is required before high-impact release actions.",
                ],
                risks=[
                    "Ambiguous requirements can cause scope drift.",
                    "Slug collisions and redirect abuse require explicit guardrails.",
                ],
            )

        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.responses.create(
            model=self.model,
            input=(
                "Summarize this software requirement. Return concise sections for "
                f"summary, assumptions, and risks.\n\n{prompt}"
            ),
        )
        text = response.output_text.strip()
        return LlmDecision(summary=text, assumptions=[], risks=[])

