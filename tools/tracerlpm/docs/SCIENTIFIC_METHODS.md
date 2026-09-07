# Scientific methods and interpretation

This application is an independent reimplementation of the age-distribution and tracer-transport methods described in USGS TracerLPM. It runs without Excel. It is not a USGS product, is not affiliated with USGS, and has not been reviewed or endorsed by USGS.

The governing reference is Jurgens, B.C., Bohlke, J.K., and Eberts, S.M. (2012, revised 2014), *TracerLPM (Version 1): An Excel workbook for interpreting groundwater age distributions from environmental tracer data*, USGS Techniques and Methods 4-F3: [report and citation](https://pubs.usgs.gov/publication/tm4F3), [full manual](https://pubs.usgs.gov/tm/4-f3/pdf/tm4-F3.pdf). The implementation also inspected the user's installed workbook, examples, input histories, and available VBA source.

## What an estimated age means

A groundwater sample can contain water recharged across many different years. A lumped parameter model (LPM) describes the fraction of that sample contributed by each age. Its mean is a summary of the distribution, not the age of every water parcel. A sample with a large mean age can still contain a small, important fraction of recently recharged water.

A fitted distribution is conditional on the model family, tracer input histories, tracer corrections, and other fixed assumptions. Several distributions can fit the same observations. A small residual does not establish a unique distribution, a particular physical flowpath, or the absence of contamination. The most useful result includes the model and parameters, the modeled concentrations and their discrepancies from observations, and the cumulative fractions within relevant age intervals.

The distribution is an **exit or discharge age distribution**. Its mean need not equal the mean age of all groundwater stored in the aquifer.

## Relation to the original workbook

| Original capability | Scientific treatment in this application |
| --- | --- |
| Piston flow (PFM), exponential mixing (EMM), exponential piston flow (EPM), partial exponential (PEM), dispersion (DM) | Original distribution families and original EPM/PEM ratio conventions are retained. |
| Binary mixtures | Any two supported component distributions can be combined; the fraction always belongs to the first component. Carbon-14 and tritium ratios receive their necessary special treatment. |
| User-defined distributions | Age and weight pairs represent discrete water parcels. Nonnegative weights are normalized to sum to one. |
| Tracer input history | Installed histories can be used, and custom histories can be supplied. Linear interpolation and explicit interval-step treatment are distinguished. Boundary treatment is an assumption. |
| Tracer-tracer and time-series calculations | Concentrations are predicted at each sample date using the same transport equations. Comparison to measured concentrations requires appropriate measurement units and input histories. |
| Age-frequency and cumulative plots | Distributions, quantiles and cumulative fractions describe sample composition. A PFM or custom parcel is a probability mass, not a smooth density. |
| Source-loading forecasts | Transport convolves a specified concentration history with the selected age distribution. Nitrate-N can have an explicitly specified first-order loss rate. Predictions depend on the scenario and stationary transport assumptions. |
| Full partial exponential model | An extension implementing the general screened-interval concept in the manual's appendix; this is distinct from the original two-parameter PEM. |
| Gamma model | An additional age-distribution family. It was not among the original five TracerLPM primary models. |
| Excel/VBA interface and XLL calculations | Replaced by a separate interface and Python numerical engine. Excel macros and the installed XLL are not required. Exact agreement with every legacy numerical result is not claimed. |

The [USGS software history](https://www.usgs.gov/software/tracerlpm) identifies version 1.1.0, released January 15, 2020. Its changes included additional tritium records, argon-39, krypton-85 and krypton-81, correction of the southern-hemisphere CFC-11/CFC-12 curves, and extension of worksheet dates to 2030. Extending date rows does not create observations through 2030. The imported records are a legacy dataset; portions were reconstructed, extrapolated, or held constant.

## Transport calculation

Let `a` be saturated-zone age in years, `t` the sampling date in decimal years, `u` unsaturated-zone travel time, `I(t)` the input concentration, and `g(a)` the normalized age density. For a stable tracer:

`C(t) = integral I(t-a-u) g(a) da`, over nonnegative ages.

For ordinary radioactive decay with rate `lambda` through both zones:

`C(t) = integral I(t-a-u) exp[-lambda(a+u)] g(a) da`.

The saturated-zone mean is `tau = integral a g(a) da`. For a common water unsaturated-zone time, total water mean age is `tau + u`. The separate gas lag permits gases moving through unsaturated-zone air to have a different effective delay. That gas lag is not automatically the unsaturated-zone travel time of water.

The engine splits continuous distributions at probability intervals and input-history dates, then uses Gaussian quadrature within each interval. Its quadrature weights are scaled to the corresponding cumulative probability mass. Discrete age distributions are summed exactly at their parcel ages. Numerical distributions extend into the far tail to approximately the `1 - 10^-12` quantile. Very narrow and very broad distributions need special care; conservation and analytical decay checks are included in the tests.

The original XLL used its own time-step, interval lookup, convergence and quadrature conventions. The desktop engine's linear history interpolation is an intentional numerical choice. Choose step interpolation when the listed value represents the whole interval beginning at that date. A sharp input pulse can produce different answers under these two conventions. Records outside their stated period may be held at a boundary, set to zero, or rejected according to the chosen setting. Holding a boundary is an assumption, not a measured historical value.

## Distribution parameters

All means and age thresholds are in years. Ratios and shape parameters are dimensionless.

**PFM:** All water has age `tau`, including the supported zero-age limit. This represents negligible age mixing in the selected pathway. It is compatible with some short-screen or narrowly distributed pathways, but fitting it does not establish well construction or aquifer geometry.

**EMM:** `g(a) = exp(-a/tau)/tau`. The cumulative fraction younger than age `x` is `1-exp(-x/tau)`. The median is `tau ln(2)`. The distribution has an old tail extending indefinitely. It can describe a uniformly recharged homogeneous aquifer collected across its full thickness, with mixing at the well or spring, or a well-mixed reservoir.

**EPM:** The entered ratio `r` is piston-flow volume divided by exponential-flow volume. Define `theta=tau/(1+r)` and `d=tau*r/(1+r)`. Ages follow a shifted exponential:

`g(a)=exp[-(a-d)/theta]/theta` for `a>=d`, and zero below `d`.

Here `d` is minimum saturated-zone age and `theta` the exponential scale. Setting `r=0` produces EMM; a large ratio approaches PFM. The interpretation is exponential flow followed by piston flow within the saturated zone. Use the explicit unsaturated-zone option for that separate process.

**Original PEM:** The entered ratio `r` is unsampled saturated thickness divided by sampled saturated thickness. The original model assumes that the sampled interval extends down to the aquifer base. Set `theta=tau/[1+ln(1+r)]` and `d=theta*ln(1+r)`, then use the same shifted-exponential density above.

For equal means, `EPM ratio = ln(1 + PEM ratio)` produces **exactly the same distribution and tracer predictions**. The models differ in their geometric interpretation. An EPM/PEM tie does not provide two independent pieces of evidence. A screen-derived ratio can be misleading if the well does not sample down to the actual aquifer base.

**Full PEM:** This extension samples a bounded depth interval from the exponential aquifer age-depth relation. Upper and lower ratios are `z/(H-z)`, where `z` is depth below the water table and `H` aquifer thickness. The lower ratio must exceed the upper ratio. A lower ratio of zero is a special setting meaning the screen extends to the aquifer base, giving an unbounded old tail. Full PEM with upper ratio `r` and lower setting zero reduces to original PEM with ratio `r`. The entered mean is still the mean of the sampled interval.

**DM:** The dispersion parameter is `DP=D/(v*x)`, the inverse Peclet number. For positive age:

`g(a) = sqrt[tau/(4*pi*DP*a^3)] exp[-(a-tau)^2/(4*DP*tau*a)]`.

Its variance is `2*DP*tau^2`. Small DP gives a narrow distribution approaching PFM; a larger DP broadens the distribution and moves its peak younger. DP does not uniquely determine field dispersivity without supporting velocity and path-length information. The implemented DP range is `0.00001` to `100`.

**Gamma:** Shape `k` and scale `tau/k` define `g(a)=a^(k-1)exp(-a*k/tau)/[Gamma(k)(tau/k)^k]`. Shape one gives EMM. Its variance is `tau^2/k`. The implemented shape range is `0.05` to `1000`.

**Binary:** Ordinary concentrations, densities and saturated-zone means use `f*component1+(1-f)*component2`. `f` always refers to the first component, which may be the older or younger component. Changing component order requires changing the fraction to `1-f` and swapping component-specific settings.

## Tracer-specific treatment

### Tritium, tritiogenic helium and initial tritium

The tritium half-life is 12.32 years, consistent with the [USGS 2018 precipitation reconstruction](https://www.usgs.gov/publications/tritium-deposition-precipitation-united-states-1953-2012). The same tritium input history produces all four tritium-family outputs. With `lambda=ln(2)/12.32`, a parcel has:

- Remaining tritium: `H=I(t-a-u) exp[-lambda(a+u)]`.
- Retained tritiogenic helium: `He=I(t-a-u) exp(-lambda*u) [1-exp(-lambda*a)]`.
- Initial tritium at saturated-zone entry: `H0=H+He=I(t-a-u) exp(-lambda*u)`.
- Sample ratio: `bulk H / bulk H0`, after integration and mixing.

Helium produced during unsaturated-zone transit is assumed lost to atmospheric exchange. Helium produced after saturation is assumed retained and transported with the water. Measured tritiogenic helium must have atmospheric, excess-air and terrigenic components corrected as appropriate. Raw dissolved helium concentrations cannot be entered as tritium units.

For a binary mixture the program mixes the H and H0 inventories separately and divides their totals. Averaging component H/H0 ratios by water fraction would generally be incorrect. The familiar apparent piston-flow age `ln(1+He/H)/lambda` does not equal the mean age of a general mixture.

H0 and H/H0 calculated from the same measured H/He pair are dependent quantities. They should not be counted as additional independent observations in a weighted statistical fit. A ratio with zero initial-tritium inventory is undefined.

### Carbon-14

Radioactive decay uses a 5730-year half-life. A supplied initial-activity factor scales the input history. A constant 100-pmC initial history is a simplifying alternative, not a full atmospheric radiocarbon calibration. Legacy long-term and bomb histories reflect their original calibration vintage.

The original manual expects sample values in absolute percent modern carbon, pmC, without normalizing groundwater isotope fractionation to delta13C=-25 per mil. Laboratory conventions must be checked. In the manual's conventions, normalized pM can be converted using measured delta13C as:

`pmC = pM * [(1+delta13C/1000)/0.975]^2`.

Ordinary distributions assume equal dissolved inorganic carbon concentration across parcels. For a binary mixture:

`C14 = [f*DIC1*C14_1+(1-f)*DIC2*C14_2] / [f*DIC1+(1-f)*DIC2]`.

DIC values must be positive and use the same concentration unit. This is carbon-mass weighting; it can differ substantially from water-volume weighting. Low radiocarbon activity can reflect old water, reactions with radiocarbon-dead carbon, or mixtures. The application does not replace geochemical inverse modeling.

### Helium-4

Only a suitably corrected radiogenic component is appropriate. At uniform accumulation rate `R`, predicted helium is `R*tau`. Thus helium-4 by itself constrains a mean conditional on its rate, not the distribution shape.

The production-based rate is:

`R = bulk_density/porosity * (1.19e-13*U + 2.88e-14*Th)`.

U and Th are in ppm; dry bulk density is in g/cm3; porosity is a fraction. R is in cm3 STP per gram water per year. Grain density and dry bulk density are not interchangeable. An explicit user accumulation rate can be used instead. In this model the retained radiogenic signal accumulates during saturated-zone residence.

Atmospheric/excess-air helium, external crustal and mantle sources, and non-steady release from minerals complicate the calculation. Freely fitting both accumulation rate and age identifies their product rather than each quantity independently.

### Gas tracers and other radioisotopes

CFCs and SF6 are expressed as equivalent atmospheric mixing ratios in pptv, after appropriate recharge-temperature, elevation and excess-air correction. These are not raw dissolved-gas mass concentrations. The program uses the input-history units; it does not silently perform noble-gas corrections.

The engine uses half-lives of 269 years for argon-39, 10.756 years for krypton-85 and 229,000 years for krypton-81. Argon-39 and krypton-81 can use a constant modern reference of 100; select values in matching modern-reference units. Krypton-85 requires an input history. Histories and measured activities must use compatible conventions.

See the [USGS groundwater dating laboratory background](https://water.usgs.gov/lab/chlorofluorocarbons/background/) and [SF6 guidance](https://water.usgs.gov/lab/sf6/sampling/index.html) for relevant corrections and source processes. Those pages include historical examples; numerical sensitivity statements from earlier atmospheric periods should not be treated as current universal calibration factors.

## Reading plausible interpretations

Interpretation should begin with an actual feature of the result: a cumulative recent fraction, a long tail, comparable alternative fits, a bound reached during fitting, or a particular tracer's discrepancy.

| Calculated pattern | A defensible interpretation and next check |
| --- | --- |
| Mixed distributions fit independent tracers more closely than PFM | Age mixing is more compatible within the tested assumptions. Well construction and hydrogeologic evidence can help distinguish model geometries. |
| Material modeled fraction below a chosen recent-age threshold | The sample includes a pathway potentially responsive to recent recharge loading. This alone establishes neither pollutant concentration nor water safety. |
| Large old tail despite a moderate median | A response to changing source concentrations can persist for a long time. A specified source-loading forecast is needed to quantify the response. |
| Similar residuals for substantially different means or shapes | The observations do not distinguish those tested alternatives well. Additional independent tracers or repeated samples may help. |
| One CFC is lower than modeled | Evaluate degradation, sorption, gas loss, recharge corrections and model inadequacy. A low value alone does not diagnose degradation. |
| CFC or SF6 is higher than modeled | Evaluate local/non-atmospheric input, excess air, recharge corrections and the selected age model. SF6 can have geogenic sources. |
| Low retained tritiogenic helium relative to other constraints | Examine helium correction, gas loss and unsaturated-zone assumptions. Multiple explanations can produce the discrepancy. |
| Modern tracer is undetected | Old water, dilution, tracer loss and detection limits can all matter. A nondetect is an upper limit, not an exact zero concentration. |
| Repeated seasonal residual pattern | Consider whether pumping or recharge changes the age distribution. A stationary LPM is only one hypothesis. |

Do not remove a discordant tracer solely to improve fit. Record any exclusion and its independent analytical or geochemical reason. Tracer behavior and corrections are illustrated in a recent [USGS Mississippi River Valley alluvial aquifer study](https://pubs.usgs.gov/publication/sir20245127/full).

The number of independent observations must be compared with the number of parameters actually fitted. Fixed parameters do not count, while fitted ages, shapes, fractions, delays and scaling factors do. When observations do not outnumber fitted parameters, small residuals provide little evidence of goodness of fit. More observations alone do not guarantee identifiability. Multimodal tracer histories can produce multiple local minima, so optimizer output should be inspected alongside alternative solutions and parameter bounds.

Measurement uncertainties must be positive and use the same units as observations. Weighted residuals are `(predicted-observed)/uncertainty`. User-selected fitting scales are not automatically analytical uncertainties. A relative-error score or a weighted residual sum is not a probability that a model is true. Parameter uncertainty and hypothesis tests require additional statistical assumptions.

## Forecast assumptions

A loading scenario assumes its input concentration represents water entering the contributing recharge area, and the age distribution remains unchanged. Changes in pumping, recharge, source footprint or chemical reactions can invalidate that assumption.

For a conservative tracer initially at steady uniform concentration followed by complete source shutdown, the remaining normalized concentration is `1-F(s)`, where `s` is elapsed time and F the age CDF, with the appropriate water unsaturated-zone delay. Median and other quantiles therefore describe this specific response scenario. They are not unconditional remediation deadlines. For nitrate-N, a specified first-order loss rate applies to the modeled travel time; fitting environmental tracers does not independently establish that reaction rate.

## Numerical checks and limits of validation

The full test suite currently contains **147 passing tests**, comprising 100 engine checks, 40 workflow checks and seven workbook/provenance tests. The workbook tests additionally reported 141 passing subcases. It was run with Python 3.13, NumPy 2.4.2, SciPy 1.17.0 and pytest 9.0.3 on September 6, 2026:

`python -m pytest tests -q -p no:cacheprovider -p no:tmpdir`

The checks include probability normalization and means, analytic radioactive Laplace transforms, independent integration across aquifer depth for full PEM, sharp and step input histories, zero-age PFM, unsaturated-zone isotope conservation, binary ratio and DIC mass balance, custom discrete ages, input validation, and demanding small/large distribution shapes and old mean ages. Ordinary concentration comparisons generally use relative tolerances of `2e-6`; extreme-shape concentration checks use `2e-5`, with small absolute tolerances near zero.

Workflow tests cover synthetic age recovery, distinct solutions from a nonmonotonic input history, censored-likelihood direction, parameter bounds, model comparison, exact calendar boundaries for piston-flow ages, per-date history coverage, CSV validation, saved-project reproduction using embedded histories, HTML escaping, and the conservative source-shutdown scenario. Reported fitted and supplied parameter states are checked separately. The workflow tests use a temporary-directory fixture compatible with this Windows sandbox; the command disables pytest's separate default temporary-directory mechanism.

An extreme DM check at DP=100 and mean age 100,000 years triggers a SciPy warning about an internal inverse-Gaussian tail-quantile calculation. Its probability, mean and concentration checks still pass. This is recorded so the warning is not mistaken for a hidden scientific validation result.

These are numerical verification checks. They do not establish that an age model is appropriate at a field site or guarantee exact parity with every Excel/XLL result. The original example workbooks also contain cached outputs that do not always satisfy the tritium isotope mass balance; inconsistent caches are not treated as correct targets. Source-based example comparisons are documented separately in the example regression tests and provenance notes.

For a reported study result, preserve the observations, correction assumptions, input-history source and coverage, model alternatives, parameter bounds, fitting choices and excluded-data reasons along with the result.
