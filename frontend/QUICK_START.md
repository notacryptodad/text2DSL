# Text2DSL Frontend - Quick Start Guide

Get up and running with the Text2DSL frontend in 5 minutes.

## Prerequisites

- Node.js 18+ installed
- Backend server running on `http://localhost:8000`

## Installation

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

Open `http://localhost:3000` in your browser.

## First Query

1. Wait for the connection indicator to turn green
2. Select a provider (default: PostgreSQL)
3. Type a natural language query:
   ```
   Show me all users who signed up in the last 30 days
   ```
4. Press Enter or click Send
5. Watch the real-time progress updates
6. View the generated query and results

## Common Commands

```bash
# Development
npm run dev              # Start dev server with hot reload

# Production
npm run build           # Build for production
npm run preview         # Preview production build

# Code Quality
npm run lint            # Run ESLint

# Testing (manual)
# Open http://localhost:3000 and test features
```

## Troubleshooting

### Connection Issues

**Problem**: Connection indicator stays yellow/red

**Solution**:
```bash
# Check if backend is running
curl http://localhost:8000/health

# If not, start the backend:
cd .. && make run-dev
```

### Port Already in Use

**Problem**: Port 3000 is already in use

**Solution**:
```bash
# Use a different port
PORT=3001 npm run dev
```

### Dependencies Won't Install

**Problem**: npm install fails

**Solution**:
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

## Key Features

### 1. Provider Selection
- Click any provider in the sidebar
- Current providers: PostgreSQL, MySQL, MongoDB, Splunk

### 2. Dark Mode
- Click the moon/sun icon in the header
- Automatically saves your preference

### 3. Query History
- All queries and responses stay in the chat
- Scroll up to view previous queries

### 4. Copy Query
- Click the copy icon on any generated query
- Paste into your SQL client or application

### 5. Progress Tracking
- Real-time updates during query processing
- Progress bar shows completion percentage

## Example Queries

Try these to see the system in action:

```
# Simple SELECT
Show me all active users

# Aggregation
What are the top 10 products by revenue this month?

# Join
List all orders with customer information from the last week

# Filter with date
Find all transactions over $1000 in the past 90 days

# Complex query
Show me the average order value by customer segment,
sorted by segment size
```

## Architecture

```
Browser (Port 3000)
       ↓
   WebSocket
       ↓
Backend (Port 8000)
       ↓
   Agents → Database
```

## Configuration

### Change Backend URL

Edit `vite.config.js`:

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://your-backend:8000',
      changeOrigin: true,
    },
  },
}
```

### Environment Variables

Create `.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## Development Tips

### Hot Module Replacement
- Changes to `.jsx` files reload instantly
- Changes to `.css` files update without full reload

### React DevTools
- Install React DevTools browser extension
- Inspect component state and props

### WebSocket Debugging
- Open DevTools → Network → WS
- View all WebSocket messages

### Console Logging
- All WebSocket events are logged to console
- Check for errors or warnings

## Next Steps

- Read [README.md](./README.md) for detailed documentation
- See [INTEGRATION.md](./INTEGRATION.md) for API details
- Check [design.md](../design.md) for system architecture

## Need Help?

Common issues and solutions:

| Issue | Solution |
|-------|----------|
| White screen | Check console for errors |
| Slow loading | Check backend health endpoint |
| Styles not working | Run `npm run build` to rebuild |
| WebSocket errors | Verify backend WebSocket endpoint |

## Production Deployment

```bash
# Build optimized bundle
npm run build

# Preview production build locally
npm run preview

# Deploy dist/ folder to:
# - Vercel: vercel deploy
# - Netlify: netlify deploy
# - AWS S3: aws s3 sync dist/ s3://bucket-name
```

## Resources

- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

---

**Happy querying!**
