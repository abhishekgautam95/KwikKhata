.PHONY: install test lint format typecheck run serve docker-build docker-up clean

install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy .

run:
	python main.py

serve:
	uvicorn app:app --reload

docker-build:
	docker build -t kwikkhata:latest .

docker-up:
	docker-compose up

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .mypy_cache .pytest_cache .ruff_cache dist build *.egg-info htmlcov .coverage
