"""Patches the Fluidd bundle (index-*.js) for the new QIDI Box data format.

usage:
  python patch_qidi_box.py --version X.Y.Z <original index.js> <output index.js> \\
      <filament-0.2.json> [<filament-0.4.json> ...]

Each JSON file must be named filament-<nozzle>.json. The lists are embedded per
nozzle size; at runtime the bundle picks one using
configfile.settings.extruder.nozzle_diameter (fallback: 0.4).

Besides the patched bundle the script writes a SHA256SUMS file next to it.
"""
import sys, json, re, hashlib, os
args = sys.argv[1:]
if len(args) < 4 or args[0] != "--version":
    sys.exit(__doc__)
version = args[1]
if not re.fullmatch(r"\d+\.\d+\.\d+", version):
    sys.exit("Version must look like 1.2.3")
src, dst, *jsons = args[2:]
s = open(src, encoding="utf-8").read()
qfd = {}
for jsn in jsons:
    m = re.search(r"filament-(\d+\.\d+)\.json$", jsn.replace("\\", "/"))
    if not m:
        sys.exit("File name must be filament-<nozzle>.json: " + jsn)
    lst = qfd.setdefault(m.group(1), {})
    for name, v in json.load(open(jsn, encoding="utf-8")).items():
        n = name[5:] if name.startswith("QIDI ") else name
        e = [n, v["type"], v["filament_vendor"]]
        if lst.setdefault(v["filament_id"], e) != e:
            print("Conflict", m.group(1), v["filament_id"], lst[v["filament_id"]], e)
# Print start for .3mf files: the firmware (Moonraker printer.print.start) takes an optional "plateindex"
# (default "1"). A .3mf that only contains e.g. Metadata/plate_7.gcode fails with
# "shadow_native_plate_1.gcode not found" unless the right plate is passed. The plate number is read from
# the ZIP central directory with two small HTTP range requests (the whole file is not downloaded).
# The requests go to the origin of the page (nginx proxy): Fluidd may talk to Moonraker on another origin
# (port 7125), where a "Range" header needs a CORS preflight that Moonraker does not allow.
PLATE_HELPER = r'''const qbxPrintParams=async f=>{const p={filename:f};if(!/\.3mf$/i.test(f))return p;try{const get=h=>fetch("/server/files/gcodes/"+f.split("/").map(encodeURIComponent).join("/")+"?date="+Date.now(),{headers:{Range:h}}).then(async r=>{if(!r.ok)throw new Error("HTTP "+r.status);return{data:await r.arrayBuffer(),headers:{"content-range":r.headers.get("content-range")||""}}});const r=await get("bytes=-70000"),t=new Uint8Array(r.data),cr=/\/(\d+)\s*$/.exec(r.headers["content-range"]),ts=(cr?+cr[1]:t.length)-t.length,v=new DataView(t.buffer,t.byteOffset,t.byteLength);let e=-1;for(let i=t.length-22;i>=0;i--)if(v.getUint32(i,!0)===101010256){e=i;break}if(e<0)return p;const sz=v.getUint32(e+12,!0),off=v.getUint32(e+16,!0);if(!sz||sz>5e6||off===4294967295)return p;const c=off>=ts?t.subarray(off-ts,off-ts+sz):new Uint8Array((await get(`bytes=${off}-${off+sz-1}`)).data),d=new DataView(c.buffer,c.byteOffset,c.byteLength),td=new TextDecoder,pl=[];let o=0;while(o+46<=c.length&&d.getUint32(o,!0)===33639248){const n=d.getUint16(o+28,!0),x=d.getUint16(o+30,!0),m=d.getUint16(o+32,!0),q=/^Metadata\/plate_(\d+)\.gcode$/i.exec(td.decode(c.subarray(o+46,o+46+n)));q&&pl.push(+q[1]);o+=46+n+x+m}pl.length&&(p.plateindex=String(Math.min(...pl)))}catch(e){console.warn("qbx plate detection failed",e)}return p};
'''
helper = (
 '/* QIDI Box patch for Fluidd v1.30.5 - patch version ' + version + ' */\n'
 'window.__qidiBoxPatch="' + version + '";\n'
 'const qbxColor=(v,d)=>{if(Array.isArray(v))v=v[0];if(v==null||v==="")return"#00000000";const x=String(v).trim().replace(/[\'"#]/g,"");if(/^[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(x))return"#"+x.slice(0,6).toUpperCase();return(d&&d[x])||"#00000000"};\n'
 'const qbxIsLoaded=c=>{const e=c.$store.state.printer.printer.box_extras;if(!e)return!1;if(e.b_endstop_state!==void 0)return e.b_endstop_state===0&&c.variables.lastLoadSlot===c.selectIndex;return e.loaded_slot==="slot"+c.selectIndex};\n'
 'const qbxFil=' + json.dumps(qfd, separators=(",", ":"), ensure_ascii=False) + ';\n'
 'const qbxFilMerge=(d,c)=>{if(!d)return d;for(const k of Object.keys(d))/^fila\\d+$/.test(k)&&delete d[k];let n;try{n=Number(c.$store.state.printer.printer.configfile.settings.extruder.nozzle_diameter).toFixed(1)}catch(e){}const l=qbxFil[n]||qbxFil["0.4"]||Object.assign({},...Object.values(qbxFil));for(const i in l)d["fila"+i]={filament:l[i][0],type:l[i][1],vendor:l[i][2]};return d};\n'
 + PLATE_HELPER
)
edits = [
 # Colors: keep the raw value (list/hex string), no parseInt
 ('s[v]=parseInt(e[g]??"0",10)}else if(g.startsWith("filament_slot"))', 's[v]=e[g]??"0"}else if(g.startsWith("filament_slot"))', 1),
 # Filament ID is now a string (e.g. 'QFG00')
 ('n[v]=parseInt(e[g]??"0",10)}else if(g.startsWith("vendor_slot"))', 'n[v]=e[g]??"0"}else if(g.startsWith("vendor_slot"))', 1),
 # Color display
 ('C=((a=this.officialFilasListDictData)==null?void 0:a.colordict[String(this.variables.colorSlot[m])])??"#00000000"',
  'C=qbxColor(this.variables.colorSlot[m],(a=this.officialFilasListDictData)==null?void 0:a.colordict)', 1),
 ('color:((u=this.officialFilasListDictData)==null?void 0:u.colordict[this.variables.rackExtra[0]])??"#00000000"',
  'color:qbxColor(this.variables.rackExtra[0],(u=this.officialFilasListDictData)==null?void 0:u.colordict)', 1),
 ('l=o?o[this.variables.colorSlot[n]]:"#000000"', 'l=qbxColor(this.variables.colorSlot[n],o)', 1),
 # Filament list: merge the embedded list of the active nozzle
 ('setOfficiallFilasList",wn.configToDict(t))', 'setOfficiallFilasList",qbxFilMerge(wn.configToDict(t),this))', 2),
 # Fallback: name/color/vendor from box_extras.boxes[].filament_info (reported by the firmware)
 (',this.itemsCopy.push({label:v,color:C,filament:w,vendor:S,isRotating:!1})}const E=',
  ';{const _i=this.$store.state.printer.printer.box_extras?.boxes?.[Math.floor(m/4)]?.filament_info?.[m%4];_i&&(w=w||_i.filament_str||"",S=_i.vendor_str||S,C==="#00000000"&&(C=qbxColor(_i.color_rgb_str,null)))}this.itemsCopy.push({label:v,color:C,filament:w,vendor:S,isRotating:!1})}const E=', 1),
 # Avoid a crash when the ID is unknown
 ('a===this.officialFilasListDictData[l.filaIndex].type', 'a===this.officialFilasListDictData[l.filaIndex]?.type', 1),
 ('s=this.selectedValueSlot[t])==null?void 0:s.filaIndex].type', 's=this.selectedValueSlot[t])==null?void 0:s.filaIndex]?.type', 1),
 # Write-back: color as ['RRGGBB'], filament as 'ID'
 ('set selectedColor(t){const s=this.getKeyByValue(this.officialFilasListDictData.colordict,t);s&&(this.selectIndex===16?I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=color_slot16 VALUE="${s}"`):I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=color_slot${this.selectIndex} VALUE="${s}"`))',
  'set selectedColor(t){const s=String(t||"").replace("#","").toUpperCase();/^[0-9A-F]{6}$/.test(s)&&I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=color_slot${this.selectIndex} VALUE="[\'${s}\']"`)', 1),
 ('(this.selectIndex===16?I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=filament_slot16 VALUE="${s.replace("fila","")}"`):I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=filament_slot${this.selectIndex} VALUE="${s.replace("fila","")}"`))',
  'I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=filament_slot${this.selectIndex} VALUE="\'${s.replace("fila","")}\'"`)', 1),
 # Load/Unload enablement: firmware 01.01.07.01 no longer reports box_extras.b_endstop_state,
 # but reports box_extras.loaded_slot. Use the old condition when the endstop is present.
 ('this.$store.state.printer.printer.box_extras.b_endstop_state===0&&this.variables.lastLoadSlot===this.selectIndex',
  'qbxIsLoaded(this)', 2),
 # Uninstall/Load/Unload buttons: the display of firmware 01.01.07.01 sends
 # EJECT_FILAMENT_CONTROL SLOT=<n>, LOAD_FILAMENT_CONTROL SLOT=<n> and UNLOAD_FILAMENT_CONTROL SLOT=<n>.
 # E_BOX/E_LOAD/E_UNLOAD are still accepted but no longer do anything.
 ('const n=["E_BOX","E_LOAD","E_UNLOAD"];I.printerGcodeScript(`${n[t-1]} slot=${s}`)',
  'const n=["EJECT_FILAMENT_CONTROL","LOAD_FILAMENT_CONTROL","UNLOAD_FILAMENT_CONTROL"];I.printerGcodeScript(`${n[t-1]} SLOT=${s}`)', 1),
 # Print start: pass the plate index of .3mf files (see PLATE_HELPER above)
 ('async printerPrintStart(r){he("printer.print.start",{dispatch:"void",params:{filename:r}})}',
  'async printerPrintStart(r){he("printer.print.start",{dispatch:"void",params:await qbxPrintParams(r)})}', 1),
 # Firmware 01.01.07.01 renamed the RFID command and expects a numeric slot:
 # RFID_READ SLOT=slot2 -> READ_RFID SLOT=2
 ('I.printerGcodeScript(`RFID_READ SLOT=slot${t}`)', 'I.printerGcodeScript(`READ_RFID SLOT=${t}`)', 1),
]
for a, b, n in edits:
    assert s.count(a) == n, (s.count(a), a[:70])
    s = s.replace(a, b)
open(dst, "w", encoding="utf-8", newline="").write(helper + s)
with open(dst, "rb") as f:
    digest = hashlib.sha256(f.read()).hexdigest()
sums = os.path.join(os.path.dirname(os.path.abspath(dst)), "SHA256SUMS")
with open(sums, "w", encoding="utf-8", newline="\n") as f:
    f.write(digest + "  " + os.path.basename(dst) + "\n")
print("ok", "version", version, {k: len(v) for k, v in qfd.items()})
print(digest)
