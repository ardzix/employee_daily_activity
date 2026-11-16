from unittest.mock import patch, Mock
from urllib.parse import parse_qs, urlsplit
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from authentication.central_sso import SESSION_KEY

PROFILE = {"user_id": "f0c63539-5dbd-431c-b3ac-635cffbd1f82", "email": "synthetic-central@example.test"}


class CentralClockinTests(TestCase):
    def response(self, data, status=200):
        return Mock(status_code=status, ok=200 <= status < 300, is_redirect=False, json=Mock(return_value=data))

    def start(self, client):
        response = client.get("/auth/login/?next=/dashboard/?tab=mine", secure=True)
        self.assertEqual(response.status_code, 302)
        url = urlsplit(response["Location"])
        self.assertEqual(url.netloc, "sso.arnatech.id")
        params = parse_qs(url.query)
        self.assertEqual(params["redirect_uri"], ["https://clockin.arnatech.id/api/auth/callback"])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        return params["state"][0]

    @patch("authentication.central_sso.requests.post")
    def test_login_callback_uses_server_session_without_browser_tokens(self, post):
        client = Client()
        state = self.start(client)
        post.side_effect = [self.response({"session": "s"*64, "expires_in": 3600}, 201),
                            self.response({"access": "server-only-jwt", "profile": PROFILE})]
        response = client.get("/api/auth/callback", {"code": "single-use", "state": state}, secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/dashboard/?tab=mine")
        self.assertEqual(client.session[SESSION_KEY], "s"*64)
        self.assertIn("_auth_user_id", client.session)
        self.assertNotIn("access_token", client.session)
        self.assertNotIn("refresh_token", client.session)
        cookie = response.cookies["__Host-arna_clockin"]
        self.assertTrue(cookie["secure"] and cookie["httponly"])
        self.assertEqual(cookie["domain"], "")
        self.assertNotIn("server-only-jwt", str(response.cookies))
        self.assertFalse(get_user_model().objects.get(sso_id=PROFILE["user_id"]).has_usable_password())

    @patch("authentication.central_sso.requests.post")
    def test_bad_state_and_replayed_callback_reject_before_exchange(self, post):
        client = Client()
        self.start(client)
        for _ in range(2):
            response = client.get("/api/auth/callback?code=once&state=wrong", secure=True)
            self.assertEqual(response.status_code, 400)
        post.assert_not_called()

    @patch("authentication.central_sso.requests.post")
    def test_global_session_revocation_invalidates_local_django_login(self, post):
        user = get_user_model().objects.create_user(username=PROFILE["user_id"], sso_id=PROFILE["user_id"], email=PROFILE["email"])
        client = Client()
        client.force_login(user)
        session = client.session
        session[SESSION_KEY] = "s"*64
        session.save()
        post.return_value = self.response({}, 401)
        response = client.get("/dashboard/", secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/auth/login/?next="))
        self.assertNotIn("_auth_user_id", client.session)

    @patch("authentication.central_sso.requests.post")
    def test_logout_is_csrf_protected_and_all_choice_is_explicit(self, post):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/auth/logout/", {"all": "true"}, secure=True).status_code, 403)
        client.get("/auth/logout/", secure=True)
        session = client.session
        session[SESSION_KEY] = "s"*64
        session.save()
        post.return_value = self.response({"logged_out": True})
        response = client.post("/auth/logout/", {"all": "true", "csrfmiddlewaretoken": client.cookies["csrftoken"].value},
                               secure=True, HTTP_ORIGIN="https://clockin.arnatech.id")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(post.call_args.kwargs["json"]["all"])

    def test_local_credential_login_routes_are_disabled(self):
        for path in ["/auth/api/login/", "/auth/api/google-login/", "/auth/api/mfa/verify/"]:
            self.assertEqual(Client().post(path, {"email": "unused", "password": "unused"}, secure=True).status_code, 302)

    @patch("authentication.central_sso.requests.post")
    def test_admin_uses_central_identity_without_granting_staff_privileges(self, post):
        self.assertTrue(Client().get("/admin/login/", secure=True)["Location"].startswith("/auth/login/"))
        client = Client()
        session = client.session
        session[SESSION_KEY] = "s"*64
        session.save()
        post.return_value = self.response({"access": "server-only-jwt", "profile": PROFILE})
        self.assertEqual(client.get("/admin/login/", secure=True).status_code, 403)
        user = get_user_model().objects.get(sso_id=PROFILE["user_id"])
        self.assertFalse(user.is_staff)
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        self.assertEqual(client.get("/admin/login/", secure=True)["Location"], "/admin/")
