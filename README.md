# PDF Document Q&A System

A RAG (Retrieval-Augmented Generation) system for question answering over PDF documents. This application allows users to upload PDF documents and ask questions about their content, using advanced language models and vector search for accurate responses.

## Features

- PDF document upload and processing
- Text extraction and intelligent chunking
- Vector-based semantic search
- Question answering using state-of-the-art language models
- Real-time processing status updates
- System resource monitoring
- PDF metadata extraction and display
- Responsive web interface
- Docker-based deployment
- Development environment with hot reloading

## Prerequisites

- Docker and Docker Compose
- NVIDIA GPU (optional, for GPU acceleration)
- NVIDIA Container Toolkit (if using GPU)

## Quick Start

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd mini-rag
   ```

2. Create environment files:
   - Copy `.env.example` to `.env` for production
   - Copy `.env.development` for development

3. Start the application:

   For production:
   ```bash
   docker compose up -d
   ```

   For development:
   ```bash
   docker compose -f docker-compose.dev.yml up
   ```

4. Access the application:
   - Production: http://localhost
   - Development: http://localhost:5173

## Configuration

### Environment Variables

- `MODEL_DEVICE`: Set to 'gpu' to use CUDA if available (default: 'cpu')
- `TORCH_THREADS`: Number of threads for CPU processing (default: 4)
- `MAX_UPLOAD_SIZE`: Maximum PDF file size in bytes
- `MAX_PAGES`: Maximum number of pages per PDF
- `CHUNK_SIZE`: Text chunk size for processing
- `CHUNK_OVERLAP`: Overlap between chunks
- `CONTEXT_WINDOW`: Model context window size
- `MAX_RETRIES`: Maximum retries for processing tasks

### Development vs Production

The development environment includes:
- Hot reloading for both frontend and backend
- Larger file size limits
- Debug logging
- Direct volume mounts for code changes
- Vite dev server features

## Architecture

### Backend (FastAPI)

- PDF processing and text extraction
- Vector store management
- RAG implementation
- System metrics collection
- REST API endpoints

### Frontend (React + TypeScript)

- Document upload interface
- Real-time status updates
- Question answering interface
- System monitoring dashboard
- PDF metadata display

## Development

1. Start the development environment:
   ```bash
   docker compose -f docker-compose.dev.yml up
   ```

2. Frontend development:
   - Changes are automatically reflected
   - Access Vite dev server at http://localhost:5173

3. Backend development:
   - Changes trigger automatic reload
   - API available at http://localhost:8000
   - Swagger UI at http://localhost:8000/docs

## Production Deployment

1. Configure production environment:
   ```bash
   cp .env.example .env
   # Edit .env with production values
   ```

2. Build and start services:
   ```bash
   docker compose up -d --build
   ```

3. Monitor logs:
   ```bash
   docker compose logs -f
   ```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Resource Management

The application includes built-in resource monitoring:
- CPU usage tracking
- Memory usage monitoring
- GPU utilization (if available)
- Historical metrics collection
- Processing queue management

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Create a Pull Request

## License

[Your chosen license]

## Acknowledgments

- Mistral AI for the language model
- PyTorch team
- FastAPI framework
- React community