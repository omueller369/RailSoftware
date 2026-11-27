package de.lokzeitleiste.app.portal
import org.junit.Assert.*
import org.junit.Test

class PrintTransferTest {
    private fun rejects(action:()->Unit) { try { action();fail("invalid print transfer accepted") } catch(_:IllegalArgumentException) { } }
    @Test fun largePdfSurvivesPacketsWithoutChanges() {
        val transfer=PrintTransfer();val bytes=ByteArray(250000){(it%251).toByte()};val id=transfer.begin("pdf","Schicht",bytes.size)
        for(offset in bytes.indices step 49152)transfer.append(id,bytes.copyOfRange(offset,minOf(offset+49152,bytes.size)))
        val document=transfer.finish(id);assertEquals("pdf",document.kind);assertArrayEquals(bytes,document.bytes);assertFalse(transfer.active)
    }
    @Test fun limitsAndAbortPreventStaleOrMixedJobs() {
        val transfer=PrintTransfer();rejects { transfer.begin("pdf","",10) };rejects { transfer.begin("pdf","Titel",16000001) }
        val id=transfer.begin("layout","Lokaler Bericht",20)
        rejects { transfer.begin("pdf","Zweiter Auftrag",10) };rejects { transfer.append("fremd",byteArrayOf(1)) };rejects { transfer.append(id,ByteArray(49153)) };rejects { transfer.finish(id) }
        transfer.abort("fremd");assertTrue(transfer.active);transfer.abort(id);assertFalse(transfer.active)
        val next=transfer.begin("pdf","Neuer Auftrag",1);transfer.append(next,byteArrayOf(42));assertEquals(42,transfer.finish(next).bytes[0].toInt())
        transfer.begin("layout","Seitenwechsel",20);transfer.clear();assertFalse(transfer.active)
    }
}
