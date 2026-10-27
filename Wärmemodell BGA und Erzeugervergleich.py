# -*- coding: utf-8 -*-
"""
Created on Tue Jan 13 16:32:42 2026

@author: Föcker
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math

###############################################################################
# Funktionen des Wärmemodells
def berechne_reaktorflaeche(d,h):
    r = d/2
    A_floor = math.pi*r**2
    A_wall = math.pi*d*h
    return (A_floor, A_wall)

def berechne_dachflaeche (d,h_dach):
    r = d/2
    r_ball = (r**2 + h_dach**2)/(2*h_dach)
    A_roof = 2* math.pi * r_ball * h_dach
    return A_roof
    
def berechne_waermeverlust_gas (v_dot_bg, temp_S): 
    #Berechnung des täglichen Wärmeverlusts (latent und sensibel) durch den 
    #Gasaustrag. 
    #Akzeptiert eine pandas Serie für die Außentemperatur
    
    p_total_hpa = 1013.25
    p_sat_hpa = 6.112 * math.exp((17.67*temp_GR)/(temp_GR +243.5))
    
    #absolute Luftfeuchte * (Masse Wasser pro Masse trockenes Gas)
    x = (M_h2o / M_biogas_dry) * (p_sat_hpa / (p_total_hpa - p_sat_hpa))
    
    # #täglcihe Masse des trockenen Biogases
    mass_biogas_dry = v_dot_bg * rho_bg_dry
    
    # #tägliche Masse des ausgetragenen Wassserdampfs
    mass_h2o_vap = mass_biogas_dry * x
    
    h_v_h2o = (-0.00000020 *temp_GR**4 + 0.00009444 * temp_GR**3 -0.01823791
               *temp_GR**2-1.26304656 *temp_GR +2489.28046616) #kJ/kg

    #täglicher latenter Wärmeverlust (konstanter Wert, da T_Fermenter konstant)
    loss_lat = mass_h2o_vap * h_v_h2o 
    
    #2. sensibler Wärmeverlust (Dieser Teil ist von der Außentemperatur 
    #abhängig)
    
    dT_gas = temp_GR - temp_S
    
    
    loss_sens_gas = mass_biogas_dry * cp_bg_dry*dT_gas #J/kg
    loss_sens_vap = mass_h2o_vap * cp_h2o_vap * dT_gas
    loss_sens_total = (loss_sens_gas+loss_sens_vap)/1000 #kJ/kg
    
    #Gesamtverluste in kWh/d
    loss_gas = (loss_lat + loss_sens_total )/3.6e3
    
    return loss_gas

#Berechnung Energieeintrag Fermenter
def Energiebedarf_Fermenter(m_dot, temp_S, temp_GR, Cp_GR):
    
    #Heizenergiebedarf zur Aufheizung des Substrats
    energy_subs = (m_dot * Cp_GR * (temp_GR - temp_S))/3.6e6
    
    return energy_subs

def loss_convective(temp_S, temp_GR, Cp_GR, k_wall, k_ground, k_roof, 
                    u_wand,u_boden, u_dach, temp_erde):
    
    dT_air = temp_GR - temp_S
    dt_ground = temp_GR - temp_erde
    
    #Verluste in kW berechnen 
    loss_wall = (k_wall * u_wand *dT_air)/1000    #kW
    loss_ground = (k_ground * u_boden * dt_ground) / 1000
    loss_roof = (k_roof * u_dach * dT_air) /1000
    
    # Verluste in kWh/d
    Energy_loss_conv = (loss_ground+loss_roof+loss_wall) * 24 #kWh/d
    
    return Energy_loss_conv  

def Lastgang_Waermenetz(temp_S, Q_total_Waermenetz):
    A = 2.496
    B = -34.74
    C = 5.661
    D = 0.1021
    
    h_tempS = D + A / (1 + (B / (temp_S - 40)) ** C) 
    
    Lastgang_Netz = (Q_total_Waermenetz/365) * h_tempS
    
    return Lastgang_Netz

# Berechnung auskoppelbare Wärme Gärrest in kwh/
def Waermeauskopplung (m_dot, temp_S, temp_GR, Cp_GR, dT):
    
    Q_res = (m_dot * Cp_GR * dT)/3.6e6
    
    return Q_res

# Funktionen der Simulation der Wärmeerzeuger
#Berechnung Wärmepumpe

def WP (Q_res, Prozesswaermeenergie_Gesamt):   #kWh/d
   
    P_WP = Prozesswaermeenergie_Gesamt-Q_res
    return (P_WP) 

#Die folgende Funktion berechnet den Eigenwärmebedarf der Biogasanlage als
# Indikator für die
# Genauigkeit des Wärmemodells

def Eigenwaermebedarf(LG_bga, v_dot_bg, HW_bg, eta_bhkw):
    
    Q_bg = v_dot_bg*HW_bg  #kWh/d
    Q_bg_th = Q_bg * eta_bhkw  #kWh/d
    eta_th = LG_bga/Q_bg_th

    return eta_th #kWh/kWh

def Vielstoffofen (LG_total, HW_GP, TS_GP_vor, TS_GP_nach, eta_th_ofen, X_sep):
    
    E_bedarf = LG_total / eta_th_ofen
    
    m_dot_GP_daily_dry = E_bedarf/(HW_GP*TS_GP_nach)
    
    m_dot_GP_daily_wet = m_dot_GP_daily_dry * TS_GP_nach / X_sep / TS_GP_vor

    
    return m_dot_GP_daily_dry, m_dot_GP_daily_wet

def ikwk (
    el_market,           # Strompreise [€/MWh]
    heizlast_kw,         # Thermische Last [kW]
    speicher_start_kwh,  # Startfüllstand [kWh]
    speicher_kapa_kwh,   # Kapazität [kWh]
    
    # BHKW Parameter
    price_signal_bhkw,   # Einschaltschwelle [€/MWh]
    p_el_bhkw,           # Nennleistung elektrisch [kW]
    eta_el_bhkw,         # Wirkungsgrad el
    eta_th_bhkw,         # Wirkungsgrad th
    
    # Heizstab Parameter
    p_el_hs,             # Leistung [kW]
    Stromnebenkostenzuschlag,
    # WP Parameter
    price_signal_wp,     # Einschaltschwelle [€/MWh]
    p_el_wp,             # Leistung elektrisch [kW]
    cop_wp,              # COP
    
    # Regelung
    signal_wp_on # WP darf nur an, wenn Speicher < X% voll
):
    # """
    # Simuliert das gesamte iKWK-System in einer einzigen Zeitschleife.
    # Dies ermöglicht Abhängigkeiten (WP läuft nur, wenn Speicher leer).
    # """
    
    # --- 1. SICHERHEIT: ALLES IN NUMPY ARRAYS WANDELN ---
    # Das verhindert den "Ambiguous Truth Value" Fehler zuverlässig
    el_market = np.array(el_market)
    heizlast_kw = np.array(heizlast_kw)
    
    steps = len(el_market)
    
    # --- 2. THERMISCHE LEISTUNGEN BERECHNEN ---
    p_th_bhkw_nenn = (p_el_bhkw / eta_el_bhkw) * eta_th_bhkw
    p_th_hs_nenn = p_el_hs * 0.99 # Annahme eta=0.99
    p_th_wp_nenn = p_el_wp * cop_wp
    
    # --- 3. ERGEBNIS-ARRAYS VORBEREITEN ---
    # Wir speichern hier die thermischen Leistungen (für den Speicher)
    lastgang_bhkw_th = np.zeros(steps)
    lastgang_hs_th = np.zeros(steps)
    lastgang_wp_th = np.zeros(steps)
    
    speicher_saldo = np.zeros(steps)
    speicher_netto_fluss = np.zeros(steps)
    
    # Counter und Status
    starts_bhkw = 0; war_an_bhkw = False
    starts_hs = 0;   war_an_hs = False
    starts_wp = 0;   war_an_wp = False
    
    aktueller_speicher = speicher_start_kwh
    
    # --- 4. DIE HAUPTSCHLEIFE (ITERATION) ---
    for t in range(steps):
        
        preis = el_market[t]
        last = heizlast_kw[t]
        
        # A) HEIZSTAB (Vorrang bei negativen Preisen)
        if preis < (0-Stromnebenkostenzuschlag):
            p_hs = p_th_hs_nenn * 1/4
            hs_an = True
        else:
            p_hs = 0
            hs_an = False
            
        # B) BHKW (Preissignal)
        if preis >= price_signal_bhkw:
            p_bhkw = p_th_bhkw_nenn *1/4
            bhkw_an = True
        else:
            p_bhkw = 0
            bhkw_an = False
            
        # C) WÄRMEPUMPE (Preis + Speicherstand)
        # Bedingung 1: Preis ist günstig (aber nicht negativ, da läuft HS)
        preis_ok = (0 <= preis < price_signal_wp)
        
        # Bedingung 2: Speicher ist leer genug
        # Wir schauen auf den Füllstand VOR der Produktion in diesem Schritt
        fuellstand_rel = aktueller_speicher / speicher_kapa_kwh
        speicher_bedarf = fuellstand_rel < signal_wp_on
        
        if preis_ok and speicher_bedarf:
            p_wp = p_th_wp_nenn *1/4
            wp_an = True
        else:
            p_wp = 0
            wp_an = False
            
        # D) STARTS ZÄHLEN
        if bhkw_an and not war_an_bhkw: starts_bhkw += 1
        if hs_an and not war_an_hs:     starts_hs += 1
        if wp_an and not war_an_wp:     starts_wp += 1
        
        war_an_bhkw = bhkw_an
        war_an_hs = hs_an
        war_an_wp = wp_an
        
        # E) SPEICHER BILANZIERUNG
        # Summe Erzeugung (Thermisch!)
        erzeugung = (p_bhkw + p_hs + p_wp)
        
        # Nettofluss (kW): Erzeugung - Last
        netto_kw = erzeugung - last
        
        # Energieänderung in dieser Viertelstunde (kW * 0.25h)
        delta_kwh = netto_kw * 0.25
        
        # Neuer Füllstand berechnen
        neuer_speicher = aktueller_speicher + delta_kwh
        
        # Grenzen (Clipping)
        if neuer_speicher > speicher_kapa_kwh:
            neuer_speicher = speicher_kapa_kwh
            # In Realität würde hier abgeregelt, im Modell ist die Energie 
            #"verloren" (Notkühler)
            
        elif neuer_speicher < 0:
            neuer_speicher = 0
            # Hier müsste eigentlich ein Gaskessel einspringen
            
        # F) WERTE SPEICHERN
        lastgang_bhkw_th[t] = p_bhkw
        lastgang_hs_th[t]   = p_hs
        lastgang_wp_th[t]   = p_wp
        speicher_saldo[t]   = neuer_speicher
        speicher_netto_fluss[t] = netto_kw
        
        aktueller_speicher = neuer_speicher

    # --- 5. RÜCKGABE ALS TUPEL ---
    return (
        lastgang_bhkw_th, 
        lastgang_hs_th, 
        lastgang_wp_th, 
        speicher_saldo, 
        starts_bhkw, 
        starts_hs, 
        starts_wp
    )

# Die folgenden Funktionen sind aus einer älterne Version der Simulation. 
# In der aktuellen Version sind die TEile "BHKW", "Heizstab" und "Wärmepumpe" 
#gemeinsam gesteuert als "IKWK" System implementiert

def BHKW(el_market, price_signal_on, P_el_BHKW):
    
    #bhkw Logik
    BHKW_Lastgang = []
    starts_bhkw = 0
    war_an_bhkw = False
    
    for i in el_market: 
        ist_an_bhkw = i >= price_signal_on
        if ist_an_bhkw:
            P_out_bhkw = P_el_BHKW
            if not war_an_bhkw:
                starts_bhkw += 1
        else: 
            P_out_bhkw = 0 #kW
        
        BHKW_Lastgang.append(P_out_bhkw)
        war_an_bhkw = ist_an_bhkw
    
    return BHKW_Lastgang, starts_bhkw

def Heizstab (el_market, P_el_HS, price_signal_WP_on, price_signal_on):
    HS_Lastgang = []
    starts_HS = 0
    war_an = False
    
    for i in el_market: 
        ist_an = i < 0
        if ist_an:
            P_out = P_el_HS
            if not war_an:
                starts_HS += 1
        else: 
            P_out = 0 #kW
        
        HS_Lastgang.append(P_out)
        war_an = ist_an
    
    return HS_Lastgang, starts_HS

def WP_Lastgang (el_market, P_el_WP, price_signal_WP_on):
    WP_Lastgang = []
    starts_WP = 0
    war_an = False
    
    for i in el_market: 
        ist_an = i < price_signal_WP_on and i >= 0
        if ist_an:
            P_out = P_el_WP * COP_WP
            if not war_an:
                starts_WP += 1
        else: 
            P_out = 0 #kW
        
        WP_Lastgang.append(P_out)
        war_an = ist_an
    return WP_Lastgang, starts_WP

def Speicher (heizlast_kw_hourly, bhkw_kw_hourly, WP_kW_hourly, HS_kW_hourly, 
              Speicher_start,Speicher_kapa):
    
    # Q_Speicher = V_Speicher * cp_h20 * (Temp_vor-Temp_rueck)
    # Q_Speicher = heizlast_kw_hourly - bhkw_kw_hourly-WP_kW_hourly
   
    # Berechnet den Speicherfüllstand unter Berücksichtigung von Kapazitätsgrenzen.
    # Da der aktuelle Füllstand vom vorherigen abhängt (Pfadabhängigkeit),
    # ist hier eine Schleife (oder numba) notwendig, wenn man Limits (Min/Max) hat.
  
    # Erzwinge von numpy arrays: 
    heizlast_kw_hourly = np.array(heizlast_kw_hourly)
    bhkw_kw_hourly = np.array(bhkw_kw_hourly)
    WP_kW_hourly = np.array(WP_kW_hourly)
    HS_kW_hourly= np.array(HS_kW_hourly)
    
    # Netto-Leistung (Positiv = Überschuss/Laden, Negativ = Defizit/Entladen)    
    Lastgang_Speicher = (-heizlast_kw_hourly + bhkw_kw_hourly+ WP_kW_hourly
    +HS_kW_hourly)
    
    # Energieänderung pro Zeitschritt (15 min = 0.25 h)
    delta_energie_kwh = Lastgang_Speicher 
    
    # Speicherverlauf berechnen
    Speicher_Saldo = np.zeros_like(delta_energie_kwh)
    aktuell = Speicher_start
    
    # Iteration ist hier nötig für Min/Max-Begrenzung (Clipping)
    # (Bei sehr großen Arrays könnte man dies mit numba beschleunigen)
    for i in range(len(delta_energie_kwh)):
        aktuell += delta_energie_kwh[i]
        
        # Begrenzung: Nicht unter 0 und nicht über Kapazität
        if aktuell < 0:
            aktuell = 0
        elif aktuell > Speicher_kapa:
            aktuell = Speicher_kapa
            
        Speicher_Saldo[i] = aktuell
    return Speicher_Saldo, Lastgang_Speicher


###############################################################################
###############################################################################
###############################################################################

#Konstanten
#Cp_GR = 3800 #J/kg*K spez. Wärmekapazität Gärrest

#Einlesen der Zeitreihen TEmperatur und EPEX DayAhead Markt
mean_temp = pd.read_csv(("mittl._Temp_tag_2024.csv"), delimiter = ";", 
                        skiprows=0)  #Einlese der Temperaturdaten aus CDC 
#                                       @Deutscher Wetterdienst


el_price24 = pd.read_csv(
"energycharts_Stromproduktion_und_Börsenstrompreise_in_Deutschland_2024.csv",
 delimiter = ";", skiprows=1)
el_market = el_price24.iloc[:,1] #€/MWh

temp_erde = 10  #°C  #Annahme zur Berechnung des Wärmeverlustes über die 
#   Bodenplatte der ANlage

v_dot_bg = 5000 #Nm^3/d durschnittliche tägliche Gasproduktion der Anlage
#h_v_h2o = 2.406e6 #J/kg Verdampfungsenthalpie Wasser bei 40°C
cp_bg_dry = 1500 #J/kgK spez. wärmekapazität trockenes Biogas
cp_h2o_vap = 1860 #J/kgK spez. Wärmekapazität Wasserdampf
rho_bg_dry = 1.22 #kg/m^3 Dichte trockenes Biogas (Normzustand)
M_biogas_dry = 27.26 #g/mol Molmasse trockenes Biogas
M_h2o = 18.015 #g/mol molare Masse Wasser

cp_h20 = 4200 #J/kgK spez. Wärmekapazität Wasser
cp_straw = 2000 #J/kgK spez. Wärmekapazität Stroh
TS_Substrat = 0.12 # %/100   Trockensubstanzgehalt des Substrats

HW_bg = 5.5 #kWh/m^3
eta_bhkw = 0.405  #aus Benchmark Datenbank

HW_GP = 2.8 #kWh/kg Heizwert des Gärproduktes
TS_GP_nach = 0.3 # %/100 Trockensubstanzgehalt des Gärproduktes nach der 
#                       Separation
TS_GP_vor = 0.1 # %/100 Trockensubstanzgehalt vor der Separation
X_sep = 0.25  # Abscheidegrad der Separation

#Variablen
m_dot= 36876 #kg/d  Substrat-massenstrom der BGA
temp_S = mean_temp.iloc[:,1] #einlesen Tagesdurchschnittstemperaturen
temp_GR= 40 #°C   # Eingestellte Prozesstemperatur
dT = 15 #°C Temperaturabsenkung Gärrest am Wärmetauscher
Verlustterm_WÜ = 0.2
eta_WÜ = 0.95


Gasgestehungskosten = 0.08 #€/kWh


Q_total_Waermenetz = 3200000 #kWh/a Gesamtwärmebedarf des Wärmenetzes

Abschreibezeitraum = 10 #Jahre
Zinssatz = 4 # %

#Eingabe Geometriedaten Biogasanlage
d_f1 = 16
d_f2 = 16
d_f3 = 26

h_f1 = 6
h_f2 = 6
h_f3 = 6

hd_f1 = 5
hd_f2 = 5
hd_f3 = 5

u_wand = 0.325977069 #W/m^2*K
u_boden = 0.250980684
u_dach = 1.883926052

#Initialisierung 
d = 1 #m Durchmesser Fermenter
h= 1 #m Höhe Fermenter ohne Dach
h_dach = 1 #m Dachspitzenhöhe über Phasenübergang


#Berechnung Spezifische Wärmekapazität Substrat
Cp_GR = cp_h20*(1-TS_Substrat)+cp_straw*TS_Substrat  #J/kg

# Variablen definieren für die Berechnung der Geometrien
f1_ground, f1_wall = berechne_reaktorflaeche(d= d_f1, h= h_f1)
f1_roof = berechne_dachflaeche(d=d_f1,h_dach= hd_f1)

f2_ground, f2_wall = berechne_reaktorflaeche(d= d_f2, h= h_f2)
f2_roof = berechne_dachflaeche(d= d_f2,h_dach= hd_f2)

ng1_ground, ng1_wall = berechne_reaktorflaeche(d= d_f3, h= h_f3)
ng1_roof = berechne_dachflaeche(d=d_f3,h_dach= hd_f3)

# kumulierte Flächen 
k_wall = f1_wall + f2_wall + ng1_wall
k_ground = f1_ground + f2_ground + ng1_ground
k_roof = f1_roof + f2_roof + ng1_roof

energy_ferm = Energiebedarf_Fermenter(m_dot, temp_S, temp_GR, Cp_GR)
energy_ferm_mean = sum(energy_ferm)/365

loss_conv = loss_convective(temp_S, temp_GR, Cp_GR, k_wall, k_ground, k_roof,
                            u_wand,u_boden, u_dach, temp_erde)
loss_conv_mean = sum(loss_conv)/365

loss_gas = berechne_waermeverlust_gas (v_dot_bg, temp_S) 
loss_gas_mean = sum(loss_gas)/365

LG_bga = Energiebedarf_Fermenter(m_dot, temp_S, temp_GR, Cp_GR) + loss_conv 
+ loss_gas
LG_bga_mean = sum(LG_bga)/365

print ("Berechnete Geometrie")
print (f"kumulierte Wandfläche: {k_wall: .2f} m^2") 
print (f"kumulierte Bodenfläche: {k_ground:.2f} m^2")
print (f"kumulierte Dachfläche: {k_roof: .2f} m^2")
print (f'Durchschnittliche konvektive Wärmeverluste: {loss_conv_mean} kWh/d')
print (f'Durchschnittliche Gas-Wärmeverluste: {loss_gas_mean} kWh/d')
print (f'''Durchschnittlicher Energiebedarf zum Aufheizen des Substrates:
       {energy_ferm_mean} kWh/d''')
print (f'Durchschnittlicher Prozessenergiebedarf: {LG_bga_mean} kWh/d')

#Berechnung des Eigenstromverbrauchs bei vollverstromung des Gases
X_th_eigen = ((sum(Eigenwaermebedarf(LG_bga, v_dot_bg, HW_bg, eta_bhkw))/365)
                *100 ) #%

print (f'Der Eigenwaermebedarf der Biogasanlage betraegt: {X_th_eigen}')

# Abrufung der Funktion zum Lastgang des Wärmenetzes
LG_Netz = Lastgang_Waermenetz(temp_S, Q_total_Waermenetz)
#Berechnung des kombinierten Lastgangs
LG_total = LG_Netz + LG_bga
#Heizenergiebedarf des Fermenters == Waermesenke der WP

#Dem Gärrest bei gegebenen Delta T entnehmbare Wärme
Auskoppelbare_waerme = Waermeauskopplung(m_dot, temp_S, temp_GR, Cp_GR, dT) 

#############################################################################
# Nicht teil der Simulation aber für folgende verbesserte 
# Wärmepumpendimsionierung noch relevant: 

# #Kilowatt Verdichterleistung
WP_P_el = WP(Waermeauskopplung(m_dot, temp_S, temp_GR, Cp_GR, dT), LG_bga)/24 #kW
WP_P_el_mean = sum(WP_P_el)/365 #kW

# #Heizleistung Wärmepumpe
#WP_P_th = WP_P_el*WP_COP

# #Jahresarbeitszahl der WP
#WP_COP= WP(Waermeauskopplung, Energiebedarf_Fermenter)[1].sum()/365
WP_COP = LG_bga/WP_P_el
WP_SCOP = sum(WP_COP)/365

print(f''''Die aus dem Gärprodukt auskoppelbare Wärmemenge beträgt: 
      {Auskoppelbare_waerme} kWh/d''')
###############################################################################
###############################################################################
###############################################################################4

# Eingabe der Variablen für die Simulaiton der Wärmeerzeuger


# # Fermenterheizung Rohgasbrenner
P_nenn_RGB = 1000 #kW  #Heizleistung des Rohgasbrenners (RGB)
CapEx_RGB = 200 # €/kW   # Spezifische INvestitinskosten des RGB
Wartung = 0.01 #€/kWh   # Spezifische Wartungskosten

Kosten_Rohgasbrenner = ((((sum(LG_total)*(1/eta_WÜ))*(Gasgestehungskosten
                        +Wartung)) 
                        + ((CapEx_RGB*P_nenn_RGB)*(1+Zinssatz/100)
                           /Abschreibezeitraum))
                            /sum(LG_total)) *(-1)
# Anteil der zum Heizen genutzen Menge Gas an der Jahresgeaamtproduktion
gasuse_RGB = (sum(LG_total)*(1/eta_WÜ)/HW_bg)/(v_dot_bg*365) * 100

print(f'''Der durchschnittliche Wärmeerzeugungspreis des Rohgasbrenners beträgt: 
      {Kosten_Rohgasbrenner} €/kWh''')
print(f'''Der Rohgasbrenner verwendet {gasuse_RGB} % der Gasproduktion der
      BGA \n zur Wärmebereitstellung. ''')

###############################################################################
#Vielstoffofen

P_nenn_ofen = 999 #kW
P_th_max_ofen = 700 #kW_th
eta_th_ofen = P_th_max_ofen/P_nenn_ofen

m_dot_GP = Vielstoffofen(LG_total, HW_GP, TS_GP_vor, TS_GP_nach, 
                         eta_th_ofen, X_sep)[0]
m_dot_GP_wet = Vielstoffofen(LG_total, HW_GP, TS_GP_vor, TS_GP_nach, 
                             eta_th_ofen, X_sep)[1]
m_GP_total_dry = sum(m_dot_GP)
m_dot_GP_mean = m_GP_total_dry/365
m_dot_GP_total_wet = sum(m_dot_GP_wet)
m_dot_GP_wet_mean = m_dot_GP_total_wet/365
x_GP = (m_dot_GP_mean/m_dot)*100
m_dot_ash = m_dot_GP_mean * 0.05

P_dauer = sum(LG_total)/8000

CapEx_ofen = 890.891 #€/kW
P_el_ofen = 15 #kW
Strompreis_ofen = 0.18 #€/kWH
Arbeitsstunden = 1 #h/Tag
Lohnkosten = 28 # €/h
Wartung = 0.05 #%/100 von CapEx
Brennstoffkosten = (m_GP_total_dry/1000) * 1.48 

Waermeerzeugungspreis_ofen = ((((((CapEx_ofen*P_nenn_ofen)*(1+Zinssatz/100))
                                 /Abschreibezeitraum)
                              +(8000 * P_el_ofen*Strompreis_ofen)
                              +(365*Arbeitsstunden*Lohnkosten)
                              + ((Wartung*(CapEx_ofen*P_nenn_ofen))))
                              + (Brennstoffkosten))
                              /sum(LG_total)) * (-1)

print(f'Es fällt täglich ein Massenstrom von {m_dot_ash} kg/d an Asche an.')
print(f'''Die zur Deckung des Wärmebedarfs durschnittlich einzusetzende Menge 
      separierten Gärprodukts pro Tag ist {m_dot_GP_mean} kg/d. ''')
print(f'''Dies erfordert einen täglich zu separierenden Massenstrom
      nasses Gärprodukt von {m_dot_GP_wet_mean} kg/d. ''')

#print(f'Der dadurch eingesparte Gärprodukt-Massenstrom beträgt {x_GP} %')

print(f''''Bei Dauerbetrieb (7000h) müsste der Ofen bei einer Leistung von 
      {P_dauer} kW betrieben werden.''' )
print(f''''Der spezifische Waermeerzeugungspreis des Ofens beträgt
      {Waermeerzeugungspreis_ofen} €/kWh.''')
###############################################################################
###############################################################################
###############################################################################
#Modellsteuerung des iKWK Systems
price_signal_on = 110#€/MWh   #Preissignal ab dem das BHKW anspringen soll
P_el_BHKW = 525 #kW_elektrisch  # Nennleistung des BHLW elektrisch
eta_el_BHKW = 0.385   # elektrischer Wirkungsgrad
eta_th_BHKW = 0.45  # thermischer Wirkungsgrad
P_th_BHKW = (P_el_BHKW / eta_el_BHKW) * eta_th_BHKW   #Berechnung der erzeugten
# Thermischen Energiemenge

P_el_WP = 250 #kW    # Nennleistung elektrisch der WP
COP_WP = 3   # Coefficient of Performance  (ACHTUNG: geigentlich 
#Jahresabreitszahl da konstant über sein Jahr gerechnet)
price_signal_WP_on = 150 #€/MWh    # Preissignal, bis zu dem die WP arbeiten darf
signal_wp_on = 0.4 # %/100 Speicherkapazitaet    Bedingung, damit die WP 
#arbeiten kann -> Speicher muss unter 50 % voll sein

P_el_HS = 1000 #kW   elektrische Leistung des PtH Moduls

# Teil Wirtschaftlichkeit 

Speicher_kapa = 25000 #kWh    Kapazität des Wärmespeichers

Speicher_Fuellstand = 30 #%    Füllstand des SPeichers bei Beginn der SImulation

#Spezifische Invetitionskosten der im iKWK Modell verwendetetn Technologien
CapEx_spez_BHKW = 1300 # €/kW 
#CapEx_spez_BHKW_modernisiert = 500 #€/kW
CapEx_spez_WP = 1000 #€/kW
CapEx_spez_HS = 60 # €/kW
CapEx_spez_Speicher = 7 #€/kWh

#Förderungszuschlag in der ikWK Ausschreibung
ikwk_bonus_kWh = 0.07 #€/mWh 

#Gebührenpauschale für Netznutzung inkl. Steuern, NEtzgebühren usw. 
Stromnebenkostenzuschlag = 100 #€/MWh

###############################################################################
###############################################################################
###############################################################################

#AUfruf der iKWK Simulation 
   
# --- VORBEREITUNG DER DATEN ---
# Wir stellen sicher, dass alle Zeitreihen gleich lang sind
heizlast_kw_hourly = np.repeat(LG_total / 96, 96)
min_len = min(len(el_market), len(heizlast_kw_hourly))
el_market = el_market[:min_len]
heizlast_kw_hourly = heizlast_kw_hourly[:min_len]
stunden_achse = np.arange(min_len)

# Startwert in kWh umrechnen (falls Prozent gegeben ist)
Speicher_start_kwh = Speicher_kapa * (Speicher_Fuellstand / 100)

print("Starte iKWK Simulation...")


# Rückgabewerte direkt in einzelnen Variablen auffangen 
(
    bhkw_kw_hourly,   # Thermisch!
    HS_kW_hourly,     # Thermisch!
    WP_kW_hourly,     # Thermisch!
    Speicher_Saldo,   # kWh Füllstand
    starts_BHKW,
    starts_HS,
    starts_WP
) = ikwk(
    el_market=el_market,
    heizlast_kw=heizlast_kw_hourly,
    speicher_start_kwh=Speicher_start_kwh,
    speicher_kapa_kwh=Speicher_kapa,
    
    price_signal_bhkw=price_signal_on,
    p_el_bhkw=P_el_BHKW,
    eta_el_bhkw=eta_el_BHKW,
    eta_th_bhkw=eta_th_BHKW,
    
    p_el_hs=P_el_HS,
    Stromnebenkostenzuschlag = Stromnebenkostenzuschlag,
    
    price_signal_wp=price_signal_WP_on,
    p_el_wp=P_el_WP,
    cop_wp=COP_WP,
    
    signal_wp_on = signal_wp_on # WP läuft nur, wenn Speicher < 50%
)

#Speicherung der benötigten Daten in einem Dataframe

# DataFrame 
Lastgang_system = pd.DataFrame({
    "Lastgang BHKW": bhkw_kw_hourly,
    "Lastgang WP": WP_kW_hourly,
    "Lastgang Heizstab": HS_kW_hourly,
    "Speicher Füllstand": Speicher_Saldo,
    "Strompreis": el_market
})


#Exportoption des Data Frames als CSV
Lastgang_system.to_csv("Lastgang_System.csv")

###############################################################################
###############################################################################

#Erstellung des Berichts in der Command Line
Q_th_bhkw = sum(bhkw_kw_hourly)
Q_el_bhkw = sum((bhkw_kw_hourly/eta_th_BHKW)) * eta_el_BHKW
runtime_BHKW = Q_el_bhkw/P_el_BHKW
gasuse_bhkw = (Q_el_bhkw/HW_bg)/(v_dot_bg*365)*100

print(f'Das BHKW produziert: {Q_el_bhkw/1000} MWh elektrische Energie im Jahr')
print(f'Das BHKW startet: {starts_BHKW} mal')
print(f'''Das BHKW lief: {runtime_BHKW} Stunden bei einer Nennleistung von
      {P_el_BHKW} kW.''')
print(f'Das BHKW produziert {Q_th_bhkw} MWh thermische Energie.')
print(f'''Das BHKW verwendet {gasuse_bhkw} % der jährlichen Gasproduktion der 
      BGA zur Wärme/Stromerzeugung''')
###############################################################################
###############################################################################

Q_th_wp = sum(WP_kW_hourly)
Q_el_wp = Q_th_wp/COP_WP

runtime_wp = Q_el_wp/P_el_WP

print(f'Die WP produziert: {Q_th_wp/1000} MWh thermische Energie im Jahr')
print(f'Die WP startet: {starts_WP} mal')
print (f'''Die WP lief insgesamt {runtime_wp} Stunden bei einer Nennleistung
       von {P_el_WP} kW.''')
###############################################################################
###############################################################################

Q_th_hs = sum(HS_kW_hourly)
Q_el_hs = Q_th_hs/0.99 
runtime_HS = Q_el_hs / P_el_HS

print(f'Der Heizstab produziert: {Q_th_hs/1000} MWh thermische Energie im Jahr')
print(f'''Der HS lief: {runtime_HS} Stunden bei einer Nennleistung von 
      {P_el_HS} kW.''')
###############################################################################
###############################################################################
#Wirtschaftlichkeit 

Cashflow_BHKW = (((bhkw_kw_hourly/eta_th_BHKW)) * eta_el_BHKW) * (el_market/1000) 
Cashflow_WP = -1 * (WP_kW_hourly/COP_WP) * (el_market/1000)  
Cashflow_HS = -HS_kW_hourly * (el_market/1000)

BHKW_Konto = (np.cumsum(Cashflow_BHKW)[35134]) 
- (Q_el_bhkw * Gasgestehungskosten) 

WP_Konto = (np.cumsum(Cashflow_WP)[35134]) 
- ((Q_el_wp) * Stromnebenkostenzuschlag/1000)

HS_Konto = (np.cumsum(Cashflow_HS)[35134]) 
- (Q_el_hs*Stromnebenkostenzuschlag/1000)

Gesamt_Konto = BHKW_Konto + WP_Konto + HS_Konto

Preis_waermeerzeugung = Gesamt_Konto/ (Q_th_bhkw+Q_th_hs+Q_th_wp)


print(f'Die mit dem BHKW generierten Einnahmen betragen {BHKW_Konto} €')
print(f'Die mit der Waermepumpe generierten Einnahmen betragen {WP_Konto} €')
print(f'Die mit dem Heizstab generierten Einnahmen betragen {HS_Konto} €')
print(f'''Die Gesamteinnahmen am Strommarkt betragen 
      {BHKW_Konto+WP_Konto+HS_Konto} € ''')
print(f''''Der spezifische Preis der Waemrmeerzeung ist:
      {Preis_waermeerzeugung} €/kWh''')



CapEx_BHKW = ((CapEx_spez_BHKW * P_el_BHKW * (1+Zinssatz/100)) 
                / Abschreibezeitraum)
#CapEx_BHKW_modernisiert = (CapEx_spez_BHKW_modernisiert * 
#P_el_BHKW * (1+Zinssatz/100)) / Abschreibezeitraum
CapEx_WP = (CapEx_spez_WP * P_el_WP * (1+Zinssatz/100)) / Abschreibezeitraum
CapEx_HS = (CapEx_spez_HS * P_el_HS * (1+Zinssatz/100))/ Abschreibezeitraum
CapEx_Speicher = (CapEx_spez_Speicher * Speicher_kapa 
                  * (1+Zinssatz/100))/Abschreibezeitraum





ikwk_bonus = Q_el_bhkw * ikwk_bonus_kWh
ikwk_bonus_spez = ikwk_bonus/(Q_th_bhkw)

Waermeerzeugungskosten_spez_BHKW_modernisiert = ((-1*(CapEx_BHKW/Q_th_bhkw)) 
                                                + ((BHKW_Konto)/Q_th_bhkw)) 
Waermeerzeugungskosten_spez_BHKW_modernisiert_bonus = (
(-1*(CapEx_BHKW/Q_th_bhkw)) + ((BHKW_Konto)/Q_th_bhkw) + ikwk_bonus_spez)
Waermeerzeugungskosten_spez_WP = (-1*(CapEx_WP/Q_th_wp)) + (WP_Konto/Q_th_wp)
Waermeerzeugungskosten_spez_HS = (-1*(CapEx_HS/Q_th_hs)) + (HS_Konto/Q_th_hs)

Waermeerzeugungskosten_spez_gesamt = ((
                    (Waermeerzeugungskosten_spez_BHKW_modernisiert * Q_th_bhkw)
                    + (Waermeerzeugungskosten_spez_WP * Q_th_wp)
                    + (Waermeerzeugungskosten_spez_HS * Q_th_hs)
                    + (CapEx_Speicher*(-1)))
                    / (Q_th_bhkw+Q_th_wp+Q_th_hs))
                                

Waermeerzeugungskosten_spez_gesamt_bonus = ((
            (Waermeerzeugungskosten_spez_BHKW_modernisiert_bonus * Q_th_bhkw)
            + (Waermeerzeugungskosten_spez_WP * Q_th_wp)
            + (Waermeerzeugungskosten_spez_HS * Q_th_hs))
            / (Q_th_bhkw+Q_th_wp+Q_th_hs))


print(f'''Die spezifischen Wärmeerzeugungskosten des BHKW betragen:
      {Waermeerzeugungskosten_spez_BHKW_modernisiert} €/kWh.''')
print (f'''Die spezifischen Wärmeerzeugungskosten des BHKW, inkl. IKWK Bonus
       betragen: {Waermeerzeugungskosten_spez_BHKW_modernisiert_bonus} €/kWh.''')
print(f'''Die spezifischen Wärmeerzeugungskosten der WP betragen:
      {Waermeerzeugungskosten_spez_WP} €/kWh.''')
print(f'''Die spezifischen Wärmeerzeugungskosten des Heizstabs 
      betragen: {Waermeerzeugungskosten_spez_HS} €/kWh.''')

print(f'''Die spezifischen Wärmeerzeugungskosten des Gesamtsystems betragen: 
      {Waermeerzeugungskosten_spez_gesamt} €/kWh.''')
print(f'''Die spezifischen Wärmeerzeugungskosten des Gesamtsystems inkl IKWK 
      Bonus betragen: {Waermeerzeugungskosten_spez_gesamt_bonus} €/kWh.''')
###############################################################################
###############################################################################
############################################################################### 

###############################################################################
###############################################################################
###############################################################################    
# Daten Plotten
data_plot = pd.DataFrame({ 
    "Wärmeenerigebedarf Gesamt" :  LG_bga,
    "Substrataufheizung" : energy_ferm,
    "Verluste Konvektion" : loss_conv,
    "Verluste Gas" : loss_gas, 
    "mittlere Außentemperatur" : temp_S})
plt.figure(figsize = (12,6))

plt.plot(data_plot.index, data_plot['Wärmeenerigebedarf Gesamt'], 
         label='Gesamt-Wärmeenergie')
plt.plot(data_plot.index, data_plot['Substrataufheizung'], 
         label = 'Substrataufheizung')
plt.plot(data_plot.index, data_plot['Verluste Gas'], label='Gasverluste')
plt.plot(data_plot.index, data_plot['Verluste Konvektion'], 
         label='Konvektionsverluste')
#plt.plot(data_plot.index, data_plot['mittlere Außentemperatur'], 
#label = 'Mittlere Außentemperatur')
# 3. Titel und Achsenbeschriftungen hinzufügen 
#plt.title('Simulierter Jahresverlauf des Prozesswärmebedarfs der
# Modellbiogasanlage')
plt.xlabel('Tag des Jahres 2024', fontsize= 12)
plt.ylabel('Energiebedarf BGA (kWh/d)', fontsize= 12)
plt.grid(True) # Ein Gitter hinzufügen für bessere Lesbarkeit
plt.legend()


###############################################################################
###############################################################################

# 2. Plotten
# plt.figure(figsize=(15, 8)) 

fig, ax1 = plt.subplots(figsize=(30,12))



# B) BHKW-Betrieb als Stufenlinie
ax1.step(stunden_achse,Lastgang_system['Lastgang BHKW'], where='post', 
         color='blue', linewidth=0.08, label='Energiefluss BHKW (kWh_th)')

# C) Waermepumpenbetrieb als Stufenlinie
ax1.step(stunden_achse, Lastgang_system["Lastgang WP"], where='post', 
         color='green', linewidth=0.02, #
         label='Energiefluss Wärmepumpe (kWh_th)')

# D) Speicherfüllung als Stufenlinie. Betrag im negativen Bereich ist der
# Betrag um den der Speicher im jeweiligen X-Abschnitt gefüllt wird"
#ax1.step(stunden_achse, Lastgang_system["Lastgang Speicher"] , where='post',
# color='orange', linewidth=0.05, label='Speicher Energiefluss (kWh_th)')

ax1.step(stunden_achse, Lastgang_system["Lastgang Heizstab"], where = 'post',
         color = 'yellow', linewidth = 1,
         label = 'Energiefluss Heizstab (kWh_th)')

# A) Wärmebedarf als Fläche im Hintergrund
ax1.fill_between(stunden_achse, heizlast_kw_hourly, 
                 color='red', alpha=0.3, 
                 label='Energiebedarf Wärmesenke (kWh_th)')
#plt.fill_between(stunden_achse, Lastgang_system["Speicher"], color='grey', 
#alpha=0.3, label='Speicher (kWh_th)')

#plt.title("Jahresganglinie: Wärmebedarf vs. Erzeuger und Speicher")
ax1.set_xlabel("Viertelstunde des Jahres", color = "black", fontsize=20)
ax1.set_ylabel("Energiefluss pro Viertelstunde [kWh]", color = "black", 
               fontsize=20)
ax1.tick_params(axis='y', labelcolor = 'black')
ax1.grid(True, alpha = 0.5)
# plt.legend(loc='upper right')
# plt.grid(True, alpha=0.5)

ax2 = ax1.twinx()  # Teilen der X-Achse
ax2.step(stunden_achse, Lastgang_system["Speicher Füllstand"], color='red', 
         alpha=1, label='Speicher (kWh_th)')
ax2.set_ylabel('Speicherinhalt [kWh]', color = 'black', fontsize=20)
ax2.tick_params(axis='y', labelcolor= 'black')

#Begrenzungslinine für max. Kapazitaet
ax2.axhline(y=Speicher_kapa, color='black', linestyle='--', linewidth=1, 
            label='Max. Kapazität')


# 1. Aktuelle Grenzen holen (nachdem geplottet wurde)
y1_min, y1_max = ax1.get_ylim()
y2_min, y2_max = ax2.get_ylim()

# 2. Sicherstellen, dass 0 enthalten ist (falls Daten rein positiv/negativ sind)
y1_min = min(y1_min, 0); y1_max = max(y1_max, 0)
y2_min = min(y2_min, 0); y2_max = max(y2_max, 0)

# 3. Verhältnisse berechnen (Wie viel "Platz" braucht die negative Seite 
#relativ zur positiven?)
# Wenn max=0 (rein negativ), setzen wir ratio auf unendlich groß für die Logik
ratio1 = abs(y1_min) / y1_max if y1_max != 0 else 1e9
ratio2 = abs(y2_min) / y2_max if y2_max != 0 else 1e9

# 4. Das größere Verhältnis gewinnt (bestimmt die Nulllinien-Position)
target_ratio = max(ratio1, ratio2)

# 5. Grenzen anpassen
# Wir erweitern jeweils die Seite, die "zu kurz" ist, 
#um das Verhältnis zu matchen.
# Neue Min-Grenze = - (Ziel-Verhältnis * Max-Grenze)

if ratio1 < target_ratio and y1_max != 0:
    ax1.set_ylim(bottom = -target_ratio * y1_max)
elif ratio2 < target_ratio and y2_max != 0:
    ax2.set_ylim(bottom = -target_ratio * y2_max)
#Legende für beide Achsen

lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax2.get_legend_handles_labels()
ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='lower right', 
           facecolor = 'white', labelcolor='black', framealpha=1, 
           fontsize=20, edgecolor = 'black' )


# X-Achse mit Monatsnamen
monats_ticks = np.arange(0, 35136, 2930)
monats_namen = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul',
                'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
if len(monats_ticks) > 12: monats_ticks = monats_ticks[:12]
plt.xticks(monats_ticks, monats_namen, fontsize=20)

###############################################################################


# plot des Strommarktpreises 2024 
plt.figure(figsize=(15, 4))
plt.plot(el_market)

#plt.title("Strommarktpreise")
plt.xlabel("Viertelstunden", fontsize= 12)
plt.ylabel("€/MWh", fontsize= 12)
plt.legend(loc='upper right')
plt.grid(True, alpha=0.5)
# X-Achse mit Monatsnamen
monats_ticks = np.arange(0, 35160, 2930)
monats_namen = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep',
                'Okt', 'Nov', 'Dez']
if len(monats_ticks) > 12: monats_ticks = monats_ticks[:12]
plt.xticks(monats_ticks, monats_namen)

##############################################################################
#Plot des Lastgangs des Waermenetzes

plt.figure(figsize=(15, 8))
plt.plot(LG_Netz)

# plt.title("Lastgang Waermenetz")
plt.xlabel("Tage des Jahres 2024", fontsize= 12)
plt.ylabel("kWh/d", fontsize= 12)
plt.legend(loc='upper right')
plt.grid(True, alpha=0.5)



###############################################################################
###############################################################################
###############################################################################

