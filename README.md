# Consult-Workshop — Your Own Daily AI Briefing

You're going to build a small automated pipeline that wakes up every morning, fetches articles from news feeds you choose, scores each one against your own research profile using an LLM, and publishes a clean summary to a web dashboard. Everything runs on GitHub — no server, no subscription, nothing to install locally unless you want to.

By the end of this you'll have a dashboard at `https://YOUR-USERNAME.github.io/Consult-Workshop` with a fresh briefing waiting for you every morning.

---

## What it does

- **Daily briefing** — fetches your RSS feeds, has an LLM score each article for relevance to your topic (Tier 0–3), writes an executive summary for the best ones, and commits the result to your repo as a Markdown file
- **Web dashboard** — reads those files via the GitHub API and displays them; log in once with your own GitHub token
- **Weekly round-up** — a synthesis of the week's briefings, generated every Sunday
- **Social monitoring** — pulls in posts from Twitter/X accounts you follow and summarises what they're discussing
- **Manual trigger** — run a briefing on demand from the Actions tab at any time
- **Source discovery** — paste any website URL into the "Add source" workflow and it finds the RSS feed automatically

---

## What I'm giving you for the workshop

For the session itself you don't need to create any accounts yet. I'll give you:

- An **OpenRouter API key** — this is what pays for the LLM calls. You can get your own later at [openrouter.ai/keys](https://openrouter.ai/keys); for now just use the one I give you.
- An **RSSHub instance URL** — this is what converts Twitter/X accounts into RSS feeds. I'm running my own on Railway, you can use it. If you want to set up your own after the workshop, there's a section at the bottom on how to do that.

The only account you actually need right now is a **GitHub account** (free).

---

## Setting up

Work through these in order. Most steps are just editing a file and clicking commit.

---

### Step 1 — Fork the repo

Click **Fork** in the top-right corner. Leave the name as `Consult-Workshop` or rename it — just remember the name for Step 5. Click **Create fork**.

Your fork is now at `https://github.com/YOUR-USERNAME/Consult-Workshop`.

---

### Step 2 — Define your research profile

Open `config/report_profile.yaml` (click the file, then the pencil icon) and fill in the fields. This is what tells the LLM what counts as relevant. The inline comments explain each field.

The most important fields:

- **`core_focus`** — 2–4 sentences on what you care about, what goal you want to achieve with the daily briefings. Be specific. *"AI policy in Europe"* is too broad. *"How the EU AI Act affects compliance costs for Dutch insurance companies"* is good. The more concrete you are, the better the scoring.
- **`themes`** — list 6–12 specific topics to track
- **`tier_1` description** — what does "perfectly relevant" look like for your topic? Describe the criteria the LLM should use.

Commit when done.

---

### Step 3 — Choose your RSS feeds

Open `config/sources.yaml` and replace or add to the example feeds in the `rss_feeds` section. Each entry needs a name, a URL, a category label (can be anything — it's just for your own organisation), and a language.

To find a feed URL: most news sites expose one at `/feed`, `/rss`, or `/feed.xml`. Try appending those to any domain, or use [feedsearch.dev](https://feedsearch.dev). Alternatively, use the "Add source" workflow in the Actions tab — you paste a URL and it discovers the feed automatically.

Start with 6–12 feeds. You can always add more later.

---

### Step 4 — Add your Twitter/X accounts

Still in `config/sources.yaml`, scroll to the `social` section and add the Twitter/X accounts you want to follow. Pick people who post about your research topic — researchers, journalists, policy makers, whoever.

```yaml
social:
  twitter_accounts:
    - handle: ylecun
      name: Yann LeCun
      relevance_hint: AI research, open-source AI debates
    - handle: AndrewYNg
      name: Andrew Ng
      relevance_hint: AI industry, education
```

The `handle` is the Twitter username without the `@`. Add as many as you want. The pipeline summarises what they're all discussing in a separate section of the briefing.

You can also use popular LLMs ofcourse to help you search for relevant folk's twitter handles and have it fill in the format above.

The RSSHub URL itself comes from a secret you'll add in Step 6 — no need to put it in this file.

---

### Step 5 — Name your dashboard (optional)

The dashboard auto-detects your GitHub username and repo name from the Pages URL — you don't need to touch those. The only thing worth changing is the title:

Open `web/config.js` and edit this one line:

```javascript
const DASHBOARD_TITLE = 'My Briefing Dashboard';  // call it whatever you want
```

Commit if you changed it, skip this step entirely if you don't care about the title.

---

### Step 6 — Add your secrets

Go to your fork → **Settings → Secrets and variables → Actions**.

Add these three secrets one by one (click **New repository secret** for each):

| Secret name | Value |
|-------------|-------|
| `OPENROUTER_API_KEY` | The API key I gave you |
| `RSSHUB_INSTANCE` | The RSSHub URL I gave you |
| `GH_PAT` | A GitHub personal access token — see below |

**Getting the GH_PAT:**

The dashboard uses this token to read your briefing files, trigger the Generate runs, and manage a few settings. We'll make a **fine-grained token** scoped to just your repo — safer than a broad classic token.

1. Go to [github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta) and click **Generate new token**
2. Give it a name (e.g. `Consult-Workshop dashboard`) and set an expiry (90 days is fine)
3. Under **Repository access** → select **Only select repositories** → pick your fork
4. Under **Permissions** → open **Repository permissions** and set these three:
   - **Contents** → **Read and write** *(reads briefings; lets you add/remove sources from the dashboard)*
   - **Actions** → **Read and write** *(triggers the Generate runs; checks run status)*
   - **Variables** → **Read and write** *(saves your default model choice)*
5. Click **Generate token** — copy it immediately, you won't see it again. You'll also need it to log in to the dashboard in Step 9, so keep it somewhere handy for now (notes app is fine, you'll paste it twice)
6. Add it as the `GH_PAT` secret

---

### Step 7 — Enable GitHub Pages

Go to **Settings → Pages**, set **Source** to **GitHub Actions**, click **Save**. That's it. The first deploy happens automatically when you push to `main` — takes about a minute.

When you make changes to the code, it can take up to 3min for the changes to be visible on the Github Page. Can be a bit annoying when you quickly want to test some things, but eh, it's free so can't complain too much, make yourself a drink in the meanwhile!

---

### Step 8 — Run your first briefing

Go to the **Actions** tab → **Daily Briefing** → **Run workflow → Run workflow**. Leave the model field blank. It takes about 60–90 seconds. When the green checkmark appears, there's a new file in `briefings/`.

---

### Step 9 — Open the dashboard

Go to `https://YOUR-USERNAME.github.io/Consult-Workshop`. On the auth screen, paste your `GH_PAT` (from Step 6) and click Save. Your first briefing should be right there. If you changed the name of the repo when you forked the original, you need to replace 'Consult-Workshop' with that name!!

This URL will be what you can use going forward to visit your dashboard. If you make other Github Pages (which is easy to do with coding agents that are everywhere now) they use the same format, with the git-repo name replacing 'Consult-Workshop'. This can allow you to easily make fancy looking portfolio websites that cost you zero in hosting and complies well with coding agents. The pages are static so they are somewhat limited in what they can do, but for 90% of simple use cases they work fine.

---

## Things you can change

### Choosing a different model

Haiku 4.5 is the default — it's fast, cheap (~€0.01–0.02 per briefing), and good enough for scoring and summarising news articles. If you want higher quality or want to try something else, change the `isDefault: true` flag in `web/config.js`.

To find models: go to [openrouter.ai/models](https://openrouter.ai/models), pick one, and copy its model ID (the string like `anthropic/claude-sonnet-4-5`). Add it to the `MODELS` array in `config.js`:

```javascript
const MODELS = [
  { id: 'anthropic/claude-haiku-4.5',  label: 'Claude Haiku 4.5',  costIn: 0.25, costOut: 1.25, isDefault: true },
  { id: 'mistralai/mistral-small-3.2', label: 'Mistral Small 3.2', costIn: 0.10, costOut: 0.30 },
  // ...
];
```

The costs are simple guestimations (put in costIn and costOut), you can edit those depending on what you see happening on OpenRouter for yourself. Costs increase/decrease as updates come and go and the context of the briefing increases or decreases. You don't need big expensive models for this workflow generally.

Note: some models need to be explicitly enabled on your OpenRouter account before they work. If a run fails with an auth or model error, check [openrouter.ai/settings/credits](https://openrouter.ai/settings/credits) to make sure the model is available.

---

### Changing the schedule

Open `.github/workflows/daily_briefing.yml` and edit the cron line:

```yaml
- cron: '0 6 * * *'  # 06:00 UTC = 08:00 CEST
```

Use [crontab.guru](https://crontab.guru) to build your own expression. Times are in UTC — subtract 2 hours for CEST, 1 for CET.

---

### Behaviour knobs (optional)

These can be set as **repository variables** at **Settings → Secrets and variables → Actions → Variables**. They all have sensible defaults so you don't need to touch them, but they're there if you want to experiment.

| Variable | Default | What it does |
|----------|---------|-------------|
| `LOOKBACK_HOURS` | `25` | How far back to look for articles |
| `SERENDIPITY_N` | `3` | Extra sources randomly sampled per run from the serendipity pool |
| `TIER1_THRESHOLD` | `3` | Minimum Tier 1 articles before the pipeline stops iterating |
| `INCLUDE_TIER3` | `false` | Set to `true` to show low-signal articles in the briefing |
| `OPENROUTER_MODEL` | `anthropic/claude-haiku-4.5` | Default model for scheduled runs (overrides config.js) |

---

## Setting up your own RSSHub (after the workshop)

During the workshop you're using my RSSHub instance. If you want to keep running your own briefing after we're done, you'll need your own — or you're welcome to keep using mine for a while, just let me know.

RSSHub is an open-source tool that converts all kinds of websites (Twitter/X included) into RSS feeds. The quickest way to run it is on [Railway](https://railway.app):

1. Sign up at [railway.app](https://railway.app)
2. Deploy the [DIYgod/RSSHub](https://docs.rsshub.app/deploy/railway) template (~€3–5/month)
3. In your Railway project, set the `TWITTER_AUTH_TOKEN` and `TWITTER_CT0` environment variables (instructions below)
4. Update your `RSSHUB_INSTANCE` secret in GitHub to point to your Railway URL

**Getting the Twitter auth cookies**

RSSHub uses your own Twitter session to fetch feeds. To get the values:

1. Log in to [x.com](https://x.com) in your browser
2. Open DevTools (F12) → **Application** → **Cookies** → `https://x.com`
3. Copy the values for `auth_token` and `ct0`
4. Set them as `TWITTER_AUTH_TOKEN` and `TWITTER_CT0` in your Railway project's Variables tab

These cookies expire after roughly 30 days. When Twitter accounts stop appearing in your briefing, that's why — just repeat the steps above to refresh them.

---

## Troubleshooting

**The run failed right away**
→ Check that `OPENROUTER_API_KEY` is added as a *secret* (not a variable). Open the failed run and expand the "Run briefing" step to read the actual error.

**Everything is Tier 3 / "LLM scoring skipped"**
→ The API key is wrong, expired, or out of credit. Check at [openrouter.ai/keys](https://openrouter.ai/keys). Also double-check the model name is a valid OpenRouter ID.

**The briefing runs but the articles seem off-topic**
→ `core_focus` and `tier_1` in `report_profile.yaml` are too vague. Name specific institutions, geographies, or datasets. Also make sure your feeds actually cover your topic.

**Dashboard says "Token rejected" or Generate button gives a permissions error**
→ The GH_PAT has expired or is missing a permission. Make sure you created a fine-grained token (not a classic one) with **Contents**, **Actions**, and **Variables** all set to **Read and write**, scoped to your repo. Generate a new one following Step 6.

**Dashboard says "Failed to load sources" or shows nothing**
→ The dashboard auto-detects your username and repo from the GitHub Pages URL, so this usually means you're not on the Pages URL yet (e.g. you opened `index.html` as a local file). Open the dashboard via `https://YOUR-USERNAME.github.io/Consult-Workshop` instead. If that still fails, check that GitHub Pages is deployed (Actions tab → Deploy Dashboard run should be green).

**Dashboard gives a 404**
→ Go to Settings → Pages and confirm the source is set to **GitHub Actions** (not a branch). Check the Actions tab for a Deploy run.

**Twitter accounts stopped showing up**
→ The RSSHub auth cookies expired. See [Setting up your own RSSHub](#setting-up-your-own-rsshub-after-the-workshop) → Getting the Twitter auth cookies.

## Syncing updates

If I push improvements to this base repo, you can pull them into your fork by clicking **Sync fork → Update branch** on your fork's main page. If you've edited `config/report_profile.yaml` or `config/sources.yaml`, GitHub will flag merge conflicts — resolve them to keep your customisations.
