# github_bot/router.py

from fastapi import APIRouter, Request, Header, status, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from github_bot.github_auth import get_installation_token, generate_jwt
from github_bot.mcp_client import get_summary
from github_bot.utils import fetch_pr_diff_and_files
from github_bot.config import settings
from github_bot.post_comment import format_comment, post_comment_to_pr
import hmac
import httpx
import base64
import json
import urllib.parse

webhook_router = APIRouter()


@webhook_router.post("/webhook")
async def handle_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None)
):
    body = await request.body()
    # print("Received webhook")

    # --- Signature verification ---
    expected_sig = "sha256=" + hmac.new(
        settings.WEBHOOK_SECRET.encode(), body, digestmod="sha256"
    ).hexdigest()
    if not hmac.compare_digest(expected_sig, x_hub_signature_256):
        print("Invalid signature detected")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "Invalid signature"}
        )

    # --- Parse JSON payload ---
    try:
        payload = await request.json()
    except Exception:
        return {"error": "Invalid JSON"}

    action = payload.get("action")
    if payload.get("pull_request") is None or action not in ["opened", "synchronize", "reopened"]:  # noqa
        return {"msg": "Ignored event"}

    pr = payload["pull_request"]
    repo = payload["repository"]
    installation_id = payload["installation"]["id"]

    # --- Get GitHub installation token ---
    token = get_installation_token(
        app_id=settings.APP_ID,
        private_key_path=settings.PRIVATE_KEY_PATH,
        installation_id=installation_id
    )

    # --- Fetch PR diff and files ---
    pr_number = payload["number"]
    files_url = pr["url"] + "/files"
    diff_url = f"https://api.github.com/repos/{repo['owner']['login']}/{repo['name']}/pulls/{pr_number}"  # noqa
    files, diff_text = fetch_pr_diff_and_files(diff_url, files_url, token)
    # --- Prepare payload for MCP ---
    pr_data = {
        "pr_number": pr_number,
        "title": pr["title"],
        "description": pr.get("body") or "",
        "repo_full_name": repo["full_name"],
        "diff": diff_text,
        "files": [
            {
                "filename": f["filename"],
                "status": f["status"],
                "additions": f.get("additions", 0),
                "deletions": f.get("deletions", 0)
            }
            for f in files
        ],
        "user": {
            "login": pr["user"]["login"],
            "id": pr["user"]["id"],
            "url": pr["user"]["html_url"]
        }
    }

    # --- Call MCP ---
    mcp_response = get_summary(pr_data)

    # Store analysis in database
    from db.crud import upsert_pr_summary
    from datetime import datetime

    # Convert string dates to datetime objects
    def parse_date(date_str):
        if not date_str:
            return None
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))

    await upsert_pr_summary(
        repo_full_name=repo["full_name"],
        pr_number=pr_number,
        pr_url=pr["html_url"],
        title=pr["title"],
        author_login=pr["user"]["login"],
        created_at=parse_date(pr["created_at"]),
        closed_at=parse_date(pr.get("closed_at")),
        merged_at=parse_date(pr.get("merged_at")),
        is_merged=pr.get("merged", False),
        commits_count=pr.get("commits", 0),
        additions=pr.get("additions", 0),
        deletions=pr.get("deletions", 0),
        changed_files=pr.get("changed_files", 0),
        comments_count=pr.get("comments", 0),
        review_comments_count=pr.get("review_comments", 0),
        approvals_count=0,  # You can calculate this from reviews
        violation_count=len(mcp_response["rule_violations"]),
        violations=mcp_response["rule_violations"],
        summary_text=mcp_response["summary"],
        summary_generated_at=parse_date(pr["updated_at"])
    )

    comment_body = format_comment(
        mcp_response["summary"], mcp_response["rule_violations"]
    )
    comment_body = format_comment(mcp_response["summary"], mcp_response["rule_violations"])
    post_comment_to_pr(repo["full_name"], pr_number, comment_body, token)

    return {"msg": "Webhook processed"}


@webhook_router.get("/auth/github/callback")
async def github_oauth_callback(code: str):
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
        )
    # print("GitHub token response:", token_resp.text)
    token_data = token_resp.json()
    access_token = token_data.get("access_token")

    if not access_token:
        return {"error": "Failed to get access token"}

    # Get user info
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"}
        )
    user_data = user_resp.json()

    # Encode user data
    encoded_user = base64.urlsafe_b64encode(json.dumps(user_data).encode()).decode()

    # Redirect to frontend
    redirect_url = f"{settings.FRONTEND_URL}/dashboard?token={access_token}&user={encoded_user}"
    return RedirectResponse(url=redirect_url)


@webhook_router.get("/login/github")
def login_github():
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": "read:user user:email repo",
        "allow_signup": "true"
    }
    url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@webhook_router.get("/repos")
async def get_repos(token: str = Header(..., alias="Authorization")):
    # Remove "Bearer " prefix
    github_token = token.replace("Bearer ", "")
    # Fetch repos from GitHub API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"token {github_token}"}
        )
        repos_data = response.json()
        # Transform to match your frontend interface
        repos = []
        for repo in repos_data:
            repos.append({
                "name": repo["name"],
                "full_name": repo["full_name"],
                "open_prs": repo.get("open_issues_count", 0),  # or fetch actual PR count
                "last_updated": repo["updated_at"],
                "description": repo.get("description"),
                "private": repo.get("private", False)
            })

        return repos


@webhook_router.get("/repos/{repo:path}/pull-requests")
async def get_repo_prs(repo: str, token: str = Header(..., alias="Authorization")):    
    # Try to get installation token for this repository
    try:
        # First, get the installation ID for this repository
        jwt_token = generate_jwt(settings.APP_ID, settings.PRIVATE_KEY_PATH)
        
        async with httpx.AsyncClient() as client:
            # Get installations for the app
            installations_response = await client.get(
                "https://api.github.com/app/installations",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json"
                }
            )
            
            if installations_response.status_code != 200:
                print(f"Failed to get installations: {installations_response.status_code}")
                # Fall back to personal access token
                github_token = token.replace("Bearer ", "")
            else:
                installations = installations_response.json()
                
                # Find installation for this repository
                installation_id = None
                for installation in installations:
                    if installation.get("account", {}).get("login") in repo:
                        installation_id = installation["id"]
                        break
                
                if installation_id:
                    # Get installation token
                    github_token = get_installation_token(
                        settings.APP_ID, 
                        settings.PRIVATE_KEY_PATH, 
                        installation_id
                    )
                else:
                    github_token = token.replace("Bearer ", "")
    except Exception as e:
        github_token = token.replace("Bearer ", "")

    async with httpx.AsyncClient() as client:
        github_url = f"https://api.github.com/repos/{repo}/pulls"

        response = await client.get(
            github_url,
            headers={"Authorization": f"Bearer {github_token}"}
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        prs_data = response.json()

        # Transform to match your frontend interface
        prs = []
        for pr in prs_data:
            prs.append({
                "number": pr["number"],
                "title": pr["title"],
                "author": pr["user"]["login"],
                "status": pr["state"],  # "open", "closed"
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"]
            })

        return prs


@webhook_router.get("/repos/{repo:path}/prs/{pr_number}")
async def get_pr_details(repo: str, pr_number: int, token: str = Header(..., alias="Authorization")):
    github_token = token.replace("Bearer ", "")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{repo}/pulls/{pr_number}",
            headers={"Authorization": f"Bearer {github_token}"}
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        pr_data = response.json()

        # Get analysis from database
        from db.connection import get_db_pool
        pool = get_db_pool()

        db_row = await pool.fetchrow(
            "SELECT summary_text, violations FROM pr_summary WHERE repo_full_name = $1 AND pr_number = $2",
            repo, pr_number
        )

        summary = ""
        violations: list = []

        if db_row:
            summary = db_row["summary_text"] or ""
            violations_data = db_row["violations"]
            if violations_data:
                if isinstance(violations_data, str):
                    import json
                    violations = json.loads(violations_data)
                elif isinstance(violations_data, list):
                    violations = violations_data
                else:
                    violations = []
            else:
                violations = []
        
        # Transform to match your frontend interface
        pr_details = {
            "number": pr_data["number"],
            "title": pr_data["title"],
            "author": pr_data["user"]["login"],
            "status": pr_data["state"],
            "created_at": pr_data["created_at"],
            "updated_at": pr_data["updated_at"],
            "summary": summary,  # AI-generated summary
            "violations": violations,  # AI-generated violations
            "owner": pr_data["user"]["login"],
            "last_updated": pr_data["updated_at"]
        }

        return pr_details
