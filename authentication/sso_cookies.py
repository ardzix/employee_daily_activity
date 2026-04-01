"""
Public SSO cookies shared across subdomains (names must match the Account portal).

When PUBLIC_AUTH_COOKIE_DOMAIN is set (e.g. .arnatech.id), the browser sends
arna_sso_access_token and arna_sso_refresh_token to all subdomains under that domain.
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
    """Set public cookies so other subdomains (e.g. account.*) can reuse the same tokens."""
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
    """Clear public cookies (domain/path must match how they were set)."""
    if not getattr(settings, 'PUBLIC_AUTH_COOKIE_DOMAIN', '').strip():
        return response
    opts = _cookie_params(0)
    # max_age=0 clears the cookie in browsers
    response.set_cookie(settings.SSO_PUBLIC_ACCESS_COOKIE_NAME, '', **opts)
    response.set_cookie(settings.SSO_PUBLIC_REFRESH_COOKIE_NAME, '', **opts)
    return response
