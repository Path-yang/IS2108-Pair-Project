from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandParser

from customers.models import CustomerProfile


class Command(BaseCommand):
    help = "Identify and optionally remove test User accounts that are not linked to CustomerProfile data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Actually delete the test users (default is to only list them).",
        )
        parser.add_argument(
            "--unlinked-only",
            action="store_true",
            help="Only show/delete users that are not linked to any CustomerProfile.",
        )

    def handle(self, *args, **options):
        # Find potential test users
        # Common patterns: username contains "test", "demo", "example", or very generic names
        test_patterns = ["test", "demo", "example", "user", "admin"]
        
        all_users = User.objects.filter(is_staff=False)
        test_users = []
        
        for user in all_users:
            username_lower = user.username.lower()
            email_lower = (user.email or "").lower()
            
            # Check if username or email matches test patterns
            is_test = any(pattern in username_lower for pattern in test_patterns) or \
                     any(pattern in email_lower for pattern in test_patterns)
            
            # Also check if user has no linked CustomerProfile
            has_profile = CustomerProfile.objects.filter(user=user).exists()
            
            if options["unlinked_only"]:
                if not has_profile:
                    test_users.append((user, is_test, has_profile))
            else:
                if is_test or not has_profile:
                    test_users.append((user, is_test, has_profile))
        
        if not test_users:
            self.stdout.write(self.style.SUCCESS("No test users found."))
            return
        
        self.stdout.write(
            self.style.WARNING(
                f"Found {len(test_users)} potential test user(s):\n"
            )
        )
        
        for user, is_test_pattern, has_profile in test_users:
            reasons = []
            if is_test_pattern:
                reasons.append("matches test pattern")
            if not has_profile:
                reasons.append("no linked CustomerProfile")
            
            reason_str = " (" + ", ".join(reasons) + ")" if reasons else ""
            
            self.stdout.write(
                f"  - {user.username} ({user.email}){reason_str}"
            )
        
        if options["delete"]:
            self.stdout.write(self.style.WARNING("\nDeleting test users..."))
            deleted_count = 0
            for user, _, _ in test_users:
                username = user.username
                user.delete()
                deleted_count += 1
                self.stdout.write(f"  Deleted: {username}")
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully deleted {deleted_count} test user(s)."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "\nTo actually delete these users, run with --delete flag."
                )
            )
            if not options["unlinked_only"]:
                self.stdout.write(
                    self.style.WARNING(
                        "To only show users without CustomerProfile, use --unlinked-only flag."
                    )
                )

