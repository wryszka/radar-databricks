# Databricks notebook source
# Postcode-district reference data for the radar-databricks demo.
#
# Synthesised from real UK geography but with no licensed source data — every
# district is a real UK postcode district, but population weights, flood scores,
# and lat/long centroids are demo-grade approximations.
#
# Imported via:
#   - `%run ../utils/postcode_reference` from a Databricks notebook
#   - `from postcode_reference import POSTCODE_DISTRICTS` from a local Python
#     script (the header is just a magic comment; the file is valid Python).
#
# Schema:
#   district          str   UK postcode district (e.g. "SW1", "M1", "BS1")
#   region            str   ITL1-ish region label
#   lat / lng         float Demo centroid (~district centre, +/- a few miles)
#   pop_weight        int   Relative weight for policy distribution (1=sparse, 10=dense)
#   flood_base        int   Baseline flood score 0-100 (modified by stochastic noise)
#   watercourse       str   Nearest named river / coast (None for inland-dry)
#   distance_to_water int   Approx distance to nearest meaningful watercourse (m)
#
# Curated to make the demo's punchline land:
#   - Population weighted toward London + major regional cities
#   - Flood scores geographically coherent (Thames Valley, Severn, Trent,
#     Calder/Aire, Fens, South Coast surge zones all elevated)
#   - 2 deliberate "surprise" clusters where pop_weight is high AND flood_base
#     is high — e.g. TW9 (Richmond), YO1 (York). These should be the "huh, I
#     didn't realise we had that much there" moments on the map.

# Each tuple: (district, region, lat, lng, pop_weight, flood_base, watercourse, dist_m)
POSTCODE_DISTRICTS = [
    # ── London (Central — high pop, modest flood thanks to Thames Barrier) ─
    ("EC1", "London", 51.523, -0.103, 10, 12, "Thames",   2400),
    ("EC2", "London", 51.518, -0.087, 10, 10, "Thames",   2200),
    ("EC3", "London", 51.512, -0.080,  9, 18, "Thames",    900),
    ("EC4", "London", 51.514, -0.099,  9, 22, "Thames",    600),
    ("SW1", "London", 51.498, -0.137, 10, 15, "Thames",    700),
    ("SE1", "London", 51.501, -0.090,  9, 24, "Thames",    400),
    ("W1",  "London", 51.515, -0.142, 10,  8, "Thames",   2700),
    ("N1",  "London", 51.539, -0.098,  8,  6, "Regent's Canal", 1500),
    ("E1",  "London", 51.518, -0.062,  8, 14, "Thames",   1700),
    ("E14", "London", 51.504, -0.020,  9, 28, "Thames",    300),  # Canary Wharf
    ("WC1", "London", 51.521, -0.124,  8,  5, None,       3500),
    ("WC2", "London", 51.512, -0.124,  8,  9, "Thames",   1900),
    ("NW1", "London", 51.535, -0.144,  7,  5, "Regent's Canal", 1200),
    ("SE10","London", 51.482, -0.005,  6, 32, "Thames",    250),  # Greenwich
    ("SE15","London", 51.473, -0.071,  6,  7, None,       2800),
    ("W2",  "London", 51.515, -0.187,  7,  6, None,       2900),
    ("W6",  "London", 51.491, -0.224,  6, 11, "Thames",    900),
    ("E8",  "London", 51.546, -0.062,  6,  4, None,       3300),

    # ── London "Surprise" cluster — Thames-adjacent west London ─────────────
    # High property values, dense, AND high flood risk (1947 + 2014 floods).
    # This is the cluster nobody flags until they see the choropleth.
    ("TW9", "London", 51.464, -0.290,  7, 72, "Thames",     150),  # Richmond
    ("TW10","London", 51.453, -0.300,  6, 78, "Thames",      80),  # Ham/Petersham
    ("TW11","London", 51.421, -0.330,  6, 70, "Thames",     180),  # Teddington
    ("KT1", "South East", 51.413, -0.300, 7, 74, "Thames",   120),  # Kingston
    ("KT2", "South East", 51.420, -0.297, 6, 65, "Thames",   220),

    # ── Thames Valley (upstream) — flood-prone ──────────────────────────────
    ("RG1", "South East", 51.456, -0.974, 5, 64, "Thames",    300),  # Reading
    ("RG4", "South East", 51.480, -0.985, 4, 70, "Thames",    180),  # Caversham
    ("OX1", "South East", 51.751, -1.255, 5, 58, "Thames",    400),  # Oxford
    ("OX4", "South East", 51.736, -1.213, 4, 62, "Thames",    300),
    ("SL1", "South East", 51.510, -0.594, 5, 36, None,       2200),  # Slough
    ("SL4", "South East", 51.484, -0.610, 4, 68, "Thames",    200),  # Windsor
    ("GU1", "South East", 51.236, -0.572, 4, 30, "Wey",      1100),  # Guildford
    ("HP1", "South East", 51.749, -0.475, 3, 22, None,       2700),
    ("HP10","South East", 51.621, -0.732, 3, 18, None,       3000),

    # ── South East — coastal + general ──────────────────────────────────────
    ("BN1", "South East", 50.823, -0.142, 5, 42, "English Channel", 800),  # Brighton
    ("PO1", "South East", 50.800, -1.094, 5, 70, "Solent",     150),  # Portsmouth
    ("PO19","South East", 50.836, -0.779, 4, 58, "Chichester Harbour", 400),
    ("PO22","South East", 50.793, -0.667, 3, 64, "English Channel", 250),  # Bognor Regis
    ("SO14","South East", 50.901, -1.404, 5, 60, "Solent",    300),  # Southampton
    ("SO17","South East", 50.928, -1.395, 4, 28, None,       1900),
    ("ME1", "South East", 51.388, 0.518,  3, 48, "Medway",    300),  # Rochester
    ("CT1", "South East", 51.279, 1.080,  3, 22, "Stour",    1200),  # Canterbury
    ("TN1", "South East", 51.132, 0.263,  3, 18, None,       2500),
    ("BH1", "South West", 50.722, -1.876, 4, 52, "English Channel", 400),  # Bournemouth
    ("DT1", "South West", 50.715, -2.443, 2, 38, "Frome",    1000),

    # ── South West ──────────────────────────────────────────────────────────
    ("BS1", "South West", 51.453, -2.597, 6, 38, "Avon",      400),  # Bristol
    ("BS2", "South West", 51.466, -2.575, 5, 26, "Avon",     1300),
    ("BS3", "South West", 51.434, -2.605, 5, 22, None,       1900),
    ("BS5", "South West", 51.467, -2.561, 4, 18, None,       2300),
    ("BS8", "South West", 51.456, -2.620, 5, 14, None,       2700),
    ("BA1", "South West", 51.385, -2.358, 3, 32, "Avon",     1100),  # Bath
    ("EX1", "South West", 50.722, -3.520, 3, 30, "Exe",      1000),  # Exeter
    ("EX4", "South West", 50.727, -3.546, 3, 28, "Exe",      1200),
    ("PL1", "South West", 50.371, -4.143, 3, 46, "Plym",      400),  # Plymouth
    ("PL4", "South West", 50.378, -4.122, 3, 36, "Plym",     1100),
    ("TQ1", "South West", 50.469, -3.526, 2, 50, "English Channel", 350),  # Torquay
    ("TR1", "South West", 50.265, -5.052, 2, 38, "Truro/Fal", 700),

    # ── Severn Valley — flood-prone heavyweight ─────────────────────────────
    ("GL1", "South West", 51.864, -2.245, 3, 78, "Severn",    150),  # Gloucester
    ("GL3", "South West", 51.890, -2.137, 2, 68, "Severn",    700),
    ("WR1", "Midlands",   52.193, -2.222, 3, 74, "Severn",    250),  # Worcester
    ("WR5", "Midlands",   52.171, -2.196, 2, 62, "Severn",    900),
    ("HR1", "Midlands",   52.054, -2.715, 2, 58, "Wye",       400),  # Hereford
    ("SY1", "Midlands",   52.708, -2.755, 3, 80, "Severn",    180),  # Shrewsbury
    ("TF1", "Midlands",   52.683, -2.453, 3, 50, "Severn",   1100),  # Telford
    ("TF2", "Midlands",   52.691, -2.443, 2, 46, "Severn",   1300),

    # ── Midlands — Birmingham + Trent/Derby ─────────────────────────────────
    ("B1",  "Midlands",   52.480, -1.900, 8, 12, None,       2700),  # Birmingham
    ("B2",  "Midlands",   52.481, -1.895, 7, 10, None,       3000),
    ("B3",  "Midlands",   52.487, -1.901, 7,  8, None,       3200),
    ("B4",  "Midlands",   52.486, -1.886, 6, 10, None,       2800),
    ("B5",  "Midlands",   52.473, -1.895, 6, 14, "Rea",      1900),
    ("B15", "Midlands",   52.467, -1.928, 6,  9, None,       3100),
    ("B17", "Midlands",   52.460, -1.971, 5, 18, "Bourn Brook", 1100),
    ("CV1", "Midlands",   52.408, -1.510, 4, 14, "Sherbourne", 1500),
    ("LE1", "Midlands",   52.633, -1.131, 4, 32, "Soar",      400),  # Leicester
    ("NG1", "Midlands",   52.954, -1.155, 4, 56, "Trent",     900),  # Nottingham
    ("NG2", "Midlands",   52.926, -1.140, 4, 70, "Trent",     200),
    ("NG7", "Midlands",   52.951, -1.181, 4, 38, "Trent",    1700),
    ("DE1", "Midlands",   52.921, -1.476, 3, 60, "Derwent",   500),  # Derby
    ("DE22","Midlands",   52.941, -1.510, 3, 52, "Derwent",  1100),

    # ── East of England — Fens + East Anglia ────────────────────────────────
    ("CB1", "East", 52.197, 0.140,  4, 28, "Cam",        700),  # Cambridge
    ("CB4", "East", 52.227, 0.118,  3, 32, "Cam",        500),
    ("PE1", "East", 52.582, -0.246, 3, 62, "Nene",       300),  # Peterborough
    ("PE13","East", 52.664, 0.158,  2, 82, "Nene/Fens",   80),  # Wisbech ← surprise!
    ("PE30","East", 52.751, 0.398,  2, 76, "Great Ouse", 200),  # King's Lynn
    ("NR1", "East", 52.628, 1.299,  3, 46, "Wensum",     400),  # Norwich
    ("NR2", "East", 52.631, 1.276,  3, 38, "Wensum",     900),
    ("IP1", "East", 52.062, 1.155,  3, 42, "Orwell",     500),  # Ipswich
    ("CO1", "East", 51.892, 0.901,  3, 22, "Colne",     1200),  # Colchester
    ("AL1", "East", 51.748, -0.339, 3, 14, "Ver",       1700),  # St Albans

    # ── North West — Manchester + Liverpool ─────────────────────────────────
    ("M1",  "North West", 53.479, -2.241, 8, 28, "Irwell",    600),  # Manchester
    ("M2",  "North West", 53.481, -2.244, 7, 24, "Irwell",    700),
    ("M3",  "North West", 53.485, -2.252, 7, 26, "Irwell",    500),
    ("M4",  "North West", 53.486, -2.227, 6, 18, None,       1700),
    ("M14", "North West", 53.440, -2.226, 5, 14, None,       2300),
    ("M16", "North West", 53.456, -2.272, 5, 22, "Mersey",   1100),
    ("M20", "North West", 53.418, -2.234, 5, 30, "Mersey",    700),
    ("L1",  "North West", 53.402, -2.978, 6, 36, "Mersey",    400),  # Liverpool
    ("L2",  "North West", 53.408, -2.992, 5, 42, "Mersey",    250),
    ("L3",  "North West", 53.412, -2.987, 5, 38, "Mersey",    300),
    ("L8",  "North West", 53.385, -2.969, 4, 24, "Mersey",   1300),
    ("L17", "North West", 53.362, -2.929, 4, 18, None,       1900),
    ("WA1", "North West", 53.387, -2.586, 3, 32, "Mersey",    700),
    ("PR1", "North West", 53.762, -2.703, 3, 36, "Ribble",    600),  # Preston
    ("CH1", "North West", 53.193, -2.892, 3, 22, "Dee",       900),  # Chester
    ("CA1", "North West", 54.892, -2.926, 2, 64, "Eden/Caldew", 200),  # Carlisle (2005, 2015 floods)

    # ── Yorkshire — Calder/Aire surprise + Hull surge ───────────────────────
    ("LS1", "Yorkshire", 53.798, -1.549, 5, 38, "Aire",      400),  # Leeds
    ("LS2", "Yorkshire", 53.806, -1.546, 5, 32, "Aire",      700),
    ("LS3", "Yorkshire", 53.804, -1.567, 4, 36, "Aire",      500),
    ("LS6", "Yorkshire", 53.823, -1.576, 4, 14, None,       2200),
    ("LS11","Yorkshire", 53.781, -1.553, 4, 42, "Aire",      350),
    ("BD1", "Yorkshire", 53.793, -1.755, 4, 22, "Bradford Beck", 800),  # Bradford
    ("HX1", "Yorkshire", 53.722, -1.862, 3, 76, "Calder",    150),  # Halifax (Calder)
    ("HX2", "Yorkshire", 53.731, -1.892, 2, 72, "Calder",    400),
    ("HD1", "Yorkshire", 53.645, -1.785, 3, 56, "Colne",     500),  # Huddersfield
    ("WF1", "Yorkshire", 53.682, -1.498, 3, 48, "Calder",    700),  # Wakefield
    ("S1",  "Yorkshire", 53.382, -1.470, 5, 44, "Don",       400),  # Sheffield
    ("S2",  "Yorkshire", 53.371, -1.464, 4, 28, "Sheaf",     900),
    ("S6",  "Yorkshire", 53.401, -1.518, 4, 36, "Don",       600),
    ("S10", "Yorkshire", 53.382, -1.503, 4, 12, None,       2400),
    ("S11", "Yorkshire", 53.367, -1.495, 4, 10, None,       2700),
    ("HG1", "Yorkshire", 53.998, -1.541, 2, 26, "Nidd",     1100),  # Harrogate
    ("YO1", "Yorkshire", 53.962, -1.080, 3, 88, "Ouse",      120),  # York ← classic flood
    ("HU1", "Yorkshire", 53.745, -0.337, 3, 84, "Humber",    150),  # Hull
    ("HU3", "Yorkshire", 53.739, -0.367, 2, 78, "Humber",    300),
    ("DN1", "Yorkshire", 53.524, -1.137, 3, 58, "Don",       500),  # Doncaster

    # ── North East ──────────────────────────────────────────────────────────
    ("NE1", "North East", 54.972, -1.612, 4, 26, "Tyne",      400),  # Newcastle
    ("NE2", "North East", 54.989, -1.604, 3, 18, None,       1500),
    ("NE3", "North East", 55.012, -1.617, 3, 12, None,       2400),
    ("NE6", "North East", 54.974, -1.564, 3, 22, "Tyne",      700),
    ("SR1", "North East", 54.905, -1.380, 3, 32, "Wear",      400),  # Sunderland
    ("TS1", "North East", 54.575, -1.232, 3, 36, "Tees",      500),  # Middlesbrough
    ("DH1", "North East", 54.776, -1.575, 2, 22, "Wear",      900),

    # ── Wales ───────────────────────────────────────────────────────────────
    ("CF10","Wales", 51.479, -3.179, 4, 32, "Taff",      300),  # Cardiff
    ("CF11","Wales", 51.475, -3.197, 3, 28, "Taff",      700),
    ("CF14","Wales", 51.519, -3.196, 3, 14, None,       2100),
    ("CF24","Wales", 51.485, -3.166, 3, 24, "Taff",     1300),
    ("SA1", "Wales", 51.620, -3.943, 3, 36, "Tawe",      400),  # Swansea
    ("NP10","Wales", 51.554, -3.000, 2, 28, "Usk",      1100),  # Newport
    ("LL30","Wales", 53.328, -3.829, 2, 50, "Irish Sea", 250),  # Llandudno

    # ── Scotland ────────────────────────────────────────────────────────────
    ("EH1", "Scotland", 55.952, -3.190, 5, 14, None,       2400),  # Edinburgh
    ("EH2", "Scotland", 55.953, -3.198, 4, 12, None,       2700),
    ("EH3", "Scotland", 55.957, -3.203, 4, 16, "Water of Leith", 1300),
    ("EH8", "Scotland", 55.948, -3.176, 3, 10, None,       3100),
    ("EH10","Scotland", 55.929, -3.211, 3, 14, "Braid Burn", 1100),
    ("G1",  "Scotland", 55.860, -4.252, 5, 38, "Clyde",     400),  # Glasgow
    ("G2",  "Scotland", 55.863, -4.260, 4, 32, "Clyde",     700),
    ("G3",  "Scotland", 55.865, -4.273, 4, 26, "Clyde",    1100),
    ("G11", "Scotland", 55.875, -4.319, 3, 18, "Kelvin",   1300),
    ("G12", "Scotland", 55.878, -4.296, 3, 14, "Kelvin",   1700),
    ("AB10","Scotland", 57.144, -2.105, 3, 28, "Dee",      1100),  # Aberdeen
    ("DD1", "Scotland", 56.462, -2.971, 3, 22, "Tay",       500),  # Dundee
    ("PA15","Scotland", 55.945, -4.755, 2, 42, "Clyde",     400),  # Greenock
    ("KY11","Scotland", 56.034, -3.470, 2, 30, "Forth",     800),  # Dunfermline

    # ── Northern Ireland ────────────────────────────────────────────────────
    ("BT1", "Northern Ireland", 54.601, -5.928, 3, 30, "Lagan",     300),  # Belfast
    ("BT2", "Northern Ireland", 54.595, -5.930, 3, 26, "Lagan",     500),
    ("BT9", "Northern Ireland", 54.580, -5.946, 3, 16, "Lagan",    1300),
]

# ── Convenience accessors ────────────────────────────────────────────────────

def as_pandas():
    """Return the reference data as a pandas DataFrame."""
    import pandas as pd
    return pd.DataFrame(POSTCODE_DISTRICTS, columns=[
        "district", "region", "lat", "lng", "pop_weight",
        "flood_base", "watercourse", "distance_to_water_m",
    ])


DISTRICTS = [r[0] for r in POSTCODE_DISTRICTS]
DISTRICT_WEIGHTS = [r[4] for r in POSTCODE_DISTRICTS]
DISTRICT_REGION = {r[0]: r[1] for r in POSTCODE_DISTRICTS}
DISTRICT_LATLNG = {r[0]: (r[2], r[3]) for r in POSTCODE_DISTRICTS}


# ── Named flood scenarios for Stage 4 ─────────────────────────────────────
# Each scenario names the affected districts and a severity multiplier
# applied to expected_loss when the scenario triggers.
FLOOD_SCENARIOS = {
    "Thames Valley 1-in-100": {
        "districts": ["TW9", "TW10", "TW11", "KT1", "KT2",
                      "RG1", "RG4", "OX1", "OX4", "SL4"],
        "severity_multiplier": 6.5,
        "narrative": "Sustained rainfall over the Chiltern catchment + spring tides "
                     "overwhelms upstream defences. 1-in-100 year return period.",
    },
    "Severn Winter Floods": {
        "districts": ["GL1", "GL3", "WR1", "WR5", "HR1",
                      "SY1", "TF1", "TF2"],
        "severity_multiplier": 5.5,
        "narrative": "Atlantic frontal systems stall over the Welsh uplands. "
                     "Severn breaches at Shrewsbury, Worcester, Tewkesbury.",
    },
    "East Coast Surge": {
        "districts": ["HU1", "HU3", "PE13", "PE30", "NR1", "NR2", "IP1"],
        "severity_multiplier": 7.0,
        "narrative": "North Sea storm surge coincides with high spring tide. "
                     "Comparable to the 2013 December tidal surge.",
    },
    "Yorkshire Calder/Aire": {
        "districts": ["HX1", "HX2", "HD1", "WF1", "LS1", "LS2", "LS11", "BD1"],
        "severity_multiplier": 5.0,
        "narrative": "Boxing Day-style precipitation over the Pennines. Calder "
                     "and Aire breach at Halifax, Mytholmroyd, central Leeds.",
    },
    "South Coast Storm": {
        "districts": ["PO1", "PO19", "PO22", "SO14", "BH1", "BN1", "TQ1"],
        "severity_multiplier": 4.5,
        "narrative": "Sustained south-westerly storm + high tide. Coastal "
                     "overtopping from Torquay through to Brighton.",
    },
}
