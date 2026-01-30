#!/bin/bash
set -e

# PyPI Publishing Script for hyperliquid-python-sdk
# PyPI username: felixchen1998

echo "=== Hyperliquid Python SDK Publishing Script ==="

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Error: Poetry is not installed. Please install it first:"
    echo "  curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Parse arguments
DRY_RUN=false
SKIP_TESTS=false
BUMP_VERSION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --bump)
            BUMP_VERSION="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: ./publish.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run      Build but don't upload to PyPI"
            echo "  --skip-tests   Skip running tests before publishing"
            echo "  --bump TYPE    Bump version before publishing (patch|minor|major)"
            echo "  -h, --help     Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./publish.sh                    # Build and publish current version"
            echo "  ./publish.sh --bump patch       # Bump patch version and publish"
            echo "  ./publish.sh --dry-run          # Build only, don't upload"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Get current version
CURRENT_VERSION=$(poetry version -s)
echo "Current version: ${CURRENT_VERSION}"

# Bump version if requested
if [ -n "$BUMP_VERSION" ]; then
    echo "Bumping $BUMP_VERSION version..."
    poetry version "$BUMP_VERSION"
    NEW_VERSION=$(poetry version -s)
    echo "New version: ${NEW_VERSION}"
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "Warning: You have uncommitted changes"
    git status --short
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run tests unless skipped
if [ "$SKIP_TESTS" = false ]; then
    echo "Running tests..."
    poetry run pytest --cov-report=term-missing --cov=hyperliquid -x || {
        echo "Tests failed! Aborting publish."
        exit 1
    }
    echo "Tests passed!"
else
    echo "Skipping tests (--skip-tests flag set)"
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info

# Build the package
echo "Building package..."
poetry build

# Show what was built
echo "Built packages:"
ls -la dist/

# Load .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Publish to PyPI
if [ "$DRY_RUN" = true ]; then
    echo "Dry run mode - skipping upload to PyPI"
    echo "Package built successfully! To publish manually, run:"
    echo "  poetry publish"
else
    echo "Publishing to PyPI..."

    if [ -n "$PYPI_TOKEN" ]; then
        echo "Using PYPI_TOKEN from environment"
        poetry publish --username __token__ --password "$PYPI_TOKEN"
    else
        echo "No PYPI_TOKEN found. You will be prompted for credentials."
        poetry publish
    fi

    FINAL_VERSION=$(poetry version -s)
    echo "Successfully published hyperliquid ${FINAL_VERSION} to PyPI!"
    echo "View at: https://pypi.org/project/hyperliquid/${FINAL_VERSION}/"
fi

echo "Done!"
