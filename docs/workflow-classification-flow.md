# Flujo de Clasificación de Workflows y Detección de Patrones

**Versión:** 1.0
**Fecha:** Febrero 2026
**Scripts:** `classify_workflows.py` → `find_patterns.py`

---

## ¿Para qué sirve esto?

El pipeline base (categorize_emails.py) ya detecta **qué pasó** en cada email: incidentes, sentimiento, entidades. Pero no responde una pregunta clave para la automatización:

> *"¿Qué paso operativo representa este email, quién lo dispara y con qué frecuencia se repite?"*

Estos dos scripts añaden esa capa. Juntos responden preguntas como:
- "Crowley le envía a Econo un Arrival Notice todos los lunes — ¿se puede automatizar esa captura?"
- "El 73% de los emails de customs son Document Requests del mismo broker — ¿hay un patrón procesable?"
- "Este thread siempre sigue la secuencia Vessel Update → Arrival Notice → Pickup Coordination"

---

## Visión general del pipeline completo

```
data/test_emails.csv
        │
        ▼
┌─────────────────────────┐
│   categorize_emails.py  │  ← Paso 1 (ya ejecutado)
│   (LLM pass completo)   │  Extrae: incidentes, entidades,
└─────────────┬───────────┘  sentimiento, email_type
              │
              ▼
  output/categorized_emails.json
              │
              │  (también lee data/test_emails.csv)
              ▼
┌─────────────────────────┐
│  classify_workflows.py  │  ← Paso 2 (nuevo)
│  (LLM pass liviano)     │  Clasifica: workflow_type,
└─────────────┬───────────┘  trigger_actor, automation_potential
              │
              ▼
  output/workflow_classifications.json
              │
              ▼
┌─────────────────────────┐
│     find_patterns.py    │  ← Paso 3 (nuevo)
│  (análisis estadístico) │  Agrega: frecuencias, actores,
└─────────────┬───────────┘  patrones temporales, cadenas
              │
              ▼
  output/pattern_analysis.json
  + reporte en consola
```

---

## Paso 2: `classify_workflows.py`

### Qué hace

Por cada email que no sea MARKETING, READ_RECEIPT u OTHER, hace **una llamada liviana a Claude** con:
- `from_email` + `subject` + primeros 1000 caracteres del body limpio + `email_type`

El modelo devuelve un JSON pequeño con la clasificación del workflow.

### Taxonomía de workflows

| Categoría | Tipos posibles |
|---|---|
| `TRACKING` | ARRIVAL_NOTICE · VESSEL_UPDATE · CONTAINER_STATUS |
| `DOCUMENTATION` | BL_RELEASE · DELIVERY_ORDER · CUSTOMS_CLEARANCE · ISF_FILING · DOCUMENT_REQUEST |
| `FREIGHT` | BOOKING_CONFIRMATION · CARGO_READY · PICKUP_COORDINATION · VESSEL_ROLLOVER_NOTICE |
| `BILLING` | FREIGHT_INVOICE · DETENTION_DEMURRAGE_NOTICE · RATE_QUOTE |
| `COMMUNICATION` | STATUS_UPDATE · FOLLOW_UP · ESCALATION · OTHER |

### Tipos de actores que pueden disparar el workflow

```
CARRIER | FORWARDER | CUSTOMS_BROKER | WAREHOUSE | SUPPLIER | CLIENT | NAUTA | SYSTEM
```

### Output por email

```json
{
  "queue_id": "6bf7ab15-...",
  "client_name": "Econo",
  "email_type": "AUTO_NOTIFICATION",
  "workflow_category": "TRACKING",
  "workflow_type": "ARRIVAL_NOTICE",
  "workflow_step": "NOTIFICATION",
  "trigger_actor_type": "CARRIER",
  "trigger_actor_name": "crowley.com",
  "is_routine": true,
  "recurrence_signals": ["automated notification", "weekly batch"],
  "automation_potential": "HIGH",
  "automation_reason": "Standardized carrier notification sent automatically on vessel arrival, no human input required."
}
```

### Lógica de skips y reanudación

El script es idempotente: si se interrumpe, puede reanudarse sin reprocesar emails ya clasificados.

```
Email en CSV
    │
    ├── ¿Ya clasificado en output/workflow_classifications.json?
    │       └── Sí → skip (reanudación)
    │
    ├── ¿email_type es MARKETING / READ_RECEIPT / OTHER?
    │       └── Sí → skip (no operativo)
    │
    └── No → llamada a Claude → guardar resultado
```

### Costo estimado

| Volumen | Tokens aprox. | Costo estimado |
|---|---|---|
| 500 emails | ~200K input + ~50K output | ~$2–3 USD |
| 36K emails (full) | ~14M input | ~$150–200 USD |

Se usa `max_tokens=512` (respuesta pequeña, solo JSON) y `temperature=0` (clasificación determinista).

### Cómo ejecutar

```bash
# Ejecución completa
python3 scripts/classify_workflows.py

# Prueba con 20 emails
python3 scripts/classify_workflows.py --limit 20

# Custom paths
python3 scripts/classify_workflows.py \
  --input data/test_emails.csv \
  --categorized output/categorized_emails.json \
  --output output/workflow_classifications.json
```

---

## Paso 3: `find_patterns.py`

### Qué hace

No llama a ninguna API. Lee `workflow_classifications.json` y `categorized_emails.json`, cruza los datos estadísticamente y produce cinco tipos de análisis.

### Análisis 1 — Frecuencia de workflows por cliente

Responde: *"¿Qué tipo de comunicación domina para cada cliente?"*

```
Econo (93 emails)
  ARRIVAL_NOTICE          38.7%  ████████
  BOOKING_CONFIRMATION    22.6%  █████
  DOCUMENT_REQUEST        12.9%  ███
```

### Análisis 2 — Patrón actor → workflow

Responde: *"¿Qué workflows dispara cada actor de forma consistente?"*

Agrupa por `trigger_actor_name`, calcula la distribución de `workflow_type`, y reporta los actores con ≥ 3 emails.

```
crowley.com               → ARRIVAL_NOTICE      (87.0%,  n=23)
kuehne-nagel.com          → DOCUMENT_REQUEST    (64.0%,  n=14)
customs-broker@xyz.com    → CUSTOMS_CLEARANCE   (71.4%,  n=7)
```

### Análisis 3 — Patrones temporales

Responde: *"¿Qué días de la semana se concentran ciertos workflows?"*

Cruza `inserted_at` del email original con `workflow_type` para construir una tabla por cliente:

```json
"Econo": [
  { "day": "Monday",    "total": 18, "top_workflows": [{"ARRIVAL_NOTICE": 12}] },
  { "day": "Wednesday", "total": 11, "top_workflows": [{"DOCUMENT_REQUEST": 7}] }
]
```

Esto permite detectar ritmos operativos semanales — por ejemplo, "Econo recibe Arrival Notices los lunes".

### Análisis 4 — Clusters de automatización

Responde: *"¿Cuáles son las mejores oportunidades de automatización y cuánto volumen representan?"*

Agrupa por `(cliente, workflow_type, trigger_actor_type)` considerando solo registros con `automation_potential = HIGH | MEDIUM`.

Calcula:
- **Volumen mensual estimado** (asume ventana de 90 días)
- **Routine rate** — % de emails marcados como `is_routine`
- **Top recurrence signals** — señales que el modelo detectó

```json
{
  "client": "Econo",
  "workflow_type": "ARRIVAL_NOTICE",
  "trigger_actor_type": "CARRIER",
  "email_count": 21,
  "estimated_monthly_volume": 7.0,
  "routine_rate_pct": 95.2,
  "top_recurrence_signals": ["automated notification", "weekly pattern"],
  "sample_reason": "Standardized carrier notification, no human decision needed."
}
```

### Análisis 5 — Cadenas de workflows

Responde: *"¿Qué secuencias de pasos aparecen consistentemente en el mismo thread?"*

Agrupa por `thread_id` (del email original), ordena por `inserted_at`, y cuenta sub-cadenas de 2 y 3 pasos.

```
VESSEL_UPDATE → ARRIVAL_NOTICE                          (n=14)
ARRIVAL_NOTICE → PICKUP_COORDINATION                    (n=11)
VESSEL_UPDATE → ARRIVAL_NOTICE → PICKUP_COORDINATION    (n=8)
DOCUMENT_REQUEST → CUSTOMS_CLEARANCE                    (n=6)
```

Estos patrones revelan los **procesos completos** que hoy están fragmentados en emails, y son el insumo directo para modelar workflows en PRISMA.

### Output JSON

```json
{
  "generated_at": "2026-02-24T...",
  "summary": {
    "total_classifications": 487,
    "clients_analyzed": 26,
    "actors_identified": 34,
    "automation_opportunities": 18,
    "workflow_chains_found": 12
  },
  "workflow_frequency_by_client": { ... },
  "actor_workflow_patterns": { ... },
  "temporal_patterns": { ... },
  "automation_clusters": [ ... ],
  "workflow_chains": [ ... ]
}
```

### Cómo ejecutar

```bash
# Requiere que classify_workflows.py ya haya corrido
python3 scripts/find_patterns.py

# Custom paths
python3 scripts/find_patterns.py \
  --classifications output/workflow_classifications.json \
  --categorized output/categorized_emails.json \
  --output output/pattern_analysis.json
```

---

## Orden de ejecución completo

```bash
# 1. Categorización base (ya ejecutado, genera categorized_emails.json)
python3 scripts/categorize_emails.py

# 2. Clasificación de workflows (segundo LLM pass, ~$2-3 para 500 emails)
python3 scripts/classify_workflows.py

# 3. Detección de patrones (sin costo, solo estadísticas)
python3 scripts/find_patterns.py
```

---

## Archivos de entrada y salida

| Script | Lee | Escribe |
|---|---|---|
| `categorize_emails.py` | `data/test_emails.csv` | `output/categorized_emails.json` |
| `classify_workflows.py` | `data/test_emails.csv` + `output/categorized_emails.json` | `output/workflow_classifications.json` |
| `find_patterns.py` | `output/workflow_classifications.json` + `output/categorized_emails.json` | `output/pattern_analysis.json` |

`categorized_emails.json` sirve a los dos scripts nuevos: `classify_workflows.py` lo usa para filtrar por `email_type`, y `find_patterns.py` lo usa para cruzar `thread_id` e `inserted_at`.
