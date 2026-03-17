import time

import anthropic
from typing import Iterator

from config.settings import Settings
from core.token_tracker import TokenTracker, TokenUsage

MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 10]


class BudgetExceededError(Exception):
    """Raised when monthly budget is exceeded."""
    pass


# Tasks that can use the cheaper Haiku model
HAIKU_CONTEXTS = {"summarize", "classify", "extract", "format", "morning_briefing"}


class ClaudeClient:
    def __init__(self, settings: Settings, token_tracker: TokenTracker):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.haiku_model = "claude-haiku-3-5"
        self.max_tokens = settings.claude_max_tokens
        self.token_tracker = token_tracker

    def _pick_model(self, context_label: str) -> str:
        """Use Haiku for cheap tasks, Sonnet for everything else."""
        if context_label in HAIKU_CONTEXTS:
            return self.haiku_model
        return self.model

    def _check_budget(self):
        """Block API calls if monthly budget is exceeded."""
        stats = self.token_tracker.monthly_stats()
        if stats["budget_pct"] >= 100:
            raise BudgetExceededError(
                f"Budget mensuel dépassé ({stats['cost_usd']:.2f}$ / {self.token_tracker.monthly_budget}$). "
                f"Augmente le budget dans .env (MONTHLY_BUDGET_USD) ou attends le mois prochain."
            )

    def _call_with_retry(self, func):
        """Call an API function with retry on overloaded/rate-limit errors."""
        for attempt in range(MAX_RETRIES + 1):
            try:
                return func()
            except Exception as e:
                if isinstance(e, anthropic.APIStatusError) and e.status_code not in (429, 529, 503):
                    raise
                if attempt == MAX_RETRIES:
                    raise
                delay = RETRY_DELAYS[attempt]
                time.sleep(delay)

    @staticmethod
    def _make_cached_system(system: str) -> list[dict]:
        """Wrap system prompt with cache_control for Anthropic prompt caching."""
        return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

    @staticmethod
    def _add_cache_to_tools(tools: list[dict]) -> list[dict]:
        """Add cache_control to the last tool definition for prompt caching."""
        if not tools:
            return tools
        tools = [dict(t) for t in tools]  # shallow copy
        tools[-1] = {**tools[-1], "cache_control": {"type": "ephemeral"}}
        return tools

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str,
        context_label: str = "chat",
    ) -> anthropic.types.Message:
        self._check_budget()
        model = self._pick_model(context_label)
        cached_system = self._make_cached_system(system)
        cached_tools = self._add_cache_to_tools(tools)
        response = self._call_with_retry(lambda: self.client.messages.create(
            model=model,
            max_tokens=self.max_tokens,
            system=cached_system,
            messages=messages,
            tools=cached_tools,
        ))
        self._track_usage(response, context_label)
        return response

    def simple_chat(
        self,
        messages: list[dict],
        system: str,
        context_label: str = "chat",
    ) -> anthropic.types.Message:
        self._check_budget()
        model = self._pick_model(context_label)
        cached_system = self._make_cached_system(system)
        response = self._call_with_retry(lambda: self.client.messages.create(
            model=model,
            max_tokens=self.max_tokens,
            system=cached_system,
            messages=messages,
        ))
        self._track_usage(response, context_label)
        return response

    def stream_response(
        self,
        messages: list[dict],
        system: str,
        context_label: str = "chat",
    ) -> Iterator[str]:
        self._check_budget()
        model = self._pick_model(context_label)
        cached_system = self._make_cached_system(system)
        with self.client.messages.stream(
            model=model,
            max_tokens=self.max_tokens,
            system=cached_system,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text
            # Track after stream completes
            response = stream.get_final_message()
            self._track_usage(response, context_label)

    def _track_usage(self, response: anthropic.types.Message, context_label: str):
        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_write_tokens=getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
            cache_read_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            model=self.model,
            context=context_label,
        )
        self.token_tracker.record(usage)
