/**
 * TicketDetail component - full ticket view with retract button
 */
import { useState, useEffect } from 'react'
import { apiClient } from '../services/api'
import type { TicketDetail as TicketDetailType } from '../types'

interface TicketDetailProps {
  ticketKey: string
  onBack?: () => void
}

export function TicketDetail({ ticketKey, onBack }: TicketDetailProps) {
  const [ticket, setTicket] = useState<TicketDetailType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retractLoading, setRetractLoading] = useState(false)
  const [retractSuccess, setRetractSuccess] = useState(false)

  useEffect(() => {
    loadTicket()
  }, [ticketKey])

  const loadTicket = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await apiClient.getTicketDetail(ticketKey)
      setTicket(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load ticket')
    } finally {
      setLoading(false)
    }
  }

  const handleRetract = async () => {
    if (!ticket) return

    const confirmed = window.confirm(
      `Are you sure you want to retract the automated response for ${ticketKey}?\n\n` +
        `This will:\n` +
        `- Strike through the original comment in Jira\n` +
        `- Add a note that it was retracted\n` +
        `- Log the retraction in audit logs\n\n` +
        `This action cannot be undone.`
    )

    if (!confirmed) return

    const retractedBy = prompt('Enter your name or email:')
    if (!retractedBy) return

    setRetractLoading(true)
    setError(null)

    try {
      await apiClient.retractResponse(ticketKey, retractedBy)
      setRetractSuccess(true)
      // Reload ticket to show retracted status
      await loadTicket()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to retract response')
    } finally {
      setRetractLoading(false)
    }
  }

  const canRetract = () => {
    if (!ticket) return false
    if (ticket.action !== 'auto_respond') return false
    if (ticket.retracted_at) return false

    // Check if within 5-minute window
    if (ticket.comment_posted_at) {
      const postedAt = new Date(ticket.comment_posted_at)
      const now = new Date()
      const elapsedMinutes = (now.getTime() - postedAt.getTime()) / 1000 / 60
      return elapsedMinutes <= 5
    }

    return false
  }

  const getTimeRemaining = () => {
    if (!ticket?.comment_posted_at) return null

    const postedAt = new Date(ticket.comment_posted_at)
    const now = new Date()
    const elapsedSeconds = (now.getTime() - postedAt.getTime()) / 1000
    const remainingSeconds = 300 - elapsedSeconds // 5 minutes = 300 seconds

    if (remainingSeconds <= 0) return 'Window expired'

    const minutes = Math.floor(remainingSeconds / 60)
    const seconds = Math.floor(remainingSeconds % 60)
    return `${minutes}m ${seconds}s remaining`
  }

  if (loading) {
    return <div className="p-4">Loading ticket details...</div>
  }

  if (error && !ticket) {
    return <div className="p-4 text-red-600">Error: {error}</div>
  }

  if (!ticket) {
    return <div className="p-4">Ticket not found</div>
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {onBack && (
        <button onClick={onBack} className="mb-4 text-blue-600 hover:underline">
          ← Back to list
        </button>
      )}

      <div className="bg-white shadow rounded-lg p-6">
        {/* Header */}
        <div className="flex justify-between items-start mb-6">
          <div>
            <h1 className="text-3xl font-bold mb-2">{ticket.ticket_key}</h1>
            <p className="text-gray-600">{ticket.summary}</p>
          </div>
          <a
            href={ticket.jira_url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            View in Jira →
          </a>
        </div>

        {/* Success message */}
        {retractSuccess && (
          <div className="mb-4 p-4 bg-green-100 border border-green-400 rounded">
            Response successfully retracted!
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 rounded">
            {error}
          </div>
        )}

        {/* Action and Status */}
        <div className="grid grid-cols-2 gap-6 mb-6">
          <div>
            <h3 className="text-sm font-semibold text-gray-500 mb-2">Action</h3>
            <span
              className={`px-3 py-1 text-sm font-semibold rounded ${
                ticket.action === 'auto_respond'
                  ? 'bg-green-100 text-green-800'
                  : ticket.action === 'escalate'
                  ? 'bg-yellow-100 text-yellow-800'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              {ticket.action.replace('_', ' ').toUpperCase()}
            </span>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-500 mb-2">Status</h3>
            {ticket.retracted_at ? (
              <span className="text-red-600 font-semibold">
                Retracted by {ticket.retracted_by}
              </span>
            ) : ticket.action === 'auto_respond' ? (
              <span className="text-green-600">Response Posted</span>
            ) : (
              <span className="text-gray-500">Escalated</span>
            )}
          </div>
        </div>

        {/* Ticket Details */}
        <div className="border-t pt-6 mb-6">
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <span className="text-sm font-semibold text-gray-500">Reporter:</span>
              <span className="ml-2">{ticket.reporter}</span>
            </div>
            <div>
              <span className="text-sm font-semibold text-gray-500">Created:</span>
              <span className="ml-2">{new Date(ticket.created).toLocaleString()}</span>
            </div>
          </div>

          <div className="mb-4">
            <h3 className="text-sm font-semibold text-gray-500 mb-2">Description</h3>
            <p className="text-gray-700 whitespace-pre-wrap">
              {ticket.description || '(No description)'}
            </p>
          </div>
        </div>

        {/* Response/Escalation Info */}
        {ticket.action === 'auto_respond' && (
          <div className="border-t pt-6 mb-6">
            <h3 className="text-sm font-semibold text-gray-500 mb-2">Matched Response</h3>
            <p className="font-mono text-sm">{ticket.matched_response_id}</p>

            {ticket.comment_posted_at && (
              <p className="text-sm text-gray-600 mt-2">
                Posted at: {new Date(ticket.comment_posted_at).toLocaleString()}
              </p>
            )}
          </div>
        )}

        {ticket.escalation_reason && (
          <div className="border-t pt-6 mb-6">
            <h3 className="text-sm font-semibold text-gray-500 mb-2">Escalation Reason</h3>
            <p className="text-gray-700">{ticket.escalation_reason}</p>
          </div>
        )}

        {/* Confidence Scores */}
        <div className="border-t pt-6 mb-6">
          <h3 className="text-sm font-semibold text-gray-500 mb-4">
            Classification Confidence
          </h3>
          <div className="space-y-2">
            {Object.entries(ticket.confidence_scores || {})
              .sort((a, b) => b[1].confidence - a[1].confidence)
              .slice(0, 5)
              .map(([responseId, data]) => (
                <div key={responseId} className="flex items-center gap-4">
                  <div className="w-32 text-sm font-mono">{responseId}</div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-200 rounded h-6">
                        <div
                          className={`h-full rounded ${
                            data.confidence >= 0.8
                              ? 'bg-green-500'
                              : data.confidence >= 0.5
                              ? 'bg-yellow-500'
                              : 'bg-gray-400'
                          }`}
                          style={{ width: `${data.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-semibold w-12">
                        {(data.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">{data.reasoning}</p>
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* Retract Button */}
        {canRetract() && !ticket.retracted_at && (
          <div className="border-t pt-6">
            <div className="bg-yellow-50 border border-yellow-200 rounded p-4 mb-4">
              <p className="text-sm text-yellow-800">
                You can retract this response within 5 minutes of posting.
              </p>
              <p className="text-sm font-semibold text-yellow-900 mt-1">
                {getTimeRemaining()}
              </p>
            </div>

            <button
              onClick={handleRetract}
              disabled={retractLoading}
              className="px-6 py-3 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
            >
              {retractLoading ? 'Retracting...' : 'Retract Response'}
            </button>
          </div>
        )}

        {/* Metadata */}
        <div className="border-t pt-6 mt-6">
          <div className="grid grid-cols-3 gap-4 text-sm text-gray-600">
            <div>
              <span className="font-semibold">System Version:</span> {ticket.system_version}
            </div>
            <div>
              <span className="font-semibold">Config Version:</span> {ticket.config_version}
            </div>
            <div>
              <span className="font-semibold">Processing Time:</span>{' '}
              {ticket.processing_duration_ms}ms
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
