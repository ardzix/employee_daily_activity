from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.conf import settings
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
import requests
import json
from employees.models import Employee
from .forms import UserProfileForm
import jwt
import os

User = get_user_model()


def login_view(request):
    """Display login page"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    
    context = {
        'sso_url': settings.SSO_BASE_URL,
        'app_name': 'Employee Daily Activity Tracker',
        'google_client_id': os.getenv("GOOGLE_CLIENT_ID")
    }
    return render(request, 'authentication/login.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def api_register(request):
    """Handle user registration with SSO service"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return JsonResponse({'error': 'Email and password are required'}, status=400)
        
        # Call SSO registration API
        try:
            sso_response = requests.post(
                f"{settings.SSO_BASE_URL}/api/auth/register/",
                json={'email': email, 'password': password},
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
        except requests.exceptions.Timeout:
            return JsonResponse({'error': 'Registration service timeout. Please try again later.'}, status=503)
        except requests.exceptions.ConnectionError:
            return JsonResponse({'error': 'Cannot connect to registration service. Please check your internet connection.'}, status=503)
        except Exception as e:
            return JsonResponse({'error': f'Registration service error: {str(e)}'}, status=503)
        
        if sso_response.status_code == 201:
            return JsonResponse({'success': True, 'message': 'Registration successful. Please check your email for verification code.'})
        elif sso_response.status_code == 400:
            try:
                response_data = sso_response.json()
                # Handle different error response formats from SSO
                if isinstance(response_data, dict):
                    # Check for field-specific errors
                    if 'email' in response_data:
                        if isinstance(response_data['email'], list):
                            error_msg = response_data['email'][0]
                        else:
                            error_msg = str(response_data['email'])
                    elif 'password' in response_data:
                        if isinstance(response_data['password'], list):
                            error_msg = response_data['password'][0]
                        else:
                            error_msg = str(response_data['password'])
                    elif 'error' in response_data:
                        error_msg = response_data['error']
                    elif 'detail' in response_data:
                        error_msg = response_data['detail']
                    elif 'message' in response_data:
                        error_msg = response_data['message']
                    else:
                        # If it's a dict but no recognizable error field, stringify it
                        error_msg = str(response_data)
                else:
                    error_msg = str(response_data)
                
                return JsonResponse({'error': error_msg}, status=400)
            except (json.JSONDecodeError, KeyError):
                # If we can't parse the response, show the raw response
                return JsonResponse({'error': f'Registration failed: {sso_response.text}'}, status=400)
        else:
            # For other status codes, try to get the error message
            try:
                response_data = sso_response.json()
                error_msg = response_data.get('error', response_data.get('detail', f'Registration service returned status {sso_response.status_code}'))
                return JsonResponse({'error': error_msg}, status=503)
            except:
                return JsonResponse({'error': f'Registration service unavailable (Status: {sso_response.status_code})'}, status=503)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data provided'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Registration failed: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_verify_email(request):
    """Handle email verification with OTP"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        otp = data.get('otp')
        
        if not email or not otp:
            return JsonResponse({'error': 'Email and OTP are required'}, status=400)
        
        # Call SSO email verification API
        try:
            sso_response = requests.post(
                f"{settings.SSO_BASE_URL}/api/auth/verify-email/",
                json={'email': email, 'otp': otp},
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
        except requests.exceptions.Timeout:
            return JsonResponse({'error': 'Email verification service timeout. Please try again later.'}, status=503)
        except requests.exceptions.ConnectionError:
            return JsonResponse({'error': 'Cannot connect to verification service. Please check your internet connection.'}, status=503)
        except Exception as e:
            return JsonResponse({'error': f'Verification service error: {str(e)}'}, status=503)
        
        if sso_response.status_code == 200:
            return JsonResponse({'success': True, 'message': 'Email verified successfully'})
        elif sso_response.status_code == 400:
            try:
                response_data = sso_response.json()
                # Handle different error response formats
                if isinstance(response_data, dict):
                    if 'otp' in response_data:
                        if isinstance(response_data['otp'], list):
                            error_msg = response_data['otp'][0]
                        else:
                            error_msg = str(response_data['otp'])
                    elif 'email' in response_data:
                        if isinstance(response_data['email'], list):
                            error_msg = response_data['email'][0]
                        else:
                            error_msg = str(response_data['email'])
                    elif 'error' in response_data:
                        error_msg = response_data['error']
                    elif 'detail' in response_data:
                        error_msg = response_data['detail']
                    elif 'message' in response_data:
                        error_msg = response_data['message']
                    else:
                        error_msg = 'Invalid OTP or OTP expired'
                else:
                    error_msg = str(response_data)
                
                return JsonResponse({'error': error_msg}, status=400)
            except:
                return JsonResponse({'error': f'Email verification failed: {sso_response.text}'}, status=400)
        elif sso_response.status_code == 404:
            return JsonResponse({'error': 'User not found. Please register first.'}, status=404)
        else:
            try:
                response_data = sso_response.json()
                error_msg = response_data.get('error', response_data.get('detail', f'Verification service returned status {sso_response.status_code}'))
                return JsonResponse({'error': error_msg}, status=503)
            except:
                return JsonResponse({'error': f'Verification service unavailable (Status: {sso_response.status_code})'}, status=503)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data provided'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Email verification failed: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_resend_email_otp(request):
    """Handle OTP resend request"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if not email:
            return JsonResponse({'error': 'Email is required'}, status=400)
        
        # Call SSO resend OTP API
        try:
            sso_response = requests.post(
                f"{settings.SSO_BASE_URL}/api/auth/resend-email-otp/",
                json={'email': email},
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
        except requests.exceptions.Timeout:
            return JsonResponse({'error': 'Resend service timeout. Please try again later.'}, status=503)
        except requests.exceptions.ConnectionError:
            return JsonResponse({'error': 'Cannot connect to resend service. Please check your internet connection.'}, status=503)
        except Exception as e:
            return JsonResponse({'error': f'Resend service error: {str(e)}'}, status=503)
        
        if sso_response.status_code == 200:
            return JsonResponse({'success': True, 'message': 'OTP resent successfully'})
        elif sso_response.status_code == 400:
            try:
                response_data = sso_response.json()
                # Handle different error response formats
                if isinstance(response_data, dict):
                    if 'email' in response_data:
                        if isinstance(response_data['email'], list):
                            error_msg = response_data['email'][0]
                        else:
                            error_msg = str(response_data['email'])
                    elif 'error' in response_data:
                        error_msg = response_data['error']
                    elif 'detail' in response_data:
                        error_msg = response_data['detail']
                    elif 'message' in response_data:
                        error_msg = response_data['message']
                    else:
                        error_msg = 'Cannot resend OTP at this time. Please wait a few minutes before trying again.'
                else:
                    error_msg = str(response_data)
                
                return JsonResponse({'error': error_msg}, status=400)
            except:
                return JsonResponse({'error': f'Cannot resend OTP: {sso_response.text}'}, status=400)
        elif sso_response.status_code == 404:
            return JsonResponse({'error': 'User not found. Please register first.'}, status=404)
        else:
            try:
                response_data = sso_response.json()
                error_msg = response_data.get('error', response_data.get('detail', f'Resend service returned status {sso_response.status_code}'))
                return JsonResponse({'error': error_msg}, status=503)
            except:
                return JsonResponse({'error': f'Resend service unavailable (Status: {sso_response.status_code})'}, status=503)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data provided'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Resend OTP failed: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    """Handle API login with SSO service"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return JsonResponse({'error': 'Email and password are required'}, status=400)
        
        # Call SSO login API
        try:
            sso_response = requests.post(
                f"{settings.SSO_BASE_URL}/api/auth/login/",
                json={'email': email, 'password': password},
                headers={'Content-Type': 'application/json'},
                timeout=15  # Increased timeout
            )
            
        except requests.exceptions.Timeout:
            return JsonResponse({'error': 'Authentication service timeout. Please try again later.'}, status=503)
        except requests.exceptions.ConnectionError:
            return JsonResponse({'error': 'Cannot connect to authentication service. Please check your internet connection.'}, status=503)
        except Exception as e:
            return JsonResponse({'error': f'Authentication service error: {str(e)}'}, status=503)
        
        if sso_response.status_code == 200:
            response_data = sso_response.json()
            
            # Check if MFA is required
            if response_data.get('mfa_required'):
                return JsonResponse({
                    'mfa_required': True,
                    'email': email,
                    'message': 'MFA verification required'
                })
            
            # Login successful, we have tokens
            access_token = response_data.get('access')
            refresh_token = response_data.get('refresh')
            
            if access_token and refresh_token:
                # Store tokens in session
                request.session['access_token'] = access_token
                request.session['refresh_token'] = refresh_token
                
                # Authenticate user
                user = authenticate_with_token(access_token)
                
                if user:
                    login(request, user)
                    return JsonResponse({'success': True, 'redirect_url': '/dashboard/'})
                else:
                    return JsonResponse({'error': 'Failed to authenticate user. Please contact support.'}, status=401)
            else:
                return JsonResponse({'error': 'Invalid authentication response from SSO service'}, status=500)
        
        elif sso_response.status_code == 400:
            try:
                response_data = sso_response.json()
                # Handle different error response formats
                if isinstance(response_data, dict):
                    if 'email' in response_data:
                        if isinstance(response_data['email'], list):
                            error_msg = response_data['email'][0]
                        else:
                            error_msg = str(response_data['email'])
                    elif 'password' in response_data:
                        if isinstance(response_data['password'], list):
                            error_msg = response_data['password'][0]
                        else:
                            error_msg = str(response_data['password'])
                    elif 'error' in response_data:
                        error_msg = response_data['error']
                    elif 'detail' in response_data:
                        error_msg = response_data['detail']
                    elif 'message' in response_data:
                        error_msg = response_data['message']
                    elif 'non_field_errors' in response_data:
                        if isinstance(response_data['non_field_errors'], list):
                            error_msg = response_data['non_field_errors'][0]
                        else:
                            error_msg = str(response_data['non_field_errors'])
                    else:
                        error_msg = 'Invalid credentials'
                else:
                    error_msg = 'Invalid credentials'
                
                return JsonResponse({'error': error_msg}, status=400)
            except:
                return JsonResponse({'error': f'Login failed: {sso_response.text}'}, status=400)
        else:
            try:
                response_data = sso_response.json()
                error_msg = response_data.get('error', response_data.get('detail', f'Authentication service returned status {sso_response.status_code}'))
                return JsonResponse({'error': error_msg}, status=503)
            except:
                return JsonResponse({'error': f'Authentication service unavailable (Status: {sso_response.status_code})'}, status=503)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data provided'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Authentication failed: {str(e)}'}, status=500)
    
@csrf_exempt
@require_http_methods(["POST"])
def api_google_login(request):
    """Handle API Google login with SSO service"""
    try:
        data = json.loads(request.body)
        token = data.get('token')
        
        if not token:
            return JsonResponse({'error': 'Token required'}, status=400)
        
        # Call SSO login API
        try:
            sso_response = requests.post(
                f"{settings.SSO_BASE_URL}/api/auth/google-login/",
                json={'token': token},
                headers={'Content-Type': 'application/json'},
                timeout=15  # Increased timeout
            )
            
        except requests.exceptions.Timeout:
            return JsonResponse({'error': 'Authentication service timeout. Please try again later.'}, status=503)
        except requests.exceptions.ConnectionError:
            return JsonResponse({'error': 'Cannot connect to authentication service. Please check your internet connection.'}, status=503)
        except Exception as e:
            return JsonResponse({'error': f'Authentication service error: {str(e)}'}, status=503)
        
        if sso_response.status_code == 200:
            response_data = sso_response.json()
            email= response_data.get('email')
            # Check if MFA is required
            if response_data.get('mfa_required'):
                return JsonResponse({
                    'mfa_required': True,
                    'email': email,
                    'message': 'MFA verification required'
                })
            
            # Login successful, we have tokens
            access_token = response_data.get('access')
            refresh_token = response_data.get('refresh')
            
            if access_token and refresh_token:
                # Store tokens in session
                request.session['access_token'] = access_token
                request.session['refresh_token'] = refresh_token
                
                # Authenticate user
                user = authenticate_with_token(access_token)
                
                if user:
                    login(request, user)
                    return JsonResponse({'success': True, 'redirect_url': '/dashboard/'})
                else:
                    return JsonResponse({'error': 'Failed to authenticate user. Please contact support.'}, status=401)
            else:
                return JsonResponse({'error': 'Invalid authentication response from SSO service'}, status=500)
        
        elif sso_response.status_code == 400:
            try:
                response_data = sso_response.json()
                # Handle different error response formats
                if isinstance(response_data, dict):
                    if 'email' in response_data:
                        if isinstance(response_data['email'], list):
                            error_msg = response_data['email'][0]
                        else:
                            error_msg = str(response_data['email'])
                    elif 'error' in response_data:
                        error_msg = response_data['error']
                    elif 'detail' in response_data:
                        error_msg = response_data['detail']
                    elif 'message' in response_data:
                        error_msg = response_data['message']
                    elif 'non_field_errors' in response_data:
                        if isinstance(response_data['non_field_errors'], list):
                            error_msg = response_data['non_field_errors'][0]
                        else:
                            error_msg = str(response_data['non_field_errors'])
                    else:
                        error_msg = 'Invalid credentials'
                else:
                    error_msg = 'Invalid credentials'
                
                return JsonResponse({'error': error_msg}, status=400)
            except:
                return JsonResponse({'error': f'Login failed: {sso_response.text}'}, status=400)
        else:
            try:
                response_data = sso_response.json()
                error_msg = response_data.get('error', response_data.get('detail', f'Authentication service returned status {sso_response.status_code}'))
                return JsonResponse({'error': error_msg}, status=503)
            except:
                return JsonResponse({'error': f'Authentication service unavailable (Status: {sso_response.status_code})'}, status=503)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data provided'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Authentication failed: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def mfa_verify(request):
    """Handle MFA verification"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        mfa_token = data.get('mfa_token')
        
        if not email or not mfa_token:
            return JsonResponse({'error': 'Email and MFA token are required'}, status=400)
        
        # Call SSO MFA verify API
        try:
            sso_response = requests.post(
                f"{settings.SSO_BASE_URL}/api/auth/mfa/verify/",
                json={'email': email, 'mfa_token': mfa_token},
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
        except requests.exceptions.Timeout:
            return JsonResponse({'error': 'MFA verification service timeout. Please try again later.'}, status=503)
        except requests.exceptions.ConnectionError:
            return JsonResponse({'error': 'Cannot connect to MFA verification service. Please check your internet connection.'}, status=503)
        except Exception as e:
            return JsonResponse({'error': f'MFA verification service error: {str(e)}'}, status=503)
        
        if sso_response.status_code == 200:
            response_data = sso_response.json()
            access_token = response_data.get('access')
            refresh_token = response_data.get('refresh')
            
            if access_token and refresh_token:
                # Store tokens in session
                request.session['access_token'] = access_token
                request.session['refresh_token'] = refresh_token
                
                # Authenticate user using Simple JWT
                user = authenticate_with_token(access_token)
                if user:
                    login(request, user)
                    return JsonResponse({'success': True, 'redirect_url': '/dashboard/'})
                else:
                    return JsonResponse({'error': 'Failed to authenticate user after MFA verification. Please contact support.'}, status=401)
            else:
                return JsonResponse({'error': 'Invalid MFA verification response from SSO service'}, status=500)
        
        elif sso_response.status_code == 400:
            try:
                response_data = sso_response.json()
                # Handle different error response formats
                if isinstance(response_data, dict):
                    if 'mfa_token' in response_data:
                        if isinstance(response_data['mfa_token'], list):
                            error_msg = response_data['mfa_token'][0]
                        else:
                            error_msg = str(response_data['mfa_token'])
                    elif 'email' in response_data:
                        if isinstance(response_data['email'], list):
                            error_msg = response_data['email'][0]
                        else:
                            error_msg = str(response_data['email'])
                    elif 'error' in response_data:
                        error_msg = response_data['error']
                    elif 'detail' in response_data:
                        error_msg = response_data['detail']
                    elif 'message' in response_data:
                        error_msg = response_data['message']
                    elif 'non_field_errors' in response_data:
                        if isinstance(response_data['non_field_errors'], list):
                            error_msg = response_data['non_field_errors'][0]
                        else:
                            error_msg = str(response_data['non_field_errors'])
                    else:
                        error_msg = 'Invalid MFA token'
                else:
                    error_msg = 'Invalid MFA token'
                
                return JsonResponse({'error': error_msg}, status=400)
            except:
                return JsonResponse({'error': f'MFA verification failed: {sso_response.text}'}, status=400)
        elif sso_response.status_code == 404:
            return JsonResponse({'error': 'User not found. Please try logging in again.'}, status=404)
        else:
            try:
                response_data = sso_response.json()
                error_msg = response_data.get('error', response_data.get('detail', f'MFA verification service returned status {sso_response.status_code}'))
                return JsonResponse({'error': error_msg}, status=503)
            except:
                return JsonResponse({'error': f'MFA verification service unavailable (Status: {sso_response.status_code})'}, status=503)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data provided'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'MFA verification failed: {str(e)}'}, status=500)


def logout_view(request):
    """Logout user and revoke tokens"""
    refresh_token = request.session.get('refresh_token')
    
    # Attempt to logout from SSO service
    if refresh_token:
        try:
            requests.post(
                f"{settings.SSO_BASE_URL}/api/auth/logout/",
                json={'refresh': refresh_token},
                headers={'Content-Type': 'application/json'}
            )
        except:
            pass  # Continue with logout even if SSO logout fails
    
    # Clear session
    request.session.flush()
    
    # Django logout
    logout(request)
    
    messages.success(request, 'You have been successfully logged out.')
    return redirect('authentication:login')


@login_required
def profile_view(request):
    """Display and handle user profile editing"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            # Username should remain as sso_id and not change when email changes
            user.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('authentication:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserProfileForm(instance=request.user)
    
    context = {
        'user': request.user,
        'employee': getattr(request.user, 'employee_profile', None),
        'form': form,
    }
    return render(request, 'authentication/profile.html', context)


def refresh_token_view(request):
    """Refresh JWT access token"""
    refresh_token = request.session.get('refresh_token')
    
    if not refresh_token:
        return JsonResponse({'error': 'No refresh token available'}, status=401)
    
    try:
        response = requests.post(
            f"{settings.SSO_BASE_URL}/api/auth/token/refresh/",
            json={'refresh': refresh_token},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            new_access_token = data.get('access')
            new_refresh_token = data.get('refresh')  # Simple JWT rotates refresh tokens
            
            if new_access_token:
                request.session['access_token'] = new_access_token
                if new_refresh_token:
                    request.session['refresh_token'] = new_refresh_token
                return JsonResponse({
                    'access': new_access_token,
                    'refresh': new_refresh_token
                })
            else:
                return JsonResponse({'error': 'Invalid response from token service'}, status=500)
        else:
            # Refresh token is invalid, need to login again
            request.session.flush()
            logout(request)
            return JsonResponse({'error': 'Token expired, please login again'}, status=401)
            
    except Exception as e:
        return JsonResponse({'error': f'Token refresh failed: {str(e)}'}, status=500)


def authenticate_with_token(access_token):
    """Authenticate user using access token by validating JWT and extracting user info"""
    try:
        # First, let's decode the token to see what claims it has (without verification)
        unverified_payload = jwt.decode(access_token, options={"verify_signature": False})
        
        # Simple validation - just check if token is properly signed with our public key
        try:
            # Basic verification - just signature and expiration
            jwt.decode(
                access_token,
                settings.SSO_PUBLIC_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": False,  # Skip audience verification
                    "verify_iss": False,  # Skip issuer verification
                }
            )
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError as e:
            return None
        
        # Extract user information from unverified payload (we trust it since signature is valid)
        sso_user_id = unverified_payload.get('user_id')
        
        if not sso_user_id:
            return None
        
        # Try to find existing user by sso_id
        try:
            user = User.objects.get(sso_id=str(sso_user_id))
            
            # Update tokens
            user.sso_access_token = access_token
            user.save()
            
            return user
            
        except User.DoesNotExist:
            # Create new user with sso_id
            user = User.objects.create(
                sso_id=str(sso_user_id),
                # email will be auto-generated as <sso_id>@arnatech.id
                # username will be set to sso_id
                first_name="",
                last_name="",
                sso_access_token=access_token,
                is_active=True
            )
            
            return user
                
    except Exception as e:
        return None
