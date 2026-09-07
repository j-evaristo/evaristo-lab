# Scientific sources and third-party components

This is an independent implementation inspired by USGS TracerLPM, not an official USGS release. Scientific methods and the legacy input histories derive from USGS TracerLPM 1.1 and USGS Techniques and Methods 4–F3 by Jurgens, Böhlke and Eberts. Source/history provenance is preserved with the data.

- [USGS TracerLPM](https://www.usgs.gov/software/tracerlpm)
- [Scientific manual](https://pubs.usgs.gov/tm/4-f3/)

The browser runtime is self-hosted, unmodified Pyodide 314.0.6, CPython 3.14.2, NumPy 2.4.6 and SciPy 1.18.0. Upstream wheel hashes were verified against the pinned Pyodide lockfile. All seven runtime files are listed in runtime-manifest.json.

- Pyodide — Mozilla Public License 2.0, with included dependencies' own licenses.
- Python — Python Software Foundation license and bundled notices.
- NumPy — BSD-3-Clause and included numerical-library notices.
- SciPy — BSD-3-Clause and included numerical-library notices.
- React and React DOM — MIT.
- Base UI, Recharts and supporting JavaScript dependencies — their included package licenses.
- Lucide icons — ISC license.

License files from the distributed numerical wheels are retained in those wheels and separately extracted under ../licenses/. Python and Pyodide license text is supplied there, along with exact upstream source links. The build records the JavaScript packages actually bundled and copies their available license notices under ../licenses/javascript/.

The application is delivered with its scientific source. No project-wide open-source license has been selected for newly authored application code; the owner should choose one before offering public reuse. Third-party rights and obligations remain governed by their original licenses.

Browser attribution: Jaivime Evaristo, PhD — evaristo@alumni.upenn.edu.
