# github_bot/utils.py

import httpx


def fetch_pr_diff_and_files(diff_url: str, files_url: str, token: str):
    """
    Fetches:
    - The raw diff from the GitHub Pull Request
    - The structured list of changed files

    Returns:
        (files: List[dict], diff_text: str)
    """

    file_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    diff_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3.diff"
    }

    with httpx.Client() as client:
        # Fetch structured file list
        file_resp = client.get(files_url, headers=file_headers)
        if file_resp.status_code != 200:
            raise Exception(
                f"Failed to fetch files: {file_resp.status_code}, {file_resp.text}"  # noqa
            )
        files = file_resp.json()

        # Fetch unified diff
        diff_resp = client.get(diff_url, headers=diff_headers)
        if diff_resp.status_code != 200:
            raise Exception(
                f"Failed to fetch diff: {diff_resp.status_code}, {diff_resp.text}"  # noqa
            )
        diff_text = diff_resp.text

    return files, diff_text
