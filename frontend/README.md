# Text2DSL Frontend

A modern React-based web interface for the Text2DSL natural language to query converter.

## Features

- **Real-time Query Processing**: WebSocket-based streaming for live updates
- **Multi-Provider Support**: Switch between SQL, NoSQL, and Splunk providers
- **Dark Mode**: Automatic dark mode based on system preferences with manual toggle
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Query Management**: View generated queries, confidence scores, and execution results
- **Progress Tracking**: Real-time progress updates during query processing
- **Copy to Clipboard**: Easy copying of generated queries
- **Error Handling**: Clear error messages and connection state indicators

## Prerequisites

- Node.js 18+ or npm/yarn
- Text2DSL backend running on `http://localhost:8000`

## Installation

1. Install dependencies:

```bash
npm install
```

## Development

Start the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

### Development Features

- Hot Module Replacement (HMR) for instant updates
- Automatic proxy to backend API (`http://localhost:8000`)
- WebSocket proxy for real-time communication
- ESLint for code quality
- Tailwind CSS for styling

## Building for Production

Build the application:

```bash
npm run build
```

The built files will be in the `dist/` directory.

Preview the production build:

```bash
npm run preview
```

## Configuration

### Backend URL

The frontend automatically connects to:
- **Development**: `http://localhost:8000` (via Vite proxy)
- **Production**: Same host as the frontend

To change the backend URL, modify `vite.config.js`:

```javascript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://your-backend-url:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://your-backend-url:8000',
        ws: true,
      },
    },
  },
})
```

### Environment Variables

Create a `.env` file in the frontend directory for custom configuration:

```env
# API Base URL (optional, defaults to proxy in dev)
VITE_API_URL=http://localhost:8000

# WebSocket URL (optional, defaults to proxy in dev)
VITE_WS_URL=ws://localhost:8000
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatMessage.jsx      # Message display component
│   │   ├── ProviderSelect.jsx   # Provider selection dropdown
│   │   └── QueryInput.jsx       # Query input field
│   ├── hooks/
│   │   └── useWebSocket.js      # WebSocket connection hook
│   ├── styles/
│   │   └── App.css              # Global styles and Tailwind imports
│   ├── App.jsx                  # Main application component
│   └── main.jsx                 # Application entry point
├── index.html                   # HTML template
├── package.json                 # Dependencies and scripts
├── vite.config.js              # Vite configuration
├── tailwind.config.js          # Tailwind CSS configuration
└── README.md                    # This file
```

## Usage

### Sending Queries

1. Select a database provider from the sidebar
2. Type your natural language query in the input box
3. Press Enter or click the Send button
4. Watch real-time progress updates
5. View the generated query, confidence score, and results

### Example Queries

- "Show me all users who signed up last month"
- "What are the top 10 orders by revenue?"
- "Find customers with more than 5 orders"
- "List products with low stock levels"

### Features Guide

#### Dark Mode
- Toggle using the moon/sun icon in the header
- Automatically detects system preference on first load
- Preference is saved in localStorage

#### Provider Selection
- Click any provider in the sidebar to switch
- Available providers:
  - PostgreSQL (SQL)
  - MySQL (SQL)
  - MongoDB (NoSQL)
  - Splunk (SPL)

#### Query Results
- **Generated Query**: The DSL query generated from your natural language input
- **Confidence Score**: How confident the system is in the query (0-100%)
- **Validation Status**: Whether the query passed syntax and semantic checks
- **Execution Result**: Row count and execution time (if enabled)
- **Processing Details**: Token usage, cost, and timing information

#### Connection Status
- Green dot: Connected and ready
- Yellow dot: Connecting...
- Red dot: Disconnected or error

## Troubleshooting

### WebSocket Connection Issues

If you see "Connecting..." or connection errors:

1. Ensure the backend is running on `http://localhost:8000`
2. Check that WebSocket endpoint is accessible: `ws://localhost:8000/ws/query`
3. Check browser console for detailed error messages
4. Verify CORS settings on the backend

### Build Issues

If you encounter build errors:

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
npm run dev
```

### Style Issues

If Tailwind styles are not applied:

```bash
# Rebuild Tailwind
npm run build
```

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Android)

## Technologies Used

- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Icon library
- **WebSocket API**: Real-time communication

## Contributing

1. Follow the existing code style
2. Use ESLint for code quality: `npm run lint`
3. Test in both light and dark modes
4. Ensure responsive design works on mobile

## License

Part of the Text2DSL project.
