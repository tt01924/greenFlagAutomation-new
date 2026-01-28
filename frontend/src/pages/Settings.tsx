/**
 * Settings page - system configuration and admin controls
 */
import { Link } from 'react-router-dom'
import { KillSwitch } from '../components/KillSwitch'
import { ShadowModeStatus } from '../components/ShadowModeStatus'

export function Settings() {
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
                <Link
                  to="/"
                  className="inline-flex items-center px-4 py-2 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                >
                  Dashboard
                </Link>
                <Link
                  to="/reports"
                  className="inline-flex items-center px-4 py-2 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                >
                  Reports
                </Link>
                <Link
                  to="/settings"
                  className="inline-flex items-center px-4 py-2 border-b-2 border-blue-500 text-sm font-medium text-gray-900"
                >
                  Settings
                </Link>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 px-4">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Settings</h1>

        {/* System Status Banner */}
        <ShadowModeStatus />

        {/* Kill Switch Section */}
        <div className="mb-8">
          <KillSwitch />
        </div>

        {/* System Information */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            System Information
          </h2>
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="font-medium text-gray-500">Service</dt>
              <dd className="mt-1 text-gray-900">Green Flag Automation</dd>
            </div>
            <div>
              <dt className="font-medium text-gray-500">Version</dt>
              <dd className="mt-1 text-gray-900">1.0.0</dd>
            </div>
            <div>
              <dt className="font-medium text-gray-500">Environment</dt>
              <dd className="mt-1 text-gray-900">Development</dd>
            </div>
            <div>
              <dt className="font-medium text-gray-500">API Endpoint</dt>
              <dd className="mt-1 text-gray-900 font-mono text-xs">
                /api
              </dd>
            </div>
          </dl>
        </div>

        {/* Documentation Links */}
        <div className="mt-8 bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Documentation
          </h2>
          <div className="space-y-2">
            <a
              href="/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="block text-blue-600 hover:text-blue-800 text-sm"
            >
              → API Documentation (Swagger UI)
            </a>
            <a
              href="https://github.com/Skyscanner/green-flag-automation"
              target="_blank"
              rel="noopener noreferrer"
              className="block text-blue-600 hover:text-blue-800 text-sm"
            >
              → GitHub Repository
            </a>
            <a
              href="https://skyscanner.atlassian.net"
              target="_blank"
              rel="noopener noreferrer"
              className="block text-blue-600 hover:text-blue-800 text-sm"
            >
              → Jira Project
            </a>
            <a
              href="https://skyscanner.slack.com/channels/cassini-squad"
              target="_blank"
              rel="noopener noreferrer"
              className="block text-blue-600 hover:text-blue-800 text-sm"
            >
              → Slack Channel (#cassini-squad)
            </a>
          </div>
        </div>
      </main>
    </div>
  )
}
