from openai import OpenAI

class OpenAIClient:
    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key
        )

    def generate_text(self, messages={}, model="gpt-3.5-turbo"):
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return completion.choices[0].message.content


from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

openai_client = OpenAIClient(api_key=api_key)
