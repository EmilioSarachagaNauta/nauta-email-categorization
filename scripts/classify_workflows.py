#!/usr/bin/env python3
"""
Workflow Classification Agent for Nauta Email Categorization.

Makes a lightweight second LLM pass per email to classify workflow type,
trigger actor, and automation potential.

Reads:  data/emails.csv
Writes: output/workflow_classifications.json

Cost estimate: ~$2-3 for 500 emails (max_tokens=512, lightweight prompt)
"""

import csv
import json
import os
import re
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

import anthropic
from bs4 import BeautifulSoup


SKIP_EMAIL_TYPES = {'MARKETING', 'READ_RECEIPT', 'OTHER'}

WORKFLOW_TAXONOMY = """
Workflow type taxonomy (category: types):
- TRACKING:      ARRIVAL_NOTICE | VESSEL_UPDATE | CONTAINER_STATUS
- DOCUMENTATION: BL_RELEASE | DELIVERY_ORDER | CUSTOMS_CLEARANCE | ISF_FILING | DOCUMENT_REQUEST
- FREIGHT:       BOOKING_CONFIRMATION | CARGO_READY | PICKUP_COORDINATION | VESSEL_ROLLOVER_NOTICE
- BILLING:       FREIGHT_INVOICE | DETENTION_DEMURRAGE_NOTICE | RATE_QUOTE
- COMMUNICATION: STATUS_UPDATE | FOLLOW_UP | ESCALATION | OTHER
""".strip()


def clean_html(html_text: str) -> str:
    """Parse HTML and extract clean plain text for LLM processing."""
    if not html_text or not html_text.strip():
        return ''

    soup = BeautifulSoup(html_text, 'lxml')

    for tag in soup(['script', 'style', 'head', 'meta', 'link']):
        tag.decompose()

    for tag in soup.find_all(['br', 'p', 'div', 'tr', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        tag.insert_before('\n')

    for tag in soup.find_all(['td', 'th']):
        tag.insert_after('\t')

    text = soup.get_text()

    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.splitlines()]
    cleaned_lines = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                cleaned_lines.append('')
            prev_blank = True
        else:
            cleaned_lines.append(line)
            prev_blank = False

    return '\n'.join(cleaned_lines).strip()


def read_emails_csv(csv_path: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Read emails from CSV file."""
    csv.field_size_limit(sys.maxsize)
    emails = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            emails.append(row)
    return emails


def load_existing_classifications(output_path: str) -> Dict[str, Any]:
    """Load existing classifications to allow resuming an interrupted run."""
    if Path(output_path).exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {item['queue_id']: item for item in data.get('classifications', [])}
    return {}


def load_email_types(categorized_path: str) -> Dict[str, str]:
    """Load queue_id → email_type mapping from categorized_emails.json."""
    if not Path(categorized_path).exists():
        return {}
    with open(categorized_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {
        email['queue_id']: email.get('email_type', '')
        for email in data.get('emails', [])
    }


def build_prompt(email: Dict[str, Any], email_type: str) -> str:
    """Build a lightweight classification prompt."""
    body_raw = email.get('body', '')
    body_clean = clean_html(body_raw) if '<' in body_raw else body_raw
    body_snippet = body_clean[:1000]

    return f"""You are a logistics workflow classifier. Classify this email for automation opportunity analysis.

Email:
- From: {email.get('from_email', '')}
- Subject: {email.get('subject', '')}
- Email type: {email_type}
- Body (first 1000 chars):
{body_snippet}

{WORKFLOW_TAXONOMY}

Trigger actor types: CARRIER | FORWARDER | CUSTOMS_BROKER | WAREHOUSE | SUPPLIER | CLIENT | NAUTA | SYSTEM
Workflow steps: INITIATION | NOTIFICATION | CONFIRMATION | FOLLOW_UP | ESCALATION | CLOSURE
Automation potential: HIGH = fully automatable routine, MEDIUM = partially automatable, LOW = needs human judgment, NONE = unique/ad-hoc

Respond with ONLY a JSON object (no markdown fences):
{{
  "workflow_category": "TRACKING | DOCUMENTATION | FREIGHT | BILLING | COMMUNICATION",
  "workflow_type": "specific type from taxonomy",
  "workflow_step": "INITIATION | NOTIFICATION | CONFIRMATION | FOLLOW_UP | ESCALATION | CLOSURE",
  "trigger_actor_type": "CARRIER | FORWARDER | CUSTOMS_BROKER | WAREHOUSE | SUPPLIER | CLIENT | NAUTA | SYSTEM",
  "trigger_actor_name": "company or domain inferred from from_email or content",
  "is_routine": true,
  "recurrence_signals": ["e.g. weekly batch", "automated notification"],
  "automation_potential": "HIGH | MEDIUM | LOW | NONE",
  "automation_reason": "one sentence explaining why"
}}"""


def classify_email(client: anthropic.Anthropic, email: Dict[str, Any], email_type: str) -> Dict[str, Any]:
    """Call Claude to classify a single email's workflow type."""
    prompt = build_prompt(email, email_type)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text.strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Try extracting from markdown code block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        # Try bare JSON object
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        raise


def save_output(results: List[Dict[str, Any]], output_path: str) -> None:
    """Save current results to JSON file (called incrementally)."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": datetime.now().isoformat() + "Z",
        "total_classifications": len(results),
        "classifications": results,
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description='Classify email workflows using Claude (lightweight second LLM pass)'
    )
    parser.add_argument('--input', default='data/emails.csv',
                        help='Input CSV file (default: data/test_emails.csv)')
    parser.add_argument('--categorized', default='output/categorized_emails.json',
                        help='Categorized emails JSON for email_type lookup')
    parser.add_argument('--output', default='output/workflow_classifications.json',
                        help='Output JSON file (default: output/workflow_classifications.json)')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of emails to process (for testing)')
    parser.add_argument('--clients', nargs='+', default=None,
                        help='Only process emails from these clients (e.g. --clients Econo "B Fernandez")')
    parser.add_argument('--delay', type=float, default=0.1,
                        help='Delay between API calls in seconds (default: 0.1)')
    parser.add_argument('--save-every', type=int, default=10,
                        help='Save incrementally every N processed emails (default: 10)')
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    client = anthropic.Anthropic(api_key=api_key)

    print(f"📂 Reading emails from {args.input}...")
    emails = read_emails_csv(args.input, limit=args.limit)
    print(f"   Loaded {len(emails)} emails")

    if args.clients:
        client_filter = set(args.clients)
        emails = [e for e in emails if e.get('client_name') in client_filter]
        print(f"   Filtered to {len(emails)} emails from: {', '.join(sorted(client_filter))}")

    print(f"📊 Loading email types from {args.categorized}...")
    email_types = load_email_types(args.categorized)
    print(f"   Found {len(email_types)} email type mappings")

    existing = load_existing_classifications(args.output)
    if existing:
        print(f"   Resuming: {len(existing)} classifications already done, will skip")

    results = list(existing.values())
    skipped = 0
    processed = 0
    errors = 0

    to_process = [e for e in emails if e.get('queue_id') not in existing]
    print(f"\n🔍 Processing {len(to_process)} emails ({len(existing)} already classified)...")

    for i, email in enumerate(to_process):
        queue_id = email.get('queue_id', '')
        client_name = email.get('client_name', '')
        email_type = email_types.get(queue_id, '')

        # Skip non-operational email types
        if email_type in SKIP_EMAIL_TYPES:
            skipped += 1
            continue

        try:
            llm_result = classify_email(client, email, email_type)

            record = {
                "queue_id": queue_id,
                "client_name": client_name,
                "email_type": email_type,
                **llm_result,
            }
            results.append(record)
            processed += 1

            if processed % args.save_every == 0:
                print(f"  [{i+1}/{len(to_process)}] {processed} processed | "
                      f"last: {llm_result.get('workflow_type', '?')} ({client_name})")
                save_output(results, args.output)

            if args.delay > 0:
                time.sleep(args.delay)

        except Exception as e:
            errors += 1
            print(f"  ❌ Error on {queue_id}: {e}")
            results.append({
                "queue_id": queue_id,
                "client_name": client_name,
                "email_type": email_type,
                "error": str(e),
            })

    save_output(results, args.output)

    print(f"\n✅ Done!")
    print(f"   Processed:  {processed}")
    print(f"   Skipped:    {skipped} (MARKETING/READ_RECEIPT/OTHER)")
    print(f"   Errors:     {errors}")
    print(f"   Total:      {len(results)}")
    print(f"   Output:     {args.output}")


if __name__ == '__main__':
    main()
