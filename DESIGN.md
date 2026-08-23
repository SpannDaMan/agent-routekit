# Local Model Route Planner Design Authority

This file is the implementation authority for the Local Model Route Planner display identity and public repository surfaces. Brand meaning and rights constraints live in [BRAND.md](BRAND.md).

## Core visual idea

The mark represents three candidate routes entering a gate, one route clearing the gate, and a small verification turn at the exit. The silhouette should read as a compact route junction first and a subtle check-shaped path second.

## Mark acceptance criteria

- Canvas: square, built on a 24-unit grid.
- Safe area: keep all live geometry inside the central 18 units.
- Primary stroke: rounded, 2.4 units at the 24-unit source grid.
- Nodes: three equal circles, each 2.8 units in diameter.
- Route: no more than three bends and no decorative micro-lines.
- Corners: round line caps and joins.
- Small-size rule: at 16 px, reduce to the main route and three nodes; never add a wordmark inside the icon.

## Color tokens

| Token | Value | Use |
| --- | --- | --- |
| `routekit.deepNavy` | `#06235D` | primary structure, text, and dark surfaces |
| `routekit.signalBlue` | `#0183E0` | selected route and plugin brand color |
| `routekit.electricCyan` | `#09CEFC` | verified exit or status accent |
| `routekit.cloudWhite` | `#F8FAFC` | light surface and approved source background |
| `routekit.slate` | `#64748B` | secondary text |

## Typography

- Repository and docs: system sans or Inter when available.
- Code and receipt examples: a platform monospace stack.
- Product name styling: “Local Model Route Planner.” Keep `agent-routekit` only for stable machine identifiers and legacy asset custody.
- The icon contains no generated text.

## Plugin-page assets

- `icon.png`: 512×512 transparent PNG with a large, safe-fill mark for composer and compact plugin surfaces.
- `logo.png`: 1024×1024 PNG with the transparent mark on a light surface.
- `logo-dark.png`: 1024×1024 PNG with the transparent mark on a night surface.
- `screenshot1.png`: 1600×900 PNG showing a sanitized routing receipt and the product promise.
- `Agent RouteKit Transparent Master 220826.png`: accepted transparent derivative, verified by `Logo Generation Manifest 220826.json` and its paired extraction receipt.
- PNG delivery files are deterministic resize or layout derivatives of that master. The repository intentionally carries no locally reconstructed SVG master.

## Layout and elevation

- Use generous negative space and one focal mark.
- Tiles use a 22% corner radius with no simulated device frame.
- Avoid drop shadows on the mark. A tile may use a restrained 1 px border.
- Never use glossy 3D, glassmorphism, fake depth, or a busy background.

## Accessibility and fit

- Maintain at least 4.5:1 contrast for text and at least 3:1 for meaningful non-text graphics where applicable.
- Inspect the mark at 16, 24, 32, 64, 128, and 512 px.
- Preserve a clear outer margin of at least 12% of the canvas.
- No route segment may disappear on either the light or dark asset.

## Do

- Keep the route silhouette clear before adding color.
- Use signal blue for selection and electric cyan for the verified exit within the deep-navy/glacial-blue family.
- Rebuild exact labels and receipt content in deterministic production assets.

## Do not

- Use more than two brand colors in the mark.
- Use third-party product glyphs, trademarked swirl shapes, or a generic sparkle.
- Render text through the image model.
- redraw, trace, recolor, inpaint, or reconstruct the canonical transparent master locally.
