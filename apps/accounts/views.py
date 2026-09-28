"""Usuarios del laboratorio, roles, mi perfil y cambio de clave (Fase 11b). Las vistas
sólo orquestan: formularios + services/selectors."""
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.forms import LabUserForm, PasswordChangeForm, ProfileForm
from apps.accounts.models import User
from apps.accounts.permissions import ADMIN_ROLES, role_abilities, role_required
from apps.accounts.selectors import lab_users as q
from apps.accounts.services import lab_users as svc
from apps.core.exceptions import ApplicationError


def _user(pk) -> User:
    try:
        return q.get_lab_user(pk=pk)
    except (User.DoesNotExist, ValidationError, ValueError) as exc:
        raise Http404("Usuario no encontrado.") from exc


@role_required(*ADMIN_ROLES)
def user_list(request):
    return render(request, "lab_users/list.html", {
        "users": q.lab_users(query=request.GET.get("q", ""),
                             show_inactive=request.GET.get("inactivos") == "1"),
        "query": request.GET.get("q", ""), "show_inactive": request.GET.get("inactivos") == "1",
    })


@role_required(*ADMIN_ROLES)
def user_new(request):
    form = LabUserForm(request.POST or None, initial={"roles": []})
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            user, password = svc.create_lab_user(
                username=data["username"], first_name=data["first_name"],
                last_name=data["last_name"], email=data["email"], phone=data["phone"],
                roles=data["roles"], password=data["password"], by=request.user)
            svc.update_lab_user(user=user, data=data, roles=data["roles"], by=request.user)
        except ApplicationError as exc:
            form.add_error(None, exc.message)
        else:
            return _show_password(request, user, password, created=True)
    return render(request, "lab_users/form.html", {"form": form, "creating": True})


def _show_password(request, user, password, *, created: bool):
    """La clave temporal se muestra una sola vez (no se guarda en claro en ningún lado)."""
    return render(request, "lab_users/password_shown.html", {
        "target": user, "password": password, "created": created})


@role_required(*ADMIN_ROLES)
def user_edit(request, pk):
    user = _user(pk)
    initial = {f: getattr(user, f) for f in svc.PROFILE_FIELDS}
    initial.update(username=user.username, roles=svc.role_codes(user))
    form = LabUserForm(request.POST or None, initial=initial, editing=True)
    if request.method == "POST" and form.is_valid():
        try:
            svc.update_lab_user(user=user, data=form.cleaned_data,
                                roles=form.cleaned_data["roles"], by=request.user)
        except ApplicationError as exc:
            form.add_error(None, exc.message)
        else:
            messages.success(request, f"Usuario {user.username} actualizado.")
            return redirect("lab_users:list")
    return render(request, "lab_users/form.html", {"form": form, "target": user})


@role_required(*ADMIN_ROLES)
@require_POST
def user_toggle(request, pk):
    user = _user(pk)
    try:
        svc.set_active(user=user, active=not user.is_active, by=request.user)
    except ApplicationError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, f"Usuario {user.username} "
                         f"{'activado' if user.is_active else 'desactivado'}.")
    return redirect("lab_users:edit", pk=user.pk)


@role_required(*ADMIN_ROLES)
@require_POST
def user_reset_password(request, pk):
    user = _user(pk)
    return _show_password(request, user, svc.reset_password(user=user, by=request.user),
                          created=False)


@role_required(*ADMIN_ROLES)
def roles(request):
    all_roles = q.all_roles()
    return render(request, "lab_users/roles.html", {
        "roles": all_roles,
        "rows": [(label, [r.code in codes for r in all_roles])
                 for label, codes in role_abilities()],
    })


# Cuenta propia -------------------------------------------------------------------------
@login_required
def profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        svc.update_profile(form=form)
        messages.success(request, "Perfil guardado.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form,
                                                     "roles": svc.role_codes(request.user)})


@login_required
def password(request):
    form = PasswordChangeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            svc.change_password(user=request.user, current=form.cleaned_data["current"],
                                new=form.cleaned_data["new"])
        except ApplicationError as exc:
            form.add_error(None, exc.message)
        else:
            update_session_auth_hash(request, request.user)  # no cierra la sesión
            messages.success(request, "Clave cambiada.")
            return redirect("tenant-home")
    return render(request, "accounts/password.html", {
        "form": form, "forced": request.user.must_change_password})
