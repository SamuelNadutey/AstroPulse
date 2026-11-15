"""Template context processors for AstroPulse."""
from core.models import CheckIn, Reading
from core.services import current_blackout


def app_state(request):
    """Add local status and whether the latest displayed check-in is simulated."""
    latest_checkin = CheckIn.objects.select_related("crew_member").order_by(
        "-date", "-pk"
    ).first()
    simulated = False
    if latest_checkin:
        simulated = Reading.objects.filter(
            crew_member=latest_checkin.crew_member,
            recorded_at=latest_checkin.date,
            is_simulated=True,
        ).exists()
    return {"app_blackout": current_blackout(), "app_simulated": simulated}
