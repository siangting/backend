## 啟動 command
'''
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
'''

## ENV (置於/backend/下)
OPENAI_API_KEY=YOUR_API_KEY
SECRET_KEY=YOUR_SECRET_KEY (用於加密)