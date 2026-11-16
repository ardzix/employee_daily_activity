from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import TransactionTestCase


class LocationMigrationTests(TransactionTestCase):
    old = ('activities', '0004_dailyactivity_checkin_location_and_more')
    latest = ('activities', '0006_location_optional')

    def tearDown(self):
        MigrationExecutor(connection).migrate([self.latest])
        super().tearDown()

    def test_historical_missing_locations_survive_upgrade(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.old])
        apps = executor.loader.project_state([self.old]).apps
        user = apps.get_model('authentication', 'User').objects.create(
            email='migration@example.invalid', sso_id='migration-user', username='migration-user')
        activity = apps.get_model('activities', 'DailyActivity').objects.create(
            user=user, date='2026-01-01', checkin_location=None, checkout_location=None)
        executor = MigrationExecutor(connection)
        executor.migrate([self.latest])
        row = executor.loader.project_state([self.latest]).apps.get_model('activities', 'DailyActivity').objects.get(pk=activity.pk)
        self.assertIsNone(row.checkin_location)
        self.assertIsNone(row.checkout_location)
        self.assertEqual(row.user_id, user.pk)

    def test_previously_applied_original_migration_can_upgrade(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.old])
        executor = MigrationExecutor(connection)
        executor.loader = MigrationLoader(connection, replace_migrations=False)
        executor.migrate([('activities', '0005_alter_dailyactivity_checkin_location_and_more')])
        executor = MigrationExecutor(connection)
        executor.migrate([self.latest])
        apps = executor.loader.project_state([self.latest]).apps
        user = apps.get_model('authentication', 'User').objects.create(
            email='applied@example.invalid', sso_id='applied-user', username='applied-user')
        row = apps.get_model('activities', 'DailyActivity').objects.create(
            user=user, date='2026-01-02', checkin_location=None, checkout_location=None)
        self.assertIsNotNone(row.pk)
