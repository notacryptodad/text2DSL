#!/bin/bash

# Verification script for Playwright E2E test setup
# This script checks that all components are in place

echo "🔍 Verifying Playwright E2E Test Setup"
echo "========================================"
echo ""

# Check if we're in the frontend directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Not in frontend directory"
    exit 1
fi

echo "✅ In frontend directory"

# Check if Playwright is installed
if ! npm list @playwright/test > /dev/null 2>&1; then
    echo "❌ Error: @playwright/test not installed"
    exit 1
fi

echo "✅ Playwright package installed"

# Check Playwright version
VERSION=$(npx playwright --version)
echo "✅ Playwright version: $VERSION"

# Check if playwright.config.js exists
if [ ! -f "playwright.config.js" ]; then
    echo "❌ Error: playwright.config.js not found"
    exit 1
fi

echo "✅ playwright.config.js exists"

# Check if e2e directory exists
if [ ! -d "e2e" ]; then
    echo "❌ Error: e2e directory not found"
    exit 1
fi

echo "✅ e2e directory exists"

# Check for required directories
REQUIRED_DIRS=("e2e/.auth" "e2e/fixtures" "e2e/pages")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "❌ Error: $dir not found"
        exit 1
    fi
    echo "✅ $dir exists"
done

# Check for global setup
if [ ! -f "e2e/global-setup.js" ]; then
    echo "❌ Error: e2e/global-setup.js not found"
    exit 1
fi

echo "✅ global-setup.js exists"

# Check for fixtures
if [ ! -f "e2e/fixtures/auth.fixture.js" ]; then
    echo "❌ Error: e2e/fixtures/auth.fixture.js not found"
    exit 1
fi

echo "✅ auth.fixture.js exists"

# Check for Page Object Models
REQUIRED_POMS=("LoginPage.js" "ChatPage.js" "ReviewPage.js" "AdminDashboardPage.js")
for pom in "${REQUIRED_POMS[@]}"; do
    if [ ! -f "e2e/pages/$pom" ]; then
        echo "❌ Error: e2e/pages/$pom not found"
        exit 1
    fi
    echo "✅ $pom exists"
done

# Check for test scenarios
REQUIRED_SPECS=(
    "scenario-0-user-management.spec.js"
    "scenario-1-admin-setup.spec.js"
    "scenario-2-schema-annotation.spec.js"
    "scenario-3-query-generation.spec.js"
    "scenario-4-review-queue.spec.js"
    "scenario-5-feedback.spec.js"
)

for spec in "${REQUIRED_SPECS[@]}"; do
    if [ ! -f "e2e/$spec" ]; then
        echo "❌ Error: e2e/$spec not found"
        exit 1
    fi
    echo "✅ $spec exists"
done

# Check package.json scripts
if ! grep -q "test:e2e" package.json; then
    echo "❌ Error: test:e2e script not found in package.json"
    exit 1
fi

echo "✅ npm scripts configured"

# Check .gitignore
if ! grep -q "e2e/.auth" .gitignore; then
    echo "⚠️  Warning: e2e/.auth/ not in .gitignore"
else
    echo "✅ Test artifacts in .gitignore"
fi

echo ""
echo "=========================================="
echo "✅ All checks passed!"
echo ""
echo "Next steps:"
echo "1. Ensure backend and frontend servers can start:"
echo "   - Backend: cd .. && uvicorn src.text2x.api.app:app --port 8000"
echo "   - Frontend: npm run dev -- --port 5173"
echo ""
echo "2. Run global setup to authenticate test users:"
echo "   node e2e/global-setup.js"
echo ""
echo "3. Run a single test to verify:"
echo "   npx playwright test scenario-0-user-management --headed"
echo ""
echo "4. Run all tests:"
echo "   npm run test:e2e"
echo ""
echo "5. View test report:"
echo "   npm run test:e2e:report"
echo ""
