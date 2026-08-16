## Connect to Recall MCP (Claude Desktop)

Add this to your `claude_desktop_config.json`:

Windows path: `%APPDATA%\Claude\claude_desktop_config.json`
Mac path: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "recall": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://dsa-mcp.onrender.com/mcp"
      ]
    }
  }
}
```

Save the file, fully quit Claude Desktop, then reopen it.
