#!/usr/bin/env python3
"""
One-off backfill: migrate EdgeDevice bearer tokens to the secure at-rest format.

Before this migration `edge_devices.device_token` held the bearer token in clear
text and `token_hash` was often NULL. The new scheme keeps an indexed sha256
`token_hash` for lookups plus an encrypted-at-rest copy in `device_token` (the
token is also the HMAC signing secret, so it must stay recoverable — see
models_device_encryption.EdgeDevice.set_device_token).

This script upgrades every legacy row in place:
  * computes token_hash from the existing plaintext token, and
  * re-encrypts the plaintext into `device_token`.

It is idempotent: rows whose `device_token` already decrypts cleanly (i.e. are
already ciphertext) are skipped. Auth paths also self-heal via
EdgeDevice.lookup_by_token, so this script is belt-and-suspenders for inactive
devices that would otherwise never re-authenticate.

Usage:
    DEVICE_TOKEN_ENC_KEY=... DATABASE_URL=... SESSION_SECRET=... \
        python3 scripts/backfill_device_token_hash.py [--dry-run]

Run it AFTER deploying the new model code and BEFORE relying on plaintext being
absent from the database.
"""
import os
import sys

# Ensure the project root is importable when run as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    dry_run = '--dry-run' in sys.argv

    # Import inside main so --help/usage errors don't require a full app context.
    from app import app  # noqa: E402  (Flask app carries the SQLAlchemy config)
    from db import db  # noqa: E402
    from models_device_encryption import EdgeDevice, _device_token_cipher  # noqa: E402

    cipher = _device_token_cipher()
    if cipher is None:
        print("WARNING: no DEVICE_TOKEN_ENC_KEY/SESSION_SECRET configured — tokens "
              "cannot be encrypted at rest. Set one before running for real.",
              file=sys.stderr)

    upgraded = 0
    skipped = 0
    failed = 0

    with app.app_context():
        devices = EdgeDevice.query.all()
        for device in devices:
            raw = device.device_token
            if not raw:
                skipped += 1
                continue

            # Already ciphertext? Decrypt cleanly -> nothing to do.
            already_encrypted = False
            if cipher is not None:
                try:
                    cipher.decrypt(raw.encode())
                    already_encrypted = True
                except Exception:
                    already_encrypted = False

            if already_encrypted and device.token_hash:
                skipped += 1
                continue

            # Legacy plaintext row: re-store securely (hash + ciphertext).
            try:
                if dry_run:
                    print(f"[dry-run] would upgrade device id={device.id} "
                          f"name={device.device_name!r}")
                else:
                    device.set_device_token(raw)
                upgraded += 1
            except Exception as e:  # pragma: no cover - defensive
                failed += 1
                print(f"ERROR upgrading device id={device.id}: {e}", file=sys.stderr)

        if not dry_run and upgraded:
            db.session.commit()

    print(f"Done. upgraded={upgraded} skipped={skipped} failed={failed} "
          f"(dry_run={dry_run})")
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
