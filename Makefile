
install:
	pip install -r requirements.txt

.PHONY: build
build:
	COMPOSE_BAKE=true docker-compose build

.PHONY: test
test:
	docker-compose exec web python -m pytest

.PHONY: up
up:
	COMPOSE_BAKE=true docker-compose up $(s)

up-scale:
	docker-compose up --build --scale worker=3

# curl -X POST http://localhost:8004/tasks -H "Content-Type: application/json"
# curl -N http://localhost:8004/tasks/$TASK_ID/progress