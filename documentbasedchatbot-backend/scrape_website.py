#!/usr/bin/env python3
"""
Web scraper to extract content from https://www.myhealthschool.in/
and save it to company_info.txt for the chatbot to learn from.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

def scrape_website(start_url, max_pages=20):
    """Scrape website content and extract text."""

    visited = set()
    to_visit = [start_url]
    all_content = []

    # Domain for limiting scraping to this site only
    domain = urlparse(start_url).netloc

    print(f"Starting to scrape {start_url}...")
    print(f"Will limit to domain: {domain}")
    print()

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)

        if url in visited:
            continue

        print(f"Scraping ({len(visited)+1}/{max_pages}): {url}")
        visited.add(url)

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()

            # Get text
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            if text.strip():
                all_content.append(f"\n\n--- Page: {url} ---\n\n{text}")

            # Find all links on this page
            for link in soup.find_all('a', href=True):
                next_url = urljoin(url, link['href'])
                next_domain = urlparse(next_url).netloc

                # Only follow links within the same domain
                if next_domain == domain and next_url not in visited:
                    # Remove fragments and query params for cleaner URLs
                    next_url = next_url.split('#')[0]
                    if next_url not in to_visit:
                        to_visit.append(next_url)

            time.sleep(0.5)  # Be respectful to the server

        except Exception as e:
            print(f"  Error scraping {url}: {e}")

    return '\n'.join(all_content)

def main():
    """Main function to scrape and save content."""

    url = "https://www.myhealthschool.in/"

    print("=" * 60)
    print("WEBSITE CONTENT SCRAPER")
    print("=" * 60)
    print()

    # Scrape website
    content = scrape_website(url, max_pages=30)

    print()
    print("=" * 60)
    print(f"Scraped {len(content)} characters of content")
    print("=" * 60)

    # Save to file
    output_file = "company_info.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[OK] Content saved to {output_file}")
    print()

    # Show preview
    preview = content[:500]
    print("Preview of scraped content:")
    print("-" * 60)
    print(preview)
    print("-" * 60)
    print()
    print("Next step: Run 'python ingest.py' to update the vector database")

if __name__ == "__main__":
    main()
