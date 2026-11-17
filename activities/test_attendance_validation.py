import json
import uuid
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import TestCase
from django.utils import timezone
from activities.models import DailyActivity, PlannedActivity, DailyGoal


class AttendanceValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="attendance-test", email="attendance@example.invalid", sso_id=str(uuid.uuid4()), password=None)
        self.client.force_login(self.user)
        resolver = patch("authentication.central_sso.resolve", return_value={"access": "server-only-synthetic",
            "profile": {"user_id": self.user.sso_id, "email": self.user.email}})
        resolver.start()
        self.addCleanup(resolver.stop)

    def post(self, **changes):
        data = {"lat": "-6.2", "long": "106.8", "planned_activities": json.dumps([{"title": "Work"}]),
                "daily_goals": json.dumps([{"title": "Goal"}])}
        data.update(changes)
        return self.client.post("/activities/api/check-in/", data, secure=True)

    def test_210_character_activity_returns_clear_400_without_writing_attendance(self):
        response = self.post(planned_activities=json.dumps([{"title": "x" * 210}]))
        self.assertEqual(response.status_code, 400)
        self.assertIn("200", response.json()["error"])
        self.assertIn("Planned activity 1, title", response.json()["error"])
        self.assertIn("planned_activities", response.json()["fields"])
        self.assertFalse(DailyActivity.objects.exists())
        self.assertFalse(PlannedActivity.objects.exists())

    def test_goal_and_target_lengths_are_checked_before_any_write(self):
        for goal in [{"title": "x" * 201}, {"title": "Goal", "target_value": "x" * 101}]:
            with self.subTest(goal_length=len(goal["title"])):
                response = self.post(daily_goals=json.dumps([goal]))
                self.assertEqual(response.status_code, 400)
                self.assertIn("daily_goals", response.json()["fields"])
                self.assertFalse(DailyActivity.objects.exists())
                self.assertFalse(PlannedActivity.objects.exists())

    def test_malformed_structure_and_field_values_return_400(self):
        for raw in ['{"title":"object"}', '["not an object"]', '[null]', '[',
                    '[{"title":"Work","priority":99}]', '[{"title":"Work","estimated_duration":"invalid"}]',
                    '[{"title":"   "}]']:
            with self.subTest(raw=raw):
                self.assertEqual(self.post(planned_activities=raw).status_code, 400)
                self.assertFalse(DailyActivity.objects.exists())

    def test_exact_limits_succeed_and_duplicate_submit_does_not_duplicate_records(self):
        data = {"planned_activities": json.dumps([{"title": "a" * 200}]),
                "daily_goals": json.dumps([{"title": "g" * 200, "target_value": "t" * 100}])}
        self.assertEqual(self.post(**data).status_code, 200)
        self.assertEqual(self.post(**data).status_code, 400)
        self.assertEqual(DailyActivity.objects.count(), 1)
        self.assertEqual(PlannedActivity.objects.count(), 1)
        self.assertEqual(DailyGoal.objects.count(), 1)
        self.assertEqual(len(PlannedActivity.objects.get().title), 200)

    def test_failed_pending_row_can_be_retried_without_losing_existing_data(self):
        row = DailyActivity.objects.create(user=self.user, date=timezone.localdate(), morning_problems="existing")
        self.assertEqual(self.post(planned_activities=json.dumps([{"title": "x" * 210}])).status_code, 400)
        row.refresh_from_db()
        self.assertIsNone(row.checkin_time)
        self.assertEqual(row.morning_problems, "existing")
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(DailyActivity.objects.get().pk, row.pk)

    def test_unexpected_write_failure_rolls_back_new_attendance_and_children(self):
        with patch("activities.views.DailyGoal.objects.create", side_effect=DatabaseError("synthetic failure")):
            with self.assertRaises(DatabaseError):
                self.post()
        self.assertFalse(DailyActivity.objects.exists())
        self.assertFalse(PlannedActivity.objects.exists())

    def test_legacy_newline_input_still_succeeds(self):
        response = self.post(planned_activities="First task\nSecond task", daily_goals="One goal")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PlannedActivity.objects.count(), 2)

    def test_invalid_location_is_rejected_before_writes(self):
        for values in [{"lat": "91"}, {"long": "not-a-number"}, {"lat": "1" * 101}]:
            self.assertEqual(self.post(**values).status_code, 400)
            self.assertFalse(DailyActivity.objects.exists())

    def test_overlong_additional_activity_does_not_record_checkout(self):
        row = DailyActivity.objects.create(user=self.user, date=timezone.localdate(), checkin_time=timezone.now())
        response = self.client.post("/activities/api/check-out/", {"lat": "-6.2", "long": "106.8",
            "additional_activities": json.dumps([{"title": "x" * 210}])}, secure=True)
        self.assertEqual(response.status_code, 400)
        self.assertIn("200", response.json()["error"])
        row.refresh_from_db()
        self.assertIsNone(row.checkout_time)
