# Input histories and USGS reference examples

The files in this directory were extracted read-only from the user's installed USGS TracerLPM workbooks. Neither the workbooks nor their macros were executed or modified. Each JSON record includes its original workbook or sheet location and a SHA-256 hash so its provenance can be checked.

## Histories

`histories.json` is a dictionary of 133 input histories. Each record contains `label`, `tracer`, `years`, `values`, `source`, and `note`. Concentrations and decimal years retain the original cached numeric precision. `before_value`, `after_value`, `half_life`, `supported_end_year`, and `stored_end_year` expose boundary assumptions and record limitations.

The installed TracerLPM 1.1 workbook contains 131 modern series on a monthly axis from 1850 through 2030, plus northern and southern IntCal13 paleo-atmospheric 14C series from calendar year −48050 through 1950. For the four modern 14C curves, original IntCal13 points before 1850 are joined to the original modern points from 1850 onward. This introduces no interpolation or rescaling. The two paleo-only series are also preserved separately. A `source_components` field identifies each join.

Common IDs are:

| ID | Tracer and input area |
|---|---|
| stored_E | CFC-12, Northern Hemisphere |
| stored_F | CFC-11, Northern Hemisphere |
| stored_G | CFC-113, Northern Hemisphere |
| stored_I | SF6, Northern Hemisphere |
| stored_O / stored_P / stored_Q | 14C, Northern Hemisphere Zones 1 / 2 / 3 |
| stored_R | 14C, Southern Hemisphere |
| stored_S / stored_T / stored_U | 3H, Ottawa / Vienna / Modesto |
| stored_V / stored_AB | 3H, Albuquerque / Missouri River Basin |
| stored_Y | 85Kr, Freiburg |
| stored_Z / stored_AA | 39Ar / 81Kr, constant 100 percent modern |
| stored_AN through stored_EE | 96 regional tritium histories, original latitude–longitude grid labels |

Most northern-hemisphere gas and tritium histories become constant at 2020 and are extended through 2030 in the workbook. Those extensions are assumptions, not verified contemporary measurements. Some series have much earlier limits. Southern-hemisphere CFC and SF6 curves contain terminal zero placeholders after 2009.9167; these zeros must not be interpreted as contemporary atmospheric concentrations. Their notes identify this explicitly.

`supported_end_year` is inferred from the final numerical change, or from the last point before a terminal gas zero. It is a warning threshold, not an independently verified final observation date. The full original stored values are retained to permit transparent auditing. Select representative histories or import a suitable replacement before fitting recent samples.

The original workbook uses 3H0 under the label “3Ho” and 3H/3H0 under “3H/3Ho”. This package normalizes only these names. Both derived tritium tracers use a 3H input history; they must be calculated from radioactive decay and production, not read from independent input curves. Radiogenic 4He has no atmospheric input history in this table and instead uses an accumulation-rate model.

The stored gas units are equivalent atmospheric mixing ratios in pptv. These are not dissolved-water mass concentrations. The workbook does not supply a solubility/excess-air conversion workflow. Suitable recharge temperature, elevation/pressure, salinity, excess-air and fractionation corrections must precede use of dissolved CFC/SF6 measurements in these fields.

The default before-history boundary is the first original stored concentration. This gives zero for anthropogenic gases, a pre-bomb baseline for 3H, and 100 percent modern for 39Ar and 81Kr. For 14C, this boundary is at the beginning of IntCal13, approximately 50,000 years before 1950. Modeling older recharge requires an explicit additional assumption. Constant modern 39Ar and 81Kr histories are model boundary conditions, rather than measured monthly series.

Tracer half-lives retained from TracerLPM 1.1 are 12.32 yr (3H), 10.76 yr (85Kr), 269 yr (39Ar), 5730 yr (14C), and 229000 yr (81Kr). The source NO3-N history is a site-specific Modesto example with a 0.001 yr⁻¹ first-order reaction rate, represented in the workbook by a 693.1471805599452 yr half-life. It is not a general nitrate dating assumption.

## Reference examples

`usgs_examples.json` contains the three installed USGS example workbooks' sample records, exact model input arrays from the formula-referenced ranges, saved model parameters, and selected cached reference outputs. Their original half-year input arrays differ from the monthly master histories and must be used when evaluating source parity.

1. **Modesto PSW-1:** The latest saved PEM fit has saturated mean age 64.40008417761223 yr, PEM ratio 0.10046829311419031, and zero UZ delay at decimal sample year 2004.6256830601094. Its cached SF6 result is 0.7500000205640422 pptv. An independently evaluated exact integral with piecewise constant half-year inputs gives 0.750000020564048, a difference below 6×10⁻¹⁵. This is a strong concentration parity target. The cached 3H result is 4.606341051895307 TU, versus 4.607083265877147 TU from the exact integral; the small difference is consistent with the original monthly numerical discretization. The cached 3He and 3H0 values fail isotope mass balance and are deliberately excluded from parity targets.
2. **Albuquerque SSW_2007:** The latest saved BMM-DM-DM fit has young saturated mean age 21.302631897591688 yr, young DP 0.010084716213561754, young fraction 0.10834437523267285, old mean 12100 yr, old DP 0.1 and water UZ delay 15 yr; gas UZ delay is zero. The cached concentrations are 2.3479622068032033 TU 3H, 43.80770427438591 pmC 14C and 5.4434420447064324 pptv CFC-113. Independent 24-point Gauss–Legendre quadrature gives 2.340034613447348, 43.818806122758716 and 5.451240263043991 respectively. The differences are 0.338%, 0.0253% and 0.143%, consistent with the older XLL discretization. The tests require agreement within 0.5% of the original cache and within 2×10⁻⁶ concentration units of the independent quadrature.
3. **Missouri River:** The tritium sample time series spans 1963–1997. The latest saved EMM-plus-zero-age-PFM fit has EMM mean 5.990525111831544 yr and EMM fraction 0.6054013209523926, giving mixture mean 3.6266718159012963 yr by direct arithmetic. The currently saved TimeSeriesFits worksheet has missing sample cells and a `#VALUE!` result. No concentration values from that damaged cache are treated as golden references. The intact samples and source histories remain useful for independent time-series fitting.

Saved fits used the source workbook's optimization choices, constraints, and historical curve vintages. They are context-specific examples and not unique age determinations. A new least-squares fit with measurement uncertainties can legitimately differ from the workbook's sum-of-relative-errors optimum.

## Scope of source inspection

The workbook's 18 worksheets cover tracer definitions, input histories, samples, tracer–tracer and time-series output, fit setup, saved ages, user-defined age distributions, age-distribution plots, and forecasting. Its five principal model families are PFM, EMM, EPM, PEM and DM; the model list also includes every ordered binary pair. Embedded VBA source was extracted for inspection. The worksheet formulas invoke compiled `_xll` functions, while similar VBA functions bear `_VB` suffixes. Several apparent defects in those older VBA routines mean they should not be copied as a numerical authority. The scientific equations and independently validated outputs take precedence.

Primary method reference: Jurgens, B.C., Böhlke, J.K., and Eberts, S.M., 2012, *TracerLPM (Version 1): An Excel workbook for interpreting groundwater age distributions from environmental tracer data*, USGS Techniques and Methods 4-F3, https://pubs.usgs.gov/tm/4-f3/ .

The normalized JSON data preserve source material for research use. No claim of USGS endorsement or exact parity across the entire original workbook is implied.
