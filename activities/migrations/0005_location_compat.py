"""Replace the unapplied NOT NULL change without inventing historical locations.

Keep the original migration file for environments that already applied it.
0006 also relaxes those environments after Django recognizes this replacement.
"""
import activities.models
from django.db import migrations, models


class Migration(migrations.Migration):
    replaces = [('activities', '0005_alter_dailyactivity_checkin_location_and_more')]
    dependencies = [('activities', '0004_dailyactivity_checkin_location_and_more')]
    operations = [
        migrations.AlterField(
            model_name='dailyactivity', name=name,
            field=models.CharField(blank=True, null=True, max_length=100,
                help_text='Format: lat,long', validators=[activities.models.validate_lat_long]),
        ) for name in ('checkin_location', 'checkout_location')
    ]
