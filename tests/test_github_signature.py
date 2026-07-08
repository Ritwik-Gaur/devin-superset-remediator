from __future__ import annotations

import hashlib
import hmac
import unittest

from app.github import verify_signature


class SignatureTests(unittest.TestCase):
    def test_signature_verifies(self) -> None:
        payload = b'{"ok": true}'
        secret = "secret"
        digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        self.assertTrue(verify_signature(secret, payload, f"sha256={digest}"))

    def test_signature_rejects_wrong_digest(self) -> None:
        self.assertFalse(verify_signature("secret", b"{}", "sha256=bad"))

    def test_missing_secret_allows_local_development(self) -> None:
        self.assertTrue(verify_signature(None, b"{}", None))


if __name__ == "__main__":
    unittest.main()

