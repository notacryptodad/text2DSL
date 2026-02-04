import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as ROUTES from '../constants/routes';

export const useKeyboardShortcuts = () => {
  const navigate = useNavigate();
  const [showHelpModal, setShowHelpModal] = useState(false);
  const lastKeyRef = useRef({ key: null, timestamp: 0 });
  const SEQUENCE_TIMEOUT = 1000; // 1 second timeout for sequence detection

  useEffect(() => {
    const handleKeyDown = (event) => {
      // Skip if user is typing in an input field
      const target = event.target;
      const isInputField =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable;

      if (isInputField) {
        return;
      }

      const currentTime = Date.now();
      const key = event.key.toLowerCase();

      // Handle single key shortcuts
      if (key === '?') {
        event.preventDefault();
        setShowHelpModal(true);
        return;
      }

      if (key === 'escape') {
        setShowHelpModal(false);
        return;
      }

      // Handle 'g' key sequences
      if (key === 'g') {
        lastKeyRef.current = { key: 'g', timestamp: currentTime };
        return;
      }

      // Check if we have a valid 'g' sequence
      const lastKey = lastKeyRef.current.key;
      const timeSinceLastKey = currentTime - lastKeyRef.current.timestamp;

      if (lastKey === 'g' && timeSinceLastKey < SEQUENCE_TIMEOUT) {
        event.preventDefault();

        // Reset the sequence
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
            // Invalid sequence, do nothing
            break;
        }
      } else {
        // Reset if timeout exceeded or not part of sequence
        lastKeyRef.current = { key: null, timestamp: 0 };
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [navigate]);

  return { showHelpModal, setShowHelpModal };
};
