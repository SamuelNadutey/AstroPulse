"""Data models for AstroPulse.

Demo data created by seed_demo is SIMULATED and must be labeled as such
wherever it is shown (AGENTS.md hard rule 3).
"""
from django.db import models

# Environment keys from the build plan (section 4). Labels and equipment
# details come from data/environments.json in Stage 3.
ENVIRONMENT_CHOICES = [
    ("station", "Station"),
    ("transit", "Transit"),
    ("rover", "Rover"),
    ("surface_base", "Surface base"),
]


class CrewMember(models.Model):
    """A crew member profile. Demo profiles are created by seed_demo."""

    name = models.CharField(max_length=120)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Reading(models.Model):
    """One indicator value for one crew member on one day.

    indicator_key must match a key in data/indicators.json.
    """

    crew_member = models.ForeignKey(
        CrewMember,
        on_delete=models.CASCADE,
        related_name="readings",
    )
    indicator_key = models.CharField(max_length=32)
    value = models.FloatField()
    recorded_at = models.DateField()
    environment = models.CharField(max_length=32, choices=ENVIRONMENT_CHOICES)
    is_simulated = models.BooleanField(default=False)
    in_blackout = models.BooleanField(default=False)

    class Meta:
        ordering = ["recorded_at", "indicator_key"]
        constraints = [
            models.UniqueConstraint(
                fields=["crew_member", "indicator_key", "recorded_at"],
                name="unique_reading_per_indicator_per_day",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.crew_member} {self.indicator_key} {self.recorded_at}: {self.value}"


class CheckIn(models.Model):
    """A daily check-in for one crew member."""

    crew_member = models.ForeignKey(
        CrewMember,
        on_delete=models.CASCADE,
        related_name="checkins",
    )
    date = models.DateField()
    environment = models.CharField(max_length=32, choices=ENVIRONMENT_CHOICES)
    in_blackout = models.BooleanField(default=False)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(
                fields=["crew_member", "date"],
                name="unique_checkin_per_day",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.crew_member} check-in {self.date}"


class AppState(models.Model):
    """Singleton application state.

    Holds the current crew-facing toggle state such as blackout mode.
    Only one row should ever exist; views use get_or_create(id=1).
    """

    blackout = models.BooleanField(
        default=False,
        help_text="Current blackout state: no contact with ground.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Application state"
        verbose_name_plural = "Application state"

    def __str__(self) -> str:
        return f"AppState blackout={self.blackout}"


class RelayItem(models.Model):
    """One item to relay to ground once comms are restored.

    Created when an indicator is flagged during blackout. Open items are
    deduplicated by (crew_member, indicator_key, for_date) so the same day
    cannot generate multiple unresolved entries.
    """

    crew_member = models.ForeignKey(
        CrewMember,
        on_delete=models.CASCADE,
        related_name="relay_items",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    for_date = models.DateField()
    indicator_key = models.CharField(max_length=32)
    severity = models.CharField(max_length=16)
    headline = models.TextField()
    reason = models.TextField(blank=True)
    action_taken = models.TextField(blank=True)
    contact_ground_open = models.BooleanField(default=False)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-for_date", "indicator_key"]
        constraints = [
            models.UniqueConstraint(
                fields=["crew_member", "indicator_key", "for_date"],
                name="unique_open_relay_item_per_day",
                condition=models.Q(resolved=False),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.crew_member} {self.indicator_key} {self.for_date}: {self.severity}"
