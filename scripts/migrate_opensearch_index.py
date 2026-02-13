#!/usr/bin/env python3
"""
Migrate from text2dsl-queries to text2dsl-samples-{provider} indices.

Blue-green migration with field transformation per migration-guide.md.

Usage:
    # Dry run (validate only)
    uv run python scripts/migrate_opensearch_index.py --dry-run

    # Full migration
    uv run python scripts/migrate_opensearch_index.py

    # Migrate + create aliases
    uv run python scripts/migrate_opensearch_index.py --create-aliases

    # Rollback (switch alias back to old index)
    uv run python scripts/migrate_opensearch_index.py --rollback
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

from opensearchpy import AsyncOpenSearch, RequestError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class IndexMigration:
    """Handles blue-green migration from old to new OpenSearch index schema."""

    OLD_INDEX = "text2dsl-queries"
    NEW_INDEX_PREFIX = "text2dsl-samples"
    ALIAS = "text2dsl-queries-active"
    PROVIDERS = ["sql", "mongodb", "splunk"]

    def __init__(self, host: str = "localhost", port: int = 9200,
                 username: str = None, password: str = None, use_ssl: bool = False):
        http_auth = (username, password) if username and password else None
        self.client = AsyncOpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=http_auth,
            use_ssl=use_ssl,
            verify_certs=use_ssl,
            ssl_show_warn=False,
            timeout=60,
        )

    def _new_index(self, provider: str) -> str:
        return f"{self.NEW_INDEX_PREFIX}-{provider}"

    async def create_new_indices(self, dry_run: bool = False) -> None:
        """Create provider-specific indices with the new schema."""
        from text2x.services.opensearch_service import OpenSearchService

        svc = OpenSearchService(opensearch_client=self.client)

        for provider in self.PROVIDERS:
            index_name = self._new_index(provider)
            if dry_run:
                exists = await self.client.indices.exists(index=index_name)
                logger.info(f"[DRY RUN] Index '{index_name}': {'exists' if exists else 'would be created'}")
            else:
                created = await svc.create_index_if_not_exists(index_name=index_name)
                if created:
                    logger.info(f"✓ Created index: {index_name}")
                else:
                    logger.info(f"⚠ Index {index_name} already exists")

    async def reindex_data(self, dest_provider: str = "sql", dry_run: bool = False) -> None:
        """Reindex data from old index to new provider-specific index."""
        dest_index = self._new_index(dest_provider)

        # Check source exists
        if not await self.client.indices.exists(index=self.OLD_INDEX):
            logger.warning(f"Source index '{self.OLD_INDEX}' does not exist, skipping reindex")
            return

        source_count = (await self.client.count(index=self.OLD_INDEX))["count"]
        logger.info(f"Source index '{self.OLD_INDEX}' has {source_count} documents")

        if source_count == 0:
            logger.info("No documents to migrate")
            return

        if dry_run:
            logger.info(f"[DRY RUN] Would reindex {source_count} docs from '{self.OLD_INDEX}' → '{dest_index}'")
            return

        reindex_body = {
            "source": {"index": self.OLD_INDEX},
            "dest": {"index": dest_index},
            "script": {
                "source": (
                    "ctx._source.natural_language_query = ctx._source.containsKey('question') ? ctx._source.remove('question') : ctx._source.get('nl_query');"
                    "ctx._source.dsl_query = ctx._source.containsKey('sql') ? ctx._source.remove('sql') : ctx._source.get('generated_query');"
                    "ctx._source.dsl_query_analyzed = ctx._source.dsl_query;"
                    "ctx._source.provider_type = 'sql';"
                    "ctx._source.provider_id = ctx._source.containsKey('provider_id') ? ctx._source.provider_id : 'default';"
                    "ctx._source.status = 'approved';"
                    "ctx._source.is_good_example = true;"
                    "ctx._source.source = 'migrated';"
                    "ctx._source.query_intent = ctx._source.containsKey('query_intent') ? ctx._source.query_intent : 'unknown';"
                    "ctx._source.complexity_level = ctx._source.containsKey('difficulty') ? ctx._source.difficulty : 'medium';"
                    "ctx._source.involved_tables = ctx._source.containsKey('involved_tables') ? ctx._source.involved_tables : ['unknown'];"
                    "ctx._source.usage_count = 0;"
                    "ctx._source.success_rate = 1.0;"
                    "ctx._source.avg_similarity_score = 0.0;"
                    "ctx._source.embedding_model = 'titan-v2';"
                    "ctx._source.indexed_at = new Date();"
                    "if (ctx._source.created_at == null) { ctx._source.created_at = new Date(); }"
                    "ctx._source.updated_at = new Date();"
                )
            },
        }

        logger.info(f"Starting reindex: '{self.OLD_INDEX}' → '{dest_index}'...")
        start = time.time()

        response = await self.client.reindex(body=reindex_body, wait_for_completion=False)
        task_id = response.get("task")
        logger.info(f"Reindex task started: {task_id}")

        # Poll for completion
        while True:
            task_status = await self.client.tasks.get(task_id=task_id)
            if task_status.get("completed"):
                elapsed = time.time() - start
                resp = task_status.get("response", {})
                total = resp.get("total", 0)
                created = resp.get("created", 0)
                failures = resp.get("failures", [])
                logger.info(f"✓ Reindex complete in {elapsed:.1f}s: {created}/{total} docs migrated")
                if failures:
                    logger.warning(f"  {len(failures)} failures: {failures[:3]}")
                break
            await asyncio.sleep(2)

    async def validate(self, dest_provider: str = "sql") -> bool:
        """Validate document counts match between old and new index."""
        dest_index = self._new_index(dest_provider)

        if not await self.client.indices.exists(index=self.OLD_INDEX):
            logger.info(f"Source index '{self.OLD_INDEX}' does not exist, skipping validation")
            return True

        source_count = (await self.client.count(index=self.OLD_INDEX))["count"]
        dest_count = (await self.client.count(index=dest_index))["count"]

        if source_count == dest_count:
            logger.info(f"✓ Document counts match: {source_count}")
            return True
        else:
            logger.error(f"✗ Count mismatch: source={source_count}, dest={dest_count}")
            return False

    async def create_aliases(self, dry_run: bool = False) -> None:
        """Create alias pointing to new SQL index."""
        dest_index = self._new_index("sql")

        if dry_run:
            logger.info(f"[DRY RUN] Would create alias '{self.ALIAS}' → '{dest_index}'")
            return

        actions = [{"add": {"index": dest_index, "alias": self.ALIAS}}]

        # Remove old alias if it exists
        try:
            existing = await self.client.indices.get_alias(name=self.ALIAS)
            for idx in existing:
                actions.insert(0, {"remove": {"index": idx, "alias": self.ALIAS}})
        except Exception:
            pass  # Alias doesn't exist yet

        await self.client.indices.update_aliases(body={"actions": actions})
        logger.info(f"✓ Alias '{self.ALIAS}' → '{dest_index}'")

    async def rollback(self) -> None:
        """Switch alias back to old index."""
        actions = []

        # Remove alias from new indices
        for provider in self.PROVIDERS:
            idx = self._new_index(provider)
            if await self.client.indices.exists(index=idx):
                actions.append({"remove": {"index": idx, "alias": self.ALIAS}})

        # Add alias to old index
        if await self.client.indices.exists(index=self.OLD_INDEX):
            actions.append({"add": {"index": self.OLD_INDEX, "alias": self.ALIAS}})

        if actions:
            try:
                await self.client.indices.update_aliases(body={"actions": actions})
                logger.info(f"✓ Rolled back alias '{self.ALIAS}' → '{self.OLD_INDEX}'")
            except Exception as e:
                logger.error(f"Rollback failed: {e}")
        else:
            logger.warning("Nothing to rollback")

    async def close(self):
        await self.client.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Migrate OpenSearch indices for text2DSL")
    parser.add_argument("--host", default="localhost", help="OpenSearch host")
    parser.add_argument("--port", type=int, default=9200, help="OpenSearch port")
    parser.add_argument("--username", default=None, help="OpenSearch username")
    parser.add_argument("--password", default=None, help="OpenSearch password")
    parser.add_argument("--ssl", action="store_true", help="Use SSL")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, no changes")
    parser.add_argument("--create-aliases", action="store_true", help="Create index aliases after migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback alias to old index")
    return parser.parse_args()


async def main():
    args = parse_args()
    migration = IndexMigration(
        host=args.host, port=args.port,
        username=args.username, password=args.password,
        use_ssl=args.ssl,
    )

    try:
        if args.rollback:
            await migration.rollback()
            return

        # Step 1: Create new indices
        logger.info("=== Step 1: Create new indices ===")
        await migration.create_new_indices(dry_run=args.dry_run)

        # Step 2: Reindex data
        logger.info("\n=== Step 2: Reindex data ===")
        await migration.reindex_data(dry_run=args.dry_run)

        # Step 3: Validate
        logger.info("\n=== Step 3: Validate ===")
        valid = await migration.validate()

        # Step 4: Create aliases (optional)
        if args.create_aliases:
            logger.info("\n=== Step 4: Create aliases ===")
            await migration.create_aliases(dry_run=args.dry_run)

        if valid or args.dry_run:
            logger.info("\n✓ Migration completed successfully")
        else:
            logger.error("\n✗ Migration validation failed - consider rollback")
            sys.exit(1)

    finally:
        await migration.close()


if __name__ == "__main__":
    asyncio.run(main())
