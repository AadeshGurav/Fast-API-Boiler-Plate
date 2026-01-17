"""Demo business classes showcasing User and RBAC systems."""

from __future__ import annotations

# Import all demo classes to ensure they are registered with ClassStore
from app.classes.demo import (
    library_manager,
    permission_workflow_demo,
    rbac_management_demo,
    user_management_demo,
)

__all__ = [
    "library_manager",
    "permission_workflow_demo",
    "rbac_management_demo",
    "user_management_demo",
]
