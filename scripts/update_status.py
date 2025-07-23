from activities.models import DailyActivity
from django.utils import timezone
from datetime import datetime, timedelta
import pytz


def update_status():
    jakarta_tz = pytz.timezone('Asia/Jakarta')
    count_late = 0
    count_early = 0

    grace_period = timedelta(minutes=5)

    for activity in DailyActivity.objects.select_related('user__employee_profile').all():
        updated = False

        # Ensure attendance_status is set if missing
        if not activity.attendance_status or activity.attendance_status.strip() == '':
            if activity.checkin_time and hasattr(activity.user, 'employee_profile'):
                checkin_time_local = activity.checkin_time.astimezone(jakarta_tz)
                expected_start = jakarta_tz.localize(
                    datetime.combine(activity.date, activity.user.employee_profile.effective_work_start_time)
                )
                if checkin_time_local > expected_start:
                    activity.attendance_status = 'late'
                else:
                    activity.attendance_status = 'on_time'
            else:
                activity.attendance_status = 'absent'
            updated = True

        # Fix late check-in
        if activity.checkin_time and hasattr(activity.user, 'employee_profile'):
            checkin_time_local = activity.checkin_time.astimezone(jakarta_tz)
            expected_start = jakarta_tz.localize(
                datetime.combine(activity.date, activity.user.employee_profile.effective_work_start_time)
            )
            if checkin_time_local > expected_start and activity.attendance_status == 'on_time':
                activity.attendance_status = 'late'
                updated = True
                count_late += 1

        # Fix early checkout
        if activity.checkout_time and hasattr(activity.user, 'employee_profile'):
            checkout_time_local = activity.checkout_time.astimezone(jakarta_tz)
            work_end = getattr(activity.user.employee_profile, 'effective_work_end_time', None)
            if work_end:
                expected_end = jakarta_tz.localize(
                    datetime.combine(activity.date, work_end)
                )
                print(f"Check-out: {checkout_time_local} | Expected: {expected_end} | Early? {checkout_time_local < (expected_end - grace_period)}")
                if checkout_time_local < (expected_end - grace_period):
                    if activity.attendance_status != 'early_checkout':
                        activity.attendance_status = 'early_checkout'
                        activity.status = 'early_checkout'
                        updated = True
                        count_early += 1
                else:
                    # Reset to completed if previously marked as early_checkout
                    if activity.attendance_status == 'early_checkout':
                        # Determine punctuality based on check-in time
                        checkin_time_local = None
                        expected_start = None
                        if activity.checkin_time and hasattr(activity.user, 'employee_profile'):
                            checkin_time_local = activity.checkin_time.astimezone(jakarta_tz)
                            expected_start = jakarta_tz.localize(
                                datetime.combine(activity.date, activity.user.employee_profile.effective_work_start_time)
                            )
                        if checkin_time_local and expected_start and checkin_time_local > expected_start:
                            activity.attendance_status = 'late'
                        else:
                            activity.attendance_status = 'on_time'
                        activity.status = 'completed'
                        updated = True

        # Final fallback: ensure attendance_status is never empty
        if not activity.attendance_status or activity.attendance_status.strip() == '':
            activity.attendance_status = 'absent'
            updated = True

        if updated:
            activity.save()
            print(f"Updated {activity.user} on {activity.date}: status={activity.status}, attendance_status={activity.attendance_status}")

    print(f"Done. {count_late} late check-ins fixed, {count_early} early check-outs fixed.")