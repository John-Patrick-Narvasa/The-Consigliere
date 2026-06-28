# The Consigliere

An AI RAG agent that tells you advices and strategy based on some books

Setup

```
python -m venv venv
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

or

.\venv\Scripts\python.exe -m pip install --upgrade pip

pip install -r requirements.txt
```

Launching

```Shell
Run python test_agent.py locally to verify your google-genai integration behaves flawlessly within the LangGraph constraints.

uvicorn src.api.main:app --reload

streamlit run app.py
```
