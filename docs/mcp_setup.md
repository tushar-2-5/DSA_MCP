# Recall MCP Setup Guide

## System Prompt for Claude Desktop / Cursor / Continue

Add this to your IDE Rules (Cursor: Settings → Rules, 
Claude Desktop: Profile → Custom Instructions):

---
You have access to Recall MCP server for DSA practice memory.

SECURITY RULES — ALWAYS FOLLOW:
1. First message ALWAYS: call get_or_create_user(email="MY_EMAIL")
2. Save the returned user_id AND token
3. Pass BOTH to every subsequent Recall tool call
4. NEVER use anyone else's email or user_id
5. If you get an auth error, call get_or_create_user again

My email: [USER SETS THIS IN THEIR OWN RULES]
---

## How It Works
- get_or_create_user returns a 30-day JWT token
- Every tool verifies the token matches the user_id
- Users can only see their own mastery, attempts, and mistakes
