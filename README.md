# Biogas Plant Heat Model & iKWK Simulation

A Python model that estimates the annual **process heat demand of a biogas plant** (incl. a connected district heating network) on a daily basis and simulates a **price-driven innovative CHP system (iKWK)** – CHP unit, heat pump, power-to-heat element and thermal storage – on a 15-minute resolution using day-ahead electricity prices. It also compares the **specific heat generation costs** of several supply options.

> Developed as part of a research/engineering study on flexible heat supply for biogas plants. Reference year: **2024**.

---

## Features

### 1. Heat demand model (daily resolution)
- **Geometry** of up to three digesters (cylinder + spherical-cap roof) → wall, floor and roof areas
- **Substrate heating** – energy to heat the incoming substrate from ambient to process temperature
- **Transmission losses** through wall, roof (vs. ambient air) and floor (vs. ground temperature) using U-values
- **Gas losses** – latent (water vapour saturation, Magnus formula) and sensible heat leaving with the biogas
- **Self heat demand** of the plant relative to the CHP's thermal output (model plausibility check)
- **District heating load profile** from a sigmoid (SigLinDe-type) temperature function scaled to the annual demand
- **Recoverable heat** from the digestate for a given temperature drop

### 2. Heat generator comparison
| Option | Output |
|---|---|
| Raw gas burner | specific heat cost (€/kWh), share of biogas production used |
| Multi-fuel furnace (separated digestate as fuel) | fuel demand (dry/wet), ash quantity, specific heat cost |
| iKWK system | runtimes, starts, energy volumes, market revenues, specific heat cost (with/without iKWK bonus) |

### 3. iKWK simulation (15-min resolution)
Dispatch logic in `ikwk()`, evaluated every quarter hour:

| Unit | Switch-on condition |
|---|---|
| Power-to-heat (heating rod) | price < −`Stromnebenkostenzuschlag` |
| CHP (BHKW) | price ≥ `price_signal_on` |
| Heat pump | 0 ≤ price < `price_signal_WP_on` **and** storage level < `signal_wp_on` |

The thermal storage is balanced against the combined heat load and clipped to `[0, capacity]`. Start counts per unit are tracked.

### 4. Economics
- Market revenues/costs per unit from the day-ahead price
- Gas cost (CHP), grid fees/levies (heat pump, heating rod)
- Annualised CAPEX (simple model: `CAPEX · (1 + i) / depreciation period`)
- Specific heat generation costs per unit and for the whole system, optionally including the iKWK bonus

---

## Requirements

- Python ≥ 3.9
- `pandas`, `numpy`, `matplotlib`

```bash
pip install pandas numpy matplotlib
```

## Input data

Both files must be placed in the working directory (semicolon-separated):

| File | Content | Source |
|---|---|---|
| `mittl._Temp_tag_2024.csv` | Daily mean air temperature 2024 (°C, 2nd column) | [DWD Climate Data Center](https://opendata.dwd.de/climate_environment/CDC/) |
| `energycharts_Stromproduktion_und_Börsenstrompreise_in_Deutschland_2024.csv` | Day-ahead prices 2024 in 15-min resolution (€/MWh, 2nd column, one header row skipped) | [Energy-Charts (Fraunhofer ISE)](https://www.energy-charts.info/) |

The data files are not included in this repository.

## Usage

```bash
python biogas_ikwk_simulation.py
```

*(Rename to match the actual script file name.)*

All parameters are set directly in the script (sections *Konstanten*, *Variablen*, *Modellsteuerung des iKWK Systems*, *Wirtschaftlichkeit*). Key parameters:

| Parameter | Default | Meaning |
|---|---|---|
| `v_dot_bg` | 5000 Nm³/d | Biogas production |
| `m_dot` | 36,876 kg/d | Substrate mass flow |
| `temp_GR` | 40 °C | Process temperature |
| `Q_total_Waermenetz` | 3,200,000 kWh/a | Annual heat demand of the district heating network |
| `P_el_BHKW` | 525 kW | CHP electrical rating |
| `price_signal_on` | 110 €/MWh | CHP switch-on price |
| `P_el_WP`, `COP_WP` | 250 kW, 3 | Heat pump rating and (constant) COP |
| `price_signal_WP_on` | 150 €/MWh | Max. price for heat pump operation |
| `P_el_HS` | 1000 kW | Power-to-heat rating |
| `Speicher_kapa` | 25,000 kWh | Thermal storage capacity |
| `Stromnebenkostenzuschlag` | 100 €/MWh | Flat grid fees, levies and taxes |
| `Zinssatz`, `Abschreibezeitraum` | 4 %, 10 a | Interest rate, depreciation period |

## Outputs

- **Console report**: geometry, heat losses, process heat demand, generator results and specific heat costs
- **`Lastgang_System.csv`**: 15-min time series of CHP, heat pump and heating rod output, storage level and electricity price
- **Plots**:
  1. Annual process heat demand of the plant by component
  2. iKWK dispatch vs. heat demand with storage level (twin axis)
  3. Day-ahead electricity price 2024
  4. District heating load profile

## Code structure

| Function | Purpose |
|---|---|
| `berechne_reaktorflaeche`, `berechne_dachflaeche` | Digester surface areas |
| `berechne_waermeverlust_gas` | Latent + sensible gas losses |
| `Energiebedarf_Fermenter` | Substrate heating demand |
| `loss_convective` | Transmission losses |
| `Lastgang_Waermenetz` | District heating load profile |
| `Waermeauskopplung`, `WP` | Recoverable digestate heat, heat pump sizing |
| `Eigenwaermebedarf` | Self heat demand ratio |
| `Vielstoffofen` | Digestate fuel demand of the furnace |
| `ikwk` | **Current** combined iKWK dispatch + storage simulation |
| `BHKW`, `Heizstab`, `WP_Lastgang`, `Speicher` | Legacy single-unit functions (superseded by `ikwk`, kept for reference) |

## Known limitations & open issues

Model assumptions:
- Constant COP for the heat pump (effectively a seasonal performance factor)
- Storage clipping: surplus heat above capacity is discarded (emergency cooler); unmet demand at an empty storage is **not tracked** (a backup boiler would be required)
- Daily heat demand is distributed evenly over the 96 quarter hours of each day
- No ramp rates, minimum runtimes or part-load efficiencies

Points worth reviewing in the code:
- **Line continuation**: in `LG_bga = ... + loss_conv` followed by `+ loss_gas` on a new line, the second line is a separate statement, so **gas losses are not added**. The same applies to `BHKW_Konto`, `WP_Konto` and `HS_Konto` (gas costs and grid fees are not subtracted). Wrap the expressions in parentheses.
- `berechne_waermeverlust_gas` uses the global `temp_GR` instead of a function argument.
- In `ikwk()`, unit outputs are already converted to kWh per quarter hour (`· 1/4`) and the heat load is passed as kWh per quarter hour (`LG_total / 96`), but the storage balance multiplies by `0.25` again – storage changes appear to be scaled down by a factor of 4.
- 2024 is a leap year (366 days, 35,136 quarter hours), while daily means divide by 365; the final index `35134` is hard-coded.
- The variable `Wartung` is reused with different meanings (€/kWh for the raw gas burner, fraction of CAPEX for the furnace).
- `Q_th_bhkw` is printed as MWh but is in kWh; `ikwk_bonus_kWh` is commented as €/MWh but used as €/kWh.
- The CHP (≥ 110 €/MWh) and heat pump (< 150 €/MWh) price windows overlap, so both may run simultaneously.

## Author

Föcker – January 2026

## License

*Add a license (e.g. MIT) before publishing.*
