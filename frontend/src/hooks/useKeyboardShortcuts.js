import { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import * as ROUTES from '../constants/routes';

/**
 * Enhanced keyboard shortcuts hook with support for:
 * - Navigation shortcuts (g + key sequences)
 * - Chat shortcuts (Cmd/Ctrl + K, H, Enter, L, ?, Escape, Up Arrow)
 * 
 * @param {Object} handlers - Optional handlers for chat-specific shortcuts
 * @param {Function} handlers.onProviderSwitch - Cmd/Ctrl + K handler
 * @param {Function} handlers.onToggleHistory - Cmd/Ctrl + H handler
 * @param {Function} handlers.onSendQuery - Cmd/Ctrl + Enter handler
 * @param {Function} handlers.onCancelQuery - Escape handler (when query running)
 * @param {Function} handlers.onClearChat - Cmd/Ctrl + L handler
 * @param {Function} handlers.onRecallLastQuery - Up Arrow handler (in empty input)
 * @param {boolean} handlers.isQueryRunning - Whether a query is currently running
 */
export const useKeyboardShortcuts = (handlers = {}) => {
  const navigate = useNavigate();
  const [showHelpModal, setShowHelpModal] = useState(false);
  const lastKeyRef = useRef({ key: null, timestamp: 0 });
  const SEQUENCE_TIMEOUT = 1000; // 1 second timeout for sequence detection

  const {
    onProviderSwitch,
    onToggleHistory,
    onSendQuery,
    onCancelQuery,
    onClearChat,
    onRecallLastQuery,
    isQueryRunning = false,
  } = handlers;

  const handleKeyDown = useCallback((event) => {
    const target = event.target;
    const isInputField =
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable;

    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const modKey = isMac ? event.metaKey : event.ctrlKey;
    const key = event.key.toLowerCase();
    const currentTime = Date.now();

    // === MODIFIER KEY SHORTCUTS (work everywhere) ===
    
    // Cmd/Ctrl + K: Quick provider switch
    if (modKey && key === 'k') {
      event.preventDefault();
      onProviderSwitch?.();
      return;
    }

    // Cmd/Ctrl + H: Toggle history sidebar
    if (modKey && key === 'h') {
      event.preventDefault();
      onToggleHistory?.();
      return;
    }

    // Cmd/Ctrl + Enter: Send query (works in input fields)
    if (modKey && event.key === 'Enter') {
      event.preventDefault();
      onSendQuery?.();
      return;
    }

    // Cmd/Ctrl + L: Clear chat
    if (modKey && key === 'l') {
      event.preventDefault();
      onClearChat?.();
      return;
    }

    // Cmd/Ctrl + / or Cmd/Ctrl + ?: Show shortcuts help
    if (modKey && (key === '/' || key === '?')) {
      event.preventDefault();
      setShowHelpModal(true);
      return;
    }

    // === ESCAPE KEY ===
    if (key === 'escape') {
      // First priority: close help modal if open
      if (showHelpModal) {
        setShowHelpModal(false);
        return;
      }
      // Second priority: cancel running query
      if (isQueryRunning) {
        event.preventDefault();
        onCancelQuery?.();
        return;
      }
      return;
    }

    // === UP ARROW: Recall last query (only in empty input) ===
    if (event.key === 'ArrowUp' && isInputField) {
      const inputValue = target.value || target.innerText || '';
      if (inputValue.trim() === '') {
        event.preventDefault();
        onRecallLastQuery?.();
        return;
      }
    }

    // === NON-INPUT FIELD SHORTCUTS ===
    if (isInputField) {
      return;
    }

    // Handle single key shortcuts (non-input only)
    if (key === '?') {
      event.preventDefault();
      setShowHelpModal(true);
      return;
    }

    // Handle 'g' key sequences for navigation
    if (key === 'g') {
      lastKeyRef.current = { key: 'g', timestamp: currentTime };
      return;
    }

    // Check if we have a valid 'g' sequence
    const lastKey = lastKeyRef.current.key;
    const timeSinceLastKey = currentTime - lastKeyRef.current.timestamp;

    if (lastKey === 'g' && timeSinceLastKey < SEQUENCE_TIMEOUT) {
      event.preventDefault();
      lastKeyRef.current = { key: null, timestamp: 0 };

      // Navigate based on second key
      switch (key) {
        case 'c':
          navigate(ROUTES.APP);
          break;
        case 'r':
          navigate(ROUTES.REVIEW);
          break;
        case 's':
          navigate(ROUTES.SCHEMA_ANNOTATION);
          break;
        case 'a':
          navigate(ROUTES.ADMIN);
          break;
        case 'w':
          navigate(ROUTES.ADMIN_WORKSPACES);
          break;
        default:
          break;
      }
    } else {
      lastKeyRef.current = { key: null, timestamp: 0 };
    }
  }, [
    navigate,
    onProviderSwitch,
    onToggleHistory,
    onSendQuery,
    onCancelQuery,
    onClearChat,
    onRecallLastQuery,
    isQueryRunning,
    showHelpModal,
  ]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);

  return { showHelpModal, setShowHelpModal };
};

export default useKeyboardShortcuts;
