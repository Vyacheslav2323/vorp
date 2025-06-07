import openai
import os
from dotenv import load_dotenv

load_dotenv()  # load .env variables
openai.api_key = os.getenv("OPENAI_API_KEY")

response = openai.ChatCompletion.create(
    model="gpt-4o",  # or "gpt-4o" if you have access
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Once upon a time,"}
    ],
    max_tokens=50
)


print(response.choices[0].message.content.strip())