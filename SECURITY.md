# Security policy

exostab is a scientific command-line tool. It reads public data from the NASA Exoplanet Archive and YAML files
you give it, and it writes results to a local folder. It stores no credentials.

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's private vulnerability reporting ("Security" tab, "Report a
vulnerability") or email mehmet@mehmet-oz.com. You should get an answer within a week.

## Supported versions

Only the latest released version receives fixes.

## Notes

- YAML files are read with `yaml.safe_load`, so they cannot run code.
- The archive is queried over HTTPS through astroquery. Cached data live in your user cache folder, or in
  `EXOSTAB_CACHE_DIR` if you set it.
