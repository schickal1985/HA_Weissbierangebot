# 🍺 Weissbier-Radar (Home Assistant Integration & HACS)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2023.8%2B-blue.svg)](https://www.home-assistant.io/)

**Weissbier-Radar** ist eine leichtgewichtige Home Assistant Custom Integration (HACS), die wöchentlich Prospekte und Angebote für **Franziskaner Weißbier** und **Erdinger Weißbier** (Kästen 20 x 0,5l) bei Supermärkten und Discountern (**Netto Marken-Discount, Edeka, Kaufland, Rewe, Penny, Metro etc.**) automatisiert überwacht.

---

## ✨ Features

* 🚀 **Vollautomatische Prospekt-Überwachung:** Kein manuelles Durchblättern von Werbe-PDFs mehr nötig.
* 📍 **Postleitzahl-Genau:** Findet die Angebote für deine Region (z. B. PLZ `84385` / Pfarrkirchen, Aidenbach, Bad Birnbach).
* 🍺 **Fokus auf Top-Weißbiere:** Standardmäßig für **Franziskaner** und **Erdinger** – flexibel per Klick aktivierbar.
* 🏷️ **Detaillierte Sensor-Attribute:**
  * Aktueller Angebotspreis (z. B. `12.99 €`)
  * Gültigkeitszeitraum (z. B. `bis 29.08.2026`)
  * Bester Händler & Ersparnis
  * Direkter Link zur Angebotsseite
* 🔔 **Smarte Push-Benachrichtigungen:** Erhalte Montagmorgen eine Benachrichtigung auf dein Smartphone, wenn dein Lieblingsweißbier im Angebot ist.
* 🛡️ **100% Sicher & Read-Only:** Ändert **keine** Systemeinstellungen, greift nur lesend zu und hinterlässt beim Deinstallieren keinerlei Rückstände.

---

## 📦 Installation über HACS (Custom Repository)

1. Öffne **Home Assistant** und gehe zu **HACS**.
2. Klicke oben rechts auf das **Drei-Punkte-Menü** und wähle **„Benutzerdefinierte Repositories“** (*Custom repositories*).
3. Trage deine GitHub-Repository-URL ein:
   * **URL:** `https://github.com/DEIN-BENUTZERNAME/weissbier-radar`
   * **Typ:** `Integration`
4. Klicke auf **Hinzufügen**.
5. Klicke in HACS auf **Herunterladen** und starte Home Assistant einmalig neu.

---

## ⚙️ Einrichtung in Home Assistant (UI)

1. Gehe in Home Assistant zu **Einstellungen -> Geräte & Dienste -> Integration hinzufügen**.
2. Suche nach **„Weissbier Radar“**.
3. Gib deine **Postleitzahl** (z. B. `84385`) ein und wähle deine gewünschten Händler und Sorten aus.
4. Fertig! Die Sensoren werden sofort erstellt und ermitteln vollautomatisch den tagesaktuellen Bestpreis (alle Kastenpreise > 8,00 €). Über das **Zahnrad ⚙️ (Konfigurieren)** kannst du überwachte Händler und Sorten jederzeit anpassen.

---

## 📊 Erstellte Sensoren

| Sensor-Entität | Beschreibung | Beispiel-Status |
| :--- | :--- | :--- |
| `sensor.franziskaner_weissbier_bester_preis` | Günstigster Preis für Franziskaner | `12.99 €` |
| `sensor.franziskaner_weissbier_netto_marken_discount` | Franziskaner bei Netto | `12.99 €` |
| `sensor.franziskaner_weissbier_edeka` | Franziskaner bei Edeka | `Kein Angebot` |
| `sensor.franziskaner_weissbier_kaufland` | Franziskaner bei Kaufland | `Kein Angebot` |
| `sensor.erdinger_weissbier_bester_preis` | Günstigster Preis für Erdinger | `14.98 €` |
| `sensor.erdinger_weissbier_netto_marken_discount` | Erdinger bei Netto | `Kein Angebot` |
| `sensor.erdinger_weissbier_edeka` | Erdinger bei Edeka | `Kein Angebot` |
| `sensor.erdinger_weissbier_kaufland` | Erdinger bei Kaufland | `Kein Angebot` |

---

## 📱 Automations-Vorlagen (Push-Nachrichten bei Preisänderungen)

Alle fertigen Automatisierungs-Vorlagen (sowohl als kompakte **Universal-Automation** für alle Sensoren als auch als **8 einzelne YAML-Konfigurationen**) findest du in der Datei [`automations.yaml`](file:///c:/Users/patri/Desktop/Antigravity/Weissbier/automations.yaml).

### Fertige Automation: Preisüberwachung (an iPhone 13)

```yaml
alias: "🍺 Weißbier-Radar: Preisüberwachung (Alle Sensoren)"
description: "Sendet eine kurze Push-Nachricht an das iPhone bei Angeboten oder wenn ein Angebot endet."
mode: queued
max: 10
trigger:
  - platform: state
    entity_id:
      - sensor.franziskaner_weissbier_bester_preis
      - sensor.franziskaner_weissbier_netto_marken_discount
      - sensor.franziskaner_weissbier_edeka
      - sensor.franziskaner_weissbier_kaufland
      - sensor.erdinger_weissbier_bester_preis
      - sensor.erdinger_weissbier_netto_marken_discount
      - sensor.erdinger_weissbier_edeka
      - sensor.erdinger_weissbier_kaufland
condition:
  - condition: template
    value_template: >
      {{ trigger.from_state is defined 
         and trigger.from_state is not none 
         and trigger.to_state is not none 
         and trigger.from_state.state not in ['unavailable', 'unknown'] 
         and trigger.to_state.state not in ['unavailable', 'unknown'] 
         and trigger.from_state.state | float(0) != trigger.to_state.state | float(0) }}
action:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.state | float(0) < trigger.from_state.state | float(0) }}"
        sequence:
          - action: notify.mobile_app_sp_iphone_13
            data:
              title: >
                {% set is_best = 'bester_preis' in trigger.entity_id %}
                {% set haendler = state_attr(trigger.entity_id, 'bester_haendler') if is_best else state_attr(trigger.entity_id, 'haendler') %}
                🍺 {{ state_attr(trigger.entity_id, 'produkt') }} bei {{ haendler }}: {{ trigger.to_state.state }} €
              message: >
                {% set is_best = 'bester_preis' in trigger.entity_id %}
                {% set haendler = state_attr(trigger.entity_id, 'bester_haendler') if is_best else state_attr(trigger.entity_id, 'haendler') %}
                {{ state_attr(trigger.entity_id, 'produkt') }} jetzt für {{ trigger.to_state.state }} € (vorher {{ trigger.from_state.state }} €) bei {{ haendler }}.
              data:
                url: "{{ state_attr(trigger.entity_id, 'angebots_link') }}"
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.state | float(0) > trigger.from_state.state | float(0) }}"
        sequence:
          - action: notify.mobile_app_sp_iphone_13
            data:
              title: >
                {% set is_best = 'bester_preis' in trigger.entity_id %}
                {% set haendler = state_attr(trigger.entity_id, 'bester_haendler') if is_best else state_attr(trigger.entity_id, 'haendler') %}
                ℹ️ {{ state_attr(trigger.entity_id, 'produkt') }}: Kein Angebot mehr
              message: >
                {% set is_best = 'bester_preis' in trigger.entity_id %}
                {% set haendler = state_attr(trigger.entity_id, 'bester_haendler') if is_best else state_attr(trigger.entity_id, 'haendler') %}
                Preis bei {{ haendler }} wieder auf {{ trigger.to_state.state }} € gestiegen.
```

---

## 🎨 Lovelace Dashboard Vorlage (Markdown Card)

Füge deinem Dashboard eine **Markdown-Karte** hinzu:

```yaml
type: markdown
title: "🍺 Weißbier-Radar"
content: >
  ### **Franziskaner Weißbier (20 x 0,5l)**
  * **Bester Preis:** **{{ states('sensor.franziskaner_weissbier_bester_preis') }} €** (bei {{ state_attr('sensor.franziskaner_weissbier_bester_preis', 'bester_haendler') }})
  * **Netto:** {{ states('sensor.franziskaner_weissbier_netto_marken_discount') }} {% if states('sensor.franziskaner_weissbier_netto_marken_discount') != 'Kein Angebot' %}€{% endif %}
  * **Edeka:** {{ states('sensor.franziskaner_weissbier_edeka') }} {% if states('sensor.franziskaner_weissbier_edeka') != 'Kein Angebot' %}€{% endif %}
  * **Kaufland:** {{ states('sensor.franziskaner_weissbier_kaufland') }} {% if states('sensor.franziskaner_weissbier_kaufland') != 'Kein Angebot' %}€{% endif %}

  ---

  ### **Erdinger Weißbier (20 x 0,5l)**
  * **Bester Preis:** **{{ states('sensor.erdinger_weissbier_bester_preis') }} €** (bei {{ state_attr('sensor.erdinger_weissbier_bester_preis', 'bester_haendler') }})
  * **Netto:** {{ states('sensor.erdinger_weissbier_netto_marken_discount') }} {% if states('sensor.erdinger_weissbier_netto_marken_discount') != 'Kein Angebot' %}€{% endif %}
  * **Edeka:** {{ states('sensor.erdinger_weissbier_edeka') }} {% if states('sensor.erdinger_weissbier_edeka') != 'Kein Angebot' %}€{% endif %}
  * **Kaufland:** {{ states('sensor.erdinger_weissbier_kaufland') }} {% if states('sensor.erdinger_weissbier_kaufland') != 'Kein Angebot' %}€{% endif %}
```

---

## 📄 Lizenz

Dieses Projekt steht unter der [MIT Lizenz](LICENSE).
