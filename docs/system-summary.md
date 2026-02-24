# Sistema de Categorización de Emails — ¿Qué detecta y qué entrega?

**Versión:** 1.0
**Fecha:** Febrero 2026
**Equipo:** Data Team - Nauta

---

## ¿Qué hace el sistema?

Procesa automáticamente los emails de operaciones de Nauta y extrae información estructurada: incidentes, señales positivas, entidades involucradas y sentimiento. El output alimenta la capa de inteligencia de **Ask Nauta**.

---

## 1. Clasificación de emails

Antes de analizar, el modelo clasifica cada email en una de estas categorías:

| Tipo | Descripción | ¿Se analiza? |
|---|---|---|
| `OPERATIONAL` | Comunicación real entre personas sobre una operación activa | ✅ Sí |
| `AUTO_NOTIFICATION` | Notificación automática con valor operativo (BL listo, llegada de buque, levante aprobada) | ✅ Sí |
| `MARKETING` | Propuesta comercial, oferta no solicitada | ❌ No |
| `READ_RECEIPT` | Acuse de lectura (asunto empieza con "Read:") | ❌ No |
| `OTHER` | Documentos escaneados, memos sin contexto operativo | ❌ No |

> En una muestra de 50 emails: 26 OPERATIONAL, 7 AUTO_NOTIFICATION, 9 READ_RECEIPT, 5 MARKETING, 3 OTHER.

---

## 2. Incidentes detectados

Se detectan tres grandes categorías:

### A. Delays y disrupciones
- Vessel rollover / vessel omission
- Retrasos de proveedor / producción
- Congestión portuaria
- Retrasos de aduana (Levante, Form 7501)
- Documentación tardía (ISF, BL, HBL)

### B. Cambios de costo
- Detention y demurrage
- Cambios de tarifa de flete
- Errores / discrepancias en facturas
- Surcharges (BAF, CAF, PSS)
- Impuestos Puerto Rico (IVU 11.5%)

### C. Problemas operacionales
- Confusión PO-Booking
- Confusión de IOR (Importer of Record)
- Múltiples follow-ups sin respuesta
- Problemas de calidad documental
- Problemas de sistema (BL no liberado en plataforma)

Para cada incidente se entrega:
- **Severidad**: LOW / MEDIUM / HIGH / CRITICAL
- **Entidades afectadas**: bookings, POs, contenedores
- **Impacto financiero**: monto, moneda, tipo
- **Estado**: resuelto o pendiente + descripción de resolución
- **Fecha de detección y resolución**

---

## 3. Señales positivas

El sistema también detecta eventos positivos que indican buen desempeño de proveedores y forwarders:

- Notificaciones proactivas antes de ser solicitadas
- Documentos listos (BL, ISF, Delivery Order)
- Levante aprobada / customs clearance sin inspección
- Resoluciones el mismo día
- Gestos comerciales (absorción de diferencial, extensión de free time)

---

## 4. Análisis de sentimiento

Por cada email se clasifica:

| Nivel | Señal |
|---|---|
| `POSITIVE` | Confirmaciones, agradecimientos, resoluciones |
| `NEUTRAL` | Actualizaciones de rutina |
| `CONCERNED` | Primer follow-up, urgencia moderada |
| `URGENT` | 2do/3er follow-up, palabras clave: "urgente", "ASAP" |
| `CRITICAL` | 3er+ follow-up, impacto operacional, escalación a gerencia |

---

## 5. Entidades extraídas por email

De cada email se extraen automáticamente:
- **POs, Customer POs, Sales Orders**
- **Booking numbers, Container numbers**
- **BL / MBL / HBL numbers, Levantes, Form 7501, ISF**
- **Vessel + voyage + IMO**
- **Shippers, consignees, carriers, brokers de aduana**
- **POL, POD, puertos de tránsito, destino final**
- **Fechas clave**: ETD, ETA, Last Free Date, deadlines documentales
- **Impacto financiero**: montos de detention/demurrage, tarifas

---

## 6. Output

El sistema genera un archivo JSON con dos vistas:

- **Timeline**: lista cronológica plana de todos los incidentes y señales positivas — ordenada por fecha, lista para consumir en Ask Nauta
- **Emails**: detalle completo por email, con todas las entidades y análisis

### Relación entre Timeline y Emails

El timeline es intencionalmente liviano: contiene solo lo mínimo para leer el evento. El vínculo con el detalle completo se hace a través del `queue_id`:

```
timeline[n].queue_id  ──→  emails[i].queue_id   (registro completo)
```

Por ejemplo, un evento del timeline como este:

```json
{
  "queue_id": "ef9802a8-...",
  "event_type": "INCIDENT",
  "subcategory": "Documentation quality issues",
  "summary": "Missing steel percentage breakdown..."
}
```

...se cruza con su registro en `emails` usando el mismo `queue_id`, donde se encuentran las entidades completas, el análisis de sentimiento, fechas clave, acciones requeridas y el `context_for_ask_nauta`.

> **¿Por qué `queue_id` y no `message_id`?**
> `queue_id` es la clave primaria de PRISMA — siempre presente y garantizadamente única.
> `message_id` puede ser nulo y su propósito es otro: junto con `related_queue_ids`, sirve para identificar y agrupar distintos `queue_id` que corresponden al mismo correo físico.
