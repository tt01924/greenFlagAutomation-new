/**
 * Dashboard page - main view showing tickets and escalations
 */
import { useState } from 'react'
import { TicketList } from '../components/TicketList'
import { TicketDetail } from '../components/TicketDetail'
import { EscalationList } from '../components/EscalationList'

type ViewMode = 'tickets' | 'escalations' | 'detail'

export function Dashboard() {
  const [viewMode, setViewMode] = useState<ViewMode>('tickets')
  const [selectedTicketKey, setSelectedTicketKey] = useState<string | null>(null)

  const handleTicketClick = (ticketKey: string) => {
    setSelectedTicketKey(ticketKey)
    setViewMode('detail')
  }

  const handleBackToList = () => {
    setSelectedTicketKey(null)
    setViewMode('tickets')
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Navigation Header */}
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-gray-900">
                  Green Flag Automation
                </h1>
              </div>
              <div className="ml-6 flex space-x-4">
                <button
                  onClick={() => setViewMode('tickets')}
                  className={`inline-flex items-center px-4 py-2 border-b-2 text-sm font-medium ${
                    viewMode === 'tickets' || viewMode === 'detail'
                      ? 'border-blue-500 text-gray-900'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  All Tickets
                </button>
                <button
                  onClick={() => setViewMode('escalations')}
                  className={`inline-flex items-center px-4 py-2 border-b-2 text-sm font-medium ${
                    viewMode === 'escalations'
                      ? 'border-blue-500 text-gray-900'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Escalations
                </button>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6">
        {viewMode === 'tickets' && (
          <TicketList onTicketClick={handleTicketClick} />
        )}

        {viewMode === 'detail' && selectedTicketKey && (
          <TicketDetail
            ticketKey={selectedTicketKey}
            onBack={handleBackToList}
          />
        )}

        {viewMode === 'escalations' && (
          <EscalationList onTicketClick={handleTicketClick} />
        )}
      </main>
    </div>
  )
}
