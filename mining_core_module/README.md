# Mining Core Module

A standalone Bitcoin mining profitability calculator and data analysis system.

## Features

- **Mining Calculator**: Real-time profitability calculations for individual miners
- **Batch Calculator**: Process multiple miners simultaneously with CSV import/export
- **Analytics Dashboard**: Technical indicators, market analysis, and historical data
- **API Integration**: CoinWarz API and Bitcoin RPC client for real-time data
- **Report Generation**: Comprehensive mining analysis reports
- **Independent Operation**: No user authentication dependencies

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL database (optional, defaults to SQLite)

### Installation

1. Clone or extract the mining_core_module directory
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables (optional):
   ```bash
   export DATABASE_URL="postgresql://user:password@localhost/mining_core"
   export SESSION_SECRET="your-secret-key"
   export COINWARZ_API_KEY="your-coinwarz-api-key"
   export BITCOIN_RPC_URL="your-bitcoin-rpc-url"
   ```

### Running the Application

#### Development Mode
```bash
python main.py
```

#### Production Mode with Gunicorn
```bash
gunicorn --bind 0.0.0.0:5001 --workers 4 main:app
```

The application will be available at `http://localhost:5001`

## API Endpoints

### Health Check
- `GET /health` - System health status
- `GET /api/info` - API information

### Calculator
- `GET /calculator/` - Calculator interface
- `POST /calculator/api/calculate` - Perform mining calculations
- `GET /calculator/api/miners` - Get available miner models
- `GET /calculator/api/network-data` - Get network statistics

### Batch Calculator
- `GET /batch/` - Batch calculator interface
- `POST /batch/api/batch-calculate` - Process batch calculations
- `POST /batch/api/export/csv` - Export results to CSV
- `POST /batch/api/export/excel` - Export results to Excel
- `GET /batch/api/template/download` - Download CSV template

### Analytics
- `GET /analytics/` - Analytics dashboard
- `GET /analytics/api/dashboard-stats` - Dashboard statistics
- `GET /analytics/api/market-data` - Market data
- `GET /analytics/api/technical-indicators` - Technical indicators
- `POST /analytics/api/collect-data` - Trigger data collection
- `POST /analytics/api/generate-report` - Generate analysis report

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///mining_core.db` |
| `SESSION_SECRET` | Session secret key | `mining-core-dev-key-2025` |
| `DEBUG` | Debug mode | `False` |
| `PORT` | Server port | `5001` |
| `COINWARZ_API_KEY` | CoinWarz API key | - |
| `BITCOIN_RPC_URL` | Bitcoin RPC URL | `https://go.getblock.io/mainnet` |
| `BITCOIN_RPC_USER` | Bitcoin RPC username | - |
| `BITCOIN_RPC_PASSWORD` | Bitcoin RPC password | - |

### Configuration Profiles

- **Development**: Debug enabled, SQLite database
- **Production**: Optimized settings, PostgreSQL recommended
- **Testing**: In-memory database, debug enabled

## Database Models

### Core Models
- `MinerModel`: Mining hardware specifications
- `NetworkSnapshot`: Bitcoin network state snapshots
- `MarketAnalytics`: Market data and metrics
- `TechnicalIndicators`: Technical analysis indicators
- `MiningMetrics`: Mining performance metrics
- `SLAMetrics`: System performance metrics

## Data Sources

### Supported APIs
- **CoinWarz**: Bitcoin network statistics and pricing
- **Bitcoin RPC**: Direct blockchain data access
- **Custom**: Historical data backfill and analysis

### Data Collection
- Real-time network data updates
- Historical data backfill
- Market analytics collection
- Technical indicator calculation

## Performance

### Optimization Features
- Batch processing with worker threads
- Database connection pooling
- Efficient data grouping algorithms
- Memory usage optimization for large datasets
- Caching for frequently accessed data

### Limits
- Batch calculator: Up to 1,000 miners per batch
- API rate limiting: 60 requests per minute
- Database connection pool: 5-15 connections

## Development

### Project Structure
```
mining_core_module/
├── app.py                 # Flask application factory
├── main.py               # Application entry point
├── config.py             # Configuration management
├── models.py             # Database models
├── mining_calculator.py  # Core calculation engine
├── routes/               # Route handlers
├── templates/            # HTML templates
├── static/              # Static assets (CSS, JS)
├── modules/             # Feature modules
├── api/                 # External API clients
└── utils/               # Utility functions
```

### Adding New Features
1. Create route handlers in `routes/`
2. Add templates in `templates/`
3. Update navigation in `templates/base.html`
4. Add static assets in `static/`

### Database Migrations
The application automatically creates tables on startup. For schema changes:
1. Update models in `models.py`
2. Restart the application
3. Tables will be created/updated automatically

## Troubleshooting

### Common Issues

**Port 5001 already in use**
```bash
# Find process using port
lsof -i :5001
# Kill process
kill -9 <PID>
```

**Database connection errors**
- Check DATABASE_URL format
- Ensure database server is running
- Verify credentials and permissions

**Missing API data**
- Check COINWARZ_API_KEY configuration
- Verify network connectivity
- Review logs for API rate limits

### Logging

Logs are written to:
- Console (development mode)
- `logs/mining_core.log` (production mode)

Log levels: DEBUG, INFO, WARNING, ERROR

### Performance Monitoring

Monitor system resources:
```bash
# CPU and memory usage
python -c "import psutil; print(f'CPU: {psutil.cpu_percent()}%, Memory: {psutil.virtual_memory().percent}%')"

# Database connections
grep "database" logs/mining_core.log
```

## Security

### Best Practices
- Use strong SESSION_SECRET in production
- Enable HTTPS in production deployment
- Regularly update dependencies
- Monitor API usage for anomalies
- Backup database regularly

### Rate Limiting
- API endpoints have built-in rate limiting
- Batch operations have size limits
- Database connection pooling prevents overload

## Production Deployment

### Recommended Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set production environment
export FLASK_ENV=production
export DATABASE_URL="postgresql://user:pass@localhost/mining_core"
export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"

# Start with Gunicorn
gunicorn --bind 0.0.0.0:5001 --workers 4 --timeout 300 main:app
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5001
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "main:app"]
```

## License

This is an independent mining analysis module extracted from a larger system.

## Support

For issues and questions:
1. Check the logs for error details
2. Verify configuration settings
3. Review the API documentation
4. Check database connectivity

## Version History

- **v1.0.0**: Initial standalone release
  - Core mining calculator
  - Batch processing
  - Analytics dashboard
  - API integration
  - Independent operation