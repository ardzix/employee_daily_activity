"""Also reconcile installations where the original 0005 was already applied."""
from django.db import migrations


def relax_original_constraints(apps, schema_editor):
    # Replacement state is nullable even when an installation ran the original
    # 0005. Force the database transition rather than letting AlterField skip it.
    model = apps.get_model('activities', 'DailyActivity')
    for name in ('checkin_location', 'checkout_location'):
        field = model._meta.get_field(name)
        previous = field.clone()
        previous.set_attributes_from_name(name)
        previous.model = model
        previous.null = False
        schema_editor.alter_field(model, previous, field, strict=False)


class Migration(migrations.Migration):
    dependencies = [('activities', '0005_location_compat')]
    operations = [migrations.RunPython(relax_original_constraints, migrations.RunPython.noop)]
