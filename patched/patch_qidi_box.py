"""Patches the QIDI Fluidd bundle (index-*.js) for the newer QIDI Box firmware.

Works on the bundles of the QIDI X-Max 4 (Fluidd v1.30.5, firmware 01.01.07.01) and of the
QIDI Plus 4 (Fluidd v1.30.4, firmware 1.8.2 / 2.1.1).

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

# Data layer. Newer QIDI firmware (Max 4 01.01.07.01, Plus 4 2.1.1) reports the box data in the Moonraker object
# "multi_color_controller" with already resolved names (flat keys box<N>_filament_info_<M>_*), the loaded slot and
# the busy state ("operation"). Older firmware only has save_variables with numeric IDs and the lists from
# officiall_filas_list.cfg: that path stays as the fallback.
DATA_HELPER = r'''const qbxMccBox=P=>{const m=P&&P.multi_color_controller;return m&&m.box?m:null};
const qbxSlotInfo=(P,m)=>{const n=Math.floor(m/4),k=m%4,c=qbxMccBox(P);if(c){const b=c.box,p="box"+n+"_filament_info_"+k+"_";if(b[p+"filament_id"]!==void 0)return{id:b[p+"filament_id"],name:b[p+"filament_str"],type:b[p+"filament_type"],vendor:b[p+"vendor_str"],color:b[p+"color_rgb_str"]}}const i=P?.box_extras?.boxes?.[n]?.filament_info?.[k];return i?{id:i.filament_id,name:i.filament_str,type:i.filament_type,vendor:i.vendor_str,color:i.color_rgb_str}:null};
const qbxVarsMcc=(r,o)=>{const c=qbxMccBox(r&&r.printer);if(!c)return o;const b=c.box,cnt=Math.max(o.boxCount||0,c.box_count||b.box_count||0);for(let n=0;n<cnt;n++)for(let k=0;k<4;k++){const p="box"+n+"_filament_info_"+k+"_",m=n*4+k;if(b[p+"filament_id"]!==void 0){o.filamentSlot[m]=b[p+"filament_id"];o.colorSlot[m]=b[p+"color_rgb_str"]}}const x=c.extra&&c.extra.filament_info;x&&x.filament_id!==void 0&&(o.rackExtra=[x.color_rgb_str,x.filament_id,o.rackExtra[2]]);return o};
const qbxBusy=P=>{const o=P?.multi_color_controller?.operation,e=P?.box_extras,k=P?.multi_color_controller?.task;return!!(o&&o.box_button_state||e&&e.box_button_state||k&&k.flow_id)};
const qbxEndstops=P=>{const x=P?.box_extras||{},b=qbxMccBox(P)?.box||{},f=P?.["filament_switch_sensor filament_switch_sensor"]||{};return{e:x.e_endstop_state!==void 0?x.e_endstop_state:b.e_endstop_state!==void 0?b.e_endstop_state:f.filament_detected?1:0,b:x.b_endstop_state!==void 0?x.b_endstop_state:b.b_endstop_state}};
const qbxIsLoaded=c=>{const P=c.$store.state.printer.printer,e=P.box_extras,m=qbxMccBox(P);if(e&&e.b_endstop_state!==void 0)return e.b_endstop_state===0&&c.variables.lastLoadSlot===c.selectIndex;const l=m&&m.box.loaded_slot||e&&e.loaded_slot;return l==="slot"+c.selectIndex};
const qbxNewFmt=c=>{const v=c.$store.state.printer.printer.save_variables?.variables||{};return[0,1,2,3].some(i=>typeof v["filament_slot"+i]==="string")};
const qbxHas=(c,n)=>n in(c.$store.getters["printer/getAvailableCommands"]||{});
'''

helper = (
 '/* QIDI Box patch for Fluidd - patch version ' + version + ' */\n'
 'window.__qidiBoxPatch="' + version + '";\n'
 'const qbxColor=(v,d)=>{if(Array.isArray(v))v=v[0];if(v==null||v==="")return"#00000000";const x=String(v).trim().replace(/[\'"#]/g,"");if(/^[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(x))return"#"+x.slice(0,6).toUpperCase();return(d&&d[x])||"#00000000"};\n'
 + DATA_HELPER +
 'const qbxFil=' + json.dumps(qfd, separators=(",", ":"), ensure_ascii=False) + ';\n'
 'const qbxFilMerge=(d,c)=>{if(!d)return d;let n;try{n=Number(c.$store.state.printer.printer.configfile.settings.extruder.nozzle_diameter).toFixed(1)}catch(e){}const l=qbxFil[n]||qbxFil["0.4"]||Object.assign({},...Object.values(qbxFil));for(const i in l)d["fila"+i]={filament:l[i][0],type:l[i][1],vendor:l[i][2]};return d};\n'
 + PLATE_HELPER
)

# Each edit is (old, new, expected count) or ("re", pattern, replacement function, expected count).
# The regex edits cover names that the minifier chose differently in the two bundles.
edits = [
 # Colors and filament IDs: keep the raw value (list/hex string, text ID or legacy number), no parseInt
 ('s[v]=parseInt(e[g]??"0",10)}else if(g.startsWith("filament_slot"))', 's[v]=e[g]??"0"}else if(g.startsWith("filament_slot"))', 1),
 ('n[v]=parseInt(e[g]??"0",10)}else if(g.startsWith("vendor_slot"))', 'n[v]=e[g]??"0"}else if(g.startsWith("vendor_slot"))', 1),
 # Data layer: colors and filament IDs of all slots (and the external spool) from multi_color_controller
 ('a[16]=1,{boxCount:t,colorSlot:s,filamentSlot:n,vendorSlot:i,slot:a,valueSlot:o,slotSync:l,rackExtra:c,lastLoadSlot:u}',
  'a[16]=1,qbxVarsMcc(r,{boxCount:t,colorSlot:s,filamentSlot:n,vendorSlot:i,slot:a,valueSlot:o,slotSync:l,rackExtra:c,lastLoadSlot:u})', 1),
 # Color display
 ('C=((a=this.officialFilasListDictData)==null?void 0:a.colordict[String(this.variables.colorSlot[m])])??"#00000000"',
  'C=qbxColor(this.variables.colorSlot[m],(a=this.officialFilasListDictData)==null?void 0:a.colordict)', 1),
 ('color:((u=this.officialFilasListDictData)==null?void 0:u.colordict[this.variables.rackExtra[0]])??"#00000000"',
  'color:qbxColor(this.variables.rackExtra[0],(u=this.officialFilasListDictData)==null?void 0:u.colordict)', 1),
 ('l=o?o[this.variables.colorSlot[n]]:"#000000"', 'l=qbxColor(this.variables.colorSlot[n],o)', 1),
 # Filament list: merge the embedded list of the active nozzle (keeps the legacy numeric entries)
 ("re", r'setOfficiallFilasList",(\w+)\.configToDict\(t\)\)',
  lambda m: 'setOfficiallFilasList",qbxFilMerge(' + m.group(1) + '.configToDict(t),this))', 2),
 # Box card: name, vendor and color of every slot from the firmware (multi_color_controller, else box_extras)
 ("re", r',this\.itemsCopy\.push\(\{label:v,color:C,filament:(\w+),vendor:S,isRotating:!1\}\)\}const E=',
  lambda m: ';{const _i=qbxSlotInfo(this.$store.state.printer.printer,m);_i&&(' + m.group(1) + '=_i.name||' + m.group(1)
            + ',S=_i.vendor||S,_i.color&&(C=qbxColor(_i.color,null)))}this.itemsCopy.push({label:v,color:C,filament:'
            + m.group(1) + ',vendor:S,isRotating:!1})}const E=', 1),
 # Print-start dialog: material type of a slot from the firmware, no crash when the ID is unknown
 ('t[n]={label:a,color:l,filaIndex:c}', 't[n]={label:a,color:l,filaIndex:c,type:qbxSlotInfo(this.$store.state.printer.printer,n)?.type}', 1),
 ('a===this.officialFilasListDictData[l.filaIndex].type', 'a===(l.type||this.officialFilasListDictData[l.filaIndex]?.type)', 1),
 ('this.filelabels[t]!==this.officialFilasListDictData[(s=this.selectedValueSlot[t])==null?void 0:s.filaIndex].type',
  'this.filelabels[t]!==(((s=this.selectedValueSlot[t])==null?void 0:s.type)||this.officialFilasListDictData[s?.filaIndex]?.type)', 1),
 # Busy state of the box (buttons are disabled while it works)
 ('get isOperating(){const t=this.$store.state.printer.printer.box_extras;return!(!t||!t.box_button_state)}',
  'get isOperating(){return qbxBusy(this.$store.state.printer.printer)}', 1),
 # Print start with the box switched off: the end stop values (extruder, box) are no longer reported in
 # box_extras on newer firmware. Take them from multi_color_controller / the filament sensor instead of
 # blocking the print.
 ('get isOkPrinter(){return this.enableBox===!1?this.$store.state.printer.printer.box_extras.e_endstop_state===1?this.$store.state.printer.printer.box_extras.b_endstop_state===0?',
  'get isOkPrinter(){const E=qbxEndstops(this.$store.state.printer.printer);return this.enableBox===!1?E.e===1?E.b===0?', 1),
 # Material dropdown: only the entries of the format that the firmware uses (text IDs or legacy numbers)
 ('for(const s in this.officialFilasListDictData)s.startsWith("fila")&&t.add(this.officialFilasListDictData[s].filament);return Array.from(t)}',
  'for(const s in this.officialFilasListDictData)s.startsWith("fila")&&qbxNewFmt(this)===!/^fila\\d+$/.test(s)&&t.add(this.officialFilasListDictData[s].filament);return Array.from(t)}', 1),
 # Write-back in the format the firmware uses: text IDs ['RRGGBB'] / 'QFG00', or the legacy numeric IDs
 ('set selectedColor(t){const s=this.getKeyByValue(this.officialFilasListDictData.colordict,t);s&&(this.selectIndex===16?I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=color_slot16 VALUE="${s}"`):I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=color_slot${this.selectIndex} VALUE="${s}"`))',
  'set selectedColor(t){if(qbxNewFmt(this)){const s=String(t||"").replace("#","").toUpperCase();/^[0-9A-F]{6}$/.test(s)&&I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=color_slot${this.selectIndex} VALUE="[\'${s}\']"`)}else{const s=this.getKeyByValue(this.officialFilasListDictData.colordict,t);s&&I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=color_slot${this.selectIndex} VALUE="${s}"`)}', 1),
 ('(this.selectIndex===16?I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=filament_slot16 VALUE="${s.replace("fila","")}"`):I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=filament_slot${this.selectIndex} VALUE="${s.replace("fila","")}"`))',
  'qbxNewFmt(this)===!/^fila\\d+$/.test(s)&&I.printerGcodeScript(qbxNewFmt(this)?`SAVE_VARIABLE VARIABLE=filament_slot${this.selectIndex} VALUE="\'${s.replace("fila","")}\'"`:`SAVE_VARIABLE VARIABLE=filament_slot${this.selectIndex} VALUE="${s.replace("fila","")}"`)', 1),
 # Load/Unload enablement: the loaded slot comes from loaded_slot when the endstop field is not reported
 ('this.$store.state.printer.printer.box_extras.b_endstop_state===0&&this.variables.lastLoadSlot===this.selectIndex',
  'qbxIsLoaded(this)', 2),
 # Uninstall/Load/Unload: newer firmware (display) sends EJECT/LOAD/UNLOAD_FILAMENT_CONTROL SLOT=<n>; the old
 # E_BOX/E_LOAD/E_UNLOAD are still accepted there but do nothing. Pick by the commands the printer reports.
 ('const n=["E_BOX","E_LOAD","E_UNLOAD"];I.printerGcodeScript(`${n[t-1]} slot=${s}`)',
  'const n=qbxHas(this,"LOAD_FILAMENT_CONTROL")?["EJECT_FILAMENT_CONTROL","LOAD_FILAMENT_CONTROL","UNLOAD_FILAMENT_CONTROL"]:["E_BOX","E_LOAD","E_UNLOAD"];I.printerGcodeScript(`${n[t-1]} SLOT=${s}`)', 1),
 # RFID re-read: READ_RFID SLOT=<n> on newer firmware, RFID_READ SLOT=slot<n> on older firmware (Plus 4 2.1.1 lists READ_RFID but ignores it)
 ('I.printerGcodeScript(`RFID_READ SLOT=slot${t}`)',
  'I.printerGcodeScript(qbxHas(this,"READ_RFID")&&qbxNewFmt(this)?`READ_RFID SLOT=${t}`:`RFID_READ SLOT=slot${t}`)', 1),
 # Print start without used_extruders in the file metadata (e.g. a .3mf whose only plate is not plate 1):
 # Fluidd silently mapped every tool to the same-numbered slot (T0 -> slot0) and started the print without
 # showing the slot-mapping dialog. Show the dialog instead, using preset_colours/filament_type as tools.
 ('const n=e.getFileMeta(t,s);if(((n==null?void 0:n.used_extruders)??[]).length>0)return!0;for(let i=0;',
  'const n=e.getFileMeta(t,s);if(((n==null?void 0:n.used_extruders)??[]).length>0||((n==null?void 0:n.preset_colours)??[]).length>0)return!0;for(let i=0;', 1),
 ('get usedExtruders(){var t;return((t=this.fileMeta)==null?void 0:t.used_extruders)||[]}',
  'get usedExtruders(){var t;const u=(t=this.fileMeta)==null?void 0:t.used_extruders;return u&&u.length?u:Array.from({length:((t=this.fileMeta)==null?void 0:t.preset_colours||[]).length},(c,i)=>i)}', 1),
 # Print start: pass the plate index of .3mf files (see PLATE_HELPER above)
 ("re", r'async printerPrintStart\(r\)\{(\w+)\("printer\.print\.start",\{dispatch:"void",params:\{filename:r\}\}\)\}',
  lambda m: 'async printerPrintStart(r){' + m.group(1) + '("printer.print.start",{dispatch:"void",params:await qbxPrintParams(r)})}', 1),
]
for e in edits:
    if e[0] == "re":
        _, pat, fn, n = e
        found = len(re.findall(pat, s))
        assert found == n, (found, n, pat[:80])
        s = re.sub(pat, fn, s)
    else:
        a, b, n = e
        assert s.count(a) == n, (s.count(a), n, a[:80])
        s = s.replace(a, b)
os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
open(dst, "w", encoding="utf-8", newline="").write(helper + s)
with open(dst, "rb") as f:
    digest = hashlib.sha256(f.read()).hexdigest()
sums = os.path.join(os.path.dirname(os.path.abspath(dst)), "SHA256SUMS")
with open(sums, "w", encoding="utf-8", newline="\n") as f:
    f.write(digest + "  " + os.path.basename(dst) + "\n")
print("ok", "version", version, {k: len(v) for k, v in qfd.items()})
print(digest)
