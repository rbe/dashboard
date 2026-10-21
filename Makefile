# Build and run the dashboard with Podman.
#
# Host requirements: Podman and make only.
# Node.js, npm, pnpm, yarn, and tsc are not required on the host.

IMAGE ?= localhost/dashboard:latest
NAME  ?= dashboard
PORT  ?= 4173

.DEFAULT_GOAL := help
.PHONY: help build run stop

help: ## Show this help
	@echo "Host requirements: Podman and make only. Node.js and TypeScript are not required."
	@echo
	@echo "Targets:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-8s %s\n", $$1, $$2}'
	@echo
	@echo "make run is detached and listens on http://127.0.0.1:$(PORT)."
	@echo "The board file is ./data/dashboard.md (mounted into the container)."
	@echo "Override the port with: make run PORT=9000"

build: ## Build the container image
	podman build -f Containerfile -t $(IMAGE) .

run: build ## Run the app detached (stop it with make stop)
	podman run -d --replace --name $(NAME) \
		-p 127.0.0.1:$(PORT):$(PORT) \
		-e PORT=$(PORT) \
		-e DASHBOARD_FILE=/app/data/dashboard.md \
		-v "$(CURDIR)/data:/app/data:Z" \
		$(IMAGE)
	@echo "Dashboard at http://127.0.0.1:$(PORT)"

stop: ## Stop and remove the detached container
	podman rm --force --ignore $(NAME)
