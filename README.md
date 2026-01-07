# AI E-Sign

AI-powered document signing platform with automatic field detection.

## Features

- **PDF Upload & Processing:** Upload PDFs and automatically render page images
- **Automatic Field Detection:** Detect form fields (signatures, dates, checkboxes, etc.)
- **Smart Classification:** Classify field types and assign to appropriate signers
- **Sender Variables:** Set values at send-time that signers can see but not edit
- **Digital Signatures:** Draw signatures directly in the browser
- **Tamper-Evident Audit Trail:** Blockchain-style hash chain for compliance
- **Completion Certificates:** Generate PDF certificates with audit history

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- (Optional) Docker & Docker Compose

### Local Development

#### Backend

```bash
cd apps/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000
```

#### Frontend

```bash
cd apps/web

# Install dependencies
npm install

# Run the development server
npm run dev
```

Open http://localhost:3000 in your browser.

### Docker Compose

```bash
docker-compose up
```

This starts:
- Backend API at http://localhost:8000
- Frontend at http://localhost:3000
- PostgreSQL database

## Architecture

```
ai-esign/
├── apps/
│   ├── web/          # Next.js frontend
│   │   ├── src/
│   │   │   ├── app/        # Pages (App Router)
│   │   │   ├── components/ # React components
│   │   │   ├── lib/        # Utilities, API client, store
│   │   │   └── types/      # TypeScript types
│   │   └── ...
│   └── backend/      # FastAPI backend
│       ├── app/
│       │   ├── api/        # API routes
│       │   ├── core/       # Config, security
│       │   ├── models/     # SQLAlchemy models
│       │   ├── schemas/    # Pydantic schemas
│       │   └── services/   # Business logic
│       └── ...
├── docs/             # Documentation
├── sample_docs/      # Sample contracts for testing
├── scripts/          # Utility scripts
└── docker-compose.yml
```

## API Documentation

When the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Key Workflows

### 1. Upload Document

1. Log in with email
2. Upload PDF document
3. View rendered pages

### 2. Add Fields

Option A: **Manual**
- Select field type from toolbar
- Draw rectangle on document
- Adjust properties in side panel

Option B: **Automatic**
- Click "Detect Fields" button
- Review detected fields
- Edit/delete as needed

### 3. Send for Signing

1. Click "Send for Signing"
2. Add recipients (name, email, role)
3. Fill sender variables if any
4. Send - recipients get signing links

### 4. Sign Document

1. Open signing link (sent via email or shown in UI)
2. Fill text fields
3. Draw signature
4. Click "Complete Signing"

### 5. Download Completed Document

1. View envelope status
2. Download signed PDF
3. Download completion certificate

## Field Types

| Type | Description |
|------|-------------|
| TEXT | Free-form text input |
| NAME | Name field |
| EMAIL | Email address |
| DATE_SIGNED | Auto-populated on sign |
| CHECKBOX | Yes/No checkbox |
| SIGNATURE | Drawn signature |
| INITIALS | Drawn initials |

## Field Owners

| Owner | Description |
|-------|-------------|
| SENDER | Set at send-time, read-only for signers |
| SIGNER_1 | First signing party |
| SIGNER_2 | Second signing party |

## Anchor Tags

For highest detection accuracy, use anchor tags in your documents:

```
Client Signature: [sig|signer1]
Client Date: [date|signer1]
Company Signature: [sig|signer2]
```

Format: `[type|role]`

Types: `sig`, `date`, `name`, `email`, `text`, `check`, `init`
Roles: `signer1`, `signer2`, `sender`

## Sender Variables

Use `{{variable_name}}` in documents for sender-provided values:

```
Effective Date: {{effective_date}}
Total Fee: {{total_fee}}
```

These are filled when sending and visible to signers.

## Testing

### Generate Sample Documents

```bash
python scripts/generate_sample_docs.py
```

### Run Field Detection Evaluation

```bash
python scripts/evaluate_field_detection.py
```

### Run Backend Tests

```bash
cd apps/backend
pytest
```

### Run Frontend Tests

```bash
cd apps/web
npm test
```

## Configuration

Environment variables (set in `.env` or environment):

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | sqlite:///./esign.db | Database connection string |
| SECRET_KEY | (required) | JWT signing key |
| STORAGE_PATH | ./storage | File storage directory |
| LLM_PROVIDER | none | LLM for classification (openai, anthropic, none) |
| OPENAI_API_KEY | - | OpenAI API key |
| ANTHROPIC_API_KEY | - | Anthropic API key |
| SIGNING_LINK_BASE_URL | http://localhost:3000 | Base URL for signing links |
| SIGNING_LINK_EXPIRY_HOURS | 72 | Link expiration time |

## Security

- **Authentication:** Magic link email (no passwords stored)
- **Signing Links:** JWT tokens with expiration, invalidated after use
- **Audit Trail:** Hash chain for tamper detection
- **Storage:** Files stored locally (S3 support planned)

## Documentation

- [Architecture Decisions](docs/decisions.md)
- [Field Detection](docs/detection.md)
- [Data Model & Audit Trail](docs/audit.md)

## Acceptance Criteria

| Criterion | Target | Description |
|-----------|--------|-------------|
| Field Detection | ≥80% recall | Find obvious blanks/checkboxes/signatures |
| Classification | ≥80% accuracy | Correct field type |
| Owner Inference | ≥70% accuracy | Correct party assignment |
| Sender Variables | Working | Set at send, visible to signer |
| End-to-End | Working | Upload → Fields → Send → Sign → Download |

## Threat Model

### Assets
- Document content (confidential contracts)
- Signing credentials (tokens)
- Audit trail integrity

### Threats & Mitigations
- **Token theft:** Short expiration, single-use
- **Audit tampering:** Hash chain detection
- **Unauthorized access:** Token-based auth, scoped permissions
- **PII exposure:** Minimal storage, no logging of content

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request
