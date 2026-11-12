"""Role-aware access helpers."""
from __future__ import annotations

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect


def role_required(role: str):
    """Allow only accounts with ``role``; everyone else is redirected home."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if request.user.role != role:
                messages.warning(
                    request, "That area is for a different kind of WBooks account."
                )
                return redirect("books:dashboard")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def parent_required(view_func):
    return role_required("parent")(view_func)


def child_required(view_func):
    return role_required("child")(view_func)
