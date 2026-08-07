# Waltham Forest Bin Collection

A Home Assistant custom integration that shows your **London Borough of Waltham
Forest** bin collection dates as sensors, so you can automate reminders.

> Unofficial, community-built, and free. Not affiliated with or endorsed by the
> London Borough of Waltham Forest. It reads the same public "Find My Bin
> Collection Dates" service the council website uses.

## What you get

A device per address with one sensor per service, each holding the **next
collection date** (a `date` sensor):

| Entity | Service |
|---|---|
| `sensor.refuse` | Domestic (black bin) refuse |
| `sensor.recycling` | Recycling |
| `sensor.food_waste` | Food waste |
| `sensor.garden_waste` | Garden waste |

Each sensor also exposes attributes: `days_until`, `round_schedule`, the raw
`service_name`, and `upcoming` (a short list of projected future dates). Only the
services your address actually has are created.

### Calendar

A **calendar entity** (`calendar.collections`) shows upcoming collections in the
Home Assistant calendar, so you get a month-ahead view. Each collection is an
all-day event named after the service.

> ⚠️ **Only the next date per service is authoritative** (fetched from the
> council). Later dates — in `upcoming` and in the calendar — are *projected*
> from the round frequency (weekly / fortnightly) and do **not** account for
> bank-holiday shifts, when the council moves collections.

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories**.
2. Add `https://github.com/Playcolors-co/ha-binhass` as an **Integration**.
3. Install **Waltham Forest Bin Collection**, then restart Home Assistant.
4. **Settings → Devices & Services → Add Integration → Waltham Forest Bin
   Collection**.
5. Enter your **postcode**, pick your **address** from the list. Done — no UPRN
   to look up by hand.

Data refreshes every 12 hours.

## Example automation — "tomorrow's bins"

Notify the evening before a collection. Adjust the entities and the notify
service to your setup.

```yaml
automation:
  - alias: "Bin reminder — tomorrow"
    trigger:
      - trigger: time
        at: "19:00:00"
    variables:
      bins:
        - sensor.refuse
        - sensor.recycling
        - sensor.food_waste
        - sensor.garden_waste
      tomorrow: "{{ (now() + timedelta(days=1)).strftime('%Y-%m-%d') }}"
      due: >-
        {{ bins | select('is_state', tomorrow)
                | map('replace', 'sensor.', '')
                | map('replace', '_', ' ') | list }}
    condition:
      - condition: template
        value_template: "{{ due | count > 0 }}"
    action:
      - service: script.push_notification
        data:
          message: "🗑️ Tomorrow: {{ due | join(', ') }}"
```

## How it works

Waltham Forest has no official API. The integration replicates the public
Firmstep/AchieveForms `apibroker/runLookup` calls over plain HTTPS:

1. `authapi/isauthenticated` → a session id.
2. `apibroker/runLookup` (address lookup) → your address list for a postcode.
3. `apibroker/runLookup` (collections lookup, backed by *Whitespace*) → the
   services at your address with their next collection dates.

No credentials, no scraping browser, no Selenium.

## Privacy

Your postcode and UPRN are stored only in your Home Assistant config entry and
sent only to the council portal to fetch your dates. Nothing is hardcoded in
this repository.

## License

MIT.
