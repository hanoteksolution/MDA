from django.core.management.base import BaseCommand

from apps.authentication.bootstrap import bootstrap_roles_and_permissions


class Command(BaseCommand):
    help = "Bootstrap system roles and permissions (no users, company, or sample data)"

    def handle(self, *args, **options):
        bootstrap_roles_and_permissions(stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS("System bootstrap completed."))
