from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
import json
from .models import UserVocabulary, VocabularySet, VocabularySetMembership
from core.theme_config import get_theme_context
from translation.vocabulary_service import vocabulary_service

@login_required
def my_vocabulary(request):
    """
    Display the user's vocabulary list showing both known and learning words using unique lemmas.
    """
    context = get_theme_context()
    context['title'] = 'My Vocabulary'
    
    # Get the user's vocabulary from the database - already unique by lemma due to model constraints
    learned_words_objs = UserVocabulary.objects.filter(
        user=request.user, 
        status='learned'
    ).order_by('lemma')  # Order by lemma instead of word
    
    learning_words_objs = UserVocabulary.objects.filter(
        user=request.user, 
        status='learning'
    ).order_by('lemma')  # Order by lemma instead of word
    
    # Create word objects with translations for the template
    learned_words = []
    for obj in learned_words_objs:
        learned_words.append({
            'id': obj.id,
            'word': obj.word,  # Most recent form encountered
            'lemma': obj.lemma,  # Base form
            'vocabulary_form': obj.vocabulary_form or obj.lemma,  # Proper vocabulary form or fallback to lemma
            'translation': obj.translation or "",
            'language': obj.language,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at
        })
    
    learning_words = []
    for obj in learning_words_objs:
        learning_words.append({
            'id': obj.id,
            'word': obj.word,  # Most recent form encountered
            'lemma': obj.lemma,  # Base form
            'vocabulary_form': obj.vocabulary_form or obj.lemma,  # Proper vocabulary form or fallback to lemma
            'translation': obj.translation or "",
            'language': obj.language,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at
        })
    
    # Add to context
    context['learned_words'] = learned_words
    context['learning_words'] = learning_words
    
    # Only count learned and learning words for actual vocabulary stats
    vocabulary_words = len(learned_words) + len(learning_words)
    
    # Count stats (only for words in the vocabulary - learning and learned)
    context['stats'] = {
        'total_words': vocabulary_words,
        'learned_count': len(learned_words),
        'learning_count': len(learning_words),
        'learned_percent': round(len(learned_words) / vocabulary_words * 100 if vocabulary_words else 0, 1),
        'learning_percent': round(len(learning_words) / vocabulary_words * 100 if vocabulary_words else 0, 1),
    }
    
    return render(request, 'vocabulary/my_vocabulary.html', context)

@login_required
def vocabulary_sets(request):
    """
    Display user's vocabulary sets
    """
    context = get_theme_context()
    context['title'] = 'Vocabulary Sets'
    
    sets = VocabularySet.objects.filter(user=request.user).order_by('name')
    
    # Add word count to each set
    sets_with_counts = []
    for vocab_set in sets:
        word_count = VocabularySetMembership.objects.filter(vocabulary_set=vocab_set).count()
        sets_with_counts.append({
            'id': vocab_set.id,
            'name': vocab_set.name,
            'description': vocab_set.description,
            'word_count': word_count,
            'created_at': vocab_set.created_at,
            'updated_at': vocab_set.updated_at
        })
    
    context['vocabulary_sets'] = sets_with_counts
    
    return render(request, 'vocabulary/sets.html', context)

@login_required
def create_vocabulary_set(request):
    """
    Create a new vocabulary set
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            
            if not name:
                return JsonResponse({
                    'success': False,
                    'error': 'Set name is required'
                }, status=400)
            
            # Check if set already exists
            if VocabularySet.objects.filter(user=request.user, name=name).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'A set with this name already exists'
                }, status=400)
            
            # Create the set
            vocab_set = VocabularySet.objects.create(
                user=request.user,
                name=name,
                description=description
            )
            
            return JsonResponse({
                'success': True,
                'set_id': vocab_set.id,
                'name': vocab_set.name,
                'description': vocab_set.description
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Method not allowed'
    }, status=405)

@login_required
def add_word_to_set(request):
    """
    Add a word to a vocabulary set
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            word_id = data.get('word_id')
            set_id = data.get('set_id')
            
            # Get the vocabulary word and set
            vocab_word = get_object_or_404(UserVocabulary, id=word_id, user=request.user)
            vocab_set = get_object_or_404(VocabularySet, id=set_id, user=request.user)
            
            # Add to set (if not already in it)
            membership, created = VocabularySetMembership.objects.get_or_create(
                vocabulary_word=vocab_word,
                vocabulary_set=vocab_set
            )
            
            if created:
                return JsonResponse({
                    'success': True,
                    'message': f'Added "{vocab_word.word}" (lemma: {vocab_word.lemma}) to "{vocab_set.name}"'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Word is already in this set'
                })
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Method not allowed'
    }, status=405)

@login_required
def manage_word_lemma(request):
    """
    Manage a word's vocabulary form - allow user to see word information using OpenAI
    """
    if request.method == 'GET':
        word = request.GET.get('word', '').strip()
        language = request.GET.get('language', 'ko')  # Default to Korean
        
        if not word:
            return JsonResponse({
                'success': False,
                'error': 'No word provided'
            }, status=400)
        
        # Get vocabulary form and translation using OpenAI
        vocabulary_form, translation = vocabulary_service.get_vocabulary_form_and_translation(word, language)
        
        if not vocabulary_form:
            vocabulary_form = word  # Fallback to original word
        if not translation:
            translation = ''
        
        # Check if this vocabulary form exists in user's vocabulary
        try:
            vocab_entry = UserVocabulary.objects.get(
                user=request.user,
                lemma=vocabulary_form,  # vocabulary_form is stored as lemma
                language=language
            )
            
            return JsonResponse({
                'success': True,
                'word': word,
                'vocabulary_form': vocabulary_form,
                'translation': translation,
                'in_vocabulary': True,
                'status': vocab_entry.status,
                'stored_translation': vocab_entry.translation or '',
                'current_word_form': vocab_entry.word
            })
        except UserVocabulary.DoesNotExist:
            return JsonResponse({
                'success': True,
                'word': word,
                'vocabulary_form': vocabulary_form,
                'translation': translation,
                'in_vocabulary': False
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Method not allowed'
    }, status=405)
