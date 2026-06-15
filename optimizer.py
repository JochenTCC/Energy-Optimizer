def heuristic_optimizer(matrix, current_hour, current_soc):
    """Berechnet den Modus und die Ladeleistung basierend auf Preisschwellenwerten."""
    all_prices = sorted([row['k_act'] for row in matrix])
    if not all_prices:
        return 0, 0.0
        
    k_avg = sum(all_prices) / len(all_prices)
    cutoff_low = all_prices[4]   # Günstigste ~20%
    cutoff_high = all_prices[-5] # Teuerste ~20%
    
    current_row = next((row for row in matrix if row['hour'] == current_hour), None)
    if not current_row:
        return 0, 0.0
        
    current_price = current_row['k_act']
    mode = 0
    target_power = 0.0
    
    print(f"\n--- Optimierungs-Entscheidung für {current_hour}:00 Uhr ---")
    print(f"Aktueller Preis: {current_price} Cent/kWh | Tag-Schnitt: {k_avg:.2f} Cent/kWh")
    print(f"Aktueller Live-SoC: {current_soc}%")
    
    if current_price <= cutoff_low and current_soc < 90:
        mode = 1
        target_power = 2.5
        print("-> Entscheidung: ZWANGSLADEN")
    elif current_price < k_avg and current_soc < 60:
        future_rows = [row for row in matrix if current_hour < row['hour'] <= current_hour + 6]
        incoming_spike = any(row['k_act'] >= cutoff_high for row in future_rows)
        if incoming_spike:
            mode = 2
            target_power = 0.0
            print("-> Entscheidung: ENTLADESPERRE")
    else:
        print("-> Entscheidung: AUTOMATIK")
        
    return mode, target_power