"""Validate attendance input before opening a database transaction."""
import json
from django.core.exceptions import ValidationError
from rest_framework import serializers
from .models import DailyActivity, PlannedActivity, DailyGoal, AdditionalActivity


class AttendanceInputError(Exception):
    def __init__(self, message, fields):
        super().__init__(message)
        self.fields = fields


class PlannedActivityInput(serializers.ModelSerializer):
    class Meta:
        model = PlannedActivity
        fields = ("title", "description", "priority", "estimated_duration")
        validators = []


class DailyGoalInput(serializers.ModelSerializer):
    class Meta:
        model = DailyGoal
        fields = ("title", "description", "priority", "target_value")
        validators = []


class AdditionalActivityInput(serializers.ModelSerializer):
    class Meta:
        model = AdditionalActivity
        fields = ("title", "description", "category", "status", "duration", "impact_on_planned_work")
        validators = []


def validate_entries(raw, serializer_class, field, label):
    raw = raw.strip()
    if raw.startswith(("[", "{")):
        try:
            values = json.loads(raw)
        except ValueError:
            raise AttendanceInputError(f"{label}: invalid JSON. Send a list of objects.", {field: ["Invalid JSON."]}) from None
    else:
        # Preserve the legacy newline-separated input contract.
        values = [{"title": line.strip()} for line in raw.splitlines() if line.strip()]
    serializer = serializer_class(data=values, many=True)
    if not serializer.is_valid():
        errors = serializer.errors
        message = f"{label}: send a list of valid objects."
        if isinstance(errors, list):
            for index, item in enumerate(errors):
                if item:
                    if isinstance(item, dict):
                        name, details = next(iter(item.items()))
                        message = f"{label} {index + 1}, {name}: {details[0]}"
                    else:
                        message = f"{label} {index + 1}: provide a valid object."
                    break
        raise AttendanceInputError(message, {field: errors})
    return serializer.validated_data


def validate_location(location):
    try:
        return DailyActivity._meta.get_field("checkin_location").clean(location, None)
    except ValidationError as error:
        raise AttendanceInputError("Location: " + " ".join(error.messages), {"location": error.messages}) from None
