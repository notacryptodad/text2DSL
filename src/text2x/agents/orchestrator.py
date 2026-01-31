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
from text2x.models import (
    Conversation,
    ConversationStatus,
    ConversationTurn,
    QueryResponse,
    QueryResult,
    ReasoningTrace,
    ValidationStatus,
    SchemaContext,
    RAGExample,
    ValidationResult,
    ExecutionResult,
)
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

            # Prepare feedback for next iteration
            validation_feedback = validation_result

        # Check if clarification is needed
        needs_clarification, clarification_question = await self._check_clarification_needed(
            user_query=user_query,
            query_result=query_result,
            schema_context=schema_context
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
        1. confidence >= threshold AND validation_passed
        2. OR iteration_count >= max_iterations
        """
        # Max iterations reached
        if iteration >= self.max_iterations:
            return True, "max_iterations_reached"

        # Confidence + validation criteria met
        if (
            query_result.confidence_score >= self.confidence_threshold
            and query_result.validation_result.validation_status == ValidationStatus.PASSED
        ):
            return True, "confidence_and_validation_met"

        # Continue iterating
        return False, "continue_iteration"

    async def _check_clarification_needed(
        self,
        user_query: str,
        query_result: QueryResult,
        schema_context: SchemaContext
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if user clarification is needed based on confidence and ambiguity
        """
        # If confidence is below clarification threshold, request clarification
        if query_result.confidence_score < self.clarification_threshold:
            logger.info(
                f"Low confidence ({query_result.confidence_score:.3f}), "
                f"requesting clarification"
            )

            clarification_question = await self._generate_clarification_question(
                user_query=user_query,
                query_result=query_result,
                schema_context=schema_context
            )

            return True, clarification_question

        return False, None

    async def _generate_clarification_question(
        self,
        user_query: str,
        query_result: QueryResult,
        schema_context: SchemaContext
    ) -> str:
        """Use LLM to generate a helpful clarification question"""
        tables_str = ", ".join([t.name for t in schema_context.relevant_tables])

        messages = [
            LLMMessage(role="system", content=self.build_system_prompt()),
            LLMMessage(
                role="user",
                content=f"""The system has low confidence in understanding the user's query.
Generate a clarification question to help the user provide more specific information.

User Query: {user_query}

Available Tables: {tables_str}

Generated Query (low confidence): {query_result.generated_query}

Confidence Score: {query_result.confidence_score:.2f}

Generate ONE specific clarification question that would help improve the query.
Focus on ambiguities in the user's request or missing details.
Keep it concise and friendly."""
            )
        ]

        try:
            response = await self.invoke_llm(messages, temperature=0.3)
            return response.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate clarification question: {e}")
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
