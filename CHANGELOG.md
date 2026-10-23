# Changelog

All notable changes to this patch are listed here. Newest version first.

Version numbers follow `MAJOR.MINOR.PATCH`:

- `PATCH` (0.9.**1**): small fix, no extra steps for you
- `MINOR` (0.**10**.0 / 1.**1**.0): new or improved functionality
- `MAJOR` (**2**.0.0): larger change that may need extra steps
- Versions below `1.0.0` are **pre-releases** (still being tested).

Every release lists its SHA-256 checksum in the release notes and in `patched/SHA256SUMS`.

---

## [0.9.1] - Pre-release

Makes the box card buttons work again on firmware **01.01.07.01**. Update from 0.9.0 by replacing `index-DlFvHGAh.js` again (see the README).

### Fixed

- **Load, Unload, Uninstall:** the firmware renamed the commands. The buttons now send `LOAD_FILAMENT_CONTROL SLOT=<n>`, `UNLOAD_FILAMENT_CONTROL SLOT=<n>`, and `EJECT_FILAMENT_CONTROL SLOT=<n>` (as the printer display does). The old `E_LOAD`, `E_UNLOAD`, and `E_BOX` are still accepted by the firmware but do nothing.
- **RFID re-read button:** now sends `READ_RFID SLOT=<n>` (was `RFID_READ SLOT=slot<n>`).
- **Unload was always disabled:** the firmware no longer reports `box_extras.b_endstop_state`. The loaded slot is now taken from `box_extras.loaded_slot` (old rule kept as a fallback).

### Tested

- Load, Unload, and Uninstall from the Fluidd box card: reported working and in sync with the printer display (one X-Max 4).
- RFID re-read button in the Fluidd box card: reported working.
- "Box Settings" switches (auto reload, RFID on insert, RFID on startup): reported working and in sync with the printer display settings (unchanged code, still writes the `auto_*` variables).
- Writing color and material from the box card: values are saved in the same format the firmware uses, and the printer display shows the new values immediately.

### Not tested yet

- Print-start slot mapping dialog.
- Spoolman integration (the author will test this separately).
- Starting a print from Fluidd: fails in the author's environment for a `.3mf` file (see known issues). Whether plain `.gcode` files work has not been checked yet.

### Known issues

- `box_button_state` is not reported by the firmware, so the buttons are not disabled while an operation is running.
- Unconfirmed (based on reading the Fluidd code, not yet seen on a printer): if Spoolman is connected and *Show spool selection dialog on print start* is on, Fluidd may skip the box slot-mapping dialog (original Fluidd behavior). See the README.
- Starting a `.3mf` file from Fluidd fails in the author's environment on firmware 01.01.07.01 with `3MF processing error: [Errno 2] No such file or directory: '/home/qidi/printer_data/.temp/shadow_native_plate_1.gcode'`. The error comes from the firmware, not from this patch, and is not fixed here (under investigation). Workaround: start from the printer display or export plain `.gcode`.
- Testing is ongoing. This changelog and the patched file will be updated as results come in.

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
