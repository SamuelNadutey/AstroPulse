"""Load SIMULATED demo readings for one scenario.

Usage:
    python manage.py seed_demo --scenario <name> [--reset]

Only the demo crew member's data is touched. Without --reset, the command
fails if demo data already exists, so scenarios cannot silently mix.
With --reset, the demo crew member's existing readings and check-ins are
replaced. All rows are marked is_simulated=True and must be shown as SIMULATED.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import CheckIn, CrewMember, Reading
from simulator.generator import SCENARIOS, generate, load_indicators

DEMO_NAME = "Demo crew (SIMULATED)"
DEMO_ENVIRONMENT = "station"
DEMO_DAYS = 21
DEMO_SEED = 42


class Command(BaseCommand):
    help = "Load SIMULATED demo readings for a scenario (21 days, seeded)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--scenario",
            required=True,
            choices=SCENARIOS,
            help="Scenario name.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the demo crew member's existing readings and check-ins first.",
        )

    def handle(self, *args, **options):
        scenario = options["scenario"]
        indicators = load_indicators()
        rows = generate(scenario, days=DEMO_DAYS, seed=DEMO_SEED)
        today = timezone.localdate()

        demo_exists = CrewMember.objects.filter(name=DEMO_NAME).exists()
        if demo_exists and not options["reset"]:
            raise CommandError("Demo data is already loaded. Re-run with --reset to replace it.")

        with transaction.atomic():
            crew, _ = CrewMember.objects.get_or_create(name=DEMO_NAME)
            if options["reset"]:
                Reading.objects.filter(crew_member=crew).delete()
                CheckIn.objects.filter(crew_member=crew).delete()

            blackout_by_day: dict[int, bool] = {}
            for row in rows:
                recorded_on = today - timedelta(days=DEMO_DAYS - row["day"])
                blackout_by_day[row["day"]] = blackout_by_day.get(row["day"], False) or row["in_blackout"]
                Reading.objects.update_or_create(
                    crew_member=crew,
                    indicator_key=row["indicator_key"],
                    recorded_at=recorded_on,
                    defaults={
                        "value": row["value"],
                        "environment": DEMO_ENVIRONMENT,
                        "is_simulated": True,
                        "in_blackout": row["in_blackout"],
                    },
                )

            for day, in_blackout in blackout_by_day.items():
                CheckIn.objects.update_or_create(
                    crew_member=crew,
                    date=today - timedelta(days=DEMO_DAYS - day),
                    defaults={
                        "environment": DEMO_ENVIRONMENT,
                        "in_blackout": in_blackout,
                        "note": "SIMULATED demo check-in",
                    },
                )

        self._print_summary(scenario, crew, rows, indicators, blackout_by_day, today)

    def _print_summary(self, scenario, crew, rows, indicators, blackout_by_day, today):
        keys = [ind["key"] for ind in indicators]
        table: dict[int, dict[str, float]] = {}
        for row in rows:
            table.setdefault(row["day"], {})[row["indicator_key"]] = row["value"]

        self.stdout.write(
            self.style.SUCCESS(
                f"SIMULATED demo data loaded: scenario '{scenario}', crew '{crew.name}', "
                f"{DEMO_DAYS} days, {len(keys)} indicators ({len(rows)} readings)."
            )
        )
        header = f"{'day':>3}  {'date':<10}  " + "  ".join(f"{k:>12}" for k in keys) + "  blackout"
        self.stdout.write(header)
        self.stdout.write("-" * len(header))
        for day in range(1, DEMO_DAYS + 1):
            date = today - timedelta(days=DEMO_DAYS - day)
            values = "  ".join(f"{table[day][k]:>12.2f}" for k in keys)
            flag = "yes" if blackout_by_day.get(day) else "no"
            self.stdout.write(f"{day:>3}  {date.isoformat():<10}  {values}  {flag:>8}")
