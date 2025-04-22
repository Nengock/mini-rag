import { useState } from 'react'
import { askQuestion } from '../api'
import ReactMarkdown from 'react-markdown'

interface Props {
  documentId: string
}

interface QueryResult {
  answer: string
  context: string[]
  confidence: number
  metadata?: {
    model: string
    chunks_used: number
    total_tokens: number
    context_window: number
    device: string
  }
}

const ERROR_MESSAGES = {
  EMPTY_QUESTION: 'Please enter a question',
  TOO_LONG: 'Question is too long (max 500 characters)',
  NETWORK_ERROR: 'Failed to connect to the server. Please check your internet connection.',
  SERVER_ERROR: 'An error occurred while processing your question. Please try again.',
  DOC_NOT_FOUND: 'The document was not found or has not been processed yet.',
} as const

const QueryInterface = ({ documentId }: Props) => {
  const [question, setQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<QueryResult | null>(null)
  const [error, setError] = useState('')
  const [loadingMessage, setLoadingMessage] = useState('')

  const getErrorMessage = (error: any): string => {
    if (error?.response?.status === 404) {
      return ERROR_MESSAGES.DOC_NOT_FOUND
    }
    if (error?.response?.status === 400) {
      return error?.response?.data?.detail || ERROR_MESSAGES.SERVER_ERROR
    }
    if (error?.message?.includes('network')) {
      return ERROR_MESSAGES.NETWORK_ERROR
    }
    return ERROR_MESSAGES.SERVER_ERROR
  }

  const validateQuestion = (text: string): string | null => {
    if (!text.trim()) {
      return ERROR_MESSAGES.EMPTY_QUESTION
    }
    if (text.length > 500) {
      return ERROR_MESSAGES.TOO_LONG
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate question
    const validationError = validateQuestion(question)
    if (validationError) {
      setError(validationError)
      return
    }

    setIsLoading(true)
    setError('')
    setResult(null)
    setLoadingMessage('Processing your question...')

    try {
      const response = await askQuestion({
        question,
        document_id: documentId
      })
      setResult(response)
    } catch (err) {
      console.error('Query error:', err)
      setError(getErrorMessage(err))
    } finally {
      setIsLoading(false)
      setLoadingMessage('')
    }
  }

  return (
    <div className="bg-white p-8 rounded-lg shadow-md">
      <form onSubmit={handleSubmit} className="mb-6">
        <div className="mb-4">
          <label htmlFor="question" className="block text-sm font-medium text-gray-700 mb-2">
            Ask a question about the document
          </label>
          <div className="relative">
            <input
              type="text"
              id="question"
              value={question}
              onChange={(e) => {
                setQuestion(e.target.value)
                setError('')  // Clear error when user types
              }}
              className={`w-full px-4 py-2 border rounded-md focus:ring-blue-500 focus:border-blue-500
                ${error ? 'border-red-500' : 'border-gray-300'}
                ${isLoading ? 'bg-gray-50' : 'bg-white'}`}
              placeholder="Enter your question..."
              disabled={isLoading}
              maxLength={500}
            />
            <div className="absolute right-2 bottom-2 text-xs text-gray-400">
              {question.length}/500
            </div>
          </div>
        </div>
        
        <button
          type="submit"
          disabled={isLoading || !question.trim()}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 
                   disabled:bg-blue-300 disabled:cursor-not-allowed
                   transition-colors duration-200"
        >
          {isLoading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Processing...
            </span>
          ) : (
            'Ask Question'
          )}
        </button>
      </form>

      {error && (
        <div className="text-red-600 p-4 bg-red-50 rounded-md mb-4">
          {error}
        </div>
      )}

      {isLoading && loadingMessage && (
        <div className="text-blue-600 p-4 bg-blue-50 rounded-md mb-4 animate-pulse">
          {loadingMessage}
        </div>
      )}

      {result && (
        <div className="mt-6 space-y-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold mb-2">Answer:</h3>
            <div className="bg-gray-50 p-4 rounded-md prose max-w-none">
              <ReactMarkdown>{result.answer}</ReactMarkdown>
            </div>
          </div>
          
          <div>
            <h3 className="text-lg font-semibold mb-2">Relevant Context:</h3>
            <div className="bg-gray-50 p-4 rounded-md space-y-2">
              {result.context.map((text, index) => (
                <p key={index} className="text-sm text-gray-600">{text}</p>
              ))}
            </div>
          </div>
          
          <div className="mt-4 text-sm text-gray-500 space-y-1">
            <div>Confidence Score: {(result.confidence * 100).toFixed(1)}%</div>
            {result.metadata && (
              <>
                <div>Model: {result.metadata.model}</div>
                <div>Chunks Used: {result.metadata.chunks_used}</div>
                <div>Total Tokens: {result.metadata.total_tokens}</div>
                <div>Device: {result.metadata.device}</div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default QueryInterface