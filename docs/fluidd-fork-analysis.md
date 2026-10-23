# Fluidd fork: feasibility and effort analysis

Status: working document, written on branch `feature/print-start`. Numbers come from a comparison of the QIDI Fluidd bundle with the official upstream release. Effort figures are **estimates** with a wide margin.

## 1. Question

QIDI no longer develops or supports its Fluidd fork (information from the author, not verified). Is it realistic to maintain the QIDI-specific parts ourselves, for the current firmware of the Max 4 and the Plus 4, and how much work is that?

## 2. What was compared

| Item | Source |
|---|---|
| QIDI bundle | `fluidd/assets/index-DlFvHGAh.js` from the QIDI_MAX4 firmware repository (reports itself as Fluidd v1.30.5) |
| Upstream | Official release archive `fluidd.zip` of `fluidd-core/fluidd`, tag `v1.30.5`, published 2024-10-16, 3,797,631 bytes, SHA-256 `472f5a0fca52170d3beb2232c22934a2ff993cd46c23db2b338609056ff56d8f`, main bundle `index-Dtd0i8SC.js` |
| QIDI history | The 30 `index-*.js` builds that lie side by side in the QIDI repository |

Method: sizes, file lists, string literals, translation keys in use (`$t("app.…")`), API paths, G-code commands, and Klipper objects that the code reads. Because the bundles are minified, variable names differ, and a line-by-line diff is not possible. Code that changes layout or behavior without adding texts, commands, or objects is **not** visible with these methods.

## 3. Findings

### 3.1 Size

| | Bytes |
|---|---|
| QIDI bundle (current) | 1,778,263 |
| Upstream v1.30.5 bundle | 1,720,206 |
| Difference | +58,057 |
| QIDI build without any box code (`index-BQrhHlHK.js`) | 1,741,942 |
| Box code in the current QIDI build (difference to the build above) | ≈ 36,321 (about 2 % of the bundle) |

The 30 QIDI builds grow from about 1.74 MB to 1.78 MB. QIDI therefore kept extending the box functions over time.

### 3.2 What QIDI added

| Area | Addition |
|---|---|
| Texts | 36 new translation keys in use: 26 for the box (buttons, settings, automatic reload, humidity, labels), 9 for the file dialog (print start), 1 in the settings |
| API paths | `/printer/breakheater` and `/printer/breakmacro` (custom Moonraker endpoints) |
| Klipper objects read | `box_extras`, `box_stepper slotN`, `aht20 …` (humidity), `filament_switch_sensor`, `save_variables` |
| G-code sent | `E_BOX`, `E_LOAD`, `E_UNLOAD`, `RFID_READ`, and `SAVE_VARIABLE` for slots, colors, material, vendor, `value_tN`, and the box settings |
| Components | box card, box settings, automatic reload view, humidity display, slot-mapping dialog at print start, a few icon components |
| Files | `.3mf` handling (`.gcode.3mf` preview), language `zh-TW` |

### 3.3 What QIDI removed

19 translation keys in use disappeared: managing several printers (add endpoint, API URL), several timelapse settings, and a filter for Moonraker temporary upload files. The languages `pt_BR` and `zh-HK` are missing.

### 3.4 Base version

QIDI's bundle uses slightly older libraries than the release (for example `1.15.2` instead of `1.15.3`, `1.7.4` instead of `1.7.7`, `3.1.6` instead of `3.1.7`). It was built from an upstream revision shortly before the `v1.30.5` release, not from the tag itself. This is manageable for a fork, but an exact diff against the tag is not possible.

## 4. What changed with firmware 01.01.07.01

Already handled by the patch in this repository (see `CHANGELOG.md`):

- new data formats (`color_slotN`, `filament_slotN`),
- renamed commands (`LOAD/UNLOAD/EJECT_FILAMENT_CONTROL`, `READ_RFID`),
- removed status fields (`b_endstop_state` and others; the loaded slot is now `box_extras.loaded_slot`),
- print start of `.3mf` files (`plateindex`),
- print start when the file metadata has no `used_extruders`.

This list shows how often the firmware changes the interface without notice.

## 4a. Plus 4 findings (read-only, 2026-10-23)

Sources: firmware folders 1.7.1 (repository), 1.8.2 and v2.1.1 (Fluidd folders), a configuration backup of printer QIDI4-1 (folder `1.7.3`, 2025-11-15), and live read-only queries (Moonraker `GET`) to two Plus 4 printers (QIDI4-1, QIDI4-2) while both were printing. Nothing was changed on the printers.

| Finding | Result |
|---|---|
| Fluidd bundle | Plus 4 firmware 1.8.2 and v2.1.1 ship the **same** bundle `index-BHXUyR-O.js` (SHA-256 prefix `4770bade`, Fluidd `v1.30.4`, 1,772,209 bytes). Both printers serve exactly this file. |
| Compared with the Max 4 bundle | Different build (Max 4: `v1.30.5`, 1,778,263 bytes). Both still send the **old** commands (`RFID_READ`, `E_LOAD`, `E_UNLOAD`, `E_BOX`). |
| Commands known to the Plus 4 firmware (`HELP`) | The **new** commands exist already: `READ_RFID`, `LOAD_FILAMENT_CONTROL`, `UNLOAD_FILAMENT_CONTROL`, `EJECT_FILAMENT_CONTROL`, `UPDATE_FILAMENT_INFORMATION`, `SET_ENABLE_AUTO_RELOAD`, `SET_ENABLE_RFID_READ`, `SET_ENABLE_INIT_READ_RFID`, plus per-tool `UNLOAD_T0..T15` and the object `rfid_bridge`. |
| Slot data format | **Old** format: `color_slot0 = 2`, `filament_slot0 = 39` (integer IDs). The Max 4 firmware 01.01.07.01 already uses `['228332']` and `'QFG00'`. |
| `box_extras` fields | The Plus 4 still reports `b_endstop_state`, `e_endstop_state`, `box_button_state`, and `loaded_slot`. The Max 4 no longer reports the first three. |
| Box modules | Older Plus 4 sources (folder "Optionale Qidi Box Makro Dateien") are plain Python: `box_extras.py` registers `E_LOAD`/`E_UNLOAD`/`E_BOX`, `box_stepper.py` registers `RFID_READ` with the slot name. The current firmware's versions of these files were not available. |
| Klipper / MCU | Both printers: Klipper `v0.12.0-65-g96ab9069-dirty`, MCU build 2024-03-01, box MCU `KLP_MCU_MKS_V1_1.1.1`, Moonraker API 1.4.0, nozzle 0.4. |

Interpretation:

- The Max 4 firmware (01.01.07.01) looks **ahead** of the Plus 4 firmware (2.1.1) in this transition (inference from the data formats only; the version numbers of the two product lines cannot be compared): new data format and removed fields on the Max 4, new commands but still the old data format on the Plus 4. A later Plus 4 update will probably bring the same changes.
- The patch of this repository is written for the Max 4 format. On the current Plus 4 it would **not** work as is: it replaces the legacy `fila<N>` list (numeric IDs like `39`) with the new string IDs. A single patch for both printers needs format detection (numeric IDs: keep the legacy list; string IDs: use the embedded list).
- Whether the old commands (`E_LOAD`, `RFID_READ`) still work on the current Plus 4 firmware is **not tested** (both printers were printing).

Open for the Plus 4:

- Firmware version: both printers (QIDI4-1 and QIDI4-2) run **v2.1.1** (reported by the author). This matches the bundle they serve (identical to the one in the `v2.1.1 Fluidd` folder), so the findings above describe firmware 2.1.1: new commands known, slot data still in the old format, old Fluidd.
- Test of the old Fluidd's buttons (Load, Unload, Uninstall, RFID) on an idle Plus 4.
- The contents of the archive `v2.1.1国外.rar` (needs an unpacker) to compare the Plus 4 box modules with the Max 4 repository.

## 4b. Unified data source `multi_color_controller` (live check on three printers, 2026-10-23)

The notes of the RFID Wisp project (`C:\DEV\RFIDwisp-dev`, tested on Max 4, both Plus 4 and a Q2) and a live read-only query show: the Moonraker object `multi_color_controller` is present with the same structure on the Max 4 (01.01.07.01) and on both Plus 4 (2.1.1). It carries the **already resolved** data, so no ID lists are needed:

| Content | Fields |
|---|---|
| Per slot (flat names) | `box<N>_filament_info_<M>_filament_str`, `_filament_type`, `_vendor_str`, `_color_rgb_str` (hex list), `_filament_id`, `_min_temp`, `_max_temp`, `_box_min_temp`, `_box_max_temp`, `_filament_per`, `_info_from_rfid`, `_read_rfid_state` |
| Per box | `box<N>_aht20_humidity`, `_aht20_temp`, `_box_inserted_<M>`, `_filament_inserted_<M>`, `_box_target_temp`, `_dry_state`, `_end_time`, `_is_online` |
| Global in `box` | `b_endstop_state`, `loaded_slot`, `last_load_slot`, `is_tool_change`, `auto_refill`, `box_count`, `buffer_*` |
| `operation` | `box_button_state`, `operate_state`, `active_slot` (replaces `box_extras.box_button_state` on the Max 4) |
| `extra` | the external spool (`identity: external`) with name, color, type, temperatures |
| `task` | `flow_id`, `current_queue`, `current_step`, `is_paused` (state of running box flows) |
| Settings | `enable_box`, `auto_read_rfid`, `auto_init_detect`, `auto_reload_detect`, `load_retry_num` |

Consequences:

- A single data layer for Max 4 and Plus 4 is possible: read `multi_color_controller` when present, fall back to the old `save_variables` format otherwise (RFID Wisp does exactly this). The embedded filament lists are then only needed for the material dropdown.
- The fields that disappeared from `box_extras` on the Max 4 (`b_endstop_state`, `box_button_state`) exist in `multi_color_controller` (`box.b_endstop_state`, `operation.box_button_state`).
- Older firmware versions (before the change) were only covered by unit tests in RFID Wisp; nobody had such a printer for live tests.

## 4c. Print start on the Plus 4

The Plus 4 2.1.1 sources (`virtual_sdcard.py`, `klippy_apis.py` in `X-Plus4/Firmware/v2.1.1/div`) differ from the Max 4 firmware:

- Klipper's `SDCARD_PRINT_FILE` only opens plain G-code files. There is **no 3MF handling and no plate index** (Moonraker accepts `plateindex` but does not pass it on).
- The `.3mf` error seen on the Max 4 (`shadow_native_plate_1.gcode`) therefore cannot occur on the Plus 4 2.1.1; printing `.3mf` files from Fluidd is simply not supported there.
- The plate-index change of this repository is harmless on the Plus 4 (it only acts on `.3mf` file names).

## 5. Options

| Option | Content | Effort (estimate) | Assessment |
|---|---|---|---|
| A. Keep patching the bundle | As done so far | hours to one day per change | Works today, but fragile and hard to maintain. No source, and every new QIDI build needs new replacements. |
| B. Fork of Fluidd v1.30.5 | Rebuild the QIDI functions with source code, tests, and a build | about 1.5 to 3 weeks part-time | Best maintainability. More initial work. |
| C. Separate small box page | Own page next to unmodified Fluidd | about 1 to 2 weeks | Less work, but not integrated into Fluidd. |

Rough breakdown for B:

| Task | Estimate |
|---|---|
| Build upstream v1.30.5 from source and verify it | 0.5 to 1 day |
| List all QIDI changes precisely (including layout) | 1 to 2 days |
| Rebuild box card, settings, automatic reload, humidity, print-start dialog | 5 to 8 days |
| Adapt to firmware 01.01.07.01 (mostly known from this repository) | 1 to 2 days |
| Texts in several languages | 1 to 2 days |
| Release, tests, documentation | 2 to 3 days |
| Plus 4 (only with data and a tester) | 1 to 3 days |

The bottleneck is testing on real printers, not writing the code.

## 6. Risks

- QIDI changes the firmware without notice.
- The Plus 4 is not known. Only the Max 4 repository was analyzed.
- The box modules of the firmware are compiled. Only their interface (commands and fields) is visible.
- Loading, unloading, and ejecting move filament and heat the nozzle. Errors there are not only display errors.
- A fork needs someone to maintain it permanently, and upstream Fluidd moves on.
- Fluidd is licensed under GPL-3.0, so a fork must stay open under the same license.

## 7. Recommendation

1. Finish the open tests of the patch and publish the next version.
2. Start a prototype of the box card on top of Fluidd v1.30.5. A few days of work show how cleanly the QIDI functions can be rebuilt, before a decision is made.
3. Clarify the Plus 4 as soon as someone provides data (firmware folder with the Fluidd bundle, `box_extras`, the `HELP` list, `saved_variables.cfg`) and can test.

## 8. Open points

- Plus 4: which firmware, which Fluidd bundle, same box commands?
- Who maintains an eventual fork when the next firmware appears?
- Layout changes by QIDI that this analysis cannot see.
