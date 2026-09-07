# TracerLPM Browser user guide

## Start a project

Wait for the scientific engine to show Ready. The first visit loads about 31 MB of Python and numerical libraries. All files come from this website; calculations and measurements remain on your device.

The opening data are a synthetic EPM demonstration. Select a USGS example for a worked original dataset, or choose New project and enter your measurements. Original example uncertainty scales are illustrative, not laboratory measurements.

## Observations

Each row contains a sample identifier, calendar sampling date, tracer, observed value or reporting limit, positive 1σ uncertainty, recharge history and inclusion flag. Enter years without commas: 2015 or 2015.5. ISO dates such as 2015-07-01 are also accepted. Scientific notation is supported for small values, for example 1.5e-11.

All included rows share one stationary age distribution, even when sample IDs or sampling dates differ. Use separate projects for unrelated wells.

For a nondetect, select Below limit (<), enter its reporting limit as Value, and provide a positive measurement-error scale. These rows use censored Gaussian likelihood and are not treated as exact zeros.

CFC and SF6 require corrected equivalent atmospheric pptv. Do not enter raw dissolved gas concentrations. Tritiogenic helium is entered as corrected TU. Carbon and helium corrections require independent scientific judgment.

Import observations replaces the table. Import history adds a selectable history. Import discrete ages loads a common age/weight distribution and selects CUSTOM for component 1. Files are read locally and are not uploaded.

## Models and fitting

Choose PFM, EMM, EPM, PEM, DM, full PEM, Gamma or CUSTOM. Binary mixing combines two supported distributions; the fraction always belongs to component 1, which may be older or younger.

Evaluate calculates tracer predictions at the supplied settings. Fit estimates component 1 mean age, plus its shape, the second mean, and mixing fraction when their controls are selected. Component 2 shape and full-PEM screen ratios remain fixed. CUSTOM ages and weights are fixed and cannot be fitted.

Set age and shape bounds deliberately. A solution near a bound may be controlled by that bound. Model comparison fits the five original single-component families. EPM and one-sided PEM are the same shifted-exponential family after reparameterization; ties are not independent geological confirmation.

Water UZ time and gas lag are separate. A0 scales carbon-14 input; it does not perform geochemical correction. DIC concentrations weight carbon-14 in binary mixtures and must use matching concentration units. Nitrate loss is an explicit first-order scenario parameter.

The Cancel control terminates the calculation Worker and retains observations/settings. The next calculation starts a new Worker. Large multi-parameter fits can take longer on modest devices.

## Histories and provenance

Inspect the history curve and source before choosing it. The legacy dataset contains 133 records, including original example histories and reconstructed/projected data. Storage through 2030 does not establish observed coverage through 2030. Legacy gas series include projections after January 2014 and numerous curves plateau at 2020.

Linear interpolation and step interpolation are distinct assumptions. The prehistory and posthistory controls can hold an endpoint, use zero, or require full coverage. Import a representative updated history when the legacy series is inappropriate.

## Results and interpretations

The saturated-zone mean and median exclude water UZ delay. The total mean includes it. The younger-than-10-year fraction includes total water travel time. The pre-1950 fraction uses the displayed reference sample date.

Age percentiles describe the distribution, not confidence intervals for the fitted parameters. CUSTOM/PFM masses appear as jumps in the cumulative plot and in a separate discrete-fraction plot; they are not a smooth density.

Residuals are (modeled − observed)/σ. For a nondetect, this visual residual is not the likelihood contribution. The reported objective identifies the likelihood treatment. A chi-square p-value is deliberately unavailable for some objectives or insufficient residual degrees of freedom.

The conditional age scan holds other fitted parameters fixed. It is not a confidence interval or a fully profiled likelihood. Inspect alternative minima, fit bounds, and tracer-specific discrepancies.

Interpretation notes are rule-based scientific explanations from the shared desktop service. They quantify modeled mixing and response, and suggest plausible alternatives such as history mismatch, recharge correction, contamination, degradation, gas loss or nonstationary flow. They do not diagnose a unique cause or establish water safety.

Editing inputs clears results, ensuring a displayed result never silently belongs to different settings. Save a project or report first when you want to retain a previous scenario.

## Forecast

Forecast uses the evaluated/fitted project snapshot. Set decimal start and end years, then calculate. Tracer curves use the selected histories and are normalized to their first forecast concentration. Absolute values are preserved in the full forecast CSV and JSON.

The uniform conservative source-stop curve is a separate stationary-loading scenario, 100 × [1 − age CDF], shifted by the water UZ delay. It is not a site cleanup-time prediction. Tracers with a zero starting concentration are omitted from normalized curves.

## Save and export

Save project downloads a desktop-compatible JSON file and embeds the selected built-in histories. Keep it alongside the report for reproducibility. Opening a project restores its observations, settings, custom histories and notes.

Results CSV preserves full precision. HTML reports contain interpretations, diagnostic notes, settings and input-history checksums. Complete result JSON also includes plot arrays and fitting information. Each graph exports CSV and SVG; SVG is a vector figure suitable for further scientific formatting.

Work is not saved automatically. Download a project before closing the page. Browser reloads need the website to be reachable. This release does not install an offline service worker.

## Scientific reference and attribution

[USGS TracerLPM manual](https://pubs.usgs.gov/tm/4-f3/). This browser edition is an independent implementation and has not been reviewed or endorsed by USGS.

A fitted age is a model result, not a unique water history.

Jaivime Evaristo, PhD — evaristo@alumni.upenn.edu
