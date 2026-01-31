# Frontend Testing Checklist

This document provides a comprehensive testing checklist for the Text2DSL frontend application.

## Build & Development

- [x] **npm install** runs without errors
- [x] **npm run dev** starts development server successfully
- [x] **npm run build** creates production build without errors
- [x] **npm run lint** passes with no warnings or errors
- [x] **npm run preview** serves production build correctly
- [x] Hot Module Replacement (HMR) works in development
- [x] Build outputs to `dist/` directory
- [x] Source maps generated for debugging

## Core Functionality

### Query Processing
- [ ] User can type natural language query in input field
- [ ] Textarea auto-resizes as content grows
- [ ] Enter key sends query
- [ ] Shift+Enter creates new line
- [ ] Query is sent via WebSocket
- [ ] Loading indicator appears during processing
- [ ] Input is disabled during processing
- [ ] User message appears in chat
- [ ] Assistant response appears with generated query
- [ ] Query is properly formatted and syntax-highlighted
- [ ] Copy button works and shows checkmark feedback
- [ ] Download button saves query as file

### Provider Selection
- [ ] Provider sidebar displays all providers
- [ ] Can select PostgreSQL provider
- [ ] Can select MySQL provider
- [ ] Can select MongoDB provider
- [ ] Can select Splunk provider
- [ ] Selected provider is highlighted
- [ ] Provider icon displays correctly
- [ ] Provider type label is shown

### WebSocket Connection
- [ ] Connection establishes on page load
- [ ] Connection status indicator shows "connected"
- [ ] Green dot appears when connected
- [ ] Yellow dot appears when connecting
- [ ] Red dot appears when disconnected
- [ ] Automatic reconnection works after disconnect
- [ ] Reconnection attempts shown in console
- [ ] Max reconnection attempts respected
- [ ] Error messages display on connection failure

### Progress Indicator
- [ ] Progress bar appears during query processing
- [ ] Stage indicators show current step
- [ ] Progress percentage updates in real-time
- [ ] Stage labels are correct (schema → RAG → generation → validation → execution)
- [ ] Progress bar animates smoothly
- [ ] Progress bar disappears on completion
- [ ] Loading spinner animates

### Query Results Display
- [ ] Generated query displays with syntax highlighting
- [ ] Confidence score shows as percentage
- [ ] Confidence bar color matches score (green/yellow/red)
- [ ] Validation status icon displays (✓/⚠/✗)
- [ ] Validation message shows
- [ ] Execution results display (if enabled)
- [ ] Row count shown
- [ ] Execution time shown
- [ ] Error messages display for failed queries

### Reasoning Trace
- [ ] Trace section is collapsible
- [ ] Click to expand/collapse works
- [ ] Summary stats display (time, tokens, cost)
- [ ] Schema Expert agent trace shows
- [ ] RAG Retrieval agent trace shows
- [ ] Query Builder agent trace shows
- [ ] Validator agent trace shows
- [ ] Agent details expandable individually
- [ ] Token counts display correctly
- [ ] Latency metrics display correctly
- [ ] Cost calculation displays
- [ ] Agent-specific details show

### Conversation History
- [ ] History icon in header shows conversation count
- [ ] Click history icon opens sidebar
- [ ] Conversations list displays
- [ ] Each conversation shows preview
- [ ] Timestamps display correctly
- [ ] Click conversation to resume
- [ ] Current conversation is highlighted
- [ ] Delete button removes conversation
- [ ] New conversation button clears chat
- [ ] History persists after page reload
- [ ] History sidebar closes with X button
- [ ] Mobile: History shows as modal overlay
- [ ] Desktop: History shows as slide-in sidebar

### Settings Panel
- [ ] Settings panel is collapsible
- [ ] Trace level dropdown works
- [ ] Can select "None" trace level
- [ ] Can select "Summary" trace level
- [ ] Can select "Full" trace level
- [ ] Enable execution toggle works
- [ ] Max iterations slider works (1-10)
- [ ] Current value displays for slider
- [ ] Confidence threshold slider works (0-100%)
- [ ] Threshold percentage displays
- [ ] Settings persist after page reload
- [ ] Settings applied to new queries

### Dark Mode
- [ ] System preference detected on first load
- [ ] Toggle button switches theme
- [ ] Dark mode persists after page reload
- [ ] All components adapt to dark mode
- [ ] Syntax highlighting adapts to dark mode
- [ ] Icons change appropriately (sun/moon)
- [ ] Smooth transition between themes
- [ ] No flashing during theme change

### Welcome Screen
- [ ] Displays when no messages present
- [ ] Shows app title and description
- [ ] Feature cards display
- [ ] Example queries display
- [ ] Click example query starts conversation
- [ ] Get Started button works
- [ ] Icons display correctly
- [ ] Responsive layout works

### Error Handling
- [ ] Application-level errors caught by ErrorBoundary
- [ ] Error screen displays with error details
- [ ] Reload button works on error screen
- [ ] WebSocket errors display in chat
- [ ] Connection errors show user-friendly message
- [ ] Validation errors display clearly
- [ ] Error details are collapsible
- [ ] Errors don't crash the application

## User Interface

### Layout & Responsive Design
- [ ] Desktop layout (3-column: sidebar, chat, settings)
- [ ] Tablet layout adapts properly
- [ ] Mobile layout stacks correctly
- [ ] Header is always visible
- [ ] Chat area scrolls independently
- [ ] Sidebar is fixed
- [ ] Footer/input area is sticky
- [ ] No horizontal scroll on mobile
- [ ] Touch targets are adequate (44x44px minimum)

### Visual Design
- [ ] Primary color (blue) used consistently
- [ ] Color contrast meets WCAG AA standards
- [ ] Icons are clear and recognizable
- [ ] Typography is readable
- [ ] Spacing is consistent
- [ ] Borders and shadows appropriate
- [ ] Hover states work on interactive elements
- [ ] Focus states visible for keyboard navigation
- [ ] Loading states clear and animated
- [ ] Disabled states visually distinct

### Accessibility
- [ ] All buttons have aria-labels
- [ ] Form inputs have labels
- [ ] Images have alt text (or aria-hidden)
- [ ] Focus visible on keyboard navigation
- [ ] Tab order is logical
- [ ] Screen reader friendly structure
- [ ] Color is not the only indicator
- [ ] Semantic HTML used (header, main, aside, etc.)
- [ ] ARIA roles used appropriately

## Performance

### Loading & Rendering
- [ ] Initial page load < 3 seconds
- [ ] Code splitting implemented
- [ ] Lazy loading for components (if applicable)
- [ ] Images optimized
- [ ] Fonts load efficiently
- [ ] No layout shifts during load
- [ ] Smooth animations (60fps)
- [ ] No lag when typing in input

### Data & State
- [ ] Conversations persist in localStorage
- [ ] Settings persist in localStorage
- [ ] Dark mode preference persists
- [ ] No memory leaks with WebSocket
- [ ] Old conversations can be cleared
- [ ] Large conversation history doesn't slow down app
- [ ] State updates don't cause unnecessary re-renders

## Browser Compatibility

### Desktop Browsers
- [ ] Chrome (latest) works
- [ ] Firefox (latest) works
- [ ] Safari (latest) works
- [ ] Edge (latest) works
- [ ] Chrome (1 version back) works

### Mobile Browsers
- [ ] iOS Safari works
- [ ] Chrome on Android works
- [ ] Firefox on Android works
- [ ] Samsung Internet works

### Features by Browser
- [ ] WebSocket support confirmed
- [ ] localStorage support confirmed
- [ ] Clipboard API works (or fallback)
- [ ] CSS Grid/Flexbox works
- [ ] Dark mode media query works
- [ ] Smooth scrolling works

## Edge Cases

### Input Validation
- [ ] Empty query doesn't submit
- [ ] Very long query (5000 chars) handled
- [ ] Special characters in query handled
- [ ] Line breaks in query preserved
- [ ] Rapid query submissions handled

### WebSocket Edge Cases
- [ ] Handles disconnect during query processing
- [ ] Handles reconnect mid-stream
- [ ] Handles malformed messages gracefully
- [ ] Handles very large messages
- [ ] Handles rapid message succession

### State Edge Cases
- [ ] localStorage full handled gracefully
- [ ] localStorage disabled handled
- [ ] Cookies disabled handled
- [ ] JavaScript errors don't crash app
- [ ] Network errors handled
- [ ] CORS errors handled

### UI Edge Cases
- [ ] Very long query in chat wraps properly
- [ ] Very long generated query displays correctly
- [ ] Many conversations (100+) display performance OK
- [ ] Rapid theme switching works
- [ ] Window resize handled smoothly
- [ ] Browser zoom (50%-200%) works

## Integration

### Backend Communication
- [ ] WebSocket connects to correct URL in dev
- [ ] WebSocket connects to correct URL in prod
- [ ] Proxy configuration works in dev
- [ ] CORS handled properly
- [ ] Request format matches backend expectation
- [ ] Response format parsed correctly
- [ ] Event types handled correctly
- [ ] Conversation ID tracked properly

### Third-Party Libraries
- [ ] Prism.js highlights SQL correctly
- [ ] Prism.js highlights MongoDB queries correctly
- [ ] Prism.js highlights Splunk SPL correctly
- [ ] Lucide icons render correctly
- [ ] Tailwind classes applied correctly
- [ ] No console errors from libraries

## Security

### Data Handling
- [ ] No sensitive data in localStorage
- [ ] No API keys exposed in client code
- [ ] User queries not logged to console in production
- [ ] No XSS vulnerabilities in message display
- [ ] Safe handling of HTML in messages
- [ ] Safe handling of code in queries

### Network Security
- [ ] HTTPS used in production (if applicable)
- [ ] WSS (secure WebSocket) used in production (if applicable)
- [ ] No mixed content warnings
- [ ] CORS properly configured

## Documentation

- [x] README.md is comprehensive
- [x] README_FEATURES.md documents all features
- [x] Code comments are clear
- [x] Component props documented (JSDoc or comments)
- [x] Complex logic explained with comments
- [x] API integration documented
- [x] Environment variables documented

## Known Issues

Document any known issues or limitations:

1. Conversation history stored in localStorage (5-10MB limit)
2. No server-side conversation persistence
3. Syntax highlighting limited to supported languages
4. No offline support
5. Single user only (no authentication)

## Test Automation (Future)

Future testing improvements:
- [ ] Unit tests for components (React Testing Library)
- [ ] Integration tests for flows (Cypress/Playwright)
- [ ] E2E tests for critical paths
- [ ] Visual regression tests (Percy/Chromatic)
- [ ] Performance tests (Lighthouse CI)
- [ ] Accessibility tests (axe-core)

## Sign-off

Tested by: _________________
Date: _________________
Environment: _________________
Notes: _________________
