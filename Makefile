.PHONY: docker-up docker-down docker-logs docker-reset docker-ps

docker-up:
	docker compose -f docker/docker-compose.yml up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@docker compose -f docker/docker-compose.yml ps

docker-down:
	docker compose -f docker/docker-compose.yml down

docker-logs:
	docker compose -f docker/docker-compose.yml logs -f

docker-reset:
	docker compose -f docker/docker-compose.yml down -v
	docker compose -f docker/docker-compose.yml up -d

docker-ps:
	docker compose -f docker/docker-compose.yml ps
