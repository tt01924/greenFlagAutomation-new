/**
 * API client for Green Flag Automation backend
 */
import axios, { AxiosInstance } from 'axios'
import type { Ticket, TicketDetail, Escalation, WeeklyReport } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error.response?.data || error.message)
        return Promise.reject(error)
      }
    )
  }

  // Ticket endpoints
  async getTickets(
    limit: number = 50,
    offset: number = 0,
    action?: string
  ): Promise<{ tickets: Ticket[]; total: number; limit: number; offset: number }> {
    const params: any = { limit, offset }
    if (action) params.action = action

    const response = await this.client.get('/dashboard/tickets', { params })
    return response.data
  }

  async getTicketDetail(ticketKey: string): Promise<TicketDetail> {
    const response = await this.client.get(`/dashboard/tickets/${ticketKey}`)
    return response.data
  }

  async retractResponse(ticketKey: string, retractedBy: string): Promise<any> {
    const response = await this.client.post(
      `/dashboard/tickets/${ticketKey}/retract`,
      null,
      {
        params: { retracted_by: retractedBy },
      }
    )
    return response.data
  }

  // Escalation endpoints
  async getEscalations(
    overdueOnly: boolean = false,
    limit: number = 50,
    offset: number = 0
  ): Promise<{ escalations: Escalation[]; total: number; limit: number; offset: number }> {
    const params: any = { limit, offset }
    if (overdueOnly) params.overdue_only = true

    const response = await this.client.get('/dashboard/escalations', { params })
    return response.data
  }

  // Report endpoints
  async getWeeklyReport(weeksAgo: number = 0): Promise<WeeklyReport> {
    const response = await this.client.get('/dashboard/reports/weekly', {
      params: { weeks_ago: weeksAgo },
    })
    return response.data
  }

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get('/health')
    return response.data
  }

  async readinessCheck(): Promise<{ status: string; checks: any }> {
    const response = await this.client.get('/health/ready')
    return response.data
  }
}

// Export singleton instance
export const apiClient = new ApiClient()
