"""Daily check-in form built from data/indicators.json + data/environments.json.

Device indicators are only asked when the selected environment lists them in
``available_equipment`` (for example the rover has no SpO2 clip, so spo2 is
skipped there). Self-report indicators are always asked.

Valid ranges (min_valid/max_valid), the mood scale and the equipment lists
are PLACEHOLDERS, not clinical or operational values (AGENTS.md hard rule 6).
"""
from __future__ import annotations

from django import forms

from core.services import get_environment, load_environments, load_indicators

NON_INDICATOR_FIELDS = ("environment", "blackout", "note")


def _environment_choices() -> list[tuple[str, str]]:
    return [(entry["key"], entry["label"]) for entry in load_environments()]


class CheckInForm(forms.Form):
    """One day's check-in: environment, one field per askable indicator,
    a blackout checkbox and a free-text note."""

    def __init__(self, environment: str = "station", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.environment_key = environment
        self.environment_config = get_environment(environment)

        environment_field = forms.ChoiceField(
            label="Environment",
            choices=_environment_choices(),
            initial=self.environment_key,
        )
        # HTMX partial swap: re-render only the fields for the new
        # environment. The URL is a local placeholder route (no external URLs).
        environment_field.widget.attrs.update(
            {
                "hx-get": "/checkin/fields/",
                "hx-target": "#checkin-fields",
                "hx-swap": "outerHTML",
            }
        )
        self.fields["environment"] = environment_field

        equipment = set(self.environment_config["available_equipment"])
        for config in load_indicators():
            key = config["key"]
            if config["input_type"] == "device" and key not in equipment:
                continue  # e.g. the rover has no SpO2 clip
            self.fields[key] = self._indicator_field(config)

        self.fields["blackout"] = forms.BooleanField(
            label="Blackout: no contact with ground",
            required=False,
        )
        self.fields["note"] = forms.CharField(
            label="Note (optional)",
            required=False,
            widget=forms.Textarea(attrs={"rows": 2}),
        )

    @staticmethod
    def _indicator_field(config: dict):
        """Build a form field for one indicator with friendly error messages."""
        key = config["key"]
        label = config["label"]
        unit = config["unit"]
        lo = config["min_valid"]
        hi = config["max_valid"]
        if key == "mood":
            # Mood is the 1-to-5 self-report scale from the build plan.
            return forms.TypedChoiceField(
                label=label,
                choices=[(str(i), str(i)) for i in range(1, 6)],
                coerce=int,
                error_messages={
                    "invalid": "Mood should be a number from 1 to 5 (placeholder scale).",
                    "invalid_choice": "Mood should be a number from 1 to 5 (placeholder scale).",
                },
            )
        friendly = (
            f"{label} should be between {lo} and {hi} {unit} "
            f"(placeholder range, not a clinical limit)."
        )
        return forms.FloatField(
            label=label,
            min_value=lo,
            max_value=hi,
            error_messages={
                "required": f"{label} is needed for today's check-in.",
                "invalid": f"Enter {label.lower()} as a number.",
                "min_value": friendly,
                "max_value": friendly,
            },
            widget=forms.NumberInput(attrs={"inputmode": "decimal", "step": "any"}),
        )

    def link_errors_to_aria(self) -> None:
        """Point each invalid field's aria-describedby at its error block.

        Call after is_valid() so the template's error list
        (id="<auto_id>_error") is announced by screen readers.
        """
        for name, field in self.fields.items():
            prefix = self.add_prefix(name)
            errors = self.errors.get(prefix)
            if not errors:
                continue
            field_auto_id = self.auto_id % prefix if self.auto_id else ""
            if not field_auto_id:
                continue
            described = field.widget.attrs.get("aria-describedby", "")
            ids = [i for i in described.split() if i]
            error_id = f"{field_auto_id}_error"
            if error_id not in ids:
                ids.append(error_id)
            field.widget.attrs["aria-describedby"] = " ".join(ids)

    def indicator_values(self) -> list[tuple[str, float | int]]:
        """Return [(indicator_key, value)] from cleaned_data, in form order."""
        return [
            (key, value)
            for key, value in self.cleaned_data.items()
            if key not in NON_INDICATOR_FIELDS
        ]
