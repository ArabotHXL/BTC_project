from datetime import datetime, timezone


SENSITIVE_FIELDS = {'token', 'secret', 'password', 'private_key', 'wallet', 'mnemonic'}


def redact_payload(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    result = {}
    for key, value in data.items():
        if any(s in key.lower() for s in SENSITIVE_FIELDS):
            result[key] = '***REDACTED***'
        elif isinstance(value, dict):
            result[key] = redact_payload(value)
        elif isinstance(value, list):
            result[key] = [redact_payload(item) if isinstance(item, dict) else item for item in value]
        else:
            result[key] = value
    return result


def build_evidence_ref(ref_type: str, ref_id, source: str = None) -> dict:
    return {"type": ref_type, "id": ref_id, "source": source}


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
