"""Local startup identity and fail-closed production/configured-root behavior."""
import pytest

from scripts import bootstrap_container_trust as bootstrap
from src.security.trust_roots import TrustRootNotFound, TrustRootStore


@pytest.fixture
def setup(reset_ops_db, tmp_path, monkeypatch):
    for key in ('FRONTLINE_TRUST_ROOT_PATH', 'FRONTLINE_TRUST_ROOT_KEY_ID', 'FRONTLINE_SIGNING_KEY', 'ENV', 'PILOT_HARDENED', 'SOC2_MODE'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('FRONTLINE_BOOTSTRAP_LOCAL_TRUST', '1')
    monkeypatch.setattr(bootstrap, 'REPO_ROOT', tmp_path)
    store = TrustRootStore(json_path=tmp_path/'trust-roots.json')
    # Isolate fallback public files from any developer key; DB/JSON stay real.
    monkeypatch.setattr(store, '_auto_import_initial_key', lambda con: {})
    monkeypatch.setattr(store, '_load_from_default_key', lambda: {})
    return tmp_path/'keys', store


def test_first_start_creates_owner_only_identity_and_restart_preserves_it(setup):
    directory, store = setup
    assert bootstrap.initialize(key_dir=directory, store=store) == 'local_trust_initialized'
    private = directory/'locker_ed25519.pem'
    before = private.read_bytes(), store.get_active_public_key()
    assert private.stat().st_mode & 0o777 == 0o600
    assert bootstrap.initialize(key_dir=directory, store=store) == 'existing_trust_unchanged'
    assert before == (private.read_bytes(), store.get_active_public_key())


@pytest.mark.parametrize('mode', ['production', 'explicit', 'no-opt-in'])
def test_production_and_operator_configuration_never_get_a_fallback_identity(setup, monkeypatch, mode):
    directory, store = setup
    if mode == 'production': monkeypatch.setenv('ENV', 'production')
    elif mode == 'explicit': monkeypatch.setenv('FRONTLINE_TRUST_ROOT_PATH', '/operator/chosen/missing.json')
    else: monkeypatch.delenv('FRONTLINE_BOOTSTRAP_LOCAL_TRUST')
    assert bootstrap.initialize(key_dir=directory, store=store) in {'operator_trust_required', 'operator_configured_trust_unchanged'}
    assert not directory.exists()
    with pytest.raises(TrustRootNotFound): store.get_active_public_key()


def test_revoked_identity_is_not_replaced(setup):
    directory, store = setup
    bootstrap.initialize(key_dir=directory, store=store)
    original = (directory/'locker_ed25519.pem').read_bytes()
    store.revoke_root('default-locker-key')
    with pytest.raises(TrustRootNotFound): bootstrap.initialize(key_dir=directory, store=store)
    assert (directory/'locker_ed25519.pem').read_bytes() == original


def test_orphan_public_key_is_not_overwritten(setup):
    directory, store = setup
    directory.mkdir()
    public = directory/'locker_ed25519.pub.pem'
    public.write_bytes(b'existing-public-key')
    with pytest.raises(RuntimeError, match='Restore'): bootstrap.initialize(key_dir=directory, store=store)
    assert public.read_bytes() == b'existing-public-key'
    assert not (directory/'locker_ed25519.pem').exists()


def test_broken_existing_store_is_not_replaced(setup):
    directory, store = setup
    store._json_path.write_text('broken operator store')
    with pytest.raises(RuntimeError, match='Repair'): bootstrap.initialize(key_dir=directory, store=store)
    assert store._json_path.read_text() == 'broken operator store'
    assert not directory.exists()
