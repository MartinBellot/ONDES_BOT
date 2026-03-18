from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm
from rich.live import Live
from rich.text import Text

from config.prompts import get_system_prompt
from core.claude_client import ClaudeClient
from core.memory import Memory
from core.tool_registry import ToolRegistry
from ui.themes import C, BORDERS, BOX

# Maximum chars for a single tool result kept in history
TOOL_RESULT_MAX_CHARS = 1500
# Token budget for conversation history (1 token ≈ 4 chars)
MAX_HISTORY_TOKENS = 30_000
# Number of messages before triggering a summarization
SUMMARIZE_THRESHOLD = 16


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token ≈ 4 chars for French/English mixed text."""
    return len(text) // 4


def _message_text(msg: dict) -> str:
    """Extract text from a message dict for token estimation."""
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", "") or block.get("content", ""))
            elif hasattr(block, "text"):
                parts.append(block.text)
        return " ".join(parts)
    return str(content)


def _truncate_tool_result(result: str) -> str:
    """Truncate a large tool result, keeping head + tail for context."""
    if len(result) <= TOOL_RESULT_MAX_CHARS:
        return result
    head_size = TOOL_RESULT_MAX_CHARS * 2 // 3
    tail_size = TOOL_RESULT_MAX_CHARS // 3
    truncated_chars = len(result) - head_size - tail_size
    return (
        result[:head_size]
        + f"\n\n[...{truncated_chars} caractères tronqués...]\n\n"
        + result[-tail_size:]
    )


class ConversationManager:
    def __init__(
        self,
        claude_client: ClaudeClient,
        tool_registry: ToolRegistry,
        memory: Memory,
        console: Console,
    ):
        self.client = claude_client
        self.tools = tool_registry
        self.memory = memory
        self.console = console
        self.history: list[dict] = []
        self._cached_facts: str | None = None
        self._facts_dirty = True  # Force first load
        self._summary_prefix: str = ""  # Summarized old conversation

    def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        self._trim_history()

        system = self._build_system_prompt()

        # Smart tool routing: only send relevant tools based on user message
        tools = self.tools.get_tools_for_message(user_message)

        tools_used: list[str] = []
        thinking_live = Live(
            self._render_thinking("Réflexion en cours", tools_used),
            console=self.console,
            refresh_per_second=4,
            transient=True,  # Disappears when stopped
        )
        thinking_live.start()

        try:
            if tools:
                response = self.client.chat_with_tools(
                    messages=self._get_messages_for_api(),
                    tools=tools,
                    system=system,
                )
            else:
                # Pure conversation — no tools needed, cheaper call
                response = self.client.simple_chat(
                    messages=self._get_messages_for_api(),
                    system=system,
                )

            # Tool use loop
            while response.stop_reason == "tool_use":
                # Collect tool names being used
                for block in response.content:
                    if block.type == "tool_use":
                        tools_used.append(block.name)
                thinking_live.update(self._render_thinking("Utilisation d'outils", tools_used))

                thinking_live.stop()
                tool_results = self._execute_tools(response)
                self.history.append({"role": "assistant", "content": response.content})
                self.history.append({"role": "user", "content": tool_results})
                thinking_live.start()
                thinking_live.update(self._render_thinking("Analyse des résultats", tools_used))

                # In tool loop, keep using full tool set to allow follow-up calls
                response = self.client.chat_with_tools(
                    messages=self._get_messages_for_api(),
                    tools=tools or self.tools.get_all_tools(),
                    system=system,
                )
        finally:
            thinking_live.stop()

        # Extract text response
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        self.history.append({"role": "assistant", "content": response.content})

        # Summarize old history if it's getting too long
        self._maybe_summarize()

        return text

    def _get_messages_for_api(self) -> list[dict]:
        """Build the messages list, prepending summary as context if available."""
        if self._summary_prefix:
            summary_msg = {
                "role": "user",
                "content": f"[Résumé de la conversation précédente]\n{self._summary_prefix}",
            }
            ack_msg = {
                "role": "assistant",
                "content": "Compris, j'ai le contexte de notre conversation précédente.",
            }
            return [summary_msg, ack_msg] + self.history
        return self.history

    def _execute_tools(self, response) -> list[dict]:
        import asyncio

        results = []
        for block in response.content:
            if block.type == "tool_use":
                # Check if confirmation needed
                if self.tools.requires_confirmation(block.name):
                    confirmed = self._ask_confirmation(block.name, block.input)
                    if not confirmed:
                        results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Action annulée par l'utilisateur.",
                        })
                        continue

                # Execute the tool
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            result = pool.submit(
                                asyncio.run, self.tools.execute(block.name, block.input)
                            ).result()
                    else:
                        result = asyncio.run(self.tools.execute(block.name, block.input))
                except RuntimeError:
                    result = asyncio.run(self.tools.execute(block.name, block.input))

                self.memory.log_action(block.name, str(block.input), str(result))

                # Truncate large tool results before storing in history
                truncated = _truncate_tool_result(str(result))

                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": truncated,
                })
        return results

    def _ask_confirmation(self, tool_name: str, inputs: dict) -> bool:
        details = Table.grid(padding=(0, 2))
        details.add_column(style=f"bold {C['text_dim']}")
        details.add_column()

        details.add_row("Action", f"[{C['amber']}]{tool_name}[/]")
        for key, value in inputs.items():
            display_value = str(value)
            if key != "body" and len(display_value) > 100:
                display_value = display_value[:100] + "..."
            details.add_row(key, f"[{C['text']}]{display_value}[/]")

        self.console.print(Panel(
            details,
            title=f"[bold {C['amber']}]⚠️  CONFIRMATION REQUISE[/]",
            border_style=BORDERS["confirm"],
            box=BOX,
            padding=(1, 2),
        ))

        return Confirm.ask(f"[bold {C['text']}]Confirmer cette action ?[/]", console=self.console)

    @staticmethod
    def _render_thinking(message: str, tools_used: list[str] | None = None) -> Panel:
        """Render the ephemeral thinking/reflection panel."""
        content = Text()
        content.append(f"  {message}", style=f"italic {C['pink']}")
        content.append(" ···", style=f"bold {C['pink_dim']}")

        if tools_used:
            content.append("\n")
            for tool in tools_used:
                content.append(f"\n  ⚡ ", style=C["amber"])
                content.append(tool, style=C["text_dim"])

        return Panel(
            content,
            title=f"[{C['pink']}]💭 RÉFLEXION[/]",
            title_align="left",
            border_style=BORDERS["thinking"],
            box=BOX,
            padding=(0, 1),
        )

    def _build_system_prompt(self) -> str:
        facts = self._get_cached_facts()
        return get_system_prompt(facts)

    def _get_cached_facts(self) -> str:
        """Return cached memory facts, refreshing only when dirty."""
        if self._facts_dirty or self._cached_facts is None:
            self._cached_facts = self.memory.get_relevant_facts()
            self._facts_dirty = False
        return self._cached_facts

    def invalidate_facts_cache(self):
        """Call this when a fact is saved/deleted to force reload."""
        self._facts_dirty = True

    def _trim_history(self):
        """Token-aware history trimming: keep under MAX_HISTORY_TOKENS."""
        total = sum(_estimate_tokens(_message_text(m)) for m in self.history)
        while total > MAX_HISTORY_TOKENS and len(self.history) > 2:
            removed = self.history.pop(0)
            total -= _estimate_tokens(_message_text(removed))

    def _maybe_summarize(self):
        """Summarize oldest messages when history gets long, compressing context."""
        if len(self.history) < SUMMARIZE_THRESHOLD:
            return

        # Take the first half of history to summarize
        split = len(self.history) // 2
        # Ensure split is on an even boundary (keep user/assistant pairs)
        if split % 2 != 0:
            split += 1

        old_messages = self.history[:split]
        old_text_parts = []
        for msg in old_messages:
            role = msg["role"]
            text = _message_text(msg)
            if text:
                old_text_parts.append(f"{role}: {text[:300]}")

        old_text = "\n".join(old_text_parts)

        # Build summary via a cheap API call
        try:
            summary_response = self.client.simple_chat(
                messages=[{
                    "role": "user",
                    "content": (
                        "Résume cette conversation en 3-5 phrases concises. "
                        "Garde les faits clés, décisions, et résultats d'actions. "
                        "Ne garde pas les détails techniques des résultats d'outils.\n\n"
                        f"{old_text[:3000]}"
                    ),
                }],
                system="Tu es un assistant qui résume des conversations. Sois très concis.",
                context_label="summarize",
            )
            summary = summary_response.content[0].text

            # Save summary in memory for persistence
            topics = [msg.get("role", "") for msg in old_messages[:3]]
            self.memory.save_conversation_summary(summary, topics)

            # Replace old history with summary prefix
            if self._summary_prefix:
                self._summary_prefix += "\n" + summary
            else:
                self._summary_prefix = summary

            # Keep only the recent half
            self.history = self.history[split:]
        except Exception:
            # If summarization fails, just trim by count as fallback
            if len(self.history) > 30:
                self.history = self.history[-30:]

    def clear_history(self):
        self.history.clear()
        self._summary_prefix = ""
        self.tools._active_groups.clear()
