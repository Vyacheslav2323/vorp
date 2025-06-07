from django.db import models
from django.contrib.auth.models import User

class UserVocabulary(models.Model):
    """
    Store user's vocabulary words with their learning status using lemmas
    """
    STATUS_CHOICES = [
        ('unknown', 'Unknown'),
        ('learning', 'Learning'),
        ('learned', 'Learned'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    word = models.CharField(max_length=200)  # Original word as encountered
    lemma = models.CharField(max_length=200, default='')  # Base form of the word
    vocabulary_form = models.CharField(max_length=200, blank=True, null=True)  # Proper vocabulary form from OpenAI
    translation = models.CharField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    language = models.CharField(max_length=10, default='en')  # Language of the word
    target_language = models.CharField(max_length=10, default='ko')  # Language to translate to
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'lemma', 'language']  # Use lemma for uniqueness
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'lemma']),  # Index on lemma instead of word
            models.Index(fields=['user', 'word']),  # Keep index on word for search
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.word} (lemma: {self.lemma}, {self.status})"

class VocabularySet(models.Model):
    """
    Allow users to organize vocabulary into sets/collections
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'name']
    
    def __str__(self):
        return f"{self.user.username}: {self.name}"

class VocabularySetMembership(models.Model):
    """
    Many-to-many relationship between vocabulary words and sets
    """
    vocabulary_word = models.ForeignKey(UserVocabulary, on_delete=models.CASCADE)
    vocabulary_set = models.ForeignKey(VocabularySet, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['vocabulary_word', 'vocabulary_set']
    
    def __str__(self):
        return f"{self.vocabulary_word.word} in {self.vocabulary_set.name}"
