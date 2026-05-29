"""Reusable DRF object-level permissions."""
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Authenticated users may read any object; only the owner may write it.

    The owning relation defaults to ``user``; set ``owner_field`` on the view to
    point at a different FK (e.g. ``author`` for forum content).
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner_field = getattr(view, "owner_field", "user")
        return getattr(obj, f"{owner_field}_id", None) == request.user.id
