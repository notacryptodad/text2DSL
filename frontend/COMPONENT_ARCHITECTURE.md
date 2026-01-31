# Text2DSL Frontend - Component Architecture

## Component Hierarchy

```
main.jsx
  └── ErrorBoundary
        └── App
              ├── Header
              │     ├── ConnectionStatus
              │     ├── HistoryToggle
              │     └── DarkModeToggle
              │
              ├── Sidebar (Left)
              │     ├── ProviderSelect
              │     └── SettingsPanel
              │
              ├── MainChat (Center)
              │     ├── WelcomeScreen (when no messages)
              │     ├── ChatMessage[] (message list)
              │     ├── ProgressIndicator
              │     └── QueryInput
              │
              └── ConversationHistory (Right Sidebar, conditional)
```

## Component Relationships

### Data Flow
```
useWebSocket Hook
  ↓ (WebSocket events)
App (state management)
  ↓ (props)
Components (render UI)
  ↓ (user actions)
App (event handlers)
  ↓ (send messages)
useWebSocket Hook
```

### State Management Flow
```
localStorage
  ↓ (on mount)
App State
  ├── messages[]
  ├── conversations[]
  ├── settings{}
  ├── selectedProvider
  ├── conversationId
  ├── darkMode
  └── showHistory
  ↓ (on change)
localStorage (persist)
```

## Component Details

### Core Components

#### 1. App.jsx (Main Container)
**Responsibility**: Application state and orchestration
**State**:
- messages: Array of chat messages
- conversations: Array of saved conversations
- conversationId: Current conversation ID
- selectedProvider: Current database provider
- settings: Query processing settings
- darkMode: Theme preference
- showHistory: History sidebar visibility

**Props Passed Down**:
- To ChatMessage: message, providerId
- To ProviderSelect: providers, selected, onChange
- To QueryInput: onSend, disabled, placeholder
- To ConversationHistory: conversations, currentId, onSelect, onNew, onDelete
- To ProgressIndicator: progress
- To SettingsPanel: settings, onChange
- To WelcomeScreen: onGetStarted

**Event Handlers**:
- handleSendQuery: Send query via WebSocket
- handleWebSocketMessage: Process incoming messages
- handleNewConversation: Start new conversation
- handleSelectConversation: Switch to existing conversation
- handleDeleteConversation: Remove conversation
- toggleDarkMode: Toggle theme

#### 2. ChatMessage.jsx (Message Display)
**Responsibility**: Render individual messages with syntax highlighting
**Props**:
- message: Message object with type, content, metadata

**Message Types**:
- user: User's query
- assistant: Generated query with details
- error: Error messages
- clarification: Clarification requests
- progress: Progress updates

**Features**:
- Syntax highlighting (Prism.js)
- Copy to clipboard
- Download query
- Expandable trace sections
- Agent detail expansion

**Internal State**:
- copied: Copy button feedback
- traceExpanded: Trace section visibility
- agentDetailsExpanded: Individual agent visibility

#### 3. QueryInput.jsx (Input Field)
**Responsibility**: Capture and submit user queries
**Props**:
- onSend: Function to call on submit
- disabled: Whether input is disabled
- placeholder: Input placeholder text

**Features**:
- Auto-resize textarea
- Enter to send
- Shift+Enter for new line
- Loading state
- Character limit (5000)

**Internal State**:
- query: Current input value
- isLoading: Submission state

#### 4. ProviderSelect.jsx (Provider Selector)
**Responsibility**: Database provider selection
**Props**:
- providers: Array of available providers
- selected: Currently selected provider
- onChange: Callback when selection changes

**Features**:
- Visual cards with icons
- Selected state highlighting
- Provider metadata display

#### 5. ConversationHistory.jsx (History Sidebar)
**Responsibility**: List and manage conversations
**Props**:
- conversations: Array of saved conversations
- currentId: Current conversation ID
- onSelect: Switch to conversation
- onNew: Start new conversation
- onDelete: Remove conversation

**Features**:
- Chronological list
- Preview and timestamps
- Delete individual conversations
- Highlight current conversation
- Responsive (modal on mobile, sidebar on desktop)

#### 6. ProgressIndicator.jsx (Progress Display)
**Responsibility**: Show real-time processing progress
**Props**:
- progress: Object with stage, message, progress

**Features**:
- Animated progress bar
- Stage indicators
- Percentage display
- Stage labels

**Stages**:
1. Started
2. Schema Retrieval
3. RAG Search
4. Query Generation
5. Validation
6. Execution
7. Completed

#### 7. SettingsPanel.jsx (Configuration)
**Responsibility**: Query processing configuration
**Props**:
- settings: Settings object
- onChange: Callback when settings change

**Settings**:
- trace_level: none/summary/full
- enable_execution: boolean
- max_iterations: 1-10
- confidence_threshold: 0-1

**Features**:
- Collapsible panel
- Real-time value display
- Persistent settings

#### 8. WelcomeScreen.jsx (Onboarding)
**Responsibility**: First-time user experience
**Props**:
- onGetStarted: Callback for getting started

**Features**:
- Feature highlights
- Example queries
- Call-to-action
- Responsive layout

#### 9. ErrorBoundary.jsx (Error Handler)
**Responsibility**: Catch and display React errors
**Props**:
- children: Wrapped components

**Features**:
- Error screen display
- Error details (collapsible)
- Reload button
- Prevents app crash

### Hooks

#### useWebSocket.js
**Responsibility**: WebSocket connection management
**Parameters**:
- onMessage: Message handler
- onError: Error handler
- onOpen: Connection opened handler
- onClose: Connection closed handler

**Returns**:
- connectionState: "connected" | "connecting" | "disconnected" | "error"
- progress: Current progress state
- sendQuery: Function to send query
- connect: Function to connect
- disconnect: Function to disconnect

**Features**:
- Automatic connection on mount
- Reconnection with exponential backoff
- Event parsing and dispatch
- Connection state management
- Progress state extraction

## Data Models

### Message Object
```javascript
{
  id: number,              // Unique message ID
  type: string,            // "user" | "assistant" | "error" | "clarification" | "progress"
  content: string,         // Message content or query
  timestamp: Date,         // Message timestamp

  // Assistant message fields
  confidence?: number,      // 0-1
  validationStatus?: string,// "valid" | "invalid" | "warning"
  executionResult?: {...},  // Execution details
  trace?: {...},           // Reasoning trace
  providerId?: string,     // Provider ID
  iterations?: number,     // Iteration count

  // Error message fields
  details?: any,           // Error details

  // Clarification message fields
  content?: string[],      // Questions array

  // Progress message fields
  stage?: string,          // Progress stage
  progress?: number,       // 0-1
}
```

### Conversation Object
```javascript
{
  id: string,              // Conversation ID (UUID)
  messages: Message[],     // Array of messages
  timestamp: Date,         // Last updated
  provider: string,        // Provider name
}
```

### Settings Object
```javascript
{
  trace_level: "none" | "summary" | "full",
  enable_execution: boolean,
  max_iterations: number,    // 1-10
  confidence_threshold: number, // 0-1
}
```

### Provider Object
```javascript
{
  id: string,              // Provider ID
  name: string,            // Display name
  type: string,            // Provider type
  icon: string,            // Emoji icon
}
```

## Styling Architecture

### Tailwind CSS Utility Classes
All components use Tailwind for styling with consistent patterns:

**Colors**:
- Primary: blue (primary-500, etc.)
- Gray scale: gray-50 to gray-900
- Semantic: red (error), yellow (warning), green (success)

**Dark Mode**:
- All classes use `dark:` variants
- Smooth transitions on theme change
- Custom colors for dark mode

**Responsive**:
- Mobile-first approach
- Breakpoints: sm, md, lg, xl
- Adaptive layouts

### Custom CSS
**App.css**:
- Scrollbar styling
- Animation keyframes
- Focus states
- Code block styling

**prism-custom.css**:
- Syntax highlighting theme
- Dark/light mode support
- Token colors

## Performance Optimizations

### Code Splitting
- Automatic via Vite
- Lazy loading (potential improvement)

### State Management
- Strategic use of useState
- useEffect dependencies optimized
- No unnecessary re-renders

### Rendering
- Keys on lists
- Conditional rendering
- Memoization where needed (potential improvement)

### Bundle Size
- Tree shaking enabled
- CSS purging via Tailwind
- Minification in production
- Gzip compression

## Testing Strategy

### Unit Tests (Future)
- Component rendering
- User interactions
- State updates
- Edge cases

### Integration Tests (Future)
- WebSocket communication
- State persistence
- Multi-component flows

### E2E Tests (Future)
- Full user journeys
- Error scenarios
- Browser compatibility

## Accessibility Features

### Semantic HTML
- `<header>`, `<main>`, `<aside>`, `<button>`, etc.
- Proper heading hierarchy
- Form labels

### ARIA
- aria-label on buttons
- aria-hidden on decorative elements
- Role attributes where needed

### Keyboard Navigation
- Tab order logical
- Focus visible
- Enter/Escape handled

### Screen Readers
- Alt text on images
- Descriptive labels
- Status messages announced

## Security Considerations

### XSS Prevention
- React escapes by default
- No dangerouslySetInnerHTML
- Safe HTML in messages

### Data Privacy
- No sensitive data in localStorage
- Queries not logged in production
- CORS handled by backend

### Secure Communication
- WSS in production
- HTTPS enforced
- No mixed content

## Deployment Considerations

### Build Process
1. `npm install` - Install dependencies
2. `npm run build` - Create production build
3. Build outputs to `dist/`
4. Serve `dist/` with any static file server

### Environment Configuration
- Development: Uses Vite proxy
- Production: Relative URLs or env vars
- WebSocket URL configurable

### Browser Support
- Modern browsers (ES6+)
- Polyfills not needed
- Progressive enhancement

## Maintenance Guide

### Adding New Components
1. Create in `src/components/`
2. Export from component file
3. Import in parent component
4. Pass props down
5. Update this documentation

### Modifying State
1. Identify state location (App.jsx)
2. Update state with setState
3. Ensure persistence if needed
4. Test all affected components

### Adding Features
1. Update design document
2. Create/modify components
3. Update state management
4. Test thoroughly
5. Update documentation

### Debugging
1. Check browser console
2. Use React DevTools
3. Check WebSocket messages
4. Verify localStorage
5. Check network tab

## Common Patterns

### Props Passing
```javascript
// Parent
<Component prop={value} onAction={handler} />

// Child
function Component({ prop, onAction }) {
  return <button onClick={onAction}>{prop}</button>
}
```

### State Updates
```javascript
// Simple
const [value, setValue] = useState(initial)
setValue(newValue)

// Based on previous
setValue(prev => prev + 1)

// Object updates
setSettings(prev => ({ ...prev, key: value }))
```

### Event Handlers
```javascript
const handleAction = (param) => {
  // Update state
  setState(newValue)

  // Call callback
  if (onAction) onAction(param)
}
```

### Conditional Rendering
```javascript
{condition && <Component />}
{condition ? <A /> : <B />}
{array.map(item => <Item key={item.id} {...item} />)}
```

## Conclusion

The Text2DSL frontend architecture is clean, maintainable, and scalable. Components are well-organized, state management is straightforward, and the codebase follows React best practices. The application is production-ready and easy to extend.
