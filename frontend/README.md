# Green Flag Automation - Frontend Dashboard

React-based dashboard for viewing and managing automated Jira ticket responses.

## Features

- **Ticket List**: View all processed tickets with filtering by action type (auto-respond, escalate, shadow)
- **Ticket Detail**: Detailed view with confidence scores, metadata, and retract button (5-minute window)
- **Escalation List**: View escalated tickets with overdue status (>4 hours)
- **Weekly Reports**: Statistics and analytics with automation rate, false positive rate, and top categories
- **Responsive Design**: Tailwind CSS with mobile-first approach

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **React Router 6** for routing
- **Axios** for API calls
- **Tailwind CSS** for styling
- **Recharts** for data visualization (optional, can be used for future enhancements)

## Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

## Setup

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Configure API endpoint (if different from default):
   - Edit [vite.config.ts](vite.config.ts:10-13) to change the proxy target
   - Default: `http://localhost:8000`

## Development

Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Build

Build for production:
```bash
npm run build
```

The built files will be in the `dist/` directory.

## Project Structure

```text
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── TicketList.tsx   # Ticket table with filters
│   │   ├── TicketDetail.tsx # Detailed ticket view
│   │   ├── EscalationList.tsx # Escalation table
│   │   └── WeeklyReport.tsx # Statistics and reports
│   ├── pages/               # Page components
│   │   ├── Dashboard.tsx    # Main dashboard page
│   │   └── Reports.tsx      # Reports page
│   ├── services/            # API clients
│   │   └── api.ts           # Axios API client
│   ├── types/               # TypeScript types
│   │   └── index.ts         # Type definitions
│   ├── App.tsx              # Root component with routing
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles with Tailwind
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm test` - Run tests with Vitest

## API Endpoints Used

The dashboard connects to the following backend API endpoints:

- `GET /api/dashboard/tickets` - List tickets with pagination and filters
- `GET /api/dashboard/tickets/{ticket_key}` - Get ticket details
- `GET /api/dashboard/escalations` - List escalated tickets
- `POST /api/dashboard/tickets/{ticket_key}/retract` - Retract an automated response
- `GET /api/dashboard/reports/weekly` - Get weekly statistics
- `GET /health` - Backend health check

## Component Features

### TicketList
- Pagination (20 per page)
- Filter by action: all, auto_respond, escalate, shadow
- Color-coded action badges
- Click to view details

### TicketDetail
- Full ticket information with metadata
- Confidence scores visualization
- Retract button (5-minute window after posting)
- Countdown timer showing time remaining
- Link to view in Jira

### EscalationList
- Filter for overdue escalations (>4 hours)
- Time elapsed display
- Overdue status highlighting
- Confidence pattern analysis

### WeeklyReport
- Navigate between weeks
- Statistics cards (total, auto-responded, escalated, retracted)
- Action distribution visualization
- Quality metrics (automation rate, false positive rate)
- Top canned responses
- Top escalation reasons

## Environment Variables

No environment variables required. API endpoint is configured in [vite.config.ts](vite.config.ts).

## Browser Support

Modern browsers with ES2020 support:
- Chrome 80+
- Firefox 75+
- Safari 13.1+
- Edge 80+
