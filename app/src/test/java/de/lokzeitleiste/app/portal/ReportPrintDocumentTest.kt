package de.lokzeitleiste.app.portal
import org.junit.Assert.*
import org.junit.Test

class ReportPrintDocumentTest {
    @Test fun preservesIncompleteReportAsEscapedText() {
        val html=ReportPrintDocument.render("Schichtvorschau", "ENTWURF\nVon: — (fehlt)\n<script>evil()</script>\nZiel: Łódź")
        assertTrue(html.contains("Von: — (fehlt)"))
        assertTrue(html.contains("&lt;script&gt;"))
        assertFalse(html.contains("<script>"))
        assertFalse(html.contains("<iframe"))
        assertTrue(html.contains("Łódź"))
        assertTrue(html.contains("white-space:pre-wrap"))
    }
    @Test fun boundsPrintContent() {
        for(pair in listOf("" to "Bericht", "Titel" to "", "X".repeat(201) to "Text", "Titel" to "X".repeat(500001))) {
            try { ReportPrintDocument.render(pair.first,pair.second);fail("invalid report accepted") } catch(_:IllegalArgumentException) { }
        }
    }
}
