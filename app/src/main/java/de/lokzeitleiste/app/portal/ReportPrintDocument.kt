/* Gemeinsame Verarbeitung für Dokumentablage und Dateizugriff. */
package de.lokzeitleiste.app.portal

/** Die Schichtvorschau wird als maskierter Text ohne Skripte oder externe Inhalte gedruckt. */
object ReportPrintDocument {
    fun render(title:String,text:String):String {
        require(title.isNotBlank() && title.length<=200 && text.isNotBlank() && text.length<=500000) { "Ungültige Berichtsvorschau." }
        fun escape(value:String)=value.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\"","&quot;").replace("'","&#39;")
        return "<!doctype html><html lang=\"de\"><head><meta charset=\"utf-8\"><title>${escape(title)}</title><style>@page{size:A4;margin:16mm}body{font:11pt/1.5 sans-serif;color:#000;background:#fff}h1{font-size:24px}div{white-space:pre-wrap;overflow-wrap:anywhere}</style></head><body><div>${escape(text)}</div></body></html>"
    }
    /** Die lokale Ersatzansicht verwendet dieselben Spalten und Abschnitte wie der PDF-Bericht. */
    fun renderLayout(title:String,layout:org.json.JSONObject):String {
        require(title.length<=200 && layout.toString().length<=1000000)
        fun esc(value:String)=value.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\"","&quot;").replace("'","&#39;")
        fun table(rows:org.json.JSONArray,weights:org.json.JSONArray?=null,spans:org.json.JSONArray?=null,meta:Boolean=false):String {
            val count=rows.getJSONArray(0).length();require(count in 1..10 && rows.length()<=1000)
            val defaults=when(count){2->listOf(.29,.71);5->listOf(.12,.27,.17,.27,.17);6->listOf(.29,.17,.16,.14,.14,.10);7->listOf(.18,.18,.14,.14,.08,.22,.06);else->List(count){1.0/count}}
            val out=StringBuilder("<table><colgroup>")
            for(i in 0 until count){val width=(weights?.optDouble(i,defaults[i])?:defaults[i]).coerceIn(0.0,1.0)*100;out.append("<col style='width:${width}%' />")};out.append("</colgroup>")
            for(i in 0 until rows.length()) {
                val row=rows.getJSONArray(i);require(row.length()==count);val span=(0 until (spans?.length()?:0)).any { spans!!.getInt(it)==i };out.append("<tr>")
                if(span)out.append("<td colspan='$count'>${esc(row.optString(0,"—"))}</td>")
                else for(j in 0 until count){val tag=if(i==0 && !meta)"th" else "td";val css=if(meta && j%2==0)" class='key'" else "";out.append("<$tag$css>${esc(row.optString(j,"—"))}</$tag>")}
                out.append("</tr>")
            };return out.append("</table>").toString()
        }
        fun sections(values:org.json.JSONArray):String {
            val out=StringBuilder()
            for(i in 0 until values.length()){val section=values.getJSONArray(i);val indent=(section.optDouble(2,0.0)*100).coerceIn(0.0,50.0);out.append("<div style='margin-left:${indent}%'><h2>${esc(section.getString(0))}</h2>${table(section.getJSONArray(1),section.optJSONArray(3),section.optJSONArray(4))}</div>")}
            return out.toString()
        }
        val lines=layout.getJSONArray("lines");val half=(lines.length()+1)/2;val pairs=org.json.JSONArray()
        for(i in 0 until half){val pair=org.json.JSONArray();val left=lines.getJSONArray(i);pair.put(left.optString(0));pair.put(left.optString(1));val right=lines.optJSONArray(i+half);pair.put(right?.optString(0)?:"");pair.put(right?.optString(1)?:"");pairs.put(pair)}
        val body=StringBuilder("<section><h1>${esc(layout.getString("title"))}</h1>${table(pairs,org.json.JSONArray("[0.22,0.28,0.22,0.28]"),meta=true)}${sections(layout.getJSONArray("sections"))}</section>")
        val pages=layout.optJSONArray("print_pages")
        if(pages!=null){for(i in 0 until pages.length()){body.append("<section class='train page'>");val blocks=pages.getJSONArray(i);for(j in 0 until blocks.length())body.append("<div class='train-block'>${sections(blocks.getJSONArray(j))}</div>");body.append("</section>")}}
        else {val trains=layout.getJSONArray("train_pages");for(i in 0 until trains.length())body.append("<section class='train'>${sections(trains.getJSONArray(i))}</section>")}
        return "<!doctype html><html><head><meta charset='utf-8'><title>${esc(title)}</title><style>@page{size:A4;margin:12mm}body{font:8pt/11pt sans-serif;color:#000}h1{font-size:17pt;line-height:22pt;color:#17445b}h2{font-size:11pt;line-height:15pt;color:#17445b;margin:12pt 0 6pt}table{border-collapse:collapse;width:100%;table-layout:fixed}td,th{border:.4pt solid #bdcdd7;padding:6pt 7pt;vertical-align:top;overflow-wrap:anywhere;font-weight:normal}tr:nth-child(even),.key{background:#f1f6f8}th{background:#dcebf4}.train{break-inside:avoid;page-break-inside:avoid}.train-block{break-inside:avoid;page-break-inside:avoid}.train.page{break-before:page}.train td,.train th{padding:3pt 7pt;font:8pt/1.35 sans-serif}.train-block:first-child h2:first-child{margin-top:0}.train-block+.train-block{margin-top:12pt}footer{position:fixed;bottom:0;color:#546b7b;font-size:8pt}body>section.train:nth-of-type(2){break-before:page}section{break-inside:auto}</style></head><body><footer>${esc(layout.optString("draft_label",""))}</footer>$body</body></html>"
    }

}
