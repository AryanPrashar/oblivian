import time
import os
from typing import Any, Dict
from dotenv import load_dotenv # ADD THIS


# Load secrets before anything else runs
load_dotenv()

print("🌑 BOOT SEQUENCE INITIATED.", flush=True)

from check_inbox import get_unread_emails
from execute import process_refund, resolve_and_archive, mark_as_read
from think import analyze_email


def _handle_message(message_id: str, email_data: Dict[str, str]) -> None:
    sender_email = email_data.get("from", "unknown-sender")
    email_body = email_data.get("body", "")


    decision: Dict[str, Any] = analyze_email(email_body)
    action = decision.get("action")
    stripe_id = decision.get("stripe_id")


    if action == "refund" and isinstance(stripe_id, str) and stripe_id.startswith("pi_"):
        process_refund(stripe_id, sender_email)
        resolve_and_archive(message_id, sender_email, stripe_id)
        print("Refund executed")
        return
    elif action == "human_review":
        mark_as_read(message_id)
        print(f"🌑 ECLIPSE: Flagged for human review: {sender_email}")
        return
    else:
        mark_as_read(message_id)
        print("🌑 ECLIPSE: Ignored and marked read")


def main() -> None:
    print("🌑 OBLIVIAN ENGINE ONLINE. Monitoring inbox...", flush=True)
    while True:
        try:
            unread_emails = get_unread_emails()
            if unread_emails:
                print(f"🌑 ECLIPSE: Scan found {len(unread_emails)} unread.", flush=True)


            for message_id, email_data in unread_emails.items():
                try:
                    _handle_message(message_id, email_data)
                except Exception as message_error:
                    sender_email = email_data.get("from", "unknown-sender")
                    print(f"🌑 ECLIPSE: Failed {sender_email}: {message_error}")
        except Exception as loop_error:
            print(f"🌑 ECLIPSE: Loop fault: {loop_error}")


        time.sleep(60)


if __name__ == "__main__":
    main()

