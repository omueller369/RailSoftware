package de.lokzeitleiste.app.portal
import org.junit.Assert.*
import org.junit.Test
class PortalPolicyTest {
    private val policy=PortalPolicy("https://ctl-software.io-goerlitz.eu")
    @Test fun laReaderAndOnlyPublicRendererAssetsArePackaged() {
        assertEquals("tf-portal.html",policy.asset("/tf/la-anweisungen"))
        assertEquals("la-instructions.js",policy.asset("/tf/la-instructions.js"))
        assertEquals("la-instructions.css",policy.asset("/tf/la-instructions.css"))
        assertEquals("la-vendor/pdf.mjs",policy.asset("/tf/la-vendor/pdf.mjs"))
        assertEquals("la-vendor/pdf.worker.mjs",policy.asset("/tf/la-vendor/pdf.worker.mjs"))
        assertNull(policy.asset("/tf/la-vendor/../account.js"))
        assertNull(policy.asset("/tf/la-vendor/manifest.json"))
        assertNull(policy.asset("/api/v1/tf/la-instructions/1/pdf"))
    }
    @Test fun polandRailTilesAreOfflineAssetsWithStrictPaths() {
        assertEquals("poland-rail.js",policy.asset("/tf/poland-rail.js"))
        assertEquals("poland-rail-data/overview.js",policy.asset("/tf/poland-rail-data/overview.js"))
        assertEquals("poland-rail-data/tile-275-172.js",policy.asset("/tf/poland-rail-data/tile-275-172.js"))
        assertNull(policy.asset("/tf/poland-rail-data/../account.js"))
        assertNull(policy.asset("/tf/poland-rail-data/manifest.json"))
    }
    @Test fun polishGraphIsPublicOfflineReferenceWithStrictPaths() {
        assertEquals("poland-stk.js",policy.asset("/tf/poland-stk.js"))
        assertEquals("poland-stk-worker.js",policy.asset("/tf/poland-stk-worker.js"))
        assertEquals("poland-stk-data/topology.json",policy.asset("/tf/poland-stk-data/topology.json"))
        assertEquals("poland-stk-data/geometry-372.json",policy.asset("/tf/poland-stk-data/geometry-372.json"))
        assertNull(policy.asset("/tf/poland-stk-data/geometry-1000.json"))
        assertNull(policy.asset("/tf/poland-stk-data/../account.json"))
        assertNull(policy.asset("/api/v1/tf/poland-route-knowledge/manual"))
    }
    @Test fun standaloneStkModuleUsesBundledEditorAndTables() {
        assertEquals("tf-portal.html",policy.asset("/tf/stk-anlegen"))
        assertEquals("route-table.js",policy.asset("/tf/route-table.js"))
    }
    @Test fun routeKnowledgeAndTrafficArePackaged() {
        val policy=PortalPolicy("https://example.test")
        assertEquals("tf-portal.html",policy.asset("/tf/streckenkenntnisse"))
        assertEquals("route-knowledge.js",policy.asset("/tf/route-knowledge.js"))
        assertEquals("rail-network-data.js",policy.asset("/tf/rail-network-data.js"))
        assertEquals("m1-basemap-data.js",policy.asset("/tf/m1-basemap-data.js"))
        assertEquals("m1-map.js",policy.asset("/tf/m1-map.js"))
        assertEquals("route-editor.js",policy.asset("/tf/route-editor.js"))
        assertEquals("gps-route-tools.js",policy.asset("/tf/gps-route-tools.js"))
        assertEquals("map-gestures.js", policy.asset("/map-gestures.js"))
        assertEquals("android-offline.js",policy.asset("/android-offline.js"))
        assertEquals("rail-network.js",policy.asset("/tf/rail-network.js"))
        assertEquals("route-coverage.js",policy.asset("/tf/route-coverage.js"))
        assertEquals("location-editor.js",policy.asset("/tf/location-editor.js"))
        assertEquals("knowledge-inventory.js",policy.asset("/tf/knowledge-inventory.js"))
        assertEquals("route-imports.js",policy.asset("/tf/route-imports.js"))
        assertEquals("route-csv.js",policy.asset("/tf/route-csv.js"))
        assertEquals("beta-traffic.js",policy.asset("/tf/beta-traffic.js"))
    }
    @Test fun exactOrigin() {
        assertTrue(policy.sameOrigin("https://ctl-software.io-goerlitz.eu/tf"))
        assertTrue(policy.sameOrigin("https://ctl-software.io-goerlitz.eu:443/documents"))
        for(url in listOf("http://ctl-software.io-goerlitz.eu/tf","https://ctl-software.io-goerlitz.eu.evil.test/tf","https://ctl-software.io-goerlitz.eu:444/tf","https://attacker@ctl-software.io-goerlitz.eu/tf","file:///tf","javascript:alert(1)")) assertFalse(url,policy.sameOrigin(url))
    }
    @Test fun onlyPublicMapTiles() {
        for (url in listOf("https://tile.openstreetmap.org/10/548/335.png", "https://tiles.openrailwaymap.org/standard/10/548/335.png", "https://tile.openstreetmap.org:443/0/0/0.png")) {
            assertTrue(url, policy.mapTile(url))
            assertFalse(url, policy.sameOrigin(url))
        }
        for (url in listOf("http://tile.openstreetmap.org/10/548/335.png", "https://tile.openstreetmap.org.evil.test/10/548/335.png", "https://user@tile.openstreetmap.org/10/548/335.png", "https://tile.openstreetmap.org:444/10/548/335.png", "https://tile.openstreetmap.org/10/548/335.png?token=secret", "https://tile.openstreetmap.org/10/548/335.png#fragment", "https://tile.openstreetmap.org/account", "https://tile.openstreetmap.org/10/1024/335.png", "https://tile.openstreetmap.org/20/1/1.png", "https://tiles.openrailwaymap.org/other/10/548/335.png", "https://tile.openstreetmap.org/10/548/335%2epng")) assertFalse(url, policy.mapTile(url))
    }
    @Test fun onlyPackagedPublicViews() {
        assertEquals("station-contributions.js",policy.asset("/tf/station-contributions.js"))
        for(kind in listOf("electric","steam","diesel","tank")) assertEquals("gps-marker-$kind.png",policy.asset("/tf/gps-marker-$kind.png"))
        assertNull(policy.asset("/tf/gps-marker-unknown.png"))
        assertEquals("station-catalog-data.js",policy.asset("/tf/station-catalog-data.js"))
        assertEquals("station-catalog.js",policy.asset("/tf/station-catalog.js"))
        assertEquals("report-tabs.js",policy.asset("/tf/report-tabs.js"))
        assertEquals("tf-portal.html",policy.asset("/tf/updates"))
        assertEquals("updates.js",policy.asset("/tf/updates.js"))
        assertEquals("tf-portal.html",policy.asset("/tf/gps-demo"))
        assertEquals("gps-demo.js",policy.asset("/tf/gps-demo.js"))
        assertEquals("infra-go.js",policy.asset("/tf/infra-go.js"))
        assertEquals("gps-demo-visibility.js",policy.asset("/tf/gps-demo-visibility.js"))
        assertEquals("loco-handover.html",policy.asset("/tf/lokuebergabebuch"))
        assertEquals("loco-handover.html",policy.asset("/tf/loco-handover"))
        assertEquals("loco-handover.js",policy.asset("/tf/loco-handover.js"))
        assertEquals("handover-protocols.js",policy.asset("/tf/handover-protocols.js"))
        for(path in listOf("/tf","/tf/hilfe","/locales/messages.js","/theme.js","/theme.css","/tf/notizen","/tf/notes.js","/tf/help.js","/tf/help-content.js","/tf/help.css","/tf/arbeitsbericht","/tf/bahnhoefe","/tf/arbeitsplan","/documents","/account","/my/worktime")) assertNotNull(policy.asset(path))
        for(path in listOf("/admin","/api/v1/tf/portal","/api/v1/documents/download","/tf/../../secret")) assertNull(policy.asset(path))
    }
}
