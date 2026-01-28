/**
 * EscalationList component - displays escalated tickets with overdue status
 */
import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../services/api'
import type { Escalation } from '../types'

interface EscalationListProps {
  onTicketClick?: (ticketKey: string) => void
}

export function EscalationList({ onTicketClick }: EscalationListProps) {
  const [escalations, setEscalations] = useState<Escalation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [overdueOnly, setOverdueOnly] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const limit = 20

  const loadEscalations = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const offset = (page - 1) * limit
      const data = await apiClient.getEscalations(overdueOnly, limit, offset)

      setEscalations(data.escalations)
      setTotal(data.total)
    } catch (err) {
      const error = err as Error
      setError(error.message || 'Failed to load escalations')
    } finally {
      setLoading(false)
    }
  }, [page, overdueOnly])

  useEffect(() => {
    loadEscalations()
  }, [loadEscalations])

  const handleTicketClick = (ticketKey: string) => {
    if (onTicketClick) {
      onTicketClick(ticketKey)
    }
  }

  const handleOverdueFilterChange = () => {
    setOverdueOnly(!overdueOnly)
    setPage(1) // Reset to first page when filter changes
  }

  const getTimeElapsed = (createdAt: string): string => {
    const created = new Date(createdAt)
    const now = new Date()
    const elapsedMinutes = (now.getTime() - created.getTime()) / 1000 / 60

    if (elapsedMinutes < 60) {
      return `${Math.floor(elapsedMinutes)}m ago`
    }

    const elapsedHours = elapsedMinutes / 60
    if (elapsedHours < 24) {
      return `${Math.floor(elapsedHours)}h ago`
    }

    const elapsedDays = elapsedHours / 24
    return `${Math.floor(elapsedDays)}d ago`
  }

  const totalPages = Math.ceil(total / limit)

  if (loading) {
    return <div className="p-4">Loading escalations...</div>
  }

  if (error) {
    return <div className="p-4 text-red-600">Error: {error}</div>
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Escalated Tickets</h1>
        <div className="flex gap-4 items-center">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={overdueOnly}
              onChange={handleOverdueFilterChange}
              className="w-4 h-4"
            />
            <span className="text-sm font-semibold">
              Overdue Only (&gt;4 hours)
            </span>
          </label>
          <button
            onClick={loadEscalations}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Refresh
          </button>
        </div>
      </div>

      {escalations.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          {overdueOnly
            ? 'No overdue escalations found'
            : 'No escalations found'}
        </div>
      ) : (
        <>
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ticket
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Summary
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Reporter
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Reason
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {escalations.map((escalation) => (
                  <tr
                    key={escalation.id}
                    onClick={() => handleTicketClick(escalation.ticket_key)}
                    className={`hover:bg-gray-50 cursor-pointer ${
                      escalation.is_overdue ? 'bg-red-50' : ''
                    }`}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm font-medium text-blue-600">
                        {escalation.ticket_key}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 line-clamp-2">
                        {escalation.ticket_summary}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-600">
                        {escalation.reporter}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-700 line-clamp-2">
                        {escalation.escalation_reason}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-600">
                        {getTimeElapsed(escalation.created_at)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {escalation.is_overdue ? (
                        <span className="px-3 py-1 text-xs font-semibold rounded bg-red-100 text-red-800">
                          OVERDUE
                        </span>
                      ) : (
                        <span className="px-3 py-1 text-xs font-semibold rounded bg-yellow-100 text-yellow-800">
                          PENDING
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-between">
              <div className="text-sm text-gray-700">
                Showing {(page - 1) * limit + 1} to{' '}
                {Math.min(page * limit, total)} of {total} escalations
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                  className="px-4 py-2 border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <div className="px-4 py-2 border rounded bg-gray-50">
                  Page {page} of {totalPages}
                </div>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page === totalPages}
                  className="px-4 py-2 border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}

          {/* Top Confidence Scores Summary */}
          {escalations.length > 0 && escalations[0].confidence_scores && (
            <div className="mt-6 bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4">
                Recent Escalation Confidence Patterns
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                Showing confidence scores from the most recent escalation to help
                identify classification patterns that may need adjustment.
              </p>
              <div className="space-y-2">
                {Object.entries(escalations[0].confidence_scores)
                  .sort((a, b) => b[1].confidence - a[1].confidence)
                  .slice(0, 3)
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
                        <p className="text-xs text-gray-600 mt-1">
                          {data.reasoning}
                        </p>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
