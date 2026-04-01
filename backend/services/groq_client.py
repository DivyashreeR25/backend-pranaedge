from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def call_groq(prompt, model="llama-3.1-8b-instant", max_tokens=1500):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an AI wellness expert."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content