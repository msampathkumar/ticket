# Vendored frontend dependencies

The Web UI loads no third-party code from the network. Each library is a pinned, unmodified upstream build named `<lib>-<version>.min.js`.

| File | Version | Upstream source | sha256 |
| --- | --- | --- | --- |
| `tailwindcss-play-3.4.17.min.js` | 3.4.17 | `https://cdn.tailwindcss.com/3.4.17` | `176e894661aa9cdc9a5cba6c720044cbbf7b8bd80d1c9a142a7c24b1b6c50d15` |
| `lucide-1.57.0.min.js` | 1.57.0 | npm `lucide@1.57.0` `dist/umd/lucide.min.js` | `c397c5299c5eb529d3523d9224f88ed9dcf147e5dd3456373b5e1e06fcd724c4` |
| `sortable-1.15.2.min.js` | 1.15.2 | npm `sortablejs@1.15.2` `Sortable.min.js` | `ca68430703c4f5960e90735867c6e94d29b5a3de37107d8100e5a301007e9e6e` |
| `marked-15.0.12.min.js` | 15.0.12 | npm `marked@15.0.12` `marked.min.js` | `3e7e7d7feb3e5d58cb6c804f68ab5c24cc7e5eb6270fd6e5cbb9124739217d0c` |
| `purify-3.4.17.min.js` | 3.4.17 | npm `dompurify@3.4.17` `dist/purify.min.js` | `cd37898f9782adf54820c413191b5691803f0f137c799d6edcfd38523b4c2c31` |

## Tailwind

`tailwindcss-play-3.4.17.min.js` is the Tailwind Play CDN runtime: it compiles utility classes in the browser, including classes built dynamically in `js/*.js`, and reads `tailwind.config` from `index.html`. It is not published to npm, so the hash is taken from the versioned CDN URL. A precompiled CSS build would be smaller and faster but needs a Node build step and a content scan that can miss dynamic class names.

## Updating a library

1. Download the exact version (for npm packages: `npm pack <pkg>@<version>` and copy the file listed above).
2. Check it matches jsDelivr: `curl -s https://cdn.jsdelivr.net/npm/<pkg>@<version>/<path> | shasum -a 256`.
3. Add the new file, update the `<script>` tag in `index.html`, update this table, and delete the old file.
