#!/usr/bin/env python3
import os
import django
import openai
import json

# — set up Django environment —
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nameless_vocab_app.settings")
django.setup()

# — imports from your app —
from users.models import CustomUser
from vocab_list.textgen import simple_tokens

# — configure OpenAI key —
openai.api_key = os.getenv("OPENAI_API_KEY")

def debug_generate(user, topic, target_lang, native_lang):
    print(f"\n🔍 Debugging generate_text for user={user.username}")
    print(f"   topic       = {topic!r}")
    print(f"   target_lang = {target_lang!r}")
    print(f"   native_lang = {native_lang!r}\n")

    # 1) build the exact prompt you use in generate_text_for_user()
    system_msg = "You are a creative sci-fi writer who ALWAYS uses the requested language strictly."
    user_msg = f"Write one fun, advanced-vocab paragraph about space & aliens ENTIRELY in {target_lang}."
    print(">>> SYSTEM MESSAGE:")
    print(system_msg)
    print(">>> USER MESSAGE:")
    print(user_msg, "\n")

    # 2) call GPT directly
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg},
        ],
        temperature=1.0,
        max_tokens=300,
    )
    raw = resp.choices[0].message.content
    print("=== RAW GPT OUTPUT ===")
    print(raw or "(empty string)")
    print("======================\n")

    # 3) tokenize
    tokens = simple_tokens(raw)
    print("TOKENS (simple_tokens):", tokens, "\n")

    # 4) compute coverage / unknowns
    #    assume user has no known words for this test
    known = set()  
    unknowns = [t for t in tokens if t.lower() not in known]
    coverage = 1 - len(unknowns)/len(tokens) if tokens else 0.0
    print(f"Coverage: {coverage:.2%}")
    print("Unknown lemmas:", unknowns, "\n")

if __name__ == "__main__":
    try:
        user = CustomUser.objects.get(username="slim")
    except CustomUser.DoesNotExist:
        print("User 'slim' not found in database.")
        exit(1)

    # tweak these to your test parameters:
    debug_generate(user, topic="space", target_lang="ko", native_lang="en")
