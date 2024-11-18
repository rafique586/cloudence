# GCP SRE Agent

An AI-powered SRE agent for GCP monitoring and incident management.

## Features

- 🤖 AI-powered incident management
- 📊 Real-time monitoring dashboard
- 🔍 Natural language query processing
- 🚨 Intelligent alerting system
- 📈 Performance metrics visualization
- 💰 Cost optimization insights
- 🛡️ Security monitoring

## Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/gcp-sre-agent.git
cd gcp-sre-agent
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your GCP credentials and configuration
```

3. **Install dependencies**
```bash
# Backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Frontend
cd src/ui
npm install
```

4. **Run with Docker Compose**
```bash
docker-compose up
```

5. **Access the services**
- Dashboard UI: http://localhost:3000
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Configuration

The agent can be configured through `src/config/config.yaml`. Key configuration options include:

- GCP project settings
- Monitoring intervals
- Alert thresholds
- Dashboard preferences
- Regional settings

## Development

1. **Run tests**
```bash
pytest tests/
```

2. **Format code**
```bash
black src/ tests/
isort src/ tests/
```

3. **Run linters**
```bash
flake8 src/ tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.