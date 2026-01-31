.PHONY: help install dev build preview clean lint format check-deps

help:
	@echo "Text2DSL Frontend - Available Commands"
	@echo ""
	@echo "  make install     - Install dependencies"
	@echo "  make dev         - Start development server"
	@echo "  make build       - Build for production"
	@echo "  make preview     - Preview production build"
	@echo "  make lint        - Run ESLint"
	@echo "  make clean       - Remove build artifacts and dependencies"
	@echo "  make check-deps  - Check for outdated dependencies"
	@echo ""

install:
	@echo "Installing dependencies..."
	npm install

dev:
	@echo "Starting development server..."
	npm run dev

build:
	@echo "Building for production..."
	npm run build

preview:
	@echo "Previewing production build..."
	npm run preview

lint:
	@echo "Running ESLint..."
	npm run lint

format:
	@echo "Formatting code..."
	npx prettier --write "src/**/*.{js,jsx,css}"

clean:
	@echo "Cleaning build artifacts..."
	rm -rf node_modules dist .vite package-lock.json

check-deps:
	@echo "Checking for outdated dependencies..."
	npm outdated

setup: install
	@echo "Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Start backend: cd .. && make run-dev"
	@echo "  2. Start frontend: make dev"
	@echo "  3. Open http://localhost:3000"
