import argparse
import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import re
import shlex
import sys
from typing import Any, Optional
from urllib.parse import urljoin

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import JSONRPCRequest, JSONRPCResponse, Result
from pydantic import BaseModel
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import TerminalFormatter


METHODS = (
    "prompts/list",
    "prompts/get",
    "resources/list",
    "resources/read",
    "resources/templates/list",
    "tools/list",
    "tools/call",
)


@asynccontextmanager
async def simplified_streamablehttp_client(*args, **kwargs):
    """Simplified version of streamablehttp_client(), which only returns (read, write) tuple.

    Usage example:
        async with simplified_streamablehttp_client(...) as (read, write):
            ...
    """
    async with streamablehttp_client(*args, **kwargs) as (read, write, _):
        yield (read, write)


class Client(BaseModel):
    cmd_or_url: str
    method: str
    params: dict[str, Any]

    metadata: dict[str, str]
    """Additional metadata.

    STDIO transport:
    - The key/value pairs are passed as environment variables to the server.

    SSE transport:
    - The key/value pairs are passed as HTTP headers to the server.
    """

    async def invoke(self, verbose: bool) -> Result:
        if self.cmd_or_url.startswith(("http://", "https://")):
            url = self.cmd_or_url
            headers = self.metadata or None
            if url.endswith("/sse"):
                # Explicitly specified SSE transport.
                client = sse_client(url=url, headers=headers)
            else:
                # Default to Streamable HTTP transport.
                if not url.endswith("/mcp"):
                    url = url.removesuffix("/") + "/mcp"
                client = simplified_streamablehttp_client(url=url, headers=headers)
        else:
            # STDIO transport
            elements = shlex.split(self.cmd_or_url)
            if not elements:
                raise ValueError("stdio command is empty")

            command, args = elements[0], elements[1:]
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=self.metadata or None,
            )
            client = stdio_client(server_params)

        async with client as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                if verbose:
                    self.show_jsonrpc_request()

                match self.method:
                    case "prompts/list":
                        result = await session.list_prompts()

                    case "prompts/get":
                        result = await session.get_prompt(**self.params)

                    case "resources/list":
                        result = await session.list_resources()

                    case "resources/read":
                        result = await session.read_resource(**self.params)

                    case "resources/templates/list":
                        result = await session.list_resource_templates()

                    case "tools/list":
                        result = await session.list_tools()

                    case "tools/call":
                        result = await session.call_tool(**self.params)

                    case _:
                        raise ValueError(f"Unsupported method: {self.method}")

                if verbose:
                    self.show_jsonrpc_response(result)
                else:
                    print_json(result)

                return result

    def show_jsonrpc_request(self) -> None:
        print("Request:")
        print_json(
            JSONRPCRequest(
                jsonrpc="2.0",
                id=1,
                method=self.method,
                params=self.params or None,
            )
        )

    def show_jsonrpc_response(self, result: Result) -> None:
        print("Response:")
        print_json(
            JSONRPCResponse(
                jsonrpc="2.0",
                id=1,
                result=result.model_dump(exclude_defaults=True),
            )
        )


def print_json(result: BaseModel) -> None:
    """Print the given result object with syntax highlighting."""
    json_str = result.model_dump_json(indent=2, exclude_defaults=True)
    if not sys.stdout.isatty():
        print(json_str)
    else:
        highlighted = highlight(json_str, JsonLexer(), TerminalFormatter())
        print(highlighted)


def load_config(config_path: Optional[str] = None) -> dict[str, Any]:
    """Load configuration from JSON file.

    If config_path is specified, load from that path.
    Otherwise, try to load from .cmcp/mcp.json or ~/.cmcp/mcp.json.
    """
    if config_path:
        config_file = Path(config_path)
        if not config_file.exists():
            raise ValueError(f"Config file not found: {config_path}")
    else:
        # Try .cmcp/mcp.json first
        local_config = Path(".cmcp/mcp.json")
        home_config = Path.home() / ".cmcp" / "mcp.json"

        if local_config.exists():
            config_file = local_config
        elif home_config.exists():
            config_file = home_config
        else:
            raise ValueError(
                "No config file found. Please specify --config or create "
                ".cmcp/mcp.json or ~/.cmcp/mcp.json"
            )

    with open(config_file, "r") as f:
        config = json.load(f)

    return config


def get_server_from_config(
    server_name: str, config: dict[str, Any]
) -> tuple[str, dict[str, Any], dict[str, str]]:
    """Extract cmd_or_url, params, and metadata from config for a given server name.

    Args:
        server_name: The server name (without the leading ':')
        config: The configuration dictionary

    Returns:
        A tuple of (cmd_or_url, params, metadata)
    """
    mcp_servers = config.get("mcpServers", {})

    if server_name not in mcp_servers:
        raise ValueError(
            f"Server '{server_name}' not found in config. "
            f"Available servers: {', '.join(mcp_servers.keys())}"
        )

    server_config = mcp_servers[server_name]

    # Check if it's a local server (stdio) or remote server (http)
    if "command" in server_config:
        # Local server (stdio transport)
        command = server_config["command"]
        args = server_config.get("args", [])

        # Build the command string
        cmd_parts = [command] + args
        cmd_or_url = " ".join(shlex.quote(part) for part in cmd_parts)

        # Environment variables become metadata for stdio transport
        metadata = server_config.get("env", {})
    elif "url" in server_config:
        # Remote server (http transport)
        cmd_or_url = server_config["url"]

        # HTTP headers become metadata for http transport
        metadata = server_config.get("headers", {})
    else:
        raise ValueError(
            f"Invalid server config for '{server_name}': "
            "must have either 'command' (for stdio) or 'url' (for http)"
        )

    # No params from config (params come from command line)
    params = {}

    return cmd_or_url, params, metadata


def parse_items(items: list[str]) -> tuple[dict[str, Any], dict[str, str]]:
    """Parse items in the form of `key:value`, `key=string_value` or `key:=json_value`."""

    # Regular expression pattern
    PATTERN = re.compile(r"^([^:=]+)(=|:=|:)(.+)$", re.DOTALL)

    params: dict[str, Any] = {}
    metadata: dict[str, str] = {}

    def parse(item: str) -> None:
        match = PATTERN.match(item)
        if not match:
            raise ValueError(f"Invalid item: {item!r}")

        key, separator, value = match.groups()
        match separator:
            case "=":  # String field
                params[key] = value
            case ":=":  # Raw JSON field
                try:
                    parsed_value = json.loads(value)
                    params[key] = parsed_value
                except json.JSONDecodeError:
                    raise ValueError(f"Invalid JSON value: {value!r}")
            case ":":  # Metadata
                metadata[key] = value
            case _:
                raise ValueError(f"Unsupported separator: {separator!r}")

    for item in items:
        parse(item)

    return params, metadata


def main() -> None:
    parser = argparse.ArgumentParser(
        description="A command-line utility for interacting with MCP servers."
    )
    parser.add_argument(
        "cmd_or_url",
        help="The command (stdio-transport), URL (http-transport), or server name (starting with ':') to connect to the MCP server",
    )
    parser.add_argument("method", help="The method to be invoked")
    parser.add_argument(
        "items",
        nargs="*",
        help="""\
The parameter values (in the form of `key=string_value` or `key:=json_value`),
or the metadata values (in the form of `key:value`)\
""",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output showing JSON-RPC request/response",
    )
    parser.add_argument(
        "--config",
        help="Path to config file (defaults to .cmcp/mcp.json or ~/.cmcp/mcp.json)",
    )
    args = parser.parse_args()

    if args.method not in METHODS:
        parser.error(
            f"Invalid method: {args.method} (choose from {', '.join(METHODS)})."
        )

    try:
        # Check if cmd_or_url is a server name reference (starts with ':')
        if args.cmd_or_url.startswith(":"):
            server_name = args.cmd_or_url[1:]  # Remove the leading ':'

            try:
                config = load_config(args.config)
            except ValueError as exc:
                parser.error(str(exc))

            try:
                cmd_or_url, params, metadata = get_server_from_config(
                    server_name, config
                )
            except ValueError as exc:
                parser.error(str(exc))
        else:
            cmd_or_url = args.cmd_or_url
            params, metadata = parse_items(args.items)

    except ValueError as exc:
        parser.error(str(exc))

    client = Client(
        cmd_or_url=cmd_or_url,
        method=args.method,
        params=params,
        metadata=metadata,
    )
    asyncio.run(client.invoke(args.verbose))


if __name__ == "__main__":
    main()
