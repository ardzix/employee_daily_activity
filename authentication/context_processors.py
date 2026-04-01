"""
Inject profile-completion reminder state into all templates (after login).
"""
import time

from django.conf import settings

PROFILE_REMINDER_SESSION_KEY = 'sso_profile_reminder_cache'


def profile_completion_reminder(request):
    """
    If SSO UserProfile is missing full_name, profile_picture, or phone_number,
    set show_profile_completion_reminder True so base.html can show a modal.

    Result is cached in session for a short TTL to avoid calling SSO on every request.
    """
    base = {
        'show_profile_completion_reminder': False,
        'profile_reminder_missing': [],
        'account_portal_profile_url': settings.ACCOUNT_PORTAL_PROFILE_URL,
    }

    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return base

    ttl = int(getattr(settings, 'PROFILE_COMPLETION_REMINDER_CACHE_SECONDS', 300))
    now = time.time()
    cache = request.session.get(PROFILE_REMINDER_SESSION_KEY)

    if (
        isinstance(cache, dict)
        and (now - cache.get('ts', 0)) < ttl
        and 'incomplete' in cache
        and 'missing' in cache
    ):
        incomplete = bool(cache['incomplete'])
        missing = list(cache['missing'])
        return {
            'show_profile_completion_reminder': incomplete,
            'profile_reminder_missing': missing if incomplete else [],
            'account_portal_profile_url': settings.ACCOUNT_PORTAL_PROFILE_URL,
        }

    from authentication.sso_profile import fetch_sso_user_profile

    profile = fetch_sso_user_profile(request)
    full_name = (profile.get('full_name') or '').strip()
    picture = (profile.get('profile_picture') or '').strip()
    phone = (profile.get('phone_number') or '').strip()

    missing = []
    if not full_name:
        missing.append('full_name')
    if not picture:
        missing.append('profile_picture')
    if not phone:
        missing.append('phone_number')

    incomplete = len(missing) > 0
    request.session[PROFILE_REMINDER_SESSION_KEY] = {
        'ts': now,
        'incomplete': incomplete,
        'missing': missing,
    }
    request.session.modified = True

    return {
        'show_profile_completion_reminder': incomplete,
        'profile_reminder_missing': missing,
        'account_portal_profile_url': settings.ACCOUNT_PORTAL_PROFILE_URL,
    }
