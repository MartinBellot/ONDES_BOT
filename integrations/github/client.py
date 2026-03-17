"""GitHub integration — repos, issues, PRs, actions, notifications via gh CLI."""

import json
import subprocess
import shutil


def _run(args: list[str], timeout: int = 15) -> tuple[str, str, int]:
    """Run a gh CLI command and return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout dépassé", 1
    except FileNotFoundError:
        return "", "GitHub CLI (gh) n'est pas installé. Installe-le avec: brew install gh", 127


class GitHubClient:
    """GitHub integration via the official gh CLI (no API token config needed)."""

    def __init__(self):
        self._gh = shutil.which("gh")

    def is_available(self) -> bool:
        """Check if gh CLI is installed and authenticated."""
        if not self._gh:
            return False
        _, _, rc = _run(["gh", "auth", "status"], timeout=5)
        return rc == 0

    # ═══════════════════════════ REPOS ═══════════════════════════

    def list_repos(self, limit: int = 10, sort: str = "updated") -> str:
        """List user's repos."""
        stdout, stderr, rc = _run([
            "gh", "repo", "list", "--limit", str(limit),
            "--sort", sort, "--json", "name,description,visibility,updatedAt,primaryLanguage",
        ])
        if rc != 0:
            return f"Erreur: {stderr}"

        try:
            repos = json.loads(stdout)
        except json.JSONDecodeError:
            return f"Erreur parsing: {stdout[:200]}"

        if not repos:
            return "Aucun repo trouvé."

        lines = []
        for r in repos:
            vis = "🔒" if r.get("visibility") == "PRIVATE" else "🌐"
            lang = r.get("primaryLanguage", {})
            lang_str = f" [{lang.get('name', '')}]" if lang else ""
            desc = r.get("description", "") or ""
            desc_short = f" — {desc[:60]}" if desc else ""
            lines.append(f"{vis} **{r['name']}**{lang_str}{desc_short}")

        return "\n".join(lines)

    def repo_info(self, repo: str) -> str:
        """Get detailed info about a repo (owner/repo or just repo for current user)."""
        stdout, stderr, rc = _run([
            "gh", "repo", "view", repo, "--json",
            "name,description,url,stargazerCount,forkCount,primaryLanguage,defaultBranchRef,isPrivate,createdAt",
        ])
        if rc != 0:
            return f"Erreur: {stderr}"

        try:
            r = json.loads(stdout)
        except json.JSONDecodeError:
            return f"Erreur parsing: {stdout[:200]}"

        lang = r.get("primaryLanguage", {})
        branch = r.get("defaultBranchRef", {})
        return (
            f"**{r.get('name', '?')}**\n"
            f"  URL: {r.get('url', '?')}\n"
            f"  Description: {r.get('description', '—')}\n"
            f"  Langage: {lang.get('name', '?') if lang else '?'}\n"
            f"  Branche par défaut: {branch.get('name', '?') if branch else '?'}\n"
            f"  ⭐ {r.get('stargazerCount', 0)} | 🍴 {r.get('forkCount', 0)}\n"
            f"  Visibilité: {'Privé' if r.get('isPrivate') else 'Public'}"
        )

    def clone_repo(self, repo: str, directory: str | None = None) -> str:
        """Clone a repo."""
        cmd = ["gh", "repo", "clone", repo]
        if directory:
            cmd.append(directory)
        stdout, stderr, rc = _run(cmd, timeout=120)
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"✅ Repo **{repo}** cloné. {stdout}"

    # ═══════════════════════════ ISSUES ═══════════════════════════

    def list_issues(self, repo: str | None = None, state: str = "open", limit: int = 10) -> str:
        """List issues for a repo."""
        cmd = ["gh", "issue", "list", "--state", state, "--limit", str(limit),
               "--json", "number,title,state,author,labels,createdAt,assignees"]
        if repo:
            cmd.extend(["-R", repo])

        stdout, stderr, rc = _run(cmd)
        if rc != 0:
            return f"Erreur: {stderr}"

        try:
            issues = json.loads(stdout)
        except json.JSONDecodeError:
            return f"Erreur parsing: {stdout[:200]}"

        if not issues:
            return f"Aucune issue ({state})."

        lines = []
        for i in issues:
            labels = ", ".join(l.get("name", "") for l in i.get("labels", []))
            label_str = f" [{labels}]" if labels else ""
            state_emoji = "🟢" if i.get("state") == "OPEN" else "🟣"
            author = i.get("author", {}).get("login", "?")
            lines.append(f"{state_emoji} #{i['number']} **{i['title']}**{label_str} — @{author}")

        return "\n".join(lines)

    def create_issue(self, title: str, body: str = "", repo: str | None = None, labels: str = "") -> str:
        """Create a new issue."""
        cmd = ["gh", "issue", "create", "--title", title]
        if body:
            cmd.extend(["--body", body])
        if repo:
            cmd.extend(["-R", repo])
        if labels:
            cmd.extend(["--label", labels])

        stdout, stderr, rc = _run(cmd)
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"✅ Issue créée: {stdout}"

    def close_issue(self, issue_number: int, repo: str | None = None) -> str:
        """Close an issue."""
        cmd = ["gh", "issue", "close", str(issue_number)]
        if repo:
            cmd.extend(["-R", repo])

        _, stderr, rc = _run(cmd)
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"✅ Issue #{issue_number} fermée."

    def view_issue(self, issue_number: int, repo: str | None = None) -> str:
        """View issue details."""
        cmd = ["gh", "issue", "view", str(issue_number),
               "--json", "number,title,body,state,author,labels,assignees,comments,createdAt"]
        if repo:
            cmd.extend(["-R", repo])

        stdout, stderr, rc = _run(cmd)
        if rc != 0:
            return f"Erreur: {stderr}"

        try:
            i = json.loads(stdout)
        except json.JSONDecodeError:
            return f"Erreur parsing: {stdout[:200]}"

        labels = ", ".join(l.get("name", "") for l in i.get("labels", []))
        assignees = ", ".join(a.get("login", "") for a in i.get("assignees", []))
        comments = i.get("comments", [])
        comment_str = ""
        for c in comments[:5]:
            author = c.get("author", {}).get("login", "?")
            body = c.get("body", "")[:200]
            comment_str += f"\n  💬 @{author}: {body}"

        return (
            f"**#{i['number']} {i['title']}**\n"
            f"  État: {i.get('state', '?')} | Auteur: @{i.get('author', {}).get('login', '?')}\n"
            f"  Labels: {labels or '—'} | Assignés: {assignees or '—'}\n\n"
            f"  {i.get('body', '—')[:500]}"
            f"{comment_str}"
        )

    # ═══════════════════════════ PULL REQUESTS ═══════════════════════════

    def list_prs(self, repo: str | None = None, state: str = "open", limit: int = 10) -> str:
        """List pull requests."""
        cmd = ["gh", "pr", "list", "--state", state, "--limit", str(limit),
               "--json", "number,title,state,author,headRefName,baseRefName,isDraft,reviewDecision"]
        if repo:
            cmd.extend(["-R", repo])

        stdout, stderr, rc = _run(cmd)
        if rc != 0:
            return f"Erreur: {stderr}"

        try:
            prs = json.loads(stdout)
        except json.JSONDecodeError:
            return f"Erreur parsing: {stdout[:200]}"

        if not prs:
            return f"Aucune PR ({state})."

        lines = []
        for pr in prs:
            draft = " 📝 DRAFT" if pr.get("isDraft") else ""
            review = pr.get("reviewDecision", "")
            review_emoji = {"APPROVED": " ✅", "CHANGES_REQUESTED": " ❌", "REVIEW_REQUIRED": " 🔍"}.get(review, "")
            author = pr.get("author", {}).get("login", "?")
            branch = f"{pr.get('headRefName', '?')} → {pr.get('baseRefName', '?')}"
            lines.append(f"🔀 #{pr['number']} **{pr['title']}**{draft}{review_emoji}\n   {branch} — @{author}")

        return "\n".join(lines)

    def create_pr(self, title: str, body: str = "", base: str = "main", repo: str | None = None) -> str:
        """Create a pull request from current branch."""
        cmd = ["gh", "pr", "create", "--title", title, "--base", base]
        if body:
            cmd.extend(["--body", body])
        if repo:
            cmd.extend(["-R", repo])

        stdout, stderr, rc = _run(cmd)
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"✅ PR créée: {stdout}"

    def view_pr(self, pr_number: int, repo: str | None = None) -> str:
        """View PR details with diff stats."""
        cmd = ["gh", "pr", "view", str(pr_number),
               "--json", "number,title,body,state,author,headRefName,baseRefName,files,reviewDecision,additions,deletions"]
        if repo:
            cmd.extend(["-R", repo])

        stdout, stderr, rc = _run(cmd)
        if rc != 0:
            return f"Erreur: {stderr}"

        try:
            pr = json.loads(stdout)
        except json.JSONDecodeError:
            return f"Erreur parsing: {stdout[:200]}"

        files = pr.get("files", [])
        file_summary = "\n".join(f"  {f.get('path', '?')} (+{f.get('additions', 0)}/-{f.get('deletions', 0)})" for f in files[:15])

        return (
            f"**#{pr['number']} {pr['title']}**\n"
            f"  {pr.get('headRefName', '?')} → {pr.get('baseRefName', '?')}\n"
            f"  État: {pr.get('state', '?')} | Review: {pr.get('reviewDecision', '—')}\n"
            f"  +{pr.get('additions', 0)} / -{pr.get('deletions', 0)}\n\n"
            f"  {pr.get('body', '—')[:300]}\n\n"
            f"  **Fichiers modifiés:**\n{file_summary}"
        )

    def merge_pr(self, pr_number: int, method: str = "squash", repo: str | None = None) -> str:
        """Merge a pull request."""
        cmd = ["gh", "pr", "merge", str(pr_number), f"--{method}"]
        if repo:
            cmd.extend(["-R", repo])

        _, stderr, rc = _run(cmd)
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"✅ PR #{pr_number} mergée ({method})."

    # ═══════════════════════════ ACTIONS / CI ═══════════════════════════

    def list_runs(self, repo: str | None = None, limit: int = 5) -> str:
        """List recent GitHub Actions workflow runs."""
        cmd = ["gh", "run", "list", "--limit", str(limit),
               "--json", "databaseId,displayTitle,status,conclusion,workflowName,headBranch,createdAt"]
        if repo:
            cmd.extend(["-R", repo])

        stdout, stderr, rc = _run(cmd)
        if rc != 0:
            return f"Erreur: {stderr}"

        try:
            runs = json.loads(stdout)
        except json.JSONDecodeError:
            return f"Erreur parsing: {stdout[:200]}"

        if not runs:
            return "Aucun run trouvé."

        lines = []
        for r in runs:
            status = r.get("conclusion") or r.get("status", "?")
            emoji = {"success": "✅", "failure": "❌", "in_progress": "🔄", "cancelled": "⛔"}.get(status, "⏳")
            lines.append(
                f"{emoji} **{r.get('displayTitle', '?')}**\n"
                f"   Workflow: {r.get('workflowName', '?')} | Branche: {r.get('headBranch', '?')} | ID: {r.get('databaseId', '?')}"
            )

        return "\n\n".join(lines)

    def view_run(self, run_id: int, repo: str | None = None) -> str:
        """View a specific workflow run (jobs + logs)."""
        cmd = ["gh", "run", "view", str(run_id), "--json",
               "databaseId,displayTitle,status,conclusion,jobs,workflowName"]
        if repo:
            cmd.extend(["-R", repo])

        stdout, stderr, rc = _run(cmd)
        if rc != 0:
            return f"Erreur: {stderr}"

        try:
            run = json.loads(stdout)
        except json.JSONDecodeError:
            return f"Erreur parsing: {stdout[:200]}"

        jobs = run.get("jobs", [])
        job_lines = []
        for j in jobs:
            status = j.get("conclusion") or j.get("status", "?")
            emoji = {"success": "✅", "failure": "❌", "in_progress": "🔄"}.get(status, "⏳")
            job_lines.append(f"  {emoji} {j.get('name', '?')} — {status}")

        return (
            f"**{run.get('displayTitle', '?')}**\n"
            f"  Workflow: {run.get('workflowName', '?')}\n"
            f"  Status: {run.get('conclusion') or run.get('status', '?')}\n\n"
            f"  **Jobs:**\n" + "\n".join(job_lines)
        )

    # ═══════════════════════════ NOTIFICATIONS ═══════════════════════════

    def notifications(self, limit: int = 10) -> str:
        """Get GitHub notifications summary."""
        stdout, stderr, rc = _run([
            "gh", "api", "/notifications", "--jq",
            f'.[:{ limit}] | .[] | "\\(.subject.type): \\(.subject.title) [\\(.repository.full_name)]"',
        ])
        if rc != 0:
            return f"Erreur: {stderr}"
        return stdout if stdout else "Aucune notification."

    # ═══════════════════════════ GIT LOCAL ═══════════════════════════

    def git_status(self, path: str | None = None) -> str:
        """Get git status of current or specified directory."""
        cmd = ["git", "status", "--short"]
        kwargs = {}
        if path:
            kwargs["cwd"] = path
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, **kwargs)
            if result.returncode != 0:
                return f"Erreur: {result.stderr}"
            status = result.stdout.strip()

            # Also get branch info
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=5, **kwargs,
            )
            branch_name = branch.stdout.strip() or "?"

            if not status:
                return f"🌿 Branche: **{branch_name}** — Rien à committer, working tree clean."
            return f"🌿 Branche: **{branch_name}**\n\n{status}"
        except Exception as e:
            return f"Erreur: {e}"

    def git_diff(self, path: str | None = None, staged: bool = False) -> str:
        """Get git diff (staged or unstaged)."""
        cmd = ["git", "diff", "--stat"]
        if staged:
            cmd.append("--staged")
        kwargs = {}
        if path:
            kwargs["cwd"] = path
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, **kwargs)
            if result.returncode != 0:
                return f"Erreur: {result.stderr}"
            return result.stdout.strip()[:2000] if result.stdout.strip() else "Aucune différence."
        except Exception as e:
            return f"Erreur: {e}"
