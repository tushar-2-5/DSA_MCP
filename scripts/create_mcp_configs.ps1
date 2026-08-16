# Read .env file values dynamically
$envFilePath = "C:\Users\KIIT\OneDrive\Desktop\DSA PROJECT MCP\.env"
$envVars = @{}
Get-Content $envFilePath | ForEach-Object {
    if ($_ -match '^\s*([^=]+)=(.*)$') {
        $envVars[$matches[1].Trim()] = $matches[2].Trim()
    }
}

$dbUrl = $envVars["DATABASE_URL"]
$geminiKey = $envVars["GEMINI_API_KEY"]
$projectDir = "C:\Users\KIIT\OneDrive\Desktop\DSA PROJECT MCP"

Write-Host "=== Step 3: Claude Desktop config ==="
New-Item -ItemType Directory -Force -Path "$env:APPDATA\Claude" | Out-Null
$claudeConfig = @{
    mcpServers = @{
        recall = @{
            command = "uv"
            args = @("run", "python", "-m", "server.main", "--transport", "stdio")
            cwd = $projectDir
            env = @{
                DATABASE_URL = $dbUrl
                GEMINI_API_KEY = $geminiKey
            }
        }
    }
} | ConvertTo-Json -Depth 5
Set-Content -Path "$env:APPDATA\Claude\claude_desktop_config.json" -Value $claudeConfig
Write-Host "Claude Desktop config created."

Write-Host "=== Step 4: Cursor config ==="
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.cursor" | Out-Null
$cursorConfig = @{
    mcpServers = @{
        recall = @{
            command = "uv"
            args = @("run", "python", "-m", "server.main", "--transport", "stdio")
            cwd = $projectDir
            env = @{
                DATABASE_URL = $dbUrl
                GEMINI_API_KEY = $geminiKey
            }
        }
    }
} | ConvertTo-Json -Depth 5
Set-Content -Path "$env:USERPROFILE\.cursor\mcp.json" -Value $cursorConfig
Write-Host "Cursor config created."

Write-Host "=== Step 5: Windsurf config ==="
$windsurfDir = "$env:APPDATA\Windsurf\User\globalStorage\codeium.windsurf"
$windsurfPath = "$windsurfDir\mcp_config.json"
If (Test-Path $windsurfDir) {
    Set-Content -Path $windsurfPath -Value $cursorConfig
    Write-Host "Windsurf config created."
} Else {
    Write-Host "Windsurf not installed - skipping"
}

Write-Host "=== Step 6: Continue (VS Code) config ==="
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.continue" | Out-Null
$continueConfigPath = "$env:USERPROFILE\.continue\config.json"

If (Test-Path $continueConfigPath) {
    Write-Host "Continue config exists - showing current content:"
    Get-Content $continueConfigPath
} Else {
    $continueConfig = @{
        mcpServers = @(
            @{
                name = "recall"
                command = "uv"
                args = @("run", "python", "-m", "server.main", "--transport", "stdio")
                cwd = $projectDir
                env = @{
                    DATABASE_URL = $dbUrl
                    GEMINI_API_KEY = $geminiKey
                }
            }
        )
    } | ConvertTo-Json -Depth 5
    Set-Content -Path $continueConfigPath -Value $continueConfig
    Write-Host "Continue config created"
}

Write-Host "=== Step 7: Verify all configs ==="
Write-Host "=== Claude Desktop ==="
Write-Host (Test-Path "$env:APPDATA\Claude\claude_desktop_config.json")
Write-Host "=== Cursor ==="
Write-Host (Test-Path "$env:USERPROFILE\.cursor\mcp.json")
Write-Host "=== Continue ==="
Write-Host (Test-Path "$env:USERPROFILE\.continue\config.json")
