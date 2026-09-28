# Security Briefing Aggregator

A daily page of 10 cybersecurity articles, picked from 28 RSS feeds covering news, threat intelligence and offensive security research. Each article is shown in full on the page, without ads or cookie banners. A GitHub Actions job rebuilds the page every morning, and an article that has been shown once is not shown again.

Live page: https://kleinmichalgit.github.io/security-feed/

## Installation and local use

Requires Python 3.12.

```bash
pip install -r requirements.txt pytest
playwright install chromium
```

| Command                                | What it does                                                            |
| -------------------------------------- | ----------------------------------------------------------------------- |
| `python aggregator.py`                 | Builds `index.html` and records the shown articles in `data/state.json` |
| `python aggregator.py --no-state`      | Builds `index.html` without reading or writing the state file           |
| `python aggregator.py --limit 15`      | Changes the number of articles                                          |
| `python aggregator.py --check-sources` | Checks every feed and exits non-zero if any fails                       |
| `pytest`                               | Runs the tests in `tests/`                                              |

## Disclaimer and legal

This is an open-source educational non-commercial project.

- **Authorship**: Aggregator maintained by Michal Klein.
- **Content Rights**: This tool is an aggregator. Full credit belongs to the original authors and publications linked in each post. This project does not claim ownership of the scraped content.
