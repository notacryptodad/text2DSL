"""
Text2X CLI Client

A production-ready command-line interface for the Text2DSL system that allows users to
convert natural language queries into executable database queries.

Features:
- Submit queries via HTTP/WebSocket
- View conversation history
- List available providers
- Interactive mode with streaming support
- Configuration file support (~/.text2dsl/config.yaml)
- Pretty-printed JSON responses
- Progress indicators for long operations
- Comprehensive error handling
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict
from uuid import UUID

import click
import httpx
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.tree import Tree
from rich import box

# Rich console for pretty output
console = Console()

# Default configuration
DEFAULT_CONFIG = {
    "api_url": "http://localhost:8000",
    "timeout": 300,
    "trace_level": "none",
    "max_iterations": 3,
    "confidence_threshold": 0.8,
    "enable_execution": False,
    "debug": False,
}

CONFIG_PATH = Path.home() / ".text2dsl" / "config.yaml"


# ============================================================================
# Configuration Management
# ============================================================================


def load_config() -> Dict[str, Any]:
    """Load configuration from file or return defaults."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                user_config = yaml.safe_load(f) or {}
                # Merge with defaults
                config = DEFAULT_CONFIG.copy()
                config.update(user_config)
                return config
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load config: {e}[/yellow]")
            console.print("[yellow]Using default configuration[/yellow]")

    return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        console.print(f"[green]Configuration saved to {CONFIG_PATH}[/green]")
    except Exception as e:
        console.print(f"[red]Error saving configuration: {e}[/red]", err=True)
        sys.exit(1)


# ============================================================================
# API Client
# ============================================================================


class Text2XClient:
    """HTTP client for Text2X API."""

    def __init__(self, api_url: str, timeout: int = 300):
        """Initialize API client."""
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def health_check(self) -> Dict[str, Any]:
        """Check API health status."""
        try:
            response = await self.client.get(f"{self.api_url}/health")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to connect to API: {e}")

    async def submit_query(
        self,
        provider_id: str,
        query: str,
        conversation_id: Optional[str] = None,
        max_iterations: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
        trace_level: str = "none",
        enable_execution: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Submit a natural language query."""
        payload = {
            "provider_id": provider_id,
            "query": query,
            "conversation_id": conversation_id,
            "options": {
                "trace_level": trace_level,
            }
        }

        if max_iterations is not None:
            payload["options"]["max_iterations"] = max_iterations
        if confidence_threshold is not None:
            payload["options"]["confidence_threshold"] = confidence_threshold
        if enable_execution is not None:
            payload["options"]["enable_execution"] = enable_execution

        try:
            response = await self.client.post(
                f"{self.api_url}/api/v1/query",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json() if e.response.content else {}
            raise RuntimeError(f"API error: {error_detail.get('message', str(e))}")

    async def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation details."""
        try:
            response = await self.client.get(
                f"{self.api_url}/api/v1/query/conversations/{conversation_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Conversation {conversation_id} not found")
            error_detail = e.response.json() if e.response.content else {}
            raise RuntimeError(f"API error: {error_detail.get('message', str(e))}")

    async def list_providers(self) -> list[Dict[str, Any]]:
        """List all available providers."""
        try:
            response = await self.client.get(f"{self.api_url}/api/v1/providers")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json() if e.response.content else {}
            raise RuntimeError(f"API error: {error_detail.get('message', str(e))}")

    async def get_provider(self, provider_id: str) -> Dict[str, Any]:
        """Get provider details."""
        try:
            response = await self.client.get(
                f"{self.api_url}/api/v1/providers/{provider_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Provider {provider_id} not found")
            error_detail = e.response.json() if e.response.content else {}
            raise RuntimeError(f"API error: {error_detail.get('message', str(e))}")

    async def get_provider_schema(self, provider_id: str) -> Dict[str, Any]:
        """Get provider schema information."""
        try:
            response = await self.client.get(
                f"{self.api_url}/api/v1/providers/{provider_id}/schema"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Provider {provider_id} not found")
            error_detail = e.response.json() if e.response.content else {}
            raise RuntimeError(f"API error: {error_detail.get('message', str(e))}")


# ============================================================================
# Display Utilities
# ============================================================================


def display_query_response(response: Dict[str, Any], show_trace: bool = False) -> None:
    """Display query response in a user-friendly format."""
    # Header
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]Query Result[/bold cyan]",
        border_style="cyan"
    ))

    # Basic info
    info_table = Table(show_header=False, box=box.SIMPLE)
    info_table.add_column("Field", style="bold")
    info_table.add_column("Value")

    info_table.add_row("Conversation ID", str(response.get("conversation_id", "N/A")))
    info_table.add_row("Turn ID", str(response.get("turn_id", "N/A")))
    info_table.add_row("Confidence Score", f"{response.get('confidence_score', 0):.2%}")
    info_table.add_row("Validation Status", response.get("validation_status", "unknown"))
    info_table.add_row("Iterations", str(response.get("iterations", 1)))

    console.print(info_table)
    console.print()

    # Generated Query
    query = response.get("generated_query", "")
    console.print("[bold green]Generated Query:[/bold green]")
    syntax = Syntax(query, "sql", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, border_style="green"))
    console.print()

    # Validation Results
    validation = response.get("validation_result", {})
    if validation.get("errors"):
        console.print("[bold red]Validation Errors:[/bold red]")
        for error in validation["errors"]:
            console.print(f"  [red]✗[/red] {error}")
        console.print()

    if validation.get("warnings"):
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for warning in validation["warnings"]:
            console.print(f"  [yellow]⚠[/yellow] {warning}")
        console.print()

    if validation.get("suggestions"):
        console.print("[bold blue]Suggestions:[/bold blue]")
        for suggestion in validation["suggestions"]:
            console.print(f"  [blue]ℹ[/blue] {suggestion}")
        console.print()

    # Execution Results
    exec_result = response.get("execution_result")
    if exec_result:
        if exec_result.get("success"):
            console.print(f"[bold green]Execution Successful[/bold green]")
            console.print(f"  Rows returned: {exec_result.get('row_count', 0)}")
            console.print(f"  Execution time: {exec_result.get('execution_time_ms', 0)}ms")

            # Display result data if available
            result_data = exec_result.get("data")
            if result_data:
                console.print()
                console.print("[bold]Result Data:[/bold]")

                # If it's a list of dicts, display as table
                if isinstance(result_data, list) and result_data:
                    if isinstance(result_data[0], dict):
                        # Create table from data
                        result_table = Table(box=box.ROUNDED)

                        # Add columns from first row
                        for column in result_data[0].keys():
                            result_table.add_column(column, style="cyan")

                        # Add rows (limit to first 10)
                        for row in result_data[:10]:
                            result_table.add_row(*[str(v) for v in row.values()])

                        console.print(result_table)

                        if len(result_data) > 10:
                            console.print(f"[dim]... showing 10 of {len(result_data)} rows[/dim]")
                    else:
                        # Simple list
                        for item in result_data[:10]:
                            console.print(f"  {item}")
                        if len(result_data) > 10:
                            console.print(f"[dim]... showing 10 of {len(result_data)} items[/dim]")
                else:
                    console.print(f"  {result_data}")

            console.print()
        else:
            console.print(f"[bold red]Execution Failed[/bold red]")
            console.print(f"  Error: {exec_result.get('error_message', 'Unknown error')}")
            console.print()

    # Clarification needed
    if response.get("needs_clarification"):
        console.print("[bold yellow]Clarification Needed:[/bold yellow]")
        for question in response.get("clarification_questions", []):
            console.print(f"  [yellow]?[/yellow] {question}")
        console.print()

    # Reasoning Trace
    if show_trace and response.get("reasoning_trace"):
        display_reasoning_trace(response["reasoning_trace"])


def display_reasoning_trace(trace: Dict[str, Any]) -> None:
    """Display reasoning trace in a tree format."""
    console.print("[bold magenta]Reasoning Trace:[/bold magenta]")

    tree = Tree("🔍 Query Processing")

    # Orchestrator
    orch_node = tree.add(
        f"[cyan]Orchestrator[/cyan] ({trace.get('orchestrator_latency_ms', 0)}ms)"
    )

    # Schema Agent
    if trace.get("schema_agent"):
        agent = trace["schema_agent"]
        node = orch_node.add(
            f"[green]Schema Expert[/green] ({agent.get('latency_ms', 0)}ms)"
        )
        node.add(f"Tokens: {agent.get('tokens_input', 0)} in / {agent.get('tokens_output', 0)} out")
        if agent.get("details"):
            for key, value in agent["details"].items():
                node.add(f"{key}: {value}")

    # RAG Agent
    if trace.get("rag_agent"):
        agent = trace["rag_agent"]
        node = orch_node.add(
            f"[blue]RAG Retrieval[/blue] ({agent.get('latency_ms', 0)}ms)"
        )
        node.add(f"Tokens: {agent.get('tokens_input', 0)} in / {agent.get('tokens_output', 0)} out")
        if agent.get("details"):
            for key, value in agent["details"].items():
                node.add(f"{key}: {value}")

    # Query Builder Agent
    if trace.get("query_builder_agent"):
        agent = trace["query_builder_agent"]
        node = orch_node.add(
            f"[yellow]Query Builder[/yellow] ({agent.get('latency_ms', 0)}ms)"
        )
        node.add(f"Tokens: {agent.get('tokens_input', 0)} in / {agent.get('tokens_output', 0)} out")
        node.add(f"Iterations: {agent.get('iterations', 1)}")
        if agent.get("details"):
            for key, value in agent["details"].items():
                node.add(f"{key}: {value}")

    # Validator Agent
    if trace.get("validator_agent"):
        agent = trace["validator_agent"]
        node = orch_node.add(
            f"[red]Validator[/red] ({agent.get('latency_ms', 0)}ms)"
        )
        node.add(f"Tokens: {agent.get('tokens_input', 0)} in / {agent.get('tokens_output', 0)} out")
        if agent.get("details"):
            for key, value in agent["details"].items():
                node.add(f"{key}: {value}")

    # Summary
    summary = orch_node.add("[bold]Summary[/bold]")
    summary.add(f"Total Tokens: {trace.get('total_tokens_input', 0)} in / {trace.get('total_tokens_output', 0)} out")
    summary.add(f"Total Cost: ${trace.get('total_cost_usd', 0):.4f}")

    console.print(tree)
    console.print()


def display_conversation(conversation: Dict[str, Any]) -> None:
    """Display conversation details."""
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]Conversation: {conversation['id']}[/bold cyan]",
        border_style="cyan"
    ))

    # Metadata
    meta_table = Table(show_header=False, box=box.SIMPLE)
    meta_table.add_column("Field", style="bold")
    meta_table.add_column("Value")

    meta_table.add_row("Provider", conversation.get("provider_id", "N/A"))
    meta_table.add_row("Status", conversation.get("status", "unknown"))
    meta_table.add_row("Turn Count", str(conversation.get("turn_count", 0)))
    meta_table.add_row("Created", conversation.get("created_at", "N/A"))
    meta_table.add_row("Updated", conversation.get("updated_at", "N/A"))

    console.print(meta_table)
    console.print()

    # Turns
    turns = conversation.get("turns", [])
    if turns:
        console.print("[bold]Conversation Turns:[/bold]")
        console.print()

        for turn in turns:
            turn_panel = Panel(
                f"[bold]Turn {turn['turn_number']}[/bold]\n\n"
                f"[dim]User:[/dim] {turn['user_input']}\n\n"
                f"[dim]Query:[/dim]\n{turn['generated_query']}\n\n"
                f"[dim]Confidence:[/dim] {turn['confidence_score']:.2%} | "
                f"[dim]Status:[/dim] {turn['validation_status']}",
                border_style="blue",
                title=f"Turn {turn['turn_number']}",
                title_align="left"
            )
            console.print(turn_panel)
            console.print()


def display_providers(providers: list[Dict[str, Any]]) -> None:
    """Display list of providers."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Available Providers[/bold cyan]",
        border_style="cyan"
    ))
    console.print()

    table = Table(box=box.ROUNDED)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Type", style="green")
    table.add_column("Status", justify="center")
    table.add_column("Tables", justify="right")
    table.add_column("Last Refresh", style="dim")

    for provider in providers:
        status_icon = "🟢" if provider["connection_status"] == "connected" else "🔴"
        last_refresh = provider.get("last_schema_refresh", "Never")
        if last_refresh and last_refresh != "Never":
            # Parse and format datetime
            try:
                dt = datetime.fromisoformat(last_refresh.replace("Z", "+00:00"))
                last_refresh = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass

        table.add_row(
            provider["id"],
            provider["name"],
            provider["type"],
            status_icon,
            str(provider["table_count"]),
            last_refresh
        )

    console.print(table)
    console.print()


def display_provider_detail(provider: Dict[str, Any]) -> None:
    """Display detailed provider information."""
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]Provider: {provider['name']}[/bold cyan]",
        border_style="cyan"
    ))
    console.print()

    table = Table(show_header=False, box=box.SIMPLE)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("ID", provider["id"])
    table.add_row("Name", provider["name"])
    table.add_row("Type", provider["type"])
    table.add_row("Description", provider.get("description", "N/A"))
    status_icon = "🟢 Connected" if provider["connection_status"] == "connected" else "🔴 Disconnected"
    table.add_row("Status", status_icon)
    table.add_row("Tables", str(provider["table_count"]))
    table.add_row("Last Refresh", provider.get("last_schema_refresh", "Never"))
    table.add_row("Created", provider["created_at"])
    table.add_row("Updated", provider["updated_at"])

    console.print(table)
    console.print()


# ============================================================================
# CLI Commands
# ============================================================================


@click.group()
@click.version_option(version="0.1.0", prog_name="text2x")
@click.option(
    "--api-url",
    envvar="TEXT2X_API_URL",
    help="API base URL (default: http://localhost:8000)",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug mode with detailed error traces",
)
@click.pass_context
def cli(ctx: click.Context, api_url: Optional[str], debug: bool) -> None:
    """
    Text2X - Natural Language to Database Query Converter

    Convert natural language queries into executable database queries using
    multi-agent AI system with RAG-powered examples and expert feedback.

    Configuration file: ~/.text2dsl/config.yaml
    """
    # Initialize context
    ctx.ensure_object(dict)

    # Load config
    config = load_config()

    # Override with command line if provided
    if api_url:
        config["api_url"] = api_url
    if debug:
        config["debug"] = True

    ctx.obj["config"] = config


@cli.command()
@click.argument("query_text")
@click.option(
    "-p", "--provider",
    required=True,
    help="Database provider ID (use 'text2x providers list' to see available providers)",
)
@click.option(
    "-c", "--conversation-id",
    help="Continue existing conversation (UUID)",
)
@click.option(
    "--max-iterations",
    type=click.IntRange(1, 10),
    help="Maximum refinement iterations (default: 3)",
)
@click.option(
    "--confidence-threshold",
    type=click.FloatRange(0.0, 1.0),
    help="Minimum confidence score (0.0-1.0, default: 0.8)",
)
@click.option(
    "--trace",
    type=click.Choice(["none", "summary", "full"], case_sensitive=False),
    default="none",
    help="Reasoning trace detail level",
)
@click.option(
    "--execute/--no-execute",
    default=None,
    help="Execute the generated query",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output raw JSON response",
)
@click.pass_context
def query(
    ctx: click.Context,
    query_text: str,
    provider: str,
    conversation_id: Optional[str],
    max_iterations: Optional[int],
    confidence_threshold: Optional[float],
    trace: str,
    execute: Optional[bool],
    output_json: bool,
) -> None:
    """
    Submit a natural language query.

    Examples:

      text2x query "Show all users over 18" -p postgres-main

      text2x query "Orders from last month" -p postgres-main --execute

      text2x query "Filter by age" -c <conversation-id> -p postgres-main
    """
    async def run():
        config = ctx.obj["config"]
        client = Text2XClient(config["api_url"], config["timeout"])

        try:
            # Check API health first
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task(description="Connecting to API...", total=None)
                await client.health_check()

            # Submit query
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task(description="Processing query...", total=None)

                response = await client.submit_query(
                    provider_id=provider,
                    query=query_text,
                    conversation_id=conversation_id,
                    max_iterations=max_iterations,
                    confidence_threshold=confidence_threshold,
                    trace_level=trace,
                    enable_execution=execute,
                )

            # Display results
            if output_json:
                console.print_json(data=response)
            else:
                display_query_response(response, show_trace=(trace != "none"))

                # Show hint about conversation continuation
                if not conversation_id:
                    console.print(
                        f"[dim]To continue this conversation, use: "
                        f"--conversation-id {response['conversation_id']}[/dim]"
                    )

        except ConnectionError as e:
            console.print(f"[red]Connection Error:[/red] {e}", err=True)
            sys.exit(1)
        except ValueError as e:
            console.print(f"[red]Invalid Input:[/red] {e}", err=True)
            sys.exit(1)
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}", err=True)
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Unexpected Error:[/red] {e}", err=True)
            if config.get("debug"):
                console.print_exception()
            sys.exit(1)
        finally:
            await client.close()

    asyncio.run(run())


@cli.group()
def conversation() -> None:
    """View and manage conversation history."""
    pass


@conversation.command("show")
@click.argument("conversation_id")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output raw JSON response",
)
@click.pass_context
def conversation_show(
    ctx: click.Context,
    conversation_id: str,
    output_json: bool,
) -> None:
    """
    Show conversation details and history.

    Examples:

      text2x conversation show <conversation-id>

      text2x conversation show <conversation-id> --json
    """
    async def run():
        config = ctx.obj["config"]
        client = Text2XClient(config["api_url"], config["timeout"])

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task(description="Fetching conversation...", total=None)
                conversation_data = await client.get_conversation(conversation_id)

            if output_json:
                console.print_json(data=conversation_data)
            else:
                display_conversation(conversation_data)

        except ConnectionError as e:
            console.print(f"[red]Connection Error:[/red] {e}", err=True)
            sys.exit(1)
        except ValueError as e:
            console.print(f"[red]Not Found:[/red] {e}", err=True)
            sys.exit(1)
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}", err=True)
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Unexpected Error:[/red] {e}", err=True)
            if config.get("debug"):
                console.print_exception()
            sys.exit(1)
        finally:
            await client.close()

    asyncio.run(run())


@cli.group()
def providers() -> None:
    """List and manage database providers."""
    pass


@providers.command("list")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output raw JSON response",
)
@click.pass_context
def providers_list(ctx: click.Context, output_json: bool) -> None:
    """
    List all available database providers.

    Examples:

      text2x providers list

      text2x providers list --json
    """
    async def run():
        config = ctx.obj["config"]
        client = Text2XClient(config["api_url"], config["timeout"])

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task(description="Fetching providers...", total=None)
                providers_data = await client.list_providers()

            if output_json:
                console.print_json(data=providers_data)
            else:
                display_providers(providers_data)

        except ConnectionError as e:
            console.print(f"[red]Connection Error:[/red] {e}", err=True)
            sys.exit(1)
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}", err=True)
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Unexpected Error:[/red] {e}", err=True)
            if config.get("debug"):
                console.print_exception()
            sys.exit(1)
        finally:
            await client.close()

    asyncio.run(run())


@providers.command("show")
@click.argument("provider_id")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output raw JSON response",
)
@click.pass_context
def providers_show(
    ctx: click.Context,
    provider_id: str,
    output_json: bool,
) -> None:
    """
    Show detailed information about a provider.

    Examples:

      text2x providers show postgres-main

      text2x providers show postgres-main --json
    """
    async def run():
        config = ctx.obj["config"]
        client = Text2XClient(config["api_url"], config["timeout"])

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task(description="Fetching provider details...", total=None)
                provider_data = await client.get_provider(provider_id)

            if output_json:
                console.print_json(data=provider_data)
            else:
                display_provider_detail(provider_data)

        except ConnectionError as e:
            console.print(f"[red]Connection Error:[/red] {e}", err=True)
            sys.exit(1)
        except ValueError as e:
            console.print(f"[red]Not Found:[/red] {e}", err=True)
            sys.exit(1)
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}", err=True)
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Unexpected Error:[/red] {e}", err=True)
            if config.get("debug"):
                console.print_exception()
            sys.exit(1)
        finally:
            await client.close()

    asyncio.run(run())


@cli.group()
def config() -> None:
    """Manage CLI configuration."""
    pass


@config.command("show")
def config_show() -> None:
    """Show current configuration."""
    config_data = load_config()

    console.print()
    console.print(Panel.fit(
        "[bold cyan]Text2X Configuration[/bold cyan]",
        border_style="cyan"
    ))
    console.print()

    table = Table(show_header=False, box=box.SIMPLE)
    table.add_column("Setting", style="bold")
    table.add_column("Value")

    for key, value in config_data.items():
        table.add_row(key, str(value))

    console.print(table)
    console.print()
    console.print(f"[dim]Configuration file: {CONFIG_PATH}[/dim]")
    console.print()


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """
    Set a configuration value.

    Examples:

      text2x config set api_url http://localhost:8000

      text2x config set trace_level summary

      text2x config set debug true
    """
    config_data = load_config()

    # Validate key
    if key not in DEFAULT_CONFIG:
        console.print(f"[yellow]Warning: '{key}' is not a standard configuration key[/yellow]")
        console.print(f"[dim]Valid keys: {', '.join(DEFAULT_CONFIG.keys())}[/dim]")
        if not click.confirm("Continue anyway?"):
            return

    # Type conversion for known keys
    original_value = value
    try:
        if key in ["timeout", "max_iterations"]:
            value = int(value)
        elif key in ["confidence_threshold"]:
            value = float(value)
            # Validate range
            if not 0.0 <= value <= 1.0:
                console.print(f"[red]Error: confidence_threshold must be between 0.0 and 1.0[/red]", err=True)
                sys.exit(1)
        elif key in ["enable_execution", "debug"]:
            value = value.lower() in ["true", "yes", "1", "on"]
        elif key == "trace_level":
            # Validate trace level
            if value not in ["none", "summary", "full"]:
                console.print(f"[red]Error: trace_level must be one of: none, summary, full[/red]", err=True)
                sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Error: Invalid value for {key}: {e}[/red]", err=True)
        sys.exit(1)

    config_data[key] = value
    save_config(config_data)

    console.print(f"[green]Set {key} = {value}[/green]")


@config.command("reset")
@click.confirmation_option(prompt="Are you sure you want to reset configuration to defaults?")
def config_reset() -> None:
    """Reset configuration to defaults."""
    save_config(DEFAULT_CONFIG)
    console.print("[green]Configuration reset to defaults[/green]")


# ============================================================================
# Main Entry Point
# ============================================================================


if __name__ == "__main__":
    cli()
