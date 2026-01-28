/**
 * WeeklyReport component - displays weekly statistics and trends
 */
import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../services/api'
import type { WeeklyReport as WeeklyReportType } from '../types'

export function WeeklyReport() {
  const [report, setReport] = useState<WeeklyReportType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [weeksAgo, setWeeksAgo] = useState(0)

  const loadReport = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await apiClient.getWeeklyReport(weeksAgo)
      setReport(data)
    } catch (err) {
      const error = err as Error
      setError(error.message || 'Failed to load weekly report')
    } finally {
      setLoading(false)
    }
  }, [weeksAgo])

  useEffect(() => {
    loadReport()
  }, [loadReport])

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  const getWeekLabel = (): string => {
    if (weeksAgo === 0) return 'Current Week'
    if (weeksAgo === 1) return 'Last Week'
    return `${weeksAgo} Weeks Ago`
  }

  if (loading) {
    return <div className="p-4">Loading weekly report...</div>
  }

  if (error) {
    return <div className="p-4 text-red-600">Error: {error}</div>
  }

  if (!report) {
    return <div className="p-4">No report data available</div>
  }

  const stats = report.statistics

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">{getWeekLabel()}</h1>
          <p className="text-gray-600">
            {formatDate(report.week_start)} - {formatDate(report.week_end)}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setWeeksAgo(weeksAgo + 1)}
            disabled={weeksAgo >= 52}
            className="px-4 py-2 border rounded hover:bg-gray-50 disabled:opacity-50"
          >
            ← Older
          </button>
          <button
            onClick={() => setWeeksAgo(weeksAgo - 1)}
            disabled={weeksAgo === 0}
            className="px-4 py-2 border rounded hover:bg-gray-50 disabled:opacity-50"
          >
            Newer →
          </button>
          <button
            onClick={loadReport}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-sm font-semibold text-gray-500 mb-2">
            Total Tickets
          </h3>
          <p className="text-4xl font-bold">{stats.total_tickets}</p>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-sm font-semibold text-gray-500 mb-2">
            Auto-Responded
          </h3>
          <p className="text-4xl font-bold text-green-600">
            {stats.auto_responded}
          </p>
          <p className="text-sm text-gray-600 mt-2">
            {stats.automation_rate}% automation rate
          </p>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-sm font-semibold text-gray-500 mb-2">
            Escalated
          </h3>
          <p className="text-4xl font-bold text-yellow-600">
            {stats.escalated}
          </p>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-sm font-semibold text-gray-500 mb-2">
            Retracted
          </h3>
          <p className="text-4xl font-bold text-red-600">{stats.retracted}</p>
          <p className="text-sm text-gray-600 mt-2">
            {stats.false_positive_rate}% false positive rate
          </p>
        </div>
      </div>

      {/* Visual Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Action Distribution */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Action Distribution</h2>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-semibold">Auto-Responded</span>
                <span className="text-sm text-gray-600">
                  {stats.auto_responded} ({stats.automation_rate}%)
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded h-8">
                <div
                  className="bg-green-500 h-full rounded flex items-center justify-center text-white text-sm font-semibold"
                  style={{
                    width: `${
                      stats.total_tickets > 0
                        ? (stats.auto_responded / stats.total_tickets) * 100
                        : 0
                    }%`,
                  }}
                >
                  {stats.automation_rate}%
                </div>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-semibold">Escalated</span>
                <span className="text-sm text-gray-600">
                  {stats.escalated} (
                  {stats.total_tickets > 0
                    ? ((stats.escalated / stats.total_tickets) * 100).toFixed(
                        1
                      )
                    : 0}
                  %)
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded h-8">
                <div
                  className="bg-yellow-500 h-full rounded flex items-center justify-center text-white text-sm font-semibold"
                  style={{
                    width: `${
                      stats.total_tickets > 0
                        ? (stats.escalated / stats.total_tickets) * 100
                        : 0
                    }%`,
                  }}
                >
                  {stats.total_tickets > 0
                    ? ((stats.escalated / stats.total_tickets) * 100).toFixed(
                        1
                      )
                    : 0}
                  %
                </div>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-semibold">Shadow Mode</span>
                <span className="text-sm text-gray-600">
                  {stats.shadow} (
                  {stats.total_tickets > 0
                    ? ((stats.shadow / stats.total_tickets) * 100).toFixed(1)
                    : 0}
                  %)
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded h-8">
                <div
                  className="bg-gray-500 h-full rounded flex items-center justify-center text-white text-sm font-semibold"
                  style={{
                    width: `${
                      stats.total_tickets > 0
                        ? (stats.shadow / stats.total_tickets) * 100
                        : 0
                    }%`,
                  }}
                >
                  {stats.total_tickets > 0
                    ? ((stats.shadow / stats.total_tickets) * 100).toFixed(1)
                    : 0}
                  %
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quality Metrics */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Quality Metrics</h2>
          <div className="space-y-6">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-semibold">
                  Automation Success Rate
                </span>
                <span className="text-sm text-gray-600">
                  {stats.auto_responded > 0
                    ? (
                        100 -
                        (stats.retracted / stats.auto_responded) * 100
                      ).toFixed(1)
                    : 100}
                  %
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded h-8">
                <div
                  className="bg-green-500 h-full rounded flex items-center justify-center text-white text-sm font-semibold"
                  style={{
                    width: `${
                      stats.auto_responded > 0
                        ? 100 - (stats.retracted / stats.auto_responded) * 100
                        : 100
                    }%`,
                  }}
                >
                  {stats.auto_responded > 0
                    ? (
                        100 -
                        (stats.retracted / stats.auto_responded) * 100
                      ).toFixed(1)
                    : 100}
                  %
                </div>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Percentage of auto-responses not retracted
              </p>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-semibold">
                  False Positive Rate
                </span>
                <span className="text-sm text-gray-600">
                  {stats.false_positive_rate}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded h-8">
                <div
                  className={`h-full rounded flex items-center justify-center text-white text-sm font-semibold ${
                    stats.false_positive_rate > 5
                      ? 'bg-red-500'
                      : stats.false_positive_rate > 2
                      ? 'bg-yellow-500'
                      : 'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(stats.false_positive_rate * 10, 100)}%` }}
                >
                  {stats.false_positive_rate}%
                </div>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Percentage of auto-responses that were retracted
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Top Categories and Escalation Reasons */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Responses */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">
            Top Canned Responses ({report.top_responses.length})
          </h2>
          {report.top_responses.length === 0 ? (
            <p className="text-gray-500">No responses used this week</p>
          ) : (
            <div className="space-y-3">
              {report.top_responses.map((response, index) => (
                <div key={response.response_id} className="flex items-center">
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-sm font-bold text-blue-600 mr-3">
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{response.response_id}</p>
                    <p className="text-xs text-gray-500">
                      {response.count} uses (
                      {stats.auto_responded > 0
                        ? ((response.count / stats.auto_responded) * 100).toFixed(
                            1
                          )
                        : 0}
                      %)
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-lg font-bold">{response.count}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top Escalation Reasons */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">
            Top Escalation Reasons ({report.top_escalation_reasons.length})
          </h2>
          {report.top_escalation_reasons.length === 0 ? (
            <p className="text-gray-500">No escalations this week</p>
          ) : (
            <div className="space-y-3">
              {report.top_escalation_reasons.map((item, index) => (
                <div key={item.reason} className="flex items-center">
                  <div className="w-8 h-8 bg-yellow-100 rounded-full flex items-center justify-center text-sm font-bold text-yellow-600 mr-3">
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{item.reason}</p>
                    <p className="text-xs text-gray-500">
                      {item.count} escalations (
                      {stats.escalated > 0
                        ? ((item.count / stats.escalated) * 100).toFixed(1)
                        : 0}
                      %)
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-lg font-bold">{item.count}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
