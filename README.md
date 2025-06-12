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

### SSE

Interact with the SSE server:

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

### SSE transport

Run the above MCP server with SSE transport:

```bash
mcp run server.py -t sse
```

List prompts:

```bash
cmcp http://localhost:8000 prompts/list
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


[1]: https://modelcontextprotocol.io
[2]: https://github.com/modelcontextprotocol/python-sdk#quickstart
