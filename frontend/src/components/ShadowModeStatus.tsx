/**
 * ShadowModeStatus component - displays banner when shadow mode is active
 */
import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../services/api'

interface ShadowModeStatusData {
  shadow_mode_active: boolean
  shadow_mode_until: string | null
  time_remaining_seconds: number | null
  time_remaining_hours: number | null
  automation_enabled: boolean
  config_version: string
}

export function ShadowModeStatus() {
  const [status, setStatus] = useState<ShadowModeStatusData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadStatus = useCallback(async () => {
    try {
      const data = await apiClient.getShadowModeStatus()
      setStatus(data)
      setError(null)
    } catch (err) {
      const error = err as Error
      setError(error.message || 'Failed to load shadow mode status')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStatus()
    // Refresh every 60 seconds
    const interval = setInterval(loadStatus, 60000)
    return () => clearInterval(interval)
  }, [loadStatus])

  const formatTimeRemaining = (): string => {
    if (!status || status.time_remaining_hours === null) return ''

    const hours = status.time_remaining_hours
    if (hours < 1) {
      const minutes = Math.floor(hours * 60)
      return `${minutes} minute${minutes !== 1 ? 's' : ''}`
    }

    if (hours < 24) {
      const wholeHours = Math.floor(hours)
      const minutes = Math.floor((hours - wholeHours) * 60)
      if (minutes > 0) {
        return `${wholeHours}h ${minutes}m`
      }
      return `${wholeHours} hour${wholeHours !== 1 ? 's' : ''}`
    }

    const days = Math.floor(hours / 24)
    const remainingHours = Math.floor(hours % 24)
    if (remainingHours > 0) {
      return `${days}d ${remainingHours}h`
    }
    return `${days} day${days !== 1 ? 's' : ''}`
  }

  if (loading) {
    return null // Don't show anything while loading
  }

  if (error) {
    return (
      <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-red-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-red-700">
              Unable to load system status: {error}
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (!status) {
    return null
  }

  // Show kill switch banner if automation is disabled
  if (!status.automation_enabled) {
    return (
      <div className="bg-red-50 border-l-4 border-red-600 p-4 mb-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-red-600"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3 flex-1">
            <h3 className="text-sm font-medium text-red-800">
              ⚠️ Automation Disabled (Kill Switch Active)
            </h3>
            <div className="mt-2 text-sm text-red-700">
              <p>
                All automation is currently disabled. All tickets will be
                escalated to the Green Flag holder until automation is
                re-enabled.
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Show shadow mode banner if active
  if (status.shadow_mode_active) {
    return (
      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-yellow-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3 flex-1">
            <h3 className="text-sm font-medium text-yellow-800">
              Shadow Mode Active
            </h3>
            <div className="mt-2 text-sm text-yellow-700">
              <p>
                The system is in shadow mode following a canned response update.
                Tickets are being classified and logged, but responses are not
                being posted to Jira.
              </p>
              <p className="mt-1 font-semibold">
                Time remaining: {formatTimeRemaining()}
              </p>
              {status.shadow_mode_until && (
                <p className="text-xs mt-1">
                  Expires at:{' '}
                  {new Date(status.shadow_mode_until).toLocaleString()}
                </p>
              )}
              <p className="text-xs mt-1">
                Config version: {status.config_version}
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // No banner needed if automation is enabled and shadow mode is not active
  return null
}
