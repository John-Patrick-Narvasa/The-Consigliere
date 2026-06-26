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

```
uvicorn src.api.main:app --reload
```
