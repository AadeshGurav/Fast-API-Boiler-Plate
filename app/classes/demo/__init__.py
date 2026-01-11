"""Demo business classes showcasing User and RBAC systems."""

from __future__ import annotations

# Import all demo classes to ensure they are registered with ClassStore
from app.classes.demo import library_manager
from app.classes.demo import permission_workflow_demo
from app.classes.demo import rbac_management_demo
from app.classes.demo import user_management_demo

__all__ = [
    "LibraryManager",
    "PermissionWorkflowDemo",
    "RBACManagementDemo",
    "UserManagementDemo",
]
