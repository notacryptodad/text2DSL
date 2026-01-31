"""RAG Retrieval Agent - intelligent retrieval from OpenSearch"""
import asyncio
import json
import time
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

from text2x.agents.base import BaseAgent, LLMConfig, LLMMessage
from text2x.models import RAGExample, ExampleStatus, SchemaContext

logger = logging.getLogger(__name__)


class RAGRetrievalAgent(BaseAgent):
    """
    RAG Retrieval Agent - Intelligent example retrieval from OpenSearch

    Responsibilities:
    - Multi-strategy search (keyword + embedding + schema-aware)
    - Hybrid search combining multiple approaches
    - Ranking and filtering by relevance
    - Distinguish between good examples (to follow) and bad examples (to avoid)
    - Iterative refinement until quality threshold met

    Implementation follows design.md section 3.5 and 3.3 (RAG Query Strategy)
    """

    def __init__(
        self,
        llm_config: LLMConfig,
        opensearch_client: Any,
        provider_id: str,
        max_iterations: int = 3,
        min_similarity: float = 0.7,
        keyword_weight: float = 0.3,
        embedding_weight: float = 0.7,
        top_k: int = 5
    ):
        super().__init__(llm_config, agent_name="RAGRetrievalAgent")
        self.opensearch_client = opensearch_client
        self.provider_id = provider_id
        self.max_iterations = max_iterations
        self.min_similarity = min_similarity
        self.keyword_weight = keyword_weight
        self.embedding_weight = embedding_weight
        self.top_k = top_k

        logger.info(
            f"RAGRetrievalAgent initialized for provider {provider_id} "
            f"with top_k={top_k}, min_similarity={min_similarity}"
        )

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve relevant examples from OpenSearch

        Input:
            - user_query: str
            - schema_context: Optional[SchemaContext] (for schema-aware search)

        Output:
            - examples: List[RAGExample]
            - search_strategies_used: List[str]
        """
        start_time = time.time()

        user_query = input_data["user_query"]
        schema_context: Optional[SchemaContext] = input_data.get("schema_context")

        logger.info(f"Retrieving RAG examples for query: '{user_query[:50]}...'")

        # Multi-strategy search
        examples = await self._multi_strategy_search(
            user_query=user_query,
            schema_context=schema_context
        )

        duration_ms = (time.time() - start_time) * 1000
        self.add_trace(
            step="retrieve_rag_examples",
            input_data={
                "user_query": user_query[:100],
                "has_schema_context": schema_context is not None
            },
            output_data={
                "examples_found": len(examples),
                "good_examples": sum(1 for ex in examples if ex.is_good_example),
                "bad_examples": sum(1 for ex in examples if not ex.is_good_example),
                "top_similarity": examples[0].similarity_score if examples else 0.0
            },
            duration_ms=duration_ms
        )

        logger.info(
            f"Retrieved {len(examples)} examples "
            f"(good={sum(1 for ex in examples if ex.is_good_example)}, "
            f"bad={sum(1 for ex in examples if not ex.is_good_example)})"
        )

        return {
            "examples": examples,
            "search_strategies_used": ["keyword", "embedding", "schema_aware", "intent_based"]
        }

    async def _multi_strategy_search(
        self,
        user_query: str,
        schema_context: Optional[SchemaContext]
    ) -> List[RAGExample]:
        """
        Multi-strategy search as specified in design.md section 3.3

        Strategies:
        1. Keyword search (BM25)
        2. Embedding/semantic search (k-NN)
        3. Schema-aware search (filter by relevant tables)
        4. Intent-based search (filter by query intent)

        Run strategies in parallel, merge and rank results
        """
        logger.info("Running multi-strategy search")

        # Extract keywords for keyword search
        keywords = await self._extract_keywords(user_query)

        # Get embedding for semantic search
        embedding = await self._get_embedding(user_query)

        # Classify intent
        intent = await self._classify_intent(user_query)

        # Build parallel search tasks
        search_tasks = []

        # Strategy 1: Keyword search
        search_tasks.append(
            self._keyword_search(keywords)
        )

        # Strategy 2: Embedding search
        search_tasks.append(
            self._embedding_search(embedding)
        )

        # Strategy 3: Schema-aware search (if schema context available)
        if schema_context:
            table_names = [t.name for t in schema_context.relevant_tables]
            search_tasks.append(
                self._schema_aware_search(user_query, table_names)
            )

        # Strategy 4: Intent-based search
        search_tasks.append(
            self._intent_based_search(intent)
        )

        # Run all searches in parallel
        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Flatten and merge results
        all_examples: List[RAGExample] = []
        for result in results:
            if isinstance(result, list):
                all_examples.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Search strategy failed: {result}")

        # Merge and rank
        merged_examples = self._merge_and_rank(all_examples, user_query)

        # Filter by quality threshold and top_k
        filtered_examples = [
            ex for ex in merged_examples
            if ex.similarity_score >= self.min_similarity
        ][:self.top_k]

        logger.info(
            f"Multi-strategy search: {len(all_examples)} total results, "
            f"{len(merged_examples)} after merge, "
            f"{len(filtered_examples)} after filtering"
        )

        return filtered_examples

    async def _extract_keywords(self, user_query: str) -> List[str]:
        """Extract important keywords from user query using LLM"""
        messages = [
            LLMMessage(role="system", content=self.build_system_prompt()),
            LLMMessage(
                role="user",
                content=f"""Extract the most important keywords from this query for search purposes.
Focus on entities, actions, and domain-specific terms.

Query: {user_query}

Return ONLY a JSON array of keywords: ["keyword1", "keyword2", ...]"""
            )
        ]

        try:
            response = await self.invoke_llm(messages, temperature=0.0)
            content = response.content.strip()

            # Extract JSON array
            if not content.startswith("["):
                start = content.find("[")
                end = content.rfind("]") + 1
                if start >= 0 and end > start:
                    content = content[start:end]

            keywords = json.loads(content)
            logger.debug(f"Extracted keywords: {keywords}")
            return keywords
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}, using query words")
            # Fallback: simple word splitting
            return [word.lower() for word in user_query.split() if len(word) > 3]

    async def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for semantic search

        TODO: Integrate with actual embedding service (e.g., Bedrock Titan, OpenAI)
        For now, return a mock embedding
        """
        # Mock embedding for development
        # In production, use:
        # - AWS Bedrock Titan embeddings
        # - OpenAI embeddings
        # - Sentence transformers
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_int = int(hash_obj.hexdigest(), 16)

        # Generate deterministic "embedding" from hash
        embedding = [(hash_int >> i) % 100 / 100.0 for i in range(768)]
        return embedding

    async def _classify_intent(self, user_query: str) -> str:
        """Classify query intent using LLM"""
        messages = [
            LLMMessage(role="system", content=self.build_system_prompt()),
            LLMMessage(
                role="user",
                content=f"""Classify the intent of this database query request.

Query: {user_query}

Choose ONE of these intents:
- aggregation: counting, summing, averaging, grouping
- filter: finding records matching conditions
- join: combining data from multiple tables
- sort: ordering results
- complex: multiple operations combined

Return ONLY the intent word (lowercase)."""
            )
        ]

        try:
            response = await self.invoke_llm(messages, temperature=0.0)
            intent = response.content.strip().lower()

            # Validate intent
            valid_intents = {"aggregation", "filter", "join", "sort", "complex"}
            if intent in valid_intents:
                logger.debug(f"Classified intent: {intent}")
                return intent
            else:
                logger.warning(f"Invalid intent '{intent}', defaulting to 'filter'")
                return "filter"
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}, defaulting to 'filter'")
            return "filter"

    async def _keyword_search(self, keywords: List[str]) -> List[RAGExample]:
        """
        Strategy 1: Keyword search using OpenSearch BM25

        Search in natural_language_query field
        """
        try:
            # Build query string from keywords
            query_string = " ".join(keywords)

            # OpenSearch query
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match": {
                                    "natural_language_query": {
                                        "query": query_string,
                                        "operator": "or"
                                    }
                                }
                            }
                        ],
                        "filter": [
                            {"term": {"provider_id": self.provider_id}},
                            {"term": {"status": "approved"}}
                        ]
                    }
                },
                "size": self.top_k * 2  # Get more for merging
            }

            # Execute search
            response = await self.opensearch_client.search(
                index="text2dsl_examples",
                body=search_body
            )

            # Parse results
            examples = []
            for hit in response.get("hits", {}).get("hits", []):
                source = hit["_source"]
                example = self._parse_opensearch_hit(hit)
                example.similarity_score = hit["_score"] / 10.0  # Normalize BM25 score
                examples.append(example)

            logger.debug(f"Keyword search returned {len(examples)} results")
            return examples

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    async def _embedding_search(self, embedding: List[float]) -> List[RAGExample]:
        """
        Strategy 2: Embedding/semantic search using k-NN

        Search using question_embedding field
        """
        try:
            # OpenSearch k-NN query
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "knn": {
                                    "question_embedding": {
                                        "vector": embedding,
                                        "k": self.top_k * 2
                                    }
                                }
                            }
                        ],
                        "filter": [
                            {"term": {"provider_id": self.provider_id}},
                            {"term": {"status": "approved"}}
                        ]
                    }
                },
                "size": self.top_k * 2
            }

            # Execute search
            response = await self.opensearch_client.search(
                index="text2dsl_examples",
                body=search_body
            )

            # Parse results
            examples = []
            for hit in response.get("hits", {}).get("hits", []):
                example = self._parse_opensearch_hit(hit)
                example.similarity_score = hit["_score"]
                examples.append(example)

            logger.debug(f"Embedding search returned {len(examples)} results")
            return examples

        except Exception as e:
            logger.error(f"Embedding search failed: {e}")
            return []

    async def _schema_aware_search(
        self,
        user_query: str,
        table_names: List[str]
    ) -> List[RAGExample]:
        """
        Strategy 3: Schema-aware search

        Filter examples that involve the same tables identified by Schema Expert
        """
        try:
            # OpenSearch query filtering by involved tables
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match": {
                                    "natural_language_query": user_query
                                }
                            }
                        ],
                        "filter": [
                            {"term": {"provider_id": self.provider_id}},
                            {"term": {"status": "approved"}},
                            {
                                "terms": {
                                    "involved_tables": table_names
                                }
                            }
                        ]
                    }
                },
                "size": self.top_k * 2
            }

            # Execute search
            response = await self.opensearch_client.search(
                index="text2dsl_examples",
                body=search_body
            )

            # Parse results
            examples = []
            for hit in response.get("hits", {}).get("hits", []):
                example = self._parse_opensearch_hit(hit)
                example.similarity_score = hit["_score"] / 10.0
                examples.append(example)

            logger.debug(f"Schema-aware search returned {len(examples)} results")
            return examples

        except Exception as e:
            logger.error(f"Schema-aware search failed: {e}")
            return []

    async def _intent_based_search(self, intent: str) -> List[RAGExample]:
        """
        Strategy 4: Intent-based search

        Filter examples by query intent classification
        """
        try:
            # OpenSearch query filtering by intent
            search_body = {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"provider_id": self.provider_id}},
                            {"term": {"status": "approved"}},
                            {"term": {"query_intent": intent}}
                        ]
                    }
                },
                "size": self.top_k * 2
            }

            # Execute search
            response = await self.opensearch_client.search(
                index="text2dsl_examples",
                body=search_body
            )

            # Parse results
            examples = []
            for hit in response.get("hits", {}).get("hits", []):
                example = self._parse_opensearch_hit(hit)
                example.similarity_score = 0.8  # Fixed score for intent matches
                examples.append(example)

            logger.debug(f"Intent-based search returned {len(examples)} results")
            return examples

        except Exception as e:
            logger.error(f"Intent-based search failed: {e}")
            return []

    def _parse_opensearch_hit(self, hit: Dict[str, Any]) -> RAGExample:
        """Parse OpenSearch hit into RAGExample"""
        source = hit["_source"]

        return RAGExample(
            id=UUID(source["id"]) if "id" in source else uuid4(),
            provider_id=source.get("provider_id", self.provider_id),
            natural_language_query=source.get("natural_language_query", ""),
            generated_query=source.get("generated_query", ""),
            is_good_example=source.get("is_good_example", True),
            status=ExampleStatus[source.get("status", "APPROVED").upper()],
            involved_tables=source.get("involved_tables", []),
            query_intent=source.get("query_intent", ""),
            complexity_level=source.get("complexity_level", "medium"),
            reviewed_by=source.get("reviewed_by"),
            reviewed_at=None,  # Parse datetime if needed
            expert_corrected_query=source.get("expert_corrected_query"),
            similarity_score=0.0  # Will be set by caller
        )

    def _merge_and_rank(
        self,
        all_examples: List[RAGExample],
        user_query: str
    ) -> List[RAGExample]:
        """
        Merge results from multiple strategies and rank by combined score

        Deduplicates by example ID and combines scores
        """
        # Deduplicate by ID
        examples_by_id: Dict[UUID, List[float]] = {}

        for example in all_examples:
            if example.id not in examples_by_id:
                examples_by_id[example.id] = []
            examples_by_id[example.id].append(example.similarity_score)

        # Calculate combined scores
        merged_examples = []
        seen_ids = set()

        for example in all_examples:
            if example.id in seen_ids:
                continue

            seen_ids.add(example.id)

            # Average scores from different strategies
            scores = examples_by_id[example.id]
            combined_score = sum(scores) / len(scores)

            # Boost good examples, penalize bad examples
            if example.is_good_example:
                combined_score *= 1.1
            else:
                combined_score *= 0.7

            example.similarity_score = min(1.0, combined_score)
            merged_examples.append(example)

        # Sort by combined score (descending)
        merged_examples.sort(key=lambda ex: ex.similarity_score, reverse=True)

        logger.debug(
            f"Merged {len(all_examples)} examples into {len(merged_examples)} unique results"
        )

        return merged_examples

    def build_system_prompt(self) -> str:
        """Build system prompt for RAG Retrieval Agent"""
        return """You are the RAG Retrieval Agent in a multi-agent system for converting natural language to executable queries.

Your role is to:
- Intelligently retrieve relevant examples from the RAG knowledge base
- Use multiple search strategies to find the best examples
- Distinguish between good examples (to follow) and bad examples (to avoid)
- Extract keywords and classify query intent accurately

You are analytical and focused on finding the most relevant examples to help query generation."""
