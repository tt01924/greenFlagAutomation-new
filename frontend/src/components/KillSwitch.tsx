/**
 * KillSwitch component - toggle automation on/off
 */
import { useState, useEffect } from 'react'
import { apiClient } from '../services/api'

export function KillSwitch() {
  const [automationEnabled, setAutomationEnabled] = useState<boolean>(true)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  useEffect(() => {
    loadStatus()
  }, [])

  const loadStatus = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await apiClient.getKillSwitchStatus()
      setAutomationEnabled(data.automation_enabled)
    } catch (err: any) {
      setError(err.message || 'Failed to load kill switch status')
    } finally {
      setLoading(false)
    }
  }

  const handleToggle = async () => {
    const action = automationEnabled ? 'disable' : 'enable'
    const confirmMessage = automationEnabled
      ? 'Are you sure you want to DISABLE automation?\n\nAll tickets will be escalated to the Green Flag holder until automation is re-enabled.'
      : 'Are you sure you want to ENABLE automation?\n\nThe system will resume automatic ticket processing.'

    if (!window.confirm(confirmMessage)) {
      return
    }

    setActionLoading(true)
    setError(null)
    setSuccessMessage(null)

    try {
      const endpoint = automationEnabled ? 'disable' : 'enable'
      const response = await fetch(`/api/admin/kill-switch/${endpoint}`, {
        method: 'POST',
      })

      if (!response.ok) {
        throw new Error(`Failed to ${action} automation`)
      }

      const data = await response.json()
      setAutomationEnabled(data.automation_enabled)
      setSuccessMessage(
        automationEnabled
          ? '⚠️ Automation disabled - all tickets will now be escalated'
          : '✅ Automation enabled - normal processing resumed'
      )

      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(null), 5000)
    } catch (err: any) {
      setError(err.message || `Failed to ${action} automation`)
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white shadow rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-10 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            Kill Switch (Emergency Stop)
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Immediately disable all automation. All tickets will be escalated to
            the Green Flag holder.
          </p>
        </div>
        <div className="flex items-center">
          <span
            className={`mr-3 text-sm font-medium ${
              automationEnabled ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {automationEnabled ? 'Enabled' : 'Disabled'}
          </span>
          <button
            onClick={handleToggle}
            disabled={actionLoading}
            className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
              automationEnabled
                ? 'bg-green-600 focus:ring-green-500'
                : 'bg-red-600 focus:ring-red-500'
            } ${actionLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <span
              className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                automationEnabled ? 'translate-x-7' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Status Banner */}
      {!automationEnabled && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded">
          <div className="flex">
            <svg
              className="h-5 w-5 text-red-600 mr-2"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z"
                clipRule="evenodd"
              />
            </svg>
            <div>
              <h3 className="text-sm font-medium text-red-800">
                Automation Currently Disabled
              </h3>
              <p className="text-sm text-red-700 mt-1">
                All incoming tickets with the "Green-Flag" label will be
                escalated to the Green Flag holder via Slack. No automated
                responses will be posted to Jira.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Success Message */}
      {successMessage && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded">
          <p className="text-sm text-blue-700">{successMessage}</p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded">
          <p className="text-sm text-red-700">Error: {error}</p>
        </div>
      )}

      {/* Usage Info */}
      <div className="border-t pt-4 mt-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          When to use the kill switch:
        </h3>
        <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
          <li>High false positive rate detected (too many incorrect responses)</li>
          <li>Critical bug discovered in the classification logic</li>
          <li>Emergency situation requiring human review of all tickets</li>
          <li>System maintenance or testing</li>
        </ul>
        <p className="text-xs text-gray-500 mt-3">
          <strong>Note:</strong> This only affects new tickets. Previously
          processed tickets are not affected.
        </p>
      </div>

      {/* Refresh Button */}
      <div className="border-t pt-4 mt-4">
        <button
          onClick={loadStatus}
          disabled={loading || actionLoading}
          className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
        >
          Refresh Status
        </button>
      </div>
    </div>
  )
}
