"""Seed a handful of decoy admin accounts used as lures.

These are NOT real Django users — they carry no permissions and can never
authenticate. They only make the decoy endpoints/login look populated.
"""
from django.core.management.base import BaseCommand

from honeypot.models import DecoyAccount

_DECOYS = [
    ("admin", "Superuser", "admin@educto.io"),
    ("administrator", "Administrator", "administrator@educto.io"),
    ("root", "System", "root@educto.io"),
    ("backup_admin", "Backup Operator", "backup@educto.io"),
    ("svc_deploy", "Service Account", "deploy@educto.io"),
]


class Command(BaseCommand):
    help = "Create decoy admin accounts for the honeypot."

    def handle(self, *args, **options):
        created = 0
        for username, role, email in _DECOYS:
            _, was_created = DecoyAccount.objects.get_or_create(
                username=username,
                defaults={"display_role": role, "email": email},
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(
            f"Decoy accounts ready ({created} created, "
            f"{DecoyAccount.objects.count()} total)."
        ))
