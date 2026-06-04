import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# =====================================================
# THIS FUNCTION MUST EXIST EXACTLY LIKE THIS
# =====================================================
def talk(user_message: str) -> str:
    """
    Small talk handler using Groq LLM
    """

    if not user_message:
        return "I didn't understand that."

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a friendly assistant. Keep replies short and natural."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            temperature=0.7,
            max_tokens=150
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error: {str(e)}"