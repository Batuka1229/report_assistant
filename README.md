# Report AI Assistant

Streamlit application for profiling Excel/CSV data, calculating deterministic
statistics with Pandas and NumPy, optionally interpreting those results through
configurable AI endpoints, and downloading Mongolian PDF, DOCX, or XLSX reports.

## Run locally

Python 3.11 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

To enable AI, set `AI_MODEL` and `AI_API_KEY` in `.env`. `AI_BASE_URL` points
to an OpenAI-compatible chat-completions endpoint. For a local Ollama endpoint,
for example, use `AI_BASE_URL=http://localhost:11434/v1`, set `AI_MODEL`, and
set `AI_API_TYPE=ollama`; a local endpoint does not need an API key.

Additional providers can be added as comma-separated names in `AI_PROVIDERS`.
For each name, configure `AI_<NAME>_BASE_URL`, `AI_<NAME>_MODEL`, and optionally
`AI_<NAME>_API_KEY` / `AI_<NAME>_API_TYPE`. Task-specific settings such as
`AI_TREND_ANALYSIS_PROVIDER` or `AI_REPORT_WRITING_MODEL` override the default
route. Provider adapters implement `BaseAIModel`, so another API protocol can
be supported without changing analysis or UI logic.

## Data handling

Uploads are read from memory and are not written to disk. Pandas and NumPy
calculate all reported statistics, comparisons, trends, correlations, and
outliers; AI requests contain aggregated analysis only, not raw records. AI is
optional: the application still creates deterministic reports if no model is
configured or an AI request fails. The source DataFrame is never cleaned or
modified implicitly.

## Tests

```powershell
python -m unittest discover -s tests -v
```
