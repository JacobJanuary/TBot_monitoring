# Fox Crypto Trading Bot Monitor v2.0

A real-time terminal UI for monitoring cryptocurrency trading bot positions, events, and statistics.

## Features

- **Real-time Position Monitoring**: View all active positions with current prices and PnL
- **Trailing Stop Tracking**: Visual indicators for trailing stop status
- **Event Stream**: Live feed of all system events
- **Statistics Dashboard**: Hourly performance metrics and win rates
- **Alerts**: Warnings for old positions and high exposure
- **Performance**: Async architecture with sub-second updates

## Screenshots

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     FOX CRYPTO TRADING BOT MONITOR v2.0                              │
│  Status: ● RUNNING  │  Uptime: 14h 32m  │  Active: 72/150  │  Exposure: $14,400    │
├────────────────────────────────────────┬────────────────────────────────────────┤
│         ACTIVE POSITIONS (72)          │      STATISTICS (Last 1h)              │
│ ┌──────────────────────────────────┐  │  Opened:      18 positions            │
│ │Symbol    Side  Entry    Current  │  │  Closed:       5 positions            │
│ │BTCUSDT  LONG  67890.0  68420.0   │  │  TS Active:    8 positions            │
│ │Binance  13h            NOW    ✓TS│  │  Win Rate:    60.0%                   │
│ └──────────────────────────────────┘  │  Total PnL:   +$127.50                │
├────────────────────────────────────────┴────────────────────────────────────────┤
│                         EVENT STREAM (Real-time)                                     │
│ 02:15:33 [POSITION_CREATED] BTCUSDT LONG @67890.0 size:0.0029                  │
│ 02:16:45 [TS_ACTIVATED] ETHUSDT trailing stop activated at +1.5% profit        │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.10 or higher
- PostgreSQL database with monitoring schema
- Access to `fox_crypto` database (or configured database)

## Installation

1. **Clone or navigate to the project**:
   ```bash
   cd /Users/evgeniyyanvarskiy/PycharmProjects/TBot_monitoring/monitor_ui
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure database** (optional):
   Create a `.env` file in the project root:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=fox_crypto
   DB_USER=evgeniyyanvarskiy
   DB_PASSWORD=
   ```

## Usage

### Basic Usage

Run with default settings:
```bash
python main.py
```

### Advanced Options

Connect to remote database:
```bash
python main.py --db-host remote.server.com --db-user trader --db-password secret
```

Enable debug logging:
```bash
python main.py --log-level DEBUG --log-file monitor.log
```

Custom database configuration:
```bash
python main.py --db-name my_trading_db --db-port 5433
```

### Command Line Arguments

```
--db-host       Database host (default: localhost)
--db-port       Database port (default: 5432)
--db-name       Database name (default: fox_crypto)
--db-user       Database user
--db-password   Database password

--log-level     Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
--log-file      Log file path

--pool-min      Minimum connection pool size (default: 2)
--pool-max      Maximum connection pool size (default: 5)
```

### Keyboard Shortcuts

- `Q` - Quit application
- `R` - Force refresh all data
- `C` - Clear event stream
- `P` - Pause/resume updates
- `↑/↓` - Navigate positions table
- `Ctrl+C` - Emergency exit

## Project Structure

```
monitor_ui/
├── main.py                      # Entry point
├── config.py                    # Configuration
├── requirements.txt             # Dependencies
├── README.md                    # Documentation
│
├── database/
│   ├── connection.py           # DB connection pool
│   ├── queries.py              # SQL queries
│   └── models.py               # Pydantic models
│
├── ui/
│   ├── app.py                  # Main Textual app
│   ├── styles.tcss             # CSS styling
│   └── widgets/
│       ├── header.py           # Status header
│       ├── positions_table.py  # Positions display
│       ├── events_stream.py    # Event log
│       └── statistics.py       # Stats panel
│
└── services/
    └── data_fetcher.py         # Async data polling
```

## Database Schema

The monitor expects the following PostgreSQL schema:

### Required Tables

- `monitoring.positions` - Trading positions
- `monitoring.events` - System events
- `monitoring.trailing_stop_state` - Trailing stop data

### Example Schema

```sql
-- Positions table
CREATE TABLE monitoring.positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    exchange VARCHAR NOT NULL,
    side VARCHAR NOT NULL,
    quantity NUMERIC NOT NULL,
    entry_price NUMERIC NOT NULL,
    current_price NUMERIC,
    stop_loss_price NUMERIC,
    unrealized_pnl NUMERIC,
    status VARCHAR DEFAULT 'active',
    opened_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP,
    has_trailing_stop BOOLEAN DEFAULT FALSE,
    has_stop_loss BOOLEAN DEFAULT FALSE
);

-- Events table
CREATE TABLE monitoring.events (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    event_type VARCHAR NOT NULL,
    event_data JSONB,
    symbol VARCHAR,
    exchange VARCHAR,
    position_id INTEGER
);
```

## Performance

Target metrics:
- **Startup time**: < 2 seconds
- **Position updates**: < 100ms
- **Event updates**: < 50ms
- **Memory usage**: < 100MB
- **CPU usage**: < 5%

## Troubleshooting

### Database Connection Issues

**Problem**: Cannot connect to database
```
Solution:
1. Check PostgreSQL is running: pg_isready
2. Verify connection settings in .env or command line
3. Test connection: psql -h localhost -U username -d fox_crypto
```

### No Data Displayed

**Problem**: UI shows but no positions/events
```
Solution:
1. Check database has data: SELECT COUNT(*) FROM monitoring.positions;
2. Verify schema name is 'monitoring'
3. Check user has SELECT permissions
```

### High CPU Usage

**Problem**: Monitor using too much CPU
```
Solution:
1. Increase update intervals in config.py or .env
2. Reduce connection pool size
3. Check for slow queries in PostgreSQL logs
```

## Development

### Running Tests

```bash
pytest tests/
```

### Adding New Widgets

1. Create widget in `ui/widgets/`
2. Import in `ui/app.py`
3. Add to `compose()` method
4. Style in `ui/styles.tcss`

### Adding New Queries

1. Add SQL to `database/queries.py`
2. Create model in `database/models.py` if needed
3. Add fetch method to `services/data_fetcher.py`
4. Call from UI update method

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## License

This project is part of the Fox Crypto Trading Bot system.

## Support

For issues and questions:
- Check troubleshooting section
- Review database schema requirements
- Check logs with `--log-level DEBUG`

## Roadmap

### Completed ✅
- [x] Real-time position monitoring
- [x] Event stream display
- [x] Statistics panel
- [x] Trailing stop indicators
- [x] Keyboard shortcuts

### Planned 🚧
- [ ] Historical PnL charts
- [ ] Position detail modal
- [ ] Advanced filtering
- [ ] Export to CSV
- [ ] Multi-page navigation
- [ ] Alert notifications
- [ ] Performance graphs

---

**Version**: 2.0
**Last Updated**: 2025
**Author**: Fox Crypto Team
