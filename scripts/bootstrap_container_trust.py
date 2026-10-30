"""Initialize a new local pilot's trust root; never replace an existing trust identity."""
from __future__ import annotations

import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.config import REPO_ROOT
from src.security.harden import is_production_like
from src.security.trust_roots import TrustRootStore


def initialize(*, key_dir: Path | None = None, store=None) -> str:
    store = store or TrustRootStore()
    # Operator-selected identity is never silently replaced by a bootstrap key.
    if any(os.getenv(key) is not None for key in ('FRONTLINE_TRUST_ROOT_PATH', 'FRONTLINE_TRUST_ROOT_KEY_ID', 'FRONTLINE_SIGNING_KEY')):
        return 'operator_configured_trust_unchanged'
    roots = store.load_all_roots()
    if roots:
        store.get_active_public_key()  # revoked/broken configuration fails closed
        return 'existing_trust_unchanged'
    if store._json_path and store._json_path.exists():
        raise RuntimeError('Existing trust store has no usable root. Repair it explicitly; bootstrap will not replace it.')
    if os.getenv('FRONTLINE_BOOTSTRAP_LOCAL_TRUST') != '1' or is_production_like():
        return 'operator_trust_required'
    directory = key_dir or REPO_ROOT/'data/locker_keys'
    private_path = directory/'locker_ed25519.pem'
    public_path = directory/'locker_ed25519.pub.pem'
    if public_path.exists() and not private_path.exists():
        raise RuntimeError('Existing public key has no private key. Restore its original key; bootstrap will not rotate it.')
    directory.mkdir(parents=True, exist_ok=True)
    if private_path.exists():
        if private_path.stat().st_mode & 0o077:
            raise RuntimeError('Existing locker private key must have owner-only permissions')
        private = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
        if not isinstance(private, Ed25519PrivateKey):
            raise RuntimeError('Existing locker key is not Ed25519')
    else:
        private = Ed25519PrivateKey.generate()
        encoded = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        # O_EXCL prevents replacement if another first-start process wins.
        with os.fdopen(os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as file:
            file.write(encoded)
    public = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    if public_path.exists():
        if public_path.read_bytes() != public:
            raise RuntimeError('Existing private/public locker keys disagree; no key was replaced')
    else:
        with os.fdopen(os.open(public_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644), 'wb') as file:
            file.write(public)
    store.register_root(key_id='default-locker-key', public_key_pem=public.decode(), created_by='local-container-first-start')
    store.get_active_public_key()
    return 'local_trust_initialized'


if __name__ == '__main__':
    print('Container trust:', initialize())
