# 0003: Spreadsheets are handled by one pure-Python processor

**Status:** accepted (2026-10-08); amended by [0005](0005-scale-out-files-and-cache-resilience.md)

**Context.** Three processors (Excel COM, LibreOffice subprocess, Python) were selected by
OS. The LibreOffice path exported only the first sheet and wrote it back (silent data loss),
built temp file names from user-supplied sheet names (arbitrary file write), and behaved
differently per platform.

**Decision.** One implementation: openpyxl (xlsx), csv, odfpy via pandas (ods), run in a
worker thread, validating sheet names, capping size and defusing formula injection. Edits
create a new file version.

**Alternatives considered.** Keep LibreOffice for fidelity (needs an office suite in the
image, slow subprocesses, the data-loss bug is structural); xlsx-only (ods/csv were already
supported).

**Consequences.** xlsx edits are made in place (formulas and styles of untouched cells survive; charts/images do
not); ods/csv edits rebuild from values. The previous version is always kept. Legacy `.xls` is no longer processed (still storable).

**Amendment (0005).** xlsx edits now patch the zip package instead of rebuilding it, so charts
and images survive too.
