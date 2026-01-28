/**
 * Reports page - displays weekly statistics and analytics
 */
import { WeeklyReport } from '../components/WeeklyReport'
import { ShadowModeStatus } from '../components/ShadowModeStatus'

export function Reports() {
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
                <a
                  href="/"
                  className="inline-flex items-center px-4 py-2 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                >
                  All Tickets
                </a>
                <a
                  href="/reports"
                  className="inline-flex items-center px-4 py-2 border-b-2 border-blue-500 text-sm font-medium text-gray-900"
                >
                  Reports
                </a>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 px-4">
        {/* Shadow Mode / Kill Switch Banner */}
        <ShadowModeStatus />

        <WeeklyReport />
      </main>
    </div>
  )
}
