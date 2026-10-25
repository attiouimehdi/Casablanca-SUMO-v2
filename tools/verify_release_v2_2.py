"""Recompute every number quoted in the Casablanca-SUMO v2.2 data descriptor.

Usage: python verify_release_v2_2.py <release_dir>
  <release_dir> = unzipped Casablanca-SUMO-v2.2 (or a clone of the GitHub tag v2.2)
Prints a plain-text report; nothing is written.
"""
import gzip, hashlib, os, subprocess, sys, tempfile, collections
import xml.etree.ElementTree as ET
import pandas as pd

R = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(R, *a)


def sha256(path, gz=False):
    h = hashlib.sha256()
    with (gzip.open(path, 'rb') if gz else open(path, 'rb')) as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


print('== 1. Checksums')
bad = 0
for line in open(P('CHECKSUMS.sha256')):
    digest, name = line.split()
    ok = sha256(P(name)) == digest
    bad += not ok
    if not ok:
        print('  MISMATCH', name)
print(f'  {bad} mismatches')
print('  network (uncompressed) sha256:', sha256(P('network', 'casablanca_real.net.xml.gz'), gz=True))

print('== 2. Network')
edges = inner = lanes = 0; lane_len = edge_len = 0.0
junc = collections.Counter(); tls = set(); speeds = collections.Counter(); types = collections.Counter()
for _, el in ET.iterparse(gzip.open(P('network', 'casablanca_real.net.xml.gz')), events=('end',)):
    if el.tag == 'edge':
        if el.get('function') == 'internal':
            inner += 1
        else:
            edges += 1; types[el.get('type')] += 1
            ls = el.findall('lane'); lanes += len(ls)
            lane_len += sum(float(l.get('length')) for l in ls)
            edge_len += float(ls[0].get('length')) if ls else 0
            for l in ls:
                speeds[round(float(l.get('speed')) * 3.6)] += 1
        el.clear()
    elif el.tag == 'junction':
        junc[el.get('type')] += 1; el.clear()
    elif el.tag == 'tlLogic':
        tls.add(el.get('id')); el.clear()
    elif el.tag == 'location':
        print('  location', el.attrib)
nj = sum(junc.values())
print(f'  edges {edges} (+{inner} internal) | lanes {lanes} | lane-km {lane_len/1000:.1f} | edge-km {edge_len/1000:.1f}')
print(f'  junction elements {nj}: {dict(junc)} -> non-internal {nj - junc["internal"]}')
print(f'  TLS {len(tls)} | top lane speeds km/h {speeds.most_common(4)} | road types {dict(types)}')

print('== 3. Routes')
for f in sorted(os.listdir(P('routes'))):
    n = sum(1 for _, e in ET.iterparse(P('routes', f)) if e.tag == 'vehicle')
    print(f'  {f}: {n} vehicles')

print('== 4. Annual table')
df = pd.read_csv(P('casablanca_sumo_OSM_365days_v2.2.csv'))
print(f'  shape {df.shape} | NaN {int(df.isna().sum().sum())} | duplicated timestamps {int(df.timestamp.duplicated().sum())}')
print('  class %', (df.congestion_class.value_counts(normalize=True).sort_index() * 100).round(2).tolist(),
      '| counts', df.congestion_class.value_counts().sort_index().tolist())
print('  regime %', (df.scenario_sumo.value_counts(normalize=True) * 100).round(1).to_dict())
sev = df[df.congestion_class == 3]
print('  severe by regime', sev.scenario_sumo.value_counts().to_dict(),
      '| severe hours', sorted(sev.hour.unique().tolist()))
print(f'  severe share inside Ramadan 1444 (is_ramadan=1): {sev.is_ramadan.mean()*100:.1f}% | inside Mar-Apr: {sev.month.isin([3,4]).mean()*100:.1f}%')
print('  ranges: vehicles mean {:.1f} max {:.1f}; speed {:.1f}-{:.1f}; AQI {:.0f}-{:.0f}; T {:.1f}-{:.1f}; BLH {:.0f}-{:.0f}; congestion {:.4f}-{:.4f}'.format(
    df.vehicles_running.mean(), df.vehicles_running.max(), df.mean_speed_kmh.min(), df.mean_speed_kmh.max(),
    df.aqi_composite.min(), df.aqi_composite.max(), df.temperature_c.min(), df.temperature_c.max(),
    df.boundary_layer_m.min(), df.boundary_layer_m.max(), df.congestion_level.min(), df.congestion_level.max()))
c = df[['congestion_level', 'no2_ugm3', 'pm25_ugm3', 'co_mgm3', 'o3_ugm3', 'aqi_composite']].corr().iloc[0].round(3)
print('  corr with congestion', c.to_dict())
wk, we = df[df.is_weekend == 0].vehicles_running.mean(), df[df.is_weekend == 1].vehicles_running.mean()
print(f'  is_weekend: days flagged {sorted(df[df.is_weekend==1].day_of_week.unique().tolist())}; weekday mean {wk:.1f}, weekend mean {we:.1f}, ratio {wk/we:.3f}')
print('  mean vehicles by day_of_week (0=Mon):', df.groupby('day_of_week').vehicles_running.mean().round(1).tolist())
print(f'  is_ramadan days {df[df.is_ramadan==1].date.nunique()} ({df.date[df.is_ramadan==1].min()} -> {df.date[df.is_ramadan==1].max()})')
ift = df[df.scenario_sumo == 'ramadan_iftar']
print(f'  ramadan_iftar rows {len(ift)}, of which outside Ramadan 1444: {(ift.is_ramadan==0).sum()}')
print(f'  Friday-prayer rows {int(df.is_friday_prayer.sum())}, flagged weekend: {int((df.is_friday_prayer & df.is_weekend).sum())}')
print('  diurnal peak (mean vehicles by hour, top 6):', df.groupby('hour').vehicles_running.mean().round(0).sort_values(ascending=False).head(6).to_dict())

print('== 5. Regime means: SUMO summaries x scale factor vs released CSV (rows not modulated by the calendar)')
import importlib.util
_spec = importlib.util.spec_from_file_location('gen', os.path.join(HERE, 'generate_annual_table.py'))
gen = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(gen)
summ = gen.load_summaries(R)
for sc in ('rush_hour', 'normal', 'night'):
    pred = sum(i['vc'] for i in summ[sc]) / len(summ[sc]) * gen.SCALE[sc]
    rel = df[(df.scenario_sumo == sc) & (df.day_of_week != 5)].vehicles_running.mean()
    print(f'  {sc}: predicted {pred:.1f} | released (non-Saturday rows) {rel:.1f} | diff {100*(rel-pred)/pred:+.2f}%')

print('== 6. Bit-exact regeneration from the released summaries')
with tempfile.TemporaryDirectory() as t:
    v21, v22 = os.path.join(t, 'v21.csv'), os.path.join(t, 'v22.csv')
    subprocess.run([sys.executable, os.path.join(HERE, 'generate_annual_table.py'), R, v21], check=True)
    subprocess.run([sys.executable, P('scripts', 'make_v2_2_flags.py'), v21, v22], check=True)
    same = sha256(v22) == sha256(P('casablanca_sumo_OSM_365days_v2.2.csv'))
    print('  regenerated v2.2 identical to released CSV:', same)
