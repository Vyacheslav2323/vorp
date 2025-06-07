from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from vocabulary.models import UserVocabulary
from translation.vocabulary_service import vocabulary_service

class Command(BaseCommand):
    help = 'Manage vocabulary: check status and clean up duplicates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='Check vocabulary status'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up duplicates and fix vocabulary forms'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Specific username to process'
        )

    def handle(self, *args, **options):
        if not options['check'] and not options['cleanup']:
            self.stdout.write('Please specify --check or --cleanup')
            return

        # Get users to process
        if options['username']:
            users = User.objects.filter(username=options['username'])
            if not users.exists():
                self.stdout.write(self.style.ERROR(f'User {options["username"]} not found'))
                return
        else:
            users = User.objects.all()

        if options['check']:
            self.check_vocabulary(users)
        
        if options['cleanup']:
            self.cleanup_vocabulary(users)

    def check_vocabulary(self, users):
        """Check vocabulary status for users"""
        self.stdout.write(self.style.SUCCESS('\n=== CHECKING VOCABULARY ==='))
        self.stdout.write(f'Total users to check: {users.count()}')

        for user in users:
            self.stdout.write(f'\n--- User: {user.username} ---')
            vocab_words = UserVocabulary.objects.filter(user=user).order_by('-created_at')
            self.stdout.write(f'Total vocabulary words: {vocab_words.count()}')

            if vocab_words.exists():
                self.stdout.write('\nRecent vocabulary entries:')
                for word in vocab_words[:10]:
                    self.stdout.write(
                        f'  - Word: {word.word} | '
                        f'Lemma: {word.lemma} | '
                        f'Vocab Form: {word.vocabulary_form} | '
                        f'Status: {word.status} | '
                        f'Lang: {word.language} | '
                        f'Created: {word.created_at}'
                    )

            # Show Korean vocabulary summary
            korean_words = vocab_words.filter(language='ko')
            self.stdout.write(f'\nKorean vocabulary: {korean_words.count()} words')
            if korean_words.exists():
                for word in korean_words.order_by('-created_at')[:10]:
                    self.stdout.write(
                        f'  - {word.word} → {word.vocabulary_form} '
                        f'({word.status}) [{word.translation}]'
                    )

    def cleanup_vocabulary(self, users):
        """Clean up vocabulary duplicates and fix forms"""
        self.stdout.write(self.style.SUCCESS('\n=== CLEANING UP VOCABULARY ==='))
        self.stdout.write(f'Total users to process: {users.count()}')

        for user in users:
            self.stdout.write(f'\n--- Processing user: {user.username} ---')
            korean_vocab = UserVocabulary.objects.filter(user=user, language='ko')
            self.stdout.write(f'Found {korean_vocab.count()} Korean vocabulary entries')

            # Group by vocabulary forms
            vocab_groups = {}
            for vocab in korean_vocab:
                correct_vocab_form, translation = vocabulary_service.get_vocabulary_form_and_translation(
                    vocab.word, 'ko'
                )
                if not correct_vocab_form:
                    correct_vocab_form = vocab.word

                if correct_vocab_form not in vocab_groups:
                    vocab_groups[correct_vocab_form] = []
                
                vocab_groups[correct_vocab_form].append({
                    'vocab_obj': vocab,
                    'correct_form': correct_vocab_form,
                    'translation': translation
                })

            # Process each group
            for correct_form, group in vocab_groups.items():
                if len(group) > 1:
                    self.stdout.write(f'\nFound {len(group)} entries for form "{correct_form}":')
                    
                    # Find best entry to keep
                    best_entry = None
                    entries_to_delete = []

                    for item in group:
                        vocab_obj = item['vocab_obj']
                        self.stdout.write(
                            f'  - ID {vocab_obj.id}: word="{vocab_obj.word}", '
                            f'lemma="{vocab_obj.lemma}", status="{vocab_obj.status}"'
                        )

                        if vocab_obj.lemma == correct_form:
                            if best_entry is None:
                                best_entry = item
                            else:
                                if (vocab_obj.status == 'learned' and best_entry['vocab_obj'].status != 'learned') or \
                                   (vocab_obj.status == 'learning' and best_entry['vocab_obj'].status == 'unknown'):
                                    entries_to_delete.append(best_entry)
                                    best_entry = item
                                else:
                                    entries_to_delete.append(item)
                        else:
                            entries_to_delete.append(item)

                    if best_entry is None:
                        best_entry = group[0]
                        entries_to_delete = group[1:]

                    # Update best entry
                    best_vocab = best_entry['vocab_obj']
                    best_vocab.lemma = correct_form
                    best_vocab.vocabulary_form = correct_form
                    if not best_vocab.translation and best_entry['translation']:
                        best_vocab.translation = best_entry['translation']
                    best_vocab.save()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Kept and updated entry ID {best_vocab.id}'))

                    # Delete duplicates
                    for item in entries_to_delete:
                        vocab_obj = item['vocab_obj']
                        self.stdout.write(f'  ✗ Deleted duplicate entry ID {vocab_obj.id}')
                        vocab_obj.delete()

                elif len(group) == 1:
                    # Update single entry if needed
                    item = group[0]
                    vocab_obj = item['vocab_obj']
                    if vocab_obj.lemma != correct_form or vocab_obj.vocabulary_form != correct_form:
                        old_lemma = vocab_obj.lemma
                        old_form = vocab_obj.vocabulary_form
                        
                        vocab_obj.lemma = correct_form
                        vocab_obj.vocabulary_form = correct_form
                        if not vocab_obj.translation and item['translation']:
                            vocab_obj.translation = item['translation']
                        vocab_obj.save()
                        
                        self.stdout.write(
                            f'Updated entry for "{vocab_obj.word}": '
                            f'lemma: "{old_lemma}" → "{vocab_obj.lemma}", '
                            f'form: "{old_form}" → "{vocab_obj.vocabulary_form}"'
                        )

            # Show final status
            final_vocab = UserVocabulary.objects.filter(user=user, language='ko').order_by('lemma')
            self.stdout.write(f'\nFinal vocabulary for {user.username}: {final_vocab.count()} entries') 