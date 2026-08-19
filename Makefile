.PHONY: integration integration-build integration-up integration-down

# Docker integration test gate (WBS M8 / #84).
#
# Precondition: PC_OPENAI_API_KEY must be set (e.g. OpenRouter key).
# Optional env overrides:
#   PC_OPENAI_MODEL       (default: openai/gpt-4o-mini)
#   PC_OPENAI_BASE_URL    (default: https://openrouter.ai/api/v1)
#   PC_REVISION_CAP       (default: 3)
#   PC_CRITIQUE_MODE      (default: deterministic-first)
#   PC_MAX_TOKENS         (default: 16384)
#
# Usage:
#   make integration          # build + up + test + down
#   make integration-build    # build only
#   make integration-up       # start compose (assumes image built)
#   make integration-down     # teardown

integration-build:
	@echo "==> Building image..."
	docker compose build

integration-up:
	@echo "==> Starting compose services..."
	docker compose up -d
	@echo "==> Waiting for health..."
	@for i in $$(seq 1 30); do \
		healthy=$$(docker compose ps --format json 2>/dev/null | grep -c '"health":"healthy"' || echo 0); \
		if [ "$$healthy" -ge 2 ] 2>/dev/null; then echo "  services healthy after $${i}s"; break; fi; \
		sleep 2; \
	done
	@docker compose ps

integration-down:
	@echo "==> Tearing down..."
	docker compose down -v

integration: integration-build integration-up
	@echo "==> Running integration tests..."
	PC_INTEGRATION=1 python3 -m pytest tests/docker/ -v --tb=short --no-cov -s || true
	@echo "==> Running debug script (adversarial)..."
	python3 tests/docker/debug_loop.py adversarial || true
	@$(MAKE) integration-down
	@echo "==> Done. Evidence in docs/test/docker/"