# Consult-Workshop — Build Your Own AI News Briefing

Fork this repository and you will have a personalised daily AI briefing delivered to a web dashboard — automatically, for free, using GitHub Actions and GitHub Pages. No server to run. No subscription needed beyond an OpenRouter API key.

By the end of this guide you will have:
- A web dashboard at `https://YOUR-USERNAME.github.io/Consult-Workshop`
- A daily briefing that fetches articles from your chosen RSS feeds, scores them with an LLM against your research profile, and publishes a Markdown summary to your repo every morning
- A weekly round-up generated every Sunday
- A manual trigger to run a briefing on demand at any time

---

## What you get

| Feature | Details |
|---------|---------|
| **Daily briefing** | Fetches articles from your RSS feeds, scores relevance (Tier 0–3) with an LLM, generates an executive summary for the best articles |
| **Web dashboard** | GitHub Pages site to read all your briefings; no login needed beyond your own GitHub token |
| **Weekly round-up** | A synthesised overview of the week's briefings, generated every Sunday |
| **Manual trigger** | Run a briefing from the Actions tab at any time, choose any model |
| **Source discovery** | Give the "Add source" workflow any website URL — it finds the RSS feed and adds it automatically |
| **Serendipity** | A random sample of sources from an extended pool is added to each run, surfacing unexpected signals |

---

## How it works

```
1. GitHub Actions wakes up at 08:00 every morning (configurable)
2. Python fetches articles from your RSS feeds (last 25 hours)
3. Articles are sent to an LLM (via OpenRouter) with your research profile
4. The LLM assigns each article a relevance tier:
      Tier 1 — perfectly relevant    ← shown first
      Tier 2 — broadly relevant      ← shown second
      Tier 3 — low signal            ← hidden by default
      Tier 0 — exclude               ← never shown
5. An executive summary is generated for the Tier 1 articles
6. The briefing is saved as a Markdown file in briefings/ and committed to your repo
7. Your GitHub Pages dashboard reads the briefings via the GitHub API and displays them
```

The whole pipeline runs inside GitHub Actions — you do not need a server, a database, or a local Python environment (though you can run it locally too; see [Local development](#local-development-optional)).

---

## Prerequisites

- A **GitHub account** (free tier is fine)
- An **OpenRouter API key** — get one at [openrouter.ai/keys](https://openrouter.ai/keys)
  *(Your instructor may provide a key for the workshop session. You can add your own key later.)*
- Basic comfort with editing text files and clicking around GitHub. No local tooling required.

---

## Workshop setup

Work through these steps in order. Each step takes 2–5 minutes.

---

### Step 1 — Fork this repository

1. Click **Fork** in the top-right corner of this page
2. Leave the repository name as `Consult-Workshop` (or rename it — just remember the new name for Step 4)
3. Click **Create fork**

Your fork is now at `https://github.com/YOUR-USERNAME/Consult-Workshop`.

---

### Step 2 — Define your research profile

This is the most important step. The LLM reads this file to decide what counts as relevant.

1. In your fork, open `config/report_profile.yaml` (click the file, then the pencil icon ✏️)
2. Fill in every field — follow the inline comments for guidance:
   - **`title` / `title_en`** — the name of your research area
   - **`perspective`** — your analytical standpoint in one sentence
   - **`core_focus`** — 2–4 sentences describing your topic, geography, and angle
   - **`themes`** — 6–12 specific themes you want to track
   - **`key_actors`** — organisations or people to watch
   - **`tier_1` description** — what makes an article "perfectly relevant" to you
   - **`tier_2` description** — what makes an article "broadly relevant"
3. Commit directly to `main` (the default commit option)

> **Tip:** Be concrete in `core_focus`. Instead of *"AI policy"*, write *"How EU AI regulation affects insurance companies in Germany, focusing on compliance costs and competitive dynamics."* The more specific you are, the better the LLM scores articles.

---

### Step 3 — Choose your news sources

1. Open `config/sources.yaml`
2. Replace or add to the example feeds with sources relevant to your topic
3. Each entry needs:
   ```yaml
   - name: Source Name
     url: https://example.com/feed
     category: your_category   # free-form label, for your own organisation
     language: en               # or nl — display only, does not filter
   ```
4. To find a feed URL: try adding `/feed`, `/rss`, or `/feed.xml` to any news site's domain, or use [feedsearch.dev](https://feedsearch.dev)
5. Commit when done

> **Tip:** Start with 6–12 feeds. You can add more later using the "Add source" workflow (see [Adding sources](#adding-sources-after-setup)).

---

### Step 4 — Point the dashboard at your fork

1. Open `web/config.js`
2. Change `'your-github-username'` to your actual GitHub username
3. Change `'Consult-Workshop'` if you renamed your fork
4. Optionally change `DASHBOARD_TITLE` to anything you like
5. Commit

```javascript
const OWNER           = 'your-github-username';  // ← change this
const REPO            = 'Consult-Workshop';        // ← change if you renamed the fork
const DASHBOARD_TITLE = 'My Briefing Dashboard';  // ← optional: rename
```

---

### Step 5 — Add the API key secret

1. In your fork, go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `OPENROUTER_API_KEY`
4. Value: your OpenRouter API key
5. Click **Add secret**

> Secrets are encrypted and never visible after saving — not even to you. They are injected into the GitHub Actions environment at runtime.

---

### Step 6 — Add the dashboard access token

The dashboard reads your repo's files via the GitHub API. It needs a personal access token (PAT) with `repo` scope.

1. Go to [github.com/settings/tokens/new](https://github.com/settings/tokens/new)
   - Note / description: `Consult-Workshop dashboard`
   - Expiration: **90 days** (or longer if you want it to keep working)
   - Scopes: check **`repo`** (the top-level checkbox)
2. Click **Generate token** — copy it immediately (it will not be shown again)
3. Back in your repo: **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `GH_PAT`
   - Value: the token you just copied
4. Click **Add secret**

> This token is stored as a GitHub secret and is never in your code. It only gives read access to your own public repo.

---

### Step 7 — Enable GitHub Pages

1. In your fork, go to **Settings → Pages**
2. Under **Source**, select **GitHub Actions** (not "Deploy from a branch")
3. Click **Save**

The first deployment happens automatically when you push to `main`. It takes about 1–2 minutes.

---

### Step 8 — Run your first briefing

1. Go to the **Actions** tab in your fork
2. In the left sidebar, click **Daily Briefing**
3. Click **Run workflow → Run workflow** (leave the model field blank)
4. Watch the run — it takes about 60–90 seconds
5. When the green checkmark appears, a new file is in `briefings/`

---

### Step 9 — Open your dashboard

1. Your dashboard URL is: `https://YOUR-USERNAME.github.io/Consult-Workshop`
2. On the auth screen, paste your **GH_PAT** token (from Step 6) and click **Save**
3. Your first briefing should appear under **Daily briefings**

---

## Configuration reference

### `config/report_profile.yaml` — field guide

| Field | What to write |
|-------|--------------|
| `title` | Full title of your report (any language) |
| `title_en` | English version — appears in the briefing header |
| `perspective` | Your analytical standpoint in one line |
| `core_focus` | 2–4 sentences: topic, geography, angle |
| `themes` | List of 6–12 specific themes to track |
| `key_actors` | Organisations or people to watch closely |
| `tier_1` description | What makes an article "perfectly relevant" to you — be specific |
| `tier_2` description | What makes an article "broadly relevant" — can be wider |

After editing, commit and push. The next briefing run will use your updated profile.

---

### `config/sources.yaml` — section guide

| Section | Behaviour |
|---------|-----------|
| `rss_feeds` | Fetched on every single run |
| `serendipity_sources` | Randomly sampled — 3 sources per run by default |
| `social` | Twitter/X accounts via RSSHub (optional — see [Twitter/X monitoring](#twitterx-social-monitoring-optional)) |

Each feed entry needs `name`, `url`, `category`, and `language`. The `category` field is a free-form label for your own organisation and does not affect LLM scoring.

---

### `web/config.js` — field guide

| Variable | What to set |
|----------|-------------|
| `OWNER` | Your GitHub username |
| `REPO` | Your repository name |
| `DASHBOARD_TITLE` | Title shown in browser tab and page header |
| `MODELS` | LLM options in the dashboard dropdown. Edit freely — keep the object shape. |

---

### Behaviour variables (optional)

These can be set as **repository variables** (not secrets) at **Settings → Secrets and variables → Actions → Variables → New repository variable**. If not set, the defaults shown below are used.

| Variable | Default | Effect |
|----------|---------|--------|
| `OPENROUTER_MODEL` | `anthropic/claude-sonnet-4.6` | Default model for scheduled runs |
| `LOOKBACK_HOURS` | `25` | How many hours back to look for articles |
| `SERENDIPITY_N` | `3` | Sources randomly sampled from the serendipity pool per run |
| `TIER1_THRESHOLD` | `3` | Minimum Tier 1 articles before the pipeline stops iterating |
| `MAX_ITERATIONS` | `3` | Maximum fetch-and-score iterations if Tier 1 count is low |
| `INCLUDE_TIER3` | `false` | Set to `true` to show low-signal (Tier 3) articles |

---

## Adding sources after setup

**Method A — automated (recommended):**
1. Go to **Actions → Add source → Run workflow**
2. Paste one or more website URLs (comma-separated)
3. The workflow visits each site, discovers the RSS feed, and adds it to `config/sources.yaml`

**Method B — manual:**
Edit `config/sources.yaml` directly, following the format of existing entries. Commit when done.

---

## Changing the schedule

Open `.github/workflows/daily_briefing.yml` and edit the `cron` line:

```yaml
- cron: '0 6 * * *'  # 06:00 UTC = 08:00 CEST
```

Use [crontab.guru](https://crontab.guru) to build your own expression. All times are **UTC** — subtract 2 hours for CEST, 1 hour for CET.

Examples:
- `0 6 * * *` — every day at 08:00 CEST
- `0 7 * * 1-5` — weekdays only at 09:00 CEST
- `0 5 * * *` — every day at 07:00 CEST

---

## Twitter/X social monitoring (optional)

Twitter/X requires a self-hosted [RSSHub](https://rsshub.app) instance with OAuth credentials. The public `rsshub.app` no longer serves Twitter feeds reliably.

**Quickest setup: Railway one-click deploy**

1. Sign up at [railway.app](https://railway.app)
2. Deploy the [DIYgod/RSSHub](https://docs.rsshub.app/deploy/railway) template (~€3–5/month)
3. In your Railway project, add environment variables for `TWITTER_AUTH_TOKEN` and `TWITTER_CT0` (see [RSSHub docs](https://docs.rsshub.app/deploy/))
4. Add your Railway URL as a GitHub secret: **`RSSHUB_INSTANCE`** = `https://your-app.railway.app`
5. In `config/sources.yaml`, uncomment `rsshub_instance` and add `twitter_accounts` entries:
   ```yaml
   social:
     rsshub_instance: https://your-app.railway.app
     twitter_accounts:
       - handle: sama
         name: Sam Altman
         relevance_hint: AI industry, OpenAI, regulation views
   ```

**Monthly maintenance:** Twitter OAuth cookies expire after roughly 30 days. To renew: open X in your browser, open DevTools → Application → Cookies → `x.com`, copy the `auth_token` and `ct0` values, and update them in your Railway project's environment variables.

---

## Approximate cost

| Component | Cost |
|-----------|------|
| GitHub Actions (public repo) | Free |
| GitHub Pages (public repo) | Free |
| OpenRouter — Claude Sonnet 4.6 | ~$0.05–0.20 per briefing run |
| OpenRouter — Claude Haiku 4.5 | ~$0.01–0.02 per run (12× cheaper) |
| Railway RSSHub (Twitter only) | ~€3–5/month |

The briefing pipeline processes roughly 15K input tokens and 1.5K output tokens per run. Haiku 4.5 is a good budget option if cost matters.

---

## Troubleshooting

**The briefing run failed immediately**
→ Check that `OPENROUTER_API_KEY` is set as a **secret** (Settings → Secrets), not a variable. Click the failed run in the Actions tab and expand the "Run briefing" step to read the error.

**All articles are Tier 3 or the briefing says "LLM scoring skipped"**
→ Your API key is missing, invalid, or out of credit. Check at [openrouter.ai/keys](https://openrouter.ai/keys). Also verify the model name in `OPENROUTER_MODEL` is a valid OpenRouter model ID.

**The briefing runs but the articles seem unrelated to my topic**
→ Your `core_focus` and `tier_1` description in `report_profile.yaml` are too vague. Name specific institutions, datasets, or geographies. Also check that your feeds in `sources.yaml` actually cover your topic.

**The dashboard says "Token rejected or no access to repo"**
→ Your GH_PAT has expired or was not created with `repo` scope. Generate a new token (Step 6) and update the secret.

**The dashboard says "Failed to load sources" or shows an empty briefings list**
→ Your `OWNER` or `REPO` in `web/config.js` does not match your actual GitHub username or repo name. Check for typos — GitHub usernames are case-sensitive.

**The dashboard URL gives a 404**
→ Make sure Pages is configured to use **GitHub Actions** as the source (Settings → Pages), not a branch. Check the Actions tab for a "Deploy Dashboard" workflow run and read any errors.

**Twitter accounts stopped appearing**
→ The RSSHub OAuth cookies have expired. See [Twitter/X monitoring](#twitterx-social-monitoring-optional) → Monthly maintenance.

**I can't find the RSS feed for a site**
→ Use the "Add source" workflow first — it auto-discovers most feeds. If that fails, try appending `/feed`, `/rss`, or `/feed.xml` to the domain. [feedsearch.dev](https://feedsearch.dev) is a useful last resort.

---

## Local development (optional)

If you want to test the pipeline on your own machine before pushing:

```bash
# 1. Clone your fork
git clone https://github.com/YOUR-USERNAME/Consult-Workshop.git
cd Consult-Workshop

# 2. Create a virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Copy the environment file and fill in your API key
cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY=your_key_here

# 4. Test run (fetches articles, skips LLM — free)
python -m src.briefing.run --dry-run

# 5. Full run (uses your API key)
python -m src.briefing.run
```

Output is written to `outputs/briefing_YYYY-MM-DD_HHMM.md`.

---

## Syncing updates from this base repo

If improvements are pushed to this `Consult-Workshop` base repo, you can pull them into your fork:

1. On your fork's main page, click **Sync fork → Update branch**
2. If you have edited `config/report_profile.yaml` or `config/sources.yaml`, GitHub will flag merge conflicts — resolve them manually to keep your customisations

> **Important:** Sync only after committing your own changes first, otherwise the sync may overwrite your configuration files.
