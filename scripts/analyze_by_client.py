#!/usr/bin/env python3
"""
Client-level analysis of email categorization output.
Aggregates incidents, sentiment, signals and email types per client.
"""

import json
import argparse
from collections import Counter, defaultdict
from pathlib import Path


def analyze_by_client(output_path: str):
    with open(output_path, encoding='utf-8') as f:
        data = json.load(f)

    emails = data['emails']

    # Group emails by client
    clients = defaultdict(lambda: {
        'email_types': Counter(),
        'sentiments': Counter(),
        'incident_categories': Counter(),
        'incident_subcategories': Counter(),
        'severities': Counter(),
        'signal_types': Counter(),
        'financial_impacts': [],
        'unresolved_incidents': [],
        'urgent_emails': [],
        'total_emails': 0,
        'total_incidents': 0,
        'total_signals': 0,
        'action_required_count': 0,
        'operational_impact_count': 0,
    })

    for email in emails:
        client = email.get('client_name') or email.get('client_id', 'UNKNOWN')
        c = clients[client]

        c['total_emails'] += 1
        c['email_types'][email.get('email_type', 'UNKNOWN')] += 1

        sentiment = email.get('sentiment_analysis', {}).get('overall_sentiment', 'UNKNOWN')
        c['sentiments'][sentiment] += 1

        if email.get('sentiment_analysis', {}).get('action_required'):
            c['action_required_count'] += 1
        if email.get('sentiment_analysis', {}).get('operational_impact'):
            c['operational_impact_count'] += 1

        if sentiment in ('URGENT', 'CRITICAL'):
            c['urgent_emails'].append({
                'subject': email.get('email_metadata', {}).get('subject', ''),
                'sentiment': sentiment,
                'summary': email.get('summary', '')[:100]
            })

        for inc in email.get('incidents', []):
            c['total_incidents'] += 1
            c['incident_categories'][inc.get('category', 'UNKNOWN')] += 1
            c['incident_subcategories'][inc.get('subcategory', 'UNKNOWN')] += 1
            c['severities'][inc.get('severity', 'UNKNOWN')] += 1

            fin = inc.get('financial_impact', {})
            if fin.get('amount'):
                c['financial_impacts'].append({
                    'amount': fin['amount'],
                    'currency': fin.get('currency', 'USD'),
                    'type': fin.get('type', ''),
                    'subcategory': inc.get('subcategory', ''),
                    'subject': email.get('email_metadata', {}).get('subject', '')[:60]
                })

            if not inc.get('date_resolved') and not inc.get('resolution'):
                c['unresolved_incidents'].append({
                    'subcategory': inc.get('subcategory', ''),
                    'severity': inc.get('severity', ''),
                    'details': inc.get('details', '')[:100],
                    'subject': email.get('email_metadata', {}).get('subject', '')[:60]
                })

        for sig in email.get('positive_signals', []):
            c['total_signals'] += 1
            c['signal_types'][sig.get('type', 'UNKNOWN')] += 1

    return clients


def print_report(clients: dict):
    print("=" * 70)
    print("ANÁLISIS POR CLIENTE")
    print("=" * 70)

    # Sort by total incidents desc, then total emails
    sorted_clients = sorted(
        clients.items(),
        key=lambda x: (x[1]['total_incidents'], x[1]['total_emails']),
        reverse=True
    )

    for client_name, c in sorted_clients:
        operational = c['email_types'].get('OPERATIONAL', 0) + c['email_types'].get('AUTO_NOTIFICATION', 0)
        noise = c['total_emails'] - operational
        total_financial = sum(f['amount'] for f in c['financial_impacts'])

        print(f"\n{'─' * 70}")
        print(f"  {client_name.upper()}")
        print(f"{'─' * 70}")
        print(f"  Emails totales:     {c['total_emails']}  (operacionales: {operational}, ruido filtrado: {noise})")
        print(f"  Incidentes:         {c['total_incidents']}  |  Señales positivas: {c['total_signals']}")
        print(f"  Acción requerida:   {c['action_required_count']}  |  Impacto operacional: {c['operational_impact_count']}")

        if total_financial > 0:
            print(f"  Impacto financiero: ${total_financial:,.0f} USD")
            for f in c['financial_impacts']:
                print(f"    · ${f['amount']:,} {f['type']} — {f['subcategory']} ({f['subject']})")

        print(f"\n  Sentimiento:")
        for s, count in c['sentiments'].most_common():
            bar = '█' * count
            print(f"    {s:<12} {bar} ({count})")

        if c['incident_categories']:
            print(f"\n  Categorías de incidentes:")
            for cat, count in c['incident_categories'].most_common():
                print(f"    · {cat}: {count}")
            print(f"  Subcategorías:")
            for sub, count in c['incident_subcategories'].most_common(5):
                print(f"    · {sub}: {count}")

        if c['severities']:
            print(f"\n  Severidades: {dict(c['severities'].most_common())}")

        if c['unresolved_incidents']:
            print(f"\n  ⚠️  Incidentes sin resolver ({len(c['unresolved_incidents'])}):")
            for inc in c['unresolved_incidents'][:3]:
                print(f"    [{inc['severity']}] {inc['subcategory']}: {inc['details'][:80]}")

        if c['urgent_emails']:
            print(f"\n  🔴 Emails urgentes/críticos ({len(c['urgent_emails'])}):")
            for e in c['urgent_emails'][:3]:
                print(f"    [{e['sentiment']}] {e['subject'][:60]}")

        if c['signal_types']:
            print(f"\n  Señales positivas:")
            for sig, count in c['signal_types'].most_common(3):
                print(f"    · {sig}: {count}")

    # Global summary
    print(f"\n{'=' * 70}")
    print("RESUMEN GLOBAL")
    print(f"{'=' * 70}")
    total_emails = sum(c['total_emails'] for c in clients.values())
    total_incidents = sum(c['total_incidents'] for c in clients.values())
    total_signals = sum(c['total_signals'] for c in clients.values())
    total_financial = sum(
        sum(f['amount'] for f in c['financial_impacts'])
        for c in clients.values()
    )
    all_sentiments = Counter()
    for c in clients.values():
        all_sentiments.update(c['sentiments'])

    print(f"  Clientes únicos:    {len(clients)}")
    print(f"  Emails procesados:  {total_emails}")
    print(f"  Total incidentes:   {total_incidents}")
    print(f"  Total señales +:    {total_signals}")
    print(f"  Impacto financiero: ${total_financial:,.0f} USD")
    print(f"  Sentimiento global: {dict(all_sentiments.most_common())}")


def save_json_report(clients: dict, output_path: str):
    """Save a JSON version of the client report."""
    report = {}
    for client_name, c in clients.items():
        report[client_name] = {
            'total_emails': c['total_emails'],
            'email_types': dict(c['email_types']),
            'total_incidents': c['total_incidents'],
            'total_signals': c['total_signals'],
            'action_required_count': c['action_required_count'],
            'operational_impact_count': c['operational_impact_count'],
            'sentiments': dict(c['sentiments']),
            'incident_categories': dict(c['incident_categories']),
            'incident_subcategories': dict(c['incident_subcategories']),
            'severities': dict(c['severities']),
            'signal_types': dict(c['signal_types']),
            'total_financial_impact_usd': sum(f['amount'] for f in c['financial_impacts']),
            'financial_impacts': c['financial_impacts'],
            'unresolved_incidents': c['unresolved_incidents'],
            'urgent_emails': c['urgent_emails'],
        }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n✅ JSON report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Analyze categorized emails by client')
    parser.add_argument('--input', default='output/categorized_emails.json',
                        help='Input JSON file from categorize_emails.py')
    parser.add_argument('--json-output', default='output/client_analysis.json',
                        help='Output JSON report path')
    args = parser.parse_args()

    print(f"📊 Loading {args.input}...")
    clients = analyze_by_client(args.input)
    print_report(clients)
    save_json_report(clients, args.json_output)


if __name__ == '__main__':
    main()
