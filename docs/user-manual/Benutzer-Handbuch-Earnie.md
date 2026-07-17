# EARNIE — Benutzer-Handbuch

> **Entwurf.** Dieses Handbuch beschreibt Earnie aus Anwendersicht nach der Installation.
> Technische Details (Container, Config-Schema, Entwickler) stehen in der [Anwender-Dokumentation](../README.md) und im [README](../../README.md).

---

## Übersicht

### Sinn und Zweck von Earnie

**Earnie** ist ein Energie-Optimierer für Privathaushalte. Er plant und steuert, wann Strom bezogen, gespeichert, verbraucht oder eingespeist wird — mit dem Ziel, **Stromkosten zu senken** und den **Eigenverbrauch** zu erhöhen.

Besonders wirksam ist Earnie bei **dynamischen Spot-Tarifen** (z. B. aWATTar), weil Preise stündlich schwanken. Statt fester Regeln berechnet Earnie regelmäßig einen **Plan für die nächsten etwa 24–48 Stunden** (15-Minuten-Schritte) und berücksichtigt dabei:

- aktuelle und prognostizierte Strompreise  
- PV-Ertragsprognose (Wetter am Standort)  
- Zustand und Grenzen des Batteriespeichers  
- verschiebbare Verbraucher (E-Auto, Wärmepumpe, Pool, Haushaltsgeräte, …)

**Zwei Nutzungsarten:**

| Nutzung | Was Sie damit machen |
|--------|----------------------|
| **Was-wäre-wenn (ohne Smart-Home)** | Haus und Varianten konfigurieren, Jahresvergleich rechnen — z. B. ob sich Speicher, größere PV oder ein Spot-Tarif lohnen |
| **Live-Betrieb (mit Loxone)** | Dauerhaft optimieren und Sollwerte an die Hausautomation schreiben; Monitor zeigt Plan und Ist |

Nur der Hintergrunddienst (`main.py`) steuert die Anlage. Die Web-Oberfläche (Streamlit) ist das **Cockpit**: Anzeige, Konfiguration und Analyse — und unter **Echtzeit-Umgebung → Optimierer-Dienst** Start/Stop/Neustart des Daemons. Die Oberfläche selbst schreibt keine Steuerbefehle an Loxone.

### Voraussetzungen

**Für Was-wäre-wenn-Analysen (ohne Live-Steuerung):**

- PC oder Server mit Docker **oder** lokaler Python-Umgebung  
- Webbrowser für die Oberfläche  
- Grobe Angaben zu Haus, Verbrauchern, optional PV/Speicher und Strom-Tarif(en)  
- Internet für Wetter- und Preisdaten (je nach Szenario)

**Für den produktiven Live-Betrieb zusätzlich:**

- [Loxone](https://www.loxone.com/)-Miniserver mit erreichbarer HTTP-Schnittstelle  
- Sinnvolle Merker / virtuelle Eingänge für SOC, Leistungen, Freigaben und Sollwerte (siehe Kapitel *Verbindung zu Smarthome*)  
- Typischerweise: PV und/oder Batteriespeicher sowie steuerbare Verbraucher  
- Empfohlen: dynamischer Bezugs- und/oder Einspeisetarif  

Earnie ist **unabhängig von Energieversorger und Systemlieferant** gedacht; die heutige Live-Anbindung ist Loxone. Andere Systeme können später ergänzt werden.

### Lizenzbedingungen

Earnie ist **Source-Available** und für die **private, nicht-kommerzielle Nutzung** in Privathaushalten vorgesehen. Kommerzielle Nutzung, Weiterverkauf oder SaaS-Angebote sind ohne schriftliche Zustimmung nicht erlaubt.

Die Software wird „wie besehen“ bereitgestellt. Eingriffe in Speicher und Großverbraucher erfolgen auf **eigenes Risiko** des Betreibers.

Vollständige Bedingungen: [LICENSE.md](../../LICENSE.md).

### Support

- **Projekt & Issues:** [GitHub — JochenTCC/Earnie](https://github.com/JochenTCC/Earnie)  
- **Community:** z. B. Diskussionen im Loxone-Umfeld (loxforum u. Ä.)  
- **Technische Doku:** [docs/README.md](../README.md)  

Es gibt derzeit keinen vertraglichen Herstellersupport. Rückmeldungen zu neuen Hardware-Typen und Konfigurationen helfen der Weiterentwicklung.

---

## Installation

Kurzfassung der typischen Wege:

| Weg | Für wen | Hinweis |
|-----|---------|---------|
| **Docker (empfohlen Produktiv)** | Synology NAS, LoxBerry, Proxmox LXC, PC | Persistente Ordner `config/` und `runtime/` außerhalb des Images |
| **Greenfield / Ersteinrichtung** | Erste Was-wäre-wenn-Tests lokal | Eigener Stack, oft Port **8502** — getrennt vom Produktivsystem |
| **Lokal ohne Container** | Entwickler, Tests | siehe [DEVELOPER.md](../../DEVELOPER.md) |

**Typischer Ablauf (Docker):**

1. Projekt bzw. Compose-Datei bereitstellen, Verzeichnisse `config/` und `runtime/` anlegen.  
2. Container starten — fehlende Dateien werden beim ersten Start angelegt (Bootstrap).  
3. Oberfläche im Browser öffnen (Produktiv oft Port **8501**, siehe [Streamlit-Ports](../referenz/streamlit-ports.md)).  
4. Loxone-Zugang hinterlegen (falls Live geplant) und mit dem Hauskonfigurator fortfahren.

Details: [Container](../einrichtung/container.md) · [Betrieb](../einrichtung/betrieb.md) · [Greenfield](../einrichtung/greenfield-dev-stack.md).

Nach dem Start erscheinen in der Navigation zunächst vor allem **Planung** und **Echtzeit-Umgebung**. Weitere Seiten (Monitor, Szenario-Explorer, …) werden freigeschaltet, sobald die Einrichtung weit genug ist.

---

## Erste Einrichtung (für Was-Wäre-Wenn-Analyse)

Ziel dieser Phase: Ihr Haus so abbilden, dass Earnie **Vergleichsszenarien** rechnen kann — noch ohne echte Steuerung der Anlage. Ideal, um Investitionen und Tarifwahl vorab zu prüfen oder sich von der Leistungsfähigkeit von Earnie zu überzeugen.

Empfohlene Reihenfolge:

1. Hauskonfigurator (Haus, Verbraucher, PV, Speicher)  
2. Szenarieneditor (Varianten: mit/ohne Speicher, anderer Tarif, …)  
3. Live-Szenario zuweisen (welche Entitäten „gelten“ als Basis)  
4. Szenario-Explorer: Verbrauch generieren, Rechnung starten, Ergebnisse lesen  

### Hauskonfigurator

Unter **Planung → Hauskonfigurator** pflegen Sie die baulichen und technischen Bausteine Ihres Haushalts. Gespeichert werden Kataloge (Hausprofile, Komponenten), die später von Szenarien **referenziert** werden — nicht alles doppelt in einer einzigen Datei.

In der Sidebar sehen Sie fehlende Schritte der Ersteinrichtung.

#### Konfiguration eines Hauses

Ein **Hausprofil** beschreibt Standort und „Wer lebt / was verbraucht hier“:

- **Standort:** Breite, Länge, Zeitzone (wichtig für Sonnenzeiten und PV-Prognose)  
- **Verbraucher im Profil:** z. B. Haus-Wärme, E-Auto, Pool, generische Geräte  
- **Grundlast:** typischer Haushaltsverbrauch über den Tag (Vorschau im Konfigurator prüfen)

Legen Sie zuerst ein Profil an und ergänzen Sie danach die Geräte. Ohne Standort und sinnvolles Profil sind Jahresvergleiche wenig aussagekräftig. Je mehr Freiheiten sie Earnie beim Verschieben der Aktivierung der verschiedenen Verbraucher geben, umso höher sind die Einsparungspotenziale.

#### Haus-Wärme

Thermischer Verbraucher für Heizung / Wärmepumpe (je nach Modell im Profil):

- Solltemperaturen und thermische Parameter (Wärmeverlust, Volumen bzw. Gebäudekennwerte). Dafür ist ein Energieausweis des Gebäudes hilfreich.  
- Earnie schätzt den **Wärmebedarf aus Wetterdaten** und plant den Strombedarf zeitlich mit ein  
- Im Live-Betrieb später Anbindung über Loxone-Merker (Leistung, Freigabe, ggf. Temperaturen)

Je genauer die thermischen Angaben, desto realistischer der Jahresvergleich — aber grobe Werte reichen für eine erste Orientierung.

#### Elektro-Auto

E-Auto / Wallbox als planbarer Verbraucher:

- Akkukapazität, Ladeleistung, Wirkungsgrad  
- **Zeitfenster:** wann das Auto da ist und bis wann es „fertig“ sein soll (Werktag / Wochenende)  
- Ziel-SOC bzw. Rest-SOC beim Abfahren  

Earnie entscheidet **wann** am günstigsten geladen wird (günstige Stunden, PV-Überschuss) unter der Voraussetzung, dass es zum angegebenen Zeitpunkt den gewünschten End-SOC hat. Im Live-Betrieb liefert Loxone typischerweise „angesteckt“, Rest-SOC und Fertig-Zeit; Earnie schreibt Lade-Sollleistung und ggf. PV-Follow um genau den PV-Überschuss ins E-Auto zu laden.

#### Pool

Ein Pool kann als komplexer Verbraucher angesehen werden, der mehrere Einzelkomponenten umfasst, die getrennt gesteuert werden können:

- **Heizung** — thermisches Modell (Wasservolumen, Solltemperatur, Wärmeverlust); Tagesenergie ergibt sich aus dem Modell  
- **Filter** — Laufzeitbedarf (Stunden), ggf. natives Zeitfenster der Poolsteuerung; Earnie kann **zusätzlich** außerhalb dieses Fensters freigeben  

Für Was-wäre-wenn reichen Volumen, Solltemperatur und Filterstunden. Live braucht passende Merker für Temperaturen und Freigaben.

##### Hinweis

Pools haben meistens keine standardisierte Schnittstelle zur Anbindung an Smarthome-Systeme. Daher ist hier Eigenleistung gefragt oder mit erhöhtem Aufwand zu rechnen, wenn eine Anbindung durch Fachkräfte vorgenommen werden soll. Das Einsparpotenzial ist aber enorm!!

#### Allgemeine Verbraucher

Waschmaschine, Trockner, Geschirrspüler und ähnliche Geräte als **generische** Verbraucher:

| Rolle in Earnie | Bedeutung für Sie |
|-----------------|-------------------|
| **Bekannt (known)** | Feste / geplante Zeiten fließen als Grundlast ein — Earnie verschiebt sie nicht, berücksichtigt sie aber bei der Optimierung |
| **Flexibel (flex)** | Earnie darf den Start im erlaubten Fenster verschieben |
| **Manuell (manual)** | Sie planen auf der Seite *Manuelle Geräte*; Earnie gibt Start-Empfehlungen |

Leistung und typische Laufzeit angeben. Optional später ein Loxone-Leistungsmerker für Ist-Anzeige und zur Kontrolle.

#### PV-Anlagen

Unter PV-Anlagen (Komponenten-Katalog):

- installierte Leistung (**kWp**)  
- Dachneigung und Ausrichtung (Azimut: Süd ≈ 0°, Ost negativ, West positiv)  

Es können mehrere PV-Anlagen konfiguriert werden. Die konfigurierten PV-Anlagen können in den Szenarios selektiert werden. So kann in einer Was-Wäre-Wenn Analyse auch eine mögliche Erweiterung vorab analysiert werden.

Der Standort wird aus dem Hausprofil entnommen. Earnie nutzt Wetterdaten für die Ertragsprognose. 

#### Batteriespeicher

Unter Batterien:

- nutzbare Kapazität (kWh)  
- max. Lade-/Entladeleistung (kW)  
- Wirkungsgrad, min./max. SOC  
- optional **Verschleißkosten** (damit Earnie bei vielen Zyklen dies wirtschaftlich berücksichtigt)  

Im Live-Betrieb steuert Earnie Ziel-SOC und Lade-/Entlade-Sollwerte über das Smarthome-System; die konkrete Wechselrichter-Logik bleibt in der Hausautomation.

### Szenarien-Editor

Unter **Planung → Szenarieneditor** bauen Sie **Varianten** Ihres Haushalts, ohne den Live-Betrieb zu ändern.

Ein Szenario verknüpft typischerweise:

- Hausprofil  
- Batterie und/oder PV-Anlage(n). Ein Szenario ohne diese Komponenten ist auch möglich.  
- Bezugs- und Einspeisetarif  

Beispiele für Vergleiche:

- Ist-Zustand vs. größerer Speicher  
- mit PV vs. ohne PV oder mehrere PVs
- Fixpreis vs. Spot-Tarif  
- ohne Batterie, aber mit PV  

Das **Live-Szenario** (meist ID `live`) ist die Basis für den späteren Produktivbetrieb. Weitere Szenarien dienen der Analyse im Szenario-Explorer.

Tarife wählen Sie aus dem Tarifkatalog (Bezug/Einspeise). Details zu Preisen: [Preise & aWATTar](../konfiguration/preise.md).

### Szenario-Explorer (Was-Wäre-Wenn-Analyse)

Unter **Analyse → Szenario-Explorer** (erscheint nach ausreichender Planungs-Konfiguration).

Hier analysieren Sie **Langzeitvergleiche** im Zeitraum der letzen 12 Monate (für Teszwecke kann auch nur der Monat März analysiert werden) zwischen Referenz (Als Referenz wird immer das "nackte Haus" ohne PV und Speicher berechnet und zusätzlich jedes Szenari ohne Optimierung durch Earnie) und Ihren Szenarien. Das ist **kein** tägliches Live-Cockpit und ändert keine Steuerwerte an Loxone.

> Hinweis: Ergebnisse sind Modellrechnungen. Es gibt **keine Garantie**, dass Live-Einsparungen exakt den Simulationen entsprechen (Wetter, Verhalten, Tarifdetails, Hardwaregrenzen).

#### Verbrauchsdaten generieren und sichten

Vor oder beim Start einer Explorer-Rechnung brauchen Sie eine belastbare **Lastgrundlage**:

- aus dem **Hausprofil** (Zeitpläne / thermische Modelle / Flex-Fenster), und/oder  
- aus historischen Verbrauchsdaten, falls vorhanden  

Im Explorer bzw. zugehörigen Schritten können Sie Verbrauchsverläufe erzeugen und prüfen (Plausibilität, Monatsprofile). Stimmen Größenordnung und Tagesgang nicht, zuerst Profil und Geräte korrigieren — sonst sind Kostenvergleiche irreführend.

#### Szenario-Explorer ausführen

1. Gewünschte Szenarien und Zeitraum (Monate) wählen.  
2. Rechnung starten (kann je nach Umfang länger dauern).  
3. Warten, bis die Auswertung fertig ist; Ergebnisse landen in der Laufzeitablage für den Explorer.

Die Referenzökonomie vergleicht typischerweise „Last am gewählten Tarif **ohne** Batterieoptimierung“; Szenarien mit PV rechnen mit dem jeweiligen PV-Ertrag. Batterie ist Teil der **optimierten** Variante, nicht der reinen Referenz. (!!!Das muss gecheckt werden)

#### Ergebnisse des Szenario-Explorers

Auswertung u. a.:

- **Kostenvergleich** Gesamt und monatlich (Referenz vs. optimierte Szenarien)  
- **Monatsverläufe** und Plausibilitätsansichten  
- Charts zu Leistung, Verbrauch und PV je nach gewählter Ansicht  

Nutzen Sie die Ergebnisse als **Entscheidungsgrundlage** (Investition, Tarif), nicht als exakte Prognose der nächsten Stromrechnung. Es wird keine Gewähr dafür übernommen, dass die Ergebnisse genau so eintreffen werden.

---

## Verbindung zu Smarthome

Wenn die Was-wäre-wenn-Analyse überzeugt, folgt die Anbindung an die Smarthome-Steuerung. Earnie liefert **Sollwerte und Freigaben**; die konkrete Schaltlogik (Wechselrichter, Wallbox, Relais) bleibt in der Smarthome-Steuerung.

### Vorbereitung der Smarthome-Konfiguration

1. **Benutzer** am Smarthome-System mit Rechten zum Lesen und Schreiben der benötigten IOs anlegen.  
2. **Merker / virtuelle Eingänge** anlegen bzw. benennen oder vorhandene Signale übernehmen — u. a.:  
   - Batterie: SOC, Leistungen, PV-Leistung  
   - Steuerung: Ziel-SOC, Lade-/Entlade-Soll, Steuerbefehl (Automatik / Zwang)  
   - Verbraucher: Ist-Leistung lesen; Freigabe 0/1 oder E-Auto-Leistungs-Soll schreiben  
   - E-Auto: angesteckt, Fertig-Zeit, Rest-SOC, Kapazität, …  (!!! Hier muss angegeben werden, wo die konkreten Merker zu finden sind)
3. Optional **FTP-Verbrauchslog** für historische Daten.  (!!! Streichen - wo ist der Bezug zum Code?)
4. Namen in Earnie hinterlegen (Live-Konfiguration / Config) — **exakt** wie im Smarthome-System.  

Earnie liest Smarthome-Werte oft als Text mit Einheit (z. B. `3.5 kW`) ein; die Einheit wird ignoriert.

Signalübersicht: [Loxone-Signale](../referenz/loxone-signale.md) · Anbindung: [Loxone-Anbindung](../einrichtung/loxone-anbindung.md).

### Live-Konfiguration

Unter **Echtzeit-Umgebung → Live-Konfiguration**:

- welches Szenario **live** gilt (`live_scenario_id`)  
- welche Entitäten (Hausprofil, Batterie, PV, Tarife) daran hängen  

Aufgelöste Zahlen (kWp, Kapazität, Vergütung in ct/kWh) sind meist **nur Anzeige**. Geändert werden die Referenzen bzw. die Kataloge im Hauskonfigurator / Szenarieneditor.

Damit nutzen Live-Optimierung und Szenario-Explorer dieselbe Auflösungslogik.

### Loxone-Kommunikation

Unter **Echtzeit-Umgebung → Loxone-Kommunikation** (Debug / Abnahme):

- **Live-Lesen:** alle konfigurierten Merker werden periodisch vom Smarthome System eingelesen.  
- **Letzte Schreibvorgänge:** was `main.py` zuletzt gesendet hat (Erfolg ja/nein)  
- **Silent-Modus:** Earnie berechnet und zeigt Sollwerte, **schreibt aber nicht** an die Smarthome Steuerung — sinnvoll für Tests
- **Live-Modus:** Schreiben aktiv — erst nach erfolgreicher Lesekontrolle umschalten  

Prüfungen auch per Skript: `python -m scripts.verify_loxone_setup`.

Cutover-Checkliste: Lesen OK → Schreiben Erfolg → Monitor/Sankey plausibel. Details: [Loxone-Kommunikation](../ui/loxone-kommunikation.md).

---

## Live-Betrieb

Im Produktivbetrieb läuft der Optimierer dauerhaft (im Docker-Container automatisch mit der UI, oder lokal als `python main.py`) als Daemon und arbeitet im **15-Minuten-Takt** (zusätzlich bei konfigurierten Ereignissen).

Unter **Echtzeit-Umgebung → Optimierer-Dienst** können Sie den Daemon starten, stoppen oder neu starten. Die Oberfläche zeigt den aktuellen Plan; Loxone-Schreibvorgänge kommen weiterhin nur von `main.py`.

### Earnie Monitor

Unter **Betrieb → Monitor** (Sunset-2-Sunset):

Einheitliches Cockpit über **Vergangenheit, Jetzt und Vorausschau** — navigierbar in Sonnenaufgangs-Fenstern (ca. 24 h Segmente). Die Anzeige erfolgt von Sonnenaufgang (SA_x) zu Sonnenaufgang (SA_x+1), da dies auch der Zeithorizont für die Optimierung von Earnie ist. Dieses Intervall ist überaus sinnvoll, da üblicherweise ein vorhandener Speicher dort am wenigsten Energie eingespeichert hat. (Sollte dies nicht der Fall sein, ist die Batterie möglicherweise zu groß gewählt ...)

Typische Inhalte:

- **Chart 1:** Leistungen, Energieflüsse (PV, Netz, Batterie, Flex-Verbraucher), SOC, Preis  (!!! Muss noch detaillierter beschrieben werden)
- **Chart 2:** Vergleich der verbrauchten Energie und der Kosten zwischen Basis (ohne Optimierung) und mit Eingriff von Earnie  
- **Sankey:** aktueller Energiefluss aus Live-Daten  
- **Tabelle & Energievergleich:** Rohdaten und Baseline vs. Optimierung  
- **Countdown:** nächster Optimierungslauf  

Grauer Bereich = Historie aus dem Produktiv-Log; Vorausschau = letzter Plan von `main.py`. Fehlende Log-Slots bleiben sichtbar leer.
Weißer Bereich = Konkrete Optimierung für die nahe Zukunft, wo die Preise vom Anbieter schon bekanntgegeben worden sind.
Grüner Bereich = Die Preise sind noch nicht bekannt, aber das interne Preismodell in Earnie macht eine Vorhersage, wie die Preise wahrscheinlich sein werden.

Kennzahlen zur Ersparnis beziehen sich auf den **vollen Planungshorizont** (Jetzt bis übernächster Sonnenaufgang), nicht nur auf das gerade sichtbare Chart-Segment.

Charts im Detail: [Charts & Panels](../ui/charts.md) · Modus: [Betriebsmodi](../ui/betriebsmodi.md).

### Manuelle Geräte

Unter **Betrieb → Manuelle Geräte** für Verbraucher mit Rolle **manuell**:

- Laufzeiten planen bzw. Earnie-**Startempfehlungen** nutzen  
- angenommene Leistung und Dauer aus dem Hausprofil  

Geplante Läufe (mit einem Check versehen) erscheinen im Monitor (Chart 1) und fließen in die Optimierung der übrigen Lasten ein. Ideal für Geräte ohne smarte Freigabe, bei denen Sie den Start selbst setzen.

### Verbraucher-Analyse (Noch nicht implementiert)

Unter **Analyse → Verbraucheranalyse**:

Auswertung, welcher Verbrauch **autonom** (Haus/Loxone ohne Earnie-Plan) und welcher **earnie-initiiert** bzw. verschoben war. Hilft zu prüfen, ob Freigaben und Pläne greifen und wo noch Potenzial liegt.

---

## Kurz-Checkliste vom Initial-Zustand zum "Go-Live"

1. Installieren (Docker/Greenfield) und UI öffnen  
2. Hauskonfigurator: Profil, Wärme, Auto, Pool, Geräte, PV, Batterie  
3. Szenarieneditor: Live-Szenario + Vergleichsvarianten  
4. Szenario-Explorer: Verbrauch prüfen, Rechnung, Ergebnisse bewerten  
5. Loxone vorbereiten und Zugang speichern  
6. Live-Konfiguration + Loxone-Kommunikation (Silent → Live)  
7. Daemon dauerhaft laufen lassen, Monitor beobachten, Feintuning  

Bei Unklarheiten in der Konfiguration: Hover-Hilfe in `config.json` (Schema) und die Kapitel unter [docs/README.md](../README.md).
