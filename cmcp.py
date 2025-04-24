import asyncio
import argparse
import json
import os
import shlex
import sys
from urllib.parse import urljoin

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
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


def print_json(result: BaseModel) -> None:
    """Print the given result object with syntax highlighting."""
    json_str = result.model_dump_json(indent=2)
    if not sys.stdout.isatty():
        print(json_str)
    else:
        highlighted = highlight(json_str, JsonLexer(), TerminalFormatter())
        print(highlighted)


async def invoke(cmd_or_url: str, method: str, data: str) -> None:
    if cmd_or_url.startswith(("http://", "https://")):
        # SSE transport
        url = urljoin(cmd_or_url, "/sse")
        client = sse_client(url=url)
    else:
        # STDIO transport
        elements = shlex.split(cmd_or_url)
        if not elements:
            raise ValueError("stdio command is empty")

        command, args = elements[0], elements[1:]
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=os.environ,  # pass all env vars to the server
        )
        client = stdio_client(server_params)

    params = json.loads(data) if data else {}

    async with client as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            match method:
                case "prompts/list":
                    result = await session.list_prompts()

                case "prompts/get":
                    result = await session.get_prompt(**params)

                case "resources/list":
                    result = await session.list_resources()

                case "resources/templates/list":
                    result = await session.list_resource_templates()

                case "resources/read":
                    result = await session.read_resource(**params)

                case "tools/list":
                    result = await session.list_tools()

                case "tools/call":
                    result = await session.call_tool(**params)

                case _:
                    raise ValueError(f"Unknown method: {method}")

            print_json(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="A command-line utility for interacting with MCP servers."
    )
    parser.add_argument(
        "cmd_or_url",
        help="The command (stdio-transport) or URL (sse-transport) to connect to the MCP server",
    )
    parser.add_argument("method", help="The method to be invoked")
    parser.add_argument(
        "-d",
        "--data",
        type=str,
        default="",
        help="The parameter values in form of JSON string. (Defaults to %(default)r)",
    )
    args = parser.parse_args()

    if args.method not in METHODS:
        parser.error(
            f"Invalid method: {args.method} (choose from {', '.join(METHODS)})."
        )

    asyncio.run(invoke(args.cmd_or_url, args.method, args.data))


if __name__ == "__main__":
    main()
