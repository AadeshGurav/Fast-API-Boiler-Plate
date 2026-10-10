# 0005: Scale-out file handling and cache resilience

**Status:** accepted (2026-10-09)

**Context.** Four things stopped the base from running on several hosts or many workers:
files lived on one disk; listing a user's files loaded every version into memory; xlsx
edits dropped charts and images; and the in-memory cache silently multiplied rate limits
per worker. Uploads and downloads also held whole files in memory (so did the idempotency
middleware), and a Redis outage made every request wait out a 5 s timeout and then fail.

**Decision.**

* *Files stream end to end.* `StorageInterface` gains `save_stream`/`open_stream`/
  `download_url`/`purge_older_than` with buffering defaults, so existing custom backends keep
  working. `FileService.upload_stream` counts, limits and SHA-256-hashes while writing.
* *`S3Storage`* (boto3, multipart, presigned direct downloads behind `file_download_redirect`)
  is the shared backend; `local` stays the zero-setup default for one host.
* *Listing is a database query.* Each version record carries `is_latest` (migration 2
  backfills), backed by a compound index; the page and the total come from MongoDB.
* *xlsx is patched, not rebuilt.* `xlsx_patch`/`xlsx_package` rewrite only edited cells and
  copy every other zip part byte-for-byte; DTDs are refused and unpacked size is bounded.
* *The cache degrades.* Reads are misses, writes are skipped, a cool-down stops repeated
  timeouts; rate limiting fails open, idempotency and chunk sessions answer 503.
* `app_workers > 1` with `memory` cache is a startup error, not a warning.

**Alternatives considered.** Keeping `bytes` APIs and raising memory limits (cost grows with
concurrency x file size); a generic `$group` aggregation for latest-version listing (cannot
use an index for sorting, slower at depth); LibreOffice or openpyxl for xlsx (the former is a
subprocess, the latter cannot represent charts); a full circuit-breaker library (a timestamp
does the job); presigning every download unconditionally (breaks the single audit point and
needs CORS/cookie decisions per deployment, hence opt-in).

**Consequences.** `is_latest` must be maintained by `FilesOps` (only it writes file records).
Streamed idempotent uploads are compared by length, not content. Overwriting the anchor of a
shared/array formula in an xlsx is refused. Storage has no atomic create-if-absent: two simultaneous
uploads of a new version of the same file can both pass the existence check on S3; the unique
`(file_id, version)` index rejects the loser's record, but the loser's cleanup may then delete
the winner's bytes. Rare (needs concurrent writers to one file); fix by serialising versions
per file if it matters.
Not verified against a real AWS/MinIO endpoint, only against moto's S3 emulation.
