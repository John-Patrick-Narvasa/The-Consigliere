
TheConsigliere/

│

├── data/                       # Local directory for your book PDFs

│   ├── art_of_war.pdf

│   └── atomic_habits.pdf

│

├── src/

│   ├──  **init** .py

│   │

│   ├── ingestion/             # The Data Pipeline

│   │   ├──  **init** .py

│   │   ├── parser.py          # Extracts text & page metadata using PyMuPDF

│   │   └── ingest.py          # Chunks, embeds, and uploads to Pinecone

│   │

│   ├── agent/                 # The Brain (LangGraph)

│   │   ├──  **init** .py

│   │   ├── graph.py           # Defines the LangGraph state and workflow

│   │   ├── nodes.py           # Advice, Procedure, and System prompt logic

│   │   ├── state.py           # Defines agent memory/state structures

│   │   └── prompts.py         # The strict "Consigliere" prompts

│   │

│   └── api/                   # The Server Layer

│       ├──  **init** .py

│       └── main.py            # FastAPI application routes

│

├── .env                       # API keys and environment secrets

├── requirements.txt           # Python dependencies

└── app.py                     # Streamlit frontend prototype
