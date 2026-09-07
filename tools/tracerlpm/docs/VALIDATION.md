# Validation record

Verified on Windows 11, Python 3.13.7, NumPy 2.4.2, SciPy 1.17.0, Matplotlib 3.10.8, and PySide6 6.11.2.

## Automated checks

**147 tests passed, plus 141 workbook subtests.**

- **100 engine tests:** independent analytical Laplace transforms, density normalization, moments and CDFs; all supported distribution families; narrow and old distributions; sharp and stepwise histories; tritium–helium conservation; UZ daughter loss; binary ratio-of-totals; DIC-weighted carbon-14; helium accumulation; discrete ages; invalid inputs.
- **40 workflow tests:** fitted synthetic-age recovery; separated age minima; censoring; redundant derived-tracer protection; search bounds; calendar boundaries including discrete atoms; input coverage for each date; model comparison; CSV validation; portable JSON persistence; HTML escaping; source-stop forecasts.
- **7 workbook tests, with 141 subtests:** valid extracted histories and original example calculations, using explicit tolerances for legacy discretization.

Run from the source folder with `python -m pytest tests -q -p no:cacheprovider`.

## Original workbook comparisons

- Example 1 SF6: the independent step-history convolution reproduces the cached result 0.7500000205640422 pptv to floating-point precision.
- Example 1 tritium: checked with a tolerance allowing the original time discretization.
- Example 2 tritium, CFC-113 and carbon-14: checked within 0.5% of legacy cached values; independently integrated references establish the expected numerical differences.
- Example 3: binary mean and saved component/fraction consistency are checked. Absent historical cached predictions are not asserted to match.
- Some cached original tritiogenic-helium/initial-tritium cells violate the required H + He = H0 relationship. These are documented in the data audit and excluded as golden references. The new implementation instead passes isotope conservation tests.

## End-to-end GUI checks

The native interface was launched and visually inspected. The demonstration fit completes and displays four observation predictions, mean age **25.141466 years**, weighted objective **0.171015**, and residual degrees of freedom **3**. GUI smoke checks cover all six pages, threaded fitting, result rendering, a 161-date forecast, and project saving. Tests also check discrete probability-mass display and preserve missing-history identifiers instead of silently replacing them.

The final packaged Windows executable was separately launched and tested through its native Fit observations button. It reproduces the same fitted result and displays the distribution, CDF and residual table. Its bundled Python, Qt and numerical libraries load successfully. The release build uses a clean DLL search path to prevent unrelated installed tools from supplying incompatible runtime libraries. Workspace scrolling was checked at both 1460 × 980 and 1130 × 750 window sizes.

For comparison, fitting the same demonstration gives equivalent EPM and PEM solutions at approximately **25.154205 years**, a DM solution at **24.755637 years**, and substantially larger misfits for PFM and EMM. This verifies that the comparison exposes alternative distributions rather than claiming a unique model.

## Remaining scientific limits

An extreme dispersion case (DP = 100, mean = 100,000 years) triggers a SciPy inverse-Gaussian quantile warning; the associated probability, mean and concentration tests pass. Finite quadrature nodes are validated and probability conservation is checked. This is documented rather than described as complete numerical certification at every possible parameter combination.

Passing these checks does not validate a particular site's conceptual model, tracer corrections, atmospheric history, measurement covariance, or uncertainty estimates. The application is an independent scientific implementation, not an official USGS release or a certified bit-for-bit clone of the Excel XLL. Confidence intervals, covariance-aware inversion, automatic dissolved-gas correction, and geochemical correction of radiocarbon are not implemented.
