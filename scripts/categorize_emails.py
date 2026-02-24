#!/usr/bin/env python3
"""
Email Categorization System for Nauta
Processes emails to extract entities, detect incidents, and analyze sentiment.
"""

import csv
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import anthropic
from bs4 import BeautifulSoup
from pathlib import Path


class EmailCategorizer:
    """Processes emails and categorizes them according to Nauta specifications."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the categorizer with Claude API."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def clean_html(self, html_text: str) -> str:
        """Parse HTML and extract clean plain text for LLM processing."""
        if not html_text or not html_text.strip():
            return ''

        soup = BeautifulSoup(html_text, 'lxml')

        # Remove non-content tags entirely
        for tag in soup(['script', 'style', 'head', 'meta', 'link']):
            tag.decompose()

        # Convert <br> and block-level tags to newlines before extracting text
        for tag in soup.find_all(['br', 'p', 'div', 'tr', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            tag.insert_before('\n')

        # Convert <td> and <th> to tab-separated columns for table readability
        for tag in soup.find_all(['td', 'th']):
            tag.insert_after('\t')

        text = soup.get_text()

        # Normalize whitespace: collapse spaces but preserve meaningful line breaks
        lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.splitlines()]
        # Remove empty lines but keep at most one consecutive blank line
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

    def parse_snowflake_array(self, array_string: str) -> List[str]:
        """Parse Snowflake array string to Python list."""
        if not array_string or array_string == '':
            return []

        # Remove brackets and quotes, split by comma
        # Handle formats like: ["id1","id2","id3"] or ['id1','id2','id3']
        try:
            # Try to parse as JSON first
            if array_string.startswith('['):
                return json.loads(array_string)
            # If it's a string representation, parse manually
            return [item.strip().strip('"').strip("'")
                   for item in array_string.strip('[]').split(',')]
        except:
            return []

    def build_entities_from_csv(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build entities object from PRISMA-extracted data in CSV."""
        entities = {
            "purchase_orders": [],
            "customer_pos": [],
            "sales_orders": [],
            "bookings": [],
            "containers": [],
            "bl_numbers": [],
            "mbl_numbers": [],
            "hbl_numbers": [],
            "invoices": [],
            "levantes": [],
            "form_7501": [],
            "isf_numbers": [],
            "vessels": [],
            "shippers": [],
            "consignees": [],
            "carriers": [],
            "maritime_lines": [],
            "customs_brokers": [],
            "pol": None,
            "pod": None,
            "transit_ports": [],
            "final_destination": None
        }

        # Extract from PRISMA fields
        if email_data.get('po_number'):
            entities['purchase_orders'] = [email_data['po_number']]

        if email_data.get('container_number'):
            entities['containers'] = [email_data['container_number']]

        if email_data.get('booking_number'):
            entities['bookings'] = [email_data['booking_number']]

        if email_data.get('bol_number'):
            entities['bl_numbers'] = [email_data['bol_number']]

        if email_data.get('supplier_name'):
            entities['shippers'] = [email_data['supplier_name']]

        if email_data.get('vessel'):
            entities['vessels'] = [{"name": email_data['vessel'], "voyage": None, "imo": None}]

        return entities

    def build_categorization_prompt(self, email_data: Dict[str, Any]) -> str:
        """Build the prompt for Claude with email data and instructions."""

        # Clean the body text
        body_text = self.clean_html(email_data.get('body', ''))

        # Build context with existing PRISMA entities
        prisma_entities = []
        if email_data.get('po_number'):
            prisma_entities.append(f"PO: {email_data['po_number']}")
        if email_data.get('booking_number'):
            prisma_entities.append(f"Booking: {email_data['booking_number']}")
        if email_data.get('container_number'):
            prisma_entities.append(f"Container: {email_data['container_number']}")
        if email_data.get('bol_number'):
            prisma_entities.append(f"BOL: {email_data['bol_number']}")
        if email_data.get('supplier_name'):
            prisma_entities.append(f"Supplier: {email_data['supplier_name']}")
        if email_data.get('vessel'):
            prisma_entities.append(f"Vessel: {email_data['vessel']}")

        entities_context = " | ".join(prisma_entities) if prisma_entities else "None extracted by PRISMA"

        prompt = f"""You are an expert email analyst for Nauta, a supply chain logistics company.

Your task: Analyze this email to detect INCIDENTS, SENTIMENT, and POSITIVE SIGNALS.
NOTE: Basic entities (POs, containers, etc.) are already extracted by PRISMA - DO NOT re-extract them.

EMAIL:
---
From: {email_data.get('from_email', 'N/A')}
To: {email_data.get('to_email', 'N/A')}
Subject: {email_data.get('subject', 'N/A')}
Date: {email_data.get('created_at', 'N/A')}
PRISMA doc_type: {email_data.get('doc_type', 'N/A')}

PRISMA Entities: {entities_context}

Body:
{body_text[:3500]}
---

ANALYZE FOR:

## 0. EMAIL TYPE CLASSIFICATION (classify FIRST)

Classify the email into exactly one of these types:
- **OPERATIONAL**: Real communication between people about an active operation (delays, costs, document requests, follow-ups, negotiations)
- **AUTO_NOTIFICATION**: Automated system message with operational value (BL ready, arrival notice, customs approval, vessel schedule update, booking confirmation)
- **MARKETING**: Commercial proposal, unsolicited offer, sales pitch from a logistics provider or vendor
- **READ_RECEIPT**: Confirmation that someone opened an email — subject usually starts with "Read:" — no operational content
- **OTHER**: Anything that doesn't fit the above (internal memos, scanned documents with no operational context, etc.)

## 1. INCIDENT DETECTION

Categories:
**A. DELAYS & DISRUPTIONS**: Vessel Rollover ⭐, Vessel Omission ⭐, Supplier delays, Port delays, Customs delays (Levante, Form 7501), Documentation delays (ISF, BL, HBL)

**B. COST CHANGES**: Detention ⭐, Demurrage ⭐, Freight rate changes, Puerto Rico IVU (11.5%), Surcharges (BAF/CAF/PSS), Cancel/Amendment fees

**C. OPERATIONAL**: PO-Booking mapping issues ⭐, IOR confusion ⭐, Multiple follow-ups, Documentation quality issues, System issues

**D. POSITIVE SIGNALS** ✅: Proactive notifications ⭐, Document ready (BL/ISF), Customs approval (Levante) ⭐, Commercial gestures, Quick resolutions

For each incident:
- category: DELAY_DISRUPTION | COST_CHANGES | OPERATIONAL_ISSUES
- subcategory: Specific type
- severity: LOW (routine) | MEDIUM (3-7 days, $1-5K) | HIGH ($5K+, customs holds) | CRITICAL (blocked ops, >$10K)
- date_detected, date_resolved
- details, impact_description, resolution
- affected_entities: {{"bookings": [], "pos": [], "containers": []}}
- financial_impact: {{"amount": number, "currency": "USD", "type": "detention/demurrage"}}
- proactive_notification: boolean

## 2. SENTIMENT ANALYSIS

- POSITIVE: Thanks, confirmations, resolutions
- NEUTRAL: Routine updates
- CONCERNED: First follow-up, polite urgency
- URGENT: 2nd/3rd follow-up, "urgente", "ASAP"
- CRITICAL: 3rd+ follow-up, ops impact, escalation

Also: urgency_level, follow_up_count, escalation_detected, action_required, operational_impact

## 3. OUTPUT JSON

Return ONLY valid JSON (no markdown, no ```json``` tags):

{{
  "incidents": [
    {{
      "category": "DELAY_DISRUPTION",
      "subcategory": "Vessel Rollover",
      "severity": "HIGH",
      "date_detected": "YYYY-MM-DD",
      "date_resolved": null,
      "details": "Description",
      "affected_entities": {{"bookings": [], "pos": [], "containers": []}},
      "impact_description": "Impact",
      "resolution": null,
      "financial_impact": {{"amount": null, "currency": "USD", "type": null}},
      "proactive_notification": false
    }}
  ],
  "positive_signals": [
    {{
      "type": "PROACTIVE_COMMUNICATION",
      "date": "YYYY-MM-DD",
      "details": "Description",
      "value": null
    }}
  ],
  "sentiment_analysis": {{
    "overall_sentiment": "NEUTRAL",
    "urgency_level": "LOW",
    "follow_up_count": 0,
    "escalation_detected": false,
    "action_required": false,
    "operational_impact": false
  }},
  "key_dates": {{
    "etd_original": null,
    "etd_revised": null,
    "eta_original": null,
    "eta_revised": null,
    "actual_departure": null,
    "actual_arrival": null,
    "discharge_date": null,
    "last_free_date": null,
    "document_deadline": null
  }},
  "actions_required": [
    {{
      "action": "Action description",
      "assignee": "Who needs to act",
      "status": "PENDING",
      "first_requested": "YYYY-MM-DD",
      "follow_ups": 0,
      "deadline": null
    }}
  ],
  "email_type": "OPERATIONAL",
  "summary": "Brief summary",
  "context_for_ask_nauta": "Natural language context with entities, cause/effect, resolution"
}}

Return ONLY the JSON. If no incidents/signals, use empty arrays []."""

        return prompt

    def categorize_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single email and return categorized data."""

        try:
            prompt = self.build_categorization_prompt(email_data)

            # Call Claude API
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3072,  # Reduced since we're not extracting entities
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract JSON from response
            response_text = message.content[0].text

            # Try to parse JSON
            try:
                llm_result = json.loads(response_text)
            except json.JSONDecodeError as e:
                # If JSON is wrapped in markdown, try to extract it
                json_match = re.search(r'```json\s*(\{.*\})\s*```', response_text, re.DOTALL)
                if json_match:
                    llm_result = json.loads(json_match.group(1))
                else:
                    print(f"Failed to parse JSON for queue_id {email_data.get('queue_id')}: {e}")
                    print(f"Response: {response_text[:500]}")
                    return self.create_error_result(email_data, f"JSON parse error: {e}")

            # Parse related_queue_ids if present
            related_queue_ids = []
            if email_data.get('related_queue_ids'):
                related_queue_ids = self.parse_snowflake_array(email_data.get('related_queue_ids'))

            # Build complete result with PRISMA entities
            result = {
                "queue_id": email_data.get('queue_id', ''),
                "client_id": email_data.get('client_id', ''),
                "client_name": email_data.get('client_name', ''),
                "thread_id": email_data.get('thread_id') or None,
                "related_queue_ids": related_queue_ids,
                "message_id": email_data.get('message_id', ''),
                "is_thread": email_data.get('is_thread', False),
                "thread_message_count": len(related_queue_ids) if related_queue_ids else 1,
                "processed_date": datetime.now().isoformat() + "Z",
                "email_metadata": {
                    "from": email_data.get('from_email', ''),
                    "to": [e.strip() for e in email_data.get('to_email', '').split(',') if e.strip()],
                    "cc": None,
                    "subject": email_data.get('subject', ''),
                    "inserted_at": email_data.get('created_at', '')
                },
                "entities": self.build_entities_from_csv(email_data),
                "incidents": llm_result.get('incidents', []),
                "positive_signals": llm_result.get('positive_signals', []),
                "sentiment_analysis": llm_result.get('sentiment_analysis', {}),
                "key_dates": llm_result.get('key_dates', {}),
                "actions_required": llm_result.get('actions_required', []),
                "email_type": llm_result.get('email_type', 'UNKNOWN'),
                "summary": llm_result.get('summary', ''),
                "context_for_ask_nauta": llm_result.get('context_for_ask_nauta', '')
            }

            return result

        except Exception as e:
            print(f"Error processing email {email_data.get('queue_id')}: {e}")
            return self.create_error_result(email_data, str(e))

    def create_error_result(self, email_data: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """Create a minimal result object for failed processing."""
        # Parse related_queue_ids if present
        related_queue_ids = []
        if email_data.get('related_queue_ids'):
            related_queue_ids = self.parse_snowflake_array(email_data.get('related_queue_ids'))

        return {
            "queue_id": email_data.get('queue_id', ''),
            "client_id": email_data.get('client_id', ''),
            "client_name": email_data.get('client_name', ''),
            "thread_id": email_data.get('thread_id') or None,
            "related_queue_ids": related_queue_ids,
            "message_id": email_data.get('message_id', ''),
            "is_thread": email_data.get('is_thread', False),
            "thread_message_count": len(related_queue_ids) if related_queue_ids else 1,
            "processed_date": datetime.now().isoformat() + "Z",
            "email_metadata": {
                "from": email_data.get('from_email', ''),
                "to": [e.strip() for e in email_data.get('to_email', '').split(',') if e.strip()],
                "cc": None,
                "subject": email_data.get('subject', ''),
                "inserted_at": email_data.get('created_at', '')
            },
            "entities": self.build_entities_from_csv(email_data),  # Still include PRISMA entities
            "incidents": [],
            "positive_signals": [],
            "sentiment_analysis": {
                "overall_sentiment": "NEUTRAL",
                "urgency_level": "LOW",
                "follow_up_count": 0,
                "escalation_detected": False,
                "action_required": False,
                "operational_impact": False
            },
            "key_dates": {},
            "actions_required": [],
            "summary": f"Error processing email: {error_msg}",
            "context_for_ask_nauta": f"Email could not be processed: {error_msg}",
            "processing_error": error_msg
        }


def read_emails_csv(csv_path: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Read emails from CSV file."""
    import sys
    csv.field_size_limit(sys.maxsize)
    emails = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            emails.append(row)
    return emails


def build_timeline(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build a flat chronological timeline of incidents and positive signals from all emails."""
    timeline = []

    EXCLUDED_TYPES = {'MARKETING', 'READ_RECEIPT', 'OTHER'}

    for email in results:
        if 'processing_error' in email:
            continue
        if email.get('email_type') in EXCLUDED_TYPES:
            continue

        base = {
            "queue_id": email.get('queue_id', ''),
            "client_id": email.get('client_id', ''),
            "client_name": email.get('client_name', ''),
            "message_id": email.get('message_id', ''),
            "thread_id": email.get('thread_id'),
            "subject": email.get('email_metadata', {}).get('subject', ''),
            "actors": {
                "from": email.get('email_metadata', {}).get('from', ''),
                "to": email.get('email_metadata', {}).get('to', [])
            },
            "sentiment": email.get('sentiment_analysis', {}).get('overall_sentiment', 'NEUTRAL'),
            "summary": email.get('summary', '')
        }

        for incident in email.get('incidents', []):
            timeline.append({
                **base,
                "date": incident.get('date_detected'),
                "event_type": "INCIDENT",
                "incident_type": incident.get('category'),
                "subcategory": incident.get('subcategory'),
                "severity": incident.get('severity'),
                "affected_entities": incident.get('affected_entities', {}),
                "financial_impact": incident.get('financial_impact', {}),
                "details": incident.get('details'),
                "resolved": bool(incident.get('date_resolved') or incident.get('resolution')),
                "resolution": incident.get('resolution'),
            })

        for signal in email.get('positive_signals', []):
            timeline.append({
                **base,
                "date": signal.get('date'),
                "event_type": "POSITIVE_SIGNAL",
                "incident_type": None,
                "subcategory": signal.get('type'),
                "severity": None,
                "affected_entities": {},
                "financial_impact": {"amount": signal.get('value'), "currency": "USD", "type": None},
                "details": signal.get('details'),
                "resolved": True,
                "resolution": None,
            })

    # Sort chronologically, entries without date go to the end
    timeline.sort(key=lambda x: x.get('date') or '9999-99-99')

    return timeline


def save_results(results: List[Dict[str, Any]], output_path: str):
    """Save categorization results to JSON file."""
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "timeline": build_timeline(results),
        "emails": results
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Results saved to: {output_path}")
    print(f"   Total emails processed: {len(results)}")
    print(f"   Timeline events: {len(output['timeline'])}")


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description='Categorize Nauta emails')
    parser.add_argument('--input', default='data/emails.csv',
                       help='Input CSV file path')
    parser.add_argument('--output', default='output/categorized_emails.json',
                       help='Output JSON file path')
    parser.add_argument('--limit', type=int, default=10,
                       help='Limit number of emails to process (default: 10)')
    parser.add_argument('--api-key', help='Anthropic API key (or set ANTHROPIC_API_KEY env var)')

    args = parser.parse_args()

    print("🚀 Nauta Email Categorization System")
    print("=" * 50)
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Limit: {args.limit} emails")
    print()

    # Initialize categorizer
    try:
        categorizer = EmailCategorizer(api_key=args.api_key)
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\nPlease set ANTHROPIC_API_KEY environment variable or use --api-key flag")
        return 1

    # Read emails
    print(f"📧 Reading emails from {args.input}...")
    emails = read_emails_csv(args.input, limit=args.limit)
    print(f"   Found {len(emails)} emails to process\n")

    # Process emails
    results = []
    for i, email in enumerate(emails, 1):
        queue_id = email.get('queue_id', 'unknown')
        subject = email.get('subject', 'No subject')[:50]
        print(f"[{i}/{len(emails)}] Processing: {subject}...")
        print(f"           Queue ID: {queue_id}")

        result = categorizer.categorize_email(email)
        results.append(result)

        # Brief summary
        if 'processing_error' not in result:
            num_incidents = len(result.get('incidents', []))
            num_entities = sum(len(v) if isinstance(v, list) else (1 if v else 0)
                             for v in result.get('entities', {}).values())
            sentiment = result.get('sentiment_analysis', {}).get('overall_sentiment', 'N/A')
            email_type = result.get('email_type', 'UNKNOWN')
            print(f"           ✓ [{email_type}] {num_entities} entities, {num_incidents} incidents, sentiment: {sentiment}")
        else:
            print(f"           ✗ Error: {result['processing_error'][:80]}")
        print()

    # Save results
    save_results(results, args.output)

    # Summary statistics
    print("\n📊 Processing Summary")
    print("=" * 50)
    successful = sum(1 for r in results if 'processing_error' not in r)
    failed = len(results) - successful
    total_incidents = sum(len(r.get('incidents', [])) for r in results)
    total_positive = sum(len(r.get('positive_signals', [])) for r in results)

    print(f"✅ Successfully processed: {successful}/{len(results)}")
    if failed > 0:
        print(f"❌ Failed: {failed}/{len(results)}")
    print(f"🔔 Total incidents detected: {total_incidents}")
    print(f"✨ Total positive signals: {total_positive}")

    # Sentiment breakdown
    sentiment_counts = {}
    for r in results:
        sentiment = r.get('sentiment_analysis', {}).get('overall_sentiment', 'UNKNOWN')
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1

    print(f"\n📈 Sentiment Breakdown:")
    for sentiment, count in sorted(sentiment_counts.items()):
        print(f"   {sentiment}: {count}")

    print("\n✨ Done!")
    return 0


if __name__ == '__main__':
    exit(main())
