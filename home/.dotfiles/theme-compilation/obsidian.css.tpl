/* Author: sk */

.theme-dark, .theme-light {
  /* Core colors */
  --background-primary: {{ background }};
  --background-primary-alt: {{ background }};
  --background-secondary: {{ background }};
  --background-secondary-alt: {{ background }};
  --text-normal: {{ foreground }};

  /* Colors overrides */
  --color-red: {{ red }}; /*red*/
  --color-green: {{ green }}; /*green*/
  --color-yellow: {{ yellow }}; /*yellow*/
  --color-blue: {{ blue }}; /*blue*/
  --color-orange: {{ orange }};
  --color-cyan: {{ cyan }};
  --color-pink: {{ magenta }};
  --color-purple: {{ magenta }}; /*magenta*/
  
  /* Selection colors */
  --text-selection: {{ lighter_background }};

  /* Border color */
  --background-modifier-border: {{ muted }};

  /* Semantic heading colors */
  --text-title-h1: {{ red }};
  --text-title-h2: {{ green }};
  --text-title-h3: {{ yellow }};
  --text-title-h4: {{ blue }};
  --text-title-h5: {{ cyan }};
  --text-title-h6: {{ magenta }};

  /* Links and accents */
  --text-link: {{ blue }};
  --text-accent: {{ accent }};
  --text-accent-hover: {{ accent }};
  --interactive-accent: {{ accent }};
  --interactive-accent-hover: {{ accent }};

  /* Muted text */
  --text-muted: color-mix(in srgb, {{ foreground }} 70%, transparent);
  --text-faint: color-mix(in srgb, {{ foreground }} 55%, transparent);

  /* Code */
  --code-normal: {{ cyan }};
  --code-background: {{ dark_background }}; /*darker or lighter of bg*/
  --code-keyword: {{ red }};
  --code-string: {{ green }};
  --code-number: {{ yellow }};
  --code-operator: {{ blue }};
  --code-def: {{ blue }};
  --code-variable: {{ yellow }};

  /* Errors and success */
  --text-error: {{ red }};
  --text-error-hover: {{ red }};
  --text-success: {{ green }};

  /* Tags */
  --tag-color: {{ cyan }};
  --tag-background: {{ muted }};

  /* Graph */
  --graph-line: {{ muted }};
  --graph-node: {{ accent }};
  --graph-node-focused: {{ blue }};
  --graph-node-tag: {{ cyan }};
  --graph-node-attachment: {{ green }};
}

/* Headers */
.cm-header-1, .markdown-rendered h1 { color: var(--text-title-h1); }
.cm-header-2, .markdown-rendered h2 { color: var(--text-title-h2); }
.cm-header-3, .markdown-rendered h3 { color: var(--text-title-h3); }
.cm-header-4, .markdown-rendered h4 { color: var(--text-title-h4); }
.cm-header-5, .markdown-rendered h5 { color: var(--text-title-h5); }
.cm-header-6, .markdown-rendered h6 { color: var(--text-title-h6); }

/* Code blocks */
.markdown-rendered code {
  color: {{ cyan }};
}

/* Syntax highlighting
.cm-s-obsidian span.cm-keyword { color: {{ red }}; }
.cm-s-obsidian span.cm-string { color: {{ green }}; }
.cm-s-obsidian span.cm-number { color: {{ yellow }}; }
.cm-s-obsidian span.cm-comment { color: {{ muted }}; }
.cm-s-obsidian span.cm-operator { color: {{ blue }}; }
.cm-s-obsidian span.cm-def { color: {{ blue }}; } */

/* Links */
.markdown-rendered a {
  color: var(--text-link);
}

/* Blockquotes */
.markdown-rendered blockquote {
  border-left-color: {{ accent }};
}

/* Active elements */
.workspace-leaf.mod-active .workspace-leaf-header-title {
  color: var(--interactive-accent);
}

.nav-file-title.is-active {
  color: var(--interactive-accent);
}

/* Search results */
.search-result-file-title {
  color: var(--interactive-accent);
}

/* Callout Tip */
.callout[data-callout="tip"] {
  --callout-color: {{ accent }};
  --callout-icon: lucide-flame; /*change icon*/
}

.vertical-tabs-container select, .vertical-tabs-container button:not(.mod-cta), .vertical-tabs-container button.mod-cta {
  background-color: var(--code-background);
  color: var(--text-normal);
