"""Central browser SSO. All credentials remain in server-side sessions."""
import base64
import hashlib
import secrets
import time
import uuid
from urllib.parse import urlencode, unquote

import requests
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.crypto import constant_time_compare
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

CLIENT_ID = "arna-clockin"
SESSION_KEY = "central_app_session"


class SSOUnavailable(Exception):
    pass


def safe_path(value):
    from django.utils.http import url_has_allowed_host_and_scheme
    if not value or not isinstance(value, str):
        return "/dashboard/"
    decoded = unquote(value)
    if decoded.startswith("//") or "\\" in decoded or any(ord(char) < 32 for char in decoded):
        return "/dashboard/"
    return value if value.startswith("/") and url_has_allowed_host_and_scheme(value, allowed_hosts=set()) else "/dashboard/"


def sso_post(path, data, credential=None):
    try:
        response = requests.post(settings.SSO_BASE_URL.rstrip("/") + "/api/auth/sso/app-session/" + path,
            json=data, headers={"Authorization": "Bearer " + credential} if credential else {}, timeout=12,
            allow_redirects=False)
        if response.status_code in (400, 401, 403):
            return None
        if not response.ok or response.is_redirect:
            raise SSOUnavailable()
        return response.json()
    except (requests.RequestException, ValueError):
        raise SSOUnavailable() from None


def resolve(request):
    credential = request.session.get(SESSION_KEY)
    if not isinstance(credential, str) or len(credential) != 64:
        return None
    return sso_post("resolve/", {"client_id": CLIENT_ID}, credential)


def public_origin():
    # Fixed deployment origin; never derive a callback from forwarded browser headers.
    return settings.CENTRAL_SSO_APP_ORIGIN.rstrip("/")


@never_cache
@require_GET
def sign_in(request):
    verifier = secrets.token_urlsafe(48)
    state = secrets.token_urlsafe(32)
    request.session["central_pkce"] = {"state": state, "verifier": verifier,
        "expires_at": time.time() + 300,
        "return_to": safe_path(request.GET.get("next") or request.GET.get("return_to"))}
    params = {"client_id": CLIENT_ID, "redirect_uri": public_origin() + "/api/auth/callback", "state": state,
              "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode(),
              "code_challenge_method": "S256"}
    return redirect(settings.SSO_BASE_URL.rstrip("/") + "/login/?" + urlencode(params))


def local_user(profile):
    User = get_user_model()
    identity = str(uuid.UUID(str(profile.get("user_id", ""))))
    email = profile.get("email", "")
    if not isinstance(email, str) or "@" not in email:
        raise ValueError("Invalid SSO identity")
    user = User.objects.filter(sso_id=identity).first()
    if user is None:
        if User.objects.filter(email__iexact=email).exists():
            raise ValueError("This email belongs to another local identity")
        user = User(sso_id=identity, email=email, is_active=True)
        user.set_unusable_password()
        user.save()
    if not user.is_active:
        raise ValueError("Local account is disabled")
    return user


@never_cache
@require_GET
def callback(request):
    pkce = request.session.pop("central_pkce", {})
    state, code = request.GET.get("state", ""), request.GET.get("code", "")
    if (not code or not state or not constant_time_compare(state, pkce.get("state", ""))
            or pkce.get("expires_at", 0) <= time.time() or not pkce.get("verifier")
            or any(len(request.GET.getlist(k)) != 1 for k in ("code", "state"))):
        return HttpResponse("Tautan login tidak valid atau sudah kedaluwarsa. Mulai lagi dari halaman login.", status=400)
    try:
        result = sso_post("", {"grant_type": "authorization_code", "client_id": CLIENT_ID,
            "redirect_uri": public_origin() + "/api/auth/callback", "code": code, "code_verifier": pkce["verifier"]})
        if not result or not isinstance(result.get("session"), str) or len(result["session"]) != 64:
            return HttpResponse("SSO tidak dapat menyelesaikan login. Silakan mulai lagi.", status=401)
        request.session[SESSION_KEY] = result["session"]
        resolved = resolve(request)
        if not resolved:
            request.session.pop(SESSION_KEY, None)
            return HttpResponse("Session SSO sudah berakhir. Silakan masuk lagi.", status=401)
        user = local_user(resolved["profile"])
        login(request, user)
        request.session.set_expiry(min(int(result["expires_in"]), 28800))
        return redirect(safe_path(pkce.get("return_to")))
    except SSOUnavailable:
        return HttpResponse("SSO sedang tidak tersedia. Silakan coba lagi sebentar.", status=503)
    except (ValueError, KeyError, TypeError):
        request.session.pop(SESSION_KEY, None)
        return HttpResponse("Akun Clockin tidak dapat digunakan untuk identitas SSO ini.", status=403)


@never_cache
@require_http_methods(["GET", "POST"])
def sign_out(request):
    if request.method == "GET":
        return render(request, "authentication/central_logout.html")
    credential = request.session.get(SESSION_KEY)
    try:
        if credential:
            sso_post("revoke/", {"client_id": CLIENT_ID, "all": request.POST.get("all") == "true"}, credential)
    except SSOUnavailable:
        return HttpResponse("Tidak dapat menghubungi SSO untuk keluar. Silakan coba lagi.", status=503)
    logout(request)
    return redirect("/auth/signed-out/")


@never_cache
def signed_out(request):
    return HttpResponse('<h1>Anda sudah keluar dari Clockin</h1><a href="/auth/login/">Masuk kembali dengan Arna SSO</a>')


@require_GET
def admin_sign_in(request):
    # Central identity never grants local staff privileges implicitly.
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("/admin/")
    return HttpResponse("Akun ini tidak memiliki akses admin Clockin.", status=403)


class CentralSSOMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        public = ("/auth/login/", "/auth/logout/", "/auth/signed-out/", "/api/auth/callback", "/static/", "/media/", "/health/")
        if any(request.path.startswith(path) for path in public) or request.path == "/favicon.ico":
            return self.get_response(request)
        try:
            resolved = resolve(request)
            if resolved:
                user = local_user(resolved["profile"])
                if not request.user.is_authenticated or request.user.pk != user.pk:
                    login(request, user)
                request.sso_access_token = resolved["access"]
                return self.get_response(request)
        except SSOUnavailable:
            return HttpResponse("SSO sedang tidak tersedia. Silakan coba lagi sebentar.", status=503)
        except (ValueError, KeyError, TypeError):
            return HttpResponse("Akun Clockin tidak dapat digunakan untuk identitas SSO ini.", status=403)
        logout(request)
        if request.path.startswith("/api/") or request.content_type == "application/json":
            return JsonResponse({"error": "session_required", "detail": "Masuk melalui Arna SSO."}, status=401)
        return redirect("/auth/login/?" + urlencode({"next": safe_path(request.get_full_path())}))
