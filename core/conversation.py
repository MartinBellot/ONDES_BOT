from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

from config.prompts import get_system_prompt
from core.claude_client import ClaudeClient
from core.memory import Memory
from core.tool_registry import ToolRegistry


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
        self.max_history = 50

    def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        self._trim_history()

        system = self._build_system_prompt()

        # Smart tool routing: only send relevant tools based on user message
        tools = self.tools.get_tools_for_message(user_message)

        spinner = self.console.status("[bold yellow]Réflexion...[/]")
        spinner.start()

        try:
            if tools:
                response = self.client.chat_with_tools(
                    messages=self.history,
                    tools=tools,
                    system=system,
                )
            else:
                # Pure conversation — no tools needed, cheaper call
                response = self.client.simple_chat(
                    messages=self.history,
                    system=system,
                )

            # Tool use loop
            while response.stop_reason == "tool_use":
                spinner.stop()
                tool_results = self._execute_tools(response)
                self.history.append({"role": "assistant", "content": response.content})
                self.history.append({"role": "user", "content": tool_results})
                spinner.start()
                # In tool loop, keep using full tool set to allow follow-up calls
                response = self.client.chat_with_tools(
                    messages=self.history,
                    tools=tools or self.tools.get_all_tools(),
                    system=system,
                )
        finally:
            spinner.stop()

        # Extract text response
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        self.history.append({"role": "assistant", "content": response.content})

        # Auto-extract facts in background (best effort)
        self._maybe_save_facts(user_message, text)

        return text

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

                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })
        return results

    def _ask_confirmation(self, tool_name: str, inputs: dict) -> bool:
        details = Table.grid(padding=(0, 2))
        details.add_column(style="bold")
        details.add_column()

        details.add_row("Action", tool_name)
        for key, value in inputs.items():
            display_value = str(value)
            if len(display_value) > 100:
                display_value = display_value[:100] + "..."
            details.add_row(key, display_value)

        self.console.print(Panel(
            details,
            title="[bold yellow]⚠️  CONFIRMATION REQUISE[/]",
            border_style="yellow",
        ))

        return Confirm.ask("[bold]Confirmer cette action ?[/]", console=self.console)

    def _build_system_prompt(self) -> str:
        facts = self.memory.get_relevant_facts()
        return get_system_prompt(facts)

    def _trim_history(self):
        if len(self.history) > self.max_history:
            # Keep the first message and trim the oldest ones
            self.history = self.history[-self.max_history:]

    def _maybe_save_facts(self, user_msg: str, bot_response: str):
        """Best-effort fact extraction — silent failures OK."""
        try:
            # Simple heuristic: if the user mentions names, projects, preferences
            # we let Claude extract them on the next available cycle
            pass
        except Exception:
            pass

    def clear_history(self):
        self.history.clear()
