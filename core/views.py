from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from datetime import date

from .theme_config import get_theme_context
from vocabulary.models import UserVocabulary
from translation.word_processor import word_processor
from translation.vocabulary_service import vocabulary_service
from .text_utils import demo_highlight_text, highlight_text_html_with_lemmas
from .models import WordClassificationHistory, LearningMetrics

import logging
logger = logging.getLogger(__name__)


def index(request):
    context = get_theme_context()
    return render(request, 'core/index.html', context)


def login_view(request):
    context = get_theme_context()
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if not remember:
                request.session.set_expiry(0)
            return redirect('index')
        else:
            context['error'] = "Invalid username or password. Please try again."

    return render(request, 'core/login.html', context)


def logout_view(request):
    logout(request)
    return redirect('login')


def register_view(request):
    context = get_theme_context()
    context['native_languages'] = [
        {'code': 'en', 'name': 'English'},
        {'code': 'ko', 'name': 'Korean'},
        {'code': 'zh', 'name': 'Chinese'},
        {'code': 'ru', 'name': 'Russian'},
    ]
    context['target_languages'] = [
        {'code': 'en', 'name': 'English'},
        {'code': 'ko', 'name': 'Korean'},
    ]

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        native_language = request.POST.get('native_language')
        target_language = request.POST.get('target_language')

        if not (username and email and password1 and password2 and native_language and target_language):
            context['error'] = "All fields are required."
            return render(request, 'core/register.html', context)

        if password1 != password2:
            context['error'] = "Passwords do not match."
            return render(request, 'core/register.html', context)

        if native_language == target_language:
            context['error'] = "Native and target languages cannot be the same."
            return render(request, 'core/register.html', context)

        if User.objects.filter(username=username).exists():
            context['error'] = "Username already exists."
            return render(request, 'core/register.html', context)

        if User.objects.filter(email=email).exists():
            context['error'] = "Email already registered."
            return render(request, 'core/register.html', context)

        try:
            user = User.objects.create_user(username=username, email=email, password=password1)
            # (In a real app, you'd save native/target in a profile model.)
            user = authenticate(request, username=username, password=password1)
            if user:
                login(request, user)
                return redirect('index')
            else:
                return redirect('login')
        except Exception as e:
            context['error'] = f"Registration error: {e}"
            return render(request, 'core/register.html', context)

    return render(request, 'core/register.html', context)


@login_required
def vocabulary_test(request):
    """
    Vocabulary test view for Korean → English translation using OpenAI word processing.

    On POST: store the submitted text into session so that after marking words
    as "learning" or "learned," a page refresh will re-analyse the same text.
    """
    # Get theme context (dark/light mode)
    context = get_theme_context()
    context['title'] = 'Vocabulary Test - Korean → English'

    source_lang = 'ko'
    target_lang = 'en'

    # 1️⃣ Determine which text to analyze:
    if request.method == 'POST':
        user_text = request.POST.get('text', '').strip()
        # Save whatever the user submitted into the session (even if blank string)
        request.session['vocab_last_text'] = user_text
    else:
        # On GET, try to reuse the last‐submitted text from session
        user_text = request.session.get('vocab_last_text', '').strip()

    # 2️⃣ If there's no text in session (or user submitted blank), fall back to sample:
    if not user_text:
        user_text = """부서지마! 바라봐 주세요.
안녕하세요. 저는 한국어를 공부하고 있어요.
먹고 싶어요. 가고 싶어요."""

    context['original_text'] = user_text

    # 3️⃣ Build the user_vocabulary dict from the database:
    user_vocabulary = {}
    if request.user.is_authenticated:
        vocab_qs = UserVocabulary.objects.filter(user=request.user, language=source_lang)
        user_vocabulary = {
            vocab.lemma: {
                'status': vocab.status,
                'translation': vocab.translation or '',
                'word': vocab.word,
                'vocabulary_form': vocab.vocabulary_form or vocab.lemma
            }
            for vocab in vocab_qs
        }

    # 4️⃣ Run the OpenAI‐powered processing on exactly this `user_text`:
    if user_text:
        result = word_processor.process_text_for_vocabulary_test(user_text, user_vocabulary)
        context.update({
            'highlighted_html': result['html'],
            'stats': result['stats'],
            'word_analysis': result.get('word_analysis', {}),
            'matched_words': result.get('matched_words', {}),
        })

    return render(request, 'core/vocabulary_test.html', context)


# (Other views remain unchanged…)
