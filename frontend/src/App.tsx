import { useState } from 'react'
import DocumentUploader from './components/DocumentUploader'
import QueryInterface from './components/QueryInterface'
import SystemMonitor from './components/SystemMonitor'
import { Document } from './types'
import { deleteDocument } from './api'

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const formatDate = (isoString: string): string => {
  return new Date(isoString).toLocaleString()
}

// Format PDF creation date (usually in D:YYYYMMDDHHmmSS format)
const formatPDFDate = (dateStr: string): string => {
  if (!dateStr || !dateStr.startsWith('D:')) return dateStr
  const match = dateStr.match(/D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})/)
  if (!match) return dateStr
  const [_, year, month, day, hour, minute, second] = match
  return new Date(
    parseInt(year),
    parseInt(month) - 1,
    parseInt(day),
    parseInt(hour),
    parseInt(minute),
    parseInt(second)
  ).toLocaleString()
}

const App = () => {
  const [currentDocument, setCurrentDocument] = useState<Document | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showMetadata, setShowMetadata] = useState(false)

  const handleDeleteDocument = async () => {
    if (!currentDocument) return
    
    try {
      setIsDeleting(true)
      await deleteDocument(currentDocument.document_id)
      setCurrentDocument(null)
    } catch (error) {
      console.error('Error deleting document:', error)
      alert('Failed to delete document. Please try again.')
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-start mb-8">
          <h1 className="text-3xl font-bold text-gray-800">PDF Document Q&A</h1>
          <div className="w-96">
            <SystemMonitor />
          </div>
        </div>
        
        {!currentDocument ? (
          <DocumentUploader onDocumentProcessed={setCurrentDocument} />
        ) : (
          <div>
            <div className="bg-white p-6 rounded-lg shadow-md mb-6">
              <div className="flex justify-between items-start">
                <div className="flex-grow">
                  <h2 className="text-xl font-semibold mb-4">Current Document: {currentDocument.filename}</h2>
                  {currentDocument.metadata && (
                    <div>
                      <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
                        <div>
                          <strong>Status:</strong> 
                          <span className={`ml-2 ${
                            currentDocument.status === 'completed' ? 'text-green-600' : 
                            currentDocument.status === 'processing' ? 'text-blue-600' :
                            currentDocument.status.startsWith('error') ? 'text-red-600' :
                            'text-gray-600'
                          }`}>
                            {currentDocument.status}
                          </span>
                        </div>
                        <div><strong>File Size:</strong> {formatFileSize(currentDocument.metadata.file_size)}</div>
                        <div><strong>Total Pages:</strong> {currentDocument.metadata.total_pages}</div>
                        <div><strong>Total Chunks:</strong> {currentDocument.metadata.chunk_count}</div>
                        {currentDocument.metadata.average_chunk_length && (
                          <div><strong>Avg. Chunk Size:</strong> {formatFileSize(currentDocument.metadata.average_chunk_length)}</div>
                        )}
                        <div><strong>Processed:</strong> {formatDate(currentDocument.metadata.processed_at)}</div>
                        {currentDocument.metadata.completed_at && (
                          <div><strong>Completed:</strong> {formatDate(currentDocument.metadata.completed_at)}</div>
                        )}
                      </div>

                      {currentDocument.metadata.pdf_metadata && (
                        <div className="mt-4">
                          <button
                            onClick={() => setShowMetadata(!showMetadata)}
                            className="text-sm text-blue-600 hover:text-blue-800"
                          >
                            {showMetadata ? 'Hide PDF Metadata' : 'Show PDF Metadata'}
                          </button>
                          
                          {showMetadata && (
                            <div className="mt-2 grid grid-cols-2 gap-4 text-sm text-gray-600 bg-gray-50 p-4 rounded-md">
                              {currentDocument.metadata.pdf_metadata.title && (
                                <div><strong>Title:</strong> {currentDocument.metadata.pdf_metadata.title}</div>
                              )}
                              {currentDocument.metadata.pdf_metadata.author && (
                                <div><strong>Author:</strong> {currentDocument.metadata.pdf_metadata.author}</div>
                              )}
                              {currentDocument.metadata.pdf_metadata.subject && (
                                <div><strong>Subject:</strong> {currentDocument.metadata.pdf_metadata.subject}</div>
                              )}
                              {currentDocument.metadata.pdf_metadata.creator && (
                                <div><strong>Creator:</strong> {currentDocument.metadata.pdf_metadata.creator}</div>
                              )}
                              {currentDocument.metadata.pdf_metadata.creation_date && (
                                <div><strong>Created:</strong> {formatPDFDate(currentDocument.metadata.pdf_metadata.creation_date)}</div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
                <div className="space-x-4 ml-4">
                  <button 
                    onClick={handleDeleteDocument}
                    disabled={isDeleting}
                    className="text-sm text-red-600 hover:text-red-800 disabled:text-gray-400"
                  >
                    {isDeleting ? 'Deleting...' : 'Delete Document'}
                  </button>
                  <button 
                    onClick={() => setCurrentDocument(null)}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    Change Document
                  </button>
                </div>
              </div>
              
              {currentDocument.error && (
                <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-md">
                  {currentDocument.error}
                </div>
              )}
            </div>
            
            {currentDocument.status === 'completed' && (
              <QueryInterface documentId={currentDocument.document_id} />
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default App