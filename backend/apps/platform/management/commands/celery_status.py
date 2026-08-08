"""Report Celery broker, beat schedule, and worker ping.

  python manage.py celery_status
  python manage.py celery_status --require-workers
"""

from django.core.management.base import BaseCommand, CommandError

from core.health.checks import check_celery


class Command(BaseCommand):
    help = "Show Celery health: broker, beat schedule, workers"

    def add_arguments(self, parser):
        parser.add_argument(
            "--require-workers",
            action="store_true",
            help="Exit non-zero unless at least one worker responds to ping",
        )

    def handle(self, *args, **options):
        result = check_celery(require_workers=options["require_workers"])
        self.stdout.write(f"status: {result['status']}")
        self.stdout.write(f"broker: {result['broker']}")
        self.stdout.write(f"scheduled_jobs: {result['scheduled_jobs']}")
        for name in result.get("scheduled_tasks") or []:
            self.stdout.write(f"  - {name}")
        workers = result.get("workers") or []
        self.stdout.write(f"workers_online: {len(workers)}")
        for w in workers:
            self.stdout.write(f"  - {w}")
        if result.get("detail"):
            self.stdout.write(f"detail: {result['detail']}")
        if result["status"] == "error":
            raise CommandError("Celery health check failed.")
        if options["require_workers"] and result["status"] != "ok":
            raise CommandError("Celery workers required but not healthy.")
