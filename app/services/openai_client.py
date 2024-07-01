from openai import OpenAI

class OpenAIClient:
    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key
        )

    def _generate_text(self, messages={}, model="gpt-3.5-turbo"):
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return completion.choices[0].message.content

    def evaluate_relevance(self, title):
        messages=[
            {"role": "system", "content":"你是一個關聯度評估機器人，請評估新聞標題是否與「民生用品的價格變化」相關，並給予'high'、'medium'、'low'評價。(僅需回答'high'、'medium'、'low'三個詞之一)"},
            {"role": "user", "content": f"{title}"}
        ]
        return openai_client._generate_text(messages=messages)
    
    def generate_summary(self, content):
        print(content)
        messages=[
            {"role": "system", "content":"你是一個新聞摘要生成機器人，請統整新聞中提及的影響及主要原因 (影響、原因各50個字，請以json格式回答 {'影響': '...', '原因': '...'})"},
            {"role": "user", "content": f"{content}"}
        ]
        return openai_client._generate_text(messages=messages)


from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

openai_client = OpenAIClient(api_key=api_key)
