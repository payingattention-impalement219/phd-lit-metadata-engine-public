import { FormEvent, useEffect, useMemo, useState } from "react";

type SourceName =
  | "pubmed"
  | "europe_pmc"
  | "openalex"
  | "crossref"
  | "semantic_scholar"
  | "doaj"
  | "core"
  | "scopus"
  | "web_of_science"
  | "ieee_xplore"
  | "acm_digital_library"
  | "arxiv"
  | "medrxiv"
  | "biorxiv";

type SourceStatus = {
  name: SourceName;
  available: boolean;
  requires_key: boolean;
  configured: boolean;
  message: string;
  rate_limit_note: string;
  recommended_delay_seconds: number;
  daily_limit_note: string;
};

type ApiSettingStatus = {
  field: string;
  env_name: string;
  label: string;
  required_for: string[];
  help_text: string;
  secret: boolean;
  configured: boolean;
  masked_value: string;
};

type Job = {
  id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  query: string;
  total_records: number;
  deduped_records: number;
  source_counts: Record<string, number>;
  errors: Record<string, string>;
  message: string;
  active_source: string;
  active_query: string;
  completed_steps: number;
  total_steps: number;
  progress_percent: number;
};

type PaperRecord = {
  id: number;
  title: string;
  abstract: string;
  author_keywords: string[];
  indexed_keywords: string[];
  authors: string[];
  year: number | null;
  doi: string;
  pmid: string;
  pmcid: string;
  scopus_eid: string;
  journal: string;
  publication_type: string;
  citation_count: number | null;
  open_access_status: string;
  source_databases: string[];
  source_urls: string[];
  is_preprint: boolean;
  is_peer_reviewed_likely: boolean;
  has_abstract: boolean;
  has_keywords: boolean;
  duplicate_group_id: string;
};

type NotebookStatus = {
  notebook_path: string;
  jupyter_available: boolean;
  vscode_available: boolean;
  message: string;
};

const sourceLabels: Record<SourceName, string> = {
  pubmed: "PubMed / MEDLINE",
  europe_pmc: "Europe PMC",
  openalex: "OpenAlex",
  crossref: "Crossref",
  semantic_scholar: "Semantic Scholar",
  doaj: "DOAJ",
  core: "CORE",
  scopus: "Scopus",
  web_of_science: "Web of Science",
  ieee_xplore: "IEEE Xplore",
  acm_digital_library: "ACM Digital Library",
  arxiv: "arXiv",
  medrxiv: "medRxiv",
  biorxiv: "bioRxiv"
};

const sourceDescriptions: Record<SourceName, string> = {
  pubmed: "Biomedical and MEDLINE metadata",
  europe_pmc: "Biomedical and open-access enrichment",
  openalex: "Broad scholarly metadata and citation signals",
  crossref: "DOI, journal, publisher, and citation metadata",
  semantic_scholar: "Free public scholarly metadata, optional key improves rate limits",
  doaj: "Open-access journal articles",
  core: "Open repository metadata, requires key",
  scopus: "Licensed Elsevier index, requires key",
  web_of_science: "Licensed Clarivate index, import/API optional",
  ieee_xplore: "Engineering and computing metadata, requires key",
  acm_digital_library: "Computer science portal, export/import recommended",
  arxiv: "Public preprint metadata",
  medrxiv: "Medical preprint metadata",
  biorxiv: "Biology preprint metadata"
};

const defaultSources: SourceName[] = ["pubmed", "europe_pmc", "openalex", "crossref", "semantic_scholar", "doaj", "arxiv"];
const openSourcePreset: SourceName[] = ["pubmed", "europe_pmc", "openalex", "crossref", "semantic_scholar", "doaj", "arxiv"];
const restrictedSources = new Set<SourceName>(["scopus", "web_of_science", "ieee_xplore", "acm_digital_library", "core"]);
const importOnlySources = new Set<SourceName>(["web_of_science", "acm_digital_library"]);

const defaultSourceQueries: Record<SourceName, string> = {
  pubmed: `("concept A"[TIAB] OR "concept A synonym"[TIAB] OR "controlled vocabulary term"[MeSH Terms])
AND
("concept B"[TIAB] OR "concept B synonym"[TIAB] OR "method term"[TIAB])`,
  scopus: `TITLE-ABS-KEY(
  ("concept A" OR "concept A synonym" OR "related population term")
  AND
  ("concept B" OR "concept B synonym" OR "related method term")
)`,
  web_of_science: `TS=(
  ("concept A" OR "concept A synonym" OR "related population term")
  AND
  ("concept B" OR "concept B synonym" OR "related method term")
)`,
  ieee_xplore: `("concept A" OR "concept A synonym")
AND
("concept B" OR "method term" OR "technology term")`,
  acm_digital_library: `(
  Title:("concept A" OR "concept A synonym")
  OR Abstract:("concept A" OR "related population term")
)
AND
Abstract:("concept B" OR "method term" OR "technology term")`,
  arxiv: ["concept A concept B", "concept A method term", "subtopic outcome term"].join("\n\n"),
  medrxiv: ["concept A concept B", "concept A outcome term"].join("\n\n"),
  biorxiv: ["concept A method term", "subtopic technology term"].join("\n\n"),
  europe_pmc: `("concept A" OR "concept A synonym" OR "related population term")
AND
("concept B" OR "concept B synonym" OR "related method term")`,
  openalex: `("concept A" OR "concept A synonym") AND ("concept B" OR "method term")`,
  crossref: `("concept A" OR "concept A synonym") AND ("concept B" OR "method term")`,
  semantic_scholar: `("concept A" OR "concept A synonym") AND ("concept B" OR "method term")`,
  doaj: `("concept A" OR "concept A synonym") AND ("concept B" OR "method term")`,
  core: `("concept A" OR "concept A synonym") AND ("concept B" OR "method term")`
};

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
    ...options
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json() as Promise<T>;
}

function statusTone(configured: boolean) {
  return configured ? "bg-emerald-50 text-emerald-800 ring-emerald-200" : "bg-amber-50 text-amber-800 ring-amber-200";
}

function shortSourceError(source: string, error: string) {
  if (error.includes("Semantic Scholar")) return "Free source, but public rate limit reached. Retry later or add optional key.";
  if (error.includes("Scopus rejected")) return "Scopus entitlement/key issue.";
  if (error.includes("requires IEEE_API_KEY")) return "IEEE API key missing.";
  if (error.includes("requires CORE_API_KEY")) return "CORE API key missing.";
  if (error.includes("requires ELSEVIER_API_KEY")) return "Scopus API key missing.";
  return source.includes(":") ? "Search string failed." : "Source skipped or failed.";
}

export default function App() {
  const [sources, setSources] = useState<SourceStatus[]>([]);
  const [apiSettings, setApiSettings] = useState<ApiSettingStatus[]>([]);
  const [apiDraft, setApiDraft] = useState<Record<string, string>>({});
  const [selectedSources, setSelectedSources] = useState<SourceName[]>(defaultSources);
  const [query, setQuery] = useState(
    '("your condition or topic" OR "your synonym") AND ("your method" OR "your second concept")'
  );
  const [customStrings, setCustomStrings] = useState<string[]>([]);
  const [sourceQueryText, setSourceQueryText] = useState<Record<SourceName, string>>(defaultSourceQueries);
  const [keywords, setKeywords] = useState("your topic; your method; your task; your outcome; your population");
  const [startYear, setStartYear] = useState("2018");
  const [endYear, setEndYear] = useState("2026");
  const [maxResults, setMaxResults] = useState("25");
  const [requireAbstract, setRequireAbstract] = useState(false);
  const [requireKeywords, setRequireKeywords] = useState(false);
  const [includePreprints, setIncludePreprints] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [records, setRecords] = useState<PaperRecord[]>([]);
  const [filter, setFilter] = useState("");
  const [format, setFormat] = useState("xlsx");
  const [notebook, setNotebook] = useState<NotebookStatus | null>(null);
  const [notice, setNotice] = useState("");
  const [isSearching, setSearching] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(true);

  async function refreshSetup() {
    const [sourceRows, settingsRows, notebookStatus] = await Promise.all([
      api<SourceStatus[]>("/api/sources/status"),
      api<ApiSettingStatus[]>("/api/settings/api-keys"),
      api<NotebookStatus>("/api/notebooks/status")
    ]);
    setSources(sourceRows);
    setApiSettings(settingsRows);
    setNotebook(notebookStatus);
  }

  useEffect(() => {
    refreshSetup().catch((error) => setNotice(error.message));
  }, []);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const latest = await api<Job>(`/api/jobs/${job.id}`);
        setJob(latest);
        if (latest.status === "completed") {
          setSearching(false);
          const rows = await api<PaperRecord[]>(`/api/jobs/${job.id}/records`);
          setRecords(rows);
          window.clearInterval(timer);
        }
      } catch (error) {
        setNotice(error instanceof Error ? error.message : "Could not refresh job.");
      }
    }, 1800);
    return () => window.clearInterval(timer);
  }, [job]);

  const missingSettings = apiSettings.filter((setting) => !setting.configured);
  const configuredSettings = apiSettings.length - missingSettings.length;

  const filteredRecords = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    if (!needle) return records;
    return records.filter((record) =>
      [record.title, record.abstract, record.journal, record.doi, record.authors.join(" "), record.source_databases.join(" ")]
        .join(" ")
        .toLowerCase()
        .includes(needle)
    );
  }, [records, filter]);

  async function saveApiSettings(event: FormEvent) {
    event.preventDefault();
    const values = Object.fromEntries(Object.entries(apiDraft).filter(([, value]) => value.trim()));
    if (Object.keys(values).length === 0) {
      setNotice("Enter at least one value to save.");
      return;
    }
    try {
      const updated = await api<ApiSettingStatus[]>("/api/settings/api-keys", {
        method: "POST",
        body: JSON.stringify({ values })
      });
      setApiSettings(updated);
      setApiDraft({});
      await refreshSetup();
      setNotice("Settings saved to .env. New searches will use the updated values.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not save settings.");
    }
  }

  async function runSearch(event: FormEvent) {
    event.preventDefault();
    const selectedRestricted = selectedSources.filter((source) => restrictedSources.has(source));
    const notReady = sources
      .filter((source) => selectedSources.includes(source.name) && (!source.configured || importOnlySources.has(source.name)))
      .map((source) => sourceLabels[source.name]);
    if (notReady.length > 0) {
      const ok = window.confirm(
        `These selected sources are restricted, import-only, or not configured: ${notReady.join(", ")}.\n\n` +
          "They may be skipped or return entitlement messages. Continue anyway?"
      );
      if (!ok) return;
    } else if (selectedRestricted.length > 0) {
      const ok = window.confirm(
        `You selected restricted/licensed sources: ${selectedRestricted.map((source) => sourceLabels[source]).join(", ")}.\n\n` +
          "Make sure credentials and institutional access are configured. Continue?"
      );
      if (!ok) return;
    }
    setSearching(true);
    setRecords([]);
    setNotice("");
    try {
      const created = await api<Job>("/api/search", {
        method: "POST",
        body: JSON.stringify({
          query,
          query_strings: customStrings.map((item) => item.trim()).filter(Boolean),
          source_queries: Object.fromEntries(
            Object.entries(sourceQueryText)
              .map(([source, text]) => [
                source,
                text
                  .split(/\n{2,}/)
                  .map((item) => item.trim())
                  .filter(Boolean)
              ])
              .filter(([, strings]) => (strings as string[]).length > 0)
          ),
          keywords: keywords.split(";").map((item) => item.trim()).filter(Boolean),
          start_year: startYear ? Number(startYear) : null,
          end_year: endYear ? Number(endYear) : null,
          sources: selectedSources,
          max_results_per_source: Number(maxResults),
          require_abstract: requireAbstract,
          require_keywords: requireKeywords,
          include_preprints: includePreprints
        })
      });
      setJob(created);
    } catch (error) {
      setSearching(false);
      setNotice(error instanceof Error ? error.message : "Search failed.");
    }
  }

  async function exportRecords(openNotebook = false, target: "jupyter" | "vscode" = "jupyter") {
    if (!job) return;
    setNotice("");
    try {
      const body = JSON.stringify({
        job_id: job.id,
        format,
        filtered_record_ids: filteredRecords.map((record) => record.id)
      });
      if (openNotebook) {
        const result = await api<{ export: { download_url: string }; notebook: { message: string } }>(
          `/api/notebooks/export-and-open?target=${target}`,
          { method: "POST", body }
        );
        setNotice(`${result.notebook.message} Export ready: ${result.export.download_url}`);
        return;
      }
      const result = await api<{ download_url: string; filename: string; record_count: number }>("/api/exports", {
        method: "POST",
        body
      });
      setNotice(`Exported ${result.record_count} records to ${result.filename}`);
      window.open(result.download_url, "_blank");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Export failed.");
    }
  }

  async function openNotebook(target: "jupyter" | "vscode") {
    try {
      const result = await api<{ message: string }>(`/api/notebooks/open/${target}`, { method: "POST" });
      setNotice(result.message);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Notebook launcher failed.");
    }
  }

  function toggleSource(name: SourceName) {
    setSelectedSources((current) => (current.includes(name) ? current.filter((item) => item !== name) : [...current, name]));
  }

  function updateCustomString(index: number, value: string) {
    setCustomStrings((current) => current.map((item, itemIndex) => (itemIndex === index ? value : item)));
  }

  function addCustomString() {
    setCustomStrings((current) => [...current, ""]);
  }

  function removeCustomString(index: number) {
    setCustomStrings((current) => current.filter((_, itemIndex) => itemIndex !== index));
  }

  function updateSourceQuery(sourceName: SourceName, value: string) {
    setSourceQueryText((current) => ({ ...current, [sourceName]: value }));
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-slate-200 bg-white px-4 py-5 sm:px-8 lg:px-12">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm font-extrabold uppercase text-coral">Local scholarly metadata engine</p>
            <h1 className="mt-1 text-3xl font-black text-ink sm:text-4xl">PhD Literature Metadata Scraper</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">
              Search trusted academic sources, deduplicate metadata, export analysis files, and open the result notebook from one local dashboard.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="btn" type="button" onClick={() => openNotebook("jupyter")}>Open in Jupyter</button>
            <button className="btn" type="button" onClick={() => openNotebook("vscode")}>Open in VS Code</button>
          </div>
        </div>
      </header>

      {notice && <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 sm:px-8 lg:px-12">{notice}</div>}

      <section className="px-4 py-6 sm:px-8 lg:px-12">
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="panel lg:col-span-2">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 className="text-xl font-black">Setup status</h2>
                <p className="mt-1 text-sm text-slate-600">Keys are stored locally in `.env`. Saved secrets are masked and never displayed back in full.</p>
              </div>
              <button className="btn" type="button" onClick={() => setSettingsOpen((value) => !value)}>
                {settingsOpen ? "Hide settings" : "Update API keys"}
              </button>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-md border border-slate-200 p-4">
                <p className="text-sm text-slate-500">Configured fields</p>
                <p className="mt-1 text-3xl font-black">{configuredSettings}/{apiSettings.length || 7}</p>
              </div>
              <div className="rounded-md border border-slate-200 p-4">
                <p className="text-sm text-slate-500">Ready sources</p>
                <p className="mt-1 text-3xl font-black">{sources.filter((source) => source.available).length}/{sources.length || 9}</p>
              </div>
              <div className="rounded-md border border-slate-200 p-4">
                <p className="text-sm text-slate-500">Notebook tools</p>
                <p className="mt-1 text-sm font-bold text-slate-800">{notebook?.message ?? "Checking..."}</p>
                {notebook && !notebook.vscode_available && (
                  <p className="mt-2 text-xs text-slate-500">
                    VS Code fix: open VS Code, press Cmd+Shift+P, run “Shell Command: Install 'code' command in PATH”, then restart this app.
                  </p>
                )}
              </div>
            </div>

            {settingsOpen && (
              <form className="mt-5 grid gap-4" onSubmit={saveApiSettings}>
                <div className="grid gap-3 md:grid-cols-2">
                  {apiSettings.map((setting) => (
                    <div className="rounded-md border border-slate-200 p-4" key={setting.field}>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="font-black">{setting.label}</h3>
                          <p className="mt-1 text-xs font-semibold text-slate-500">{setting.env_name}</p>
                        </div>
                        <span className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${statusTone(setting.configured)}`}>
                          {setting.configured ? `saved ${setting.masked_value}` : "missing"}
                        </span>
                      </div>
                      <p className="mt-3 text-sm text-slate-600">{setting.help_text}</p>
                      <p className="mt-2 text-xs text-slate-500">Used for: {setting.required_for.join(", ")}</p>
                      <input
                        className="field-input mt-3"
                        type={setting.secret ? "password" : "email"}
                        placeholder={setting.configured ? "Leave blank to keep current value" : `Enter ${setting.env_name}`}
                        value={apiDraft[setting.field] ?? ""}
                        onChange={(event) => setApiDraft((current) => ({ ...current, [setting.field]: event.target.value }))}
                      />
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button className="btn-primary btn" type="submit">Save API settings</button>
                  <button className="btn" type="button" onClick={() => refreshSetup().catch((error) => setNotice(error.message))}>Refresh status</button>
                </div>
              </form>
            )}
          </div>

          <aside className="panel">
            <h2 className="text-xl font-black">Run progress</h2>
            <p className="mt-2 text-sm text-slate-600">{job ? job.message : "No search has started yet."}</p>
            {job && (
              <div className="mt-4 grid gap-3">
                <div>
                  <div className="mb-1 flex items-center justify-between text-xs font-bold text-slate-600">
                    <span>{job.completed_steps}/{job.total_steps || 0} steps</span>
                    <span>{job.progress_percent || 0}%</span>
                  </div>
                  <div className="h-3 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-pine transition-all"
                      style={{ width: `${job.progress_percent || 0}%` }}
                    />
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-md bg-slate-50 p-3"><p className="text-xs text-slate-500">Status</p><p className="font-black">{job.status}</p></div>
                  <div className="rounded-md bg-slate-50 p-3"><p className="text-xs text-slate-500">Raw</p><p className="font-black">{job.total_records}</p></div>
                  <div className="rounded-md bg-slate-50 p-3"><p className="text-xs text-slate-500">Deduped</p><p className="font-black">{job.deduped_records}</p></div>
                </div>
                {(job.active_source || job.active_query) && (
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                    {job.active_source && <p><span className="font-black">Active source:</span> {job.active_source}</p>}
                    {job.active_query && <p className="mt-1 break-words"><span className="font-black">Current string:</span> {job.active_query}</p>}
                  </div>
                )}
                <div className="flex flex-wrap gap-2">
                  {Object.entries(job.source_counts).map(([source, count]) => (
                    <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-bold text-emerald-800" key={source}>{source}: {count}</span>
                  ))}
                </div>
                {Object.entries(job.errors).map(([source, error]) => (
                  <details className="max-w-full overflow-hidden rounded-md border-l-4 border-coral bg-red-50 p-3 text-sm text-red-900" key={source}>
                    <summary className="cursor-pointer font-bold">{source}: {shortSourceError(source, error)}</summary>
                    <p className="mt-2 whitespace-pre-wrap break-words font-mono text-xs">{error}</p>
                  </details>
                ))}
              </div>
            )}
            <div className="mt-5 grid gap-2">
              <button className="btn" type="button" onClick={() => exportRecords(true, "jupyter")} disabled={!job || records.length === 0}>
                Export then open Jupyter
              </button>
              <button className="btn" type="button" onClick={() => exportRecords(true, "vscode")} disabled={!job || records.length === 0}>
                Export then open VS Code
              </button>
            </div>
          </aside>
        </div>
      </section>

      <section className="px-4 pb-6 sm:px-8 lg:px-12">
        <form className="panel" onSubmit={runSearch}>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="text-xl font-black">Search builder</h2>
              <p className="mt-1 text-sm text-slate-600">Choose sources, tune metadata filters, and run a repeatable search.</p>
            </div>
            <button className="btn-primary btn" type="submit" disabled={isSearching}>{isSearching ? "Searching..." : "Run metadata search"}</button>
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <label className="field-label" htmlFor="query">Main search string</label>
              <textarea className="field-input mt-1 min-h-32" id="query" value={query} onChange={(event) => setQuery(event.target.value)} />
              <p className="mt-2 text-xs text-slate-500">Use database-ready Boolean syntax. This main string always runs first.</p>
            </div>
            <div>
              <label className="field-label" htmlFor="keywords">Keywords</label>
              <textarea className="field-input mt-1 min-h-32" id="keywords" value={keywords} onChange={(event) => setKeywords(event.target.value)} />
            </div>
          </div>

          <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h3 className="font-black">Custom search strings</h3>
                <p className="mt-1 text-sm text-slate-600">
                  Add extra Boolean strings for synonyms, narrower subtopics, or database-specific phrasing. Results are merged and deduplicated.
                </p>
              </div>
              <button className="btn bg-white" type="button" onClick={addCustomString}>Add string</button>
            </div>
            <div className="mt-4 grid gap-3">
              {customStrings.map((customString, index) => (
                <div className="grid gap-2 rounded-md border border-slate-200 bg-white p-3" key={`custom-string-${index}`}>
                  <div className="flex items-center justify-between gap-3">
                    <label className="field-label" htmlFor={`custom-string-${index}`}>Custom string {index + 1}</label>
                    <button className="btn min-h-8 px-3 py-1 text-xs" type="button" onClick={() => removeCustomString(index)}>Remove</button>
                  </div>
                  <textarea
                    className="field-input min-h-20"
                    id={`custom-string-${index}`}
                    value={customString}
                    onChange={(event) => updateCustomString(index, event.target.value)}
                    placeholder='Example: ("your topic" OR "related term") AND ("your method" OR "your task")'
                  />
                </div>
              ))}
              {customStrings.length === 0 && (
                <p className="rounded-md border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500">
                  No extra strings yet. The main search string will still run.
                </p>
              )}
            </div>
          </div>

          <div className="mt-5 rounded-lg border border-slate-200 bg-white p-4">
            <div>
              <h3 className="font-black">Database-specific strings</h3>
              <p className="mt-1 text-sm text-slate-600">
                Paste syntax that belongs to one database only, such as PubMed `[TIAB]`, PubMed MeSH, Scopus `TITLE-ABS-KEY(...)`, or Web of Science `TS=...`.
                Separate multiple strings for the same database with a blank line.
              </p>
            </div>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              {selectedSources.map((sourceName) => (
                <div className="rounded-md border border-slate-200 bg-slate-50 p-3" key={`source-query-${sourceName}`}>
                  <div className="flex items-center justify-between gap-3">
                    <label className="field-label" htmlFor={`source-query-${sourceName}`}>{sourceLabels[sourceName]}</label>
                    {sourceQueryText[sourceName]?.trim() && (
                      <button className="btn min-h-8 px-3 py-1 text-xs" type="button" onClick={() => updateSourceQuery(sourceName, "")}>Clear</button>
                    )}
                  </div>
                  <textarea
                    className="field-input mt-2 min-h-28"
                    id={`source-query-${sourceName}`}
                    value={sourceQueryText[sourceName] ?? ""}
                    onChange={(event) => updateSourceQuery(sourceName, event.target.value)}
                    placeholder={`Optional ${sourceLabels[sourceName]}-specific search string`}
                  />
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-slate-500">
              ACM Digital Library is import/manual for now. Run ACM searches on its portal, export RIS/BibTeX/CSV, then keep those files with your review materials.
            </p>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div>
              <label className="field-label" htmlFor="start-year">Start year</label>
              <input className="field-input mt-1" id="start-year" value={startYear} onChange={(event) => setStartYear(event.target.value)} />
            </div>
            <div>
              <label className="field-label" htmlFor="end-year">End year</label>
              <input className="field-input mt-1" id="end-year" value={endYear} onChange={(event) => setEndYear(event.target.value)} />
            </div>
            <div>
              <label className="field-label" htmlFor="max-results">Max per source</label>
              <input className="field-input mt-1" id="max-results" value={maxResults} onChange={(event) => setMaxResults(event.target.value)} />
            </div>
          </div>

          <div className="mt-5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="font-black">Sources</h3>
                <p className="text-sm text-slate-600">Start with open sources for fewer credential errors, then add licensed databases when keys are ready.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button className="btn bg-white" type="button" onClick={() => setSelectedSources(openSourcePreset)}>Open sources only</button>
                <button className="btn bg-white" type="button" onClick={() => setSelectedSources([])}>Clear all</button>
              </div>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {sources.map((source) => (
                <label
                  className={`rounded-md border p-4 transition ${
                    selectedSources.includes(source.name) ? "border-pine bg-emerald-50" : "border-slate-200 bg-white"
                  }`}
                  key={source.name}
                >
                  <div className="flex items-start gap-3">
                    <input
                      className="mt-1"
                      type="checkbox"
                      checked={selectedSources.includes(source.name)}
                      onChange={() => toggleSource(source.name)}
                    />
                    <div>
                      <p className="font-black">{sourceLabels[source.name]}</p>
                      <p className="text-sm text-slate-600">{sourceDescriptions[source.name]}</p>
                      {source.requires_key && (
                        <p className={`mt-2 inline-flex rounded-full px-2 py-1 text-xs font-bold ring-1 ${statusTone(source.configured)}`}>
                          {source.configured ? "credential ready" : "missing credential"}
                        </p>
                      )}
                      {importOnlySources.has(source.name) && (
                        <p className="mt-2 inline-flex rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                          import/manual
                        </p>
                      )}
                      {source.message && <p className="mt-2 text-xs text-amber-800">{source.message}</p>}
                      {source.rate_limit_note && (
                        <p className="mt-2 text-xs text-slate-500">
                          Rate limit: {source.rate_limit_note}
                        </p>
                      )}
                      {source.daily_limit_note && (
                        <p className="mt-1 text-xs text-slate-500">
                          Daily quota: {source.daily_limit_note}
                        </p>
                      )}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-4">
            <label className="inline-flex items-center gap-2 text-sm font-bold"><input type="checkbox" checked={requireAbstract} onChange={(event) => setRequireAbstract(event.target.checked)} /> Require abstracts</label>
            <label className="inline-flex items-center gap-2 text-sm font-bold"><input type="checkbox" checked={requireKeywords} onChange={(event) => setRequireKeywords(event.target.checked)} /> Require keywords</label>
            <label className="inline-flex items-center gap-2 text-sm font-bold"><input type="checkbox" checked={includePreprints} onChange={(event) => setIncludePreprints(event.target.checked)} /> Include preprints</label>
          </div>
        </form>
      </section>

      <section className="border-t border-slate-200 bg-white px-4 py-6 sm:px-8 lg:px-12">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-xl font-black">Results</h2>
            <p className="mt-1 text-sm text-slate-600">{filteredRecords.length} records visible from {records.length} harvested records.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <input className="field-input min-w-64" placeholder="Filter results" value={filter} onChange={(event) => setFilter(event.target.value)} />
            <select className="field-input w-36" value={format} onChange={(event) => setFormat(event.target.value)}>
              <option value="xlsx">Excel</option>
              <option value="csv">CSV</option>
              <option value="txt">Plain text</option>
              <option value="jsonl">JSONL</option>
              <option value="bib">BibTeX</option>
              <option value="ris">RIS</option>
            </select>
            <button className="btn" type="button" onClick={() => exportRecords(false)} disabled={!job || records.length === 0}>Export</button>
          </div>
        </div>

        <div className="mt-4 overflow-auto rounded-lg border border-slate-200">
          <table className="min-w-[1100px] border-collapse text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-600">
              <tr>
                <th className="p-3">Title</th>
                <th className="p-3">Year</th>
                <th className="p-3">Journal</th>
                <th className="p-3">Keywords</th>
                <th className="p-3">Sources</th>
                <th className="p-3">Flags</th>
              </tr>
            </thead>
            <tbody>
              {filteredRecords.map((record) => (
                <tr className="border-t border-slate-100 align-top" key={record.id}>
                  <td className="max-w-xl p-3">
                    <strong className="block text-ink">{record.title || "Untitled record"}</strong>
                    <span className="mt-2 line-clamp-3 block text-slate-600">{record.abstract || "No abstract available."}</span>
                    {record.doi && <small className="mt-2 block text-amber-800">DOI: {record.doi}</small>}
                  </td>
                  <td className="p-3">{record.year ?? ""}</td>
                  <td className="p-3">{record.journal}</td>
                  <td className="p-3">{[...record.author_keywords, ...record.indexed_keywords].slice(0, 5).join("; ")}</td>
                  <td className="p-3">{record.source_databases.join(", ")}</td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-1">
                      {record.is_peer_reviewed_likely && <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-bold text-emerald-800">peer reviewed likely</span>}
                      {!record.has_abstract && <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-800">missing abstract</span>}
                      {record.is_preprint && <span className="rounded-full bg-red-50 px-2 py-1 text-xs font-bold text-red-800">preprint</span>}
                    </div>
                  </td>
                </tr>
              ))}
              {filteredRecords.length === 0 && (
                <tr>
                  <td className="p-8 text-center text-slate-500" colSpan={6}>Run a search to populate metadata results.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
