# Security Briefing Aggregator

An automated, open-source security intelligence feed that scrapes, scores, and balances news from top-tier cybersecurity sources. Designed to provide a focused daily briefing, it prevents brain fatigue by limiting context switching and providing an ad-free reading experience.

The live feed is hosted at: https://kleinmichalgit.github.io/security-feed/

## Key Features

- **Balanced Selection**: Uses a Round-Robin approach to ensure independent research blogs aren't buried by high-frequency news sites.
- **Smart Scoring**: Prioritizes content based on freshness, cross-feed trending topics, and high-impact keywords (e.g., zero-day, ransomware).
- **Deep Extraction**: Employs Playwright and Trafilatura to scrape actual article text, bypassing cookie walls for a unified reading experience.
- **Terminal UI**: High-contrast, PowerShell-blue design optimized for desktop and mobile.
- **Automated**: Powered by GitHub Actions for daily updates at 06:00 UTC.

## Tech Stack

- **Python 3.10**: Core logic and scoring.
- **Playwright**: Headless browser automation.
- **Feedparser**: RSS/Atom processing.
- **Trafilatura**: Content extraction.
- **GitHub Actions**: Scheduled execution and deployment.

## Installation and Local Use

### 1. Clone the Repository

```bash
git clone https://github.com/KleinMichalGit/security-feed.git
cd security-feed
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Generate the Feed

```bash
python aggregator.py
```

## GitHub Actions Workflow

The `.github/workflows/main.yml` script automates the process:

1. **Triggers**: Runs daily at 06:00 UTC or manually.
2. **Execution**: Installs Chromium and runs `aggregator.py`.
3. **Deployment**: Commits the new `index.html` to the `main` branch.

## Disclaimer and Legal

This is an open-source educational non-commercial project.

- **Authorship**: Aggregator maintained by Michal Klein.
- **Content Rights**: This tool is an aggregator. Full credit belongs to the original authors and publications linked in each post. This project does not claim ownership of the scraped content.
