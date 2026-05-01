// =============================================================================
// DASHBOARD CONFIGURATION
// Edit these values after forking. Everything else is automatic.
//
// OWNER           : your GitHub username (e.g. 'jsmith')
// REPO            : the name of your forked repository
// DASHBOARD_TITLE : shown in the browser tab and page header
// =============================================================================

const OWNER           = 'your-github-username';
const REPO            = 'Consult-Workshop';
const DASHBOARD_TITLE = 'My Briefing Dashboard';

// =============================================================================
// AVAILABLE MODELS
// The model with isDefault: true is used for scheduled (daily) runs.
// You can add, remove, or reorder entries — keep the same object shape.
//
// To find more models: go to https://openrouter.ai/models, pick one you like,
// and copy its model ID (the string that looks like 'provider/model-name').
// Paste it here as a new entry. costIn/costOut are per million tokens —
// handy for comparing costs in the dashboard, but won't break anything if wrong.
//
// Note: some models need to be explicitly enabled on your OpenRouter account
// before you can use them. If a run fails with a 401 or model error, check
// your OpenRouter dashboard at https://openrouter.ai/settings/credits.
// =============================================================================

const MODELS = [
  { id: 'anthropic/claude-haiku-4.5',  label: 'Claude Haiku 4.5',  costIn: 0.25, costOut: 1.25, isDefault: true },
  { id: 'anthropic/claude-sonnet-4.6', label: 'Claude Sonnet 4.6', costIn: 3,    costOut: 15   },
  { id: 'google/gemma-4-31b-it',       label: 'Gemma 4 31B',       costIn: 0.13, costOut: 0.38 },
  { id: 'deepseek/deepseek-v3.2',      label: 'DeepSeek V3.2',     costIn: 0.25, costOut: 0.38 },
];
