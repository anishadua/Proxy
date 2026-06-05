Purpose:
The purpose of the LLM-RAG (Retrieval-Augmented Generation) pipeline is to allow users to upload documents and ask questions based on their content, leveraging vector databases for efficient retrieval and LLM APIs for contextual answer generation.

Tech stack:
The technology stack used in this project includes:
- FastAPI (Python) for the backend
- `pypdf` for document parsing
- `langchain` for chunking
- `sentence-transformers` for embeddings
- `ChromaDB` with SQLite for vector database
- `MongoDB` (`pymongo`) for metadata database
- Google Gemini API (`google-generativeai`) for LLM provider
- Docker and Docker Compose for containerization

Architecture:
The architecture of the LLM-RAG pipeline is as follows:
- User interacts with the FastAPI application
- FastAPI handles upload and query requests
- DocumentProcessor processes uploaded documents and stores metadata in MongoDB
- VectorDB (ChromaDB) is used for efficient retrieval of relevant chunks
- FastAPI sends relevant chunks to LLM (Google Gemini API) for answer generation
- LLM generates answers and returns them to FastAPI
- FastAPI returns answers to the user

Design tradeoffs:
Not documented

What she'd do differently / future work:
Future enhancements include:
- Supporting additional file formats (.docx, .txt, .csv) with unstructured.io
- Implementing semantic/heading-aware chunking
- Adding user authentication and authorization
- Implementing hybrid and re-ranking search
- Creating a cloud IaC (Terraform/AWS CloudFormation)
- Developing a frontend UI for easier access
- Using cloud-based vector DBs (Pinecone, Qdrant) for production
- Using Celery for async chunking
- Scaling FastAPI with Docker containers and a load balancer
- Integrating logging and monitoring tools (ELK, Datadog, etc.)