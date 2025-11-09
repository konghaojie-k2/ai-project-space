# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered project management system that supports multimodal content and intelligent Q&A. The system enables teams to manage projects through different stages (售前, 业务调研, 数据理解, etc.), upload files/web content, and use AI for context-aware conversations with RAG (Retrieval-Augmented Generation) capabilities.

## Development Commands

### Backend Development (UV Package Manager)
```bash
# Install dependencies and create virtual environment
uv sync

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Run backend development server
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest

# Code formatting and linting
black .
isort .
flake8 .
mypy backend/

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run tests
npm test
npm run test:ui
npm run test:headed

# Linting and type checking
npm run lint
npm run type-check
```

### Docker Development
```bash
# Quick start all services
bash quick-start.sh

# Or use Docker Compose directly
docker compose -f docker-compose.simple.yml up -d

# View logs
docker compose -f docker-compose.simple.yml logs -f

# Stop services
docker compose -f docker-compose.simple.yml down

# Production deployment
docker compose up -d
```

## System Architecture

### Backend Architecture (FastAPI)
The backend follows a service-oriented architecture with clear separation of concerns:

**Core Structure:**
- `backend/app/main.py`: FastAPI application entry point with CORS, middleware, and exception handling
- `backend/app/core/`: Configuration management (config.py), database setup, logging
- `backend/app/api/`: API routes organized by feature (auth, projects, files, chat)
- `backend/app/services/`: Business logic layer (ai_service.py, file_service.py)
- `backend/app/models/`: SQLAlchemy ORM models with async support
- `backend/app/schemas/`: Pydantic models for request/response validation

**Key Services:**
- **AI Service**: Integrates with Volcengine (豆包) and OpenAI APIs for LLM capabilities
- **File Service**: Handles multimodal file uploads, processing, and vectorization
- **Model Loader**: Manages AI model loading and switching
- **Authentication**: JWT-based auth with role-based access control (admin, manager, member, viewer)

### Frontend Architecture (Next.js 14)
Modern React application using App Router with TypeScript:

**App Structure:**
- `frontend/app/(auth)/`: Authentication pages (login, register, forgot-password)
- `frontend/app/dashboard/`: Main application pages with layout protection
  - `projects/`: Project management with stage-based workflow
  - `chat/`: AI conversation interface with streaming responses
  - `files/`: File management with preview capabilities
- `frontend/components/`: Reusable components organized by type
  - `ui/`: Base UI components (Button, Input, Modal)
  - `features/`: Complex feature components (Chat, FileUpload, StreamingMarkdown)
  - `layout/`: Navigation and layout components

**State Management:**
- Zustand for global state
- TanStack Query for server state and caching
- React Hook Form with Zod for form validation

### AI/ML Integration
The system uses a sophisticated RAG architecture:

**AI Stack:**
- **Primary LLM**: Volcengine (豆包) with OpenAI API compatibility
- **Vector Database**: FAISS for document embeddings and similarity search
- **Framework**: LangChain for RAG pipeline orchestration
- **Embeddings**: Text-embedding models for document vectorization
- **Multi-modal**: Support for text, images, and document understanding

**RAG Pipeline:**
1. Document upload → Content extraction (PDF, DOCX, etc.)
2. Text splitting → Vector embedding → FAISS storage
3. Query processing → Vector similarity search → Context retrieval
4. LLM generation with retrieved context → Streaming response

### Database Architecture
**PostgreSQL Schema:**
- Projects with stage-based workflow (售前 → 业务调研 → 数据理解 → 数据探索 → 工程开发 → 实施部署)
- File metadata with permissions and content indexing
- Chat sessions with conversation history
- User management with role-based access control
- Project member assignments with hierarchical permissions

**Supporting Services:**
- Redis for caching and session storage
- MinIO for object storage (files, documents)
- ChromaDB for vector database operations

### Project Lifecycle Management
The system implements a 6-stage project workflow:
1. **售前** (Presales)
2. **业务调研** (Business Research)
3. **数据理解** (Data Understanding)
4. **数据探索** (Data Exploration)
5. **工程开发** (Engineering Development)
6. **实施部署** (Implementation & Deployment)

Each stage can have associated files, team members, and AI-powered Q&A contexts.

## Configuration

### Environment Variables
Key configuration in `.env` file:
```bash
# AI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_LLM_MODEL=gpt-3.5-turbo

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
REDIS_URL=redis://:password@localhost:6379/0

# File Storage
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=104857600  # 100MB

# Security
SECRET_KEY=your-secret-key-change-in-production
ENVIRONMENT=development
```

### Settings Management
- Uses Pydantic Settings for configuration with validation
- Environment-based configuration (development/production)
- CORS settings with automatic development mode configuration
- File type restrictions and upload limits
- Project stages and user roles configurable

## Key Technical Details

### Package Management
- **UV**: Fast Python package manager used for backend dependencies
- **npm**: Standard package manager for frontend dependencies
- **uv.lock**: Locks Python dependencies for reproducible builds

### Authentication & Authorization
- JWT tokens with access/refresh token rotation
- Role-based access control (RBAC) with hierarchical permissions
- Project-level membership with stage-based access
- API rate limiting and input validation

### File Processing
Supports multiple file formats with automatic content extraction:
- **Documents**: PDF, DOCX, XLSX, PPTX, TXT, MD
- **Images**: JPG, PNG, GIF, BMP, WebP with OCR capabilities
- **Audio**: MP3, WAV, FLAC with transcription
- **Video**: MP4, AVI, MOV, WMV with frame extraction

### Docker Deployment
Multi-service containerized architecture:
- PostgreSQL database with health checks
- Redis for caching and sessions
- MinIO object storage with web console
- ChromaDB for vector operations
- FastAPI backend application
- Next.js frontend application
- Nginx reverse proxy (production)

### Development Workflow
- **Hot Reload**: Enabled for both backend and frontend
- **Database Migrations**: Alembic for schema changes
- **Code Quality**: Black, isort, flake8, mypy for Python; ESLint, Prettier for TypeScript
- **Testing**: pytest for backend; Playwright for frontend E2E
- **Logging**: Loguru with structured logging and correlation IDs