# ============================================================================
# Focus Groups — Deployment Makefile
# ============================================================================
# Usage:
#   make deploy-all          Build, push, and deploy everything
#   make local               Run locally with docker compose
#   make test                Run pytest
#
# Override defaults:
#   make deploy-api PROJECT_ID=my-project REGION=europe-west1
# ============================================================================

# ---------------------------------------------------------------------------
# Variables — override on the command line or via environment
# ---------------------------------------------------------------------------
PROJECT_ID   ?= focusgroups-prod
REGION       ?= us-central1
REPO_NAME    ?= focusgroups
SERVICE_API  ?= focusgroups-api
SERVICE_WEB  ?= focusgroups-web
SA_NAME      ?= focusgroups-api
SA_EMAIL     ?= $(SA_NAME)@$(PROJECT_ID).iam.gserviceaccount.com
CLOUD_SQL_INSTANCE ?= $(PROJECT_ID):$(REGION):focusgroups-db

REGISTRY     ?= $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(REPO_NAME)
IMAGE_API    ?= $(REGISTRY)/api
IMAGE_WEB    ?= $(REGISTRY)/web

GIT_SHA      := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Cloud Run settings — API
API_MEMORY   ?= 2Gi
API_CPU      ?= 2
API_TIMEOUT  ?= 300
API_CONCURRENCY ?= 20
API_MIN_INSTANCES ?= 0
API_MAX_INSTANCES ?= 5

# Cloud Run settings — Web
WEB_MEMORY   ?= 256Mi
WEB_CPU      ?= 1
WEB_MIN_INSTANCES ?= 0
WEB_MAX_INSTANCES ?= 3

# Frontend build arg
API_URL      ?= https://$(SERVICE_API)-$(PROJECT_ID).run.app

# Secrets to create in Secret Manager
SECRETS      := pg-password anthropic-api-key fg-api-key

# Required GCP APIs
GCP_APIS     := run.googleapis.com \
                artifactregistry.googleapis.com \
                secretmanager.googleapis.com \
                sqladmin.googleapis.com \
                cloudbuild.googleapis.com

# ============================================================================
# Phony targets
# ============================================================================
.PHONY: build-api build-web push-api push-web deploy-api deploy-web \
        setup-secrets setup-gcp deploy-all local test help

# ============================================================================
# Help (default target)
# ============================================================================
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Build
# ============================================================================
build-api: ## Build backend Docker image tagged for Artifact Registry
	docker build -t $(IMAGE_API):latest -t $(IMAGE_API):$(GIT_SHA) .

build-web: ## Build frontend Docker image tagged for Artifact Registry
	docker build -t $(IMAGE_WEB):latest -t $(IMAGE_WEB):$(GIT_SHA) \
		--build-arg VITE_API_URL=$(API_URL) \
		./frontend

# ============================================================================
# Push
# ============================================================================
push-api: ## Push backend image to Artifact Registry
	docker push $(IMAGE_API):latest
	docker push $(IMAGE_API):$(GIT_SHA)

push-web: ## Push frontend image to Artifact Registry
	docker push $(IMAGE_WEB):latest
	docker push $(IMAGE_WEB):$(GIT_SHA)

# ============================================================================
# Deploy
# ============================================================================
deploy-api: ## Deploy backend to Cloud Run
	gcloud run deploy $(SERVICE_API) \
		--image=$(IMAGE_API):latest \
		--region=$(REGION) \
		--platform=managed \
		--service-account=$(SA_EMAIL) \
		--allow-unauthenticated \
		--memory=$(API_MEMORY) \
		--cpu=$(API_CPU) \
		--timeout=$(API_TIMEOUT) \
		--concurrency=$(API_CONCURRENCY) \
		--min-instances=$(API_MIN_INSTANCES) \
		--max-instances=$(API_MAX_INSTANCES) \
		--add-cloudsql-instances=$(CLOUD_SQL_INSTANCE) \
		--set-env-vars="PG_HOST=/cloudsql/$(CLOUD_SQL_INSTANCE),PG_DB=focusgroups,PG_USER=fg_user,CORS_ORIGINS=https://$(SERVICE_WEB)-$(PROJECT_ID).run.app,LOG_FORMAT=json" \
		--set-secrets="PG_PASSWORD=pg-password:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,FG_API_KEY=fg-api-key:latest" \
		--port=8080 \
		--startup-probe-path=/health \
		--liveness-probe-path=/health

deploy-web: ## Deploy frontend to Cloud Run
	gcloud run deploy $(SERVICE_WEB) \
		--image=$(IMAGE_WEB):latest \
		--region=$(REGION) \
		--platform=managed \
		--allow-unauthenticated \
		--memory=$(WEB_MEMORY) \
		--cpu=$(WEB_CPU) \
		--min-instances=$(WEB_MIN_INSTANCES) \
		--max-instances=$(WEB_MAX_INSTANCES) \
		--port=8080 \
		--startup-probe-path=/health

# ============================================================================
# Secrets
# ============================================================================
setup-secrets: ## Create Secret Manager secrets and grant SA access
	@echo "--- Creating secrets in Secret Manager ---"
	@for secret in $(SECRETS); do \
		echo "Creating secret: $$secret"; \
		gcloud secrets create $$secret --replication-policy=automatic 2>/dev/null || \
			echo "  (already exists)"; \
	done
	@echo ""
	@echo "--- Granting secret access to $(SA_EMAIL) ---"
	@for secret in $(SECRETS); do \
		gcloud secrets add-iam-policy-binding $$secret \
			--member="serviceAccount:$(SA_EMAIL)" \
			--role="roles/secretmanager.secretAccessor" \
			--quiet; \
	done
	@echo ""
	@echo "Secrets created. Set values with:"
	@echo '  echo -n "VALUE" | gcloud secrets versions add SECRET_NAME --data-file=-'

# ============================================================================
# GCP Project Setup
# ============================================================================
setup-gcp: ## Enable APIs, create service account and Artifact Registry repo
	@echo "--- Enabling required GCP APIs ---"
	gcloud services enable $(GCP_APIS)
	@echo ""
	@echo "--- Creating service account: $(SA_NAME) ---"
	gcloud iam service-accounts create $(SA_NAME) \
		--display-name="Focus Groups API" 2>/dev/null || \
		echo "  (already exists)"
	@echo ""
	@echo "--- Granting IAM roles ---"
	gcloud projects add-iam-policy-binding $(PROJECT_ID) \
		--member="serviceAccount:$(SA_EMAIL)" \
		--role="roles/cloudsql.client" --quiet
	gcloud projects add-iam-policy-binding $(PROJECT_ID) \
		--member="serviceAccount:$(SA_EMAIL)" \
		--role="roles/secretmanager.secretAccessor" --quiet
	gcloud projects add-iam-policy-binding $(PROJECT_ID) \
		--member="serviceAccount:$(SA_EMAIL)" \
		--role="roles/storage.objectViewer" --quiet
	@echo ""
	@echo "--- Creating Artifact Registry repository ---"
	gcloud artifacts repositories create $(REPO_NAME) \
		--repository-format=docker \
		--location=$(REGION) 2>/dev/null || \
		echo "  (already exists)"
	@echo ""
	@echo "--- Configuring Docker auth ---"
	gcloud auth configure-docker $(REGION)-docker.pkg.dev --quiet

# ============================================================================
# Composite Targets
# ============================================================================
deploy-all: build-api build-web push-api push-web deploy-api deploy-web ## Build, push, and deploy everything

# ============================================================================
# Local Development
# ============================================================================
local: ## Run locally with docker compose
	docker compose up --build

test: ## Run pytest
	python3 -m pytest tests/
