import { useState } from 'react'
import { Document } from '../types'
import { uploadDocument, checkDocumentStatus } from '../api'

interface Props {
  onDocumentProcessed: (document: Document) => void
}

const MAX_RETRIES = 30 // 1 minute timeout (2s * 30)
const RETRY_INTERVAL = 2000 // 2 seconds
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

// Error messages
const ERROR_MESSAGES = {
  FILE_TOO_LARGE: 'File size exceeds 10MB limit',
  INVALID_TYPE: 'Please upload a PDF file',
  CORRUPTED_PDF: 'The PDF file appears to be corrupted',
  EMPTY_PDF: 'No text content could be extracted from the PDF',
  UPLOAD_FAILED: 'Failed to upload document',
  PROCESSING_FAILED: 'Failed to process document',
  PROCESSING_TIMEOUT: 'Processing timed out',
  CONNECTION_ERROR: 'Connection error. Please check your internet connection',
} as const

const DocumentUploader = ({ onDocumentProcessed }: Props) => {
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<string>('')
  const [progressPercent, setProgressPercent] = useState<number>(0)
  const [retryCount, setRetryCount] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const getErrorMessage = (error: any): string => {
    if (error?.response?.status === 413) {
      return ERROR_MESSAGES.FILE_TOO_LARGE
    }
    
    const errorMessage = error?.response?.data?.detail || error?.message || 'Unknown error'
    
    if (errorMessage.includes('corrupted')) return ERROR_MESSAGES.CORRUPTED_PDF
    if (errorMessage.includes('no text content')) return ERROR_MESSAGES.EMPTY_PDF
    if (errorMessage.includes('network')) return ERROR_MESSAGES.CONNECTION_ERROR
    
    return errorMessage
  }

  const validateFile = (file: File): string | null => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      return ERROR_MESSAGES.INVALID_TYPE
    }
    if (file.size > MAX_FILE_SIZE) {
      return ERROR_MESSAGES.FILE_TOO_LARGE
    }
    return null
  }

  const parseProgressFromStatus = (status: string): number | null => {
    const match = status.match(/processing: .* \((\d+)%\)/)
    return match ? parseInt(match[1], 10) / 100 : null
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Reset states
    setIsUploading(true)
    setUploadProgress('Validating document...')
    setProgressPercent(0)
    setRetryCount(0)
    setError(null)

    // Validate file
    const validationError = validateFile(file)
    if (validationError) {
      setIsUploading(false)
      setError(validationError)
      return
    }

    try {
      setUploadProgress('Uploading document...')
      setProgressPercent(0.1)
      const formData = new FormData()
      formData.append('file', file)

      const response = await uploadDocument(formData)
      const { document_id } = response

      // Poll for document processing status
      const checkStatus = async () => {
        try {
          const status = await checkDocumentStatus(document_id)
          
          if (status.status === 'completed') {
            setIsUploading(false)
            setProgressPercent(1)
            onDocumentProcessed(status)
          } else if (status.status.startsWith('error')) {
            setIsUploading(false)
            setError(status.status.replace('error: ', ''))
          } else {
            if (retryCount >= MAX_RETRIES) {
              setIsUploading(false)
              setError(ERROR_MESSAGES.PROCESSING_TIMEOUT)
              return
            }
            
            // Parse progress from status message
            const progress = parseProgressFromStatus(status.status)
            if (progress !== null) {
              setProgressPercent(progress)
            }
            
            setUploadProgress(status.status)
            setRetryCount(prev => prev + 1)
            setTimeout(checkStatus, RETRY_INTERVAL)
          }
        } catch (error) {
          console.error('Status check error:', error)
          if (retryCount >= MAX_RETRIES) {
            setIsUploading(false)
            setError(ERROR_MESSAGES.PROCESSING_FAILED)
            return
          }
          setRetryCount(prev => prev + 1)
          setTimeout(checkStatus, RETRY_INTERVAL)
        }
      }

      await checkStatus()
    } catch (error) {
      console.error('Upload error:', error)
      setIsUploading(false)
      setError(getErrorMessage(error))
    }
  }

  return (
    <div className="bg-white p-8 rounded-lg shadow-md">
      <div className="text-center">
        <h2 className="text-xl font-semibold mb-4">Upload PDF Document</h2>
        
        <label className="block">
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileUpload}
            disabled={isUploading}
            className="block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-full file:border-0
              file:text-sm file:font-semibold
              file:bg-blue-50 file:text-blue-700
              hover:file:bg-blue-100
              disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </label>

        {error && (
          <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-md">
            {error}
          </div>
        )}

        {isUploading && !error && (
          <div className="mt-4">
            <div className="text-blue-600 mb-2">
              {uploadProgress}
            </div>
            
            {/* Progress bar */}
            <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className="h-full bg-blue-600 transition-all duration-500 ease-out"
                style={{ width: `${progressPercent * 100}%` }}
              />
            </div>
            
            <div className="text-sm text-gray-500 mt-2">
              {Math.round(progressPercent * 100)}% complete
            </div>
            
            {retryCount > 0 && (
              <div className="text-gray-500 text-sm mt-2">
                Time remaining: {Math.ceil((MAX_RETRIES - retryCount) * RETRY_INTERVAL / 1000)}s
              </div>
            )}
          </div>
        )}

        <div className="mt-4 text-sm text-gray-500">
          Maximum file size: 10MB
        </div>
      </div>
    </div>
  )
}

export default DocumentUploader