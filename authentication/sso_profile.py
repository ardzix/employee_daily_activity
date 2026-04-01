"""
Fetch UserProfile from SSO API (swagger: GET /api/profiles/, definitions.UserProfile).
"""
import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings

from authentication.sso_cookies import refresh_sso_session_tokens

logger = logging.getLogger(__name__)


def _profiles_list_from_response(data: Any) -> Optional[list]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        r = data.get('results')
        if isinstance(r, list):
            return r
    return None


EMPTY_PROFILE: Dict[str, str] = {
    'full_name': '',
    'bio': '',
    'profile_picture': '',
    'phone_number': '',
    'user_name': '',
}


def _pick_profile(payload: Any, sso_user_id: str) -> Optional[dict]:
    if not isinstance(payload, list) or not payload:
        return None
    uid = (sso_user_id or '').strip()
    for item in payload:
        if not isinstance(item, dict):
            continue
        u = item.get('user')
        if u is not None and str(u).strip() == uid:
            return item
    if len(payload) == 1 and isinstance(payload[0], dict):
        return payload[0]
    return None


def fetch_sso_user_profile(request) -> Dict[str, str]:
    """
    Load the current user's profile from GET /api/profiles/ using Bearer access token.
    On 401, try refresh_sso_session_tokens once then retry.
    Returns a dict with keys: full_name, bio, profile_picture, phone_number, user_name.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return dict(EMPTY_PROFILE)

    access = request.session.get('access_token')
    if not access:
        return dict(EMPTY_PROFILE)

    def _request(tok: str):
        return requests.get(
            f'{settings.SSO_BASE_URL}/api/profiles/',
            headers={
                'Authorization': f'Bearer {tok}',
                'Accept': 'application/json',
            },
            timeout=15,
        )

    try:
        response = _request(access)
        if response.status_code == 401 and request.session.get('refresh_token'):
            new_tok = refresh_sso_session_tokens(request)
            if new_tok:
                access = new_tok
                response = _request(access)

        if response.status_code != 200:
            logger.warning(
                'SSO profiles list HTTP %s: %s',
                response.status_code,
                response.text[:200],
            )
            return dict(EMPTY_PROFILE)

        data = response.json()
        listings = _profiles_list_from_response(data)
        if listings is None:
            logger.warning('SSO profiles unexpected JSON shape: %s', type(data).__name__)
            return dict(EMPTY_PROFILE)
        raw = _pick_profile(listings, str(getattr(user, 'sso_id', '') or ''))
        if not raw:
            return dict(EMPTY_PROFILE)

        return {
            'full_name': (raw.get('full_name') or '') if isinstance(raw.get('full_name'), str) else '',
            'bio': (raw.get('bio') or '') if isinstance(raw.get('bio'), str) else '',
            'profile_picture': (raw.get('profile_picture') or '') if isinstance(raw.get('profile_picture'), str) else '',
            'phone_number': (raw.get('phone_number') or '') if isinstance(raw.get('phone_number'), str) else '',
            'user_name': (raw.get('user_name') or '') if isinstance(raw.get('user_name'), str) else '',
        }
    except Exception as exc:
        logger.exception('SSO profile fetch failed: %s', exc)
        return dict(EMPTY_PROFILE)
