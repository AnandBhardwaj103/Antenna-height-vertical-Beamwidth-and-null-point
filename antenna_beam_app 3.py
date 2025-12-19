import streamlit as st
import numpy as np
import plotly.graph_objects as go
import math
import random

# =================================================
# PAGE CONFIG
# =================================================
st.set_page_config(page_title="AP–CPE Vertical Coverage Tool", layout="wide")

st.title("AP–CPE Vertical Coverage Analysis – Practical RF Model")
st.caption(
    "802.11ax (5.9 GHz). Fixed 10° vertical beamwidth. "
    "Environment loss and fade margin included. "
    "Hover on a CPE for detailed DL/UL link budget."
)

# =================================================
# CONSTANTS
# =================================================
VERTICAL_BEAMWIDTH = 10.0
HALF_BW = 5.0

HOUSE_HEIGHT = 6.0
CPE_HEIGHT = 7.0
TREE_MAX_HEIGHT = 5.0

AP_MAST_HEIGHT = 1.0

MAX_DISTANCE = 1500.0
FREQ_MHZ = 5900.0

# Tapered telecom tower
TOWER_BASE_WIDTH = 8.0
TOWER_TOP_WIDTH = 3.0
TOWER_SEGMENTS = 12

# =================================================
# SIDEBAR – DEPLOYMENT
# =================================================
st.sidebar.header("Deployment Parameters")

ap_height = st.sidebar.selectbox("AP Height (m)", [20, 25, 30])
tilt = st.sidebar.slider("Mechanical Down-Tilt (deg)", 0.0, 15.0, 5.0, 0.1)

# =================================================
# SIDEBAR – RF PARAMETERS
# =================================================
st.sidebar.header("AP RF Parameters")

ap_tx = st.sidebar.number_input("AP Tx Power (dBm)", 0.0, 40.0, 23.0, 0.5)
ap_gain = st.sidebar.number_input("AP Antenna Gain (dBi)", 0.0, 35.0, 17.0, 0.5)
ap_loss = st.sidebar.number_input("AP Cable Loss (dB)", 0.0, 10.0, 0.0, 0.1)
ap_eirp = ap_tx + ap_gain - ap_loss

st.sidebar.header("CPE RF Parameters")

cpe_tx = st.sidebar.number_input("CPE Tx Power (dBm)", 0.0, 30.0, 20.0, 0.5)
cpe_gain = st.sidebar.number_input("CPE Antenna Gain (dBi)", 0.0, 30.0, 12.0, 0.5)
cpe_loss = st.sidebar.number_input("CPE Cable Loss (dB)", 0.0, 10.0, 0.0, 0.1)
cpe_eirp = cpe_tx + cpe_gain - cpe_loss

# =================================================
# SIDEBAR – LINK & ENVIRONMENT
# =================================================
st.sidebar.header("Link & Environment Parameters")

bw_mhz = st.sidebar.selectbox("Channel Bandwidth (MHz)", [20, 40, 80, 160])

environment = st.sidebar.selectbox(
    "Propagation Environment",
    ["Rural", "Suburban", "Urban"]
)

fade_margin = st.sidebar.slider(
    "Fade Margin (dB)",
    0, 30, 10, 1
)

tdd_dl = st.sidebar.slider("TDD DL Ratio (%)", 50, 90, 70, 5)
tdd_ul = 100 - tdd_dl

# Environment excess loss (IEEE-style abstraction)
ENV_LOSS = {
    "Rural": 0.0,
    "Suburban": 8.0,
    "Urban": 15.0
}[environment]

# =================================================
# CPE PLACEMENT & NOISE
# =================================================
st.sidebar.header("CPE Placement & Noise")

num_cpes = st.sidebar.slider(
    "Number of CPEs",
    1, 16, 4
)

cpe_horizontal = []
cpe_noise = []

for i in range(num_cpes):
    cpe_horizontal.append(
        st.sidebar.number_input(
            f"CPE {i+1} Horizontal Distance (m)",
            100.0, MAX_DISTANCE,
            250.0 + i * 80,
            10.0
        )
    )
    cpe_noise.append(
        st.sidebar.slider(
            f"CPE {i+1} Noise (dBm)",
            -80, -55, -70, 1
        )
    )

# =================================================
# RF MODELS
# =================================================
def fspl(distance_m):
    d_km = distance_m / 1000.0
    return 32.44 + 20 * np.log10(d_km) + 20 * np.log10(FREQ_MHZ)

def snr_to_mcs(snr):
    if snr < 5: return 0
    if snr < 8: return 1
    if snr < 12: return 3
    if snr < 16: return 5
    if snr < 20: return 7
    if snr < 25: return 9
    return 11

def mcs_to_phy(mcs, bw):
    base = {
        0: 8.6, 1: 17.2, 3: 34.4,
        5: 68.8, 7: 103.2,
        9: 137.6, 11: 143.4
    }
    return base.get(mcs, 0) * (bw / 20)

# =================================================
# GEOMETRY
# =================================================
theta_u = -(tilt - HALF_BW)
theta_l = -(tilt + HALF_BW)

x = np.linspace(1, MAX_DISTANCE, 2000)
y_u = ap_height + x * np.tan(np.deg2rad(theta_u))
y_l = ap_height + x * np.tan(np.deg2rad(theta_l))

# =================================================
# PLOT
# =================================================
fig = go.Figure()

# Ground
fig.add_trace(go.Scatter(x=[0, MAX_DISTANCE], y=[0, 0], line=dict(width=4), name="Ground"))

# Trees (≤ 5 m)
for t in np.linspace(180, MAX_DISTANCE - 180, 7):
    trunk = random.uniform(1.2, 1.8)
    canopy = random.uniform(2.0, TREE_MAX_HEIGHT - trunk)
    fig.add_shape(type="rect", x0=t-0.5, x1=t+0.5, y0=0, y1=trunk,
                  fillcolor="#7B4A12", line=dict(width=0))
    fig.add_shape(type="circle", x0=t-2.0, x1=t+2.0,
                  y0=trunk, y1=trunk+canopy,
                  fillcolor="rgba(34,139,34,0.9)", line=dict(width=0))

# =================================================
# TAPERED ZIG-ZAG TELECOM TOWER
# =================================================
tower_heights = np.linspace(0, ap_height, TOWER_SEGMENTS + 1)

for i in range(TOWER_SEGMENTS):
    y0, y1 = tower_heights[i], tower_heights[i+1]
    w0 = TOWER_BASE_WIDTH - (TOWER_BASE_WIDTH - TOWER_TOP_WIDTH) * (y0 / ap_height)
    w1 = TOWER_BASE_WIDTH - (TOWER_BASE_WIDTH - TOWER_TOP_WIDTH) * (y1 / ap_height)

    fig.add_trace(go.Scatter(
        x=[-w0/2, -w1/2], y=[y0, y1],
        line=dict(width=3, color="gray"), showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=[w0/2, w1/2], y=[y0, y1],
        line=dict(width=3, color="gray"), showlegend=False
    ))

    if i % 2 == 0:
        fig.add_trace(go.Scatter(
            x=[-w0/2, w1/2], y=[y0, y1],
            line=dict(width=1.5, color="gray"), showlegend=False
        ))
    else:
        fig.add_trace(go.Scatter(
            x=[w0/2, -w1/2], y=[y0, y1],
            line=dict(width=1.5, color="gray"), showlegend=False
        ))

# AP mast + panel
fig.add_trace(go.Scatter(
    x=[0,0], y=[ap_height, ap_height + AP_MAST_HEIGHT],
    line=dict(width=4), showlegend=False
))
fig.add_shape(
    type="rect",
    x0=-1.1, x1=1.1,
    y0=ap_height + AP_MAST_HEIGHT - 1.2,
    y1=ap_height + AP_MAST_HEIGHT + 1.2,
    fillcolor="black"
)

# Beam
fig.add_trace(go.Scatter(x=x, y=y_u, line=dict(dash="dash"), name="Upper Beam"))
fig.add_trace(go.Scatter(x=x, y=y_l, name="Lower Beam"))
fig.add_trace(go.Scatter(
    x=np.concatenate([x, x[::-1]]),
    y=np.concatenate([y_u, y_l[::-1]]),
    fill="toself",
    fillcolor="rgba(0,100,255,0.15)",
    line=dict(width=0),
    name="10° Beam"
))

# =================================================
# BUILDINGS + CPEs (up to 16)
# =================================================
for i, d in enumerate(cpe_horizontal):

    fig.add_shape(
        type="rect",
        x0=d-14, x1=d+14,
        y0=0, y1=HOUSE_HEIGHT,
        fillcolor="#E6E6E6", line=dict(width=1)
    )
    fig.add_shape(
        type="rect",
        x0=d-14, x1=d+14,
        y0=HOUSE_HEIGHT-0.4, y1=HOUSE_HEIGHT,
        fillcolor="#B0B0B0", line=dict(width=0)
    )

    fig.add_trace(go.Scatter(
        x=[d,d], y=[HOUSE_HEIGHT, CPE_HEIGHT],
        mode="lines", line=dict(width=3), showlegend=False
    ))

    fig.add_shape(
        type="rect",
        x0=d-1.4, x1=d-0.2,
        y0=CPE_HEIGHT-0.4, y1=CPE_HEIGHT+0.4,
        fillcolor="#2F4F4F"
    )

    d_3d = math.sqrt(d**2 + (ap_height - CPE_HEIGHT)**2)

    total_loss = (
        fspl(d_3d)
        + ENV_LOSS
        + fade_margin
    )

    rssi_dl = ap_eirp + cpe_gain - total_loss
    rssi_ul = cpe_eirp + ap_gain - total_loss

    snr_dl = rssi_dl - cpe_noise[i]
    snr_ul = rssi_ul - cpe_noise[i]

    mcs_dl = snr_to_mcs(snr_dl)
    mcs_ul = snr_to_mcs(snr_ul)

    phy_dl = mcs_to_phy(mcs_dl, bw_mhz)
    phy_ul = mcs_to_phy(mcs_ul, bw_mhz)

    eff_dl = phy_dl * (tdd_dl / 100)
    eff_ul = phy_ul * (tdd_ul / 100)

    fig.add_trace(go.Scatter(
        x=[d], y=[CPE_HEIGHT],
        mode="markers",
        marker=dict(size=6, color="black"),
        hovertemplate=
        f"<b>CPE {i+1}</b><br>"
        f"Distance: {d_3d:.1f} m<br>"
        f"FSPL: {fspl(d_3d):.1f} dB<br>"
        f"Env Loss: {ENV_LOSS:.1f} dB<br>"
        f"Fade Margin: {fade_margin:.1f} dB<br>"
        f"RSSI DL: {rssi_dl:.1f} dBm<br>"
        f"RSSI UL: {rssi_ul:.1f} dBm<br>"
        f"MCS DL: {mcs_dl}<br>"
        f"MCS UL: {mcs_ul}<br>"
        f"DL PHY: {phy_dl:.1f} Mbps<br>"
        f"UL PHY: {phy_ul:.1f} Mbps<br>"
        f"Practical DL: {eff_dl:.1f} Mbps<br>"
        f"Practical UL: {eff_ul:.1f} Mbps"
        "<extra></extra>"
    ))

# =================================================
# LAYOUT
# =================================================
fig.update_layout(
    height=900,
    xaxis_title="Horizontal Distance from AP (m)",
    yaxis_title="Height (m)",
    xaxis=dict(range=[0, MAX_DISTANCE]),
    yaxis=dict(range=[0, ap_height + 12]),
    title="AP–CPE Vertical Coverage (Urban / Suburban / Rural + Fade Margin)"
)

st.plotly_chart(fig, use_container_width=True)
