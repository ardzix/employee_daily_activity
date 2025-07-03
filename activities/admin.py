from django.contrib import admin
from .models import DailyActivity, ActivityGoal, PlannedActivity, DailyGoal, AdditionalActivity


class ActivityGoalInline(admin.TabularInline):
    model = ActivityGoal
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


class PlannedActivityInline(admin.TabularInline):
    model = PlannedActivity
    extra = 1
    readonly_fields = ('created_at', 'updated_at')
    fields = ('order', 'title', 'description', 'priority', 'status', 'estimated_duration', 'reasons')
    ordering = ('order', 'priority')


class DailyGoalInline(admin.TabularInline):
    model = DailyGoal
    extra = 1
    readonly_fields = ('created_at', 'updated_at')
    fields = ('order', 'title', 'description', 'priority', 'status', 'target_value', 'achieved_value', 'completion_percentage', 'reasons')
    ordering = ('order', 'priority')


class AdditionalActivityInline(admin.TabularInline):
    model = AdditionalActivity
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('order', 'title', 'description', 'category', 'status', 'duration', 'impact_on_planned_work')
    ordering = ('order', 'created_at')


@admin.register(DailyActivity)
class DailyActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'status', 'attendance_status', 'checkin_time', 'checkout_time', 'planned_activities_count', 'daily_goals_count', 'additional_activities_count')
    list_filter = ('status', 'attendance_status', 'date')
    search_fields = ('user__email', 'user__sso_id', 'user__first_name', 'user__last_name')
    ordering = ('-date', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PlannedActivityInline, DailyGoalInline, AdditionalActivityInline, ActivityGoalInline]
    
    fieldsets = (
        (None, {
            'fields': ('user', 'date', 'status', 'attendance_status')
        }),
        ('Check-in/Check-out', {
            'fields': ('checkin_time', 'checkout_time')
        }),
        ('Morning Planning', {
            'fields': ('morning_problems',),
            'classes': ('collapse',)
        }),
        ('Afternoon Summary', {
            'fields': ('afternoon_problems',),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('planned_activities', 'daily_goals', 'additional_activities')
    
    def planned_activities_count(self, obj):
        return obj.planned_activities.count()
    planned_activities_count.short_description = 'Activities'
    
    def daily_goals_count(self, obj):
        return obj.daily_goals.count()
    daily_goals_count.short_description = 'Goals'
    
    def additional_activities_count(self, obj):
        return obj.additional_activities.count()
    additional_activities_count.short_description = 'Additional'


@admin.register(PlannedActivity)
class PlannedActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'daily_activity', 'status', 'priority', 'order', 'estimated_duration', 'has_reasons', 'created_at')
    list_filter = ('status', 'priority', 'created_at', 'daily_activity__date')
    search_fields = ('title', 'description', 'daily_activity__user__email', 'daily_activity__user__first_name', 'daily_activity__user__last_name')
    ordering = ('daily_activity__date', 'order', 'priority')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('daily_activity', 'title', 'description', 'status')
        }),
        ('Organization', {
            'fields': ('order', 'priority', 'estimated_duration')
        }),
        ('Afternoon Realization', {
            'fields': ('reasons',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('daily_activity', 'daily_activity__user')
    
    def has_reasons(self, obj):
        return bool(obj.reasons)
    has_reasons.boolean = True
    has_reasons.short_description = 'Has Reasons'


@admin.register(DailyGoal)
class DailyGoalAdmin(admin.ModelAdmin):
    list_display = ('title', 'daily_activity', 'status', 'priority', 'completion_percentage', 'order', 'has_reasons', 'created_at')
    list_filter = ('status', 'priority', 'created_at', 'daily_activity__date')
    search_fields = ('title', 'description', 'daily_activity__user__email', 'daily_activity__user__first_name', 'daily_activity__user__last_name')
    ordering = ('daily_activity__date', 'order', 'priority')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('daily_activity', 'title', 'description', 'status')
        }),
        ('Metrics', {
            'fields': ('target_value', 'achieved_value', 'completion_percentage')
        }),
        ('Organization', {
            'fields': ('order', 'priority')
        }),
        ('Afternoon Realization', {
            'fields': ('reasons',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('daily_activity', 'daily_activity__user')
    
    def has_reasons(self, obj):
        return bool(obj.reasons)
    has_reasons.boolean = True
    has_reasons.short_description = 'Has Reasons'


@admin.register(AdditionalActivity)
class AdditionalActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'daily_activity', 'category', 'status', 'duration', 'order', 'has_impact_notes', 'created_at')
    list_filter = ('status', 'category', 'created_at', 'daily_activity__date')
    search_fields = ('title', 'description', 'daily_activity__user__email', 'daily_activity__user__first_name', 'daily_activity__user__last_name')
    ordering = ('daily_activity__date', 'order', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('daily_activity', 'title', 'description', 'category', 'status')
        }),
        ('Details', {
            'fields': ('order', 'duration')
        }),
        ('Impact Assessment', {
            'fields': ('impact_on_planned_work',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('daily_activity', 'daily_activity__user')
    
    def has_impact_notes(self, obj):
        return bool(obj.impact_on_planned_work)
    has_impact_notes.boolean = True
    has_impact_notes.short_description = 'Has Impact Notes'


@admin.register(ActivityGoal)
class ActivityGoalAdmin(admin.ModelAdmin):
    list_display = ('title', 'daily_activity', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('title', 'daily_activity__user__email', 'daily_activity__user__sso_id', 'daily_activity__user__first_name', 'daily_activity__user__last_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('daily_activity', 'title', 'description', 'status', 'priority')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
