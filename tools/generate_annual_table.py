"""Regenerate the Casablanca-SUMO annual table from the five SUMO summary outputs.

Port of cell 5 (aggregation) and cell 6 (annual synthesis) of the original
notebook SUMO_Casablanca_OSM_Dataset_v2.ipynb, with the v2.1 empirical-quantile
congestion thresholds (0.095 / 0.22 / 0.365). Output = v2.1 table; apply
make_v2_2_flags.py to obtain v2.2.

Usage: python generate_annual_table.py <release_dir> <out_csv>
"""
import csv, sys, os
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np

INTERVAL = 300
ORDER = ['rush_hour', 'friday_prayer', 'ramadan_iftar', 'night', 'normal']


def load_summaries(release):
    res = {}
    for sc in ORDER:
        steps = ET.parse(os.path.join(release, 'output', f'{sc}_summary.xml')).findall('step')
        bk = defaultdict(lambda: {'r': [], 's': [], 'w': [], 'h': []})
        for s in steps:
            b = (int(float(s.get('time', 0))) // INTERVAL) * INTERVAL
            spd = float(s.get('meanSpeed', -1))
            bk[b]['r'].append(int(s.get('running', 0)))
            if spd >= 0:
                bk[b]['s'].append(spd)
            bk[b]['w'].append(float(s.get('meanWaitingTime', 0)))
            bk[b]['h'].append(int(s.get('halting', 0)))
        res[sc] = [{'vc': sum(d['r']) / max(1, len(d['r'])),
                    'spd': sum(d['s']) / max(1, len(d['s'])) if d['s'] else 0,
                    'wait': sum(d['w']) / max(1, len(d['w'])),
                    'halt': sum(d['h']) / max(1, len(d['h']))}
                   for _, d in sorted(bk.items())]
    return res


SCALE = {'rush_hour': 1.35, 'friday_prayer': 0.28, 'ramadan_iftar': 1.15, 'night': 0.12, 'normal': 0.55}
TEMPS_MIN = [8, 9, 11, 13, 16, 18, 20, 21, 19, 16, 12, 10]
TEMPS_MAX = [18, 19, 21, 22, 25, 27, 28, 29, 27, 24, 21, 18]
HUMID = [78, 75, 72, 68, 65, 62, 60, 62, 65, 70, 74, 77]
RAIN_PROB = [0.25, 0.22, 0.18, 0.12, 0.06, 0.02, 0.01, 0.01, 0.05, 0.12, 0.20, 0.24]
WIND_AVG = [3.2, 3.5, 3.8, 4.2, 4.5, 4.3, 4.0, 3.8, 3.5, 3.2, 3.0, 3.0]
L = 1.2
B_PM25, B_NO2, B_CO, B_O3 = 18.0, 22.0, 0.4, 55.0
THRESH = (0.095, 0.22, 0.365)  # v2.1 (v2 used 0.15 / 0.35 / 0.55)
BP_PM25 = [(0, 12, 0, 50), (12, 35, 50, 100), (35, 55, 100, 150), (55, 150, 150, 200), (150, 250, 200, 300), (250, 500, 300, 500)]
BP_NO2 = [(0, 53, 0, 50), (53, 100, 50, 100), (100, 360, 100, 150), (360, 649, 150, 200), (649, 1249, 200, 300), (1249, 2049, 300, 500)]
BP_O3 = [(0, 54, 0, 50), (54, 70, 50, 100), (70, 85, 100, 150), (85, 105, 150, 200), (105, 200, 200, 300), (200, 504, 300, 500)]


def scenario(h, d, m):
    if d == 4 and 12 <= h <= 14: return 'friday_prayer'
    if m in (3, 4) and (15 <= h <= 17 or 20 <= h <= 22): return 'ramadan_iftar'
    if 7 <= h <= 9 or 17 <= h <= 20: return 'rush_hour'
    if h >= 22 or h <= 5: return 'night'
    return 'normal'


def blh(hour):
    if 0 <= hour <= 5: return 150.0
    if 6 <= hour <= 8: return 150.0 + 200 * (hour - 5)
    if 9 <= hour <= 16: return 750.0 + 650 * np.sin(np.pi * (hour - 9) / 7)
    if 17 <= hour <= 21: return 1200.0 - 240 * (hour - 17)
    return 200.0


def wind_profile(m, h, rng):
    base = WIND_AVG[m - 1]
    diur = 1.2 if 10 <= h <= 18 else (0.7 if h <= 5 or h >= 22 else 1.0)
    return max(0.5, base * diur + rng.normal(0, 0.8))


def sub_aqi(v, bps):
    for c_l, c_h, i_l, i_h in bps:
        if v <= c_h: return i_l + (v - c_l) * (i_h - i_l) / (c_h - c_l)
    return 500.0


def generate(sumo_results):
    rng = np.random.default_rng(42)
    start = datetime(2023, 1, 1); rows = []
    for day in range(365):
        date = start + timedelta(days=day); dow, mo = date.weekday(), date.month
        is_fri = (dow == 4); is_ram = (mo in (3, 4)); is_wkd = dow in (4, 5)
        for hour in range(24):
            sc = scenario(hour, dow, mo); ivs = sumo_results[sc]; scale = SCALE[sc]
            bl_h = blh(hour); wind_ms = wind_profile(mo, hour, rng)
            dispers = np.exp(-wind_ms / 3.0); inv_boost = (1400 / bl_h) ** 0.6
            t_mean = (TEMPS_MIN[mo-1] + TEMPS_MAX[mo-1]) / 2
            amplit = (TEMPS_MAX[mo-1] - TEMPS_MIN[mo-1]) / 2
            temp_base = t_mean + amplit * np.sin(2 * np.pi * (hour - 9) / 24)
            humid_base = HUMID[mo - 1]
            rain_now = float(rng.exponential(2.5)) if rng.random() < RAIN_PROB[mo-1] / 24 else 0.0
            for idx in range(12):
                base = ivs[idx % len(ivs)]
                vc = max(0, base['vc']*scale + rng.normal(0, max(0.5, base['vc']*0.09)))
                spd = max(0.5, base['spd'] + rng.normal(0, 0.6))
                wait = max(0.0, base['wait'] + rng.normal(0, 0.9))
                halt = max(0.0, base['halt']*scale + rng.normal(0, 0.3))
                if is_fri and 12 <= hour <= 14:
                    vc *= rng.uniform(0.28, 0.40); halt *= 0.6
                if is_ram and 15 <= hour <= 17:
                    vc *= rng.uniform(1.25, 1.45); halt *= 1.25; wait *= 1.15
                if is_ram and 20 <= hour <= 22:
                    vc *= rng.uniform(1.15, 1.30); halt *= 1.12
                if is_wkd and not is_fri:
                    vc *= rng.uniform(0.70, 0.85)
                spd_deg = max(0, 1 - (spd * 3.6) / 50)
                halt_rt = halt / (vc + halt + 1)
                wait_nm = min(1.0, wait / 20.0)
                cong = 0.45*spd_deg + 0.35*halt_rt + 0.20*wait_nm + rng.normal(0, 0.03)
                if sc == 'rush_hour': cong = min(1.0, cong * rng.uniform(1.45, 1.95))
                if sc == 'ramadan_iftar': cong = min(1.0, cong * rng.uniform(1.35, 1.75))
                if sc == 'friday_prayer': cong *= rng.uniform(0.30, 0.55)
                if sc == 'night': cong *= rng.uniform(0.15, 0.45)
                cong = round(max(0, min(1, cong)), 4)
                t1, t2, t3 = THRESH
                cls = 0 if cong < t1 else (1 if cong < t2 else (2 if cong < t3 else 3))
                veh_flux = vc * 1000 / 300; em_base = max(0.05, veh_flux * L); sg = 1 + 2.0 * halt_rt
                pm25 = B_PM25 + 0.025*em_base*sg*dispers*inv_boost + rng.normal(0, 2.2)
                no2 = B_NO2 + 0.18*em_base*sg*dispers*inv_boost + rng.normal(0, 3.0)
                co = B_CO + 0.00015*em_base*sg*dispers + rng.normal(0, 0.05)
                sun = max(0, np.sin(np.pi * (hour - 6) / 12)) if 6 <= hour <= 18 else 0
                o3 = B_O3*0.6 + 22*sun + 0.15*no2*sun + rng.normal(0, 3.5)
                if rain_now > 0:
                    wash = np.exp(-rain_now / 3.0); pm25 *= wash; no2 *= wash
                pm25 = round(max(5.0, min(180.0, pm25)), 1)
                no2 = round(max(5.0, min(200.0, no2)), 1)
                co = round(max(0.1, min(8.0, co)), 2)
                o3 = round(max(15.0, min(200.0, o3)), 1)
                aqi = round(max(sub_aqi(pm25, BP_PM25), sub_aqi(no2, BP_NO2), sub_aqi(o3, BP_O3)), 0)
                temp = round(temp_base + rng.normal(0, 1.3), 1)
                humid = round(max(25, min(100, humid_base + rng.normal(0, 4.5))), 1)
                m_ = idx * 5; ts = date.replace(hour=hour, minute=m_)
                rows.append({'timestamp': ts.strftime('%Y-%m-%d %H:%M'), 'date': date.strftime('%Y-%m-%d'),
                    'hour': hour, 'minute': m_, 'day_of_week': dow, 'month': mo,
                    'is_weekend': int(is_wkd), 'is_friday_prayer': int(is_fri and 12 <= hour <= 14),
                    'is_ramadan': int(is_ram), 'scenario_sumo': sc,
                    'vehicles_running': float(round(vc, 1)), 'mean_speed_kmh': round(spd * 3.6, 1),
                    'waiting_time_s': round(wait, 2), 'halting_vehicles': round(halt, 1),
                    'pm25_ugm3': pm25, 'no2_ugm3': no2, 'co_mgm3': co, 'o3_ugm3': o3, 'aqi_composite': aqi,
                    'temperature_c': temp, 'humidity_pct': humid, 'wind_speed_ms': round(wind_ms, 2),
                    'precipitation_mm': round(rain_now, 2), 'boundary_layer_m': round(bl_h, 0),
                    'congestion_level': float(cong), 'congestion_class': cls, 'osm_network': 'real'})
    return rows


if __name__ == '__main__':
    release, out = sys.argv[1], sys.argv[2]
    rows = generate(load_summaries(release))
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f'{len(rows)} rows written to {out}')
