# Brain Relay design

## 1. Purpose and density
Brain Relay is a local task handoff workspace for people continuing work across conversations. Use compact, readable forms, restrained surfaces and first-class dark mode. No decorative gradients or remote assets.

## 2. Color and semantics
`static/tokens.css` is the only color source, with the `--relay-*` prefix. Light tokens are declared on `:root, [data-theme="light"]`; dark mode overrides the same names. Information uses text, text-2 or text-3. Status always includes words. The light primary button uses the darker primary-text value for small white text; its WCAG contrast is 5.74:1. Light text-3 uses #606D83, which yields 4.62:1 on hover surfaces (the original #626F86 yielded 4.48:1). Both pairs are verified by the local test. No chart colors or charts are used in this Alpha.

## 3. Typography
System sans-serif for prose, monospace for timestamps, IDs and output text. Font sizes, spacing, radius, shadows and motion use tokens. Heading text balances; prose uses pretty wrapping.

## 4. Components
The live `/styleguide` renders both themes with the real stylesheet. Components: `.relay-panel`, `.relay-btn`, `.relay-input`, `.relay-badge`, `.relay-note`, `.relay-error`, `.relay-empty`, `.relay-mono`, `.relay-muted`. Reuse these class names as a public interface. Show errors beside the action or fields. Disabled model controls explain why they are disabled.

## 5. Layout
All pages extend `base.html`. The editor and handoff column align at the start; both collapse to one column under 960px. No page-level horizontal overflow. The first working page, `templates/index.html`, is the sample for future pages.

## 6. Depth
Surface borders and a subtle card shadow separate panels. In dark mode the card shadow is disabled. No popup or floating overlay is needed; destructive edits use native confirmation dialogs, which supply keyboard focus handling.

## 7. Rules
Render user content with textContent or input values, never innerHTML. No CDN, remote fonts, literal component colors, positive tabindex, click handlers on noninteractive elements, or paste interception. Static assets use content-hash URLs.

## 8. Responsive and accessible behavior
Desktop and mobile layouts are supported. Visible keyboard focus, properly labeled fields, local errors, status announcements and reduced-motion behavior are required. The primary workflow needs no animation. Both themes must pass text contrast checks on actual used surfaces.

## 9. Verification
Run `python -m pytest`. `tests/test_design.py` checks text contrast in both themes and rejects literal colors outside tokens, remote assets and unsafe interaction patterns. Browser QA also checks rendered colors, both theme layouts, mobile width, actual fetch contracts, hostile HTML rendered as text, and exact download contents.
