# Browser validation record

Validation date: 2026-09-06. This record distinguishes scientific runtime validation from browser interaction testing.

## Shared scientific source

The browser's engine.py and service.py are byte-identical to the supplied desktop scientific modules. The JSON bridge validates input types, canonicalizes completed numeric edits, adapts local files through a temporary in-memory filesystem, and adds exact CDF plotting points at discrete age masses. It does not replace the scientific equations or optimizer.

## Completed checks

| Check | Result |
| --- | --- |
| Original Python scientific suite in WebAssembly | 147 tests and 141 subtests passed |
| Native-versus-WebAssembly reference cases | 24 passed |
| JSON boundary, imports, exports and plotting checks | 33 passed |
| Static HTTP Worker at a nested /tracerlpm/ path | Loaded 133 histories, evaluated and fitted the demonstration |
| Same-origin asset requests in HTTP Worker emulation | All 16 requests local to the site; no CDN requests |

The WebAssembly suite includes analytical distribution/decay checks, conservation and mass balance, tracer-specific mixing rules, original workbook tolerances, fitting, nondetects and file workflows. A SciPy quantile warning occurred in an extreme-shape inverse-Gaussian test; the test passed.

The 24 reference cases cover every supported model and all 14 tracer codes, bounded/unbounded full PEM, binary carbon-mass and tritium-inventory mixing, original examples, forecasts, atomic calendar thresholds, fitted modern/old ages, censored fits and model comparison.

Additional boundary checks cover blank and incomplete numbers, decimal/exponent editing, nonnumeric JSON booleans, malformed project text/structure, invalid dates and uncertainties, CSV quoting, leap dates, project roundtrip with embedded histories, report escaping and attribution, path confinement, and exact custom-age CDF jumps.

## Measured numerical differences

Maximum absolute differences below are across the reference cases. Tracer differences use the corresponding tracer's concentration units; age differences are years.

| Quantity | Maximum absolute difference |
| --- | --- |
| Forward tracer predictions | 1.82e-12 |
| Fitted tracer predictions | 1.65e-11 |
| Forecast absolute concentrations | 4.55e-12 |
| Fitted age statistics | 2.95e-12 |

The detailed machine-readable numeric-deviations.json contains every measured category and its worst-case input/output location. The typical differences are near floating-point precision. Universal bit-for-bit equality is not claimed.

The parity harness accepts forward values with 2e-9 relative plus 1e-15 absolute tolerance; fitted values use 2e-5 relative plus 1e-13 absolute tolerance. Near-zero residual/objective comparisons use a 1e-10 absolute tolerance. Equivalent/flat model shapes and insignificant tie ordering are not used as a false test of physical uniqueness.

## Runtime and test environment

Pinned browser runtime: Pyodide 314.0.6, CPython 3.14.2, NumPy 2.4.6, SciPy 1.18.0. The Windows reference uses Python 3.13, NumPy 2.4.2 and SciPy 1.17.0. The WebAssembly tests ran under Node 22.20.0 on Windows; the HTTP Worker harness emulated browser globals and loaded the unmodified Worker from static HTTP paths.

## Remaining validation limits

The HTTP Worker check is not a real-browser interaction test. A complete Chrome/Edge/Firefox/Safari and operating-system interaction matrix, screen-reader audit, mobile performance certification, and independent scientific review were not performed.

Before public scientific release, exercise the visible workflow in target browsers and obtain independent groundwater-tracer review. Automated agreement with the desktop implementation does not establish that a site satisfies a stationary lumped-parameter model or that its tracer corrections/input histories are valid. The original desktop is itself an independent implementation; its stated differences from the legacy workbook remain applicable.

## Evidence and reproduction

- browser-bridge-results.json: exact tested source hashes, individual reference cases and input/output checks.
- numeric-deviations.json: measured native/browser differences.
- runtime-manifest.json: pinned runtime sources and SHA-256 hashes.
- ../python/manifest.json: scientific source/data integrity hashes used at startup.
- The source distribution contains the original Python tests and reproducible bridge harness under tests/.
