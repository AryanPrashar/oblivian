import base64
import json
import os
from email.mime.text import MIMEText
from typing import Any, Dict


import stripe
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# FATAL FLAW 2 FIX: Unified Scope
SCOPES =["https://www.googleapis.com/auth/gmail.modify"]


def _get_gmail_service():
    creds = None
    token_path = "token.json"
    credentials_path = "credentials.json"
    token_json = os.getenv("GMAIL_TOKEN_JSON")
    credentials_json = os.getenv("GMAIL_CREDENTIALS_JSON")


    if token_json:
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    elif os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)


    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if credentials_json:
                flow = InstalledAppFlow.from_client_config(
                    json.loads(credentials_json), SCOPES
                )
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        if not token_json:
            with open(token_path, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())


    return build("gmail", "v1", credentials=creds)


def process_refund(stripe_id: str, sender_email: str) -> Dict[str, Any]:
    secret_key = os.getenv("STRIPE_SECRET_KEY")
    if not secret_key:
        raise ValueError("Missing STRIPE_SECRET_KEY environment variable.")


    stripe.api_key = secret_key
    try:
        payment_intent = stripe.PaymentIntent.retrieve(stripe_id)


        normalized_sender = sender_email.strip().lower()
        receipt_email = (
            (getattr(payment_intent, "receipt_email", None) or "").strip().lower()
        )


        customer_email = ""
        customer = getattr(payment_intent, "customer", None)
        if isinstance(customer, dict):
            customer_email = (customer.get("email") or "").strip().lower()
        elif isinstance(customer, str) and customer:
            customer_obj = stripe.Customer.retrieve(customer)
            customer_email = (
                (getattr(customer_obj, "email", None) or "").strip().lower()
            )
        elif customer is not None:
            customer_email = (getattr(customer, "email", None) or "").strip().lower()


        if normalized_sender not in {receipt_email, customer_email}:
            raise ValueError("IDENTITY_MISMATCH: Sender does not own this transaction")


        refund = stripe.Refund.create(payment_intent=stripe_id)
        return dict(refund)
    except stripe.error.StripeError as stripe_error:
        if getattr(stripe_error, "code", None) == "charge_already_refunded":
            print("🌑 ECLIPSE: Already refunded, proceeding to archive.")
            return {"status": "already_refunded", "success": True}
        raise


# Passed stripe_id as a parameter
def resolve_and_archive(message_id: str, sender_email: str, stripe_id: str) -> None:
    service = _get_gmail_service()
    message = service.users().messages().get(userId="me", id=message_id, format="metadata").execute()
    thread_id = message.get("threadId")


    reply_text = f"Your refund for {stripe_id} has been processed autonomously."
    mime_message = MIMEText(reply_text)
    mime_message["to"] = sender_email
    mime_message["subject"] = "Refund Processed"


    raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")
    send_body = {"raw": raw_message}
    if thread_id:
        send_body["threadId"] = thread_id


    # Send the email
    service.users().messages().send(userId="me", body=send_body).execute()
   
    # Remove INBOX label (Archive it)
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["INBOX"]},
    ).execute()


# THE INFINITE LOOP FIX (Helper Function)
def mark_as_read(message_id: str) -> None:
    service = _get_gmail_service()
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()

