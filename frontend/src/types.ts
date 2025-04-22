export interface Document {
  document_id: string
  filename: string
  status: string
  error?: string
  metadata?: {
    processed_at: string
    completed_at?: string
    file_size: number
    chunk_count: number
    total_pages: number
    average_chunk_length?: number
    processing_progress?: number
    error?: string
    pdf_metadata?: {
      title: string
      author: string
      subject: string
      creator: string
      creation_date: string
    }
  }
}

export interface QueryResponse {
  answer: string
  context: string[]
  confidence: number
  metadata: {
    model: string
    chunks_used: number
    total_tokens: number
    context_window: number
    device: string
  }
}