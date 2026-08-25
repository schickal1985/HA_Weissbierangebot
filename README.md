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
4. Fertig! Die Sensoren werden sofort erstellt und aktualisiert.

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

## 📱 Automations-Beispiel (Push-Nachricht aufs Smartphone)

Erstelle eine einfache Automation unter **Einstellungen -> Automatisierungen -> Neue Automatisierung**:

```yaml
alias: "🍺 Weißbier-Angebot Alarm"
description: "Sendet eine Push-Nachricht, wenn Franziskaner oder Erdinger im Angebot sind"
trigger:
  - platform: state
    entity_id:
      - sensor.franziskaner_weissbier_bester_preis
      - sensor.erdinger_weissbier_bester_preis
condition:
  - condition: template
    value_template: "{{ trigger.to_state.state not in ['unavailable', 'unknown', 'Kein Angebot'] and trigger.to_state.state | float(0) <= 14.50 }}"
action:
  - service: notify.notify
    data:
      title: "🍺 Weißbier im Angebot!"
      message: >
        {{ state_attr(trigger.entity_id, 'produkt') }} ist aktuell bei 
        {{ state_attr(trigger.entity_id, 'bester_haendler') }} für nur 
        {{ trigger.to_state.state }} € im Angebot (Gültig bis {{ state_attr(trigger.entity_id, 'gueltig_bis') }}).
      data:
        url: "{{ state_attr(trigger.entity_id, 'angebots_link') }}"
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
