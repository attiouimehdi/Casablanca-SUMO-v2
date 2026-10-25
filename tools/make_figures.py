#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_figures.py -- Figures for the Casablanca-SUMO v2.2 data descriptor.

v2.2 changes (2026-10-25)
  * Day types follow the v2.2 calendar flags: Mon-Thu, Friday, Saturday,
    Sunday, Ramadan 1444 (is_ramadan = 23 Mar - 21 Apr 2023). The v2.1 script
    grouped "Sun-Thu" because it assumed a Friday-Saturday weekend.
  * Saturday and Sunday are plotted separately on purpose: the generator
    reduces demand on Saturdays only, so Sunday traffic looks like a weekday
    even though is_weekend = 1 (documented limitation, see Usage Notes).
  * Heatmap marks both the Ramadan 1444 flag and the March-April span over
    which the ramadan_iftar regime is scheduled.

Generates four figures:
  fig1_network.png       OSM network by road hierarchy + signalised junctions [600 dpi]
  fig2_heatmap.pdf       Day x time-of-day heatmap of the congestion index (365 x 288)
  fig3_diurnal.pdf       Median diurnal profiles by day type, with IQR bands
  fig4_distribution.pdf  Congestion-index histogram with ordinal thresholds and
                         severe-class composition by regime

Usage
-----
    python make_figures.py --csv casablanca_sumo_OSM_365days_v2.2.csv \
                           --net network/casablanca_real.net.xml.gz \
                           --outdir figures

Dependencies: pandas, numpy, matplotlib (no sumolib needed).
"""

from __future__ import annotations

import argparse
import gzip
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.patches import Patch

mpl.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 120,
    "savefig.bbox": "tight",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

THRESHOLDS = (0.095, 0.22, 0.365)
CLASS_NAMES = ["free flow", "light", "moderate", "severe"]

OKABE = {
    "blue": "#0072B2", "orange": "#E69F00", "green": "#009E73", "red": "#D55E00",
    "purple": "#CC79A7", "sky": "#56B4E9", "yellow": "#F0E442", "grey": "#999999",
    "black": "#000000",
}


# ==========================================================================
# Data loading
# ==========================================================================
def _as_bool(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(False, index=df.index)
    s = df[col]
    if s.dtype == bool:
        return s
    if pd.api.types.is_numeric_dtype(s):
        return s.astype(float) > 0.5
    return s.astype(str).str.strip().str.lower().isin({"1", "true", "yes", "y"})


def load_dataset(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower() for c in df.columns]
    for col in ("timestamp", "congestion_level", "vehicles_running", "congestion_class"):
        if col not in df.columns:
            sys.exit(f"ERROR: missing column {col}")
    df["ts"] = pd.to_datetime(df["timestamp"], errors="raise")
    df = df.sort_values("ts").reset_index(drop=True)
    df["day"] = df["ts"].dt.normalize()
    df["doy"] = df["ts"].dt.dayofyear
    df["slot"] = (df["ts"].dt.hour * 60 + df["ts"].dt.minute) // 5
    df["weekday"] = df["ts"].dt.dayofweek          # Monday = 0
    df["ramadan"] = _as_bool(df, "is_ramadan")     # v2.2: Ramadan 1444 AH
    df["day_type"] = np.select(
        [df["ramadan"].to_numpy(),
         (df["weekday"] == 4).to_numpy(),
         (df["weekday"] == 5).to_numpy(),
         (df["weekday"] == 6).to_numpy()],
        ["Ramadan 1444", "Friday", "Saturday", "Sunday"],
        default="Mon-Thu",
    )
    df["cls"] = df["congestion_class"].astype(int)
    return df


# ==========================================================================
# Figure 1 -- network map
# ==========================================================================
HIERARCHY = [
    ("trunk", OKABE["red"], 1.10),
    ("primary", OKABE["orange"], 0.85),
    ("secondary", OKABE["blue"], 0.60),
    ("tertiary", OKABE["green"], 0.42),
    ("residential", OKABE["grey"], 0.22),
]


def parse_network(net_path: Path):
    segments = {name: [] for name, _, _ in HIERARCHY}
    segments["other"] = []
    tls_xy = []
    opener = gzip.open if net_path.suffix == ".gz" else open
    with opener(net_path, "rb") as fh:
        current = None
        for event, elem in ET.iterparse(fh, events=("start", "end")):
            if event == "start" and elem.tag == "edge":
                if elem.get("function") == "internal":
                    current = None
                else:
                    etype = (elem.get("type") or "").lower()
                    current = next((n for n, _, _ in HIERARCHY if n in etype), "other")
            elif event == "end":
                if elem.tag == "lane" and current is not None:
                    shape = elem.get("shape")
                    if shape:
                        pts = [tuple(map(float, p.split(","))) for p in shape.split()]
                        if len(pts) >= 2:
                            segments[current].append(pts)
                    elem.clear()
                elif elem.tag == "edge":
                    current = None
                    elem.clear()
                elif elem.tag == "junction":
                    if elem.get("type") == "traffic_light":
                        tls_xy.append((float(elem.get("x")), float(elem.get("y"))))
                    elem.clear()
    return segments, np.asarray(tls_xy) if tls_xy else np.empty((0, 2))


def fig1_network(net_path: Path, out: Path) -> None:
    segments, tls = parse_network(net_path)
    n_lanes = sum(len(v) for v in segments.values())
    fig, ax = plt.subplots(figsize=(6.6, 6.0))
    ax.add_collection(LineCollection(segments["other"], colors=OKABE["grey"], linewidths=0.15, alpha=0.35))
    for name, colour, lw in reversed(HIERARCHY):
        if segments[name]:
            ax.add_collection(LineCollection(segments[name], colors=colour, linewidths=lw, alpha=0.9))
    if len(tls):
        ax.scatter(tls[:, 0], tls[:, 1], s=3.0, c="black", marker="o", alpha=0.55, linewidths=0, zorder=5)
    handles = [Patch(color=c, label=n.capitalize()) for n, c, _ in HIERARCHY]
    handles.append(plt.Line2D([], [], marker="o", color="black", linestyle="", markersize=3,
                              label=f"Signalised junction (n={len(tls)})"))
    ax.legend(handles=handles, loc="upper right", frameon=False, borderaxespad=0.2, handlelength=1.4)
    ax.autoscale_view(); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    bx, by = x0 + 0.06 * (x1 - x0), y0 + 0.05 * (y1 - y0)
    ax.plot([bx, bx + 2000.0], [by, by], color="black", lw=1.6, solid_capstyle="butt")
    ax.text(bx + 1000.0, by + 0.012 * (y1 - y0), "2 km", ha="center", va="bottom", fontsize=8)
    fig.savefig(out, dpi=600)
    plt.close(fig)
    print(f"  [fig1] {out.name}: {n_lanes:,} lanes, {len(tls):,} signalised junctions")


# ==========================================================================
# Figure 2 -- annual heatmap
# ==========================================================================
def fig2_heatmap(df: pd.DataFrame, out: Path) -> None:
    grid = (df.pivot_table(index="doy", columns="slot", values="congestion_level", aggfunc="mean")
              .reindex(index=range(1, 366), columns=range(288)))
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    im = ax.imshow(grid.to_numpy(), aspect="auto", origin="lower", cmap="magma",
                   interpolation="nearest", extent=(0, 24, 1, 366))
    ax.set_xlabel("Time of day (h)"); ax.set_ylabel("Day of year (2023)")
    ax.set_xticks(range(0, 25, 3))
    months = pd.date_range("2023-01-01", "2023-12-01", freq="MS")
    ax.set_yticks([d.dayofyear for d in months]); ax.set_yticklabels([d.strftime("%b") for d in months])
    r = df.loc[df["ramadan"], "doy"]
    if len(r):
        for v in (r.min(), r.max()):
            ax.axhline(v, color="white", lw=0.8, ls="--", alpha=0.9)
        ax.text(24.3, (r.min() + r.max()) / 2, "is_ramadan", rotation=90, va="center", ha="left", fontsize=7.5)
    ma = df.loc[df["ts"].dt.month.isin([3, 4]), "doy"]
    ax.text(-0.6, (ma.min() + ma.max()) / 2, "iftar regime\n(Mar-Apr)", rotation=90, va="center",
            ha="right", fontsize=6.5, color="0.35")
    cb = fig.colorbar(im, ax=ax, pad=0.075, fraction=0.036)
    cb.set_label("Congestion index"); cb.ax.tick_params(labelsize=7.5)
    fig.savefig(out); plt.close(fig)
    print(f"  [fig2] {out.name}: grid {grid.shape}, Ramadan flag doy {r.min()}-{r.max()}")


# ==========================================================================
# Figure 3 -- diurnal profiles by day type
# ==========================================================================
DAY_TYPE_STYLE = {
    "Mon-Thu": (OKABE["blue"], "-", 1.5),
    "Friday": (OKABE["red"], "-", 1.5),
    "Saturday": (OKABE["green"], "--", 1.3),
    "Sunday": (OKABE["orange"], ":", 1.5),
    "Ramadan 1444": (OKABE["purple"], "-", 1.6),
}


def fig3_diurnal(df: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharex=True)
    for ax, col, label in zip(axes, ["vehicles_running", "congestion_level"],
                              ["Running vehicles", "Congestion index"]):
        for dtype, (colour, ls, lw) in DAY_TYPE_STYLE.items():
            sub = df[df["day_type"] == dtype]
            if sub.empty:
                continue
            g = sub.groupby("slot")[col]
            x = np.asarray(sorted(g.groups.keys())) * 5 / 60.0
            ax.fill_between(x, g.quantile(0.25).to_numpy(), g.quantile(0.75).to_numpy(),
                            color=colour, alpha=0.12, linewidth=0)
            ax.plot(x, g.median().to_numpy(), color=colour, ls=ls, lw=lw, label=dtype)
        for a, b in ((7, 10), (17, 21)):
            ax.axvspan(a, b, color="black", alpha=0.045, linewidth=0)
        ax.set_xlim(0, 24); ax.set_xticks(range(0, 25, 4))
        ax.set_xlabel("Time of day (h)"); ax.set_ylabel(label)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, ncol=5, loc="lower center", bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.06, 1, 1)); fig.savefig(out); plt.close(fig)
    print(f"  [fig3] {out.name}: days per type {df.groupby('day_type')['day'].nunique().to_dict()}")


# ==========================================================================
# Figure 4 -- distribution and severe-class composition
# ==========================================================================
def fig4_distribution(df: pd.DataFrame, out: Path) -> None:
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw={"width_ratios": [2.05, 1]})
    c = df["congestion_level"].to_numpy()
    ax.hist(c, bins=120, color=OKABE["sky"], edgecolor="none", alpha=0.9)
    top = ax.get_ylim()[1]
    for t in THRESHOLDS:
        ax.axvline(t, color=OKABE["red"], lw=1.0, ls="--")
        ax.text(t, top * 0.97, f"{t:g}", rotation=90, fontsize=7, ha="right", va="top", color=OKABE["red"])
    shares = df["cls"].value_counts(normalize=True).sort_index() * 100
    edges = [0.0, *THRESHOLDS, float(np.nanmax(c))]
    for i, share in shares.items():
        mid = (edges[i] + edges[i + 1]) / 2
        ax.text(mid, top * 0.62, f"{CLASS_NAMES[i]}\n{share:.1f}%", ha="center", va="top", fontsize=7.5)
    ax.set_xlabel("Congestion index"); ax.set_ylabel("Observations")
    ax.set_xlim(0, float(np.nanmax(c)) * 1.02)
    severe = df[df["cls"] == 3]
    comp = severe.groupby(["scenario_sumo", "ramadan"]).size().unstack(fill_value=0)
    comp = comp.reindex(columns=[False, True], fill_value=0)
    ypos = np.arange(len(comp))
    ax2.barh(ypos, comp[False].to_numpy(), color=OKABE["orange"], height=0.6, label="outside Ramadan 1444")
    ax2.barh(ypos, comp[True].to_numpy(), left=comp[False].to_numpy(), color=OKABE["purple"], height=0.6,
             label="Ramadan 1444")
    ax2.set_yticks(ypos); ax2.set_yticklabels(comp.index, fontsize=7.5); ax2.invert_yaxis()
    ax2.set_xlabel("Severe-class observations")
    for y, v in zip(ypos, comp.sum(axis=1).to_numpy()):
        ax2.text(v, y, f" {v:,}", va="center", fontsize=7.5)
    ax2.set_xlim(0, comp.sum(axis=1).max() * 1.3)
    ax2.legend(frameon=False, fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, 1.22), ncol=1)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)
    print(f"  [fig4] {out.name}: severe n={len(severe):,}, by regime x Ramadan {comp.to_dict()}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", required=True, type=Path)
    p.add_argument("--net", type=Path, default=None)
    p.add_argument("--outdir", type=Path, default=Path("figures"))
    a = p.parse_args()
    a.outdir.mkdir(parents=True, exist_ok=True)
    df = load_dataset(a.csv)
    print(f"Reading {a.csv}: {len(df):,} rows, {df['day'].nunique()} days")
    if a.net is not None:
        fig1_network(a.net, a.outdir / "fig1_network.png")
    fig2_heatmap(df, a.outdir / "fig2_heatmap.pdf")
    fig3_diurnal(df, a.outdir / "fig3_diurnal.pdf")
    fig4_distribution(df, a.outdir / "fig4_distribution.pdf")
    print("Done.")


if __name__ == "__main__":
    main()
