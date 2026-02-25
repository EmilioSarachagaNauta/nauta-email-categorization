# Workflow Intelligence — Email Automation Opportunities
### Nauta · Data Team · Febrero 2026

---

## SLIDE 1 — Portada

**Workflow Intelligence**
Identificación de automatización en operaciones de supply chain a partir de emails

> Nauta · Data Team · Febrero 2026

---

## SLIDE 2 — ¿Qué problema resolvemos?

**El equipo de operaciones vive en el inbox**

- Los operadores procesan cientos de emails por semana — llegada de contenedores, liberaciones de BL, coordinaciones de pickup, facturas de flete
- Cada email es procesado manualmente: se lee, se interpreta, se actúa
- **No sabemos qué porcentaje de ese trabajo es rutina pura vs. decisión real**

> *"Si no sabemos qué es rutina, no podemos automatizarlo"*

---

## SLIDE 3 — Qué hicimos

**Analizamos 851 emails operativos con IA**

Pipeline de dos pasos:

1. **Clasificación de workflows** — Claude lee cada email y lo etiqueta con el paso operativo que representa (Arrival Notice, BL Release, Pickup Coordination, etc.) más quién lo dispara y si es automatizable

2. **Detección de patrones** — Agregamos las clasificaciones para encontrar qué actores hacen qué de forma consistente, qué cadenas de pasos ocurren siempre juntas, y cuáles son las mejores oportunidades de automatización

**Muestra:** 5 clientes (Econo, Ballester, B Fernandez, Berrios, Me Salve) · Enero–Febrero 2026

---

## SLIDE 4 — Taxonomía de workflows detectados

**Cada email = un paso operativo identificado**

| Categoría | Tipos |
|---|---|
| **TRACKING** | Arrival Notice · Vessel Update · Container Status |
| **DOCUMENTATION** | BL Release · Delivery Order · Customs Clearance · ISF Filing · Document Request |
| **FREIGHT** | Booking Confirmation · Cargo Ready · Pickup Coordination · Vessel Rollover |
| **BILLING** | Freight Invoice · Detention & Demurrage · Rate Quote |
| **COMMUNICATION** | Status Update · Follow Up · Escalation |

**Resultado:** 52 actores identificados · 20 oportunidades de automatización · 8 cadenas de workflow

---

## SLIDE 5 — Perfil operativo por cliente

**Cada cliente tiene un patrón de comunicación distinto**

| Cliente | Workflow dominante | % del total |
|---|---|---|
| **Me Salve** | Document Request | 40% |
| **Econo** | Status Update | 20% |
| **Berrios** | Arrival Notice | 19% |
| **Ballester** | Pickup Coordination | 17% |
| **B Fernandez** | Freight Invoice | 13% |

> Me Salve dedica el 40% de su comunicación a solicitar documentos — un proceso altamente repetitivo y estructurado.

---

## SLIDE 6 — Actores con comportamiento predecible

**Algunos actores hacen siempre lo mismo — son candidatos directos a automatización**

| Actor | Workflow principal | Consistencia | Volumen |
|---|---|---|---|
| **Acumatica / SuperEcono** | Status Update | **100%** | 26 emails |
| **admincomp.com** | Document Request | **97.5%** | 40 emails |
| **ML Agency** | Delivery Order | **96%** | 25 emails |
| **Puerto Rico Hacienda** | Customs Clearance | **100%** | 16 emails |
| **Hapag-Lloyd** | Arrival Notice | **77%** | 13 emails |
| **Maersk** | Arrival Notice | **62%** | 60 emails |
| **TOTE Maritime** | BL Release | **51%** | 47 emails |

> Un actor con 100% de consistencia es un **trigger determinista** — no necesita interpretación humana.

---

## SLIDE 7 — Top oportunidades de automatización

**Ranking por volumen + rutina**

| # | Cliente | Workflow | Actor | Emails | Rutina |
|---|---|---|---|---|---|
| 1 | **Me Salve** | Document Request | CLIENT | 45 | 100% |
| 2 | **Berrios** | Arrival Notice | CARRIER | 34 | 100% |
| 3 | **Econo** | Status Update | SYSTEM | 26 | 100% |
| 4 | **Econo** | BL Release | CARRIER | 26 | 100% |
| 5 | **Berrios** | Delivery Order | FORWARDER | 24 | 100% |
| 6 | **Econo** | Pickup Coordination | CLIENT | 16 | 100% |
| 7 | **Berrios** | Customs Clearance | SYSTEM | 16 | 100% |
| 8 | **Econo** | Document Request | CLIENT | 15 | 100% |

> **100% routine rate** en todos los top 8 — el modelo no encontró ningún email de estos tipos que requiriera juicio humano.

---

## SLIDE 8 — Ejemplo completo: lo que obtenemos de un email

**De texto libre a inteligencia estructurada — en un solo paso**

---

**EMAIL ORIGINAL** *(lo que llega al inbox)*

```
De:      donotreply@totemaritime.com
Para:    ops@nauta.com
Asunto:  Bill of Lading Released – Vessel TROPICAL FANTASY / Voyage 2501N

Your Bill of Lading for the below shipment has been released.

Booking Reference:  CWPS26150023
Vessel / Voyage:    TROPICAL FANTASY / 2501N
Port of Loading:    Jacksonville, FL
Port of Discharge:  San Juan, PR
Client:             Econo / Supermercados Econo Inc.
```

---

**OUTPUT GENERADO** *(lo que el sistema extrae)*

```json
{
  "queue_id":           "49b73475-3c19-46d3-83a8-95ab72a60ffd",
  "client_name":        "Econo",
  "workflow_category":  "DOCUMENTATION",
  "workflow_type":      "BL_RELEASE",
  "workflow_step":      "NOTIFICATION",
  "trigger_actor_type": "CARRIER",
  "trigger_actor_name": "TOTE Maritime Puerto Rico",
  "is_routine":         true,
  "recurrence_signals": [
    "automated notification",
    "DONOTREPLY email address",
    "vessel reference number",
    "standard document release format"
  ],
  "automation_potential": "HIGH",
  "automation_reason": "Standard carrier document release notification with
                        structured vessel reference — no human judgment needed."
}
```

---

**LO QUE ESTO HABILITA**

| Hoy (manual) | Con este output |
|---|---|
| Operador lee el email | Sistema detecta `BL_RELEASE` de `TOTE Maritime` |
| Busca el booking en PRISMA | Cruza automáticamente con `CWPS26150023` |
| Marca el BL como liberado | Actualiza el estado del shipment en PRISMA |
| Notifica al cliente | Dispara notificación automática a Econo |
| ~5–10 min por email | **< 1 segundo** |

> TOTE Maritime envía este mismo formato en el **51% de sus 47 emails** — todos procesables sin intervención humana.

---

## SLIDE 9 — Tres emails, tres perfiles distintos

**El sistema distingue contexto, no solo palabras clave**

---

**Email 1 — Rutina pura (HIGH)**
```
Actor:    Hacienda Puerto Rico (sistema gubernamental)
Workflow: CUSTOMS_CLEARANCE · NOTIFICATION
Routine:  ✅ 100% consistente en 16 emails
Razón:    Notificación estándar del sistema SURI — formato idéntico siempre
Acción:   Actualizar estado de levante en PRISMA automáticamente
```

**Email 2 — Rutina con señales de recurrencia (HIGH)**
```
Actor:    Longsail Supply Chain (forwarder)
Workflow: DOCUMENT_REQUEST · NOTIFICATION
Signals:  "pre-alerts notification", "standardized ATD/ETA format",
          "routine invoice confirmation"
Razón:    Pre-alert estandarizado — misma estructura en cada embarque
Acción:   Parsear ATD/ETA y crear tarea de seguimiento de documentos
```

**Email 3 — Requiere atención (MEDIUM)**
```
Actor:    bfernandez.com (cliente)
Workflow: FOLLOW_UP · ESCALATION
Routine:  ⚠️ No rutinario
Razón:    Segundo seguimiento sin respuesta — requiere acción humana
Acción:   Escalar a operador responsable con contexto del thread
```

> El sistema no solo clasifica — **diferencia lo que se puede automatizar de lo que necesita un humano**.

---

## SLIDE 10 — Cadenas de workflow detectadas

**Secuencias que ocurren siempre sobre el mismo shipment**

```
ARRIVAL_NOTICE      → FREIGHT_INVOICE          (5 veces)  BKG: CAT40053191, HLCUME326...
CUSTOMS_CLEARANCE   → DOCUMENT_REQUEST         (3 veces)  BKG: CAT40054963, 08919448
BOOKING_CONFIRMATION → PICKUP_COORDINATION     (2 veces)  PO: CSPO111427, BF-115239
ISF_FILING          → DOCUMENT_REQUEST         (2 veces)  BKG: 265285216, 24143
FOLLOW_UP           → BL_RELEASE               (2 veces)  BKG: 08919448, CWPS26150023
PICKUP_COORDINATION → FREIGHT_INVOICE          (2 veces)  PO: 24026597, 24026220
ARRIVAL_NOTICE      → DOCUMENT_REQUEST         (2 veces)  PO: 23169, 23173
```

> Estas cadenas representan **procesos completos fragmentados en emails**. Cada flecha es un paso que hoy se hace manualmente y podría dispararse automáticamente cuando el anterior se completa.

---

## SLIDE 11 — Caso concreto: Arrival Notice → Freight Invoice

**El proceso más claro de automatización end-to-end**

**Hoy (manual):**
1. Maersk envía Arrival Notice → operador lo lee y lo registra
2. Días después Maersk envía Freight Invoice → operador lo procesa

**Con automatización:**
1. Maersk envía Arrival Notice → **sistema lo parsea y actualiza ETA en PRISMA automáticamente**
2. Freight Invoice llega → **sistema lo cruza con el booking y lo enruta a cuentas por pagar**

**Señal en los datos:** Maersk envía Arrival Notice en el 62% de sus emails (60 en la muestra). El formato es estructurado y consistente — cero decisión humana requerida.

---

## SLIDE 12 — Qué significa esto para PRISMA y Ask Nauta

**Dos impactos directos**

### Para PRISMA
- Hoy PRISMA extrae entidades (POs, bookings, contenedores) pero **no sabe qué paso del proceso representa cada email**
- Con workflow classification, PRISMA puede etiquetar cada email con su `workflow_type` y actualizar automáticamente el estado del shipment
- Ejemplo: cuando llega un `BL_RELEASE` de TOTE Maritime → PRISMA marca el BL como liberado sin que nadie lo lea

### Para Ask Nauta
- Las cadenas de workflow permiten **anticipar el siguiente paso**
- Si un booking está en `ARRIVAL_NOTICE`, el próximo evento probable es `FREIGHT_INVOICE` o `DOCUMENT_REQUEST`
- Ask Nauta puede proactivamente alertar: *"El contenedor de Berrios llega esta semana — esperá la factura de Maersk y la solicitud de documentos de ML Agency"*

---

## SLIDE 13 — Next steps propuestos

**Tres conversaciones que hay que tener**

### Con Imanol (Ask Nauta)
- ¿Qué contexto de workflow_type necesita Ask Nauta para mejorar sus respuestas?
- ¿Las cadenas detectadas mejoran las respuestas proactivas?
- Integración: ¿consume `workflow_classifications.json` como input adicional?

### Con el equipo de PRISMA
- ¿Se agrega `workflow_type` como campo en `agent_results`?
- ¿Se corre `classify_workflows.py` en el pipeline de procesamiento o como batch separado?
- Triggers automáticos: cuando `workflow_type = BL_RELEASE` y `trigger_actor = TOTE` → acción en sistema

### Con Operations
- Validar los top 8 clusters con los operadores: ¿coincide con su intuición?
- Identificar el primer workflow a automatizar end-to-end (candidato: **Econo BL Release**)
- Definir métricas de éxito: horas/semana recuperadas, emails procesados sin intervención

---

## SLIDE 14 — Esfuerzo y escala

**Lo que se hizo y lo que falta**

| | Hecho | Siguiente paso |
|---|---|---|
| **Muestra** | 851 emails · 5 clientes | Escalar a todos los clientes (~36K emails) |
| **Costo LLM** | ~$4–5 USD | ~$150–200 USD para universo completo |
| **Pipeline** | Script local manual | Integrar en Databricks / correr cada semana |
| **Output** | JSON estático | Feed a PRISMA + dashboard de patrones |
| **Validación** | Automática (100% rutina) | Revisión con operadores en 2 sesiones |

> El pipeline está construido, probado y documentado. La inversión para escalar es mínima.

---

## SLIDE 15 — Resumen ejecutivo

**Lo que encontramos en 851 emails**

- **52 actores identificados** — carriers, forwarders, brokers, sistemas — cada uno con un comportamiento predecible
- **Top 8 oportunidades** todas con 100% de routine rate — ninguna requiere juicio humano
- **8 cadenas de workflow** que mapean procesos completos hoy fragmentados en emails
- **Actores deterministas**: Acumatica, admincomp.com, ML Agency, Hacienda — siempre hacen lo mismo

**La oportunidad:** Una fracción significativa del tiempo que operaciones dedica al inbox es trabajo de extracción y routing, no de decisión. Eso es automatizable hoy.

---

## SLIDE 16 — Repositorio y recursos

**Para Imanol y el equipo técnico**

**Repo:** `github.com/EmilioSarachagaNauta/nauta-email-categorization`

```
scripts/
  classify_workflows.py   ← clasificación LLM por email
  find_patterns.py        ← análisis de patrones
  categorize_emails.py    ← pipeline base (incidentes, entidades)

docs/
  workflow-classification-flow.md   ← flujo técnico completo
  system-summary.md                 ← qué detecta el sistema
```

**Para correr:**
```bash
python3 scripts/classify_workflows.py   # ~$5 USD / 850 emails
python3 scripts/find_patterns.py        # sin costo, solo estadísticas
```

---

*Preparado por: Data Team — Nauta · Febrero 2026*
