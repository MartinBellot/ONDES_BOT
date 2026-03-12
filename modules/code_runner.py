import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    code: str


class PythonCodeRunner:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def execute(self, code: str, input_data: str = "") -> str:
        work_dir = Path(tempfile.mkdtemp(prefix="nietz_run_"))
        script_file = work_dir / "script.py"
        script_file.write_text(code, encoding="utf-8")

        start_time = time.perf_counter()

        try:
            result = subprocess.run(
                ["python3", str(script_file)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(work_dir),
                input=input_data if input_data else None,
                env={
                    **os.environ,
                    "PYTHONPATH": "",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )

            execution_time = time.perf_counter() - start_time

            er = ExecutionResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                execution_time=execution_time,
                code=code,
            )

        except subprocess.TimeoutExpired:
            execution_time = time.perf_counter() - start_time
            er = ExecutionResult(
                stdout="",
                stderr=f"⏰ Timeout: l'exécution a dépassé {self.timeout} secondes.",
                exit_code=-1,
                execution_time=execution_time,
                code=code,
            )

        return self._format_result(er)

    def _format_result(self, result: ExecutionResult) -> str:
        parts = []
        status = "✅ Succès" if result.exit_code == 0 else f"❌ Erreur (code {result.exit_code})"
        parts.append(f"**{status}** · {result.execution_time:.2f}s")

        if result.stdout:
            parts.append(f"\n**Sortie:**\n```\n{result.stdout.rstrip()}\n```")

        if result.stderr:
            parts.append(f"\n**Erreurs:**\n```\n{result.stderr.rstrip()}\n```")

        return "\n".join(parts)
