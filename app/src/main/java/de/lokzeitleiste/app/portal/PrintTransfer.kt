package de.lokzeitleiste.app.portal

import java.io.ByteArrayOutputStream
import java.util.UUID

/** Ein Druckauftrag wird begrenzt zusammengesetzt, bevor Android ihn erhält. */
class PrintTransfer {
    data class Document(val kind:String,val title:String,val bytes:ByteArray)
    private var id:String?=null
    private var kind=""
    private var title=""
    private var expected=0
    private var buffer:ByteArrayOutputStream?=null
    val active:Boolean get()=id!=null
    fun begin(kind:String,title:String,size:Int,token:String=UUID.randomUUID().toString()):String {
        require(!active && kind in setOf("pdf","layout"))
        require(token.matches(Regex("[A-Za-z0-9-]{1,100}")))
        require(title.isNotBlank() && title.length<=200)
        require(size in 1..if(kind=="pdf")16000000 else 1500000)
        this.kind=kind;this.title=title;expected=size;buffer=ByteArrayOutputStream(minOf(size,65536))
        return token.also { id=it }
    }
    fun append(id:String,bytes:ByteArray) {
        require(id==this.id && bytes.size in 1..49152)
        val stream=checkNotNull(buffer);require(stream.size()+bytes.size<=expected);stream.write(bytes)
    }
    fun finish(id:String):Document {
        require(id==this.id);val stream=checkNotNull(buffer);require(stream.size()==expected)
        val result=Document(kind,title,stream.toByteArray());clear();return result
    }
    fun abort(id:String) { if(id==this.id)clear() }
    fun clear() { buffer?.reset();buffer=null;id=null;title="";expected=0 }
}
