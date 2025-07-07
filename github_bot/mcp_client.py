# github_bot/mcp_client.py

import httpx
from github_bot.config import settings


def get_summary(pr_data: dict) -> dict:
    """
    Send PR data to the MCP server and return the summary and rule violations.

    Args:
        pr_data (dict): {
            title, description, diff, files[], repo_full_name, pr_number, user
        }

    Returns:
        dict: {
            "summary": str,
            "rule_violations": list
        }
    """

    try:
        response = httpx.post(settings.MCP_URL, json=pr_data, timeout=30)

        if response.status_code != 200:
            print("[MCP ERROR]", response.status_code, response.text)
            return {"summary": "", "rule_violations": []}

        return response.json()

    except Exception as e:
        print("[MCP EXCEPTION]", str(e))
        return {"summary": "", "rule_violations": []}
