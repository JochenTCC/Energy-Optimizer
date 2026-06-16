# optimizer.py
from typing import List, Dict, Any, Tuple
import pulp
import config  # Lokaler Import der Konfiguration

def heuristic_optimizer(matrix: List[Dict[str, Any]], current_hour: int, current_soc: float) -> Tuple[int, float, float]:
    """
    Berechnet den optimalen Betriebsmodus und die Ziel-Leistung für den Loxone Miniserver.
    Nutzt mathematische lineare Optimierung (MILP) über das PuLP-Framework.
    
    Modi (Ernie_Mode):
        0 = Automatik (Normalbetrieb / Batterieladung und -entladung freigegeben)
        1 = Zwangsladen (Laden aus dem Netz mit Ziel-Leistung)
        2 = Entladesperre (Batterieentladung blockiert, um Kapazität für teure Stunden zu sparen)
    """
    if not matrix:
        print("🚨 Optimizer-Fehler: Matrix ist leer.")
        return 0, 0.0, 99.0

    # 1. Parameter sicher aus der Config laden (mit Fallbacks)
    battery_capacity = float(getattr(config, 'BATTERY_CAPACITY_KWH', 10.0))
    min_soc = float(getattr(config, 'BATTERY_MIN_SOC', 10.0))
    max_soc = float(getattr(config, 'BATTERY_MAX_SOC', 100.0))
    max_power = float(getattr(config, 'BATTERY_MAX_POWER_KW', 2.5))
    efficiency = float(getattr(config, 'BATTERY_EFFICIENCY', 0.97))
    k_push = float(getattr(config, 'K_PUSH', 3.7))

    # Planungshorizont bestimmen (maximal 24 Stunden)
    N = min(24, len(matrix))

    # SoC-Grenzen von Prozent in absolute kWh umrechnen
    e_min = (min_soc / 100.0) * battery_capacity
    e_max = (max_soc / 100.0) * battery_capacity
    e_init = (current_soc / 100.0) * battery_capacity

    # 2. Lineares Optimierungsproblem erstellen
    prob = pulp.LpProblem("Energy_Cost_Minimization", pulp.LpMinimize)

    # 3. Entscheidungsvariablen definieren
    p_grid_buy = [pulp.LpVariable(f"p_grid_buy_{t}", lowBound=0) for t in range(N)]
    p_grid_sell = [pulp.LpVariable(f"p_grid_sell_{t}", lowBound=0) for t in range(N)]
    p_charge = [pulp.LpVariable(f"p_charge_{t}", lowBound=0, upBound=max_power) for t in range(N)]
    p_discharge = [pulp.LpVariable(f"p_discharge_{t}", lowBound=0, upBound=max_power) for t in range(N)]
    e_batt = [pulp.LpVariable(f"e_batt_{t}", lowBound=e_min, upBound=e_max) for t in range(N)]
    
    # Binäre Hilfsvariable: 1 = Akku lädt, 0 = Akku entlädt (verhindert Gleichzeitigkeit)
    delta_charge = [pulp.LpVariable(f"delta_charge_{t}", cat=pulp.LpBinary) for t in range(N)]

    # 4. Zielfunktion: Gesamtkosten über den Horizont minimieren
    # Netzbezug * Einkaufspreis - Einspeisung * Einspeisevergütung
    prob += pulp.lpSum([
        p_grid_buy[t] * matrix[t]['k_act'] - p_grid_sell[t] * k_push
        for t in range(N)
    ])

    # 5. Mathematische Nebenbedingungen (Constraints) definieren
    for t in range(N):
        p_pv = matrix[t]['expected_p_pv']
        p_con = matrix[t]['expected_p_act']

        # KNOTENGLEICHUNG: Energieerhaltung des Hauses
        # Erzeugung + Zukauf + Entladung == Verbrauch + Verkauf + Ladung
        prob += (p_pv + p_grid_buy[t] + p_discharge[t] == p_con + p_grid_sell[t] + p_charge[t])

        # LEISTUNGSGRENZEN: Gekoppelt an die binäre Variable
        prob += (p_charge[t] <= max_power * delta_charge[t])
        prob += (p_discharge[t] <= max_power * (1 - delta_charge[t]))

        # BATTERIE-DYNAMIK: Energieinhalt der aktuellen Stunde unter Berücksichtigung des Wirkungsgrads
        if t == 0:
            prob += (e_batt[t] == e_init + p_charge[t] * efficiency - p_discharge[t] / efficiency)
        else:
            prob += (e_batt[t] == e_batt[t-1] + p_charge[t] * efficiency - p_discharge[t] / efficiency)

    # 6. Problem mathematisch lösen (stummgeschaltet ohne Log-Spam)
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    # Fallback-Sicherung falls der Solver fehlschlägt
    if pulp.LpStatus[prob.status] != "Optimal":
        print(f"⚠️ MILP-Solver konnte keine optimale Lösung finden Status: {pulp.LpStatus[prob.status]}. Fallback auf Automatik.")
        return 0, 0.0, 99.0

    # 7. Ergebnisse für die aktuelle Stunde (t=0) extrahieren
    opt_charge = p_charge[0].varValue if p_charge[0].varValue is not None else 0.0
    opt_discharge = p_discharge[0].varValue if p_discharge[0].varValue is not None else 0.0
    opt_grid_buy = p_grid_buy[0].varValue if p_grid_buy[0].varValue is not None else 0.0
    
    p_pv_0 = matrix[0]['expected_p_pv']
    p_con_0 = matrix[0]['expected_p_act']
    net_pv_surplus = p_pv_0 - p_con_0

    # 8. Übersetzung der kontinuierlichen Solver-Ergebnisse in Loxone-Modi
    mode = 0
    target_power = 0.0
    target_soc = 99.0

    # REGEL 1: ZWANGSLADEN
    # Wenn der Solver den Akku aktiv laden will UND zeitgleich Strom aus dem Netz kauft
    if opt_charge > 0.05 and opt_grid_buy > 0.05:
        mode = 1
        target_power = round(opt_charge, 2)
        # Berechne den mathematisch exakten Ziel-SoC am Ende dieser Stunde
        opt_end_soc = (e_batt[0].varValue / battery_capacity) * 100.0
        target_soc = round(max(current_soc, opt_end_soc), 1)
    
    # REGEL 2: ENTLADESPERRE
    # Wenn ein Haus-Defizit vorliegt, der Solver aber entscheidet, den Akku NICHT zu entladen (Sperre für spätere Spitzen)
    # und der Akku theoretisch genug Energie hätte, um einzuspringen (> min_soc + 2%)
    elif net_pv_surplus < -0.05 and opt_discharge < 0.05 and current_soc > (min_soc + 2.0):
        mode = 2
        target_power = 0.0
        target_soc = 100.0  # Volle Sperrwirkung im Huawei WR erzwingen
    
    # REGEL 3: AUTOMATIK (Normalbetrieb)
    else:
        mode = 0
        target_power = 0.0
        target_soc = 99.0

    # Konsolen-Logs zur Überwachung ausgeben
    print(f"\n--- 🧮 MILP Optimierungs-Entscheidung für {current_hour}:00 Uhr ---")
    print(f"Aktueller Brutto-Preis: {matrix[0]['k_act']:.2f} Cent/kWh")
    print(f"Aktueller Akku-SoC    : {current_soc:.1f}%")
    print(f"Optimierter Fahrplan  : Ladung={opt_charge:.2f} kW | Entladung={opt_discharge:.2f} kW | Netzbezug={opt_grid_buy:.2f} kW")
    
    modi_text = {0: "AUTOMATIK", 1: "ZWANGSLADEN", 2: "ENTLADESPERRE"}
    print(f"-> Steuerbefehl Loxone: {modi_text[mode]} (Leistung: {target_power} kW, Ziel-SoC: {target_soc}%)")

    return mode, target_power, target_soc


def simulate_24h_horizon(optimization_matrix: list, initial_soc: float) -> list:
    """
    Simuliert den 24-Stunden-Verlauf des SoC unter exakter Berücksichtigung
    des neuen mathematischen Wirkungsgrads und der Leistungsbegrenzungen.
    """
    chart_rows = []
    sim_soc = initial_soc
    
    battery_capacity_kwh = float(getattr(config, 'BATTERY_CAPACITY_KWH', 10.0))
    min_soc_limit = float(getattr(config, 'BATTERY_MIN_SOC', 10.0))
    max_soc_limit = float(getattr(config, 'BATTERY_MAX_SOC', 100.0))
    max_power = float(getattr(config, 'BATTERY_MAX_POWER_KW', 2.5))
    efficiency = float(getattr(config, 'BATTERY_EFFICIENCY', 0.97))
    
    for i, row in enumerate(optimization_matrix[:24]):
        h = row['hour']
        
        # Den mathematischen Optimizer für den verbleibenden Horizont aufrufen
        mode, target_power, target_soc = heuristic_optimizer(optimization_matrix[i:], h, sim_soc)
        
        pv = row['expected_p_pv']
        con = row['expected_p_act']
        net_pv_surplus = pv - con
        
        # Realistische physikalische Nachbildung der Batteriereaktion im jeweiligen Modus
        if mode == 1:
            batt_action = target_power + max(0.0, net_pv_surplus)
            action_text = f"Zwangsladen ({target_power} kW)"
        elif mode == 2:
            batt_action = max(0.0, net_pv_surplus)
            action_text = "Entladesperre aktiv"
        else:
            batt_action = net_pv_surplus
            action_text = "Automatikbetrieb"
            
        old_soc = sim_soc
        
        # Technische Leistungsbegrenzung des Wechselrichters anwenden
        if batt_action > max_power:
            batt_action = max_power
        elif batt_action < -max_power:
            batt_action = -max_power

        # Physikalischen Wirkungsgrad auf die SoC-Änderung anwenden
        if batt_action >= 0:
            energy_change = batt_action * efficiency
        else:
            energy_change = batt_action / efficiency
            
        soc_change = (energy_change / battery_capacity_kwh) * 100
        sim_soc += soc_change
        
        # Hard-Limits absichern und reale Batterieleistung rückrechnen bei Überlauf
        if sim_soc > max_soc_limit:
            sim_soc = max_soc_limit
            actual_energy = ((max_soc_limit - old_soc) / 100) * battery_capacity_kwh
            batt_action = actual_energy / efficiency if actual_energy >= 0 else actual_energy * efficiency
        elif sim_soc < min_soc_limit:
            sim_soc = min_soc_limit
            actual_energy = ((min_soc_limit - old_soc) / 100) * battery_capacity_kwh
            batt_action = actual_energy * efficiency if actual_energy < 0 else actual_energy / efficiency
            
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