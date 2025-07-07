# github_bot/github_auth.py

import time
import httpx
import jwt  # PyJWT
from github_bot.config import settings


def generate_jwt(app_id: str, private_key_path: str) -> str:
    with open(private_key_path, "r") as f:
        private_key = f.read()

    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + (10 * 60), "iss": app_id}

    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token


def get_installation_token(
    app_id: str, private_key_path: str, installation_id: int
) -> str:
    jwt_token = generate_jwt(app_id, private_key_path)

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
    }

    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    response = httpx.post(url, headers=headers)

    if response.status_code != 201:
        raise Exception(
            f"Failed to get installation token: {response.status_code} {response.text}"
        )

    return response.json()["token"]
