import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("."))

from server.main import mcp
from tools.get_mastery_report import get_mastery_report
from tools.get_or_create_user import get_or_create_user

def verify_tools():
    tools = mcp._tool_manager.list_tools()
    print("==================================================")
    print("Tool count:", len(tools))
    for i, t in enumerate(tools):
        print(f"{i}. {t.name}: {t.description[:50]} (length: {len(t.description)})")
    print("==================================================")

    assert tools[0].name == "get_or_create_user", f"Expected get_or_create_user first, got {tools[0].name}"
    assert "say_hello" not in [t.name for t in tools], "say_hello must not be present"
    for t in tools:
        assert len(t.description) < 50, f"Tool {t.name} description >= 50 chars: {t.description}"
    print("ALL TOOL ASSERTIONS PASSED!\n")


async def verify_user_and_mastery():
    # Create / Fetch alex@recall.dev
    res = await get_or_create_user("alex@recall.dev", "recall@demo123")
    print("User Response for alex@recall.dev:")
    print(res)
    user_id = res["user_id"]
    token = res["token"]
    
    assert user_id == "77ae399e-31ea-4a84-9fdb-23dab394f2d7", f"Unexpected user_id: {user_id}"
    
    # Call get_mastery_report
    report = await get_mastery_report(user_id=user_id, token=token)
    print("\nMastery Report for alex@recall.dev:")
    print("Topic count:", len(report["topics"]))
    for topic in report["topics"]:
        slug = topic["slug"]
        score = topic["mastery_score"]
        lp = topic["last_practiced_at"]
        print(f"  - {slug}: {score:.2f} (last practiced: {lp})")
    
    assert len(report["topics"]) > 0, "Expected topics in mastery report"
    print("\nALL ALEX & MASTERY VERIFICATIONS PASSED!")


if __name__ == "__main__":
    verify_tools()
    asyncio.run(verify_user_and_mastery())
