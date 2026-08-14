# Recall DSA - VS Code Extension

An AI-powered DSA practice memory assistant for Visual Studio Code, connected to your Recall server.

## Features
- **Topic Mastery View**: See live color-coded mastery scores across all DSA topics right in your sidebar.
- **Personalized Study Plans**: Generate company-targeted 7-day study plans for Amazon, Google, Meta, and more.
- **Quick Attempt Logging**: Submit problem attempt outcomes and practice metrics with a single click.
- **Smart Startup Notifications**: Automatically highlights weak topics that require practice due to 14-day exponential memory decay.

## Configuration Settings
- `recall.serverUrl`: URL of your Recall server instance (e.g., `https://web-production-54438.up.railway.app`).
- `recall.userEmail`: Your registered account email address.
- `recall.targetCompany`: Target company for interview preparation (default: `amazon`).
- `recall.notifyOnStartup`: Enable/disable weak topic warnings on VS Code launch.
