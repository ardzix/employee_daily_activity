from functools import wraps

import jwt
from django.http import JsonResponse

from authentication.views import authenticate_with_token


def log_bearer_token_payload(token):
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        print("Bearer token payload:", payload)
        print("Bearer token fields:", list(payload.keys()))
        return payload
    except jwt.InvalidTokenError as exc:
        print("Failed to decode bearer token:", str(exc))
        return {}


def bearer_token_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        authorization = request.META.get('HTTP_AUTHORIZATION', '')
        scheme, _, token = authorization.partition(' ')

        if scheme.lower() != 'bearer' or not token:
            return JsonResponse({
                'error': 'Bearer token required',
            }, status=401)

        token = token.strip()
        token_payload = log_bearer_token_payload(token)

        user = authenticate_with_token(token)
        if not user:
            return JsonResponse({
                'error': 'Invalid or expired bearer token',
            }, status=401)

        request.user = user
        request.bearer_token = token
        request.bearer_token_payload = token_payload
        request.bearer_org_id = token_payload.get('org_id')
        request.bearer_tenant_id = request.GET.get('tenant_id') or token_payload.get('tenant_id')
        return view_func(request, *args, **kwargs)

    return wrapper
