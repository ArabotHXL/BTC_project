#!/bin/bash

# Application Management Script
# Simple script to start, stop, restart, and check status of the Flask application

APP_NAME="Bitcoin Mining Calculator"
APP_PORT=5001
APP_PID_FILE="/tmp/bitcoin_mining_calc.pid"
APP_LOG_FILE="/tmp/bitcoin_mining_calc.log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if conda is available
check_conda() {
    if ! command -v conda &> /dev/null; then
        print_error "Conda is not installed or not in PATH"
        print_info "Please install conda or add it to your PATH"
        exit 1
    fi
}

# Function to activate snakeenv
activate_snakeenv() {
    print_info "Activating snakeenv virtual environment..."
    source "$(conda info --base)/etc/profile.d/conda.sh"
    if conda activate snakeenv 2>/dev/null; then
        print_success "snakeenv activated"
        return 0
    else
        print_error "Failed to activate snakeenv"
        print_info "Please make sure snakeenv is created: conda create -n snakeenv python=3.9"
        exit 1
    fi
}

# Function to check if app is running
is_running() {
    if [ -f "$APP_PID_FILE" ]; then
        PID=$(cat "$APP_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$APP_PID_FILE"
            return 1
        fi
    fi
    
    # Also check by port
    if lsof -ti:$APP_PORT > /dev/null 2>&1; then
        PID=$(lsof -ti:$APP_PORT | head -1)
        echo "$PID" > "$APP_PID_FILE"
        return 0
    fi
    
    return 1
}

# Function to get PID
get_pid() {
    if [ -f "$APP_PID_FILE" ]; then
        PID=$(cat "$APP_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "$PID"
            return 0
        fi
    fi
    
    # Check by port
    PID=$(lsof -ti:$APP_PORT 2>/dev/null | head -1)
    if [ -n "$PID" ]; then
        echo "$PID" > "$APP_PID_FILE"
        echo "$PID"
        return 0
    fi
    
    return 1
}

# Function to start the application
start_app() {
    if is_running; then
        PID=$(get_pid)
        print_warning "Application is already running (PID: $PID)"
        print_info "Use './manage_app.sh restart' to restart it"
        return 1
    fi
    
    print_info "Starting $APP_NAME..."
    
    # Check conda
    check_conda
    
    # Change to script directory
    cd "$SCRIPT_DIR" || exit 1
    
    # Activate snakeenv
    activate_snakeenv
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Make sure you have set up your environment variables."
    fi
    
    # Start the application in background
    print_info "Starting application on port $APP_PORT..."
    nohup python main.py > "$APP_LOG_FILE" 2>&1 &
    APP_PID=$!
    echo "$APP_PID" > "$APP_PID_FILE"
    
    # Wait a moment and check if it started
    sleep 3
    
    if is_running; then
        print_success "Application started successfully!"
        print_info "PID: $APP_PID"
        print_info "Port: $APP_PORT"
        print_info "Log file: $APP_LOG_FILE"
        print_info ""
        print_info "Access the application at: http://localhost:$APP_PORT"
        print_info "View logs: tail -f $APP_LOG_FILE"
    else
        print_error "Application failed to start"
        print_info "Check the log file: $APP_LOG_FILE"
        tail -20 "$APP_LOG_FILE"
        rm -f "$APP_PID_FILE"
        return 1
    fi
}

# Function to stop the application
stop_app() {
    if ! is_running; then
        print_warning "Application is not running"
        return 1
    fi
    
    PID=$(get_pid)
    print_info "Stopping application (PID: $PID)..."
    
    # Try graceful shutdown first
    kill "$PID" 2>/dev/null
    
    # Wait up to 5 seconds
    for i in {1..5}; do
        if ! is_running; then
            print_success "Application stopped successfully"
            rm -f "$APP_PID_FILE"
            return 0
        fi
        sleep 1
    done
    
    # Force kill if still running
    if is_running; then
        print_warning "Application didn't stop gracefully, forcing shutdown..."
        kill -9 "$PID" 2>/dev/null
        sleep 1
        
        if ! is_running; then
            print_success "Application force-stopped"
            rm -f "$APP_PID_FILE"
        else
            print_error "Failed to stop application"
            return 1
        fi
    fi
}

# Function to restart the application
restart_app() {
    print_info "Restarting application..."
    stop_app
    sleep 2
    start_app
}

# Function to check status
status_app() {
    if is_running; then
        PID=$(get_pid)
        print_success "Application is running"
        print_info "PID: $PID"
        print_info "Port: $APP_PORT"
        print_info "Log file: $APP_LOG_FILE"
        
        # Check if port is accessible
        if curl -s http://localhost:$APP_PORT/health > /dev/null 2>&1; then
            print_success "Application is responding on port $APP_PORT"
        else
            print_warning "Application is running but not responding on port $APP_PORT"
        fi
        
        print_info ""
        print_info "Access: http://localhost:$APP_PORT"
    else
        print_warning "Application is not running"
        print_info "Use './manage_app.sh start' to start it"
    fi
}

# Function to show logs
show_logs() {
    if [ -f "$APP_LOG_FILE" ]; then
        print_info "Showing last 50 lines of log file..."
        echo ""
        tail -50 "$APP_LOG_FILE"
    else
        print_warning "Log file not found: $APP_LOG_FILE"
    fi
}

# Function to follow logs
follow_logs() {
    if [ -f "$APP_LOG_FILE" ]; then
        print_info "Following log file (Ctrl+C to exit)..."
        tail -f "$APP_LOG_FILE"
    else
        print_warning "Log file not found: $APP_LOG_FILE"
    fi
}

# Function to show help
show_help() {
    echo "Usage: ./manage_app.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start      Start the application"
    echo "  stop       Stop the application"
    echo "  restart    Restart the application"
    echo "  status     Check application status"
    echo "  logs       Show last 50 lines of logs"
    echo "  follow     Follow logs in real-time (Ctrl+C to exit)"
    echo "  help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./manage_app.sh start    # Start the app"
    echo "  ./manage_app.sh status   # Check if running"
    echo "  ./manage_app.sh logs     # View logs"
    echo "  ./manage_app.sh stop     # Stop the app"
}

# Main script logic
case "${1:-help}" in
    start)
        start_app
        ;;
    stop)
        stop_app
        ;;
    restart)
        restart_app
        ;;
    status)
        status_app
        ;;
    logs)
        show_logs
        ;;
    follow)
        follow_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
