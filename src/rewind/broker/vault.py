"""
Credential Vault.

Stores production credentials in an encrypted local file. The agent process
never has read access to the vault — only the Rewind proxy process does.

Encryption uses Fernet (AES-128-CBC with HMAC-SHA256) from the cryptography
library. The vault key is stored in a separate file with restricted permissions.
"""

from __future__ import annotations

import json
import logging
import os
import stat
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

_DEFAULT_VAULT_PATH = Path(".rewind/vault.enc")
_DEFAULT_KEY_PATH = Path(".rewind/vault.key")


class VaultError(Exception):
    """Raised when vault operations fail."""


class Vault:
    """
    Encrypted credential store.

    Credentials are stored as a JSON dict encrypted with Fernet.
    The key file is created with 0600 permissions (owner-only read/write).
    """

    def __init__(
        self,
        vault_path: Path | str = _DEFAULT_VAULT_PATH,
        key_path: Path | str = _DEFAULT_KEY_PATH,
    ) -> None:
        self._vault_path = Path(vault_path)
        self._key_path = Path(key_path)
        self._fernet: Fernet | None = None
        self._credentials: dict[str, dict[str, Any]] = {}

    def initialize(self) -> None:
        """Initialize the vault: create key if needed, load or create vault file."""
        self._vault_path.parent.mkdir(parents=True, exist_ok=True)

        if self._key_path.exists():
            key = self._key_path.read_bytes().strip()
            self._fernet = Fernet(key)
            logger.info("Vault key loaded from %s", self._key_path)
        else:
            key = Fernet.generate_key()
            self._key_path.write_bytes(key)
            # Restrict key file to owner-only
            os.chmod(self._key_path, stat.S_IRUSR | stat.S_IWUSR)
            self._fernet = Fernet(key)
            logger.info("New vault key generated at %s", self._key_path)

        if self._vault_path.exists():
            self._load()
        else:
            self._save()
            logger.info("Empty vault created at %s", self._vault_path)

    def _load(self) -> None:
        """Load and decrypt the vault."""
        if not self._fernet:
            raise VaultError("Vault not initialized")
        encrypted = self._vault_path.read_bytes()
        decrypted = self._fernet.decrypt(encrypted)
        self._credentials = json.loads(decrypted)

    def _save(self) -> None:
        """Encrypt and save the vault."""
        if not self._fernet:
            raise VaultError("Vault not initialized")
        plaintext = json.dumps(self._credentials, indent=2).encode()
        encrypted = self._fernet.encrypt(plaintext)
        self._vault_path.write_bytes(encrypted)

    def store_credential(
        self,
        name: str,
        credential_type: str,
        value: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a named credential in the vault."""
        self._credentials[name] = {
            "type": credential_type,
            "value": value,
            "metadata": metadata or {},
        }
        self._save()
        logger.info("Credential '%s' stored (type=%s)", name, credential_type)

    def get_credential(self, name: str) -> dict[str, Any]:
        """Retrieve a credential by name. Raises VaultError if not found."""
        if name not in self._credentials:
            raise VaultError(f"Credential '{name}' not found in vault")
        return self._credentials[name]

    def remove_credential(self, name: str) -> None:
        """Remove a credential from the vault."""
        if name not in self._credentials:
            raise VaultError(f"Credential '{name}' not found in vault")
        del self._credentials[name]
        self._save()
        logger.info("Credential '%s' removed", name)

    def list_credentials(self) -> list[dict[str, str]]:
        """List all credential names and types (NOT the values)."""
        return [
            {"name": name, "type": cred["type"]}
            for name, cred in self._credentials.items()
        ]

    @property
    def count(self) -> int:
        return len(self._credentials)
