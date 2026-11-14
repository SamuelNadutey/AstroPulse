"""Management command: python manage.py check_guidance [--strict]."""
from django.core.management.base import BaseCommand, CommandError

from core.guidance import load_sources
from core.validation import collect_errors, list_needs_source


class Command(BaseCommand):
    help = "Validate guidance rules and citations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Also fail on sources that are not verified.",
        )

    def handle(self, *args, **options):
        errors = collect_errors(strict=options["strict"])
        needs_source = list_needs_source()

        todo_errors = [e for e in errors if "uses TODO source" in e]
        structural_errors = [e for e in errors if e not in todo_errors]

        if structural_errors:
            for msg in structural_errors:
                self.stdout.write(self.style.ERROR(msg))
            if needs_source:
                self.stdout.write(self.style.WARNING("Needs a source:"))
                for item in needs_source:
                    self.stdout.write(self.style.WARNING(f"  {item}"))
            raise CommandError("Guidance validation failed.")

        self.stdout.write(self.style.SUCCESS("OK"))

        if needs_source:
            self.stdout.write(
                self.style.WARNING(
                    f"{len(needs_source)} rules/actions still need a source"
                )
            )
            for item in needs_source:
                self.stdout.write(self.style.WARNING(f"  {item}"))

        if not options["strict"]:
            unverified = [s for s in load_sources().values() if not s.get("verified")]
            if unverified:
                self.stdout.write(
                    self.style.WARNING(
                        f"{len(unverified)} sources are not yet verified"
                    )
                )
