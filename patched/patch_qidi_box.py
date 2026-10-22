"""Patcht fluidd index-*.js fuer das neue QIDI-Box-Datenformat.
usage: python patch_qidi_box.py <original index.js> <ausgabe index.js> <filament-0.2.json> [<filament-0.4.json> ...]

Jede JSON-Datei muss filament-<Duese>.json heissen. Die Listen werden pro Duese
eingebettet; zur Laufzeit waehlt die Datei anhand von
configfile.settings.extruder.nozzle_diameter (Rueckfall: 0.4).
"""
import sys, json, re
src, dst, *jsons = sys.argv[1:]
s = open(src, encoding="utf-8").read()
qfd = {}
for jsn in jsons:
    m = re.search(r"filament-(\d+\.\d+)\.json$", jsn.replace("\\", "/"))
    if not m:
        sys.exit("Dateiname muss filament-<Duese>.json lauten: " + jsn)
    lst = qfd.setdefault(m.group(1), {})
    for name, v in json.load(open(jsn, encoding="utf-8")).items():
        n = name[5:] if name.startswith("QIDI ") else name
        e = [n, v["type"], v["filament_vendor"]]
        if lst.setdefault(v["filament_id"], e) != e:
            print("Konflikt", m.group(1), v["filament_id"], lst[v["filament_id"]], e)
helper = (
 'const qbxColor=(v,d)=>{if(Array.isArray(v))v=v[0];if(v==null||v==="")return"#00000000";const x=String(v).trim().replace(/[\'"#]/g,"");if(/^[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(x))return"#"+x.slice(0,6).toUpperCase();return(d&&d[x])||"#00000000"};\n'
 'const qbxFil=' + json.dumps(qfd, separators=(",", ":"), ensure_ascii=False) + ';\n'
 'const qbxFilMerge=(d,c)=>{if(!d)return d;for(const k of Object.keys(d))/^fila\\d+$/.test(k)&&delete d[k];let n;try{n=Number(c.$store.state.printer.printer.configfile.settings.extruder.nozzle_diameter).toFixed(1)}catch(e){}const l=qbxFil[n]||qbxFil["0.4"]||Object.assign({},...Object.values(qbxFil));for(const i in l)d["fila"+i]={filament:l[i][0],type:l[i][1],vendor:l[i][2]};return d};\n'
)
edits = [
 # Farbe: roh uebernehmen (Liste/Hex), nicht parseInt
 ('s[v]=parseInt(e[g]??"0",10)}else if(g.startsWith("filament_slot"))', 's[v]=e[g]??"0"}else if(g.startsWith("filament_slot"))', 1),
 # Filament-ID ist jetzt String (z.B. 'QFG00')
 ('n[v]=parseInt(e[g]??"0",10)}else if(g.startsWith("vendor_slot"))', 'n[v]=e[g]??"0"}else if(g.startsWith("vendor_slot"))', 1),
 # Farbanzeige
 ('C=((a=this.officialFilasListDictData)==null?void 0:a.colordict[String(this.variables.colorSlot[m])])??"#00000000"',
  'C=qbxColor(this.variables.colorSlot[m],(a=this.officialFilasListDictData)==null?void 0:a.colordict)', 1),
 ('color:((u=this.officialFilasListDictData)==null?void 0:u.colordict[this.variables.rackExtra[0]])??"#00000000"',
  'color:qbxColor(this.variables.rackExtra[0],(u=this.officialFilasListDictData)==null?void 0:u.colordict)', 1),
 ('l=o?o[this.variables.colorSlot[n]]:"#000000"', 'l=qbxColor(this.variables.colorSlot[n],o)', 1),
 # Filamentliste: Zuordnung der aktiven Duese einmischen
 ('setOfficiallFilasList",wn.configToDict(t))', 'setOfficiallFilasList",qbxFilMerge(wn.configToDict(t),this))', 2),
 # Rueckfall: Name/Farbe/Hersteller aus box_extras.boxes[].filament_info (von der Firmware geliefert)
 (',this.itemsCopy.push({label:v,color:C,filament:w,vendor:S,isRotating:!1})}const E=',
  ';{const _i=this.$store.state.printer.printer.box_extras?.boxes?.[Math.floor(m/4)]?.filament_info?.[m%4];_i&&(w=w||_i.filament_str||"",S=_i.vendor_str||S,C==="#00000000"&&(C=qbxColor(_i.color_rgb_str,null)))}this.itemsCopy.push({label:v,color:C,filament:w,vendor:S,isRotating:!1})}const E=', 1),
 # Absturz vermeiden, wenn ID unbekannt
 ('a===this.officialFilasListDictData[l.filaIndex].type', 'a===this.officialFilasListDictData[l.filaIndex]?.type', 1),
 ('s=this.selectedValueSlot[t])==null?void 0:s.filaIndex].type', 's=this.selectedValueSlot[t])==null?void 0:s.filaIndex]?.type', 1),
 # Schreiben: Farbe als ['RRGGBB'], Filament als 'ID'
 ('set selectedColor(t){const s=this.getKeyByValue(this.officialFilasListDictData.colordict,t);s&&(this.selectIndex===16?I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=color_slot16 VALUE="${s}"`):I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=color_slot${this.selectIndex} VALUE="${s}"`))',
  'set selectedColor(t){const s=String(t||"").replace("#","").toUpperCase();/^[0-9A-F]{6}$/.test(s)&&I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=color_slot${this.selectIndex} VALUE="[\'${s}\']"`)', 1),
 ('(this.selectIndex===16?I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=filament_slot16 VALUE="${s.replace("fila","")}"`):I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=filament_slot${this.selectIndex} VALUE="${s.replace("fila","")}"`))',
  'I.printerGcodeScript(`SAVE_VARIABLE VARIABLE=filament_slot${this.selectIndex} VALUE="\'${s.replace("fila","")}\'"`)', 1),
]
for a, b, n in edits:
    assert s.count(a) == n, (s.count(a), a[:70])
    s = s.replace(a, b)
open(dst, "w", encoding="utf-8", newline="").write(helper + s)
print("ok", {k: len(v) for k, v in qfd.items()})
