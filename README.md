# QIDI Box Display Fix for Fluidd (QIDI X-Max 4 firmware 01.01.07.01, Plus 4 firmware 2.1.1)

**Current version: `0.9.3` (pre-release, still being tested).** Always download the file from the [release](https://github.com/ThorSc/qidi-max4-plus4-fluidd-box-patch/releases) with the **highest version number** (all current versions are pre-releases). See the [CHANGELOG](CHANGELOG.md) for what changed and what has been tested.

> [!WARNING]
> **Use at your own risk. No warranty of any kind.**
>
> This is an unofficial, community-made patch. It is **not** made, endorsed, or supported by QIDI, the Fluidd project, or Anthropic. The author provides it "as is" and **cannot guarantee that it works on your printer, and accepts no responsibility or liability** for any damage, data loss, failed prints, or voided warranty that may result from using it.
>
> You modify a file on your printer. Read the whole guide first, **make a backup**, and only continue if you are comfortable with that. If you are unsure, do not do it.
>
> Only try this while the printer is **idle** (not printing).

### Which file is for my printer?

| Printer | Firmware | File in the release | File name on the printer |
|---|---|---|---|
| QIDI X-Max 4 | 01.01.07.01 | `index-DlFvHGAh.js` | `index-DlFvHGAh.js` |
| QIDI X-Plus 4 | 2.1.1 | `plus4/index-BHXUyR-O.js` (in the release it is listed as `index-BHXUyR-O.js`) | `index-BHXUyR-O.js` |

Use only the file for your printer. The Plus 4 build and the Max 4 build were each tested by the author on one printer. Other models and firmware versions are untested.

---

## Table of contents

1. [Summary (technical)](#1-summary-technical)
2. [Step-by-step guide (for everyone)](#2-step-by-step-guide-for-everyone)
3. [Troubleshooting](#3-troubleshooting)
4. [For advanced users: rebuilding the patch](#4-for-advanced-users-rebuilding-the-patch)
5. [License and credits](#5-license-and-credits)

---

## 1. Summary (technical)

### Symptom

**X-Max 4:** after updating to firmware **01.01.07.01**, the QIDI Box card in the Fluidd web interface no longer shows the correct filament information. Colors are missing (transparent), material and vendor are empty or shown as `?`, and the print-start dialog that maps slicer extruders to box slots can fail. In addition, the **Load**, **Unload**, **Uninstall**, and **RFID re-read** buttons in the box card do nothing, and **Unload** is always disabled.

**X-Plus 4 (firmware 2.1.1):** the box card of the bundled Fluidd (v1.30.4) shows only part of the data, and it uses the old busy and loaded-slot rules. The Plus 4 still stores the slot data in the old number format, so this patch mainly makes the box card read the already resolved data from `multi_color_controller` and use the same button logic as on the Max 4.

### Root cause (Max 4)

The new firmware changed the format of the per-slot values stored in `save_variables` (`saved_variables.cfg`). The bundled Fluidd build (v1.30.5, `assets/index-DlFvHGAh.js`) still expects the old format:

| Variable | Old format (Fluidd expects) | New format (firmware 01.01.07.01) |
|---|---|---|
| `color_slotN` | integer ID, resolved through `[colordict]` in `officiall_filas_list.cfg` | list with the hex value, e.g. `['228332']` |
| `filament_slotN` | integer, resolved as section `[filaN]` in `officiall_filas_list.cfg` | string ID, e.g. `'QFG00'` |
| `vendor_slotN` | integer, resolved through `[vendor_list]` | unchanged (integer) |

Fluidd runs `parseInt()` on these values, so `['228332']` becomes the number `228332` (no match in `colordict`) and `'QFG00'` becomes `NaN` (no match in the filament list). The new IDs (`QFxxx`) are not present in `officiall_filas_list.cfg`, which still only contains `[fila1]…[fila50]`. Their definitions are shipped in `/home/qidi/QIDI_Client/resource/filament_config/filament-<nozzle>.json`, which is outside every Moonraker file root and therefore not reachable from Fluidd.

The Max 4 firmware also **renamed the G-code commands** that the box card sends. The old commands are still accepted by Klipper but silently do nothing on the Max 4. On the Plus 4 2.1.1 the old `E_LOAD` and `E_UNLOAD` still work (the display uses them), and the new Load/Unload/Uninstall commands work there as well. The commands below were read from the printer display with the Moonraker console history (`/server/gcode_store`):

| Box card button | Fluidd sends (old) | Firmware 01.01.07.01 (display) |
|---|---|---|
| RFID re-read | `RFID_READ SLOT=slot2` | `READ_RFID SLOT=2` (Plus 4 2.1.1: the display still sends `RFID_READ SLOT=slotN`; `READ_RFID` is accepted but ignored) |
| Load | `E_LOAD slot=2` | `LOAD_FILAMENT_CONTROL SLOT=2` |
| Unload | `E_UNLOAD slot=2` | `UNLOAD_FILAMENT_CONTROL SLOT=2` |
| Uninstall | `E_BOX slot=2` | `EJECT_FILAMENT_CONTROL SLOT=2` |

Finally, `box_extras.b_endstop_state`, `e_endstop_state`, and `box_button_state` are **no longer reported**. Fluidd used `b_endstop_state` together with `last_load_slot` to decide which slot is loaded, so Unload was never enabled. The firmware now reports the loaded slot as `box_extras.loaded_slot` (e.g. `slot2`; `slot16` means the external spool position). All of this (resolved names and colors of every slot, the end stop, the loaded slot, the busy state, and the external spool) is also available in the Moonraker object `multi_color_controller`, which exists on the Max 4 (01.01.07.01) and on the Plus 4 (2.1.1) with the same structure.

Starting a `.3mf` file from Fluidd fails when the file does not contain plate 1: Fluidd does not send a plate index, the firmware assumes plate 1 and cannot find `shadow_native_plate_1.gcode`. If the file metadata has no `used_extruders`, Fluidd also skips the slot-mapping dialog and silently maps the tool to the slot with the same number (T0 to slot 0).

### What the patch changes

The patch modifies only the minified Fluidd bundle (`assets/index-DlFvHGAh.js` on the Max 4, `assets/index-BHXUyR-O.js` on the Plus 4). One script builds both files:

- **Colors:** `color_slotN` is read raw (list or string) and converted to `#RRGGBB`. The old `colordict` lookup is kept as a fallback for legacy integer IDs.
- **Material / type / vendor:** the `filament-0.2/0.4/0.6/0.8.json` data (ID, name, type, vendor) is **embedded** in the bundle, one list per nozzle size. At runtime the list is chosen from `configfile.settings.extruder.nozzle_diameter` (fallback: 0.4). The legacy numeric `fila<N>` entries stay as the fallback for older firmware.
- **Data source:** name, vendor, color, and type of every slot and of the external spool are read from `multi_color_controller` (already resolved by the firmware). If that object is missing, `box_extras.boxes[].filament_info[]` and finally the old `save_variables` path are used.
- **Print start:** the plate index of `.3mf` files is sent with the start (read from the ZIP directory with two small range requests to the page origin); the slot-mapping dialog also opens when the metadata has no `used_extruders` (the tools come from `preset_colours`); an unknown filament ID no longer throws; with the box switched off the end stop values are taken from `multi_color_controller` or the filament sensor.
- **Write-back:** changing color or material in the box card writes the format of the firmware. Max 4: `color_slotN` as `['RRGGBB']` and `filament_slotN` as `'ID'`. Plus 4: numbers (for example `filament_slotN = 39` and a color from the printer's color table).
- **Button commands:** Load, Unload, and Uninstall send the new commands (table above) whenever the printer lists them (Max 4 and Plus 4). The RFID re-read button sends `READ_RFID SLOT=<n>` on the Max 4 and `RFID_READ SLOT=slot<n>` on the Plus 4 (decided by the data format of the slots).
- **Loaded slot / button enablement:** a slot counts as loaded when `loaded_slot` (from `multi_color_controller` or `box_extras`) equals that slot. If the firmware still reports `b_endstop_state` in `box_extras`, the old rule is used. So Load is disabled and Unload enabled for the loaded slot, and the reverse for all other occupied slots.
- **Busy state:** the buttons are disabled while `operation.box_button_state`, `box_extras.box_button_state`, or `task.flow_id` is set.
- **Plus 4 (firmware 2.1.1):** a separate file `plus4/index-BHXUyR-O.js` is part of the release. Only colors from the printer's color table and materials from its old list can be set there. The Plus 4 firmware opens plain G-code only (no `.3mf`), so the plate-index part is not used.

### Test status

| Item | Status |
|---|---|
| JavaScript syntax of the patched bundle (parsed in a browser) | Verified |
| Nozzle-based list selection logic (0.2 / 0.4 / 0.6 / 0.8 / unknown) | Verified (isolated test) |
| **Max 4:** color and material display for occupied slots | Reported working by one user (slots 0, 2, 3 correct) |
| Slot not detected by the printer (`runout_button = 1`) | Displayed as empty, which matches the printer state (expected, not a bug) |
| Writing color/material from the box card (`SAVE_VARIABLE` format) | Reported working (values saved in the same format as the firmware writes them) |
| Load / Unload / Uninstall buttons | Reported working and in sync with the printer display |
| Button enablement based on `loaded_slot` | Reported working (Load and Unload enabled as expected) |
| RFID re-read button (`READ_RFID`, Max 4) | Reported working |
| **Plus 4 (2.1.1, one printer):** display of slots, names, colors | Reported working by the author |
| **Plus 4:** Load / Unload / Uninstall with the new commands | Reported working (console history confirms `LOAD_FILAMENT_CONTROL`, `UNLOAD_FILAMENT_CONTROL`, `EJECT_FILAMENT_CONTROL`) |
| **Plus 4:** writing color and material (numbers), printer display follows | Reported working |
| **Plus 4:** RFID re-read (`RFID_READ`) for slot 0 and slot 1 | Reported working (console history confirms the command) |
| **Plus 4:** print start from Fluidd, Spoolman | **Not tested** |
| Firmware picks up color/material changes made in Fluidd | Reported working (printer display shows the new values immediately) |
| Starting a `.3mf` file from Fluidd (plate index) | Observed working on the Max 4 with 0.9.2: plate index `7` is sent (console history), the print started and ran for hours |
| Print-start slot-mapping dialog | Observed on the Max 4 with 0.9.2: the mapping was written to `value_t0` and the print started with that slot (loaded slot matches). Whether the preselected slot was the best match was not checked. |
| Load / Unload / Uninstall / RFID re-read on the Max 4 with 0.9.2, `task.flow_id` as busy signal | Reported working by the author |
| Print start with the box switched off (Max 4) | **Not tested** (checked only by calculation with live printer data) |
| Spoolman integration (with the box card and the print start) | **Not tested** (the author will test this separately) |
| "Box Settings" switches (auto reload, RFID on insert, RFID on startup) | Reported working, in sync with the printer display settings |

> [!NOTE]
> **Testing is ongoing.** The items marked "Not tested" are still being tested by the author. This summary and the patched file will be updated as soon as there are results. Please check back for newer versions before you apply the patch.

### Known limitations

- **Spoolman may skip the slot-mapping dialog (unconfirmed, based on reading the Fluidd code):** if Spoolman is connected and *Show spool selection dialog on print start* is enabled (the Fluidd default), Fluidd shows only the Spoolman dialog and starts the print directly. According to the code, the box slot-mapping dialog is then skipped, and the previously saved mapping (`value_t0`, `value_t1`, …) is used. This has **not been confirmed on a printer yet**. If it happens, it is original Fluidd behavior and not caused by the patch. After starting a print, check `value_t0` (and `value_t1`, …) with the Moonraker query `/printer/objects/query?save_variables`. Workaround: switch that option off in the Fluidd settings (Spoolman), or set the mapping by hand in the console, e.g. `SAVE_VARIABLE VARIABLE=value_t0 VALUE="'slot3'"`.
- **`.3mf` files with a plate other than 1:** since 0.9.2 the plate index is sent, so the print starts. The file metadata that Moonraker creates for such files is incomplete (thumbnails are missing, no `used_extruders`). That is why the slot-mapping dialog uses `preset_colours` and `filament_type` as the tools. For files with several colors that are not all used, tools that the model does not use may be offered too; assign them a slot or the print stays blocked.
- **Busy state:** whether the buttons are really disabled during a long box operation (`box_button_state` or `task.flow_id`) has not been tested. Do not click repeatedly.
- **Vendor list:** `vendor_slotN` is still an integer index (`0 = Generic`, `1 = QIDI`). Third-party vendors may be labeled incorrectly in the vendor dropdown. The card display prefers `vendor_str` from the firmware.
- **Static list:** the filament list is embedded. If QIDI adds new IDs, rebuild the patch (see [section 4](#4-for-advanced-users-rebuilding-the-patch)). Unknown IDs still display via the firmware fallback, but will be missing from the material dropdown.
- **Nozzle selection** relies on `nozzle_diameter` in `printer.cfg` matching the installed nozzle.
- Any firmware update that replaces the Fluidd files will undo the patch.
- Applies to exactly two builds: Fluidd **v1.30.5**, `assets/index-DlFvHGAh.js` (Max 4, firmware 01.01.07.01) and Fluidd **v1.30.4**, `assets/index-BHXUyR-O.js` (Plus 4, firmware 2.1.1). Other builds will not match. Other firmware versions and other models (for example the Q2) are untested.
- **Plus 4:** the firmware does not report `task.flow_id` or `box_button_state` for the old display commands, so the buttons are not disabled while the display itself runs a box operation. Do not click repeatedly. Only plain `.gcode` files can be printed (no `.3mf`).

> [!NOTE]
> These limitations reflect the current state of testing. The author continues to test, and this summary and the patched file will be updated accordingly. If a newer version is published, the checksums below will change as well.

### Versions and file checksums (SHA-256)

Each patched file carries a version number (see the [CHANGELOG](CHANGELOG.md)). It is written in the first line of the file and available as `window.__qidiBoxPatch` in the browser console. The file name cannot be changed, because Fluidd loads it by that name.

| File | SHA-256 |
|---|---|
| Original `index-DlFvHGAh.js` (QIDI_MAX4 repo, Fluidd v1.30.5) | `178b2e076d3a75716819ee13f9ea1f0c92e536546c8b2adafde8632f6723710c` |
| Original `index-BHXUyR-O.js` (Plus 4, firmware 2.1.1, Fluidd v1.30.4) | `4770bade9c2154fc1f44b3650746bc855eb008e6376f1d24820db59eb541ed59` |
| Patched `index-DlFvHGAh.js` (Max 4) and `plus4/index-BHXUyR-O.js` (Plus 4) | See `patched/SHA256SUMS`, `patched/plus4/SHA256SUMS` (in the release: `SHA256SUMS` and `SHA256SUMS-plus4`), and the notes of the matching [release](https://github.com/ThorSc/qidi-max4-plus4-fluidd-box-patch/releases) |

---

## 2. Step-by-step guide (for everyone)

**What this does:** you replace one file on your printer with a corrected version. The old file is saved first, so you can always go back.

**This guide covers both printers.** Wherever you see `<FILE>`, use the file name for your printer:

| Printer | `<FILE>` | Expected Fluidd version (`.version`) |
|---|---|---|
| QIDI X-Max 4 (firmware 01.01.07.01) | `index-DlFvHGAh.js` | `v1.30.5` |
| QIDI X-Plus 4 (firmware 2.1.1) | `index-BHXUyR-O.js` | `v1.30.4` |

Do **not** put the Max 4 file on a Plus 4 or the other way round.

**You need:**

- A computer on the same network as your printer (Windows, Mac, or Linux)
- The printer's IP address (shown on the printer's screen under network settings, or in your router)
- The printer's login for file transfer (SSH/SFTP). Look up the correct user name and password in QIDI's official documentation or support. **Do not share these credentials with anyone.**
- About 15-20 minutes

> [!IMPORTANT]
> Make sure the printer is **not printing** and no print is queued.

### Step 1: Download the patched file

1. Open the [release list](https://github.com/ThorSc/qidi-max4-plus4-fluidd-box-patch/releases) of this repository and pick the release with the **highest version number** (the top entry).
2. Under **Assets**, download **`<FILE>`** for your printer. Keep the file name exactly as it is. (Optionally also download the matching checksum file for step 8: `SHA256SUMS` for the Max 4, `SHA256SUMS-plus4` for the Plus 4.)
3. Save it somewhere easy to find, for example your Desktop.
4. Note the **version number** of the release (for example `0.9.3`).

### Step 2: Install a file transfer program

Pick one:

- **Windows:** [WinSCP](https://winscp.net) (free)
- **Mac / Linux:** [Cyberduck](https://cyberduck.io) (free), or use the built-in `scp` command in the terminal

The steps below use WinSCP. Other programs work similarly.

### Step 3: Connect to the printer

1. Start WinSCP.
2. Set **File protocol** to `SFTP`.
3. Enter your printer's **IP address** as the **Host name** (port 22).
4. Enter the **user name** and **password** for your printer, then click **Login**.
5. If a security warning about an unknown host appears, this is normal the first time. Check that the IP address is your printer's, then click **Yes** or **Accept**.

### Step 4: Find the Fluidd folder

You are looking for the folder that contains a file called **`<FILE>`** inside a folder called **`assets`**.

The easiest way is to search from a terminal on the printer. In WinSCP use **Commands > Open Terminal** (or connect with any SSH program) and run:

```bash
find / -name "<FILE>" -path "*assets*" 2>/dev/null
```

It prints one or more paths, for example `/home/qidi/fluidd/assets/<FILE>` (the folder on your printer may differ). **Write down the path.**

> [!CAUTION]
> **Nothing was found?** Then your printer uses a different Fluidd build, and this patch is **not** meant for it. **Stop here.** Do not rename or copy files to make it fit.

### Step 5: Check that it is the right version

In the same terminal, replace `/home/qidi/fluidd` with the folder from step 4 (the part before `/assets`):

```bash
cat /home/qidi/fluidd/.version
```

It should print **`v1.30.5`** on the Max 4 or **`v1.30.4`** on the Plus 4 (see the table at the top of this guide). If it shows something else, stop here.

### Step 6: Make a backup (do not skip this)

Still in the terminal (use your own path from step 4):

```bash
cp /home/qidi/fluidd/assets/<FILE> /home/qidi/fluidd/assets/<FILE>.backup
```

Check that the backup exists:

```bash
ls -l /home/qidi/fluidd/assets/ | grep "<FILE>"
```

You should see two lines: `<FILE>` and `<FILE>.backup`.

> [!TIP]
> Also copy `<FILE>.backup` to your computer for safekeeping (drag it from the right-hand WinSCP panel to the left).

### Step 7: Upload the patched file

1. In WinSCP, open the folder from step 4 (the `assets` folder) in the **right-hand** panel.
2. In the **left-hand** panel, open the folder where you saved the patched file.
3. Drag **`<FILE>`** from the left to the right.
4. When asked whether to overwrite the existing file, click **Yes**.

*(Command-line alternative from your computer, with your own user name, IP, and path:)*

```bash
scp <FILE> USER@PRINTER_IP:/home/qidi/fluidd/assets/<FILE>
```

### Step 8 (optional): Verify the upload

In the printer terminal:

```bash
sha256sum /home/qidi/fluidd/assets/<FILE>
```

Compare the result with the checksum in the matching checksum file of the release (`SHA256SUMS` or `SHA256SUMS-plus4`) (or in the release notes). It must be identical. If not, upload again.

### Step 9: Clear your browser cache

Fluidd keeps old files in the browser. Without this step you will still see the old behavior.

1. Open Fluidd in your browser.
2. Press **Ctrl + F5** (Windows/Linux) or **Cmd + Shift + R** (Mac).
3. If nothing changes, open your browser's developer tools (F12), go to **Application > Storage**, click **Clear site data**, and reload the page.

You do **not** need to restart the printer.

### Step 10: Check the result

1. Open the **QIDI Box** card in Fluidd.
2. Slots that hold filament should now show the correct **color**, **material**, and **vendor** (on the Plus 4 the names come from the firmware).
3. A slot that the printer does not detect (for example because the filament is not pushed in far enough) is shown as empty (`?`). That is the printer's own status and not caused by the patch.
4. To see which patch version is installed, run this on the printer (use your own path from step 4):

   ```bash
   head -n 1 /home/qidi/fluidd/assets/<FILE>
   ```

   It should print something like `/* QIDI Box patch for Fluidd - patch version 0.9.3 */`. Alternatively, press **F12** in the browser, open the **Console**, and enter `window.__qidiBoxPatch`.

> [!NOTE]
> Please test **Load**, **Unload**, and **Uninstall** only when the printer is idle, and stay next to the printer. They move filament and may heat the nozzle, just like the same functions on the printer display.

### How do I know if there is a newer version?

1. Check your installed version (step 10, point 4).
2. Open the [release list](https://github.com/ThorSc/qidi-max4-plus4-fluidd-box-patch/releases) and compare the highest version number there with yours.
3. If the release has a **higher** number, repeat steps 1-9 with the new file. Your backup from step 6 can be replaced by a new one.
4. Read the [CHANGELOG](CHANGELOG.md) to see what is new. Versions below `1.0.0` are pre-releases.

### How to undo the patch

If anything looks wrong, restore the backup. In the printer terminal (use your own path):

```bash
cp /home/qidi/fluidd/assets/<FILE>.backup /home/qidi/fluidd/assets/<FILE>
```

Then clear your browser cache again (step 9).

> [!NOTE]
> A QIDI firmware update will probably replace the Fluidd files and remove the patch. You can simply repeat this guide afterward, **if** the file name and Fluidd version are unchanged. Newer firmware may need a new patch version.

---

## 3. Troubleshooting

| Problem | What to try |
|---|---|
| Nothing changed after uploading | Clear the browser cache again (step 9). Try a private/incognito window. Check the checksum (step 8). |
| `find` prints nothing | Your Fluidd build is different. Stop here. This patch is not for it. |
| `.version` is not `v1.30.5` (Max 4) or `v1.30.4` (Plus 4) | Stop here. This patch is not for it. |
| Permission denied when uploading | Log in with the correct printer user. Do not use `sudo` unless you know what you are doing. |
| Box card is blank or Fluidd looks broken | Restore the backup (see [How to undo the patch](#how-to-undo-the-patch)) and clear the cache. |
| A slot shows `?` or empty although filament is inserted | The printer reports the slot as empty. Push the filament in until it triggers the slot sensor, or check the sensor. You can see the state with `http://PRINTER_IP:7125/printer/objects/query?box_stepper%20slot1` (`runout_button: 0` means filament detected). |
| Plus 4: I cannot pick a color or material that I know | The Plus 4 firmware only knows its own color table and old material list (numeric IDs). Other values cannot be stored. |
| Wrong material list for my nozzle | The list is chosen from `nozzle_diameter` in `printer.cfg`. Make sure it matches your installed nozzle. |
| Load / Unload buttons are grayed out | Unload is only enabled for the slot that the printer reports as loaded (`box_extras.loaded_slot`). Check it with `http://PRINTER_IP:7125/printer/objects/query?box_extras`. `slot16` means nothing from the box is loaded. |
| A button does nothing | Check the console history right after the click: `http://PRINTER_IP:7125/server/gcode_store?count=20`. The command should read `LOAD_FILAMENT_CONTROL SLOT=<n>` (or `UNLOAD_...`, `EJECT_...`). For RFID it should read `READ_RFID SLOT=<n>` on the Max 4 and `RFID_READ SLOT=slot<n>` on the Plus 4. If you see `E_LOAD`, `E_UNLOAD`, or `E_BOX`, the old file is still loaded (clear the cache). |
| Plus 4: RFID re-read does nothing | The spool needs a QIDI RFID tag. The console history must show `RFID_READ SLOT=slot<n>`. If it shows `READ_RFID`, the Max 4 file is installed by mistake. |

When reporting an issue, please include your firmware version, the output of `cat .version` from step 5, and a screenshot of the box card.

---

## 4. For advanced users: rebuilding the patch

`patch_qidi_box.py` regenerates the patched bundle from the **original** bundle and the QIDI filament definition files. Use it if QIDI adds new filament IDs, or to audit exactly what changes.

Requirements: Python 3. No extra packages.

```bash
python patch_qidi_box.py --version 0.9.3 <original index.js> <output index.js> \
    filament-0.2.json filament-0.4.json filament-0.6.json filament-0.8.json
```

The same command works for both printers. Use the original `index-DlFvHGAh.js` of the Max 4 (Fluidd v1.30.5) or the original `index-BHXUyR-O.js` of the Plus 4 (Fluidd v1.30.4) as input, and keep the file name for the output. The script asserts its anchors and aborts if the bundle does not match.

`--version` sets the patch version (`MAJOR.MINOR.PATCH`). It is written into the first lines of the output, and a `SHA256SUMS` file is created next to the output.

- The JSON files come from `/home/qidi/QIDI_Client/resource/filament_config/` on the printer (copy them with SFTP). The nozzle size is read from the file name (`filament-<nozzle>.json`).
- The script asserts that every replacement matches the original **exactly the expected number of times**. If a different Fluidd build changes the minified code, it aborts instead of writing a broken file.
- Only ID, name, type, and vendor are embedded. Temperatures and drying settings are ignored.
- The script prints a warning if the same ID has different data within one nozzle file.

Before deploying, you can syntax-check the result by loading it in a browser as a script (a parse error will show in the console).

---

## 5. License and credits

- [Fluidd](https://github.com/fluidd-core/fluidd) is licensed under **GPL-3.0**. The patched file is a modified version of a Fluidd build and is therefore distributed under the same license. This repository is licensed under **GPL-3.0** as well (see [LICENSE](LICENSE)). This is not legal advice.
- The original bundles come from the QIDI MAX4 firmware repository (Fluidd v1.30.5) and from the Plus 4 firmware 2.1.1 (Fluidd v1.30.4).
- Filament names and IDs originate from QIDI's own filament definition files. All trademarks belong to their respective owners.
- This project is **not affiliated with** QIDI Technology, the Fluidd project, or Anthropic.
- The analysis and patch were developed with the help of Claude (Anthropic) and tested on one X-Max 4 and one X-Plus 4 so far. Findings were derived from firmware data shared by that user, not from official documentation.

**No warranty. Use at your own risk.** See the warning at the top of this document.
