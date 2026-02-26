"""Main CLI entry point."""

import sys
import os
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich import print as rprint

from ..core.context import GitContext
from ..models.ota import OTALog
from ..utils.logger import Logger
from ..utils.config import Config
from ..utils.errors import GitContextError

console = Console()


@click.group()
@click.option('--repo', '-r', default='.', help='Path to git repository')
@click.option('--config', '-c', help='Path to config file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.version_option()
@click.pass_context
def cli(ctx, repo, config, verbose, debug):
    """GitContext - Git for AI context management.

    Track, version, and manage AI context, thoughts, and decisions alongside your code.
    """
    ctx.ensure_object(dict)

    # Setup logging
    if debug:
        Logger.setup_logger(debug=True)
    elif verbose:
        Logger.setup_logger(debug=True)

    # Load configuration
    config_obj = Config()
    if config:
        config_path = Path(config)
        if config_path.exists():
            config_obj = Config.load(config_path)

    # Override with command line options
    config_obj.verbose = verbose
    config_obj.debug = debug

    try:
        ctx.obj['gc'] = GitContext(repo, config_obj)
    except Exception as e:
        Logger.error(f"Failed to initialize GitContext: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize GitContext in repository."""
    try:
        ctx.obj['gc'].init()
    except GitContextError as e:
        Logger.error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('name')
@click.option('--from', 'from_branch', help='Parent branch')
@click.pass_context
def branch(ctx, name, from_branch):
    """Create a new context branch."""
    try:
        ctx.obj['gc'].branch(name, from_branch)
    except GitContextError as e:
        Logger.error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('branch')
@click.pass_context
def checkout(ctx, branch):
    """Switch to a context branch."""
    try:
        ctx.obj['gc'].checkout(branch)
    except GitContextError as e:
        Logger.error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('message')
@click.option('--ota-file', '-f', help='JSON file with OTA logs')
@click.option('--decisions', '-d', help='Comma-separated list of decisions')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode')
@click.pass_context
def commit(ctx, message, ota_file, decisions, interactive):
    """Commit current context."""
    try:
        if interactive:
            message = Prompt.ask("Commit message", default=message)

            # Ask for decisions
            decisions_input = Prompt.ask(
                "Decisions (comma-separated, optional)",
                default=""
            )
            decisions_list = [d.strip() for d in decisions_input.split(',') if d.strip()]

            # Ask for OTA logs
            ota_logs = []
            if Confirm.ask("Record OTA logs?"):
                while True:
                    console.print("\n[bold]OTA Log Entry[/bold]")
                    thought = Prompt.ask("  Thought")
                    action = Prompt.ask("  Action")
                    result = Prompt.ask("  Result")
                    files = Prompt.ask("  Files affected (comma-separated)", default="")

                    ota_logs.append(OTALog(
                        thought=thought,
                        action=action,
                        result=result,
                        files_affected=[f.strip() for f in files.split(',') if f.strip()]
                    ))

                    if not Confirm.ask("Add another?"):
                        break

            ctx.obj['gc'].commit(message, ota_logs, decisions_list)
        else:
            # Load OTA logs if provided
            ota_logs = []
            if ota_file:
                import json
                from datetime import datetime
                with open(ota_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        if 'timestamp' in item and isinstance(item['timestamp'], str):
                            item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                        ota_logs.append(OTALog(**item))

            # Parse decisions
            decisions_list = []
            if decisions:
                decisions_list = [d.strip() for d in decisions.split(',')]

            ctx.obj['gc'].commit(message, ota_logs, decisions_list)

    except GitContextError as e:
        Logger.error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('branch')
@click.option('--no-squash', is_flag=True, help='Merge without squashing')
@click.pass_context
def merge(ctx, branch, no_squash):
    """Merge a branch into current branch."""
    try:
        result = ctx.obj['gc'].merge(branch, squash=not no_squash)

        if not no_squash:
            console.print("\n[bold green]📊 Squash Summary[/bold green]")

            table = Table(show_header=False, box=None)
            table.add_column("Key", style="cyan")
            table.add_column("Value")
            table.add_row("Decisions", str(len(result.decisions)))
            table.add_row("Rejected", str(len(result.rejected_alternatives)))
            table.add_row("Insights", str(len(result.key_insights)))
            table.add_row("Original commits", str(result.original_commits))
            console.print(table)

            if result.decisions:
                console.print("\n[bold]Final Decisions:[/bold]")
                for d in result.decisions[:3]:
                    console.print(f"  • {d}")
                if len(result.decisions) > 3:
                    console.print(f"  ... and {len(result.decisions) - 3} more")

    except GitContextError as e:
        Logger.error(str(e))
        sys.exit(1)


@cli.command()
@click.option('--branch', '-b', help='Branch to show logs from')
@click.option('--limit', '-n', default=10, help='Number of commits to show')
@click.option('--format', '-f', type=click.Choice(['pretty', 'json', 'oneline']), default='pretty')
@click.pass_context
def log(ctx, branch, limit, format):
    """Show commit history."""
    try:
        commits = ctx.obj['gc'].log(branch, limit)

        if not commits:
            console.print("No commits found")
            return

        if format == 'json':
            import json
            console.print(json.dumps([c.to_dict() for c in commits], indent=2))
        elif format == 'oneline':
            for commit in reversed(commits):
                time_str = commit.timestamp.strftime("%Y-%m-%d %H:%M")
                console.print(f"[cyan]{commit.short_id()}[/cyan] {time_str} - {commit.message}")
        else:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Commit", style="cyan")
            table.add_column("Date")
            table.add_column("Message")
            table.add_column("Details")

            for commit in reversed(commits):
                time_str = commit.timestamp.strftime("%Y-%m-%d %H:%M")
                details = []
                if commit.decisions:
                    details.append(f"📝 {len(commit.decisions)}")
                if commit.ota_logs:
                    details.append(f"🤖 {len(commit.ota_logs)}")

                table.add_row(
                    commit.short_id(),
                    time_str,
                    commit.message,
                    " ".join(details)
                )

            console.print(table)

    except GitContextError as e:
        Logger.error(str(e))
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show current status."""
    try:
        status = ctx.obj['gc'].status()

        console.print(f"\n[bold]On branch:[/bold] [green]{status['current_branch']}[/green]")
        console.print(f"Commits: {status['commits']}")

        if status['latest_commit']:
            console.print(f"Latest: [cyan]{status['latest_commit_id']}[/cyan] - {status['latest_commit']}")

        if status.get('pending_ota_logs', 0):
            console.print(f"[yellow]⚠ {status['pending_ota_logs']} pending OTA logs[/yellow]")

        if status['uncommitted_changes']:
            console.print("[yellow]⚠ Uncommitted changes[/yellow]")

        if len(status['all_branches']) > 1:
            console.print("\n[bold]Branches:[/bold]")
            for b in status['all_branches']:
                marker = "*" if b == status['current_branch'] else " "
                console.print(f"  {marker} {b}")

    except GitContextError as e:
        Logger.error(str(e))
        sys.exit(1)


@cli.command()
@click.option('--thought', '-t', help='What you were thinking')
@click.option('--action', '-a', help='What you did')
@click.option('--result', '-r', help='What happened')
@click.option('--files', '-f', help='Comma-separated list of affected files')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode')
@click.pass_context
def ota(ctx, thought, action, result, files, interactive):
    """Record an OTA (thought process) log."""
    try:
        if interactive or not all([thought, action, result]):
            console.print("[bold]OTA Log Recording[/bold]")
            thought = Prompt.ask("Thought", default=thought or "")
            action = Prompt.ask("Action", default=action or "")
            result = Prompt.ask("Result", default=result or "")
            files_input = Prompt.ask("Files affected (comma-separated)", default=files or "")
            files_list = [f.strip() for f in files_input.split(',') if f.strip()]
        else:
            files_list = [f.strip() for f in (files or '').split(',') if f.strip()]

        log = OTALog(
            thought=thought,
            action=action,
            result=result,
            files_affected=files_list
        )

        # Save to temp file
        temp_path = ctx.obj['gc'].storage.create_temp_file(
            [log.to_dict()],
            suffix='.json'
        )

        Logger.success(f"OTA log saved to {temp_path}")

        # Ask if user wants to commit now
        if Confirm.ask("Commit now?"):
            ctx.invoke(commit, message="WIP", ota_file=str(temp_path))

    except GitContextError as e:
        Logger.error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('branch')
@click.option('--force', '-f', is_flag=True, help='Force delete')
@click.pass_context
def branch_delete(ctx, branch, force):
    """Delete a branch."""
    try:
        if not force:
            if not Confirm.ask(f"Delete branch '{branch}'?"):
                return

        ctx.obj['gc'].index.delete_branch(branch)
        ctx.obj['gc'].storage.delete("contexts", "branches", branch)
        Logger.success(f"Deleted branch: {branch}")

    except GitContextError as e:
        Logger.error(str(e))
        sys.exit(1)


@cli.command()
@click.option('--hours', default=24, help='Max age in hours')
@click.pass_context
def cleanup(ctx, hours):
    """Clean up temporary files."""
    try:
        count = ctx.obj['gc'].storage.cleanup_temp(hours)
        Logger.success(f"Cleaned up {count} temporary files")
    except GitContextError as e:
        Logger.error(str(e))
        sys.exit(1)


@cli.command()
@click.pass_context
def config(ctx):
    """Show current configuration."""
    config = ctx.obj['gc'].config

    table = Table(show_header=True, header_style="bold")
    table.add_column("Section")
    table.add_column("Key")
    table.add_column("Value")

    # LLM config
    table.add_row("llm", "provider", config.llm.provider)
    table.add_row("llm", "model", config.llm.model or "default")
    table.add_row("llm", "temperature", str(config.llm.temperature))
    table.add_row("llm", "max_tokens", str(config.llm.max_tokens))

    # Storage config
    table.add_row("storage", "context_dir", config.storage.context_dir)
    table.add_row("storage", "max_history", str(config.storage.max_history))
    table.add_row("storage", "compress_archive", str(config.storage.compress_archive))

    # Git config
    table.add_row("git", "auto_commit", str(config.git.auto_commit))
    table.add_row("git", "auto_push", str(config.git.auto_push))
    table.add_row("git", "remote_name", config.git.remote_name)

    console.print(table)


def main():
    """Main entry point."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)
    except Exception as e:
        Logger.error(f"Unexpected error: {e}")
        if Logger._debug_mode:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
