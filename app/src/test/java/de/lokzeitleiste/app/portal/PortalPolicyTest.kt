package de.lokzeitleiste.app.portal
import org.junit.Assert.*
import org.junit.Test
class PortalPolicyTest {
    private val policy=PortalPolicy("https://ctl-software.io-goerlitz.eu")
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
        assertEquals("loco-handover.html",policy.asset("/tf/lokuebergabebuch"))
        assertEquals("loco-handover.html",policy.asset("/tf/loco-handover"))
        assertEquals("loco-handover.js",policy.asset("/tf/loco-handover.js"))
        assertEquals("handover-protocols.js",policy.asset("/tf/handover-protocols.js"))
        for(path in listOf("/tf","/tf/hilfe","/locales/messages.js","/theme.js","/theme.css","/tf/notizen","/tf/notes.js","/tf/help.js","/tf/help-content.js","/tf/help.css","/tf/arbeitsbericht","/tf/bahnhoefe","/tf/arbeitsplan","/documents","/account","/my/worktime")) assertNotNull(policy.asset(path))
        for(path in listOf("/admin","/api/v1/tf/portal","/api/v1/documents/download","/tf/../../secret")) assertNull(policy.asset(path))
    }
}
