"""Template context processors for AstroPulse."""
from core.services import current_blackout


def app_state(request):
    """Add the current global blackout state to every template context."""
    return {"app_blackout": current_blackout()}
