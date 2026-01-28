/**
 * TicketList component - displays list of processed tickets with filters
 */
import { useState, useEffect } from 'react'
import { apiClient } from '../services/api'
import type { Ticket } from '../types'

interface TicketListProps {
  onTicketClick?: (ticketKey: string) => void
}

export function TicketList({ onTicketClick }: TicketListProps) {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionFilter, setActionFilter] = useState<string>('all')
  const [page, setPage] = useState(0)
  const [total, setTotal] = useState(0)

  const limit = 20

  useEffect(() => {
    loadTickets()
  }, [actionFilter, page])

  const loadTickets = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.getTickets(
        limit,
        page * limit,
        actionFilter === 'all' ? undefined : actionFilter
      )

      setTickets(response.tickets)
      setTotal(response.total)
    } catch (err: any) {
      setError(err.message || 'Failed to load tickets')
    } finally {
      setLoading(false)
    }
  }

  const getActionBadgeColor = (action: string) => {
    switch (action) {
      case 'auto_respond':
        return 'bg-green-100 text-green-800'
      case 'escalate':
        return 'bg-yellow-100 text-yellow-800'
      case 'shadow':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleString()
  }

  if (loading) {
    return <div className="p-4">Loading tickets...</div>
  }

  if (error) {
    return <div className="p-4 text-red-600">Error: {error}</div>
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-4">Processed Tickets</h2>

        {/* Filter buttons */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setActionFilter('all')}
            className={`px-4 py-2 rounded ${
              actionFilter === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setActionFilter('auto_respond')}
            className={`px-4 py-2 rounded ${
              actionFilter === 'auto_respond'
                ? 'bg-green-600 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            Auto-Responded
          </button>
          <button
            onClick={() => setActionFilter('escalate')}
            className={`px-4 py-2 rounded ${
              actionFilter === 'escalate'
                ? 'bg-yellow-600 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            Escalated
          </button>
          <button
            onClick={() => setActionFilter('shadow')}
            className={`px-4 py-2 rounded ${
              actionFilter === 'shadow'
                ? 'bg-gray-600 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            Shadow Mode
          </button>
        </div>
      </div>

      {/* Tickets table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Ticket
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Summary
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Action
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Response/Reason
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Processed At
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {tickets.map((ticket) => (
              <tr
                key={ticket.id}
                onClick={() => onTicketClick?.(ticket.ticket_key)}
                className="hover:bg-gray-50 cursor-pointer"
              >
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                  {ticket.ticket_key}
                </td>
                <td className="px-6 py-4 text-sm text-gray-900">
                  {ticket.ticket_summary}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 py-1 text-xs font-semibold rounded ${getActionBadgeColor(
                      ticket.action
                    )}`}
                  >
                    {ticket.action.replace('_', ' ')}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">
                  {ticket.matched_response_id || ticket.escalation_reason}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDate(ticket.created_at)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {ticket.retracted_at ? (
                    <span className="text-red-600 font-semibold">Retracted</span>
                  ) : ticket.action === 'auto_respond' ? (
                    <span className="text-green-600">Posted</span>
                  ) : (
                    <span className="text-gray-500">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="mt-4 flex justify-between items-center">
        <div className="text-sm text-gray-600">
          Showing {page * limit + 1} - {Math.min((page + 1) * limit, total)} of {total}{' '}
          tickets
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="px-4 py-2 bg-gray-200 rounded disabled:opacity-50"
          >
            Previous
          </button>
          <button
            onClick={() => setPage(page + 1)}
            disabled={(page + 1) * limit >= total}
            className="px-4 py-2 bg-gray-200 rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
