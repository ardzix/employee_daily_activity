from django.http import JsonResponse


def _json_request(schema_name):
    return {
        'required': True,
        'content': {
            'application/json': {
                'schema': {'$ref': f'#/components/schemas/{schema_name}'},
            },
        },
    }


def _response(description, schema_name=None):
    response = {'description': description}
    if schema_name:
        response['content'] = {
            'application/json': {
                'schema': {'$ref': f'#/components/schemas/{schema_name}'},
            },
        }
    return response


OPENAPI_SCHEMA = {
    'openapi': '3.0.3',
    'info': {
        'title': 'Employee Daily Activity Tracker API',
        'description': 'API documentation for employee daily activity tracking.',
        'version': '1.0.0',
    },
    'servers': [{'url': '/'}],
    'paths': {
        '/auth/api/register/': {
            'post': {
                'tags': ['Authentication'],
                'summary': 'Register user',
                'requestBody': _json_request('RegisterRequest'),
                'responses': {
                    '200': _response('Registration accepted', 'SuccessMessage'),
                    '400': _response('Invalid registration payload', 'ErrorMessage'),
                    '503': _response('SSO registration service unavailable', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/verify-email/': {
            'post': {
                'tags': ['Authentication'],
                'summary': 'Verify email OTP',
                'requestBody': _json_request('VerifyEmailRequest'),
                'responses': {
                    '200': _response('Email verified', 'SuccessMessage'),
                    '400': _response('Invalid or expired OTP', 'ErrorMessage'),
                    '404': _response('User not found', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/resend-email-otp/': {
            'post': {
                'tags': ['Authentication'],
                'summary': 'Resend email OTP',
                'requestBody': _json_request('ResendEmailOtpRequest'),
                'responses': {
                    '200': _response('OTP resent', 'SuccessMessage'),
                    '400': _response('Cannot resend OTP', 'ErrorMessage'),
                    '404': _response('User not found', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/login/': {
            'post': {
                'tags': ['Authentication'],
                'summary': 'Login with email and password',
                'requestBody': _json_request('LoginRequest'),
                'responses': {
                    '200': _response('Login successful or MFA required', 'LoginResponse'),
                    '400': _response('Invalid credentials', 'ErrorMessage'),
                    '503': _response('SSO authentication service unavailable', 'ErrorMessage'),
                },
            },
        },
        '/auth/bnk/login/': {
            'post': {
                'tags': ['Authentication Bearer'],
                'summary': 'Login and return JWT tokens for Bearer API clients',
                'requestBody': _json_request('LoginRequest'),
                'responses': {
                    '200': _response('JWT tokens returned or MFA required', 'BearerLoginResponse'),
                    '400': _response('Invalid login payload', 'ErrorMessage'),
                    '503': _response('SSO authentication service unavailable', 'ErrorMessage'),
                },
            },
        },
        '/auth/bnk/mfa/verify/': {
            'post': {
                'tags': ['Authentication Bearer'],
                'summary': 'Verify MFA and return JWT tokens for Bearer API clients',
                'requestBody': _json_request('MfaVerifyRequest'),
                'responses': {
                    '200': _response('JWT tokens returned', 'BearerLoginResponse'),
                    '400': _response('Invalid MFA payload', 'ErrorMessage'),
                    '503': _response('SSO MFA service unavailable', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/google-login/': {
            'post': {
                'tags': ['Authentication'],
                'summary': 'Login with Google token',
                'requestBody': _json_request('GoogleLoginRequest'),
                'responses': {
                    '200': _response('Login successful or MFA required', 'LoginResponse'),
                    '400': _response('Invalid token', 'ErrorMessage'),
                    '503': _response('SSO authentication service unavailable', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/profile/': {
            'get': {
                'tags': ['Authentication'],
                'summary': 'Get authenticated user profile',
                'security': [{'sessionAuth': []}],
                'responses': {
                    '200': _response('Profile returned', 'ProfileResponse'),
                    '401': _response('Login required', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/mfa/verify/': {
            'post': {
                'tags': ['Authentication'],
                'summary': 'Verify MFA token',
                'requestBody': _json_request('MfaVerifyRequest'),
                'responses': {
                    '200': _response('MFA verified', 'SuccessRedirect'),
                    '400': _response('Invalid MFA token', 'ErrorMessage'),
                    '401': _response('MFA token expired or invalid', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/token/refresh/': {
            'post': {
                'tags': ['Authentication'],
                'summary': 'Refresh access token from session refresh token',
                'responses': {
                    '200': _response('Token refreshed', 'TokenRefreshResponse'),
                    '401': _response('No refresh token available', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/mfa/status/': {
            'get': {
                'tags': ['MFA'],
                'summary': 'Get MFA status',
                'security': [{'sessionAuth': []}],
                'responses': {
                    '200': _response('MFA status returned', 'MfaStatusResponse'),
                    '401': _response('Not authenticated', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/mfa/set/': {
            'post': {
                'tags': ['MFA'],
                'summary': 'Start MFA setup',
                'security': [{'sessionAuth': []}],
                'responses': {
                    '200': _response('MFA setup data returned'),
                    '401': _response('Not authenticated', 'ErrorMessage'),
                    '503': _response('SSO MFA service unavailable', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/mfa/disable/': {
            'post': {
                'tags': ['MFA'],
                'summary': 'Disable MFA',
                'security': [{'sessionAuth': []}],
                'requestBody': _json_request('MfaDisableRequest'),
                'responses': {
                    '200': _response('MFA disabled'),
                    '401': _response('Not authenticated', 'ErrorMessage'),
                    '503': _response('SSO MFA service unavailable', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/passkeys/': {
            'get': {
                'tags': ['Passkeys'],
                'summary': 'List passkeys',
                'security': [{'sessionAuth': []}],
                'responses': {
                    '200': _response('Passkey list returned'),
                    '401': _response('Not authenticated', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/passkeys/register/begin/': {
            'get': {
                'tags': ['Passkeys'],
                'summary': 'Begin passkey registration',
                'security': [{'sessionAuth': []}],
                'responses': {
                    '200': _response('PublicKeyCredentialCreationOptions returned'),
                    '401': _response('Not authenticated', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/passkeys/register/complete/': {
            'post': {
                'tags': ['Passkeys'],
                'summary': 'Complete passkey registration',
                'security': [{'sessionAuth': []}],
                'requestBody': _json_request('PasskeyCredentialRequest'),
                'responses': {
                    '200': _response('Passkey registered'),
                    '401': _response('Not authenticated', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/passkeys/{passkey_id}/': {
            'delete': {
                'tags': ['Passkeys'],
                'summary': 'Delete passkey',
                'security': [{'sessionAuth': []}],
                'parameters': [
                    {
                        'name': 'passkey_id',
                        'in': 'path',
                        'required': True,
                        'schema': {'type': 'integer'},
                    },
                ],
                'responses': {
                    '200': _response('Passkey deleted'),
                    '401': _response('Not authenticated', 'ErrorMessage'),
                    '503': _response('SSO passkey service unavailable', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/passkeys/login/begin/': {
            'get': {
                'tags': ['Passkeys'],
                'summary': 'Begin passkey login',
                'responses': {
                    '200': _response('PublicKeyCredentialRequestOptions returned'),
                    '503': _response('SSO passkey service unavailable', 'ErrorMessage'),
                },
            },
        },
        '/auth/api/passkeys/login/complete/': {
            'post': {
                'tags': ['Passkeys'],
                'summary': 'Complete passkey login',
                'requestBody': _json_request('PasskeyCredentialRequest'),
                'responses': {
                    '200': _response('Login successful', 'SuccessRedirect'),
                    '500': _response('Invalid SSO response', 'ErrorMessage'),
                    '503': _response('SSO passkey service unavailable', 'ErrorMessage'),
                },
            },
        },
        '/activities/api/check-in/': {
            'post': {
                'tags': ['Activities'],
                'summary': 'Submit daily check-in',
                'security': [{'sessionAuth': []}],
                'requestBody': _json_request('CheckInRequest'),
                'responses': {
                    '200': _response('Check-in submitted', 'ActivityResponse'),
                    '400': _response('Invalid check-in payload', 'ErrorMessage'),
                    '401': _response('Login required', 'ErrorMessage'),
                },
            },
        },
        '/activities/api/check-out/': {
            'post': {
                'tags': ['Activities'],
                'summary': 'Submit daily check-out',
                'security': [{'sessionAuth': []}],
                'requestBody': _json_request('CheckOutRequest'),
                'responses': {
                    '200': _response('Check-out submitted', 'ActivityResponse'),
                    '400': _response('Invalid check-out payload', 'ErrorMessage'),
                    '401': _response('Login required', 'ErrorMessage'),
                },
            },
        },
        '/activities/api/status/': {
            'get': {
                'tags': ['Activities'],
                'summary': 'Get current daily activity status',
                'security': [{'sessionAuth': []}],
                'responses': {
                    '200': _response('Activity status returned', 'ActivityStatusResponse'),
                    '401': _response('Login required', 'ErrorMessage'),
                },
            },
        },
        '/activities/api/history/': {
            'get': {
                'tags': ['Activities'],
                'summary': 'Get activity history for the authenticated user',
                'security': [{'sessionAuth': []}],
                'parameters': [
                    {
                        'name': 'limit',
                        'in': 'query',
                        'required': False,
                        'schema': {
                            'type': 'integer',
                            'default': 30,
                            'minimum': 1,
                            'maximum': 100,
                        },
                        'description': 'Maximum number of history records to return.',
                    },
                ],
                'responses': {
                    '200': _response('Activity history returned', 'ActivityHistoryResponse'),
                    '401': _response('Login required', 'ErrorMessage'),
                },
            },
        },
        '/activities/bnk/check-in/': {
            'post': {
                'tags': ['BNK Service'],
                'summary': 'Submit daily check-in with Bearer token',
                'security': [{'bearerAuth': []}],
                'requestBody': _json_request('CheckInRequest'),
                'responses': {
                    '200': _response('Check-in submitted', 'ActivityResponse'),
                    '400': _response('Invalid check-in payload', 'ErrorMessage'),
                    '401': _response('Invalid or missing bearer token', 'ErrorMessage'),
                },
            },
        },
        '/activities/bnk/check-out/': {
            'post': {
                'tags': ['BNK Service'],
                'summary': 'Submit daily check-out with Bearer token',
                'security': [{'bearerAuth': []}],
                'requestBody': _json_request('CheckOutRequest'),
                'responses': {
                    '200': _response('Check-out submitted', 'ActivityResponse'),
                    '400': _response('Invalid check-out payload', 'ErrorMessage'),
                    '401': _response('Invalid or missing bearer token', 'ErrorMessage'),
                },
            },
        },
        '/activities/bnk/status/': {
            'get': {
                'tags': ['BNK Service'],
                'summary': 'Get current daily activity status with Bearer token',
                'security': [{'bearerAuth': []}],
                'responses': {
                    '200': _response('Activity status returned', 'ActivityStatusResponse'),
                    '401': _response('Invalid or missing bearer token', 'ErrorMessage'),
                },
            },
        },
        '/activities/bnk/history/': {
            'get': {
                'tags': ['BNK Service'],
                'summary': 'Get activity history with Bearer token',
                'security': [{'bearerAuth': []}],
                'parameters': [
                    {
                        'name': 'limit',
                        'in': 'query',
                        'required': False,
                        'schema': {
                            'type': 'integer',
                            'default': 30,
                            'minimum': 1,
                            'maximum': 100,
                        },
                        'description': 'Maximum number of history records to return.',
                    },
                ],
                'responses': {
                    '200': _response('Activity history returned', 'ActivityHistoryResponse'),
                    '401': _response('Invalid or missing bearer token', 'ErrorMessage'),
                },
            },
        },
    },
    'components': {
        'securitySchemes': {
            'sessionAuth': {
                'type': 'apiKey',
                'in': 'cookie',
                'name': 'sessionid',
            },
            'bearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            },
        },
        'schemas': {
            'RegisterRequest': {
                'type': 'object',
                'required': ['email', 'password'],
                'properties': {
                    'email': {'type': 'string', 'format': 'email'},
                    'password': {'type': 'string', 'format': 'password'},
                    'first_name': {'type': 'string'},
                    'last_name': {'type': 'string'},
                },
            },
            'VerifyEmailRequest': {
                'type': 'object',
                'required': ['email', 'otp'],
                'properties': {
                    'email': {'type': 'string', 'format': 'email'},
                    'otp': {'type': 'string'},
                },
            },
            'ResendEmailOtpRequest': {
                'type': 'object',
                'required': ['email'],
                'properties': {'email': {'type': 'string', 'format': 'email'}},
            },
            'LoginRequest': {
                'type': 'object',
                'required': ['email', 'password'],
                'properties': {
                    'email': {'type': 'string', 'format': 'email'},
                    'password': {'type': 'string', 'format': 'password'},
                },
            },
            'GoogleLoginRequest': {
                'type': 'object',
                'required': ['token'],
                'properties': {'token': {'type': 'string'}},
            },
            'MfaVerifyRequest': {
                'type': 'object',
                'required': ['token', 'mfa_token'],
                'properties': {
                    'token': {'type': 'string'},
                    'mfa_token': {'type': 'string'},
                },
            },
            'MfaDisableRequest': {
                'type': 'object',
                'properties': {
                    'password': {'type': 'string', 'format': 'password'},
                    'totp': {'type': 'string'},
                },
            },
            'PasskeyCredentialRequest': {
                'type': 'object',
                'required': ['id', 'rawId', 'response', 'type'],
                'properties': {
                    'id': {'type': 'string'},
                    'rawId': {'type': 'string'},
                    'response': {'type': 'object'},
                    'type': {'type': 'string', 'example': 'public-key'},
                    'key_name': {'type': 'string'},
                },
            },
            'CheckInRequest': {
                'type': 'object',
                'properties': {
                    'lat': {'type': 'string', 'example': '-6.200000'},
                    'long': {'type': 'string', 'example': '106.816666'},
                    'planned_activities': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'title': {'type': 'string'},
                                'description': {'type': 'string'},
                                'priority': {'type': 'integer'},
                            },
                        },
                    },
                    'daily_goals': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'title': {'type': 'string'},
                                'description': {'type': 'string'},
                                'priority': {'type': 'integer'},
                                'target_value': {'type': 'string'},
                            },
                        },
                    },
                    'morning_problems': {'type': 'string'},
                },
            },
            'CheckOutRequest': {
                'type': 'object',
                'properties': {
                    'lat': {'type': 'string', 'example': '-6.200000'},
                    'long': {'type': 'string', 'example': '106.816666'},
                    'activity_updates': {
                        'type': 'array',
                        'items': {'type': 'object'},
                    },
                    'goal_updates': {
                        'type': 'array',
                        'items': {'type': 'object'},
                    },
                    'additional_activities': {
                        'type': 'array',
                        'items': {'type': 'object'},
                    },
                    'afternoon_problems': {'type': 'string'},
                },
            },
            'SuccessMessage': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                },
            },
            'SuccessRedirect': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'redirect_url': {'type': 'string'},
                },
            },
            'LoginResponse': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'redirect_url': {'type': 'string'},
                    'mfa_required': {'type': 'boolean'},
                    'token': {'type': 'string'},
                    'message': {'type': 'string'},
                },
            },
            'BearerLoginResponse': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'token_type': {'type': 'string', 'example': 'Bearer'},
                    'access': {'type': 'string'},
                    'refresh': {'type': 'string'},
                    'mfa_required': {'type': 'boolean'},
                    'token': {'type': 'string'},
                    'email': {'type': 'string', 'format': 'email'},
                    'message': {'type': 'string'},
                    'user': {'$ref': '#/components/schemas/ProfileUser'},
                },
            },
            'ProfileResponse': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'user': {'$ref': '#/components/schemas/ProfileUser'},
                    'employee': {
                        'oneOf': [
                            {'$ref': '#/components/schemas/ProfileEmployee'},
                            {'type': 'null'},
                        ],
                    },
                    'sso_profile': {'type': 'object'},
                    'account_portal_profile_url': {'type': 'string', 'format': 'uri'},
                },
            },
            'ProfileUser': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'email': {'type': 'string', 'format': 'email'},
                    'username': {'type': 'string'},
                    'sso_id': {'type': 'string'},
                    'first_name': {'type': 'string'},
                    'last_name': {'type': 'string'},
                    'full_name': {'type': 'string'},
                    'display_full_name': {'type': 'string'},
                    'is_staff': {'type': 'boolean'},
                    'is_superuser': {'type': 'boolean'},
                    'is_active': {'type': 'boolean'},
                    'date_joined': {'type': 'string', 'format': 'date-time', 'nullable': True},
                    'last_login': {'type': 'string', 'format': 'date-time', 'nullable': True},
                    'has_employee_profile': {'type': 'boolean'},
                },
            },
            'ProfileEmployee': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'employee_id': {'type': 'string'},
                    'full_name': {'type': 'string'},
                    'phone': {'type': 'string', 'nullable': True},
                    'position': {'type': 'string'},
                    'department': {'type': 'string', 'nullable': True},
                    'work_type': {'type': 'string'},
                    'work_type_display': {'type': 'string'},
                    'employment_status': {'type': 'string'},
                    'employment_status_display': {'type': 'string'},
                    'hire_date': {'type': 'string', 'format': 'date', 'nullable': True},
                    'termination_date': {'type': 'string', 'format': 'date', 'nullable': True},
                    'work_start_time': {'type': 'string', 'nullable': True},
                    'work_end_time': {'type': 'string', 'nullable': True},
                    'effective_work_start_time': {'type': 'string', 'nullable': True},
                    'effective_work_end_time': {'type': 'string', 'nullable': True},
                    'company': {'$ref': '#/components/schemas/ProfileCompany'},
                    'manager': {
                        'type': 'object',
                        'nullable': True,
                        'properties': {
                            'id': {'type': 'integer'},
                            'employee_id': {'type': 'string'},
                            'full_name': {'type': 'string'},
                        },
                    },
                },
            },
            'ProfileCompany': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'name': {'type': 'string'},
                    'code': {'type': 'string'},
                    'timezone': {'type': 'string'},
                    'work_start_time': {'type': 'string', 'nullable': True},
                    'work_end_time': {'type': 'string', 'nullable': True},
                    'is_active': {'type': 'boolean'},
                },
            },
            'TokenRefreshResponse': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'access_token': {'type': 'string'},
                },
            },
            'MfaStatusResponse': {
                'type': 'object',
                'properties': {'mfa_enabled': {'type': 'boolean'}},
            },
            'ActivityResponse': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'activity_id': {'type': 'integer'},
                },
            },
            'ActivityStatusResponse': {
                'type': 'object',
                'properties': {
                    'checked_in': {'type': 'boolean'},
                    'checked_out': {'type': 'boolean'},
                    'status': {'type': 'string'},
                    'activity_id': {'type': 'integer'},
                },
            },
            'ActivityHistoryResponse': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'count': {'type': 'integer'},
                    'results': {
                        'type': 'array',
                        'items': {'$ref': '#/components/schemas/ActivityHistoryItem'},
                    },
                },
            },
            'ActivityHistoryItem': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'date': {'type': 'string', 'format': 'date'},
                    'status': {'type': 'string'},
                    'status_display': {'type': 'string'},
                    'attendance_status': {'type': 'string'},
                    'attendance_status_display': {'type': 'string'},
                    'checkin_time': {'type': 'string', 'format': 'date-time', 'nullable': True},
                    'checkout_time': {'type': 'string', 'format': 'date-time', 'nullable': True},
                    'checkin_location': {'type': 'string'},
                    'checkout_location': {'type': 'string'},
                    'morning_problems': {'type': 'string'},
                    'afternoon_problems': {'type': 'string'},
                    'notes': {'type': 'string'},
                    'work_duration': {
                        'type': 'object',
                        'nullable': True,
                        'properties': {
                            'seconds': {'type': 'integer'},
                            'display': {'type': 'string'},
                        },
                    },
                    'planned_activities': {
                        'type': 'array',
                        'items': {'type': 'object'},
                    },
                    'daily_goals': {
                        'type': 'array',
                        'items': {'type': 'object'},
                    },
                    'additional_activities': {
                        'type': 'array',
                        'items': {'type': 'object'},
                    },
                    'counts': {
                        'type': 'object',
                        'properties': {
                            'planned_activities': {'type': 'integer'},
                            'daily_goals': {'type': 'integer'},
                            'additional_activities': {'type': 'integer'},
                        },
                    },
                },
            },
            'ErrorMessage': {
                'type': 'object',
                'properties': {'error': {'type': 'string'}},
            },
        },
    },
}


def openapi_schema(request):
    return JsonResponse(OPENAPI_SCHEMA)
