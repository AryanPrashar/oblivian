import base64
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


def _load_env_file() -> None:
    # Support the conventional .env file and the current .env.txt filename.
    for env_name in (".env", ".env.txt"):
        env_path = Path(env_name)
        if env_path.exists():
            load_dotenv(env_path)
            break


_load_env_file()


# Read-only scope ensures emails are not marked as read.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _decode_body_data(data: str) -> str:
    if not data:
        return ""
    padding = "=" * (-len(data) % 4)
    decoded = base64.urlsafe_b64decode(data + padding)
    return decoded.decode("utf-8", errors="replace")


def _extract_plain_text(payload: Dict[str, Any]) -> str:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if mime_type == "text/plain" and body_data:
        return _decode_body_data(body_data)

    for part in payload.get("parts", []) or []:
        text = _extract_plain_text(part)
        if text:
            return text

    return ""


def _extract_sender(headers: Any) -> str:
    for header in headers or []:
        if header.get("name", "").lower() == "from":
            from_value = header.get("value", "").strip()
            if "<" in from_value and ">" in from_value:
                return from_value.split("<", 1)[1].split(">", 1)[0].strip()
            return from_value
    return ""


def get_unread_emails() -> Dict[str, Dict[str, str]]:
    """
    Authenticate with Gmail API and fetch unread inbox emails.

    Returns:
        Dict[str, Dict[str, str]]:
            A dictionary keyed by Gmail message ID.
            Each value has:
              - "from": sender email/address
              - "body": plain text body (best effort)
    """
    creds = None
    token_path = "token.json"
    credentials_path = "credentials.json"

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)

    unread_list = (
        service.users()
        .messages()
        .list(userId="me", q="in:inbox is:unread")
        .execute()
        .get("messages", [])
    )

    result: Dict[str, Dict[str, str]] = {}

    for message_meta in unread_list:
        message_id = message_meta.get("id")
        if not message_id:
            continue

        message = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        payload = message.get("payload", {})
        headers = payload.get("headers", [])

        result[message_id] = {
            "from": _extract_sender(headers),
            "body": _extract_plain_text(payload),
        }

    return result


if __name__ == "__main__":
    emails = get_unread_emails()
    print(emails)
