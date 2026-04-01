from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import login
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings

from authentication.sso_cookies import copy_public_sso_cookies_to_session, set_public_sso_auth_cookies


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """Middleware to handle SSO authentication and create Django sessions"""
    
    # Django middleware requirements
    async_mode = False
    sync_mode = True
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_response(self, request, response):
        """Refresh public SSO cookies when this middleware rotates JWTs via refresh."""
        tokens = getattr(request, '_public_sso_cookie_tokens', None)
        if tokens and getattr(settings, 'PUBLIC_AUTH_COOKIE_DOMAIN', '').strip():
            access, refresh = tokens
            set_public_sso_auth_cookies(response, access, refresh or '')
        return response
    
    def process_request(self, request):
        """Process incoming requests - use Django sessions primarily"""
        
        # No SSO cookie sync for static/media
        if (
            request.path.startswith('/static/')
            or request.path.startswith('/media/')
            or request.path == '/favicon.ico'
        ):
            return None

        # Sinkronkan arna_sso_* → session (lintas subdomain dengan Account portal)
        copy_public_sso_cookies_to_session(request)

        # Skip authentication for certain paths
        skip_paths = [
            '/',  # Root URL redirect
            '/auth/login/',
            '/auth/api/login/',
            '/auth/api/google-login/',
            '/auth/api/mfa/verify/',
            '/auth/api/register/',
            '/auth/api/verify-email/',
            '/auth/api/resend-email-otp/',
            '/auth/logout/',
            '/admin/',
        ]
        
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # If user is already authenticated via Django session, we're good
        if request.user.is_authenticated:
            return None
        
        # User is not authenticated - check if we have valid tokens to create a session
        access_token = request.session.get('access_token')
        refresh_token = request.session.get('refresh_token')
        
        if access_token:
            # Try to validate the access token and create a session
            user = self.validate_token_and_get_user(access_token)
            if user:
                login(request, user)
                return None
            else:
                # Access token is invalid/expired, try to refresh
                if refresh_token:
                    new_access_token = self.refresh_access_token(refresh_token, request)
                    if new_access_token:
                        # Try with new token
                        user = self.validate_token_and_get_user(new_access_token)
                        if user:
                            login(request, user)
                            return None
                
                # All tokens failed, clear session
                request.session.flush()
        
        # No valid authentication found
        if request.path.startswith('/api/') or request.content_type == 'application/json':
            return JsonResponse({'error': 'Authentication required'}, status=401)
        else:
            return redirect('authentication:login')
    
    def validate_token_and_get_user(self, access_token):
        from authentication.views import authenticate_with_token
        return authenticate_with_token(access_token)
    
    def refresh_access_token(self, refresh_token, request):
        """Attempt to refresh the access token using SSO service"""
        import requests
        from django.conf import settings
        
        try:
            response = requests.post(
                f"{settings.SSO_BASE_URL}/api/auth/token/refresh/",
                json={'refresh': refresh_token},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                new_access_token = data.get('access')
                new_refresh_token = data.get('refresh')  # Simple JWT rotates refresh tokens
                
                if new_access_token:
                    request.session['access_token'] = new_access_token
                    if new_refresh_token:
                        request.session['refresh_token'] = new_refresh_token
                    request.session.save()
                    # Public cookies updated in process_response
                    request._public_sso_cookie_tokens = (
                        new_access_token,
                        new_refresh_token or refresh_token,
                    )
                    return new_access_token
            
            return None
            
        except Exception as e:
            return None