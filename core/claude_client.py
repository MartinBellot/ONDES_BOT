import time

import anthropic
from typing import Iterator

from config.settings import Settings
from core.token_tracker import TokenTracker, TokenUsage

MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 10]


class ClaudeClient:
    def __init__(self, settings: Settings, token_tracker: TokenTracker):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.max_tokens = settings.claude_max_tokens
        self.token_tracker = token_tracker

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

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str,
        context_label: str = "chat",
    ) -> anthropic.types.Message:
        response = self._call_with_retry(lambda: self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
            tools=tools,
        ))
        self._track_usage(response, context_label)
        return response

    def simple_chat(
        self,
        messages: list[dict],
        system: str,
        context_label: str = "chat",
    ) -> anthropic.types.Message:
        response = self._call_with_retry(lambda: self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
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
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
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
