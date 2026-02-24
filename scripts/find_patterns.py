#!/usr/bin/env python3
"""
Pattern Finder for Nauta Email Workflow Analysis.

Aggregates workflow classifications to surface recurring automation opportunities.

Reads:  output/workflow_classifications.json
        data/emails.csv            (primary source for thread_id / date metadata)
        output/categorized_emails.json (optional fallback)
Writes: output/pattern_analysis.json
        (also prints a console report)
"""

import csv
import json
import sys
import argparse
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


# ──────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────

def load_classifications(path: str) -> List[Dict[str, Any]]:
    """Load workflow classifications, excluding errored records."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [c for c in data.get('classifications', []) if 'error' not in c]


def load_categorized_emails(path: str) -> Dict[str, Dict[str, Any]]:
    """Load categorized emails indexed by queue_id for thread/date lookups."""
    if not Path(path).exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {e['queue_id']: e for e in data.get('emails', [])}


def load_email_metadata(csv_path: str, categorized_path: str) -> Dict[str, Dict[str, Any]]:
    """Build a unified queue_id → metadata lookup.

    Reads from the emails CSV (primary source): thread_id, created_at,
    and entity fields (booking_number, container_number, bol_number, po_number).
    Overlays categorized_emails.json as fallback for any missing queue_ids.
    """
    metadata: Dict[str, Dict[str, Any]] = {}

    # Primary: emails CSV
    if Path(csv_path).exists():
        csv.field_size_limit(sys.maxsize)
        with open(csv_path, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                qid = row.get('queue_id', '')
                if qid:
                    metadata[qid] = {
                        'thread_id': row.get('thread_id') or None,
                        'inserted_at': row.get('created_at', ''),
                        'booking_number': (row.get('booking_number') or '').strip(),
                        'container_number': (row.get('container_number') or '').strip(),
                        'bol_number': (row.get('bol_number') or '').strip(),
                        'po_number': (row.get('po_number') or '').strip(),
                    }

    # Secondary: categorized_emails.json (fallback for gaps)
    if Path(categorized_path).exists():
        with open(categorized_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for e in data.get('emails', []):
            qid = e.get('queue_id', '')
            if qid and qid not in metadata:
                ent = e.get('entities', {})
                bookings = [b for b in ent.get('bookings', []) if b and b.lower() != 'null']
                containers = [c for c in ent.get('containers', []) if c and c.lower() != 'null']
                bls = [b for b in (ent.get('bl_numbers', []) + ent.get('mbl_numbers', [])) if b and b.lower() != 'null']
                pos = [p for p in ent.get('purchase_orders', []) if p and p.lower() != 'null']
                metadata[qid] = {
                    'thread_id': e.get('thread_id'),
                    'inserted_at': e.get('email_metadata', {}).get('inserted_at', ''),
                    'booking_number': bookings[0] if bookings else '',
                    'container_number': containers[0] if containers else '',
                    'bol_number': bls[0] if bls else '',
                    'po_number': pos[0] if pos else '',
                }

    return metadata


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def get_day_of_week(inserted_at: str) -> str:
    """Extract day-of-week name from ISO timestamp string."""
    if not inserted_at:
        return 'UNKNOWN'
    try:
        dt = datetime.fromisoformat(inserted_at.replace('Z', '+00:00'))
        return dt.strftime('%A')  # Monday, Tuesday, …
    except Exception:
        return 'UNKNOWN'


def pct(part: int, total: int) -> float:
    return round(part / total * 100, 1) if total else 0.0


# ──────────────────────────────────────────────
# Analysis functions
# ──────────────────────────────────────────────

def analyze_workflow_frequency(classifications: List[Dict]) -> Dict[str, Any]:
    """Workflow types per client (frequency breakdown)."""
    by_client: Dict[str, Counter] = defaultdict(Counter)

    for c in classifications:
        client = c.get('client_name') or 'UNKNOWN'
        by_client[client][c.get('workflow_type', 'UNKNOWN')] += 1

    result = {}
    for client, counts in sorted(by_client.items()):
        total = sum(counts.values())
        result[client] = {
            'total': total,
            'top_workflows': [
                {'workflow_type': wt, 'count': ct, 'pct': pct(ct, total)}
                for wt, ct in counts.most_common(5)
            ],
        }
    return result


def analyze_actor_workflow_patterns(classifications: List[Dict]) -> Dict[str, Any]:
    """For each trigger actor, which workflow types do they drive?"""
    actor_workflows: Dict[str, Counter] = defaultdict(Counter)
    actor_total: Counter = Counter()

    for c in classifications:
        actor = (c.get('trigger_actor_name') or '').strip()
        if not actor or actor.lower() in ('unknown', 'n/a', ''):
            continue
        wf = c.get('workflow_type', 'UNKNOWN')
        actor_workflows[actor][wf] += 1
        actor_total[actor] += 1

    result = {}
    # Sort by volume descending, keep actors with ≥3 emails
    for actor, _ in actor_total.most_common():
        total = actor_total[actor]
        if total < 3:
            continue
        top = actor_workflows[actor].most_common(3)
        result[actor] = {
            'total_emails': total,
            'primary_workflow': top[0][0] if top else 'UNKNOWN',
            'primary_pct': pct(top[0][1], total) if top else 0.0,
            'workflow_breakdown': [
                {'workflow_type': wt, 'count': ct, 'pct': pct(ct, total)}
                for wt, ct in top
            ],
        }
    return result


def analyze_temporal_patterns(
    classifications: List[Dict],
    email_meta: Dict[str, Dict],
) -> Dict[str, Any]:
    """Group by day-of-week × workflow_type per client."""
    # client → day → workflow_type → count
    patterns: Dict[str, Dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))

    for c in classifications:
        meta = email_meta.get(c.get('queue_id', ''), {})
        inserted_at = meta.get('inserted_at', '')
        day = get_day_of_week(inserted_at)
        client = c.get('client_name') or 'UNKNOWN'
        wf = c.get('workflow_type', 'UNKNOWN')
        patterns[client][day][wf] += 1

    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
                  'Saturday', 'Sunday', 'UNKNOWN']
    result = {}
    for client, days in sorted(patterns.items()):
        client_rows = []
        for day in days_order:
            if day not in days:
                continue
            wf_counts = days[day]
            total = sum(wf_counts.values())
            client_rows.append({
                'day': day,
                'total': total,
                'top_workflows': [
                    {'workflow_type': wt, 'count': ct}
                    for wt, ct in wf_counts.most_common(3)
                ],
            })
        if client_rows:
            result[client] = client_rows
    return result


def compute_days_in_window(email_meta: Dict[str, Dict]) -> int:
    """Calculate the actual number of days spanned by the dataset."""
    dates = []
    for meta in email_meta.values():
        ts = meta.get('inserted_at', '')
        if not ts:
            continue
        try:
            dates.append(datetime.fromisoformat(ts.replace('Z', '+00:00')))
        except Exception:
            continue
    if len(dates) < 2:
        return 90  # fallback
    return max(1, (max(dates) - min(dates)).days)


def find_automation_clusters(classifications: List[Dict], days_in_window: int = 90) -> List[Dict[str, Any]]:
    """Top automation opportunities: (client, workflow_type, actor_type) clusters."""
    key_counts: Counter = Counter()
    details: Dict[tuple, Dict] = defaultdict(lambda: {
        'potential_counts': Counter(),
        'is_routine_count': 0,
        'recurrence_signals': Counter(),
        'automation_reasons': [],
    })

    for c in classifications:
        if c.get('automation_potential') not in ('HIGH', 'MEDIUM'):
            continue
        key = (
            c.get('client_name') or 'UNKNOWN',
            c.get('workflow_type', 'UNKNOWN'),
            c.get('trigger_actor_type', 'UNKNOWN'),
        )
        key_counts[key] += 1
        d = details[key]
        d['potential_counts'][c.get('automation_potential', 'LOW')] += 1
        if c.get('is_routine'):
            d['is_routine_count'] += 1
        for sig in c.get('recurrence_signals') or []:
            d['recurrence_signals'][sig] += 1
        reason = (c.get('automation_reason') or '').strip()
        if reason and reason not in d['automation_reasons']:
            d['automation_reasons'].append(reason)

    clusters = []
    for (client, wf_type, actor_type), count in key_counts.most_common(20):
        d = details[(client, wf_type, actor_type)]
        clusters.append({
            'client': client,
            'workflow_type': wf_type,
            'trigger_actor_type': actor_type,
            'email_count': count,
            'high_automation_count': d['potential_counts'].get('HIGH', 0),
            'estimated_monthly_volume': round(count * 30 / days_in_window, 1),
            'routine_rate_pct': pct(d['is_routine_count'], count),
            'top_recurrence_signals': [s for s, _ in d['recurrence_signals'].most_common(3)],
            'sample_reason': d['automation_reasons'][0] if d['automation_reasons'] else '',
        })
    return clusters


def find_workflow_chains(
    classifications: List[Dict],
    email_meta: Dict[str, Dict],
) -> List[Dict[str, Any]]:
    """Find common workflow sequences by grouping emails that share an entity.

    Groups by booking_number, container_number, bol_number, and po_number.
    Each group is sorted by date and the sequence of workflow_types is extracted.
    Consecutive duplicate steps are collapsed (same step twice in a row = one step).
    """
    # Build quick lookup: queue_id → workflow_type
    wf_by_qid = {c['queue_id']: c.get('workflow_type', 'UNKNOWN') for c in classifications}

    entity_fields = ['booking_number', 'container_number', 'bol_number', 'po_number']
    null_values = {'', 'null', 'none', 'n/a', '[]', '{}'}

    # entity_key (e.g. "booking_number:BKG123") → [(inserted_at, queue_id)]
    entity_groups: Dict[str, List] = defaultdict(list)

    for qid, meta in email_meta.items():
        if qid not in wf_by_qid:
            continue
        for field in entity_fields:
            value = meta.get(field, '').strip()
            if value.lower() in null_values or value.startswith('[') or value.startswith('{'):
                continue
            key = f'{field}:{meta[field].strip()}'
            entity_groups[key].append((meta.get('inserted_at', ''), qid))

    chain_counts: Counter = Counter()
    chain_examples: Dict[tuple, List[str]] = defaultdict(list)

    for key, entries in entity_groups.items():
        if len(entries) < 2:
            continue
        # Sort by date, extract workflow sequence
        ordered = [wf_by_qid[qid] for _, qid in sorted(entries, key=lambda x: x[0])]
        # Collapse consecutive duplicates (e.g. STATUS_UPDATE → STATUS_UPDATE → ARRIVAL_NOTICE)
        deduped = [ordered[0]]
        for wf in ordered[1:]:
            if wf != deduped[-1]:
                deduped.append(wf)

        entity_value = key.split(':', 1)[1]
        for length in (2, 3):
            for i in range(len(deduped) - length + 1):
                chain = tuple(deduped[i: i + length])
                chain_counts[chain] += 1
                if len(chain_examples[chain]) < 3 and entity_value not in chain_examples[chain]:
                    chain_examples[chain].append(entity_value)

    chains = []
    for chain, count in chain_counts.most_common(15):
        if count < 2:
            continue
        chains.append({
            'sequence': list(chain),
            'occurrence_count': count,
            'example_entities': chain_examples[chain][:3],
        })
    return chains


# ──────────────────────────────────────────────
# Console report
# ──────────────────────────────────────────────

def print_report(
    workflow_freq: Dict,
    actor_patterns: Dict,
    automation_clusters: List[Dict],
    chains: List[Dict],
) -> None:
    """Print a human-readable summary to stdout."""
    W = 70
    print('\n' + '=' * W)
    print('  NAUTA WORKFLOW PATTERN ANALYSIS')
    print('=' * W)

    # 1. Workflow frequency per client
    print('\n📊 TOP WORKFLOWS PER CLIENT')
    print('-' * 50)
    for client, data in list(workflow_freq.items())[:8]:
        print(f'\n  {client} ({data["total"]} emails)')
        for wf in data['top_workflows'][:3]:
            bar = '█' * max(1, int(wf['pct'] / 5))
            print(f'    {wf["workflow_type"]:<38} {wf["pct"]:>5.1f}%  {bar}')

    # 2. Actor → workflow patterns
    print('\n\n🎯 ACTOR → WORKFLOW PATTERNS (top 12 by volume)')
    print('-' * 50)
    for actor, data in list(actor_patterns.items())[:12]:
        print(f'  {actor:<38} → {data["primary_workflow"]} '
              f'({data["primary_pct"]}%,  n={data["total_emails"]})')

    # 3. Automation opportunities
    print('\n\n🤖 TOP AUTOMATION OPPORTUNITIES')
    print('-' * 50)
    for i, c in enumerate(automation_clusters[:10], 1):
        print(f'  {i:2}. [{c["client"]}] {c["workflow_type"]}')
        print(f'      Actor: {c["trigger_actor_type"]} | '
              f'Emails: {c["email_count"]} | '
              f'~{c["estimated_monthly_volume"]}/mo | '
              f'Routine: {c["routine_rate_pct"]}%')
        if c['sample_reason']:
            print(f'      Reason: {c["sample_reason"]}')

    # 4. Workflow chains
    print('\n\n🔗 COMMON WORKFLOW CHAINS (by shared booking/container/BL/PO)')
    print('-' * 50)
    for chain in chains[:10]:
        seq = ' → '.join(chain['sequence'])
        examples = ', '.join(chain.get('example_entities', [])[:2])
        print(f'  {seq:<55}  (n={chain["occurrence_count"]})  e.g. {examples}')

    print('\n' + '=' * W)


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Find recurring workflow patterns in email classifications'
    )
    parser.add_argument('--classifications', default='output/workflow_classifications.json',
                        help='Workflow classifications JSON (default: output/workflow_classifications.json)')
    parser.add_argument('--emails-csv', default='data/emails.csv',
                        help='Emails CSV for thread_id/date metadata (default: data/emails.csv)')
    parser.add_argument('--categorized', default='output/categorized_emails.json',
                        help='Categorized emails JSON (optional fallback for metadata)')
    parser.add_argument('--output', default='output/pattern_analysis.json',
                        help='Output pattern analysis JSON (default: output/pattern_analysis.json)')
    args = parser.parse_args()

    print(f'📂 Loading classifications from {args.classifications}...')
    classifications = load_classifications(args.classifications)
    print(f'   Loaded {len(classifications)} valid classifications')

    print(f'📂 Building email metadata lookup...')
    email_meta = load_email_metadata(args.emails_csv, args.categorized)
    print(f'   Loaded {len(email_meta)} records (CSV + categorized)')

    print('\n🔍 Analyzing patterns...')

    workflow_freq = analyze_workflow_frequency(classifications)
    print(f'  ✓ Workflow frequency  ({len(workflow_freq)} clients)')

    actor_patterns = analyze_actor_workflow_patterns(classifications)
    print(f'  ✓ Actor→workflow      ({len(actor_patterns)} actors)')

    temporal = analyze_temporal_patterns(classifications, email_meta)
    print(f'  ✓ Temporal patterns   ({len(temporal)} clients)')

    days_in_window = compute_days_in_window(email_meta)
    print(f'   Data window: {days_in_window} days')

    automation_clusters = find_automation_clusters(classifications, days_in_window)
    print(f'  ✓ Automation clusters ({len(automation_clusters)} opportunities)')

    chains = find_workflow_chains(classifications, email_meta)
    print(f'  ✓ Workflow chains     ({len(chains)} chains)')

    # Print console report
    print_report(workflow_freq, actor_patterns, automation_clusters, chains)

    # Save JSON output
    output = {
        'generated_at': datetime.now().isoformat() + 'Z',
        'summary': {
            'total_classifications': len(classifications),
            'clients_analyzed': len(workflow_freq),
            'actors_identified': len(actor_patterns),
            'automation_opportunities': len(automation_clusters),
            'workflow_chains_found': len(chains),
            'data_window_days': days_in_window,
        },
        'workflow_frequency_by_client': workflow_freq,
        'actor_workflow_patterns': actor_patterns,
        'temporal_patterns': temporal,
        'automation_clusters': automation_clusters,
        'workflow_chains': chains,
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f'\n✅ Pattern analysis saved to: {args.output}')


if __name__ == '__main__':
    main()
