# Nvox Frontend - Transplant Journey UI

React + TypeScript + Vite + Tailwind CSS frontend application for the Transplant Journey system.

## Features

- **Authentication**: Secure signup and login with JWT tokens
- **Journey Tracking**: Visual journey progress through transplant stages
- **Dynamic Forms**: Question cards that adapt to different question types (number, boolean, text)
- **Stage Transitions**: Real-time feedback when transitioning between journey stages
- **Responsive Design**: Mobile-friendly UI with Tailwind CSS

## Tech Stack

- **React 18**: Modern React with hooks
- **TypeScript**: Type-safe development
- **Vite**: Fast build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **Docker**: Containerized deployment with Nginx

## Development

### Prerequisites

- Node.js 20+
- npm or yarn

### Local Development

1. **Install dependencies**:
   ```bash
   cd apps/nvox-fe
   npm install
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` to point to your API:
   ```
   VITE_API_URL=http://localhost:8000
   ```

3. **Start dev server**:
   ```bash
   npm run dev
   ```

   The app will be available at http://localhost:3000

4. **Build for production**:
   ```bash
   npm run build
   ```

## Running with Docker

### Using Docker Compose (Recommended)

Start the entire stack (postgres, redis, API, frontend):

```bash
# From repository root
docker compose -f apps/nvox-api/docker-compose.yaml --profile api up -d
```

This will start:
- PostgreSQL on port 5432
- Redis on port 6379
- API on port 8000
- Frontend on port 3000

Access the frontend at: **http://localhost:3000**

### Building Manually

Build the Docker image:

```bash
# From repository root
docker build -t nvox-frontend -f apps/nvox-fe/Dockerfile .
```

Run the container:

```bash
docker run -p 3000:80 nvox-frontend
```

## Project Structure

```
apps/nvox-fe/
├── src/
│   ├── components/          # React components
│   │   ├── AuthForm.tsx     # Login/Signup form
│   │   ├── JourneyProgress.tsx  # Stage progress display
│   │   ├── JourneyView.tsx      # Main journey interface
│   │   └── QuestionCard.tsx     # Question answer form
│   ├── services/            # API client
│   │   └── api.ts           # HTTP client with auth
│   ├── types/               # TypeScript types
│   │   └── api.ts           # API response types
│   ├── App.tsx              # Root component
│   ├── main.tsx             # App entry point
│   └── index.css            # Tailwind styles
├── Dockerfile               # Multi-stage Docker build
├── nginx.conf               # Nginx configuration
├── vite.config.ts           # Vite configuration
├── tailwind.config.js       # Tailwind configuration
└── tsconfig.json            # TypeScript configuration
```

## Components

### AuthForm
Combined login and signup form with toggle between modes.
- Validates email and password
- Stores JWT token in localStorage
- Automatic login after signup

### JourneyView
Main authenticated view displaying:
- Current stage and visit number
- Available questions for the stage
- Stage transition notifications
- Journey timeline information

### JourneyProgress
Visual indicator showing:
- Current stage name
- Stage ID
- Visit number

### QuestionCard
Dynamic form for answering questions:
- **Number type**: Input with min/max constraints
- **Boolean type**: Yes/No buttons
- **Text type**: Text input field
- Real-time validation
- Error handling

## API Integration

The frontend communicates with the backend API at `/v1/*` endpoints:

- `POST /v1/signup` - Create account and initialize journey
- `POST /v1/login` - Authenticate and get JWT token
- `GET /v1/journey/current` - Get current journey state and questions
- `POST /v1/journey/answer` - Submit answer and trigger stage transitions
- `DELETE /v1/user` - Anonymize user data

Authentication uses JWT Bearer tokens stored in localStorage.

## User Flow

1. **Signup/Login**: User creates account or logs in
2. **Journey Start**: Automatically starts at REFERRAL stage
3. **Answer Questions**: User answers questions for current stage
4. **Stage Transitions**: System automatically transitions based on routing rules
   - Example: Karnofsky score ≥ 40 → WORKUP stage
   - Example: Karnofsky score < 40 → EXIT stage
5. **Journey Progress**: User sees real-time updates and new questions

## Testing the UI

### Manual Testing

1. **Start services**:
   ```bash
   docker compose -f apps/nvox-api/docker-compose.yaml --profile api up -d
   ```

2. **Open browser**: http://localhost:3000

3. **Test flow**:
   - Sign up with email/password
   - See REFERRAL stage
   - Answer boolean question (ref_eligible) - no transition
   - Answer Karnofsky score = 80 - transitions to WORKUP
   - See WORKUP stage with new questions

### Using Postman

You can also test the API independently with the provided Postman collection:
```bash
apps/nvox-api/Nvox_Journey_API.postman_collection.json
```

See `apps/nvox-api/POSTMAN_GUIDE.md` for details.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |

## Troubleshooting

### Frontend can't connect to API
- Ensure API is running on port 8000
- Check `VITE_API_URL` in `.env`
- Check browser console for CORS errors
- Verify network connectivity between containers

### Login fails
- Check API logs: `docker logs nvox-api`
- Verify database is running: `docker ps`
- Check JWT token in browser DevTools → Application → Local Storage

### Build fails
- Clear node_modules: `rm -rf node_modules && npm install`
- Check Node version: `node --version` (should be 20+)
- Check for TypeScript errors: `npm run build`

### Docker build fails
- Ensure you're running from repository root
- Check Docker context in Dockerfile
- Verify Dockerfile path: `apps/nvox-fe/Dockerfile`

