# Email Categorization System for Nauta

**Version:** 1.0  
**Last Updated:** February 16, 2026  
**Owner:** Data Team - Nauta

---

## Overview

This document defines the complete categorization system for emails in Nauta's supply chain operations. The system extracts incidents, positive signals, entities, and contextual insights from email communications to power Ask Nauta's intelligence layer.

### Goals
1. **Detect operational incidents** (delays, costs, compliance issues)
2. **Extract entities** (POs, bookings, containers, invoices, etc.)
3. **Analyze sentiment** and urgency levels
4. **Identify positive signals** (proactive communication, issue resolution)
5. **Generate actionable insights** for Ask Nauta queries

### Critical Principle
**`queue_id` is sacred** - It's the primary key that links email context to structured entities in Nauta. ALWAYS extract and preserve it.

---

## 1. Entity Extraction (ALWAYS REQUIRED)

### System Identifiers
Extract these from every email:
- **`queue_id`** ⭐ (CRITICAL - links to Nauta entities in database)
- **`thread_id`** (groups related conversations)
- **`message_id`** (unique message identifier)
- **`is_thread`** (boolean - part of conversation?)

### Document Numbers
Look for patterns like:
- **Purchase Orders**: `PO6904`, `PO-18931`, `PO 6904-1`
- **Customer POs**: `21228`, `CPO 21747`
- **Sales Orders**: `SO 2009581`, `202553095833`
- **Booking Numbers**: `259491393`, `262304038`, `BKG#262304216`
- **Container Numbers**: `TCNU7158122`, `MRKU2436770`, `MSDU7354557`
- **BL Numbers**: 
  - Master BL (MBL): `257365778`, `MAEU 255847092`
  - House BL (HBL): `PYMNITJ7093061`, `SGNOE250075`
- **Invoices**: `2000038827`, `Invoice 2000038827`
- **Levante** (Customs release): `925218858`
- **Form 7501** (US Customs Entry)
- **ISF Number** (Importer Security Filing)

### Stakeholders
Extract company names and roles:
- **Shippers/Suppliers**: ADLR Trading, BZ Furniture, Hyde Guangzhou, LG Electronics
- **Consignees**: Empresas Berrios, IMI Group
- **Forwarders**: BC Global Logistics, Elements International Group, Eagle Logistics, CEVA, Girafsail
- **Carriers**: Maersk (MAEU), Hamburg Sud (HLCU), MSC (MEDU), Hapag Lloyd, ONE
- **Customs Brokers**: RE Delgado
- **NVOCC**: Longsail Shipping Line, Pyramid Lines

### Transport Details
- **Vessel Name**: POLAR ARGENTINA, ADELIE P, GUNVOR MAERSK
- **Voyage Number**: 541N, 538E, 2541S
- **Container Type**: 40HC, 40HQ, 20DV
- **IMO Number**: 9399789
- **SCAC Code**: MAEU, LUCN, HLCU

### Locations
- **POL** (Port of Loading): La Paz, Vung Tau, Ho Chi Minh, Shanghai
- **POD** (Port of Discharge): San Juan PR, Chennai, Ennore
- **Transit Port**: Manzanillo Panama, Caucedo
- **Final Destination**: Cidra PR, Carolina PR

### Dates
Extract all mentioned dates:
- **ETD** (Estimated Time of Departure)
- **ETA** (Estimated Time of Arrival)
- **Actual Departure/Arrival**
- **CRD** (Customer Required Date)
- **Gate-in Date**
- **Discharge Date**
- **Last Free Date**
- **Document Deadlines**

### Financial Information
- **Freight Rates**: `$1,800/40HC`, `USD 3,615/40HQ`
- **Detention/Demurrage**: `$3,710`, `USD 4,550`
- **Free Time**: `9 days`, `13 days combined`, `23 days`
- **Taxes**: `11.5% IVU`, `10.5% payment to Hacienda`

---

## 2. Incident Categories

### A. DELAYS & DISRUPTIONS

#### Supplier Delays
- Late production/manufacturing
- Booking cancelled due to production delays
- Missing/incomplete shipment ready
- Documentation delays from supplier
- Quality issues causing holdups

#### Maritime/Carrier Delays
**High Priority:**
- **Vessel Rollover** ⭐ - Container loses space, must wait for next sailing
- **Vessel Omission/Skip** ⭐ - Vessel skips port, containers transshipped elsewhere

**Standard:**
- Vessel schedule changes
- Port congestion
- Transshipment delays
- Equipment/container shortages
- Weather-related delays
- Blank sailings (cancelled voyages)

#### Port/Terminal Delays
- Terminal congestion
- Equipment availability issues
- Port strikes/labor issues
- Berthing delays
- Extended gate hours (note: can be positive if announced proactively)

#### Customs Delays
- Documentation review/missing documents
- Physical inspection (Red channel)
- Valuation disputes
- HS code classification issues
- Compliance holds (permits, licenses)
- **Levante delayed/pending** ⭐
- **Form 7501 delayed** ⭐

#### Documentation Delays
**Critical (time-sensitive):**
- **Missing/delayed ISF** ⭐ (must be filed 24hrs before loading)
- **Missing/delayed BL/AWB** ⭐
- **HBL not transmitted** ⭐ (shows released but not in system)

**Standard:**
- Missing commercial invoice
- Missing packing list
- Missing/delayed shipping instructions (SI)
- Missing delivery order (DO)
- Missing certificates
- Document format incorrect/rework required

---

### B. COST CHANGES & SURCHARGES

#### Product Pricing
- Unit price increases
- Currency fluctuation impacts
- Invoice price discrepancies
- Correction requests

#### Freight & Logistics Fees
**Major:**
- Ocean/air freight rate changes
- Market rate updates (increases/decreases)

**Surcharges:**
- **BAF** (Bunker Adjustment Factor) - fuel surcharge
- **CAF** (Currency Adjustment Factor)
- **PSS** (Peak Season Surcharge)

**Container Fees (HIGH PRIORITY):**
- **Detention** ⭐ - Equipment rental after free time expires
- **Demurrage** ⭐ - Port storage after free time expires
- **Combined Dem/Det** charges
- Storage fees
- Chassis fees

**Other:**
- Cancel fees (booking cancellations)
- Amendment fees (BL changes, payer changes)
- Processing fees
- Transshipment fees

#### Duties & Tariffs
- **Puerto Rico Excise Tax** ⭐ (11.5% IVU, 10.5% paid through SURI)
- VAT/IVA changes
- Customs duties adjustments
- Tariff rate changes
- Anti-dumping duties
- Section 301 charges (US)

#### Other Fees
- Customs brokerage changes
- AMS (Automated Manifest System) fees
- Inspection fees
- Late payment penalties

---

### C. OPERATIONAL ISSUES

#### Process/Communication
- Wrong email routing
- **PO-Booking mapping confusion** ⭐
- **IOR (Importer of Record) confusion** ⭐
- Multiple follow-ups without response
- Missing information requests
- Multi-party coordination issues
- Unclear tax/duty responsibility

#### Documentation Quality
- Incorrect document format
- Content/specifications unclear
- Rework required
- BL format/content disputes
- Pending items noted (e.g., "*Pendiente ISF")

#### System/Technical
- BL not released in system (despite physical release)
- HBL transmission delays
- Platform integration issues

#### Compliance
- Regulatory violations
- License/permit issues
- Documentation non-compliance

---

### D. POSITIVE SIGNALS ✅

#### Document Availability
- BL ready for download
- Arrival Notice issued
- VGM submitted
- ISF filed successfully
- Delivery order issued
- Invoice provided

#### Proactive Notifications
- **Delay notices sent before being asked** ⭐
- ETA notifications
- Vessel schedule updates
- Gate hours extension announcements
- Document ready alerts

#### Customs Clearance
- **Import declaration approved** ⭐ (Levante aprobada)
- Green channel clearance
- No inspections required
- Form 7501 completed

#### Commercial Gestures
- Rate absorption/discounts
- Freight differential absorbed
- Expedited processing
- Waived fees
- Free time extensions offered
- Extra free time at discount

#### Operational Excellence
- Same-day resolution
- Issue resolved quickly
- Documentation complete on time
- Successful departure despite earlier issues
- Process improvement commitments

---

## 3. Sentiment Analysis

Analyze sentiment **per message** (not per thread):

### Sentiment Levels

**POSITIVE**
- Thanks, confirmations
- Issues resolved
- Successful completions

**NEUTRAL**
- Routine updates
- Standard requests
- Normal coordination

**CONCERNED**
- First follow-up
- Polite urgency
- Queries about missing responses

**URGENT**
- 2nd or 3rd follow-up
- Keywords: "urgente", "ASAP", "TODAY", "RUSH", "deadline"
- High priority markers

**CRITICAL/ESCALATED**
- 3rd+ follow-up
- Operational impact mentioned ("inventory blocked", "containers unloading")
- Management escalation
- Threat of penalties
- "Action Required" in subject

### Urgency Indicators
- **Follow-up count**: Track 1st, 2nd, 3rd+ attempts
- **Keywords**: ASAP, urgente, critical, lo antes posible, TODAY, RUSH
- **Frustration**: "aún no", "sin respuesta", "en espera", "3rd request"
- **Operational impact**: containers being unloaded, need to register expense, blocking operations
- **Escalation**: CC to managers, @mentions, "management is pushing"

---

## 4. Severity Classification

Assign severity to each incident:

**LOW**
- Routine questions
- Minor format issues resolved quickly
- Small delays (1-2 days)
- Standard requests

**MEDIUM**
- Documentation delays impacting timeline
- Vessel rollovers (3-7 days)
- Follow-ups without response
- Format issues requiring rework
- Moderate detention/demurrage ($1-5K)

**HIGH**
- Multiple delays on same shipment
- Critical docs missing near deadlines
- Significant financial impact ($5K+)
- Operational blocking (inventory, unloading)
- Multiple follow-ups escalating
- Customs holds
- Vessel omissions

**CRITICAL**
- Operations completely blocked
- Major financial exposure (>$10K or accumulating daily)
- Compliance violations
- Multi-stakeholder escalation
- 3rd+ follow-up without resolution
- Critical deadlines passed

---

## 5. Output JSON Schema

The output file has two top-level keys:

```json
{
  "timeline": [ ...flat chronological list of events... ],
  "emails":   [ ...full detail per email... ]
}
```

### 5.1 Email Record Schema

Generate this structure for EVERY email (stored under `emails`):

```json
{
  "queue_id": "required string - CRITICAL for linking",
  "thread_id": "string or null",
  "related_queue_ids": ["queue_id_1", "queue_id_2"],
  "message_id": "required string",
  "is_thread": true/false,
  "thread_message_count": 1,
  "processed_date": "2026-02-16T10:30:00Z",
  
  "email_metadata": {
    "from": "sender@example.com",
    "to": ["recipient@example.com"],
    "cc": ["cc@example.com"] or null,
    "subject": "Email subject",
    "inserted_at": "2025-09-29T13:25:12Z"
  },
  
  "entities": {
    "purchase_orders": ["PO6904-1"],
    "customer_pos": ["21228"],
    "sales_orders": ["2009581"],
    "bookings": ["259491393"],
    "containers": ["TCNU7158122"],
    "bl_numbers": ["257365778"],
    "mbl_numbers": [],
    "hbl_numbers": [],
    "invoices": [],
    "levantes": [],
    "form_7501": [],
    "isf_numbers": [],
    "vessels": [
      {
        "name": "POLAR ARGENTINA",
        "voyage": "541N",
        "imo": null
      }
    ],
    "shippers": ["ADLR Trading"],
    "consignees": ["Empresas Berrios"],
    "carriers": ["BC Global Logistics"],
    "maritime_lines": ["Hamburg Sud"],
    "customs_brokers": [],
    "pol": "La Paz",
    "pod": "San Juan, Puerto Rico",
    "transit_ports": [],
    "final_destination": null
  },
  
  "incidents": [
    {
      "category": "DELAY_DISRUPTION",
      "subcategory": "Maritime - Vessel Rollover",
      "severity": "HIGH",
      "date_detected": "2025-10-01",
      "date_resolved": "2025-10-09",
      "details": "Vessel rollover affecting booking 259491393. New ETD: 09-Oct.",
      "affected_entities": {
        "bookings": ["259491393"],
        "pos": ["PO6904-1"],
        "containers": ["TCNU7158122"]
      },
      "impact_description": "ETD changed from original date to 09-Oct",
      "resolution": "Container departed on POLAR ARGENTINA 541N on 09/10",
      "financial_impact": {
        "amount": null,
        "currency": "USD",
        "type": null
      },
      "proactive_notification": true
    }
  ],
  
  "positive_signals": [
    {
      "type": "PROACTIVE_COMMUNICATION",
      "date": "2025-10-01",
      "details": "Supplier proactively sent delay notice before being asked",
      "value": null
    }
  ],
  
  "sentiment_analysis": {
    "overall_sentiment": "URGENT",
    "urgency_level": "HIGH",
    "follow_up_count": 2,
    "escalation_detected": false,
    "action_required": true,
    "operational_impact": false
  },
  
  "key_dates": {
    "etd_original": null,
    "etd_revised": "2025-10-09",
    "eta_original": null,
    "eta_revised": null,
    "actual_departure": "2025-10-09",
    "actual_arrival": null,
    "discharge_date": null,
    "last_free_date": null,
    "document_deadline": null
  },
  
  "actions_required": [
    {
      "action": "Provide shipping instructions",
      "assignee": "IMI Container Operations",
      "status": "PENDING",
      "first_requested": "2025-09-26",
      "follow_ups": 2,
      "deadline": null
    }
  ],
  
  "email_type": "OPERATIONAL",

  "summary": "Booking 259491393 (PO6904-1) experienced vessel rollover with new ETD 09-Oct. Container successfully departed on POLAR ARGENTINA.",

  "context_for_ask_nauta": "User can query: Why was PO6904-1 delayed? Answer: Vessel rollover on booking 259491393, departed 09-Oct on POLAR ARGENTINA 541N."
}
```

---

### 5.1.1 Email Type Classification

The `email_type` field is **classified by the model** before any incident analysis. It determines whether the email has operational value and controls whether it appears in the timeline.

| Value | Description | Included in timeline |
|---|---|---|
| `OPERATIONAL` | Real communication between people about an active operation (delays, costs, document requests, follow-ups, negotiations) | ✅ Yes |
| `AUTO_NOTIFICATION` | Automated system message with operational value (BL ready, arrival notice, customs approval, vessel schedule update, booking confirmation) | ✅ Yes |
| `MARKETING` | Commercial proposal, unsolicited offer, sales pitch from a logistics provider or vendor | ❌ No |
| `READ_RECEIPT` | Confirmation that someone opened an email — subject usually starts with "Read:" — no operational content | ❌ No |
| `OTHER` | Anything that doesn't fit the above (scanned documents with no operational context, internal memos, etc.) | ❌ No |

> **Why classify in the model instead of filtering in the query?**
> Rule-based filters are never exhaustive — new marketing senders, new subject patterns, and new edge cases will always appear. Having the model classify email type is robust by design: it understands context, not just patterns.
> Query-level filters are still useful to avoid spending API calls on the most obvious cases (e.g. known spam senders), but they should be a cost optimization, not the primary quality gate.

---

### 5.2 Timeline Entry Schema

The `timeline` array is a **flat, chronological list** of all incidents and positive signals across all emails. Each entry contains the minimum context needed to read the event without looking up the full email.

**Ordering:** sorted by `date` (ISO 8601 ascending). Entries without a date are placed at the end.

**`event_type` values:** `INCIDENT` | `POSITIVE_SIGNAL`

```json
{
  "date": "2025-10-01",
  "event_type": "INCIDENT",
  "queue_id": "3e9aa899-...",
  "message_id": "CABxyz@mail.gmail.com",
  "thread_id": "thread_abc123",
  "subject": "RE: Booking 259491393 - Vessel Rollover",
  "actors": {
    "from": "supplier@example.com",
    "to": ["ops@nauta.com"]
  },
  "sentiment": "URGENT",
  "incident_type": "DELAY_DISRUPTION",
  "subcategory": "Maritime - Vessel Rollover",
  "severity": "HIGH",
  "affected_entities": {
    "bookings": ["259491393"],
    "pos": ["PO6904-1"],
    "containers": ["TCNU7158122"]
  },
  "financial_impact": {
    "amount": null,
    "currency": "USD",
    "type": null
  },
  "details": "Vessel rollover affecting booking 259491393. New ETD: 09-Oct.",
  "resolved": true,
  "resolution": "Container departed on POLAR ARGENTINA 541N on 09/10",
  "summary": "Booking 259491393 (PO6904-1) experienced vessel rollover with new ETD 09-Oct."
}
```

For **positive signals**, `incident_type` and `severity` are `null`, and `subcategory` holds the signal type (e.g., `PROACTIVE_COMMUNICATION`).

---

## 6. Special Cases & Edge Cases

### Thread vs Single Message
- **is_thread = true**: Part of conversation, analyze in context of previous messages
- **is_thread = false**: Standalone notification (arrival notice, BL ready, etc.)

### Automatic Notifications
Don't over-alert on routine system notifications:
- Arrival notices (NEUTRAL, unless late)
- BL ready notifications (POSITIVE_SIGNAL)
- ETA updates (NEUTRAL, unless significant change)

### Multiple Incidents in One Email
A single email can have multiple incidents. Example:
- Vessel rollover (DELAY_DISRUPTION)
- Rate increase announced (COST_CHANGES)
- Detention charges accruing (COST_CHANGES)

### Puerto Rico Specific
- **IVU Tax**: 11.5% sales tax, but importers pay 10.5% through SURI system
- **SURI**: Puerto Rico's tax filing system
- **Form 7501**: US Customs entry form (PR is US territory)
- **Levante**: Local term for customs release

### Acronyms Reference
- **POL**: Port of Loading
- **POD**: Port of Discharge
- **ETD**: Estimated Time of Departure
- **ETA**: Estimated Time of Arrival
- **BL**: Bill of Lading
- **MBL**: Master Bill of Lading
- **HBL**: House Bill of Lading
- **AWB**: Airway Bill
- **ISF**: Importer Security Filing (US requirement)
- **VGM**: Verified Gross Mass
- **AMS**: Automated Manifest System
- **SCAC**: Standard Carrier Alpha Code
- **IMO**: International Maritime Organization number
- **IOR**: Importer of Record
- **NVOCC**: Non-Vessel Operating Common Carrier
- **BAF**: Bunker Adjustment Factor
- **CAF**: Currency Adjustment Factor
- **PSS**: Peak Season Surcharge
- **IVU**: Impuesto sobre Ventas y Uso (Puerto Rico sales tax)
- **DEM**: Demurrage
- **DET**: Detention

---

## 7. Implementation Guidelines

### Processing Priority
1. **Extract `queue_id` first** - fail if not found
2. **Extract all entities** - be thorough, these power Ask Nauta
3. **Identify incidents** - focus on high/critical severity
4. **Detect positive signals** - they're valuable context
5. **Analyze sentiment** - per message, not aggregate
6. **Generate summary** - concise, actionable

### Quality Checks
Before outputting JSON:
- `queue_id` is present and valid
- At least one entity extracted (PO, booking, container, etc.)
- Dates are in ISO 8601 format
- Amounts are numbers, not strings
- Arrays are never null (use empty array `[]` instead)
- Sentiment levels are from defined set
- Severity levels are from defined set

### Context for Ask Nauta
The `context_for_ask_nauta` field should be written as:
- **Clear natural language** that Ask Nauta can use to answer user questions
- **Include key entities** (PO numbers, container numbers, dates)
- **Explain cause and effect** when applicable
- **Mention resolution** if incident was resolved

**Example:**
```
"Booking 259491393 for PO6904-1 experienced vessel rollover on 01-Oct, 
changing ETD to 09-Oct. Container TCNU7158122 successfully departed on 
POLAR ARGENTINA 541N. BC Global absorbed freight differential of $X as 
commercial gesture."
```

---

## 8. Testing & Validation

### Test Cases
Validate your implementation with these scenarios:

1. **Simple delay notification**
   - Should detect: delay incident, vessel name, new ETD
   - Sentiment: NEUTRAL (if proactive) or CONCERNED (if reactive)

2. **Demurrage warning**
   - Should detect: cost incident, amounts, affected containers
   - Severity: HIGH or CRITICAL (based on amount and days)
   - Sentiment: URGENT or CRITICAL

3. **Thread with multiple follow-ups**
   - Should track: follow-up count, escalation pattern
   - Sentiment: Should escalate from CONCERNED → URGENT → CRITICAL

4. **Customs approval**
   - Should detect: positive signal, levante number
   - Sentiment: POSITIVE

5. **Vessel omission**
   - Should detect: high severity delay, transshipment
   - Affected entities: all bookings/containers on vessel

### Success Metrics
- **Entity extraction**: >90% of POs, bookings, containers found
- **Incident detection**: >85% of delays, cost issues detected
- **Severity accuracy**: >80% match with manual review
- **False positive rate**: <10% for critical incidents

---

## 9. Maintenance & Evolution

### When to Update This Document
- New incident types discovered in production
- New entity types added to Nauta
- Integration requirements change (Ask Nauta needs new fields)
- Severity thresholds need adjustment

### Feedback Loop
After deployment:
1. **Review misclassified emails** weekly
2. **Update categories** if patterns emerge
3. **Adjust severity thresholds** based on user feedback
4. **Refine context generation** based on Ask Nauta query quality

---

## 10. Contact & Support

**Document Owner:** Data Team - Nauta  
**For Questions Contact:**
- Emilio (Data Analytics)
- Imanol (AI Features / Ask Nauta)
- Ale (PRISMA Integration)

**Repository:** `nauta-data-airflow/docs/`  
**Related Systems:** PRISMA, Ask Nauta, Databricks

---

**End of Document**