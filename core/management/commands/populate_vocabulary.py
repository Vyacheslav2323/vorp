from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserVocabulary

class Command(BaseCommand):
    help = 'Populate the database with sample vocabulary for users'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username to populate vocabulary for (optional)')

    def handle(self, *args, **options):
        username = options.get('username')
        
        # Sample vocabulary
        sample_words = {
            'hello': 'learned',
            'world': 'learning',
            'welcome': 'learned',
            'to': 'learned',
            'the': 'learned',
            'django': 'learning',
            'application': 'learning',
            'this': 'learned',
            'is': 'learned',
            'a': 'learned',
            'test': 'learning',
            'for': 'learned',
            'text': 'learned',
            'programming': 'learning',
            'python': 'learning',
            'javascript': 'learning',
            'html': 'learned',
            'css': 'learned',
            'database': 'learning',
        }
        
        if username:
            # Get specific user
            try:
                users = [User.objects.get(username=username)]
                self.stdout.write(f"Adding vocabulary for user: {username}")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User '{username}' does not exist"))
                return
        else:
            # Get all users
            users = User.objects.all()
            self.stdout.write(f"Adding vocabulary for all users ({users.count()} users found)")
        
        for user in users:
            # Count how many words were added/updated
            added_count = 0
            updated_count = 0
            
            for word, status in sample_words.items():
                # Create or update the vocabulary word
                obj, created = UserVocabulary.objects.update_or_create(
                    user=user,
                    word=word,
                    defaults={'status': status}
                )
                
                if created:
                    added_count += 1
                else:
                    updated_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'User "{user.username}": Added {added_count} new words, updated {updated_count} existing words'
                )
            )
        
        self.stdout.write(self.style.SUCCESS('Vocabulary population completed')) 