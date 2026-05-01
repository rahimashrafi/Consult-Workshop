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
// See https://openrouter.ai/models for the full list and up-to-date pricing.
// Prices are per million tokens (costIn = input, costOut = output).
// =============================================================================

const MODELS = [
  { id: 'anthropic/claude-sonnet-4.6', label: 'Claude Sonnet 4.6', costIn: 3,    costOut: 15,   isDefault: true },
  { id: 'anthropic/claude-haiku-4.5',  label: 'Claude Haiku 4.5',  costIn: 0.25, costOut: 1.25 },
  { id: 'google/gemma-4-31b-it',       label: 'Gemma 4 31B',       costIn: 0.13, costOut: 0.38 },
  { id: 'deepseek/deepseek-v3.2',      label: 'DeepSeek V3.2',     costIn: 0.25, costOut: 0.38 },
];
