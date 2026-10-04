install:
	pip install -r backend/requirements.txt
	cd .. && pnpm install

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	pnpm dev

seed:
	cd backend && python -m app.seed.seed

test-backend:
	cd backend && python -m pytest tests -q

docker-up:
	docker compose up --build
