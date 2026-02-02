/**
 * Test fixtures for feedback and review queue tests
 * Provides mock responses for predictable E2E testing
 */

/**
 * Mock WebSocket responses for feedback tests
 * These responses enable testing feedback submission without real backend
 */
export const MOCK_FEEDBACK_RESPONSES = {
  // Simple successful query for feedback testing
  successfulQuery: {
    query: 'Show me user statistics',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'started',
          message: 'Processing query...',
          progress: 0.1,
          conversation_id: 'test-conversation-123',
        },
      },
      {
        type: 'progress',
        data: {
          stage: 'query_generation',
          message: 'Generating query...',
          progress: 0.5,
        },
      },
      {
        type: 'result',
        data: {
          stage: 'completed',
          message: 'Query processing completed',
          progress: 1.0,
          result: {
            generated_query: 'SELECT COUNT(*) as user_count FROM users',
            confidence_score: 0.92,
            validation_status: 'valid',
            validation_result: {
              status: 'valid',
              errors: [],
              warnings: [],
              suggestions: [],
            },
            execution_result: {
              success: true,
              row_count: 1,
              execution_time_ms: 45,
            },
            needs_clarification: false,
            clarification_questions: [],
            iterations: 1,
            turn_id: 'turn-456',
          },
        },
      },
    ],
  },

  // Query for negative feedback testing
  incorrectQuery: {
    query: 'Get all data from the system',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'started',
          message: 'Processing query...',
          progress: 0.1,
          conversation_id: 'test-conversation-456',
        },
      },
      {
        type: 'result',
        data: {
          stage: 'completed',
          message: 'Query processing completed',
          progress: 1.0,
          result: {
            generated_query: 'SELECT * FROM system_data',
            confidence_score: 0.75,
            validation_status: 'valid',
            validation_result: {
              status: 'valid',
              errors: [],
              warnings: ['Query may return large result set'],
              suggestions: ['Consider adding LIMIT clause'],
            },
            execution_result: {
              success: true,
              row_count: 1000,
              execution_time_ms: 250,
            },
            needs_clarification: false,
            clarification_questions: [],
            iterations: 1,
            turn_id: 'turn-789',
          },
        },
      },
    ],
  },

  // Multiple queries for category testing
  performanceQuery: {
    query: 'Test query 1',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'started',
          message: 'Processing query...',
          progress: 0.1,
          conversation_id: 'test-conversation-perf',
        },
      },
      {
        type: 'result',
        data: {
          stage: 'completed',
          message: 'Query processing completed',
          progress: 1.0,
          result: {
            generated_query: 'SELECT * FROM large_table',
            confidence_score: 0.88,
            validation_status: 'valid',
            validation_result: {
              status: 'valid',
              errors: [],
              warnings: [],
              suggestions: [],
            },
            execution_result: {
              success: true,
              row_count: 5000,
              execution_time_ms: 5000,
            },
            needs_clarification: false,
            clarification_questions: [],
            iterations: 1,
            turn_id: 'turn-perf',
          },
        },
      },
    ],
  },

  syntaxErrorQuery: {
    query: 'Test query 2',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'started',
          message: 'Processing query...',
          progress: 0.1,
          conversation_id: 'test-conversation-syntax',
        },
      },
      {
        type: 'result',
        data: {
          stage: 'completed',
          message: 'Query processing completed',
          progress: 1.0,
          result: {
            generated_query: 'SELCT * FRM users',
            confidence_score: 0.55,
            validation_status: 'invalid',
            validation_result: {
              status: 'invalid',
              errors: ['Syntax error near SELCT'],
              warnings: [],
              suggestions: ['Did you mean SELECT?'],
            },
            execution_result: {
              success: false,
              error: 'Syntax error',
            },
            needs_clarification: false,
            clarification_questions: [],
            iterations: 1,
            turn_id: 'turn-syntax',
          },
        },
      },
    ],
  },

  incorrectResultQuery: {
    query: 'Test query 3',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'started',
          message: 'Processing query...',
          progress: 0.1,
          conversation_id: 'test-conversation-incorrect',
        },
      },
      {
        type: 'result',
        data: {
          stage: 'completed',
          message: 'Query processing completed',
          progress: 1.0,
          result: {
            generated_query: 'SELECT name FROM products',
            confidence_score: 0.70,
            validation_status: 'valid',
            validation_result: {
              status: 'valid',
              errors: [],
              warnings: [],
              suggestions: [],
            },
            execution_result: {
              success: true,
              row_count: 10,
              execution_time_ms: 30,
            },
            needs_clarification: false,
            clarification_questions: [],
            iterations: 1,
            turn_id: 'turn-incorrect',
          },
        },
      },
    ],
  },

  reviewQueueQuery: {
    query: 'Test query that will get negative feedback',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'started',
          message: 'Processing query...',
          progress: 0.1,
          conversation_id: 'test-conversation-review',
        },
      },
      {
        type: 'result',
        data: {
          stage: 'completed',
          message: 'Query processing completed',
          progress: 1.0,
          result: {
            generated_query: 'SELECT * FROM data WHERE condition = true',
            confidence_score: 0.68,
            validation_status: 'valid',
            validation_result: {
              status: 'valid',
              errors: [],
              warnings: ['Low confidence query'],
              suggestions: [],
            },
            execution_result: {
              success: true,
              row_count: 42,
              execution_time_ms: 100,
            },
            needs_clarification: false,
            clarification_questions: [],
            iterations: 2,
            turn_id: 'turn-review',
          },
        },
      },
    ],
  },

  multipleSubmissionQuery: {
    query: 'Test query for multiple feedback',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'started',
          message: 'Processing query...',
          progress: 0.1,
          conversation_id: 'test-conversation-multiple',
        },
      },
      {
        type: 'result',
        data: {
          stage: 'completed',
          message: 'Query processing completed',
          progress: 1.0,
          result: {
            generated_query: 'SELECT id FROM records',
            confidence_score: 0.85,
            validation_status: 'valid',
            validation_result: {
              status: 'valid',
              errors: [],
              warnings: [],
              suggestions: [],
            },
            execution_result: {
              success: true,
              row_count: 20,
              execution_time_ms: 50,
            },
            needs_clarification: false,
            clarification_questions: [],
            iterations: 1,
            turn_id: 'turn-multiple',
          },
        },
      },
    ],
  },

  cancelFeedbackQuery: {
    query: 'Test query for cancel feedback',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'started',
          message: 'Processing query...',
          progress: 0.1,
          conversation_id: 'test-conversation-cancel',
        },
      },
      {
        type: 'result',
        data: {
          stage: 'completed',
          message: 'Query processing completed',
          progress: 1.0,
          result: {
            generated_query: 'SELECT * FROM test',
            confidence_score: 0.80,
            validation_status: 'valid',
            validation_result: {
              status: 'valid',
              errors: [],
              warnings: [],
              suggestions: [],
            },
            execution_result: {
              success: true,
              row_count: 5,
              execution_time_ms: 25,
            },
            needs_clarification: false,
            clarification_questions: [],
            iterations: 1,
            turn_id: 'turn-cancel',
          },
        },
      },
    ],
  },

  validationQuery: {
    query: 'Test query for validation',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'started',
          message: 'Processing query...',
          progress: 0.1,
          conversation_id: 'test-conversation-validation',
        },
      },
      {
        type: 'result',
        data: {
          stage: 'completed',
          message: 'Query processing completed',
          progress: 1.0,
          result: {
            generated_query: 'SELECT * FROM users LIMIT 10',
            confidence_score: 0.95,
            validation_status: 'valid',
            validation_result: {
              status: 'valid',
              errors: [],
              warnings: [],
              suggestions: [],
            },
            execution_result: {
              success: true,
              row_count: 10,
              execution_time_ms: 15,
            },
            needs_clarification: false,
            clarification_questions: [],
            iterations: 1,
            turn_id: 'turn-validation',
          },
        },
      },
    ],
  },
};

/**
 * Helper to create a mock WebSocket with feedback support
 * Call this before navigating to the page to intercept WebSocket connections
 */
export async function setupMockWebSocket(page, mockResponse) {
  await page.addInitScript((mockEvents) => {
    const OriginalWebSocket = window.WebSocket;

    window.WebSocket = function(url, protocols) {
      const ws = {
        url,
        protocols,
        readyState: 1, // OPEN
        CONNECTING: 0,
        OPEN: 1,
        CLOSING: 2,
        CLOSED: 3,
        send: function(data) {
          // Simulate async response
          setTimeout(() => {
            // Send all mock events
            mockEvents.forEach((event, index) => {
              setTimeout(() => {
                if (this.onmessage) {
                  this.onmessage({ data: JSON.stringify(event) });
                }
              }, index * 300); // 300ms between events
            });
          }, 100);
        },
        close: function() {
          this.readyState = 3; // CLOSED
          if (this.onclose) {
            this.onclose({ code: 1000, reason: 'Normal closure' });
          }
        },
        addEventListener: function(event, handler) {
          if (event === 'message') {
            this.onmessage = handler;
          } else if (event === 'open') {
            this.onopen = handler;
          } else if (event === 'close') {
            this.onclose = handler;
          } else if (event === 'error') {
            this.onerror = handler;
          }
        },
        removeEventListener: function() {},
      };

      // Trigger onopen
      setTimeout(() => {
        if (ws.onopen) {
          ws.onopen({ type: 'open' });
        }
      }, 10);

      return ws;
    };
  }, mockResponse);
}

/**
 * Mock API responses for feedback submission
 */
export async function setupMockFeedbackAPI(page) {
  await page.route('**/api/v1/query/conversations/*/feedback', async (route) => {
    // Simulate successful feedback submission
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        message: 'Feedback submitted successfully',
      }),
    });
  });
}
