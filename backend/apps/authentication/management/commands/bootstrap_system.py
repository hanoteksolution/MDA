from django.core.management.base import BaseCommand

from apps.authentication.bootstrap import bootstrap_roles_and_permissions


class Command(BaseCommand):
    help = (
        "Bootstrap system roles and permissions (no users, company, or sample data). "
        "Additive by default — custom role permissions are preserved."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-role-permissions",
            action="store_true",
            help="Wipe each system role back to built-in defaults (destroys custom Admin changes).",
        )

    def handle(self, *args, **options):
        bootstrap_roles_and_permissions(
            stdout=self.stdout,
            reset_role_permissions=options["reset_role_permissions"],
        )
        self.stdout.write(self.style.SUCCESS("System bootstrap completed."))
