"""Email integration management for Covenant Connect."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Sequence

import boto3
from botocore.exceptions import BotoCoreError, ClientError
import requests
from flask import current_app
from flask_mail import Message

from app import mail
from models import ServiceIntegration

TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}


class EmailIntegrationManager:
    """Dispatch email delivery through configured service integrations."""

    SERVICE_NAME = "email"

    @classmethod
    def send_email(
        cls,
        subject: str,
        body: str,
        recipients: Sequence[str],
        *,
        sender: str | None = None,
        html: str | None = None,
    ) -> None:
        """Send an email using the first active integration, falling back to Flask-Mail."""

        resolved_recipients = [email for email in recipients if email]
        if not resolved_recipients:
            raise ValueError("At least one recipient email address is required")

        integrations = cls._active_integrations()
        last_error: Exception | None = None

        for integration in integrations:
            try:
                cls._dispatch(integration, subject, body, resolved_recipients, sender, html)
                current_app.logger.info(
                    "Email delivered via %s integration (id=%s).",
                    integration.provider,
                    integration.id,
                )
                return
            except Exception as exc:  # pragma: no cover - defensive logging path
                last_error = exc
                current_app.logger.warning(
                    "Failed to send email via %s integration (id=%s): %s",
                    integration.provider,
                    integration.id,
                    exc,
                )

        cls._send_via_flask_mail(subject, body, resolved_recipients, sender, html)
        if last_error:
            current_app.logger.info(
                "Fell back to Flask-Mail after integration failure: %s",
                last_error,
            )

    @classmethod
    def _active_integrations(cls) -> list[ServiceIntegration]:
        return (
            ServiceIntegration.query.filter_by(service=cls.SERVICE_NAME, is_active=True)
            .order_by(ServiceIntegration.id.asc())
            .all()
        )

    @classmethod
    def _dispatch(
        cls,
        integration: ServiceIntegration,
        subject: str,
        body: str,
        recipients: Sequence[str],
        sender: str | None,
        html: str | None,
    ) -> None:
        provider = (integration.provider or "").lower()
        config = integration.config or {}

        if provider == "aws_ses":
            cls._send_via_ses(config, subject, body, recipients, sender, html)
        elif provider == "mailgun":
            cls._send_via_mailgun(config, subject, body, recipients, sender, html)
        elif provider == "smtp":
            cls._send_via_smtp(config, subject, body, recipients, sender, html)
        else:
            raise ValueError(f"Unsupported email provider '{integration.provider}'")

    @staticmethod
    def _resolve_sender(config: dict[str, object], sender: str | None) -> str:
        if sender:
            return sender
        configured = config.get("sender_email")
        if isinstance(configured, str) and configured.strip():
            return configured.strip()
        fallback = current_app.config.get("MAIL_DEFAULT_SENDER")
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip()
        return current_app.config.get("DEFAULT_MAIL_SENDER", "")

    @classmethod
    def _send_via_ses(
        cls,
        config: dict[str, object],
        subject: str,
        body: str,
        recipients: Sequence[str],
        sender: str | None,
        html: str | None,
    ) -> None:
        access_key = cls._get_str(config, "access_key_id")
        secret_key = cls._get_str(config, "secret_access_key")
        region = cls._get_str(config, "region") or "us-east-1"
        resolved_sender = cls._resolve_sender(config, sender)
        if not (access_key and secret_key and resolved_sender):
            raise ValueError("AWS SES integration is missing required credentials")

        client = boto3.client(
            "ses",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

        message = {
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body}},
        }
        if html:
            message["Body"]["Html"] = {"Data": html}

        kwargs: dict[str, object] = {
            "Source": resolved_sender,
            "Destination": {"ToAddresses": list(recipients)},
            "Message": message,
        }

        configuration_set = cls._get_str(config, "configuration_set")
        if configuration_set:
            kwargs["ConfigurationSetName"] = configuration_set

        reply_to = cls._get_str(config, "reply_to")
        if reply_to:
            kwargs["ReplyToAddresses"] = [reply_to]

        try:
            client.send_email(**kwargs)
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"AWS SES send_email failed: {exc}") from exc

    @classmethod
    def _send_via_mailgun(
        cls,
        config: dict[str, object],
        subject: str,
        body: str,
        recipients: Sequence[str],
        sender: str | None,
        html: str | None,
    ) -> None:
        api_key = cls._get_str(config, "api_key")
        domain = cls._get_str(config, "domain")
        base_url = cls._get_str(config, "base_url") or "https://api.mailgun.net/v3"
        resolved_sender = cls._resolve_sender(config, sender)
        if not (api_key and domain and resolved_sender):
            raise ValueError("Mailgun integration is missing required configuration")

        url = f"{base_url.rstrip('/')}/{domain}/messages"
        data = {
            "from": resolved_sender,
            "to": list(recipients),
            "subject": subject,
            "text": body,
        }
        if html:
            data["html"] = html

        timeout = 10
        response = requests.post(url, auth=("api", api_key), data=data, timeout=timeout)
        if response.status_code >= 400:
            raise RuntimeError(
                f"Mailgun request failed with {response.status_code}: {response.text}"
            )

    @classmethod
    def _send_via_smtp(
        cls,
        config: dict[str, object],
        subject: str,
        body: str,
        recipients: Sequence[str],
        sender: str | None,
        html: str | None,
    ) -> None:
        server = cls._get_str(config, "server")
        port_value = cls._get_str(config, "port") or "587"
        username = cls._get_str(config, "username")
        password = cls._get_str(config, "password")
        resolved_sender = cls._resolve_sender(config, sender)
        use_tls = cls._as_bool(config.get("use_tls"))

        if not server or not resolved_sender:
            raise ValueError("SMTP integration requires a server and sender email")

        try:
            port = int(port_value)
        except (TypeError, ValueError) as exc:  # pragma: no cover - invalid config guard
            raise ValueError("SMTP port must be an integer") from exc

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = resolved_sender
        message["To"] = ", ".join(recipients)
        message.set_content(body)
        if html:
            message.add_alternative(html, subtype="html")

        with smtplib.SMTP(server, port, timeout=10) as smtp:
            if use_tls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)

    @classmethod
    def _send_via_flask_mail(
        cls,
        subject: str,
        body: str,
        recipients: Sequence[str],
        sender: str | None,
        html: str | None,
    ) -> None:
        resolved_sender = sender or current_app.config.get("MAIL_DEFAULT_SENDER")
        message = Message(subject=subject, recipients=list(recipients), sender=resolved_sender, body=body)
        if html:
            message.html = html
        mail.send(message)

    @staticmethod
    def _get_str(config: dict[str, object], key: str) -> str:
        value = config.get(key)
        if isinstance(value, str):
            return value.strip()
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _as_bool(value: object | None) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in TRUE_VALUES


__all__ = ["EmailIntegrationManager"]
