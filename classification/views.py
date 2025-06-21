from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
import json
from datetime import date
from vocabulary.models import UserVocabulary
from .models import WordClassificationHistory, LearningMetrics
from translation.vocabulary_service import vocabulary_service
from translation.word_processor import WordProcessor
import logging
from core.models import DailyAnalysisUsage

# Set up logging
logger = logging.getLogger(__name__)


@login_required
def mark_as_learned(request):
    """
    Handle AJAX requests to mark learning words as learned using OpenAI vocabulary forms.
    """
    if request.method == 'POST':
        try:
            # Parse JSON data from request
            data = json.loads(request.body)
            word = data.get('word')
            vocabulary_form = data.get('vocabulary_form')  # Get vocabulary form from frontend
            language = data.get('language', get_word_language(request))
            
            # Use the vocabulary form passed from frontend, or get it from OpenAI if needed
            if not vocabulary_form:
                vocabulary_form, _ = vocabulary_service.get_vocabulary_form_and_translation(
                    word,
                    language,
                    data.get('full_text', '')  # Pass context if available
                )
                vocabulary_form = vocabulary_form or word
            
            # Update the word status in the database using vocabulary form as lemma
            try:
                vocab_word = UserVocabulary.objects.get(
                    user=request.user, 
                    lemma=vocabulary_form,  # Use vocabulary form as lemma
                    language=language
                )
                
                # Check if the word is currently in learning status
                if vocab_word.status == 'learning':
                    old_status = vocab_word.status
                    
                    # Update to learned
                    vocab_word.status = 'learned'
                    vocab_word.vocabulary_form = vocabulary_form  # Ensure vocabulary form is set
                    vocab_word.save()
                    
                    # Record the change in history
                    WordClassificationHistory.objects.create(
                        user=request.user,
                        word=f"{word} (vocabulary_form: {vocabulary_form})",
                        old_status=old_status,
                        new_status='learned'
                    )
                    
                    # Update learning metrics
                    update_learning_metrics(request.user, words_learned=1)
                    
                    # Get updated counts
                    learned_count = UserVocabulary.objects.filter(user=request.user, status='learned').count()
                    learning_count = UserVocabulary.objects.filter(user=request.user, status='learning').count()
                    vocabulary_words = learned_count + learning_count
                    
                    stats = {
                        'total_words': vocabulary_words,
                        'learned_count': learned_count,
                        'learning_count': learning_count,
                        'learned_percent': round(learned_count / vocabulary_words * 100 if vocabulary_words else 0, 1),
                        'learning_percent': round(learning_count / vocabulary_words * 100 if vocabulary_words else 0, 1),
                    }
                    
                    return JsonResponse({
                        'success': True,
                        'word': word,
                        'vocabulary_form': vocabulary_form,
                        'translation': vocab_word.translation or '',
                        'new_status': 'learned',
                        'stats': stats
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'Word "{word}" (vocabulary_form: {vocabulary_form}) is not currently in learning status'
                    })
                    
            except UserVocabulary.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Word "{word}" (vocabulary_form: {vocabulary_form}) not found in your vocabulary'
                })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

@login_required
def mark_as_unknown(request):
    """
    Handle AJAX requests to remove words from vocabulary.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            word = data.get('word')
            language = data.get('language', get_word_language(request))
            
            # Find all matching words and delete them
            vocab_words = UserVocabulary.objects.filter(
                user=request.user, 
                word=word,
                language=language
            )
            
            if not vocab_words.exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Word "{word}" not found in your vocabulary'
                })
            
            # Record the status of the first word (they should all be the same)
            old_status = vocab_words[0].status
            
            # Delete all matching words
            vocab_words.delete()
            
            # Record the change
            WordClassificationHistory.objects.create(
                user=request.user,
                word=word,
                old_status=old_status,
                new_status='deleted'
            )
            
            # Get updated counts
            learned_count = UserVocabulary.objects.filter(user=request.user, status='learned', language=language).count()
            learning_count = UserVocabulary.objects.filter(user=request.user, status='learning', language=language).count()
            vocabulary_words = learned_count + learning_count
            
            stats = {
                'total_words': vocabulary_words,
                'learned_count': learned_count,
                'learning_count': learning_count
            }
            
            return JsonResponse({
                'success': True,
                'stats': stats
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

@login_required
def remove_known_word(request):
    """
    Handle AJAX requests to remove known words from vocabulary using OpenAI vocabulary forms.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            word = data.get('word')
            lemma = data.get('lemma')  # This is actually the vocabulary_form from frontend
            language = data.get('language', get_word_language(request))
            
            # Use the lemma/vocabulary_form passed from frontend, or get it from OpenAI if needed
            if not lemma:
                vocabulary_form, _ = vocabulary_service.get_vocabulary_form_and_translation(
                    word,
                    language,
                    data.get('full_text', '')  # Pass context if available
                )
                lemma = vocabulary_form or word
            
            try:
                vocab_word = UserVocabulary.objects.get(
                    user=request.user, 
                    lemma=lemma,
                    language=language
                )
                
                if vocab_word.status == 'learned':
                    old_status = vocab_word.status
                    vocab_word.status = 'unknown'
                    vocab_word.save()
                    
                    # Record the change
                    WordClassificationHistory.objects.create(
                        user=request.user,
                        word=f"{word} (vocabulary_form: {lemma})",
                        old_status=old_status,
                        new_status='unknown'
                    )
                    
                    # Get updated counts
                    learned_count = UserVocabulary.objects.filter(user=request.user, status='learned').count()
                    learning_count = UserVocabulary.objects.filter(user=request.user, status='learning').count()
                    vocabulary_words = learned_count + learning_count
                    
                    stats = {
                        'total_words': vocabulary_words,
                        'learned_count': learned_count,
                        'learning_count': learning_count,
                        'learned_percent': round(learned_count / vocabulary_words * 100 if vocabulary_words else 0, 1),
                        'learning_percent': round(learning_count / vocabulary_words * 100 if vocabulary_words else 0, 1),
                    }
                    
                    return JsonResponse({
                        'success': True,
                        'word': word,
                        'vocabulary_form': lemma,
                        'new_status': 'unknown',
                        'stats': stats
                    })
                elif vocab_word.status == 'unknown':
                    # If word is already unknown, just delete it completely
                    vocab_word.delete()
                    
                    # Record the change
                    WordClassificationHistory.objects.create(
                        user=request.user,
                        word=f"{word} (vocabulary_form: {lemma})",
                        old_status='unknown',
                        new_status='deleted'
                    )
                    
                    # Get updated counts
                    learned_count = UserVocabulary.objects.filter(user=request.user, status='learned').count()
                    learning_count = UserVocabulary.objects.filter(user=request.user, status='learning').count()
                    vocabulary_words = learned_count + learning_count
                    
                    stats = {
                        'total_words': vocabulary_words,
                        'learned_count': learned_count,
                        'learning_count': learning_count,
                        'learned_percent': round(learned_count / vocabulary_words * 100 if vocabulary_words else 0, 1),
                        'learning_percent': round(learning_count / vocabulary_words * 100 if vocabulary_words else 0, 1),
                    }
                    
                    return JsonResponse({
                        'success': True,
                        'word': word,
                        'vocabulary_form': lemma,
                        'new_status': 'deleted',
                        'stats': stats
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'Word "{word}" (vocabulary_form: {lemma}) is currently in "{vocab_word.status}" status, not learned status'
                    })
                    
            except UserVocabulary.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Word "{word}" (vocabulary_form: {lemma}) not found in your vocabulary'
                })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

@login_required
def update_word_status(request):
    """
    AJAX: change a word from 'unknown' → 'learning'.

    We **trust the vocabulary_form sent by the browser**.  We only call the
    VocabularyService / OpenAI when the translation is missing.  The lemma
    is stored exactly as sent, so the same span will match on reload.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)

    # ------------------------------------------------------------------
    # 1) Parse payload
    # ------------------------------------------------------------------
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    word            = data.get("word", "").strip()               # surface token
    vocabulary_form = data.get("vocabulary_form", "").strip()    # lemma from span
    current_status  = data.get("current_status", "").strip()     # should be 'unknown'
    translation     = (data.get("translation") or "").strip()
    language        = data.get("language", "ko")
    full_text       = data.get("full_text", "")

    if not word or not vocabulary_form:
        return JsonResponse({"success": False, "error": "Word/lemma missing"}, status=400)

    if current_status != "unknown":
        return JsonResponse(
            {"success": False, "error": f'Word "{word}" is not in unknown status'},
            status=400,
        )

    # ------------------------------------------------------------------
    # 2) If translation missing, ask service once
    # ------------------------------------------------------------------
    if not translation:
        _, translation = vocabulary_service.get_vocabulary_form_and_translation(
            word, language, full_text or word
        )

    # ------------------------------------------------------------------
    # 3) Upsert the row keyed by **vocabulary_form sent from browser**
    # ------------------------------------------------------------------
    try:
        vocab_entry, created = UserVocabulary.objects.update_or_create(
            user=request.user,
            lemma=vocabulary_form,              # EXACT lemma from span
            language=language,
            defaults={
                "word": word,
                "vocabulary_form": vocabulary_form,
                "translation": translation,
                "status": "learning",
            },
        )
    except Exception as e:
        logger.error("Error saving UserVocabulary: %s", e, exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)

    # ------------------------------------------------------------------
    # 4) Return success + updated counts (optional)
    # ------------------------------------------------------------------
    learned_count  = UserVocabulary.objects.filter(user=request.user, status="learned",  language=language).count()
    learning_count = UserVocabulary.objects.filter(user=request.user, status="learning", language=language).count()
    total          = learned_count + learning_count

    stats = {
        "total_words": total,
        "learned_count": learned_count,
        "learning_count": learning_count,
        "learned_percent": round(learned_count  / total * 100, 1) if total else 0,
        "learning_percent": round(learning_count / total * 100, 1) if total else 0,
    }

    return JsonResponse(
        {
            "success": True,
            "word": word,
            "vocabulary_form": vocabulary_form,
            "translation": translation,
            "new_status": "learning",
            "stats": stats,
        }
    )

@login_required
def api_vocabulary_analysis(request):
    """
    API endpoint to analyze text and return vocabulary information
    """
    if request.method == 'POST':
        try:
            # Check if user has reached their daily limit
            if not DailyAnalysisUsage.can_analyze(request.user):
                time_until_reset = DailyAnalysisUsage.get_time_until_reset()
                hours, remainder = divmod(time_until_reset.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return JsonResponse({
                    'success': False,
                    'error': f"You've reached your daily limit of 5 analyses. The limit will reset in {hours:02d}:{minutes:02d}:{seconds:02d}.",
                    'limit_reached': True,
                    'reset_in': {
                        'hours': hours,
                        'minutes': minutes,
                        'seconds': seconds
                    }
                }, status=429)  # 429 Too Many Requests
            
            data = json.loads(request.body)
            text = data.get('text', '')
            language = data.get('language', get_word_language(request))
            
            if not text:
                return JsonResponse({'success': False, 'error': 'No text provided'})
            
            # Get user's vocabulary dictionary
            user_vocabulary = get_user_vocabulary_dict(request.user, language)
            
            # Process text using word processor
            result = word_processor.process_text_for_vocabulary_test(text, user_vocabulary)
            
            # Increment the usage counter
            usage = DailyAnalysisUsage.get_today_usage(request.user)
            usage.increment()
            
            # Get time until next reset
            time_until_reset = DailyAnalysisUsage.get_time_until_reset()
            hours, remainder = divmod(time_until_reset.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            return JsonResponse({
                'success': True,
                'html': result['html'],
                'stats': result['stats'],
                'analyses_remaining': max(5 - usage.count, 0),
                'analyses_used': usage.count,
                'reset_in': {
                    'hours': hours,
                    'minutes': minutes,
                    'seconds': seconds
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)