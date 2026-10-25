# Status and test plan

Working document. State as of 2026-10-25 (first written 2026-10-23). Written so that work can resume without the chat history. Nothing on branch `feature/print-start` has been pushed.

**2026-10-25:** release 0.9.2 (Max 4 only) is prepared locally on the branch: `patched/index-DlFvHGAh.js` is bit-identical to the test build that runs on the Max 4 (SHA-256 `b15431e3…2848f20`), CHANGELOG and README are updated. Waiting for the author's explicit approval to merge into `main`, push, tag, and publish. All printers were printing on 2026-10-25, so the planned tests (section 4) are still open.

## 1. Where things stand

| Item | State |
|---|---|
| Public repository | `main` at `e1cdc8c`, releases `v0.9.0` and `v0.9.1` (both pre-releases) with `index-DlFvHGAh.js` and `SHA256SUMS` |
| Local branch | `feature/print-start`, 12 commits ahead of `main` (including this document), **not pushed** |
| Rule | Do not push, merge into `main`, publish a release, or change anything public without an explicit "yes" from the author |
| Test builds (git-ignored, folder `test_builds/`) | `max4/index-DlFvHGAh.js` SHA-256 `b15431e3d0cd25fb5223d418f584634a9b2c431b1f492da7ee3d3382b2848f20`, `plus4/index-BHXUyR-O.js` SHA-256 `97e68cafcef74f99639ac0cc0f3a1393facd9ed9491c9dd7f8f931defd7ea1f8` (patch version `0.9.2`) |
| Source filament lists | `fila_lists/filament-0.2/0.4/0.6/0.8.json` (git-ignored, QIDI data, local only) |

Rebuild (run from the repository root; the original bundles come from the firmware folders of the Max 4 and the Plus 4):

```bash
python patched/patch_qidi_box.py --version 0.9.2 <original index.js> test_builds/<max4|plus4>/<same file name> \
    fila_lists/filament-0.2.json fila_lists/filament-0.4.json fila_lists/filament-0.6.json fila_lists/filament-0.8.json
```

The file name must stay the name that the printer's `index.html` loads (`index-DlFvHGAh.js` on the Max 4, `index-BHXUyR-O.js` on the Plus 4).

## 2. What the branch adds compared with `main` (release 0.9.1)

1. Plate index for `.3mf` print starts (the file of the author has only `plate_7`, the firmware assumed plate 1). The plate list is read with range requests to the page origin, not to the API origin (CORS).
2. The slot-mapping dialog also opens when the file metadata has no `used_extruders` (before, Fluidd silently mapped T0 to slot 0 and started the print).
3. Data layer: `multi_color_controller` as the source for names, vendor, color, type, the external spool, busy state, and loaded slot. The old `save_variables` path stays as the fallback.
4. One patch for the Max 4 bundle (Fluidd v1.30.5) and the Plus 4 bundle (Fluidd v1.30.4): regex anchors for the names that differ.
5. Writing color and material in the format of the firmware (text IDs on the Max 4, legacy numbers on the Plus 4).
6. New commands (`LOAD/UNLOAD/EJECT_FILAMENT_CONTROL`, `READ_RFID`) when the printer reports them, old commands otherwise.
7. `isOkPrinter` with the box switched off, and `task.flow_id` as a busy signal.
8. Analysis document `docs/fluidd-fork-analysis.md`.

## 3. Evidence level

| Item | Level |
|---|---|
| Release 0.9.1 items (color/material display, write-back, Load/Unload/Uninstall, RFID button, Box Settings switches) | Tested on the Max 4 by the author |
| Plate index fix (`PLATEINDEX="7"`, print starts) | Tested on the Max 4 (print was cancelled right after the start) |
| Items 1 and 2 above (plate index, slot-mapping dialog) | **Observed on the Max 4 on 2026-10-25** (console history: `SAVE_VARIABLE value_t0`, `SDCARD_PRINT_FILE … PLATEINDEX="7"`; the print ran for hours and the loaded slot matches `value_t0`). Preselection of the best slot was not checked. |
| Items 3 to 7 above, other than the two above | Only simulated in a browser with live read-only data of the three printers. Not tested on the printers. The Max 4 console history only shows an `EJECT_FILAMENT_CONTROL SLOT=2` sent from Fluidd. |
| Plus 4 build | **Not deployed on any printer** (the Plus 4 printers still serve the original bundle) |
| Spoolman skipping the slot-mapping dialog | Only read from the code, **unconfirmed** |
| Plus 4 behavior of the new commands | **Unknown** (listed in `HELP`, never run) |
| `task.flow_id` during a load | **Unknown** (empty when idle) |

## 4. Test plan for 2026-10-24 (after the prints have finished)

Rules: only when the printer is idle and nobody is printing. Back up the original file first. Stay next to the printer for everything that moves filament or heats the nozzle. Hard-reload the browser (private window is safest) and check `window.__qidiBoxPatch` shows `0.9.2`.

### 4.1 Max 4 (deploy `test_builds/max4/index-DlFvHGAh.js`)

1. Look only: box card (colors, names, empty slot, external spool), humidity.
2. Print start dialog: start the `.3mf` file. The dialog must appear (not silently start). Expected preselection for the black PETG: slot `1C`. Close it without confirming. If the Spoolman dialog appears first, do not start from it, switch it off in the Fluidd settings (Spoolman).
3. Real print start: confirm the dialog and check at once that `value_t0` is `slot2` (query `save_variables`) and that the right slot is loaded. Cancel if wrong.
4. Load, Unload, Uninstall, RFID: after a Load the Unload button must be enabled for that slot. Watch whether `task.flow_id` is set during the load and empty afterwards (query `multi_color_controller`). If it stays set, the buttons stay disabled: report it, the signal will be removed.
5. Box switched off: print start with an external spool must not be blocked wrongly.

### 4.2 Plus 4 (deploy `test_builds/plus4/index-BHXUyR-O.js`, one printer first)

1. Look only: slots, names, colors from `multi_color_controller` (the slot data of the printer is still in the old number format).
2. Buttons with the **new** commands: Load, Unload, Uninstall, RFID re-read. First check the console history afterwards (`/server/gcode_store`) for the command that was sent.
3. Write color and material: values must be written as numbers (for example `filament_slot0 = 39`), and the printer display must show the change. Only colors from the printer's color table and materials from its old list can be set.
4. For comparison with the unpatched Fluidd: whether the old commands (`E_LOAD`, `RFID_READ`) still do anything on firmware 2.1.1.
5. `.3mf` files are not supported by the Plus 4 firmware (Klipper opens plain G-code only); only plain `.gcode` is expected to work.

### 4.3 What to report

For each step: worked / did not work, and for failures a screenshot, the browser console (F12), and the last lines of `/server/gcode_store?count=30`.

## 5. Open decisions

- Publish `0.9.2` (merge the branch, update README and CHANGELOG, tag, release) after the tests, only on explicit approval.
- Push the branch (not needed for the release; keeps a backup on GitHub).
- Q2 support: the Q2 bundle very likely has the same code as the Max 4 bundle (the anchors of a third-party Q2 patch match exactly once), but a Q2 tester and the bundle are needed.
- Fork prototype of the box card on top of upstream Fluidd v1.30.5, see `docs/fluidd-fork-analysis.md` section 5 to 7.
- Possible new functions that QIDI never exposed in Fluidd: drying (box and external), AI detection.

## 6. Known limitations to keep in mind

- The Plus 4 slot data is in the old number format; only `multi_color_controller` gives names there.
- The external spool vendor can be empty on a Plus 4 (no vendor ID reported).
- Metadata of `.3mf` files with a plate other than 1 is incomplete in Moonraker (thumbnails 404, no `used_extruders`); the fix works around it in Fluidd.
- Do not run scripts of third parties on a printer without reading them completely.
