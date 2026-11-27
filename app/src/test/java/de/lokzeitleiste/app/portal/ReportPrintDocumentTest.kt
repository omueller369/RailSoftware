package de.lokzeitleiste.app.portal
import org.junit.Assert.*
import org.junit.Test

@org.junit.runner.RunWith(org.robolectric.RobolectricTestRunner::class)
@org.robolectric.annotation.Config(manifest=org.robolectric.annotation.Config.NONE,sdk=[35])
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
    @Test fun localLayoutUsesTablesAndEscapesEveryCell() {
        val layout=org.json.JSONObject("""{"title":"ENTWURF","lines":[["Name","<script>unsafe</script>"],["Dienstbeginn","—"]],"sections":[["Gastfahrten",[["Von","Bis"],["Łódź","Berlin"]]]],"train_pages":[[["Zugfahrt",[["Zugnr.","Start"],["123","BBB"]]]]]}""")
        val html=ReportPrintDocument.renderLayout("Schichtvorschau",layout)
        assertTrue(html.contains("<table>"));assertTrue(html.contains("size:A4"))
        assertTrue(html.contains("&lt;script&gt;"));assertFalse(html.contains("<script>"))
        assertTrue(html.contains("class='train'"));assertTrue(html.contains("Łódź"))
    }

}
