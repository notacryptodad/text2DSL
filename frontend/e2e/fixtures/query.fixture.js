/**
 * Test fixtures for query generation tests
 * Provides mock AI responses for predictable E2E testing
 */

/**
 * Mock WebSocket event sequences for different query scenarios
 */
export const MOCK_QUERY_RESPONSES = {
  // Simple query with successful result
  simpleQuery: {
    query: 'Get all products with price greater than 100',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'schema_retrieval',
          message: 'Retrieving database schema...',
          progress: 0.2,
        },
      },
      {
        type: 'progress',
        data: {
          stage: 'rag_search',
          message: 'Searching for similar examples...',
          progress: 0.4,
        },
      },
      {
        type: 'progress',
        data: {
          stage: 'query_generation',
          message: 'Generating query...',
          progress: 0.6,
        },
      },
      {
        type: 'progress',
        data: {
          stage: 'validation',
          message: 'Validating generated query...',
          progress: 0.8,
        },
      },
      {
        type: 'progress',
        data: {
          stage: 'execution',
          message: 'Executing query...',
          progress: 0.9,
        },
      },
      {
        type: 'result',
        data: {
          stage: 'completed',
          message: 'Query processing completed',
          progress: 1.0,
          result: {
            generated_query: 'SELECT * FROM products WHERE price > 100',
            confidence_score: 0.95,
            validation_status: 'valid',
            validation_result: {
              status: 'valid',
              errors: [],
              warnings: [],
              suggestions: ['Consider adding LIMIT clause for large result sets'],
            },
            execution_result: {
              success: true,
              row_count: 45,
              execution_time_ms: 125,
            },
            needs_clarification: false,
            clarification_questions: [],
            iterations: 1,
          },
        },
      },
    ],
  },

  // Query requiring clarification
  clarificationQuery: {
    query: 'Show me sales data',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'schema_retrieval',
          message: 'Retrieving database schema...',
          progress: 0.3,
        },
      },
      {
        type: 'clarification',
        data: {
          message: 'I need clarification to proceed',
          questions: [
            'Which time period do you want to see? (e.g., last week, last month, this year)',
            'Do you want total sales or individual transaction details?',
          ],
        },
      },
    ],
  },

  // Query with low confidence
  lowConfidenceQuery: {
    query: 'Complex aggregation with multiple joins',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'schema_retrieval',
          message: 'Retrieving database schema...',
          progress: 0.2,
        },
      },
      {
        type: 'progress',
        data: {
          stage: 'query_generation',
          message: 'Generating query...',
          progress: 0.6,
        },
      },
      {
        type: 'result',
        data: {
          stage: 'completed',
          message: 'Query processing completed',
          progress: 1.0,
          result: {
            generated_query:
              'SELECT t1.*, t2.* FROM table1 t1 JOIN table2 t2 ON t1.id = t2.foreign_id',
            confidence_score: 0.65,
            validation_status: 'valid',
            validation_result: {
              status: 'valid',
              errors: [],
              warnings: ['Query may return large result set'],
              suggestions: ['Consider adding WHERE clause to filter results'],
            },
            needs_clarification: false,
            clarification_questions: [],
            iterations: 2,
          },
        },
      },
    ],
  },

  // Query with validation error
  validationErrorQuery: {
    query: 'Invalid query that fails validation',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'schema_retrieval',
          message: 'Retrieving database schema...',
          progress: 0.2,
        },
      },
      {
        type: 'progress',
        data: {
          stage: 'query_generation',
          message: 'Generating query...',
          progress: 0.6,
        },
      },
      {
        type: 'progress',
        data: {
          stage: 'validation',
          message: 'Validating generated query...',
          progress: 0.8,
        },
      },
      {
        type: 'result',
        data: {
          stage: 'completed',
          message: 'Query processing completed with validation errors',
          progress: 1.0,
          result: {
            generated_query: 'SELECT * FROM nonexistent_table',
            confidence_score: 0.45,
            validation_status: 'invalid',
            validation_result: {
              status: 'invalid',
              errors: ['Table nonexistent_table does not exist'],
              warnings: [],
              suggestions: ['Check table name spelling', 'Review available tables in schema'],
            },
            needs_clarification: false,
            clarification_questions: [],
            iterations: 1,
          },
        },
      },
    ],
  },

  // Processing error
  processingError: {
    query: 'Query that causes processing error',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'schema_retrieval',
          message: 'Retrieving database schema...',
          progress: 0.2,
        },
      },
      {
        type: 'error',
        data: {
          error: 'processing_error',
          message: 'Failed to process query',
          details: {
            error: 'Connection timeout',
          },
        },
      },
    ],
  },

  // Count query
  countQuery: {
    query: 'How many records are in the database?',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'schema_retrieval',
          message: 'Retrieving database schema...',
          progress: 0.2,
        },
      },
      {
        type: 'progress',
        data: {
          stage: 'query_generation',
          message: 'Generating query...',
          progress: 0.6,
        },
      },
      {
        type: 'result',
        data: {
          stage: 'completed',
          message: 'Query processing completed',
          progress: 1.0,
          result: {
            generated_query: 'SELECT COUNT(*) as total FROM main_table',
            confidence_score: 0.98,
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
              execution_time_ms: 15,
            },
            needs_clarification: false,
            clarification_questions: [],
            iterations: 1,
          },
        },
      },
    ],
  },

  // List columns query
  listColumnsQuery: {
    query: 'What are the column names in the main table?',
    events: [
      {
        type: 'progress',
        data: {
          stage: 'schema_retrieval',
          message: 'Retrieving database schema...',
          progress: 0.3,
        },
      },
      {
        type: 'result',
        data: {
          stage: 'completed',
          message: 'Query processing completed',
          progress: 1.0,
          result: {
            generated_query: "SELECT column_name FROM information_schema.columns WHERE table_name = 'main_table'",
            confidence_score: 0.96,
            validation_status: 'valid',
            validation_result: {
              status: 'valid',
              errors: [],
              warnings: [],
              suggestions: [],
            },
            execution_result: {
              success: true,
              row_count: 8,
              execution_time_ms: 22,
            },
            needs_clarification: false,
            clarification_questions: [],
            iterations: 1,
          },
        },
      },
    ],
  },
};

/**
 * Sample test queries for integration testing
 */
export const TEST_QUERIES = {
  simple: 'Get all products with price greater than 100',
  count: 'How many records are in the database?',
  listColumns: 'What are the column names in the main table?',
  aggregation: 'Calculate the average, minimum, and maximum values for all numeric columns',
  clarification: 'Show me sales data',
  complex: 'Complex aggregation with multiple joins',
  invalid: 'Query for nonexistent table',
  error: 'Query that causes processing error',
};

/**
 * Helper to create a mock WebSocket server for testing
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
