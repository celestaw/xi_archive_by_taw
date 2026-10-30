"""Fail closed on private paths, contact details and credentials in public data."""
import ipaddress
import re
from urllib.parse import parse_qsl, unquote, urlsplit


PRIVATE_TEXT = re.compile(
    r"(?:[A-Za-z]:[/\\]+Users[/\\]+|/Users/|/home/|file://|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b|"
    r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|"
    r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}\b|"
    r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b|"
    r"\b[A-Za-z0-9_.+%-]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,24}\b)",
    re.IGNORECASE,
)


def check_public_text(value):
    if isinstance(value, str):
        if PRIVATE_TEXT.search(unquote(value)):
            raise ValueError("Public text contains a private path, contact detail or credential pattern")
    elif isinstance(value, dict):
        for child in value.values():
            check_public_text(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            check_public_text(child)
    return value


def public_url(value: str) -> str:
    check_public_text(value)
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in {"https", "http"} or not host or parsed.username or parsed.password:
            raise ValueError
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError
        if any(key.lower() in {"token", "access_token", "api_key", "password", "authorization"}
               or key.lower().startswith("x-amz-") for key, _ in parse_qsl(parsed.query)):
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError("Expected a public HTTP source URL without credentials") from None
    return value
