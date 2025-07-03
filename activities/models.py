from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class DailyActivity(models.Model):
    """Daily activity tracking model"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Check-out'),
        ('completed', 'Completed'),
        ('absent', 'Absent'),
    ]
    
    ATTENDANCE_STATUS_CHOICES = [
        ('on_time', 'On Time'),
        ('late', 'Late'),
        ('absent', 'Absent'),
    ]
    
    # User and Date
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_activities')
    date = models.DateField()
    
    # Status
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    attendance_status = models.CharField(max_length=15, choices=ATTENDANCE_STATUS_CHOICES, default='on_time')
    
    # Morning Check-in
    checkin_time = models.DateTimeField(null=True, blank=True)
    
    # Morning Problems (keeping as text field)
    morning_problems = models.TextField(
        help_text="Any problems or blockers?",
        blank=True
    )
    
    # Afternoon Check-out
    checkout_time = models.DateTimeField(null=True, blank=True)
    
    # Afternoon Problems (keeping as text field)
    afternoon_problems = models.TextField(
        help_text="Any problems encountered during the day?",
        blank=True
    )
    
    # Notes and Reflection
    notes = models.TextField(
        help_text="Additional notes or reflection",
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date', 'user__email']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.date}"
    
    @property
    def is_checked_in(self):
        """Check if user has checked in"""
        return self.checkin_time is not None
    
    @property
    def is_checked_out(self):
        """Check if user has checked out"""
        return self.checkout_time is not None
    
    @property
    def is_complete(self):
        """Check if daily activity is complete"""
        return self.status == 'completed'
    
    @property
    def work_duration(self):
        """Calculate work duration if both check-in and check-out exist"""
        if self.checkin_time and self.checkout_time:
            return self.checkout_time - self.checkin_time
        return None
    
    @property
    def is_late_checkin(self):
        """Check if user checked in late"""
        if not self.checkin_time:
            return False
        
        # If user has employee profile, use their work hours
        if hasattr(self.user, 'employee_profile'):
            expected_time = timezone.make_aware(
                timezone.datetime.combine(
                    self.date, 
                    self.user.employee_profile.effective_work_start_time
                )
            )
            return self.checkin_time > expected_time
        
        # Default work start time if no employee profile
        default_start = timezone.make_aware(
            timezone.datetime.combine(self.date, timezone.datetime.strptime('09:00', '%H:%M').time())
        )
        return self.checkin_time > default_start
    
    @property
    def is_early_checkout(self):
        """Check if user checked out early"""
        if not self.checkout_time:
            return False
        
        # If user has employee profile, use their work hours
        if hasattr(self.user, 'employee_profile'):
            expected_time = timezone.make_aware(
                timezone.datetime.combine(
                    self.date, 
                    self.user.employee_profile.effective_work_end_time
                )
            )
            return self.checkout_time < expected_time
        
        # Default work end time if no employee profile
        default_end = timezone.make_aware(
            timezone.datetime.combine(self.date, timezone.datetime.strptime('17:00', '%H:%M').time())
        )
        return self.checkout_time < default_end
    
    def mark_as_completed(self):
        """Mark the daily activity as completed"""
        self.status = 'completed'
        self.save()
    
    def mark_as_absent(self):
        """Mark the user as absent for the day"""
        self.status = 'absent'
        self.attendance_status = 'absent'
        self.save()


class PlannedActivity(models.Model):
    """Individual planned activities for a daily activity"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('deferred', 'Deferred'),
        ('not_completed', 'Not Completed'),
    ]
    
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
    ]
    
    daily_activity = models.ForeignKey(DailyActivity, on_delete=models.CASCADE, related_name='planned_activities')
    title = models.CharField(max_length=200, help_text="Brief description of the planned activity")
    description = models.TextField(blank=True, help_text="Detailed description if needed")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2, help_text="Priority level")
    estimated_duration = models.DurationField(null=True, blank=True, help_text="Estimated time to complete")
    order = models.PositiveIntegerField(default=0, help_text="Order of execution")
    
    # Afternoon realization
    reasons = models.TextField(
        blank=True,
        help_text="Reason for not completing or issues encountered"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'priority', 'created_at']
        unique_together = ['daily_activity', 'order']
    
    def __str__(self):
        return f"{self.title} - {self.daily_activity.user.full_name} ({self.daily_activity.date})"
    
    @property
    def is_completed(self):
        """Check if activity is completed"""
        return self.status == 'completed'
    
    @property
    def requires_reason(self):
        """Check if status requires a reason"""
        return self.status in ['not_completed', 'cancelled', 'deferred']


class DailyGoal(models.Model):
    """Individual daily goals for a daily activity"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('partially_completed', 'Partially Completed'),
        ('not_achieved', 'Not Achieved'),
        ('deferred', 'Deferred'),
    ]
    
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
    ]
    
    daily_activity = models.ForeignKey(DailyActivity, on_delete=models.CASCADE, related_name='daily_goals')
    title = models.CharField(max_length=200, help_text="Brief description of the goal")
    description = models.TextField(blank=True, help_text="Detailed description of the goal")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2, help_text="Priority level")
    target_value = models.CharField(max_length=100, blank=True, help_text="Target value or metric (if measurable)")
    achieved_value = models.CharField(max_length=100, blank=True, help_text="Actual achieved value")
    completion_percentage = models.PositiveIntegerField(default=0, help_text="Completion percentage (0-100)")
    order = models.PositiveIntegerField(default=0, help_text="Order of importance")
    
    # Afternoon realization
    reasons = models.TextField(
        blank=True,
        help_text="Reason for not achieving or issues encountered"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'priority', 'created_at']
        unique_together = ['daily_activity', 'order']
    
    def __str__(self):
        return f"{self.title} - {self.daily_activity.user.full_name} ({self.daily_activity.date})"
    
    @property
    def is_completed(self):
        """Check if goal is completed"""
        return self.status == 'completed'
    
    @property
    def is_partially_completed(self):
        """Check if goal is partially completed"""
        return self.status == 'partially_completed' or (self.completion_percentage > 0 and self.completion_percentage < 100)
    
    @property
    def requires_reason(self):
        """Check if status requires a reason"""
        return self.status in ['not_achieved', 'partially_completed', 'deferred']


class AdditionalActivity(models.Model):
    """Additional activities done outside of planned activities"""
    
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('in_progress', 'In Progress'),
        ('interrupted', 'Interrupted'),
    ]
    
    CATEGORY_CHOICES = [
        ('urgent', 'Urgent Task'),
        ('meeting', 'Unplanned Meeting'),
        ('support', 'Support/Help'),
        ('research', 'Research'),
        ('admin', 'Administrative'),
        ('other', 'Other'),
    ]
    
    daily_activity = models.ForeignKey(DailyActivity, on_delete=models.CASCADE, related_name='additional_activities')
    title = models.CharField(max_length=200, help_text="Brief description of the additional activity")
    description = models.TextField(blank=True, help_text="Detailed description of what was done")
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default='other', help_text="Category of additional activity")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='completed')
    duration = models.DurationField(null=True, blank=True, help_text="Time spent on this activity")
    order = models.PositiveIntegerField(default=0, help_text="Order of when it was done")
    
    # Impact on planned work
    impact_on_planned_work = models.TextField(
        blank=True,
        help_text="How this activity affected your planned work (if applicable)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ['daily_activity', 'order']
    
    def __str__(self):
        return f"{self.title} - {self.daily_activity.user.full_name} ({self.daily_activity.date})"
    
    @property
    def is_completed(self):
        """Check if additional activity is completed"""
        return self.status == 'completed'


class ActivityGoal(models.Model):
    """Legacy model - keeping for backward compatibility, but new goals should use DailyGoal"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    daily_activity = models.ForeignKey(DailyActivity, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Priority
    priority = models.IntegerField(default=1, help_text="1=Low, 2=Medium, 3=High")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', 'created_at']
    
    def __str__(self):
        return f"{self.title} - {self.daily_activity.user.full_name}"
