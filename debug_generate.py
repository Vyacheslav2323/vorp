# debug_generate.py (next to manage.py)
import os, sys, django, openai, json, re

BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nameless_vocab_app.settings")
django.setup()

from django.contrib.auth import get_user_model
from vocab_list.textgen import generate_text_for_user
from vocab_list.utils import simple_tokens

openai.api_key = os.getenv("OPENAI_API_KEY")

def debug_generate(username, topic):
    User = get_user_model()
    user = User.objects.get(username=username)

    print(f"USER={user.username!r}, TARGET={user.target_language!r}, NATIVE={user.native_language!r}\n")

    text, cov, unknowns = generate_text_for_user(
        user=user,
        topic=topic,
        target_lang=user.target_language,
        target_pct=0.9,
        max_attempts=1,
    )

    print("1) RAW TEXT:\n", text or "<empty>", "\n")
    toks = simple_tokens(text or "")
    print("2) TOKENS:\n", toks, "\n")
    print("3) COVERAGE:", cov)
    print("4) UNKNOWNS:", unknowns)

if __name__ == "__main__":
    debug_generate("slim", "space and aliens")
