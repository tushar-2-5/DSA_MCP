# Recall MCP Setup Guide

You have access to Recall MCP server for DSA practice memory.

IMPORTANT SECURITY RULES:
1. ALWAYS call get_or_create_user(email="USER_EMAIL") FIRST
2. Store the returned user_id AND token
3. Pass BOTH user_id and token to every subsequent tool call
4. NEVER use a hardcoded user_id or someone else's email
5. If token verification fails, call get_or_create_user again

My email for Recall: [USER_SETS_THIS_IN_THEIR_OWN_RULES]
