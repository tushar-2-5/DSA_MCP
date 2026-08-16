## Connect to Recall MCP (Claude Desktop)

Add this to your `claude_desktop_config.json`:

Windows path: `%APPDATA%\Claude\claude_desktop_config.json`
Mac path: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "recall": {
      "type": "sse",
      "url": "https://recall-mcp.onrender.com/sse"
    }
  }
}
```

Save the file, fully quit Claude Desktop, then reopen it.
