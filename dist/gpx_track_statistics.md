# GPX bike-course statistics

All tracks use the same terrain-dependent-power reference-rider model. Values describe the supplied GPX files, not official course certification.

## Model settings

- Total rider and bike mass: 82 kg
- Flat-terrain crank power: 200 W
- Ascent crank power: 240 W (+20%)
- Descent crank power: 150 W (-25%)
- Flat-terrain threshold: ±0.5% grade
- CdA: 0.25 m²
- Rolling-resistance coefficient: 0.004
- Drivetrain efficiency: 97.5%
- Air density: 1.225 kg/m³
- Headwind: 0 m/s
- Maximum simulated speed: 90 km/h
- Elevation resampling: 25 m
- Centered elevation smoothing: 100 m

## Comparison

| Course | Length | Altitude | Gain / loss | 95th-percentile grade up / down | Reference time | Flat time | Average speed | CDF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Austria | 180.12 km | 443–681 m | +1796 / -1796 m | 7.0% / -5.9% | 05:25:04 | 04:54:29 | 33.26 km/h | 1.10385 |
| Barcelona | 175.54 km | 2–77 m | +1496 / -1496 m | 5.5% / -5.4% | 05:08:39 | 04:47:00 | 34.14 km/h | 1.07544 |
| Copenhagen | 176.72 km | -1–74 m | +1167 / -1159 m | 4.2% / -4.0% | 05:01:11 | 04:48:55 | 35.21 km/h | 1.04242 |
| France | 170.79 km | 2–1193 m | +2489 / -2490 m | 7.5% / -7.6% | 05:28:29 | 04:39:14 | 31.22 km/h | 1.17639 |
| Hamburg | 177.05 km | -2–39 m | +596 / -591 m | 2.1% / -2.6% | 04:53:39 | 04:49:28 | 36.18 km/h | 1.01445 |
| Italy | 180.02 km | -6–188 m | +568 / -568 m | 1.6% / -4.3% | 05:03:10 | 04:54:19 | 35.63 km/h | 1.03005 |
| Kalmar | 179.59 km | -1–51 m | +779 / -779 m | 2.6% / -2.7% | 04:58:39 | 04:53:37 | 36.08 km/h | 1.01716 |
| Lanzarote | 180.78 km | 1–574 m | +2325 / -2150 m | 7.0% / -6.4% | 05:39:15 | 04:55:34 | 31.99 km/h | 1.14778 |
| Leeds | 178.20 km | 38–172 m | +2263 / -2263 m | 7.6% / -6.4% | 05:32:34 | 04:51:21 | 32.17 km/h | 1.14149 |
| Portugal | 180.81 km | -0–189 m | +1132 / -1132 m | 4.6% / -4.7% | 05:09:28 | 04:55:37 | 35.06 km/h | 1.04681 |
| Tallinn | 179.30 km | 7–63 m | +621 / -656 m | 2.6% / -3.0% | 04:57:53 | 04:53:09 | 36.12 km/h | 1.01612 |
| Thun | 180.18 km | 517–899 m | +2035 / -2034 m | 5.8% / -7.1% | 05:25:29 | 04:54:35 | 33.23 km/h | 1.10490 |
| Vitoria | 179.98 km | 509–616 m | +1141 / -1161 m | 4.0% / -4.1% | 05:05:55 | 04:54:16 | 35.31 km/h | 1.03959 |
| Wales | 178.33 km | 3–173 m | +2340 / -2341 m | 7.5% / -7.9% | 05:35:01 | 04:51:33 | 31.96 km/h | 1.14907 |

CDF is the simulated reference-rider course time divided by the same rider's time over an equally long flat route. Values above 1 indicate a slower course under the model.

## Detailed track statistics

### Austria

- Source: `austria.gpx` (3,645 track points)
- Horizontal / slope-adjusted length: 180.12 / 180.20 km
- Start / finish / net elevation: 445 / 445 / +0 m
- Minimum / maximum elevation: 443 / 681 m
- Smoothed elevation gain / loss: +1796 / -1796 m
- Uphill / flat / downhill distance: 62.34 / 45.07 / 72.78 km
- 95th-percentile uphill / downhill grade: 7.0% / -5.9%
- Maximum smoothed uphill / downhill grade: 12.1% / -10.7%
- Simulated speed, average / minimum / maximum: 33.26 / 8.37 / 86.40 km/h
- Reference / flat time: 05:25:04 / 04:54:29
- Course difficulty factor: 1.10385

### Barcelona

- Source: `barcelona.gpx` (1,541 track points)
- Horizontal / slope-adjusted length: 175.54 / 175.60 km
- Start / finish / net elevation: 9 / 9 / -0 m
- Minimum / maximum elevation: 2 / 77 m
- Smoothed elevation gain / loss: +1496 / -1496 m
- Uphill / flat / downhill distance: 65.08 / 44.42 / 66.10 km
- 95th-percentile uphill / downhill grade: 5.5% / -5.4%
- Maximum smoothed uphill / downhill grade: 16.0% / -17.9%
- Simulated speed, average / minimum / maximum: 34.14 / 6.44 / 90.00 km/h
- Reference / flat time: 05:08:39 / 04:47:00
- Course difficulty factor: 1.07544
- Data-quality warning: simulated speed reaches the configured 90 km/h cap.

### Copenhagen

- Source: `copenhagen.gpx` (4,110 track points)
- Horizontal / slope-adjusted length: 176.72 / 176.75 km
- Start / finish / net elevation: 0 / 8 / +8 m
- Minimum / maximum elevation: -1 / 74 m
- Smoothed elevation gain / loss: +1167 / -1159 m
- Uphill / flat / downhill distance: 61.56 / 53.17 / 62.01 km
- 95th-percentile uphill / downhill grade: 4.2% / -4.0%
- Maximum smoothed uphill / downhill grade: 11.5% / -12.7%
- Simulated speed, average / minimum / maximum: 35.21 / 8.75 / 90.00 km/h
- Reference / flat time: 05:01:11 / 04:48:55
- Course difficulty factor: 1.04242
- Data-quality warning: simulated speed reaches the configured 90 km/h cap.

### France

- Source: `france.gpx` (4,359 track points)
- Horizontal / slope-adjusted length: 170.79 / 170.92 km
- Start / finish / net elevation: 4 / 3 / -1 m
- Minimum / maximum elevation: 2 / 1193 m
- Smoothed elevation gain / loss: +2489 / -2490 m
- Uphill / flat / downhill distance: 68.91 / 31.92 / 70.08 km
- 95th-percentile uphill / downhill grade: 7.5% / -7.6%
- Maximum smoothed uphill / downhill grade: 20.5% / -14.6%
- Simulated speed, average / minimum / maximum: 31.22 / 5.10 / 90.00 km/h
- Reference / flat time: 05:28:29 / 04:39:14
- Course difficulty factor: 1.17639
- Data-quality warning: simulated speed reaches the configured 90 km/h cap.

### Hamburg

- Source: `hamburg.gpx` (2,385 track points)
- Horizontal / slope-adjusted length: 177.05 / 177.06 km
- Start / finish / net elevation: 6 / 11 / +5 m
- Minimum / maximum elevation: -2 / 39 m
- Smoothed elevation gain / loss: +596 / -591 m
- Uphill / flat / downhill distance: 39.90 / 95.50 / 41.65 km
- 95th-percentile uphill / downhill grade: 2.1% / -2.6%
- Maximum smoothed uphill / downhill grade: 6.7% / -5.8%
- Simulated speed, average / minimum / maximum: 36.18 / 14.25 / 65.96 km/h
- Reference / flat time: 04:53:39 / 04:49:28
- Course difficulty factor: 1.01445

### Italy

- Source: `italy.gpx` (1,255 track points)
- Horizontal / slope-adjusted length: 180.02 / 180.04 km
- Start / finish / net elevation: 1 / 1 / +0 m
- Minimum / maximum elevation: -6 / 188 m
- Smoothed elevation gain / loss: +568 / -568 m
- Uphill / flat / downhill distance: 22.19 / 134.40 / 23.46 km
- 95th-percentile uphill / downhill grade: 1.6% / -4.3%
- Maximum smoothed uphill / downhill grade: 17.0% / -9.9%
- Simulated speed, average / minimum / maximum: 35.63 / 6.10 / 83.64 km/h
- Reference / flat time: 05:03:10 / 04:54:19
- Course difficulty factor: 1.03005

### Kalmar

- Source: `kalmar.gpx` (7,234 track points)
- Horizontal / slope-adjusted length: 179.59 / 179.60 km
- Start / finish / net elevation: 2 / 2 / -0 m
- Minimum / maximum elevation: -1 / 51 m
- Smoothed elevation gain / loss: +779 / -779 m
- Uphill / flat / downhill distance: 52.58 / 73.95 / 53.08 km
- 95th-percentile uphill / downhill grade: 2.6% / -2.7%
- Maximum smoothed uphill / downhill grade: 9.0% / -5.0%
- Simulated speed, average / minimum / maximum: 36.08 / 10.95 / 61.85 km/h
- Reference / flat time: 04:58:39 / 04:53:37
- Course difficulty factor: 1.01716

### Lanzarote

- Source: `lanzarote.gpx` (18,031 track points)
- Horizontal / slope-adjusted length: 180.78 / 180.88 km
- Start / finish / net elevation: 17 / 192 / +175 m
- Minimum / maximum elevation: 1 / 574 m
- Smoothed elevation gain / loss: +2325 / -2150 m
- Uphill / flat / downhill distance: 72.92 / 33.57 / 74.39 km
- 95th-percentile uphill / downhill grade: 7.0% / -6.4%
- Maximum smoothed uphill / downhill grade: 13.9% / -13.0%
- Simulated speed, average / minimum / maximum: 31.99 / 7.34 / 90.00 km/h
- Reference / flat time: 05:39:15 / 04:55:34
- Course difficulty factor: 1.14778
- Data-quality warning: start and finish elevations differ by more than 50 m; the track may not be a closed loop; simulated speed reaches the configured 90 km/h cap.

### Leeds

- Source: `leeds.gpx` (8,783 track points)
- Horizontal / slope-adjusted length: 178.20 / 178.30 km
- Start / finish / net elevation: 102 / 102 / +0 m
- Minimum / maximum elevation: 38 / 172 m
- Smoothed elevation gain / loss: +2263 / -2263 m
- Uphill / flat / downhill distance: 72.68 / 25.50 / 80.12 km
- 95th-percentile uphill / downhill grade: 7.6% / -6.4%
- Maximum smoothed uphill / downhill grade: 18.5% / -13.8%
- Simulated speed, average / minimum / maximum: 32.17 / 5.62 / 90.00 km/h
- Reference / flat time: 05:32:34 / 04:51:21
- Course difficulty factor: 1.14149
- Data-quality warning: simulated speed reaches the configured 90 km/h cap.

### Portugal

- Source: `portugal.gpx` (4,190 track points)
- Horizontal / slope-adjusted length: 180.81 / 180.85 km
- Start / finish / net elevation: 16 / 17 / +1 m
- Minimum / maximum elevation: -0 / 189 m
- Smoothed elevation gain / loss: +1132 / -1132 m
- Uphill / flat / downhill distance: 49.61 / 80.24 / 50.99 km
- 95th-percentile uphill / downhill grade: 4.6% / -4.7%
- Maximum smoothed uphill / downhill grade: 8.9% / -9.3%
- Simulated speed, average / minimum / maximum: 35.06 / 11.14 / 81.20 km/h
- Reference / flat time: 05:09:28 / 04:55:37
- Course difficulty factor: 1.04681

### Tallinn

- Source: `tallinn.gpx` (2,911 track points)
- Horizontal / slope-adjusted length: 179.30 / 179.32 km
- Start / finish / net elevation: 49 / 14 / -35 m
- Minimum / maximum elevation: 7 / 63 m
- Smoothed elevation gain / loss: +621 / -656 m
- Uphill / flat / downhill distance: 36.45 / 103.09 / 39.78 km
- 95th-percentile uphill / downhill grade: 2.6% / -3.0%
- Maximum smoothed uphill / downhill grade: 7.1% / -7.4%
- Simulated speed, average / minimum / maximum: 36.12 / 13.47 / 73.00 km/h
- Reference / flat time: 04:57:53 / 04:53:09
- Course difficulty factor: 1.01612

### Thun

- Source: `thun.gpx` (10,029 track points)
- Horizontal / slope-adjusted length: 180.18 / 180.27 km
- Start / finish / net elevation: 559 / 559 / +0 m
- Minimum / maximum elevation: 517 / 899 m
- Smoothed elevation gain / loss: +2035 / -2034 m
- Uphill / flat / downhill distance: 79.93 / 35.57 / 64.77 km
- 95th-percentile uphill / downhill grade: 5.8% / -7.1%
- Maximum smoothed uphill / downhill grade: 11.7% / -11.8%
- Simulated speed, average / minimum / maximum: 33.23 / 8.66 / 90.00 km/h
- Reference / flat time: 05:25:29 / 04:54:35
- Course difficulty factor: 1.10490
- Data-quality warning: simulated speed reaches the configured 90 km/h cap.

### Vitoria

- Source: `vitoria.gpx` (2,932 track points)
- Horizontal / slope-adjusted length: 179.98 / 180.02 km
- Start / finish / net elevation: 551 / 531 / -20 m
- Minimum / maximum elevation: 509 / 616 m
- Smoothed elevation gain / loss: +1141 / -1161 m
- Uphill / flat / downhill distance: 57.51 / 63.84 / 58.66 km
- 95th-percentile uphill / downhill grade: 4.0% / -4.1%
- Maximum smoothed uphill / downhill grade: 10.1% / -7.2%
- Simulated speed, average / minimum / maximum: 35.31 / 9.86 / 72.35 km/h
- Reference / flat time: 05:05:55 / 04:54:16
- Course difficulty factor: 1.03959

### Wales

- Source: `wales.gpx` (2,462 track points)
- Horizontal / slope-adjusted length: 178.33 / 178.44 km
- Start / finish / net elevation: 23 / 22 / -1 m
- Minimum / maximum elevation: 3 / 173 m
- Smoothed elevation gain / loss: +2340 / -2341 m
- Uphill / flat / downhill distance: 75.82 / 28.37 / 74.25 km
- 95th-percentile uphill / downhill grade: 7.5% / -7.9%
- Maximum smoothed uphill / downhill grade: 15.3% / -17.5%
- Simulated speed, average / minimum / maximum: 31.96 / 6.73 / 90.00 km/h
- Reference / flat time: 05:35:01 / 04:51:33
- Course difficulty factor: 1.14907
- Data-quality warning: simulated speed reaches the configured 90 km/h cap.
