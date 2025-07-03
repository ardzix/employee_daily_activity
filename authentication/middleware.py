from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import login
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib.auth.models import User
from employees.models import Employee


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """Middleware to handle SSO authentication and create Django sessions"""
    
    # Django middleware requirements
    async_mode = False
    sync_mode = True
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process incoming requests - use Django sessions primarily"""
        
        # Skip authentication for certain paths
        skip_paths = [
            '/',  # Root URL redirect
            '/auth/login/',
            '/auth/api/login/',
            '/auth/api/mfa/verify/',
            '/auth/logout/',
            '/admin/',
            '/static/',
            '/media/',
            '/favicon.ico',
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
        """Simple token validation and user retrieval"""
        try:
            import jwt
            from django.conf import settings
            from django.contrib.auth.models import User
            from employees.models import Employee
            
            # Decode token without verification to get user info
            unverified_payload = jwt.decode(access_token, options={"verify_signature": False})
            
            # Basic verification - just signature and expiration
            try:
                jwt.decode(
                    access_token,
                    settings.SSO_PUBLIC_KEY,
                    algorithms=[settings.JWT_ALGORITHM],
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_nbf": True,
                        "verify_iat": True,
                        "verify_aud": False,
                        "verify_iss": False,
                    }
                )
            except jwt.ExpiredSignatureError:
                return None
            except jwt.InvalidTokenError as e:
                return None
            
            # Extract user ID
            sso_user_id = unverified_payload.get('user_id')
            if not sso_user_id:
                return None
            
            # Find or create user (but not employee record)
            try:
                employee = Employee.objects.get(sso_user_id=str(sso_user_id))
                return employee.user
            except Employee.DoesNotExist:
                try:
                    return User.objects.get(username=f"sso_{sso_user_id}")
                except User.DoesNotExist:
                    # Create new user (admin will create employee record later)
                    username = f"sso_{sso_user_id}"
                    user = User.objects.create_user(
                        username=username,
                        email=f"{sso_user_id}@temp.local",
                        first_name="",
                        last_name=""
                    )
                    
                    return user
            
        except Exception as e:
            return None
    
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
                    return new_access_token
            
            return None
            
        except Exception as e:
            return None 