# Vendored frontend dependencies

The Web UI loads no third-party code from the network. Each library is a pinned, unmodified upstream build named `<lib>-<version>.min.js`.

| File | Version | Upstream source | sha256 |
| --- | --- | --- | --- |
| `lucide-1.57.0.min.js` | 1.57.0 | npm `lucide@1.57.0` `dist/umd/lucide.min.js` | `c397c5299c5eb529d3523d9224f88ed9dcf147e5dd3456373b5e1e06fcd724c4` |
| `sortable-1.15.2.min.js` | 1.15.2 | npm `sortablejs@1.15.2` `Sortable.min.js` | `ca68430703c4f5960e90735867c6e94d29b5a3de37107d8100e5a301007e9e6e` |
| `marked-15.0.12.min.js` | 15.0.12 | npm `marked@15.0.12` `marked.min.js` | `3e7e7d7feb3e5d58cb6c804f68ab5c24cc7e5eb6270fd6e5cbb9124739217d0c` |
| `purify-3.4.17.min.js` | 3.4.17 | npm `dompurify@3.4.17` `dist/purify.min.js` | `cd37898f9782adf54820c413191b5691803f0f137c799d6edcfd38523b4c2c31` |

## Tailwind CSS

`static/css/tailwind.css` is a prebuilt, committed Tailwind 3.4.17 stylesheet. The browser loads no Tailwind runtime, and installing tk needs no Node.

- Config: `tk_webui/tailwind.config.js` (content globs `static/index.html` and `static/js/**/*.js`, `darkMode: 'class'`, `brand` colours). Input: `tk_webui/tailwind.input.css`. Neither file ships in the package.
- Rebuild after adding or changing Tailwind classes in `index.html` or `static/js/`:

  ```bash
  scripts/build-webui-css.sh
  ```

  The script downloads the pinned standalone CLI (`tailwindcss-<platform>` from the v3.4.17 GitHub release) to `~/.cache/tk/`, checks its sha256 against the release `sha256sums.txt`, and writes the CSS. Output is left unminified: minifying rewrites colour values and merges declarations, which changed computed styles compared with the old Play runtime.
- Class names must appear as complete strings in the source (e.g. `'bg-rose-500'`, not `` `bg-${color}-500` ``), or the build will not include them. Accent colours are CSS variables in `styles.css` and need no safelist.

## Updating a library

1. Download the exact version (for npm packages: `npm pack <pkg>@<version>` and copy the file listed above).
2. Check it matches jsDelivr: `curl -s https://cdn.jsdelivr.net/npm/<pkg>@<version>/<path> | shasum -a 256`.
3. Add the new file, update the `<script>` tag in `index.html`, update this table, and delete the old file.
