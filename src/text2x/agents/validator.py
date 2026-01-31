"""Validator Agent - validates and tests generated queries"""
import time
from typing import Dict, Any, Optional, List
from text2x.agents.base import BaseAgent, LLMConfig, LLMMessage
from text2x.models import ValidationResult, ValidationStatus, ExecutionResult
from text2x.providers.base import QueryProvider, ProviderCapability


class ValidatorAgent(BaseAgent):
    """
    Validator Agent
    
    Responsibilities:
    - Validate query syntax
    - Execute queries safely (with limits)
    - Analyze execution results
    - Provide diagnostic feedback for refinement
    """
    
    def __init__(
        self,
        llm_config: LLMConfig,
        provider: QueryProvider,
        execution_limit: int = 100,
        execution_timeout: float = 30.0
    ):
        super().__init__(llm_config, agent_name="ValidatorAgent")
        self.provider = provider
        self.execution_limit = execution_limit
        self.execution_timeout = execution_timeout
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and test query
        
        Input:
            - query: str
            - user_query: str (original question for semantic validation)
        
        Output:
            - validation_result: ValidationResult
            - execution_result: Optional[ExecutionResult]
        """
        start_time = time.time()
        
        query = input_data["query"]
        user_query = input_data.get("user_query", "")
        
        # Validation pipeline
        validation_result, execution_result = await self._run_validation_pipeline(
            query=query,
            user_query=user_query
        )
        
        duration_ms = (time.time() - start_time) * 1000
        self.add_trace(
            step="validate_query",
            input_data={"query_length": len(query)},
            output_data={
                "valid": validation_result.valid,
                "status": validation_result.validation_status.value,
                "executed": execution_result is not None
            },
            duration_ms=duration_ms
        )
        
        return {
            "validation_result": validation_result,
            "execution_result": execution_result
        }
    
    async def _run_validation_pipeline(
        self,
        query: str,
        user_query: str
    ) -> tuple[ValidationResult, Optional[ExecutionResult]]:
        """Run complete validation pipeline"""
        # Step 1: Syntax validation
        syntax_result = await self._validate_syntax(query)
        if not syntax_result.valid:
            return syntax_result, None
        
        # Step 2: Semantic validation (basic checks)
        semantic_result = await self._validate_semantics(query, user_query)
        if not semantic_result.valid:
            return semantic_result, None
        
        # Step 3: Execution test (if provider supports it)
        if ProviderCapability.QUERY_EXECUTION in self.provider.get_capabilities():
            execution_result = await self._execute_query(query)
            
            # Step 4: Result analysis
            result_validation = await self._analyze_results(
                query=query,
                user_query=user_query,
                execution_result=execution_result
            )
            
            return result_validation, execution_result
        else:
            # No execution capability, mark as passed if syntax/semantics OK
            return ValidationResult(
                valid=True,
                validation_status=ValidationStatus.PASSED
            ), None
    
    async def _validate_syntax(self, query: str) -> ValidationResult:
        """Validate query syntax using provider"""
        try:
            provider_result = await self.provider.validate_syntax(query)
            
            if provider_result.valid:
                return ValidationResult(
                    valid=True,
                    validation_status=ValidationStatus.PENDING
                )
            else:
                return ValidationResult(
                    valid=False,
                    validation_status=ValidationStatus.FAILED,
                    error=f"Syntax error: {provider_result.error}",
                    suggestions=["Check query syntax", "Verify table and column names"]
                )
        except Exception as e:
            return ValidationResult(
                valid=False,
                validation_status=ValidationStatus.FAILED,
                error=f"Syntax validation failed: {str(e)}",
                suggestions=["Review query structure"]
            )
    
    async def _validate_semantics(self, query: str, user_query: str) -> ValidationResult:
        """Basic semantic validation"""
        query_lower = query.lower()
        
        # Check for dangerous operations
        dangerous_ops = ['drop', 'delete', 'truncate', 'alter', 'create', 'insert', 'update']
        for op in dangerous_ops:
            if f' {op} ' in f' {query_lower} ':
                return ValidationResult(
                    valid=False,
                    validation_status=ValidationStatus.FAILED,
                    error=f"Dangerous operation detected: {op.upper()}",
                    suggestions=["Only SELECT queries are allowed"]
                )
        
        # Check if query is a SELECT
        if not query_lower.strip().startswith('select'):
            query_language = self.provider.get_query_language()
            if query_language == "SQL":
                return ValidationResult(
                    valid=False,
                    validation_status=ValidationStatus.FAILED,
                    error="Query must be a SELECT statement",
                    suggestions=["Start query with SELECT"]
                )
        
        # Passed semantic checks
        return ValidationResult(
            valid=True,
            validation_status=ValidationStatus.PENDING
        )
    
    async def _execute_query(self, query: str) -> ExecutionResult:
        """Execute query with safety limits"""
        try:
            result = await self.provider.execute_query(query, limit=self.execution_limit)
            
            if result and result.success:
                return result
            else:
                return ExecutionResult(
                    success=False,
                    error=result.error if result else "Execution failed"
                )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}"
            )
    
    async def _analyze_results(
        self,
        query: str,
        user_query: str,
        execution_result: ExecutionResult
    ) -> ValidationResult:
        """Analyze execution results to determine if query is correct"""
        if not execution_result.success:
            return ValidationResult(
                valid=False,
                validation_status=ValidationStatus.FAILED,
                error=execution_result.error,
                suggestions=self._generate_error_suggestions(execution_result.error)
            )
        
        # Check if results make sense
        if execution_result.row_count == 0:
            # Empty results might be valid, but let's use LLM to verify
            is_expected = await self._check_if_empty_expected(user_query, query)
            
            if not is_expected:
                return ValidationResult(
                    valid=False,
                    validation_status=ValidationStatus.FAILED,
                    error="Query returned no results, which seems unexpected",
                    suggestions=[
                        "Check WHERE clause conditions",
                        "Verify table contains data",
                        "Review JOIN conditions"
                    ]
                )
        
        # Check for suspicious patterns
        if execution_result.row_count == self.execution_limit:
            # Might have more results, but this is OK
            pass
        
        # Results look good
        return ValidationResult(
            valid=True,
            validation_status=ValidationStatus.PASSED
        )
    
    def _generate_error_suggestions(self, error: Optional[str]) -> List[str]:
        """Generate suggestions based on error message"""
        if not error:
            return ["Review query logic"]
        
        error_lower = error.lower()
        suggestions = []
        
        if 'table' in error_lower and ('not found' in error_lower or 'does not exist' in error_lower):
            suggestions.append("Verify table name exists in schema")
            suggestions.append("Check for typos in table name")
        
        if 'column' in error_lower and ('not found' in error_lower or 'does not exist' in error_lower):
            suggestions.append("Verify column name exists in table")
            suggestions.append("Check for typos in column name")
        
        if 'syntax' in error_lower:
            suggestions.append("Review query syntax")
            suggestions.append("Check for missing or extra commas, parentheses")
        
        if 'ambiguous' in error_lower:
            suggestions.append("Add table aliases to disambiguate columns")
            suggestions.append("Qualify column names with table names")
        
        if not suggestions:
            suggestions.append("Review error message and adjust query accordingly")
        
        return suggestions
    
    async def _check_if_empty_expected(self, user_query: str, query: str) -> bool:
        """Use LLM to determine if empty results are expected"""
        messages = [
            LLMMessage(role="system", content=self.build_system_prompt()),
            LLMMessage(
                role="user",
                content=f"""Given the user's question and the generated query that returned zero results, determine if zero results is a reasonable/expected outcome.

User Question: {user_query}

Generated Query: {query}

Consider:
1. Does the query have very specific WHERE conditions that might legitimately match nothing?
2. Does the user question ask for something that might not exist?
3. Is this likely a data issue or a query logic issue?

Respond with ONLY "EXPECTED" or "UNEXPECTED" followed by a brief reason."""
            )
        ]
        
        try:
            response = await self.invoke_llm(messages, temperature=0.0)
            return response.content.strip().upper().startswith("EXPECTED")
        except:
            # Default to unexpected if LLM fails
            return False
