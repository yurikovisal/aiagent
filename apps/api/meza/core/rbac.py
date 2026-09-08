"""Role-based access control. Permissions are enforced in the backend, never only in the UI."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "ADMIN"
    DIRECTOR = "DIRECTOR"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"
    VIEWER = "VIEWER"


class Permission(StrEnum):
    # data reading
    READ_OVERVIEW = "read:overview"
    READ_SALES = "read:sales"
    READ_PROJECTS = "read:projects"
    READ_PRODUCTION = "read:production"
    READ_WAREHOUSE = "read:warehouse"
    READ_PROCUREMENT = "read:procurement"
    READ_FINANCE = "read:finance"
    READ_DOCUMENTS = "read:documents"
    READ_EMPLOYEES = "read:employees"
    READ_MARKETING = "read:marketing"
    READ_AI_OPS = "read:ai_ops"
    READ_AUDIT = "read:audit"
    # writing
    WRITE_SALES = "write:sales"
    WRITE_PROJECTS = "write:projects"
    WRITE_PRODUCTION = "write:production"
    WRITE_WAREHOUSE = "write:warehouse"
    WRITE_PROCUREMENT = "write:procurement"
    WRITE_FINANCE = "write:finance"
    WRITE_DOCUMENTS = "write:documents"
    WRITE_EMPLOYEES = "write:employees"
    WRITE_MARKETING = "write:marketing"
    # ai / governance
    USE_MEZA = "use:meza"
    APPROVE_LOW = "approve:low_risk"
    APPROVE_HIGH = "approve:high_risk"
    MANAGE_USERS = "manage:users"
    MANAGE_SYSTEM = "manage:system"
    IMPORT_DATA = "import:data"


ALL_READ = {p for p in Permission if p.value.startswith("read:")}
ALL_WRITE = {p for p in Permission if p.value.startswith("write:")}

ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),
    Role.DIRECTOR: ALL_READ
    | ALL_WRITE
    | {Permission.USE_MEZA, Permission.APPROVE_LOW, Permission.APPROVE_HIGH, Permission.IMPORT_DATA},
    Role.DEPARTMENT_HEAD: ALL_READ - {Permission.READ_AUDIT}
    | {
        Permission.WRITE_SALES,
        Permission.WRITE_PROJECTS,
        Permission.WRITE_PRODUCTION,
        Permission.WRITE_WAREHOUSE,
        Permission.WRITE_PROCUREMENT,
        Permission.WRITE_DOCUMENTS,
        Permission.WRITE_MARKETING,
        Permission.USE_MEZA,
        Permission.APPROVE_LOW,
        Permission.IMPORT_DATA,
    },
    Role.MANAGER: {
        Permission.READ_OVERVIEW,
        Permission.READ_SALES,
        Permission.READ_PROJECTS,
        Permission.READ_PRODUCTION,
        Permission.READ_WAREHOUSE,
        Permission.READ_PROCUREMENT,
        Permission.READ_DOCUMENTS,
        Permission.READ_MARKETING,
        Permission.WRITE_SALES,
        Permission.WRITE_PROJECTS,
        Permission.WRITE_DOCUMENTS,
        Permission.WRITE_MARKETING,
        Permission.USE_MEZA,
    },
    Role.EMPLOYEE: {
        Permission.READ_OVERVIEW,
        Permission.READ_PROJECTS,
        Permission.READ_PRODUCTION,
        Permission.READ_WAREHOUSE,
        Permission.READ_DOCUMENTS,
        Permission.READ_MARKETING,
        Permission.USE_MEZA,
    },
    Role.VIEWER: {Permission.READ_OVERVIEW, Permission.READ_PRODUCTION, Permission.READ_WAREHOUSE, Permission.READ_MARKETING},
}


def permissions_for(role: str | Role) -> set[Permission]:
    try:
        return ROLE_PERMISSIONS[Role(role)]
    except (ValueError, KeyError):
        return set()


def has_permission(role: str | Role, permission: Permission) -> bool:
    return permission in permissions_for(role)
