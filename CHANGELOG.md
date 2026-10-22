# Changelog

All notable changes to this patch are listed here. Newest version first.

Version numbers follow `MAJOR.MINOR.PATCH`:

- `PATCH` (0.9.**1**): small fix, no extra steps for you
- `MINOR` (0.**10**.0 / 1.**1**.0): new or improved functionality
- `MAJOR` (**2**.0.0): larger change that may need extra steps
- Versions below `1.0.0` are **pre-releases** (still being tested).

Every release lists its SHA-256 checksum in the release notes and in `patched/SHA256SUMS`.

---

## [0.9.0] - Pre-release

First published version. Targets **Fluidd v1.30.5** (`assets/index-DlFvHGAh.js`) as shipped with QIDI X-Max 4 firmware **01.01.07.01**.

### Added

- Color display: `color_slotN` is read as a raw value (`['RRGGBB']`) and shown as `#RRGGBB`. The old `colordict` lookup remains as a fallback.
- Material, type, and vendor display for the new string filament IDs (e.g. `QFG00`). The lists from `filament-0.2/0.4/0.6/0.8.json` are embedded, one list per nozzle size, selected by `nozzle_diameter` (fallback 0.4).
- Fallback to the firmware's own data (`box_extras.boxes[].filament_info`) for IDs that are not in the embedded list.
- Print-start dialog no longer fails on unknown filament IDs.
- Write-back of color and material from the box card in the new format.
- Patch version is visible: first line of the file, and `window.__qidiBoxPatch` in the browser console.

### Tested

- JavaScript syntax of the patched bundle (parsed in a browser).
- Nozzle-based list selection logic (isolated test).
- Color and material display for occupied slots on one X-Max 4 (reported working).

### Not tested yet

- Writing color/material from the box card.
- Print-start slot mapping dialog end-to-end.
- Load / Unload buttons.

### Known issues

- Load / Unload buttons may stay disabled or misbehave: the fields `b_endstop_state`, `e_endstop_state`, and `box_button_state` are missing from `box_extras` on firmware 01.01.07.01. Not addressed yet.
- `vendor_slotN` is still an integer index (`0 = Generic`, `1 = QIDI`); third-party vendors may be labeled incorrectly in the vendor dropdown.
- Testing is ongoing. This changelog and the patched file will be updated as results come in.
