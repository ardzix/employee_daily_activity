"""
Cookie publik lintas subdomain (nama disepakati dengan portal Account SSO).

Dengan PUBLIC_AUTH_COOKIE_DOMAIN=.arnatech.id, browser mengirim
arna_sso_access_token / arna_sso_refresh_token ke semua subdomain.
"""
from django.conf import settings


def copy_public_sso_cookies_to_session(request):
    """
    Salin token dari cookie publik ke session Django jika session belum punya access.
    Idempotent / aman dipanggil berulang.
    """
    if request.session.get('access_token'):
        return
    access = request.COOKIES.get(settings.SSO_PUBLIC_ACCESS_COOKIE_NAME)
    if not access:
        return
    refresh = request.COOKIES.get(settings.SSO_PUBLIC_REFRESH_COOKIE_NAME) or ''
    request.session['access_token'] = access
    request.session['refresh_token'] = refresh
    request.session.save()


def _cookie_params(max_age):
    domain = getattr(settings, 'PUBLIC_AUTH_COOKIE_DOMAIN', '') or ''
    domain = domain.strip() or None
    secure = getattr(settings, 'SESSION_COOKIE_SECURE', False)
    return {
        'max_age': max_age,
        'path': '/',
        'domain': domain,
        'secure': secure,
        'httponly': True,
        'samesite': getattr(settings, 'SSO_PUBLIC_COOKIE_SAMESITE', 'Lax'),
    }


def set_public_sso_auth_cookies(response, access_token, refresh_token, max_age=None):
    """Set cookie publik agar subdomain lain (mis. account.*) bisa memakai token yang sama."""
    if not getattr(settings, 'PUBLIC_AUTH_COOKIE_DOMAIN', '').strip():
        return response
    age = max_age if max_age is not None else getattr(settings, 'SESSION_COOKIE_AGE', 86400)
    opts = _cookie_params(age)
    response.set_cookie(
        settings.SSO_PUBLIC_ACCESS_COOKIE_NAME,
        access_token,
        **opts,
    )
    if refresh_token:
        response.set_cookie(
            settings.SSO_PUBLIC_REFRESH_COOKIE_NAME,
            refresh_token,
            **opts,
        )
    return response


def clear_public_sso_auth_cookies(response):
    """Hapus cookie publik (domain harus sama seperti saat set)."""
    if not getattr(settings, 'PUBLIC_AUTH_COOKIE_DOMAIN', '').strip():
        return response
    opts = _cookie_params(0)
    # Django menghapus cookie dengan max_age=0
    response.set_cookie(settings.SSO_PUBLIC_ACCESS_COOKIE_NAME, '', **opts)
    response.set_cookie(settings.SSO_PUBLIC_REFRESH_COOKIE_NAME, '', **opts)
    return response
