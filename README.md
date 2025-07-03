# VPN Telegram Bot

A Telegram bot for managing VPN configurations through 3x-ui panel API. The bot generates VLESS+Reality VPN configurations and provides QR codes for easy mobile setup.

## Features

- **Multi-server support**: Choose between Netherlands and France servers
- **Rate limiting**: Maximum 3 requests per hour per user
- **VLESS+Reality protocol**: Modern VPN protocol with Reality security
- **QR code generation**: Easy mobile client setup
- **No expiration**: Unlimited validity period for VPN clients
- **Auto-activation**: Clients are enabled immediately upon creation
- **Docker deployment**: Production-ready containerized deployment

## Tech Stack

- **Language**: Python 3.9
- **Dependencies**: requests, qrcode[pil], Pillow, python-dotenv
- **VPN Protocol**: VLESS with Reality security
- **API Integration**: 3x-ui VPN panel
- **Deployment**: Docker with Swarm support

## Quick Start

### Development Mode

```bash
# Clone the repository
git clone <repository-url>
cd vpn_bot

# Install dependencies
pip install -r requirements.txt

# Run in debug mode
./run_debug.sh
```

### Production Deployment

```bash
# Deploy with Docker Swarm
./run.sh

# Update deployment
./update.sh
```

## Configuration

The bot supports two configuration modes:

### 1. Docker Secrets (Production)
Create the following secrets:
- `TELEGRAM_BOT_TOKEN`: Bot authentication token
- `API_URL`: JSON with server mapping `{"servers":{"nl":"https://nl.example.com","fr":"https://fr.example.com"},"default":"nl"}`
- `API_USERNAME`: 3x-ui panel username
- `API_PASSWORD`: 3x-ui panel password

### 2. Command Line Arguments (Debug)
```bash
python3 main.py --debug \
  --token "YOUR_BOT_TOKEN" \
  --servers '{"servers":{"nl":"https://nl.example.com","fr":"https://fr.example.com"},"default":"nl"}' \
  --username "api_user" \
  --password "api_pass"
```

## Architecture

### Core Components

- `main.py` - Entry point, bot lifecycle and message routing
- `config.py` - Global configuration and state management
- `core.py` - Telegram API wrapper functions
- `vpn.py` - VPN account management and 3x-ui API integration
- `message_handler.py` - Message processing and command handling
- `ui.py` - User interface components and keyboard layouts

### Key Features

- **Long-polling**: 100-second timeout for efficient message retrieval
- **Rate limiting**: Tracks user requests with timestamps
- **Multi-server**: Dynamic server switching based on country selection
- **Security**: No sensitive data logging, proper secret management

## API Integration

The bot integrates with 3x-ui panel API endpoints:
- `POST /login` - Authentication
- `POST /panel/api/inbounds/addClient` - Add VPN client
- `POST /panel/api/inbounds/clientIps/{email}` - Get client statistics

## User Flow

1. User starts bot with `/start`
2. User clicks "Get VPN" button
3. Bot shows country selection (🇳🇱 Netherlands, 🇫🇷 France)
4. User selects country
5. Bot creates VPN client and generates configuration
6. User receives QR code and VLESS URL

## Security Features

- No hardcoded credentials
- Docker secrets for production
- Rate limiting (3 requests/hour)
- Safe logging without API responses
- Automatic cleanup of expired user data

## Development

### Project Structure
```
vpn_bot/
├── main.py              # Entry point
├── config.py            # Configuration
├── core.py              # Telegram API
├── vpn.py               # VPN management
├── message_handler.py   # Message processing
├── ui.py                # User interface
├── platform_help.py     # Platform instructions
├── requirements.txt     # Dependencies
├── Dockerfile           # Container config
├── docker-compose.yml   # Compose config
├── run.sh              # Production script
├── run_debug.sh        # Development script
└── update.sh           # Update script
```

### Commands

```bash
# Build Docker image
docker-compose build

# Run with docker-compose
docker-compose up -d

# View logs
docker logs -f config_bot

# Run tests (if available)
# No test framework configured
```

## License

This project is provided as-is for educational and personal use.

## Support

For issues and questions, please check the bot logs and ensure proper configuration of:
- Telegram bot token
- 3x-ui panel access
- Server connectivity