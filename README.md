# Project Name

> Short one-liner describing what this project or service does.

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Setup](#setup)
- [Dependencies](#dependencies)
- [Usage](#usage)
- [API Summary](#api-summary)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Provide a brief description of the project purpose, scope, and main functionality.

---

## Features

- Bullet list of key features or components
- e.g., audit logging, pub/sub infrastructure, common utilities

---

## Setup

### Prerequisites

- Python 3.10+ installed
- Virtual environment tool (`venv`) recommended

### Installation

```bash
# Clone the repo
git clone https://your.repo.url.git
cd your-project

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt


### Environment

Required variables for Label Studio integration:

```bash
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB
GCS_BUCKET=your-curated-bucket
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-credentials.json
LABEL_STUDIO_BASE_URL=https://labelstudio.example.com
LABEL_STUDIO_API_KEY=your-labelstudio-token
LABEL_STUDIO_WEBHOOK_SECRET=shared-secret
LABEL_STUDIO_MEDIA_TOKEN=media-token
PUBLIC_BASE_URL=https://labeler.example.com
LABEL_STUDIO_LABEL_CONFIG=<View>...</View>
```

## Usage

Key endpoints:
- `POST /labeling/start` with `{ "annotationSetId": "ANST..." }`
- `GET /media/dataset-item/{dataset_item_id}?token=...`
- `POST /webhooks/labelstudio`
