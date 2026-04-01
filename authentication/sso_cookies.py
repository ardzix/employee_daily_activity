"""
Public SSO cookies shared across subdomains (names must match the Account portal).

When PUBLIC_AUTH_COOKIE_DOMAIN is set (e.g. .arnatech.id), the browser sends
arna_sso_access_token and arna_sso_refresh_token to all subdomains under that domain.
"""
from django.conf import settings


def copy_public_sso_cookies_to_session(request):
    """
    Copy arna_sso_* into the Django session when the browser sends them.

    If we only copied when the session had no access_token, an old employee session
    would block newer tokens from Account (same host). Prefer public cookies when
    their access value differs from the session.
    """
    access = request.COOKIES.get(settings.SSO_PUBLIC_ACCESS_COOKIE_NAME)
    if not access:
        return
    refresh = request.COOKIES.get(settings.SSO_PUBLIC_REFRESH_COOKIE_NAME) or ''
    session_access = request.session.get('access_token')
    session_refresh = request.session.get('refresh_token') or ''
    if session_access == access and session_refresh == refresh:
        return
    request.session['access_token'] = access
    request.session['refresh_token'] = refresh
    request.session.save()


def refresh_sso_session_tokens(request):
    """
    POST /api/auth/token/refresh/ using the session refresh token; update session.
    Returns new access token or None. Sets request._public_sso_cookie_tokens when
    PUBLIC_AUTH_COOKIE_DOMAIN is used so process_response can update arna_sso_*.
    """
    import requests

    refresh_token = request.session.get('refresh_token')
    if not refresh_token:
        return None
    try:
        response = requests.post(
            f'{settings.SSO_BASE_URL}/api/auth/token/refresh/',
            json={'refresh': refresh_token},
            headers={'Content-Type': 'application/json'},
            timeout=10,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        new_access = data.get('access')
        new_refresh = data.get('refresh')
        if not new_access:
            return None
        request.session['access_token'] = new_access
        if new_refresh:
            request.session['refresh_token'] = new_refresh
        request.session.save()
        if getattr(settings, 'PUBLIC_AUTH_COOKIE_DOMAIN', '').strip():
            request._public_sso_cookie_tokens = (
                new_access,
                new_refresh or refresh_token,
            )
        return new_access
    except Exception:
        return None


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
