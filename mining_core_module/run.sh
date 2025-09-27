#!/bin/bash

# Mining Core Module - Run Script
# Standalone Bitcoin mining calculator and analytics system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
MODE="development"
PORT=5001
WORKERS=4
HOST="0.0.0.0"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}   Mining Core Module${NC}"
    echo -e "${BLUE}   Bitcoin Mining Calculator${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -m, --mode MODE      Run mode: development|production|testing (default: development)"
    echo "  -p, --port PORT      Port to bind (default: 5001)"
    echo "  -w, --workers NUM    Number of workers for production (default: 4)"
    echo "  -h, --host HOST      Host to bind (default: 0.0.0.0)"
    echo "  --install           Install dependencies"
    echo "  --check             Check system requirements"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                          # Start in development mode"
    echo "  $0 -m production -w 8       # Start in production with 8 workers"
    echo "  $0 --install                # Install dependencies"
    echo "  $0 --check                  # Check system status"
}

# Function to check Python version
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_status "Python version: $PYTHON_VERSION"
    
    if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
        print_error "Python 3.8+ is required, found $PYTHON_VERSION"
        exit 1
    fi
}

# Function to check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found"
        exit 1
    fi
    
    # Check if virtual environment is recommended
    if [ -z "$VIRTUAL_ENV" ]; then
        print_warning "Running outside virtual environment (not recommended)"
    else
        print_status "Virtual environment: $VIRTUAL_ENV"
    fi
    
    # Try to import key modules
    python3 -c "import flask, sqlalchemy, requests" 2>/dev/null || {
        print_error "Required dependencies not installed. Run: $0 --install"
        exit 1
    }
    
    print_status "Dependencies check passed"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found"
        exit 1
    fi
    
    pip3 install -r requirements.txt
    print_status "Dependencies installed successfully"
}

# Function to check database connectivity
check_database() {
    print_status "Checking database connectivity..."
    
    python3 -c "
import os
from sqlalchemy import create_engine, text

db_url = os.environ.get('DATABASE_URL', 'sqlite:///mining_core.db')
try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('Database connection: OK')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
" || {
        print_error "Database connectivity check failed"
        exit 1
    }
}

# Function to check system status
check_system() {
    print_header
    check_python
    check_dependencies
    check_database
    
    print_status "System check completed successfully!"
    
    # Show environment info
    echo ""
    echo "Environment Information:"
    echo "  Mode: ${FLASK_ENV:-development}"
    echo "  Port: ${PORT:-5001}"
    echo "  Database: ${DATABASE_URL:-sqlite:///mining_core.db}"
    echo "  Debug: ${DEBUG:-False}"
    
    # Show available endpoints
    echo ""
    echo "Available Endpoints:"
    echo "  Health Check: http://$HOST:$PORT/health"
    echo "  Calculator: http://$HOST:$PORT/calculator/"
    echo "  Batch Calculator: http://$HOST:$PORT/batch/"
    echo "  Analytics: http://$HOST:$PORT/analytics/"
    echo "  API Info: http://$HOST:$PORT/api/info"
}

# Function to set environment variables
set_environment() {
    export FLASK_ENV="$MODE"
    export PORT="$PORT"
    export HOST="$HOST"
    
    # Set default session secret if not provided
    if [ -z "$SESSION_SECRET" ]; then
        export SESSION_SECRET="mining-core-dev-key-2025"
        if [ "$MODE" = "production" ]; then
            print_warning "Using default SESSION_SECRET. Set a secure one for production!"
        fi
    fi
    
    # Set debug mode
    if [ "$MODE" = "development" ]; then
        export DEBUG="True"
    else
        export DEBUG="False"
    fi
    
    print_status "Environment configured for $MODE mode"
}

# Function to start development server
start_development() {
    print_status "Starting development server on $HOST:$PORT"
    python3 main.py
}

# Function to start production server
start_production() {
    if ! command -v gunicorn &> /dev/null; then
        print_error "Gunicorn not found. Install with: pip install gunicorn"
        exit 1
    fi
    
    print_status "Starting production server with $WORKERS workers on $HOST:$PORT"
    
    gunicorn \
        --bind "$HOST:$PORT" \
        --workers "$WORKERS" \
        --timeout 300 \
        --worker-class sync \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --preload \
        --access-logfile - \
        --error-logfile - \
        main:app
}

# Function to start testing server
start_testing() {
    print_status "Starting testing server on $HOST:$PORT"
    export TESTING="True"
    python3 main.py
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -w|--workers)
            WORKERS="$2"
            shift 2
            ;;
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        --install)
            install_dependencies
            exit 0
            ;;
        --check)
            check_system
            exit 0
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate mode
case $MODE in
    development|production|testing)
        ;;
    *)
        print_error "Invalid mode: $MODE. Must be development, production, or testing"
        exit 1
        ;;
esac

# Main execution
print_header

# Check system requirements
check_python
check_dependencies

# Set environment
set_environment

# Create logs directory for production
if [ "$MODE" = "production" ]; then
    mkdir -p logs
fi

# Check database
check_database

print_status "Starting Mining Core Module in $MODE mode..."

# Start appropriate server
case $MODE in
    development)
        start_development
        ;;
    production)
        start_production
        ;;
    testing)
        start_testing
        ;;
esac