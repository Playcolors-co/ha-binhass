<p align="center">
  <img src="https://raw.githubusercontent.com/Playcolors-co/ha-binhass/main/assets/banner.png" alt="Waltham Forest Bin Collection" width="100%" />
</p>

<p align="center">
  Home Assistant integration for <b>London Borough of Waltham Forest</b> bin
  collection dates — sensors, a calendar, and easy reminders.
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge&logo=homeassistantcommunitystore&logoColor=white" alt="HACS Custom"></a>
  <a href="https://github.com/Playcolors-co/ha-binhass/releases"><img src="https://img.shields.io/github/v/release/Playcolors-co/ha-binhass?include_prereleases&style=for-the-badge&logo=github" alt="Release"></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2024.12%2B-41BDF5?style=for-the-badge&logo=home-assistant&logoColor=white" alt="Home Assistant">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Playcolors-co/ha-binhass?style=for-the-badge" alt="License"></a>
</p>

<p align="center">
  <a href="https://github.com/Playcolors-co/ha-binhass/actions/workflows/validate.yml"><img src="https://github.com/Playcolors-co/ha-binhass/actions/workflows/validate.yml/badge.svg" alt="Validate"></a>
  <a href="https://github.com/Playcolors-co/ha-binhass/stargazers"><img src="https://img.shields.io/github/stars/Playcolors-co/ha-binhass?style=flat" alt="Stars"></a>
  <a href="https://www.buymeacoffee.com/scattolacom"><img src="https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-FFDD00?logo=buymeacoffee&logoColor=black" alt="Buy Me A Coffee"></a>
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=Playcolors-co&repository=ha-binhass&category=integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open in HACS"></a>
  <a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=binhass"><img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Add integration"></a>
</p>

> [!NOTE]
> Unofficial, community-built, and free. Not affiliated with or endorsed by the
> London Borough of Waltham Forest. It reads the same public "Find My Bin
> Collection Dates" service the council website uses.

## ♻️ What you get

A device per address with one sensor per service, each holding the **next
collection date** (a `date` sensor):

| | Entity | Service |
|:--:|---|---|
| ⬛ | `sensor.refuse` | Domestic (black bin) refuse |
| 🟩 | `sensor.recycling` | Recycling |
| 🍎 | `sensor.food_waste` | Food waste |
| 🟫 | `sensor.garden_waste` | Garden waste |

Each sensor also exposes attributes: `days_until`, `round_schedule`, the raw
`service_name`, and `upcoming` (a short list of projected future dates). Only the
services your address actually has are created.

### 📅 Calendar

A **calendar entity** (`calendar.collections`) shows upcoming collections in the
Home Assistant calendar, so you get a month-ahead view. Each collection is an
all-day event named after the service.

> [!WARNING]
> **Only the next date per service is authoritative** (fetched from the council).
> Later dates — in `upcoming` and in the calendar — are *projected* from the
> round frequency (weekly / fortnightly) and do **not** account for bank-holiday
> shifts, when the council moves collections.

## 🚀 Installation (HACS)

1. HACS → ⋮ → **Custom repositories**.
2. Add `https://github.com/Playcolors-co/ha-binhass` as an **Integration**
   (or just click **Open in HACS** above).
3. Install **Waltham Forest Bin Collection**, then restart Home Assistant.
4. **Settings → Devices & Services → Add Integration → Waltham Forest Bin
   Collection** (or click **Add integration** above).
5. Enter your **postcode**, pick your **address** from the list. Done — no UPRN
   to look up by hand.

> [!TIP]
> Data refreshes every 12 hours. The address picker does all the UPRN lookup for
> you — you never touch a UPRN.

## 🔔 Example automation — "tomorrow's bins"

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

## ⚙️ How it works

Waltham Forest has no official API. The integration replicates the public
Firmstep/AchieveForms `apibroker/runLookup` calls over plain HTTPS — no
credentials, no scraping browser, no Selenium.

```mermaid
flowchart LR
    P["📮 Postcode"] -->|address lookup| A["🏠 Address list"]
    A -->|you pick one| U["🔑 UPRN"]
    U -->|collections lookup<br/>(Whitespace)| D["🗓️ Next date per service"]
    D --> S["🧩 Sensors"]
    D --> C["📅 Calendar"]
```

1. `authapi/isauthenticated` → a session id.
2. `apibroker/runLookup` (address lookup) → your address list for a postcode.
3. `apibroker/runLookup` (collections lookup, backed by *Whitespace*) → the
   services at your address with their next collection dates.

## 🔒 Privacy

Your postcode and UPRN are stored only in your Home Assistant config entry and
sent only to the council portal to fetch your dates. Nothing is hardcoded in
this repository.

## ☕ Support

Free, independent work. An optional coffee is appreciated, never required:

<p align="center">
  <a href="https://www.buymeacoffee.com/scattolacom"><img src="https://img.buymeacoffee.com/button-api/?text=Buy%20me%20a%20coffee&emoji=%E2%98%95&slug=scattolacom&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff" alt="Buy me a coffee" /></a>
</p>

## 📄 License

MIT — see [LICENSE](LICENSE).
