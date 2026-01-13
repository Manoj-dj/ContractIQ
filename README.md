# ContractIQ - AI-Powered Contract Analysis System

An end-to-end MLOps project for intelligent contract clause extraction, risk assessment, and conversational Q&A using fine-tuned transformer models and Retrieval-Augmented Generation (RAG).

## Overview

ContractIQ is a production-ready AI system that extracts 41 different clause types from legal contracts, performs automated risk analysis, and provides an interactive conversational interface for contract exploration. The project demonstrates comprehensive MLOps practices from model training to cloud deployment.

## Key Features

- **Intelligent Clause Extraction**: Fine-tuned TinyRoBERTa-SQuAD2 model achieving 85.97% F1 score on CUAD dataset
- **Risk Assessment Engine**: Automated risk scoring with HIGH/MEDIUM/LOW classification
- **Conversational RAG**: Multi-stage Retrieval-Augmented Generation with ChromaDB and Gemini 2.5 Flash
- **Citation-Backed Responses**: All AI responses include source references from the contract
- **In-Memory Chat History**: SQLite-based conversation persistence similar to ChatGPT
- **Professional Dashboard**: Clean, responsive UI with real-time analysis updates
- **Excel Export**: One-click export of complete analysis reports
- **Production-Ready**: Containerized deployment with CI/CD pipeline

## Technology Stack

### Machine Learning
- PyTorch for model training and inference
- Hugging Face Transformers (TinyRoBERTa-SQuAD2 base model)
- INT8 quantization for optimized inference
- MLflow + DagsHub for experiment tracking and model versioning

### Backend
- FastAPI for high-performance async API
- PDFMiner.six for text extraction
- ChromaDB for vector storage
- sentence-transformers (all-MiniLM-L6-v2) for embeddings
- Google Gemini API for conversational AI
- SQLite for chat history persistence

### Frontend
- Vanilla JavaScript with modern ES6+
- Responsive CSS with custom design system
- Real-time progress tracking

### MLOps & Infrastructure
- Docker for containerization
- GitHub Actions for CI/CD automation
- AWS ECR for container registry
- AWS EC2 for production hosting
- Git LFS for large file management

## Model Performance

Trained on CUAD (Contract Understanding Atticus Dataset) with intelligent downsampling:

**Training Results (3 epochs):**
- Overall F1 Score: 85.97%
- Exact Match: 81.82%
- AUPR: 91.20%
- P@80%R: 85.57%
- NoAns Accuracy: 93.14%

**Loss Progression:**
- Epoch 1: 0.0982 validation loss
- Epoch 2: 0.0849 validation loss
- Epoch 3: 0.0780 validation loss


## Quick Start

### Prerequisites
- Python 3.10+
- Docker (for containerized deployment)
- GEMINI_API_KEY (for conversational features)

### Local Development

```bash
# Clone repository
git clone https://github.com/Manoj-dj/ContractIQ.git
cd ContractIQ

# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
export GEMINI_API_KEY=your_api_key_here
export MODEL_PATH=./checkpoint-4089

# Run backend
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Access at http://localhost:8000


Docker Deployment


# Build image
docker build -t contractiq .

# Run container
docker run -d -p 8000:8000 \
  -e GEMINI_API_KEY=your_api_key \
  --name contractiq \
  contractiq
```


**Project Structure**

ContractIQ/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # API endpoints
│   │   ├── services/          # Business logic
│   │   └── main.py            # FastAPI application
│   └── requirements.txt
├── frontend/
│   ├── css/                   # Stylesheets
│   ├── js/                    # Client-side logic
│   └── index.html
├── checkpoint-4089/           # Fine-tuned model weights
├── Dockerfile
├── .github/workflows/
│   └── deploy.yml            # CI/CD pipeline
└── README.md

API Documentation
Once running, access interactive API docs at:

Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc

Deployment Pipeline
Automated CI/CD with GitHub Actions:

Test Stage: Linting and unit tests

Build Stage: Docker image creation with LFS support

Push Stage: Upload to AWS ECR

Deploy Stage: Pull and run on EC2 with health checks

Future Enhancements
OCR integration for scanned documents

Model refinement for improved accuracy on challenging clause types

Multi-language support

Batch processing capabilities

Advanced analytics dashboard

Documentation
For detailed technical documentation including model training process, architecture decisions, and deployment strategy, see PROJECT_DOCUMENTATION.pdf

Author
Manoj DJ
