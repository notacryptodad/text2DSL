"""Query Builder Agent - generates queries with iterative refinement"""
import json
import time
from typing import Dict, Any, List, Optional
from text2x.agents.base import BaseAgent, LLMConfig, LLMMessage
from text2x.models import SchemaContext, QueryResult, RAGExample, ValidationResult, ValidationStatus


class QueryBuilderAgent(BaseAgent):
    """
    Query Builder Agent
    
    Responsibilities:
    - Generate queries based on schema context and RAG examples
    - Score confidence in generated queries
    - Iteratively refine based on validation feedback
    - Track reasoning for explainability
    """
    
    def __init__(
        self,
        llm_config: LLMConfig,
        max_iterations: int = 5,
        confidence_threshold: float = 0.85
    ):
        super().__init__(llm_config, agent_name="QueryBuilderAgent")
        self.max_iterations = max_iterations
        self.confidence_threshold = confidence_threshold
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate query with iterative refinement
        
        Input:
            - user_query: str
            - schema_context: SchemaContext
            - rag_examples: List[RAGExample] (optional)
            - validation_feedback: ValidationResult (optional, for refinement)
            - iteration: int (optional)
        
        Output:
            - query_result: QueryResult
        """
        start_time = time.time()
        
        user_query = input_data["user_query"]
        schema_context: SchemaContext = input_data["schema_context"]
        rag_examples: List[RAGExample] = input_data.get("rag_examples", [])
        validation_feedback: Optional[ValidationResult] = input_data.get("validation_feedback")
        iteration = input_data.get("iteration", 1)
        
        # Generate query
        generated_query, reasoning_steps = await self._generate_query(
            user_query=user_query,
            schema_context=schema_context,
            rag_examples=rag_examples,
            validation_feedback=validation_feedback,
            iteration=iteration
        )
        
        # Calculate confidence score
        confidence = await self._calculate_confidence(
            user_query=user_query,
            generated_query=generated_query,
            schema_context=schema_context,
            rag_examples=rag_examples,
            iteration=iteration
        )
        
        # Create result
        query_result = QueryResult(
            generated_query=generated_query,
            confidence_score=confidence,
            validation_result=ValidationResult(
                valid=True,
                validation_status=ValidationStatus.PENDING
            ),
            iteration_count=iteration,
            reasoning_steps=reasoning_steps,
            examples_used=[ex.id for ex in rag_examples]
        )
        
        duration_ms = (time.time() - start_time) * 1000
        self.add_trace(
            step="generate_query",
            input_data={
                "user_query": user_query,
                "iteration": iteration,
                "has_feedback": validation_feedback is not None
            },
            output_data={
                "query_length": len(generated_query),
                "confidence": confidence,
                "reasoning_steps": len(reasoning_steps)
            },
            duration_ms=duration_ms
        )
        
        return {"query_result": query_result}
    
    async def _generate_query(
        self,
        user_query: str,
        schema_context: SchemaContext,
        rag_examples: List[RAGExample],
        validation_feedback: Optional[ValidationResult],
        iteration: int
    ) -> tuple[str, List[str]]:
        """Generate query using LLM"""
        # Build context for LLM
        schema_str = self._format_schema_context(schema_context)
        examples_str = self._format_rag_examples(rag_examples)
        
        # Build prompt based on iteration
        if iteration == 1:
            prompt = self._build_initial_prompt(user_query, schema_str, examples_str, schema_context)
        else:
            prompt = self._build_refinement_prompt(
                user_query,
                schema_str,
                validation_feedback,
                iteration
            )
        
        messages = [
            LLMMessage(role="system", content=self.build_system_prompt()),
            LLMMessage(role="user", content=prompt)
        ]
        
        response = await self.invoke_llm(messages, temperature=0.1)
        
        # Extract query and reasoning from response
        query, reasoning_steps = self._parse_llm_response(response.content, schema_context.query_language)
        
        return query, reasoning_steps
    
    def _build_initial_prompt(
        self,
        user_query: str,
        schema_str: str,
        examples_str: str,
        schema_context: SchemaContext
    ) -> str:
        """Build prompt for initial query generation"""
        prompt = f"""Generate a {schema_context.query_language} query to answer the following natural language question.

User Question: {user_query}

Database Schema:
{schema_str}

"""
        if examples_str:
            prompt += f"""Similar Examples:
{examples_str}

"""
        
        prompt += f"""Instructions:
1. Analyze the user question carefully
2. Identify the required tables and columns from the schema
3. Consider the similar examples if provided
4. Generate a complete, executable {schema_context.query_language} query
5. Ensure the query is syntactically correct
6. Include appropriate WHERE clauses, JOINs, and aggregations as needed

Respond in JSON format:
{{
    "reasoning": ["step 1", "step 2", ...],
    "query": "your generated query here"
}}"""
        
        return prompt
    
    def _build_refinement_prompt(
        self,
        user_query: str,
        schema_str: str,
        validation_feedback: Optional[ValidationResult],
        iteration: int
    ) -> str:
        """Build prompt for query refinement"""
        feedback_str = "No specific feedback provided."
        if validation_feedback and not validation_feedback.valid:
            feedback_str = f"Error: {validation_feedback.error}"
            if validation_feedback.suggestions:
                feedback_str += f"\nSuggestions: {', '.join(validation_feedback.suggestions)}"
        
        prompt = f"""The previous query attempt (iteration {iteration - 1}) failed validation.

User Question: {user_query}

Database Schema:
{schema_str}

Validation Feedback:
{feedback_str}

Instructions:
1. Review the validation feedback carefully
2. Identify what went wrong in the previous attempt
3. Generate a corrected query that addresses the issues
4. Ensure the query is syntactically correct and semantically appropriate

Respond in JSON format:
{{
    "reasoning": ["step 1", "step 2", ...],
    "query": "your corrected query here"
}}"""
        
        return prompt
    
    def _format_schema_context(self, schema_context: SchemaContext) -> str:
        """Format schema context for LLM"""
        lines = []
        
        for table in schema_context.relevant_tables:
            lines.append(f"\nTable: {table.name}")
            if table.description:
                lines.append(f"  Description: {table.description}")
            
            for col in table.columns:
                col_str = f"  - {col.name} ({col.type})"
                if not col.nullable:
                    col_str += " NOT NULL"
                if col.description:
                    col_str += f" -- {col.description}"
                lines.append(col_str)
        
        if schema_context.relationships:
            lines.append("\nRelationships:")
            for rel in schema_context.relationships:
                lines.append(f"  {rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}")
        
        if schema_context.suggested_joins:
            lines.append("\nSuggested Joins:")
            for join in schema_context.suggested_joins:
                lines.append(f"  {join.suggested_join_clause}")
        
        return "\n".join(lines)
    
    def _format_rag_examples(self, examples: List[RAGExample]) -> str:
        """Format RAG examples for LLM"""
        if not examples:
            return ""
        
        lines = []
        for i, example in enumerate(examples[:3], 1):  # Limit to top 3 examples
            example_type = "Good Example" if example.is_good_example else "Bad Example (Avoid)"
            lines.append(f"\n{example_type} {i}:")
            lines.append(f"Question: {example.natural_language_query}")
            lines.append(f"Query: {example.generated_query}")
            if not example.is_good_example and example.expert_corrected_query:
                lines.append(f"Corrected: {example.expert_corrected_query}")
        
        return "\n".join(lines)
    
    def _parse_llm_response(self, response: str, query_language: str) -> tuple[str, List[str]]:
        """Parse LLM response to extract query and reasoning"""
        try:
            # Try to parse as JSON
            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.startswith("```"):
                response_clean = response_clean[3:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            
            data = json.loads(response_clean.strip())
            query = data.get("query", "")
            reasoning = data.get("reasoning", [])
            
            return query, reasoning
        except:
            # Fallback: try to extract query from code blocks
            query = self._extract_query_from_text(response, query_language)
            reasoning = ["Generated query from LLM response"]
            return query, reasoning
    
    def _extract_query_from_text(self, text: str, query_language: str) -> str:
        """Extract query from text, looking for code blocks"""
        # Look for SQL/query code blocks
        import re
        
        # Try to find code blocks with language hint
        pattern = f"```(?:{query_language.lower()}|sql)\\s*\n(.*?)\n```"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try to find any code block
        pattern = r"```\s*\n(.*?)\n```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Last resort: return the whole text
        return text.strip()
    
    async def _calculate_confidence(
        self,
        user_query: str,
        generated_query: str,
        schema_context: SchemaContext,
        rag_examples: List[RAGExample],
        iteration: int
    ) -> float:
        """Calculate confidence score for generated query"""
        # Factors affecting confidence:
        # 1. Schema coverage: Are all referenced tables/columns in schema?
        # 2. Example similarity: How similar to good examples?
        # 3. Query complexity: Is the query too simple or too complex?
        # 4. Iteration count: Lower confidence for more iterations
        # 5. Ambiguity: Are there ambiguous terms in the user query?
        
        factors = {}
        
        # Factor 1: Schema coverage (0.0 - 1.0)
        factors['schema_coverage'] = self._check_schema_coverage(generated_query, schema_context)
        
        # Factor 2: Example similarity (0.0 - 1.0)
        if rag_examples:
            factors['example_similarity'] = max(ex.similarity_score for ex in rag_examples if ex.is_good_example)
        else:
            factors['example_similarity'] = 0.5  # Neutral if no examples
        
        # Factor 3: Query complexity (0.0 - 1.0, penalize extremes)
        factors['complexity'] = self._assess_complexity(generated_query, user_query)
        
        # Factor 4: Iteration penalty (0.5 - 1.0)
        factors['iteration'] = max(0.5, 1.0 - (iteration - 1) * 0.1)
        
        # Factor 5: Ambiguity score (0.0 - 1.0, lower is better)
        factors['ambiguity'] = 1.0 - self._detect_ambiguity(user_query)
        
        # Weighted average
        weights = {
            'schema_coverage': 0.3,
            'example_similarity': 0.2,
            'complexity': 0.2,
            'iteration': 0.15,
            'ambiguity': 0.15
        }
        
        confidence = sum(factors[k] * weights[k] for k in factors)
        return round(confidence, 3)
    
    def _check_schema_coverage(self, query: str, schema_context: SchemaContext) -> float:
        """Check if query references valid schema elements"""
        query_lower = query.lower()
        
        # Count referenced tables that exist in schema
        valid_tables = 0
        total_table_refs = 0
        
        for table in schema_context.relevant_tables:
            if table.name.lower() in query_lower:
                total_table_refs += 1
                valid_tables += 1
        
        if total_table_refs == 0:
            return 0.7  # Neutral if no explicit table references
        
        return valid_tables / total_table_refs
    
    def _assess_complexity(self, query: str, user_query: str) -> float:
        """Assess if query complexity matches user question"""
        query_lower = query.lower()
        
        # Simple heuristics
        has_join = 'join' in query_lower
        has_aggregation = any(agg in query_lower for agg in ['count', 'sum', 'avg', 'max', 'min', 'group by'])
        has_subquery = '(' in query and 'select' in query_lower
        
        complexity_score = 0
        if has_join:
            complexity_score += 1
        if has_aggregation:
            complexity_score += 1
        if has_subquery:
            complexity_score += 1
        
        # Check if user query implies complexity
        user_lower = user_query.lower()
        expected_complex = any(word in user_lower for word in [
            'total', 'average', 'count', 'how many', 'sum', 'maximum', 'minimum',
            'each', 'per', 'group', 'compare'
        ])
        
        if expected_complex and complexity_score > 0:
            return 0.9  # Good match
        elif not expected_complex and complexity_score == 0:
            return 0.9  # Good match
        else:
            return 0.7  # Acceptable
    
    def _detect_ambiguity(self, user_query: str) -> float:
        """Detect ambiguity in user query (0.0 = clear, 1.0 = very ambiguous)"""
        ambiguous_indicators = [
            'maybe', 'possibly', 'might', 'could', 'unclear',
            'ambiguous', 'not sure', 'something', 'stuff', 'things'
        ]
        
        user_lower = user_query.lower()
        ambiguity_count = sum(1 for indicator in ambiguous_indicators if indicator in user_lower)
        
        # Also check for very short queries
        word_count = len(user_query.split())
        if word_count < 3:
            ambiguity_count += 1
        
        return min(1.0, ambiguity_count * 0.3)
