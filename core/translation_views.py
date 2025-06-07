from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import json
from .theme_config import get_theme_context
from .models import UserVocabulary
from translation.word_processor import word_processor

@csrf_exempt
@require_http_methods(["POST"])
def translate_text(request):
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        if not text:
            return JsonResponse({'error': 'No text provided'}, status=400)

        # Use word_processor to get translations
        analysis = word_processor.get_vocabulary_forms_from_text(text)
        if not analysis:
            return JsonResponse({'error': 'Could not translate text'}, status=400)

        # Return all translations
        return JsonResponse({'translations': analysis})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def translate_word_api(request):
    """API endpoint for translating a single word using word processor"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            word = data.get('word', '')
            
            if not word:
                return JsonResponse({'error': 'No word provided'}, status=400)
            
            # Use word processor
            analysis = word_processor.get_vocabulary_forms_from_text(word)
            if not analysis or word not in analysis:
                return JsonResponse({'error': 'Could not translate word'}, status=400)
                
            word_data = analysis[word]
            
            # Return the translation without saving to vocabulary
            return JsonResponse({
                'success': True,
                'original_word': word,
                'vocabulary_form': word_data['vocabulary_form'],
                'translation': word_data['translation']
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)

@csrf_exempt
def detect_language_api(request):
    """API endpoint for detecting language using OpenAI"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            text = data.get('text', '')
            
            if not text:
                return JsonResponse({'error': 'No text provided'}, status=400)
            
            # Use OpenAI language detection
            detected_language = translator.detect_language(text)
            
            return JsonResponse({
                'success': True,
                'text': text,
                'detected_language': detected_language
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)

def translator_page(request):
    """Main translator page with UI"""
    context = get_theme_context()
    context['title'] = 'AI Translator'
    
    # Available languages for translation
    context['languages'] = [
        {'code': 'ko', 'name': 'Korean'},
        {'code': 'en', 'name': 'English'}
    ]
    
    return render(request, 'core/translator.html', context)

@login_required
def auto_translate_vocabulary(request):
    """Auto-translate all user's vocabulary words that don't have translations"""
    if request.method == 'POST':
        try:
            # Get all vocabulary words without translations
            words_to_translate = UserVocabulary.objects.filter(
                user=request.user,
                translation__isnull=True
            ) | UserVocabulary.objects.filter(
                user=request.user,
                translation=""
            )
            
            translated_count = 0
            for vocab_word in words_to_translate:
                try:
                    # Use word processor to get base form and translation
                    analysis = word_processor.get_vocabulary_forms_from_text(vocab_word.word)
                    if analysis and vocab_word.word in analysis:
                        word_data = analysis[vocab_word.word]
                        vocab_word.vocabulary_form = word_data['vocabulary_form']
                        vocab_word.translation = word_data['translation']
                        vocab_word.save()
                        translated_count += 1
                except Exception as e:
                    continue  # Skip words that fail to translate
            
            return JsonResponse({
                'success': True,
                'translated_count': translated_count,
                'message': f'Successfully translated {translated_count} words'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405) 