# github_bot/post_comment.py

import httpx


def format_comment(summary: str, violations: list) -> str:
    """
    Formats the MCP results into a GitHub markdown comment.
    """
    comment = f"## 🤖 GitHub Bot Review\n\n"
    comment += f"### ✅ PR Summary:\n\n{summary.strip()}\n\n"

    if not violations:
        comment += "### ✅ No rule violations found.\n"
    else:
        comment += "### ❌ Rule Violations:\n"
        for v in violations:
            comment += f"- **{v['rule_id']}**: {v['reason']}\n"

    comment += "\n---\n_I'm an automated reviewer powered by LLM + MCP server._"
    return comment


def post_comment_to_pr(repo_full_name: str, pr_number: int, comment_body: str, token: str):
    """
    Posts a comment to the specified PR using the GitHub API.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    payload = {"body": comment_body}
    response = httpx.post(url, headers=headers, json=payload)

    if response.status_code not in (200, 201):
        raise Exception(f"Failed to post comment: {response.status_code}, {response.text}")

    return response.json()
