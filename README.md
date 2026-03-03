# cMCP

![cmcp logo](img/cmcp-logo-small.png)

`cmcp` is a command-line utility that helps you interact with [MCP][1] servers. It's basically `curl` for MCP servers.


## Installation

```bash
pip install cmcp
```


## Usage

### STDIO

Interact with the STDIO server:

```bash
cmcp COMMAND METHOD
```

Add required parameters:

```bash
cmcp COMMAND METHOD param1=value param2:='{"arg1": "value"}'
```

Add required environment variables:

```bash
cmcp COMMAND METHOD ENV_VAR1:value ENV_VAR2:value param1=value param2:='{"arg1": "value"}'
```

### HTTP (or SSE)

Interact with the HTTP (or SSE) server:

```bash
cmcp URL METHOD
```

Add required parameters:

```bash
cmcp URL METHOD param1=value param2:='{"arg1": "value"}'
```

Add required HTTP headers:

```bash
cmcp URL METHOD Header1:value Header2:value param1=value param2:='{"arg1": "value"}'
```

### Verbose mode

Enable verbose mode to show JSON-RPC request and response:

```bash
cmcp -v COMMAND_or_URL METHOD
```


## Quick Start

Given the following MCP Server (see [here][2]):

```python
# server.py
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Demo")


# Add a prompt
@mcp.prompt()
def review_code(code: str) -> str:
    return f"Please review this code:\n\n{code}"


# Add a static config resource
@mcp.resource("config://app")
def get_config() -> str:
    """Static configuration data"""
    return "App configuration here"


# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b
```

### STDIO transport

List prompts:

```bash
cmcp 'mcp run server.py' prompts/list
```

Get a prompt:

```bash
cmcp 'mcp run server.py' prompts/get name=review_code arguments:='{"code": "def greet(): pass"}'
```

List resources:

```bash
cmcp 'mcp run server.py' resources/list
```

Read a resource:

```bash
cmcp 'mcp run server.py' resources/read uri=config://app
```

List resource templates:

```bash
cmcp 'mcp run server.py' resources/templates/list
```

List tools:

```bash
cmcp 'mcp run server.py' tools/list
```

Call a tool:

```bash
cmcp 'mcp run server.py' tools/call name=add arguments:='{"a": 1, "b": 2}'
```

### HTTP transport

Run the above MCP server with HTTP transport:

```bash
mcp run server.py -t streamable-http
```

List prompts:

```bash
cmcp http://localhost:8000 prompts/list
# or `cmcp http://localhost:8000/mcp prompts/list`
```

Get a prompt:

```bash
cmcp http://localhost:8000 prompts/get name=review_code arguments:='{"code": "def greet(): pass"}'
```

List resources:

```bash
cmcp http://localhost:8000 resources/list
```

Read a resource:

```bash
cmcp http://localhost:8000 resources/read uri=config://app
```

List resource templates:

```bash
cmcp http://localhost:8000 resources/templates/list
```

List tools:

```bash
cmcp http://localhost:8000 tools/list
```

Call a tool:

```bash
cmcp http://localhost:8000 tools/call name=add arguments:='{"a": 1, "b": 2}'
```

### SSE transport (Deprecated)

Run the above MCP server with SSE transport:

```bash
mcp run server.py -t sse
```

List prompts:

```bash
cmcp http://localhost:8000/sse prompts/list
```

Get a prompt:

```bash
cmcp http://localhost:8000/sse prompts/get name=review_code arguments:='{"code": "def greet(): pass"}'
```

List resources:

```bash
cmcp http://localhost:8000/sse resources/list
```

Read a resource:

```bash
cmcp http://localhost:8000/sse resources/read uri=config://app
```

List resource templates:

```bash
cmcp http://localhost:8000/sse resources/templates/list
```

List tools:

```bash
cmcp http://localhost:8000/sse tools/list
```

Call a tool:

```bash
cmcp http://localhost:8000/sse tools/call name=add arguments:='{"a": 1, "b": 2}'
```


## Using `mcp.json` (Advanced)

For convenience, you can use a configuration file to manage your MCP servers instead of typing the full command or URL each time. By default, `cmcp` looks for `.cmcp/mcp.json` (in the current directory) or `~/.cmcp/mcp.json` (in your home directory).

The configuration follows the standard MCP JSON format, which is also used by [Cursor](https://cursor.com/docs/context/mcp#using-mcpjson), [Claude Code](https://code.claude.com/docs/en/mcp#project-scope), [FastMCP](https://gofastmcp.com/integrations/mcp-json-configuration), and other MCP clients.

Example configuration file:

```json
{
  "mcpServers": {
    "local-server": {
      "command": "python",
      "args": ["mcp-server.py"],
      "env": {
        "API_KEY": "value"
      }
    },
    "remote-server": {
      "url": "http://localhost:3000/mcp",
      "headers": {
        "API_KEY": "value"
      }
    }
  }
}
```

Use a configured server by prefixing its name with `:`:

```bash
# Use the local-server from config
cmcp :local-server tools/list

# Use the remote-server from config
cmcp :remote-server tools/call name=add arguments:='{"a": 1, "b": 2}'

# Use a custom config file
cmcp --config /path/to/config.json :local-server tools/list
```


## Related Projects

[cA2A][3]: A command-line utility for interacting with A2A agents.


## License

[MIT][4]


[1]: https://modelcontextprotocol.io
[2]: https://github.com/modelcontextprotocol/python-sdk#quickstart
[3]: https://github.com/RussellLuo/ca2a
[4]: http://opensource.org/licenses/MIT
