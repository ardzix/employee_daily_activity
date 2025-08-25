from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db import transaction
from .models import DailyActivity, ActivityGoal, PlannedActivity, DailyGoal, AdditionalActivity
from datetime import date, datetime
import json
import pytz


@login_required
def check_in_api(request):
    """Check-in API for all users"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    today = date.today()
    jakarta_tz = pytz.timezone('Asia/Jakarta')
    
    # Get or create daily activity for the user
    daily_activity, created = DailyActivity.objects.get_or_create(
        user=request.user,
        date=today,
        defaults={
            'status': 'pending',
            'attendance_status': 'on_time'
        }
    )
    
    # Check if already checked in
    if daily_activity.checkin_time:
        return JsonResponse({'error': 'You have already checked in today'}, status=400)
    
    # Get location data
    lat = request.POST.get('lat')
    long = request.POST.get('long')
    location = None
    if lat and long:
        location = f"{lat},{long}"

    if not location:
        return JsonResponse({
            "success": False,
            "error": "Location is required. Please allow location access."
        }, status=400)

    # Get form data
    planned_activities_data = request.POST.get('planned_activities', '').strip()
    daily_goals_data = request.POST.get('daily_goals', '').strip()
    morning_problems = request.POST.get('morning_problems', '').strip()
    
    # Try to parse as JSON first (for API calls), then fall back to text parsing
    planned_activities_list = []
    daily_goals_list = []
    
    try:
        # Try to parse as JSON
        if planned_activities_data.startswith('[') or planned_activities_data.startswith('{'):
            planned_activities_list = json.loads(planned_activities_data)
        else:
            # Parse as text - split by newlines
            planned_activities_list = [{'title': line.strip()} for line in planned_activities_data.split('\n') if line.strip()]
    except:
        # Fall back to text parsing
        planned_activities_list = [{'title': line.strip()} for line in planned_activities_data.split('\n') if line.strip()]
    
    try:
        # Try to parse as JSON
        if daily_goals_data.startswith('[') or daily_goals_data.startswith('{'):
            daily_goals_list = json.loads(daily_goals_data)
        else:
            # Parse as text - split by newlines
            daily_goals_list = [{'title': line.strip()} for line in daily_goals_data.split('\n') if line.strip()]
    except:
        # Fall back to text parsing
        daily_goals_list = [{'title': line.strip()} for line in daily_goals_data.split('\n') if line.strip()]
    
    # Validate required fields
    if not planned_activities_list:
        return JsonResponse({'error': 'Please add at least one planned activity for today'}, status=400)
    
    if not daily_goals_list:
        return JsonResponse({'error': 'Please set at least one goal for today'}, status=400)
    
    with transaction.atomic():
        # Record check-in with data
        daily_activity.checkin_time = timezone.now()
        daily_activity.morning_problems = morning_problems

        if location:
            daily_activity.checkin_location = location
        
        # Determine if late (only if user has employee profile)
        if hasattr(request.user, 'employee_profile'):
            checkin_time_local = daily_activity.checkin_time.astimezone(jakarta_tz)
            expected_time = jakarta_tz.localize(
                datetime.combine(today, request.user.employee_profile.effective_work_start_time)
            )
            
            if checkin_time_local > expected_time:
                daily_activity.attendance_status = 'late'
            else:
                daily_activity.attendance_status = 'on_time'
        
        daily_activity.save()
        
        # Create PlannedActivity objects
        for i, activity_data in enumerate(planned_activities_list):
            PlannedActivity.objects.create(
                daily_activity=daily_activity,
                title=activity_data.get('title', ''),
                description=activity_data.get('description', ''),
                priority=activity_data.get('priority', 2),
                order=i + 1,
                estimated_duration=activity_data.get('estimated_duration', None)
            )
        
        # Create DailyGoal objects
        for i, goal_data in enumerate(daily_goals_list):
            DailyGoal.objects.create(
                daily_activity=daily_activity,
                title=goal_data.get('title', ''),
                description=goal_data.get('description', ''),
                priority=goal_data.get('priority', 2),
                target_value=goal_data.get('target_value', ''),
                order=i + 1
            )
    
    return JsonResponse({
        'success': True,
        'message': 'Checked in successfully!',
        'time': timezone.now().strftime('%H:%M'),
        'location': daily_activity.checkin_location,
        'planned_activities_count': len(planned_activities_list),
        'daily_goals_count': len(daily_goals_list)
    })


@login_required
def check_out_api(request):
    """Check-out API for all users"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    today = date.today()
    jakarta_tz = pytz.timezone('Asia/Jakarta')
    
    try:
        daily_activity = DailyActivity.objects.get(user=request.user, date=today)
    except DailyActivity.DoesNotExist:
        return JsonResponse({'error': 'Please check in first'}, status=400)
    
    # Check if checked in first
    if not daily_activity.checkin_time:
        return JsonResponse({'error': 'Please check in first'}, status=400)
    
    # Check if already checked out
    if daily_activity.checkout_time:
        return JsonResponse({'error': 'You have already checked out today'}, status=400)
    
    # Get form data
    afternoon_problems = request.POST.get('afternoon_problems', '').strip()

    # Get location data
    lat = request.POST.get('lat')
    long = request.POST.get('long')
    location = None
    if lat and long:
        location = f"{lat},{long}"
    
    if not location:
        return JsonResponse({
            "success": False,
            "error": "Location is required. Please allow location access."
        }, status=400)
    
    # Get activity and goal updates
    activity_updates = request.POST.get('activity_updates', '[]')
    goal_updates = request.POST.get('goal_updates', '[]')
    additional_activities_data = request.POST.get('additional_activities', '[]')
    
    try:
        activity_updates = json.loads(activity_updates) if activity_updates else []
        goal_updates = json.loads(goal_updates) if goal_updates else []
        additional_activities_list = json.loads(additional_activities_data) if additional_activities_data else []
    except:
        activity_updates = []
        goal_updates = []
        additional_activities_list = []
    
    # Parse additional activities from text if not JSON
    if not additional_activities_list:
        additional_activities_text = request.POST.get('additional_activities_text', '').strip()
        if additional_activities_text:
            additional_activities_list = [{'title': line.strip()} for line in additional_activities_text.split('\n') if line.strip()]
    
    # Validate that all activities and goals have been updated
    planned_activities = daily_activity.planned_activities.all()
    daily_goals = daily_activity.daily_goals.all()
    
    if not activity_updates and planned_activities.exists():
        return JsonResponse({'error': 'Please update status for all planned activities'}, status=400)
    
    if not goal_updates and daily_goals.exists():
        return JsonResponse({'error': 'Please update status for all daily goals'}, status=400)
    
    # Validate that activities requiring reasons have them
    activity_ids_with_status = {update.get('id'): update for update in activity_updates}
    for activity in planned_activities:
        update = activity_ids_with_status.get(activity.id)
        if update:
            status = update.get('status', 'pending')
            reasons = update.get('reasons', '').strip()
            if status in ['not_completed', 'cancelled', 'deferred'] and not reasons:
                return JsonResponse({'error': f'Please provide a reason for activity: {activity.title}'}, status=400)
    
    # Validate that goals requiring reasons have them
    goal_ids_with_status = {update.get('id'): update for update in goal_updates}
    for goal in daily_goals:
        update = goal_ids_with_status.get(goal.id)
        if update:
            status = update.get('status', 'pending')
            reasons = update.get('reasons', '').strip()
            if status in ['not_achieved', 'partially_completed', 'deferred'] and not reasons:
                return JsonResponse({'error': f'Please provide a reason for goal: {goal.title}'}, status=400)
    
    with transaction.atomic():
        # Record check-out with data
        daily_activity.checkout_time = timezone.now()
        daily_activity.afternoon_problems = afternoon_problems
        if location:
            daily_activity.checkout_location = location
        # Early checkout logic
        early_checkout = False
        if hasattr(request.user, 'employee_profile'):
            checkout_time_local = daily_activity.checkout_time.astimezone(jakarta_tz)
            expected_end_time = jakarta_tz.localize(
                datetime.combine(today, request.user.employee_profile.effective_work_end_time)
            )
            if checkout_time_local < expected_end_time:
                daily_activity.attendance_status = 'early_checkout'
                daily_activity.status = 'early_checkout'
                early_checkout = True
        if not early_checkout:
            daily_activity.status = 'completed'
        daily_activity.save()
        
        # Update PlannedActivity statuses
        for update in activity_updates:
            try:
                activity = PlannedActivity.objects.get(
                    id=update.get('id'),
                    daily_activity=daily_activity
                )
                activity.status = update.get('status', activity.status)
                activity.reasons = update.get('reasons', '')
                activity.save()
            except PlannedActivity.DoesNotExist:
                continue
        
        # Update DailyGoal statuses and completion
        for update in goal_updates:
            try:
                goal = DailyGoal.objects.get(
                    id=update.get('id'),
                    daily_activity=daily_activity
                )
                goal.status = update.get('status', goal.status)
                goal.completion_percentage = update.get('completion_percentage', goal.completion_percentage)
                goal.achieved_value = update.get('achieved_value', goal.achieved_value)
                goal.reasons = update.get('reasons', '')
                goal.save()
            except DailyGoal.DoesNotExist:
                continue
        
        # Create AdditionalActivity objects
        for i, additional_activity in enumerate(additional_activities_list):
            AdditionalActivity.objects.create(
                daily_activity=daily_activity,
                title=additional_activity.get('title', ''),
                description=additional_activity.get('description', ''),
                category=additional_activity.get('category', 'other'),
                status=additional_activity.get('status', 'completed'),
                duration=additional_activity.get('duration', None),
                impact_on_planned_work=additional_activity.get('impact_on_planned_work', ''),
                order=i + 1
            )
        
        # Update legacy goal statuses if provided
        if hasattr(request, 'POST') and 'completed_goals' in request.POST:
            completed_goals = request.POST.getlist('completed_goals')
            for goal in daily_activity.goals.all():
                if str(goal.id) in completed_goals:
                    goal.status = 'completed'
                    goal.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Checked out successfully!',
        'time': timezone.now().strftime('%H:%M'),
        'location': daily_activity.checkout_location,
        'additional_activities_count': len(additional_activities_list)
    })


@login_required
def activity_status_api(request):
    """Get activity status for users"""
    today = date.today()
    
    try:
        daily_activity = DailyActivity.objects.get(user=request.user, date=today)
        
        # Get planned activities and goals
        planned_activities = list(daily_activity.planned_activities.values(
            'id', 'title', 'description', 'status', 'priority', 'order', 'estimated_duration', 'reasons'
        ))
        daily_goals = list(daily_activity.daily_goals.values(
            'id', 'title', 'description', 'status', 'priority', 'target_value', 
            'achieved_value', 'completion_percentage', 'order', 'reasons'
        ))
        additional_activities = list(daily_activity.additional_activities.values(
            'id', 'title', 'description', 'category', 'status', 'duration', 'order', 'impact_on_planned_work'
        ))
        
        status = {
            'checked_in': bool(daily_activity.checkin_time),
            'checked_out': bool(daily_activity.checkout_time),
            'checkin_time': daily_activity.checkin_time.isoformat() if daily_activity.checkin_time else None,
            'checkout_time': daily_activity.checkout_time.isoformat() if daily_activity.checkout_time else None,
        }
        
        # Include form data if available
        if daily_activity.checkin_time:
            status['checkin_data'] = {
                'planned_activities': planned_activities,
                'daily_goals': daily_goals,
                'morning_problems': daily_activity.morning_problems,
            }
        
        if daily_activity.checkout_time:
            status['checkout_data'] = {
                'planned_activities': planned_activities,
                'daily_goals': daily_goals,
                'additional_activities': additional_activities,
                'afternoon_problems': daily_activity.afternoon_problems,
            }
            
    except DailyActivity.DoesNotExist:
        status = {
            'checked_in': False,
            'checked_out': False,
            'checkin_time': None,
            'checkout_time': None,
        }
    
    return JsonResponse(status)


@login_required
def activity_data_view(request):
    """View to display activity data"""
    today = date.today()
    
    try:
        daily_activity = DailyActivity.objects.prefetch_related(
            'planned_activities', 'daily_goals', 'additional_activities', 'goals'
        ).get(user=request.user, date=today)
    except DailyActivity.DoesNotExist:
        daily_activity = None
    
    context = {
        'today': today,
        'user': request.user,
        'daily_activity': daily_activity,
        'has_employee_profile': hasattr(request.user, 'employee_profile'),
    }
    
    return render(request, 'activities/activity_data.html', context)


@login_required
def check_in_view(request):
    messages.info(request, "Check-in is now handled on the dashboard.")
    return redirect('dashboard:index')


@login_required
def check_out_view(request):
    messages.info(request, "Check-out is now handled on the dashboard.")
    return redirect('dashboard:index')


@login_required
def daily_summary_view(request, activity_id=None):
    """Display daily activity summary - can show today's or a specific activity"""
    if activity_id:
        # Show specific activity
        daily_activity = get_object_or_404(
            DailyActivity.objects.prefetch_related(
                'planned_activities', 'daily_goals', 'additional_activities', 'goals'
            ),
            id=activity_id,
            user=request.user
        )
    else:
        # Show today's activity
        today = date.today()
        try:
            daily_activity = DailyActivity.objects.prefetch_related(
                'planned_activities', 'daily_goals', 'additional_activities', 'goals'
            ).get(user=request.user, date=today)
        except DailyActivity.DoesNotExist:
            # No activity for today, redirect to check-in
            return redirect('activities:check_in')
    
    context = {
        'user': request.user,
        'daily_activity': daily_activity,
        'goals': daily_activity.goals.all(),
        'planned_activities': daily_activity.planned_activities.all(),
        'daily_goals': daily_activity.daily_goals.all(),
        'additional_activities': daily_activity.additional_activities.all(),
        'can_check_in': not daily_activity.checkin_time and daily_activity.date == date.today(),
        'can_check_out': daily_activity.checkin_time and not daily_activity.checkout_time and daily_activity.date == date.today(),
        'has_employee_profile': hasattr(request.user, 'employee_profile'),
    }
    
    return render(request, 'activities/daily_summary.html', context)


@login_required
def activity_history_view(request):
    """Display activity history"""
    activities = DailyActivity.objects.filter(user=request.user).prefetch_related(
        'planned_activities', 'daily_goals', 'additional_activities', 'goals'
    ).order_by('-date')[:30]
    
    context = {
        'user': request.user,
        'activities': activities,
        'has_employee_profile': hasattr(request.user, 'employee_profile'),
    }
    
    return render(request, 'activities/history.html', context)


@login_required
def activity_detail_view(request, activity_id):
    """Display detailed view of a specific activity"""
    activity = get_object_or_404(
        DailyActivity.objects.prefetch_related('planned_activities', 'daily_goals', 'additional_activities', 'goals'),
        id=activity_id, 
        user=request.user
    )
    
    context = {
        'user': request.user,
        'activity': activity,
        'goals': activity.goals.all(),
        'planned_activities': activity.planned_activities.all(),
        'daily_goals': activity.daily_goals.all(),
        'additional_activities': activity.additional_activities.all(),
        'has_employee_profile': hasattr(request.user, 'employee_profile'),
    }
    
    return render(request, 'activities/detail.html', context)


@login_required
def activity_list_view(request):
    """Display list of all activities for the user"""
    activities = DailyActivity.objects.filter(user=request.user).prefetch_related(
        'planned_activities', 'daily_goals', 'additional_activities', 'goals'
    ).order_by('-date')
    
    context = {
        'user': request.user,
        'activities': activities,
        'today': date.today(),
        'has_employee_profile': hasattr(request.user, 'employee_profile'),
    }
    
    return render(request, 'activities/activity_list.html', context)


@login_required
def activity_data_redirect(request):
    """Redirect to today's activity detail view"""
    today = date.today()
    try:
        daily_activity = DailyActivity.objects.get(user=request.user, date=today)
        return redirect('activities:daily_summary', activity_id=daily_activity.id)
    except DailyActivity.DoesNotExist:
        # No activity for today, redirect to check-in
        return redirect('activities:check_in')


@login_required
def activity_data_view(request):
    """Legacy view - redirect to today's activity detail"""
    return activity_data_redirect(request) 