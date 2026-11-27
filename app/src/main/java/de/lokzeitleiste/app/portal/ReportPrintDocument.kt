/* Gemeinsame Verarbeitung für Dokumentablage und Dateizugriff. */
package de.lokzeitleiste.app.portal

/** Die Schichtvorschau wird als maskierter Text ohne Skripte oder externe Inhalte gedruckt. */
object ReportPrintDocument {
    fun render(title:String,text:String):String {
        require(title.isNotBlank() && title.length<=200 && text.isNotBlank() && text.length<=500000) { "Ungültige Berichtsvorschau." }
        fun escape(value:String)=value.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\"","&quot;").replace("'","&#39;")
        return "<!doctype html><html lang=\"de\"><head><meta charset=\"utf-8\"><title>${escape(title)}</title><style>@page{size:A4;margin:16mm}body{font:11pt/1.5 sans-serif;color:#000;background:#fff}h1{font-size:24px}div{white-space:pre-wrap;overflow-wrap:anywhere}</style></head><body><div>${escape(text)}</div></body></html>"
    }
}
