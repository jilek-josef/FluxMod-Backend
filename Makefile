IMAGE_NAME ?= fluxmod-backend
CONTAINER_NAME ?= fluxmod-backend-dev
DOCKERFILE ?= Dockerfile
PORT ?= 8000
ENV_FILE ?= .env

ENV_FILE_OPT := $(if $(wildcard $(ENV_FILE)),--env-file $(ENV_FILE),)

build:
	docker build -f $(DOCKERFILE) -t $(IMAGE_NAME) .

run:
	-@docker rm -f $(CONTAINER_NAME) >/dev/null 2>&1 || true
	docker run --rm \
		--name $(CONTAINER_NAME) \
		-p $(PORT):8000 \
		$(ENV_FILE_OPT) \
		$(IMAGE_NAME) \
		python -m gunicorn 'api2:create_app()' --bind 0.0.0.0:8000 --workers 1
