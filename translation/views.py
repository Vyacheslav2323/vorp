from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
from .word_processor import word_processor

logger = logging.getLogger(__name__)

@csrf_exempt
def translate_word_ajax(request):
    """
    AJAX endpoint to translate words using word processor
    """
    if request.method == 'POST':
        try:
            # Parse JSON data from request
            data = json.loads(request.body)
            word = data.get('word', '').strip()
            context = data.get('context', '').strip()
            
            if not word:
                return JsonResponse({
                    'success': False, 
                    'error': 'No word provided'
                }, status=400)
            
            # Use word processor to get base form and translation
            analysis = word_processor.get_vocabulary_forms_from_text(word)
            
            if analysis and word in analysis:
                word_data = analysis[word]
                vocabulary_form = word_data['vocabulary_form']
                translation = word_data['translation']
                
                return JsonResponse({
                    'success': True,
                    'vocabulary_form': vocabulary_form,
                    'translation': translation
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Translation failed'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=405)

@csrf_exempt
@require_http_methods(["POST"])
def translate_phrase(request):
    try:
        data = json.loads(request.body)
        phrase = data.get('phrase', '')
        if not phrase:
            return JsonResponse({'error': 'No phrase provided'}, status=400)

        # Use word_processor to get translation
        analysis = word_processor.get_vocabulary_forms_from_text(phrase)
        if not analysis:
            return JsonResponse({'error': 'Could not translate phrase'}, status=400)

        # Get the translation for the first (and only) word
        translation = next(iter(analysis.values()))['translation']
        return JsonResponse({'translation': translation})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def translation_preferences(request):
    """
    View for managing user translation preferences
    """
    from .models import UserTranslationPreference
    
    # Get or create user preferences
    preferences, created = UserTranslationPreference.objects.get_or_create(
        user=request.user,
        defaults={
            'default_source_language': 'auto',
            'default_target_language': 'en',
            'enable_auto_translation': True
        }
    )
    
    if request.method == 'POST':
        # Update preferences
        preferences.default_source_language = request.POST.get('default_source_language', 'auto')
        preferences.default_target_language = request.POST.get('default_target_language', 'en')
        preferences.enable_auto_translation = request.POST.get('enable_auto_translation') == 'on'
        preferences.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Preferences updated successfully'
        })
    
    return JsonResponse({
        'default_source_language': preferences.default_source_language,
        'default_target_language': preferences.default_target_language,
        'enable_auto_translation': preferences.enable_auto_translation
    })
