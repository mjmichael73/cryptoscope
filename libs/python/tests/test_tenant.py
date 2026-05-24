import pytest

from cryptoscope_shared.tenant import (
    MissingTenantError,
    TenantIdentity,
    current_tenant,
    set_tenant,
)


def test_missing_tenant_raises():
    with pytest.raises(MissingTenantError):
        current_tenant()


def test_set_and_read_tenant():
    set_tenant(TenantIdentity(id="t-1", slug="acme"))
    identity = current_tenant()
    assert identity.id == "t-1"
    assert identity.slug == "acme"


def test_empty_id_is_missing():
    set_tenant(TenantIdentity(id=""))
    with pytest.raises(MissingTenantError):
        current_tenant()
