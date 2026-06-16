# optimizer.py
from typing import List, Dict, Any, Tuple
import config  # Lokaler Import der Konfiguration

def heuristic_optimizer(matrix: List[Dict[str, Any]], current_hour: int, current_soc: float) -> Tuple[int, float]:
    """
    Berechnet den optimalen Betriebsmodus und die Ziel-Leistung für den Loxone Miniserver.
    
    Verwendet einen dynamischen Perzentil-Ansatz zur Erkennung von Preisspitzen/-tiefs
    und integriert die PV-Prognose, um ein Überladen aus dem Netz zu verhindern.
    
    Modi (Ernie_Mode):
        0 = Automatik (Normalbetrieb / Batterieladung und -entladung freigegeben)
        1 = Zwangsladen (Laden aus dem Netz mit Ziel-Leistung)
        2 = Entladesperre (Batterieentladung blockiert, um Kapazität für teure Stunden zu sparen)
    """
    if not matrix:
        print("🚨 Optimizer-Fehler: Matrix ist leer.")
        return 0, 0.0

    # Da die Matrix in main.py chronologisch ab JETZT aufgebaut wird, 
    # entspricht das erste Element [0] immer exakt der aktuellen Stunde.
    current_row = matrix[0]
    current_price = current_row['k_act']
    
    # Alle verfügbaren Preise extrahieren und sortieren für die Perzentil-Berechnung
    all_prices = sorted([row['k_act'] for row in matrix])
    n = len(all_prices)
    
    k_avg = sum(all_prices) / n
    
    # =========================================================================
    # DYNAMISCHER PERZENTIL-ANSATZ (Gummiband-Logik)
    # =========================================================================
    # Bestimmung der günstigsten 20% (P20) und teuersten 20% (P80) der verfügbaren Stunden.
    # Schützt vor IndexErrors, selbst wenn die Matrix weniger als 24h enthält.
    low_idx = max(0, int(n * 0.20))
    high_idx = min(n - 1, int(n * 0.80))
    
    cutoff_low = all_prices[low_idx]
    cutoff_high = all_prices[high_idx]
    
    # =========================================================================
    # PV-PROGNOSE INTEGRATION
    # =========================================================================
    # Wir betrachten den Ertrag und Verbrauch der kommenden Stunden (Index 1 bis 15)
    future_horizon = matrix[1:16]
    total_future_pv = sum(row['expected_p_pv'] for row in future_horizon)
    total_future_con = sum(row['expected_p_act'] for row in future_horizon)
    
    # Dynamische Anpassung der maximalen Ladegrenze für Netz-Zwangsladung:
    # Wenn am kommenden Tag viel Sonne erwartet wird, deckeln wir das Netzladen früher,
    # um wertvollen Platz im Akku für den kostenlosen Solarstrom freizuhalten.
    max_soc_for_grid_charge = 90.0
    if total_future_pv > 12.0:  # Schwellenwert (z.B. > 12 kWh prognostizierter Solarertrag)
        max_soc_for_grid_charge = 50.0
        pv_info_str = f"⚠️ Viel Sonne erwartet ({total_future_pv:.1f} kWh). Reduziere Netz-Ladegrenze auf {max_soc_for_grid_charge}%."
    else:
        pv_info_str = f"Sonne erwartet: {total_future_pv:.1f} kWh. Standard Netz-Ladegrenze: {max_soc_for_grid_charge}%."

    mode = 0
    target_power = 0.0
    target_soc = 99.0  # Standard-Ziel-SoC
    
    print(f"\n--- Optimierungs-Entscheidung für {current_hour}:00 Uhr ---")
    print(f"Aktueller Preis   : {current_price:.2f} Cent/kWh (Schnitt: {k_avg:.2f} Cent/kWh)")
    print(f"Schwellenwerte    : Low (P20): {cutoff_low:.2f} | High (P80): {cutoff_high:.2f} Cent/kWh")
    print(f"Aktueller Akku-SoC: {current_soc}% | {pv_info_str}")
    
    # =========================================================================
    # HEURISTISCHE ENTSCHEIDUNGSMATRIX
    # =========================================================================
    
    # Regel 1: ZWANGSLADEN aus dem Netz (Sehr günstiger Preis & Akku unter dynamischer Ladegrenze)
    if current_price <= cutoff_low and current_soc < max_soc_for_grid_charge:
        mode = 1
        target_power = 2.5  # Standard-Ladeleistung in kW
        target_soc = min(max_soc_for_grid_charge, 100.0)  # Ziel-SoC für das Zwangsladen
        print(f"-> Entscheidung: ZWANGSLADEN (Preis {current_price:.2f} <= Schwelle {cutoff_low:.2f} Cent/kWh)")
        
    # Regel 2: ENTLADESPERRE (Preis ist unterdurchschnittlich, aber ein massiver Spike kommt bald)
    elif current_price < k_avg and current_soc < 60.0:
        # Dank der zeitsynchronen Matrix schauen wir einfach auf die nächsten 6 Elemente (Stunden)
        next_6_hours = matrix[1:7]
        incoming_spike = any(row['k_act'] >= cutoff_high for row in next_6_hours)
        
        if incoming_spike:
            # PV-Check für die Entladesperre: Wenn die Sonne den Verbrauch bis dahin ohnehin deckt,
            # müssen wir den Akku nicht künstlich blockieren.
            if total_future_pv < total_future_con:
                mode = 2
                target_power = 0.0
                target_soc = 100  # 100% Soll-SoC 
                print("-> Entscheidung: ENTLADESPERRE (Schütze Akku-Kapazität für kommende Preisspitze)")
            else:
                print("-> Entscheidung: AUTOMATIK (Preisspike droht zwar, kommende PV deckt aber den Verbrauch)")
        else:
            print("-> Entscheidung: AUTOMATIK (Kein Preisspike in den nächsten 6h in Sicht)")
            
    # Regel 3: AUTOMATIK (Standard-Regelung des Miniservers, wenn keine Extrempreise vorliegen)
    else:
        print("-> Entscheidung: AUTOMATIK (Normaler Mischbetrieb)")
        
    return mode, target_power, target_soc

def simulate_24h_horizon(optimization_matrix: list, initial_soc: float) -> list:
    """
    Simuliert den 24-Stunden-Verlauf des SoC und der Batterie-Aktionen
    basierend auf der Preismatrix und den Prognosedaten.
    Kapselt die vollständige physikalische Berechnungslogik abseits der GUI.
    """
    import config  # Lokal oder global importieren
    
    chart_rows = []
    sim_soc = initial_soc
    battery_capacity_kwh = float(getattr(config, 'BATTERY_CAPACITY_KWH', 5.0))
    min_soc_limit = float(getattr(config, 'BATTERY_MIN_SOC', 5.0))
    max_soc_limit = float(getattr(config, 'BATTERY_MAX_SOC', 100.0))
    
    for i, row in enumerate(optimization_matrix[:24]):
        h = row['hour']
        
        # Matrix-Slice übergeben, damit die zu simulierende Stunde auf Index 0 liegt
        mode, target_power, target_soc = heuristic_optimizer(optimization_matrix[i:], h, sim_soc)
        
        pv = row['expected_p_pv']
        con = row['expected_p_act']
        net_pv_surplus = pv - con  # Erzeugungsüberschuss (>0) oder Defizit (<0)
        
        # Realistische physikalische Simulation des Akkus je nach Modus
        if mode == 1:
            # Zwangsladen aus dem Netz + PV-Überschuss falls vorhanden
            batt_action = target_power + max(0.0, net_pv_surplus)
            action_text = f"Zwangsladen ({target_power} kW)"
        elif mode == 2:
            # Entladesperre: Akku darf das Haus nicht stützen (<0), nimmt aber PV-Überschuss auf (>0)
            batt_action = max(0.0, net_pv_surplus)
            action_text = "Entladesperre aktiv"
        else:
            # Automatikbetrieb (mode=0): Akku versucht das Haus vollständig auszubalancieren
            batt_action = net_pv_surplus
            action_text = "Automatikbetrieb"
            
        old_soc = sim_soc
        # SoC-Änderung berechnen: (Leistung in kW * 1h / Kapazität in kWh) * 100%
        soc_change = (batt_action / battery_capacity_kwh) * 100
        sim_soc += soc_change
        
        # Physikalische Grenzen deckeln
        if sim_soc > max_soc_limit:
            actual_charge_pct = max_soc_limit - old_soc
            batt_action = (actual_charge_pct / 100) * battery_capacity_kwh
            sim_soc = max_soc_limit
        elif sim_soc < min_soc_limit:
            actual_discharge_pct = old_soc - min_soc_limit
            batt_action = -((actual_discharge_pct / 100) * battery_capacity_kwh)
            sim_soc = min_soc_limit
            
        chart_rows.append({
            "Uhrzeit": f"{h:02d}:00",
            "Strompreis (Cent/kWh)": row['k_act'],
            "PV-Prognose (kW)": pv,
            "Verbrauch-Prognose (kW)": con,
            "Geplante Batterie-Aktion (kW)": round(batt_action, 2),
            "Simulierter SoC (%)": round(old_soc, 1),
            "Steuerbefehl": action_text
        })
        
    return chart_rows