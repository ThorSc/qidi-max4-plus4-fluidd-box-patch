# QIDI Box Display Fix for Fluidd (QIDI X-Max 4, firmware 01.01.07.01)

> [!WARNING]
> **Use at your own risk. No warranty of any kind.**
>
> This is an unofficial, community-made patch. It is **not** made, endorsed, or supported by QIDI, the Fluidd project, or Anthropic. The author provides it "as is" and **cannot guarantee that it works on your printer, and accepts no responsibility or liability** for any damage, data loss, failed prints, or voided warranty that may result from using it.
>
> You modify a file on your printer. Read the whole guide first, **make a backup**, and only continue if you are comfortable with that. If you are unsure, do not do it.
>
> Only try this while the printer is **idle** (not printing).

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

After updating the QIDI X-Max 4 to firmware **01.01.07.01**, the QIDI Box card in the Fluidd web interface no longer shows the correct filament information. Colors are missing (transparent), material and vendor are empty or shown as `?`, and the print-start dialog that maps slicer extruders to box slots can fail.

### Root cause

The new firmware changed the format of the per-slot values stored in `save_variables` (`saved_variables.cfg`). The bundled Fluidd build (v1.30.5, `assets/index-DlFvHGAh.js`) still expects the old format:

| Variable | Old format (Fluidd expects) | New format (firmware 01.01.07.01) |
|---|---|---|
| `color_slotN` | integer ID, resolved through `[colordict]` in `officiall_filas_list.cfg` | list with the hex value, e.g. `['228332']` |
| `filament_slotN` | integer, resolved as section `[filaN]` in `officiall_filas_list.cfg` | string ID, e.g. `'QFG00'` |
| `vendor_slotN` | integer, resolved through `[vendor_list]` | unchanged (integer) |

Fluidd runs `parseInt()` on these values, so `['228332']` becomes the number `228332` (no match in `colordict`) and `'QFG00'` becomes `NaN` (no match in the filament list). The new IDs (`QFxxx`) are not present in `officiall_filas_list.cfg`, which still only contains `[fila1]…[fila50]`. Their definitions are shipped in `/home/qidi/QIDI_Client/resource/filament_config/filament-<nozzle>.json`, which is outside every Moonraker file root and therefore not reachable from Fluidd.

### What the patch changes

The patch modifies only the minified Fluidd bundle `assets/index-DlFvHGAh.js`:

- **Colors:** `color_slotN` is read raw (list or string) and converted to `#RRGGBB`. The old `colordict` lookup is kept as a fallback for legacy integer IDs.
- **Material / type / vendor:** the `filament-0.2/0.4/0.6/0.8.json` data (ID, name, type, vendor) is **embedded** in the bundle, one list per nozzle size. At runtime the list is chosen from `configfile.settings.extruder.nozzle_diameter` (fallback: 0.4). The legacy numeric `fila<N>` entries are replaced.
- **Fallback to firmware data:** if an ID is not in the embedded list, name, color, and vendor are taken from `box_extras.boxes[].filament_info[]`, which the firmware reports itself. The vendor is always taken from `vendor_str` when available.
- **Print-start dialog:** an unknown filament ID no longer throws (`?.type`).
- **Write-back:** changing color or material in the box card now writes `color_slotN` as `['RRGGBB']` and `filament_slotN` as `'ID'`.

### Test status

| Item | Status |
|---|---|
| JavaScript syntax of the patched bundle (parsed in a browser) | Verified |
| Nozzle-based list selection logic (0.2 / 0.4 / 0.6 / 0.8 / unknown) | Verified (isolated test) |
| Color and material display for occupied slots on a real X-Max 4 | Reported working by one user (slots 0, 2, 3 correct) |
| Slot not detected by the printer (`runout_button = 1`) | Displayed as empty, which matches the printer state (expected, not a bug) |
| Writing color/material from the box card (`SAVE_VARIABLE` format) | **Not tested** |
| Print-start slot mapping dialog | **Not tested** end-to-end |
| Load / Unload buttons | **Not tested, likely affected** (see below) |

> [!NOTE]
> **Testing is ongoing.** The items marked "Not tested" are still being tested by the author. This summary and the patched file will be updated as soon as there are results. Please check back for newer versions before you apply the patch.

### Known limitations

- **Load / Unload buttons:** Fluidd enables them based on `box_extras.b_endstop_state`, `e_endstop_state`, and `box_button_state`. These fields are **absent** in the status reported by firmware 01.01.07.01, so the buttons may stay disabled or behave incorrectly. This patch does not address that.
- **Vendor list:** `vendor_slotN` is still an integer index (`0 = Generic`, `1 = QIDI`). Third-party vendors may be labeled incorrectly in the vendor dropdown. The card display prefers `vendor_str` from the firmware.
- **Static list:** the filament list is embedded. If QIDI adds new IDs, rebuild the patch (see [section 4](#4-for-advanced-users-rebuilding-the-patch)). Unknown IDs still display via the firmware fallback, but will be missing from the material dropdown.
- **Nozzle selection** relies on `nozzle_diameter` in `printer.cfg` matching the installed nozzle.
- Any firmware update that replaces the Fluidd files will undo the patch.
- Applies to this exact build: Fluidd **v1.30.5**, `assets/index-DlFvHGAh.js`. Other builds will not match.

> [!NOTE]
> These limitations reflect the current state of testing. The author continues to test, and this summary and the patched file will be updated accordingly. If a newer version is published, the checksums below will change as well.

### File checksums (SHA-256)

| File | SHA-256 |
|---|---|
| Original `index-DlFvHGAh.js` (QIDI_MAX4 repo, Fluidd v1.30.5) | `178b2e076d3a75716819ee13f9ea1f0c92e536546c8b2adafde8632f6723710c` |
| Patched `index-DlFvHGAh.js` (this repo, `patched/`) | `2b17262f0bd37c2e18f06b1af61f75b8d78f0ca7cbc25543260ef7e5d1f253b0` |

---

## 2. Step-by-step guide (for everyone)

**What this does:** you replace one file on your printer with a corrected version. The old file is saved first, so you can always go back.

**You need:**

- A computer on the same network as your printer (Windows, Mac, or Linux)
- The printer's IP address (shown on the printer's screen under network settings, or in your router)
- The printer's login for file transfer (SSH/SFTP). Look up the correct user name and password in QIDI's official documentation or support. **Do not share these credentials with anyone.**
- About 15-20 minutes

> [!IMPORTANT]
> Make sure the printer is **not printing** and no print is queued.

### Step 1: Download the patched file

1. Open the `patched` folder of this repository.
2. Download **`index-DlFvHGAh.js`**. Keep the file name exactly as it is.
3. Save it somewhere easy to find, for example your Desktop.

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

You are looking for the folder that contains a file called **`index-DlFvHGAh.js`** inside a folder called **`assets`**.

The easiest way is to search from a terminal on the printer. In WinSCP use **Commands > Open Terminal** (or connect with any SSH program) and run:

```bash
find / -name "index-DlFvHGAh.js" -path "*assets*" 2>/dev/null
```

It prints one or more paths, for example `/home/qidi/fluidd/assets/index-DlFvHGAh.js`. **Write down the path.**

> [!CAUTION]
> **Nothing was found?** Then your printer uses a different Fluidd build, and this patch is **not** meant for it. **Stop here.** Do not rename or copy files to make it fit.

### Step 5: Check that it is the right version

In the same terminal, replace `/home/qidi/fluidd` with the folder from step 4 (the part before `/assets`):

```bash
cat /home/qidi/fluidd/.version
```

It should print **`v1.30.5`**. If it shows something else, stop here.

### Step 6: Make a backup (do not skip this)

Still in the terminal (use your own path from step 4):

```bash
cp /home/qidi/fluidd/assets/index-DlFvHGAh.js /home/qidi/fluidd/assets/index-DlFvHGAh.js.backup
```

Check that the backup exists:

```bash
ls -l /home/qidi/fluidd/assets/ | grep DlFvHGAh
```

You should see two lines: `index-DlFvHGAh.js` and `index-DlFvHGAh.js.backup`.

> [!TIP]
> Also copy `index-DlFvHGAh.js.backup` to your computer for safekeeping (drag it from the right-hand WinSCP panel to the left).

### Step 7: Upload the patched file

1. In WinSCP, open the folder from step 4 (the `assets` folder) in the **right-hand** panel.
2. In the **left-hand** panel, open the folder where you saved the patched file.
3. Drag **`index-DlFvHGAh.js`** from the left to the right.
4. When asked whether to overwrite the existing file, click **Yes**.

*(Command-line alternative from your computer, with your own user name, IP, and path:)*

```bash
scp index-DlFvHGAh.js USER@PRINTER_IP:/home/qidi/fluidd/assets/index-DlFvHGAh.js
```

### Step 8 (optional): Verify the upload

In the printer terminal:

```bash
sha256sum /home/qidi/fluidd/assets/index-DlFvHGAh.js
```

The result should start with **`2b17262f0bd37c2e`**. If not, upload again.

### Step 9: Clear your browser cache

Fluidd keeps old files in the browser. Without this step you will still see the old behavior.

1. Open Fluidd in your browser.
2. Press **Ctrl + F5** (Windows/Linux) or **Cmd + Shift + R** (Mac).
3. If nothing changes, open your browser's developer tools (F12), go to **Application > Storage**, click **Clear site data**, and reload the page.

You do **not** need to restart the printer.

### Step 10: Check the result

1. Open the **QIDI Box** card in Fluidd.
2. Slots that hold filament should now show the correct **color**, **material**, and **vendor**.
3. A slot that the printer does not detect (for example because the filament is not pushed in far enough) is shown as empty (`?`). That is the printer's own status and not caused by the patch.

> [!NOTE]
> Please test **Load** and **Unload** only when the printer is idle, and be ready to stop it. These buttons may not work properly on firmware 01.01.07.01 (see [known limitations](#known-limitations)).

### How to undo the patch

If anything looks wrong, restore the backup. In the printer terminal (use your own path):

```bash
cp /home/qidi/fluidd/assets/index-DlFvHGAh.js.backup /home/qidi/fluidd/assets/index-DlFvHGAh.js
```

Then clear your browser cache again (step 9).

> [!NOTE]
> A QIDI firmware update will probably replace the Fluidd files and remove the patch. You can simply repeat this guide afterward, **if** the file name and Fluidd version are unchanged.

---

## 3. Troubleshooting

| Problem | What to try |
|---|---|
| Nothing changed after uploading | Clear the browser cache again (step 9). Try a private/incognito window. Check the checksum (step 8). |
| `find` prints nothing | Your Fluidd build is different. Stop here. This patch is not for it. |
| `.version` is not `v1.30.5` | Stop here. This patch is not for it. |
| Permission denied when uploading | Log in with the correct printer user. Do not use `sudo` unless you know what you are doing. |
| Box card is blank or Fluidd looks broken | Restore the backup (see [How to undo the patch](#how-to-undo-the-patch)) and clear the cache. |
| A slot shows `?` or empty although filament is inserted | The printer reports the slot as empty. Push the filament in until it triggers the slot sensor, or check the sensor. You can see the state with `http://PRINTER_IP:7125/printer/objects/query?box_stepper%20slot1` (`runout_button: 0` means filament detected). |
| Wrong material list for my nozzle | The list is chosen from `nozzle_diameter` in `printer.cfg`. Make sure it matches your installed nozzle. |
| Load / Unload buttons are grayed out | Known limitation (see above). Not fixed by this patch. |

When reporting an issue, please include your firmware version, the output of `cat .version` from step 5, and a screenshot of the box card.

---

## 4. For advanced users: rebuilding the patch

`patch_qidi_box.py` regenerates the patched bundle from the **original** bundle and the QIDI filament definition files. Use it if QIDI adds new filament IDs, or to audit exactly what changes.

Requirements: Python 3. No extra packages.

```bash
python patch_qidi_box.py <original index.js> <output index.js> \
    filament-0.2.json filament-0.4.json filament-0.6.json filament-0.8.json
```

- The JSON files come from `/home/qidi/QIDI_Client/resource/filament_config/` on the printer (copy them with SFTP). The nozzle size is read from the file name (`filament-<nozzle>.json`).
- The script asserts that every replacement matches the original **exactly the expected number of times**. If a different Fluidd build changes the minified code, it aborts instead of writing a broken file.
- Only ID, name, type, and vendor are embedded. Temperatures and drying settings are ignored.
- The script prints a warning if the same ID has different data within one nozzle file.

Before deploying, you can syntax-check the result by loading it in a browser as a script (a parse error will show in the console).

---

## 5. License and credits

- [Fluidd](https://github.com/fluidd-core/fluidd) is licensed under **GPL-3.0**. The patched file is a modified version of a Fluidd build and is therefore distributed under the same license. This repository is licensed under **GPL-3.0** as well (see [LICENSE](LICENSE)). This is not legal advice.
- The original bundle comes from the QIDI MAX4 firmware repository (Fluidd v1.30.5).
- Filament names and IDs originate from QIDI's own filament definition files. All trademarks belong to their respective owners.
- This project is **not affiliated with** QIDI Technology, the Fluidd project, or Anthropic.
- The analysis and patch were developed with the help of Claude (Anthropic) and tested on a single X-Max 4 so far. Findings were derived from firmware data shared by that user, not from official documentation.

**No warranty. Use at your own risk.** See the warning at the top of this document.
