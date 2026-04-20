# Source Rate-Limit Notes

This app harvests metadata only, but each scholarly source still applies its own API limits. The app uses conservative per-request delays, retries `429 Too Many Requests` responses, and surfaces source-specific notes in the dashboard.

Do not commit API keys. Put keys in `.env` or the local **Setup status** panel only.

| Source | Verified / Operational Behavior | App Behavior |
|---|---|---|
| PubMed / MEDLINE | NCBI E-utilities allows 3 requests/second without an API key and up to 10 requests/second with `NCBI_API_KEY`. | Uses a conservative 0.34 second delay because each PubMed search may make both `esearch` and `efetch` calls. |
| Europe PMC | Europe PMC REST documentation does not publish one simple fixed metadata-search quota. | Uses a moderate 0.25 second delay and generic `429` retry/backoff. |
| OpenAlex | OpenAlex documents 10 requests/second and 100,000 requests/day for authenticated API use. | Uses a 0.11 second delay and sends `OPENALEX_API_KEY` when configured, plus `mailto` when `CONTACT_EMAIL` is set. |
| Crossref | Crossref rate limits are dynamic and communicated through response headers such as `X-Rate-Limit-Limit` and `X-Rate-Limit-Interval`; polite clients should include contact information. | Uses a 0.2 second delay and sends a contact `User-Agent` when `CONTACT_EMAIL` is configured. |
| Semantic Scholar | Most Graph API metadata endpoints are public/free, but public unauthenticated access is rate-limited. API keys improve throughput and predictability. | Works without a key, sends `x-api-key` only if configured, and retries `429` before showing a friendly message. |
| DOAJ | DOAJ public API quotas are modest. | Uses a conservative 0.55 second delay and generic `429` retry/backoff. |
| CORE | CORE requires an API key. Limits are account/key-specific. | Skips CORE until `CORE_API_KEY` is configured; uses a conservative 1 second delay. |
| Scopus | Elsevier/Scopus requires API credentials and entitlement. Quotas and throttles are key/product-specific in the developer portal. | Skips Scopus until `ELSEVIER_API_KEY` is configured; uses a conservative 0.5 second delay. |
| Web of Science | Clarivate limits depend on the specific Web of Science API product and entitlement. | Direct API is placeholder/import-first; no automated calls unless a concrete connector is added. |
| IEEE Xplore | IEEE Xplore limits are displayed per key in the developer portal and may include per-second and daily quotas. | Skips IEEE until `IEEE_API_KEY` is configured; uses a 0.11 second delay. Check the IEEE portal before high-volume runs. |
| ACM Digital Library | ACM is manual/export-only in this app. | No automated calls. |
| arXiv | arXiv asks clients to make no more than one request every three seconds. | Uses a 3.1 second delay. |
| medRxiv / bioRxiv | Public endpoint docs do not publish one simple global metadata quota. | Uses a conservative 1 second delay and generic `429` retry/backoff. |

## Primary References

- NCBI E-utilities API key and request limits: https://eutilities.github.io/site/API_Key/
- NCBI usage guidelines: https://eutilities.github.io/site/API_Key/usageandkey/
- OpenAlex rate limits and authentication: https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication
- OpenAlex authentication: https://developers.openalex.org/api-reference/authentication
- Crossref REST API rate limits: https://github.com/CrossRef/rest-api-doc/blob/master/rest_api.md#rate-limits
- Semantic Scholar Graph API docs: https://api.semanticscholar.org/api-docs/graph
- Europe PMC REST service: https://europepmc.org/RestfulWebService
- Elsevier developer API key settings: https://dev.elsevier.com/api_key_settings.html
- arXiv API user manual: https://info.arxiv.org/help/api/user-manual.html
