"""Orchestrator Agent - central coordinator for multi-agent query processing"""
import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from text2x.agents.base import BaseAgent, LLMConfig, LLMMessage
from text2x.agents.schema_expert import SchemaExpertAgent
from text2x.agents.rag_retrieval import RAGRetrievalAgent
from text2x.agents.query_builder import QueryBuilderAgent
from text2x.agents.validator import ValidatorAgent

# Import domain models (dataclasses) from models.py, not the database models from models/
# The models/ package exports database models, but agents need domain dataclasses
import importlib.util
from pathlib import Path as _Path

_models_file = _Path(__file__).parent.parent / "models.py"
_spec = importlib.util.spec_from_file_location("text2x_domain_models", _models_file)
_domain_models = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_domain_models)

# Use domain dataclasses that have the methods agents need (like add_turn())
Conversation = _domain_models.Conversation
ConversationStatus = _domain_models.ConversationStatus
ConversationTurn = _domain_models.ConversationTurn
QueryResponse = _domain_models.QueryResponse
QueryResult = _domain_models.QueryResult
ReasoningTrace = _domain_models.ReasoningTrace
ValidationStatus = _domain_models.ValidationStatus
SchemaContext = _domain_models.SchemaContext
RAGExample = _domain_models.RAGExample
ValidationResult = _domain_models.ValidationResult
ExecutionResult = _domain_models.ExecutionResult

from text2x.providers.base import QueryProvider

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent - Central coordinator for multi-agent query processing

    Responsibilities:
    - Manage conversation flow and state
    - Coordinate parallel dispatch to sub-agents (Schema Expert, RAG Retrieval)
    - Sequential orchestration (Query Builder, Validator)
    - Implement termination logic: confidence >= threshold AND validation_passed
    - Request user clarification when needed
    - Track full reasoning trace
    - Session management with database persistence

    Parallel Dispatch Strategy (from design.md section 3.1):
    Phase 1 (Parallel): Schema Expert + RAG Retrieval
    Phase 2 (Sequential): Query Builder
    Phase 3 (Sequential): Validator
    Phase 4 (Loop): If validation fails, return to Phase 2 with feedback
    """

    def __init__(
        self,
        llm_config: LLMConfig,
        provider: QueryProvider,
        opensearch_client: Any,
        max_iterations: int = 5,
        confidence_threshold: float = 0.85,
        clarification_threshold: float = 0.6
    ):
        super().__init__(llm_config, agent_name="OrchestratorAgent")
        self.provider = provider
        self.opensearch_client = opensearch_client
        self.max_iterations = max_iterations
        self.confidence_threshold = confidence_threshold
        self.clarification_threshold = clarification_threshold

        # Initialize sub-agents
        self.schema_expert = SchemaExpertAgent(llm_config, provider)
        self.rag_retrieval = RAGRetrievalAgent(llm_config, opensearch_client, provider.get_provider_id())
        self.query_builder = QueryBuilderAgent(llm_config, max_iterations, confidence_threshold)
        self.validator = ValidatorAgent(llm_config, provider)

        # Active conversations cache (keyed by conversation_id)
        self.conversations: Dict[UUID, Conversation] = {}

        logger.info(
            f"OrchestratorAgent initialized with max_iterations={max_iterations}, "
            f"confidence_threshold={confidence_threshold}"
        )

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main orchestration loop

        Input:
            - user_query: str
            - provider_id: str
            - conversation_id: Optional[UUID]
            - user_id: str
            - enable_execution: bool
            - trace_level: str ("none", "summary", "full")

        Output:
            - conversation_id: UUID
            - turn_id: UUID
            - query_response: QueryResponse
            - all_traces: List[ReasoningTrace]
        """
        start_time = time.time()

        user_query = input_data["user_query"]
        provider_id = input_data["provider_id"]
        conversation_id = input_data.get("conversation_id")
        user_id = input_data.get("user_id", "anonymous")
        enable_execution = input_data.get("enable_execution", False)
        trace_level = input_data.get("trace_level", "summary")
        annotations = input_data.get("annotations", {})

        logger.info(f"Processing query: '{user_query[:50]}...' for provider {provider_id}")

        # Get or create conversation
        conversation, is_new = await self._get_or_create_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            provider_id=provider_id
        )

        # Iterative refinement loop
        iteration = 0
        query_result: Optional[QueryResult] = None
        schema_context: Optional[SchemaContext] = None
        rag_examples: List[RAGExample] = []
        validation_feedback: Optional[ValidationResult] = None

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"Starting iteration {iteration}/{self.max_iterations}")

            # Phase 1: Parallel context gathering (Schema + RAG)
            if iteration == 1:
                schema_context, rag_examples = await self._parallel_context_gathering(
                    user_query=user_query,
                    annotations=annotations
                )

            # Phase 2: Query generation
            query_result = await self._generate_query(
                user_query=user_query,
                schema_context=schema_context,
                rag_examples=rag_examples,
                validation_feedback=validation_feedback,
                iteration=iteration
            )

            # Phase 3: Validation
            validation_result, execution_result = await self._validate_query(
                query=query_result.generated_query,
                user_query=user_query,
                enable_execution=enable_execution
            )

            # Update query result with validation/execution results
            query_result.validation_result = validation_result
            query_result.execution_result = execution_result

            # Check termination criteria
            should_terminate, reason = self._should_terminate(
                query_result=query_result,
                iteration=iteration
            )

            logger.info(
                f"Iteration {iteration}: confidence={query_result.confidence_score:.3f}, "
                f"validation={validation_result.validation_status.value}, "
                f"terminate={should_terminate} ({reason})"
            )

            if should_terminate:
                break

            # Check if clarification is needed DURING iteration (not after)
            # Per design.md 15.3: clarify = confidence < 0.6 AND iterations < 5
            # If confidence is very low, no amount of iteration will help without user input
            if (
                query_result.confidence_score < self.clarification_threshold
                and iteration < self.max_iterations
            ):
                logger.info(
                    f"Low confidence ({query_result.confidence_score:.3f} < {self.clarification_threshold}) "
                    f"on iteration {iteration}, requesting clarification instead of continuing"
                )
                # Break out of loop early - we'll generate clarification question below
                break

            # Prepare feedback for next iteration
            validation_feedback = validation_result

        # Check if clarification is needed (comprehensive check after loop)
        needs_clarification, clarification_question = await self._check_clarification_needed(
            user_query=user_query,
            query_result=query_result,
            schema_context=schema_context,
            iteration=iteration
        )

        # Build query response
        query_response = QueryResponse(
            generated_query=query_result.generated_query,
            confidence_score=query_result.confidence_score,
            validation_status=query_result.validation_result.validation_status,
            execution_result=query_result.execution_result,
            iterations=iteration,
            clarification_needed=needs_clarification,
            clarification_question=clarification_question,
            reasoning_trace=query_result.reasoning_steps if trace_level != "none" else []
        )

        # Collect all traces from sub-agents
        all_traces = self._collect_all_traces()

        # Add turn to conversation
        turn = conversation.add_turn(
            user_input=user_query,
            response=query_response,
            trace=all_traces
        )

        # Update conversation status
        if needs_clarification:
            conversation.status = ConversationStatus.ACTIVE
        else:
            conversation.status = ConversationStatus.COMPLETED

        duration_ms = (time.time() - start_time) * 1000
        self.add_trace(
            step="orchestrate_query_processing",
            input_data={
                "user_query": user_query[:100],
                "conversation_id": str(conversation.id),
                "is_new_conversation": is_new
            },
            output_data={
                "iterations": iteration,
                "confidence": query_result.confidence_score,
                "validation_status": query_result.validation_result.validation_status.value,
                "needs_clarification": needs_clarification,
                "turn_id": str(turn.id)
            },
            duration_ms=duration_ms
        )

        logger.info(
            f"Query processing completed: conversation_id={conversation.id}, "
            f"turn_id={turn.id}, iterations={iteration}, "
            f"confidence={query_result.confidence_score:.3f}"
        )

        return {
            "conversation_id": conversation.id,
            "turn_id": turn.id,
            "query_response": query_response,
            "all_traces": all_traces if trace_level == "full" else []
        }

    async def _get_or_create_conversation(
        self,
        conversation_id: Optional[UUID],
        user_id: str,
        provider_id: str
    ) -> tuple[Conversation, bool]:
        """Get existing conversation or create new one"""
        if conversation_id and conversation_id in self.conversations:
            # Return existing conversation
            conversation = self.conversations[conversation_id]
            return conversation, False

        # Create new conversation
        new_conversation = Conversation(
            id=conversation_id or uuid4(),
            user_id=user_id,
            provider_id=provider_id,
            status=ConversationStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            turns=[]
        )

        self.conversations[new_conversation.id] = new_conversation

        # TODO: Persist to database
        # await db_repo.create_conversation(new_conversation)

        return new_conversation, True

    async def _parallel_context_gathering(
        self,
        user_query: str,
        annotations: Dict[str, str]
    ) -> tuple[SchemaContext, List[RAGExample]]:
        """
        Phase 1: Parallel dispatch to Schema Expert and RAG Retrieval agents

        This is the key parallel optimization from design.md section 3.1
        """
        logger.info("Phase 1: Starting parallel context gathering")
        start_time = time.time()

        # Run Schema Expert and RAG Retrieval in parallel
        schema_task = self.schema_expert.process({
            "user_query": user_query,
            "annotations": annotations
        })

        rag_task = self.rag_retrieval.process({
            "user_query": user_query
        })

        # Wait for both to complete
        schema_result, rag_result = await asyncio.gather(schema_task, rag_task)

        schema_context: SchemaContext = schema_result["schema_context"]
        rag_examples: List[RAGExample] = rag_result["examples"]

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Phase 1 completed in {duration_ms:.1f}ms: "
            f"tables={len(schema_context.relevant_tables)}, "
            f"examples={len(rag_examples)}"
        )

        return schema_context, rag_examples

    async def _generate_query(
        self,
        user_query: str,
        schema_context: SchemaContext,
        rag_examples: List[RAGExample],
        validation_feedback: Optional[ValidationResult],
        iteration: int
    ) -> QueryResult:
        """Phase 2: Query generation using Query Builder agent"""
        logger.info(f"Phase 2: Generating query (iteration {iteration})")
        start_time = time.time()

        result = await self.query_builder.process({
            "user_query": user_query,
            "schema_context": schema_context,
            "rag_examples": rag_examples,
            "validation_feedback": validation_feedback,
            "iteration": iteration
        })

        query_result: QueryResult = result["query_result"]

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Phase 2 completed in {duration_ms:.1f}ms: "
            f"confidence={query_result.confidence_score:.3f}"
        )

        return query_result

    async def _validate_query(
        self,
        query: str,
        user_query: str,
        enable_execution: bool
    ) -> tuple[ValidationResult, Optional[ExecutionResult]]:
        """Phase 3: Query validation using Validator agent"""
        logger.info("Phase 3: Validating query")
        start_time = time.time()

        # Validator agent handles both validation and execution
        result = await self.validator.process({
            "query": query,
            "user_query": user_query
        })

        validation_result: ValidationResult = result["validation_result"]
        execution_result: Optional[ExecutionResult] = result.get("execution_result")

        # If execution is disabled, don't return execution result
        if not enable_execution:
            execution_result = None

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Phase 3 completed in {duration_ms:.1f}ms: "
            f"status={validation_result.validation_status.value}"
        )

        return validation_result, execution_result

    def _should_terminate(
        self,
        query_result: QueryResult,
        iteration: int
    ) -> tuple[bool, str]:
        """
        Termination logic from design.md section 3.1:

        Terminate if:
        1. confidence >= 0.85 AND validation_passed (PRIMARY CRITERIA)
        2. OR iteration_count >= max_iterations (FALLBACK)

        The termination criteria ensures we only stop when:
        - The confidence score is >= 0.85 (high confidence)
        - AND the query has passed validation (syntactically and semantically correct)

        If these criteria are not met, we continue iterating until max_iterations.
        """
        # Max iterations reached (fallback termination)
        if iteration >= self.max_iterations:
            logger.warning(
                f"Terminating after reaching max iterations ({self.max_iterations}). "
                f"Final confidence: {query_result.confidence_score:.3f}, "
                f"validation: {query_result.validation_result.validation_status.value}"
            )
            return True, "max_iterations_reached"

        # Primary termination criteria: confidence >= 0.85 AND validation passed
        confidence_check = query_result.confidence_score >= self.confidence_threshold
        # Compare enum values (strings) instead of instances to avoid issues with dynamic module loading
        validation_check = query_result.validation_result.validation_status.value == "passed"

        logger.debug(
            f"Termination check: confidence={query_result.confidence_score:.3f} >= {self.confidence_threshold}? {confidence_check}, "
            f"validation={query_result.validation_result.validation_status.value} == 'passed'? {validation_check}"
        )

        if confidence_check and validation_check:
            logger.info(
                f"Termination criteria met: confidence={query_result.confidence_score:.3f} >= "
                f"{self.confidence_threshold}, validation=PASSED"
            )
            return True, "confidence_and_validation_met"

        # Log why we're continuing
        logger.debug(
            f"Continuing iteration: confidence={query_result.confidence_score:.3f} "
            f"(threshold={self.confidence_threshold}), "
            f"validation={query_result.validation_result.validation_status.value}"
        )

        # Continue iterating
        return False, "continue_iteration"

    async def _check_clarification_needed(
        self,
        user_query: str,
        query_result: QueryResult,
        schema_context: SchemaContext,
        iteration: int
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if user clarification is needed based on multiple factors:

        1. Low confidence score (< clarification_threshold, typically 0.6)
        2. Validation failed despite multiple iterations
        3. Vague query patterns (e.g., very short queries, ambiguous terms)
        4. Multiple possible interpretations

        This implements the clarification flow for handling vague/ambiguous queries.
        Per design.md 15.3: clarify = confidence < 0.6 AND iterations < 5
        """
        reasons = []

        # Check 1: Low confidence score
        if query_result.confidence_score < self.clarification_threshold:
            reasons.append(f"low_confidence_{query_result.confidence_score:.2f}")
            logger.info(
                f"Low confidence detected: {query_result.confidence_score:.3f} < "
                f"{self.clarification_threshold}"
            )

        # Check 2: Validation failed
        if query_result.validation_result.validation_status == ValidationStatus.FAILED:
            reasons.append("validation_failed")
            logger.info("Validation failed, may need clarification")

        # Check 3: Vague query patterns
        query_words = user_query.strip().split()
        if len(query_words) <= 3:
            reasons.append("very_short_query")
            logger.info(f"Very short query detected: {len(query_words)} words")

        # Check 4: Query contains ambiguous keywords
        ambiguous_keywords = ["all", "everything", "data", "stuff", "things", "some", "any"]
        if any(keyword in user_query.lower() for keyword in ambiguous_keywords):
            if len(query_words) <= 5:  # Only flag if query is also short
                reasons.append("ambiguous_terms")
                logger.info("Ambiguous terms detected in short query")

        # Check 5: No relevant tables found
        if len(schema_context.relevant_tables) == 0:
            reasons.append("no_relevant_tables")
            logger.warning("No relevant tables found in schema context")

        # Determine if clarification is needed
        if reasons:
            logger.info(f"Clarification needed. Reasons: {', '.join(reasons)}")

            clarification_question = await self._generate_clarification_question(
                user_query=user_query,
                query_result=query_result,
                schema_context=schema_context,
                reasons=reasons
            )

            return True, clarification_question

        return False, None

    async def _generate_clarification_question(
        self,
        user_query: str,
        query_result: QueryResult,
        schema_context: SchemaContext,
        reasons: List[str] = None
    ) -> str:
        """
        Use LLM to generate a helpful clarification question for vague/ambiguous queries.

        The question should be:
        - Specific and actionable
        - Friendly and non-technical (when possible)
        - Focused on resolving the primary ambiguity
        - Context-aware (references available tables/columns)
        """
        reasons = reasons or []
        tables_str = ", ".join([t.name for t in schema_context.relevant_tables])

        # Build context based on reasons for clarification
        reason_context = ""
        if "no_relevant_tables" in reasons:
            reason_context = "\nNote: No relevant tables were found for this query."
        elif "validation_failed" in reasons:
            reason_context = f"\nNote: Query validation failed: {query_result.validation_result.error}"
        elif "very_short_query" in reasons or "ambiguous_terms" in reasons:
            reason_context = "\nNote: The query is too vague and needs more specific details."

        messages = [
            LLMMessage(role="system", content=self.build_system_prompt()),
            LLMMessage(
                role="user",
                content=f"""The system needs clarification to better understand the user's query.
Generate a helpful clarification question that guides the user to be more specific.

User Query: "{user_query}"

Available Tables: {tables_str if tables_str else "None found"}

Generated Query (low confidence): {query_result.generated_query}

Confidence Score: {query_result.confidence_score:.2f}

Reasons for clarification: {', '.join(reasons)}{reason_context}

Generate ONE specific, friendly clarification question that will help resolve the ambiguity.
Examples of good clarification questions:
- "Which table would you like to query: users, orders, or products?"
- "Do you want to see the count of records, or specific fields like name and email?"
- "Are you looking for records from a specific time period?"

Keep it concise, specific, and helpful."""
            )
        ]

        try:
            response = await self.invoke_llm(messages, temperature=0.3)
            question = response.content.strip()

            # Remove quotes if the LLM wrapped the question
            if question.startswith('"') and question.endswith('"'):
                question = question[1:-1]

            return question
        except Exception as e:
            logger.error(f"Failed to generate clarification question: {e}")

            # Fallback to a generic but helpful question
            if "no_relevant_tables" in reasons:
                return "I couldn't identify which tables to query. Could you specify which data you're interested in?"
            elif "very_short_query" in reasons:
                return "Could you provide more details about what you're looking for? For example, which fields do you need and any filtering criteria?"
            else:
                return "Could you please provide more details about what you're looking for?"

    def _collect_all_traces(self) -> List[ReasoningTrace]:
        """Collect reasoning traces from all sub-agents"""
        all_traces = []

        # Collect from orchestrator
        all_traces.extend(self.get_traces())

        # Collect from sub-agents
        all_traces.extend(self.schema_expert.get_traces())
        all_traces.extend(self.rag_retrieval.get_traces())
        all_traces.extend(self.query_builder.get_traces())
        all_traces.extend(self.validator.get_traces())

        # Sort by timestamp
        all_traces.sort(key=lambda t: t.timestamp)

        return all_traces

    def build_system_prompt(self) -> str:
        """Build system prompt for Orchestrator"""
        return """You are the Orchestrator Agent in a multi-agent system for converting natural language to executable queries.

Your role is to:
- Coordinate multiple specialized agents (Schema Expert, RAG Retrieval, Query Builder, Validator)
- Determine when user clarification is needed
- Ensure high-quality query generation through iterative refinement
- Maintain conversation context across multiple turns

You are analytical, precise, and focused on achieving the best possible results for the user."""

    async def cleanup(self):
        """Cleanup all sub-agents"""
        await self.schema_expert.cleanup()
        await self.rag_retrieval.cleanup()
        await self.query_builder.cleanup()
        await self.validator.cleanup()
        await super().cleanup()
