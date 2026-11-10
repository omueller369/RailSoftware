package de.lokzeitleiste.app.portal

import org.junit.Assert.*
import org.junit.Test

class DownloadMetadataTest {
    @Test fun utf8PdfNameOverridesBinaryFallback() {
        assertEquals("Arbeitsbericht-Müller.pdf", DownloadMetadata.name("attachment; filename*=UTF-8''Arbeitsbericht-M%C3%BCller.pdf", "download.bin"))
        assertEquals("application/pdf", DownloadMetadata.mime("Arbeitsbericht-Müller.PDF", "application/octet-stream"))
    }
    @Test fun extendedNameWinsAndPreservesPlus() {
        assertEquals("Bericht+1.pdf", DownloadMetadata.name("attachment; filename=alt.pdf; filename*=UTF-8''Bericht+1.pdf", "download.bin"))
    }
    @Test fun malformedEncodingUsesPlainName() {
        assertEquals("Bericht 100%.pdf", DownloadMetadata.name("attachment; filename*=UTF-8''bad%xx; filename=\"Bericht 100%.pdf\"", "download.bin"))
    }
    @Test fun filenamesCannotIntroducePaths() {
        assertEquals("a_b.pdf", DownloadMetadata.name("attachment; filename=\"a/b.pdf\"", "download.bin"))
        assertEquals("original.pdf", DownloadMetadata.name("", "original.pdf"))
        assertEquals("image/png", DownloadMetadata.mime("image.png", "image/png; charset=UTF-8"))
    }
}
