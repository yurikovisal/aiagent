from meza.core.rbac import Permission, Role, has_permission, permissions_for


def test_admin_has_everything():
    assert permissions_for(Role.ADMIN) == set(Permission)


def test_viewer_cannot_write():
    perms = permissions_for(Role.VIEWER)
    assert Permission.WRITE_PRODUCTION not in perms
    assert Permission.MANAGE_USERS not in perms


def test_viewer_can_read_overview():
    assert has_permission(Role.VIEWER, Permission.READ_OVERVIEW)


def test_unknown_role_has_no_permissions():
    assert permissions_for("NOT_A_ROLE") == set()
    assert not has_permission("NOT_A_ROLE", Permission.READ_OVERVIEW)


def test_manager_cannot_approve_high_risk():
    assert Permission.APPROVE_HIGH not in permissions_for(Role.MANAGER)


def test_director_can_approve_both():
    perms = permissions_for(Role.DIRECTOR)
    assert Permission.APPROVE_LOW in perms
    assert Permission.APPROVE_HIGH in perms
