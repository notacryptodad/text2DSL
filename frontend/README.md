# Text2DSL Frontend

A modern React-based web interface for the Text2DSL natural language to query converter.

## Features

### Core Features ✅
- **Real-time Query Processing**: WebSocket-based streaming for live updates with progress indicators
- **Multi-Provider Support**: Switch between PostgreSQL, MySQL, MongoDB, and Splunk
- **Syntax Highlighting**: Language-specific code highlighting with Prism.js (SQL, MongoDB, Splunk SPL)
- **Dark Mode**: Automatic dark mode based on system preferences with manual toggle
- **Responsive Design**: Mobile-first design that works on all screen sizes
- **Query Management**: View generated queries, confidence scores, validation status, and execution results
- **Conversation History**: Persistent conversation tracking with localStorage
- **Multi-turn Conversations**: Context-aware query refinement across multiple turns
- **Reasoning Trace**: Detailed agent traces showing Schema Expert, RAG Retrieval, Query Builder, and Validator steps
- **Settings Panel**: Configurable trace level, execution mode, max iterations, and confidence threshold
- **Copy & Download**: Copy queries to clipboard or download as files
- **Error Boundary**: Application-level error handling with detailed error display
- **Welcome Screen**: User-friendly onboarding with example queries

### Advanced Features
- **Progress Tracking**: Stage-based progress with visual indicators (schema → RAG → generation → validation → execution)
- **Agent Details**: Expandable trace sections showing token usage, latency, cost, and iterations per agent
- **Confidence Visualization**: Color-coded progress bars (green 85%+, yellow 70-85%, red <70%)
- **Validation Indicators**: Success/warning/error states with detailed feedback
- **Connection Monitoring**: Real-time connection state with automatic reconnection
- **Keyboard Shortcuts**: Enter to send, Shift+Enter for new line
- **Auto-resize Input**: Smart textarea that grows with content

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
│   │   ├── ChatMessage.jsx           # Message display with syntax highlighting
│   │   ├── ConversationHistory.jsx   # Conversation list sidebar
│   │   ├── ErrorBoundary.jsx         # Global error handler
│   │   ├── ProgressIndicator.jsx     # Stage-based progress visualization
│   │   ├── ProviderSelect.jsx        # Database provider selector
│   │   ├── QueryInput.jsx            # Auto-resize query input
│   │   ├── SettingsPanel.jsx         # Configuration panel
│   │   └── WelcomeScreen.jsx         # First-time user interface
│   ├── hooks/
│   │   └── useWebSocket.js           # WebSocket connection manager
│   ├── styles/
│   │   ├── App.css                   # Global styles and Tailwind
│   │   └── prism-custom.css          # Syntax highlighting theme
│   ├── App.jsx                       # Main application component
│   └── main.jsx                      # Application entry point
├── dist/                             # Production build output
├── index.html                        # HTML template
├── package.json                      # Dependencies and scripts
├── vite.config.js                    # Vite configuration
├── tailwind.config.js                # Tailwind CSS configuration
├── README.md                         # This file
└── README_FEATURES.md                # Detailed feature documentation
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
- All components and syntax highlighting adapt to theme

#### Provider Selection
- Click any provider in the sidebar to switch
- Available providers:
  - PostgreSQL 🐘 (SQL)
  - MySQL 🐬 (SQL)
  - MongoDB 🍃 (NoSQL)
  - Splunk 📊 (SPL)

#### Conversation History
- Access via history icon (📜) in the header
- View all past conversations
- Click to resume any conversation
- Delete conversations individually
- Badge shows total conversation count
- Automatically saves to localStorage

#### Settings Panel
- **Trace Level**: None (faster), Summary (balanced), Full (detailed)
- **Enable Execution**: Toggle query execution against the database
- **Max Iterations**: Set maximum refinement attempts (1-10)
- **Confidence Threshold**: Set minimum acceptable confidence (0-100%)
- Settings persist across sessions

#### Query Results
- **Generated Query**: Syntax-highlighted DSL query with copy/download buttons
- **Confidence Score**: Visual progress bar with color coding
  - Green (85%+): High confidence
  - Yellow (70-85%): Medium confidence
  - Red (<70%): Low confidence
- **Validation Status**: ✓ Valid, ⚠ Warning, or ✗ Invalid
- **Execution Result**: Row count and execution time (if enabled)
- **Reasoning Trace**: Expandable details showing:
  - Total time, tokens, and cost
  - Individual agent traces with metrics
  - Agent-specific details and iterations

#### Connection Status
- Green dot: Connected and ready
- Yellow dot: Connecting...
- Red dot: Disconnected or error
- Automatic reconnection on disconnect

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

- **React 18**: UI framework with hooks
- **Vite 5**: Next-generation build tool and dev server
- **Tailwind CSS 3**: Utility-first CSS framework
- **Lucide React**: Modern icon library (500+ icons)
- **Prism.js**: Syntax highlighting for SQL, MongoDB, Splunk SPL
- **WebSocket API**: Real-time bidirectional communication
- **localStorage API**: Client-side data persistence

## Contributing

1. Follow the existing code style
2. Use ESLint for code quality: `npm run lint`
3. Test in both light and dark modes
4. Ensure responsive design works on mobile

## License

Part of the Text2DSL project.
