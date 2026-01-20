# Adobe Design Defenders (BrandflowAI)

An intelligent Adobe Express Add-on that helps designers create brand-compliant designs with AI-powered assistance, compliance checking, and seamless integration with popular collaboration tools.

## 🎯 Features

### Core Functionality
- **AI-Powered Design Generation**: Generate designs from text descriptions using Google Gemini AI
- **Brand Compliance Checker**: Automatically verify designs against brand guidelines
- **Copyright Checker**: Detect potential copyright issues in generated images
- **Brand Image Management**: Upload and manage brand images for consistent design
- **Brand Guidelines Integration**: Upload PDF guidelines for automated compliance checking
- **Post Analysis**: Analyze past social media posts to understand what works best

### Integrations
- **LinkedIn**: Direct posting to LinkedIn
- **Slack**: Send notifications and designs to Slack channels
- **Jira**: Create team notifications and track design tasks

## 📁 Project Structure

```
Adobe-Design-Defenders/
├── backend/              # FastAPI backend server
│   ├── main.py          # Main API server with endpoints
│   ├── compliance.py    # Compliance checking module
│   ├── chatbot.py       # AI chatbot integration
│   ├── image_generator.py # Image generation logic
│   ├── config.json.example # LinkedIn config template
│   └── jira_config.json.example # Jira config template
├── src/                  # Adobe Express Add-on source files
│   ├── index.html       # Main UI
│   ├── index.js         # Frontend logic
│   ├── manifest.json    # Add-on manifest
│   └── styles.css       # Styling
├── dist/                 # Built/distributed add-on files
└── uploads/              # User uploads (brand images, guidelines, generated content)
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Node.js (for add-on development)
- Adobe Express Developer Account
- API Keys:
  - Google Gemini API
  - LinkedIn API (optional, for LinkedIn integration)
  - Slack API (optional, for Slack integration)
  - Jira API (optional, for Jira integration)
  - SerpAPI (for copyright checking)
  - ImgBB API (for image hosting)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Aakanksha13-cloud/Adobe-Design-Defenders.git
   cd Adobe-Design-Defenders
   ```

2. **Set up the backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Configure API keys**
   ```bash
   # Copy example config files
   cp config.json.example config.json
   cp jira_config.json.example jira_config.json
   
   # Edit config.json with your LinkedIn credentials
   # Edit jira_config.json with your Jira credentials
   # Edit backend/main.py with your Slack token
   ```

4. **Start the backend server**
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```

5. **Load the add-on in Adobe Express**
   - Open Adobe Express
   - Go to Add-ons → Develop Add-ons
   - Load the `src` directory or use the built `dist` directory

## 🔧 Configuration

### Backend Configuration

#### LinkedIn Integration (`backend/config.json`)
```json
{
  "access_token": "YOUR_ACCESS_TOKEN_HERE",
  "client_id": "YOUR_CLIENT_ID_HERE",
  "client_secret": "YOUR_CLIENT_SECRET_HERE",
  "redirect_uri": "http://localhost:8000/callback"
}
```

#### Jira Integration (`backend/jira_config.json`)
```json
{
  "jira_url": "https://your-domain.atlassian.net",
  "jira_email": "YOUR_EMAIL_HERE",
  "jira_api_token": "YOUR_API_TOKEN_HERE",
  "jira_project_key": "YOUR_PROJECT_KEY"
}
```

#### Slack Integration (`backend/main.py`)
Update the `SLACK_TOKEN` variable with your Slack bot token.

### API Keys

The following API keys need to be configured in the respective files:

- **Google Gemini API**: Set in `backend/compliance.py` and `backend/chatbot.py`
- **SerpAPI**: Set in `backend/compliance.py` for copyright checking
- **ImgBB API**: Set in `backend/compliance.py` for image hosting

## 📖 Usage

### Creating a Design

1. Open the add-on in Adobe Express
2. Enter a design description in the text area (e.g., "Create a summer sale announcement")
3. Optionally enable AI analysis of past posts
4. Click **CREATE** to generate your design

### Compliance Checking

1. Click the **Compliance Checker** button
2. Upload your brand guidelines PDF (if not already uploaded)
3. The system will analyze your design against brand guidelines
4. Review compliance results and recommendations

### Copyright Checking

1. Click the **Copyrighter** button
2. The system will check for potential copyright issues
3. Review the results and make necessary changes

### Brand Image Management

1. Click **Brand Image** button
2. Upload images or CSV file with image data
3. Use these images as references for consistent branding

### Brand Guidelines

1. Click **Brand Guidelines** button
2. Upload your brand guidelines PDF
3. The system will use these for compliance checking

### Integrations

- **LinkedIn**: Click the LinkedIn icon to post directly to LinkedIn
- **Slack**: Click the Slack icon to send messages to your Slack channel
- **Jira**: Click the Jira icon to send team notifications

## 🛠️ Development

### Backend API Endpoints

- `POST /generate` - Generate design from text description
- `POST /compliance-check` - Check design compliance
- `POST /copyright-check` - Check for copyright issues
- `POST /upload-brand-image` - Upload brand images
- `POST /upload-brand-guidelines` - Upload brand guidelines PDF
- `POST /analyze-posts` - Analyze past social media posts
- `POST /linkedin/post` - Post to LinkedIn
- `POST /slack/message` - Send Slack message
- `POST /jira/notification` - Send Jira notification

### Frontend Development

The add-on frontend is built using:
- Adobe Express UI components (Spectrum)
- Vanilla JavaScript
- HTML/CSS

## 📝 API Documentation

Once the backend server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🔒 Security Notes

- **Never commit sensitive credentials** to the repository
- Use environment variables or secure config files (excluded via `.gitignore`)
- Keep API keys secure and rotate them regularly
- The `.gitignore` file excludes sensitive configuration files

## 📦 Dependencies

### Backend
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `google-genai` - Google Gemini AI integration
- `PyPDF2` / `PyMuPDF` - PDF processing
- `Pillow` - Image processing
- `requests` / `httpx` - HTTP client
- `pandas` - Data processing
- `google-search-results` - SerpAPI integration

### Frontend
- Adobe Express SDK
- Spectrum Web Components

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Adobe Express Platform
- Google Gemini AI
- All API service providers

## 📧 Support

For issues and questions, please open an issue on GitHub.

---

**Note**: Make sure to configure all API keys and credentials before running the application. Refer to the example configuration files for guidance.
