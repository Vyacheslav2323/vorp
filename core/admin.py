from django.contrib import admin
from .models import UserVocabulary

@admin.register(UserVocabulary)
class UserVocabularyAdmin(admin.ModelAdmin):
    list_display = ('word', 'status', 'user', 'updated_at')
    list_filter = ('status', 'user')
    search_fields = ('word', 'user__username')
    ordering = ('word',)
    date_hierarchy = 'updated_at'
