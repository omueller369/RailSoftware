/* Gemeinsame Verarbeitung für GPS-Erfassung und Kartendarstellung. */
package de.lokzeitleiste.app.portal

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.*

/** Mirrors browser totals: gaps never add stand time; manual intervals form a union. */
object GpsLiveMetrics {
    private data class Fix(val t:Long,val lat:Double,val lon:Double,val accuracy:Double,val speed:Double?,val breakBefore:Boolean)
    private fun meters(a:Fix,b:Fix):Double {
        val rad=Math.PI/180;val h=sin((b.lat-a.lat)*rad/2).pow(2)+cos(a.lat*rad)*cos(b.lat*rad)*sin((b.lon-a.lon)*rad/2).pow(2)
        return 6371000*2*asin(sqrt(h.coerceIn(0.0,1.0)))
    }
    fun calculate(raw:JSONArray,manual:JSONArray,now:Long,stopMinutes:Int?=null):JSONObject {
        val points=(0 until raw.length()).map { val p=raw.getJSONObject(it);Fix(p.getLong("t"),p.getDouble("lat"),p.getDouble("lon"),p.getDouble("accuracy"),if(p.isNull("speed"))null else p.getDouble("speed"),p.optBoolean("break_before")) }
        fun confirmed(inclusive:Boolean):Set<Long> {
            fun fast(speed:Double)=if(inclusive)speed>=10 else speed>10
            return points.windowed(4).filter { fixes ->
                if(fixes.drop(1).any { it.breakBefore } || fixes.any { it.accuracy>50 || it.speed!=null&&!fast(it.speed*3.6) })false
                else {
                    var path=0.0
                    val valid=fixes.zipWithNext().all { (a,b) ->val dt=b.t-a.t;val d=meters(a,b);path+=d;dt in 1..30000&&fast(d*3600/dt) }
                    val d=meters(fixes.first(),fixes.last());valid&&d>=0.75*path&&fast(d*3600/(fixes.last().t-fixes.first().t))
                }
            }.map { it.first().t }.toSet()
        }
        val departures=confirmed(false);val departure=confirmed(true).minOrNull()
        val intervals=mutableListOf<Pair<Long,Long>>();var last:Fix?=null;var run:Fix?=null;var wasStopped=false;var runLast:Fix?=null;val stands=mutableListOf<Pair<Long,Long>>()
        fun finish(){val a=run;val b=runLast;if(a!=null&&b!=null&&stopMinutes!=null&&b.t-a.t>=stopMinutes*60000L)stands.add(a.t to b.t);run=null;runLast=null}
        for(p in points) {
            val before=last
            if(before!=null&&wasStopped&&p.accuracy<=50&&p.t-before.t in 1..30000&&!p.breakBefore)intervals.add(before.t to p.t)
            if(before!=null&&(p.breakBefore||p.t-before.t>30000))finish()
            if(p.accuracy>50){finish();last=p;wasStopped=false;continue}
            val speed=p.speed ?: if(before!=null&&before.accuracy<=50&&p.t-before.t in 1..30000&&!p.breakBefore)meters(before,p)/((p.t-before.t)/1000.0) else null
            val start=run
            if(start!=null){if(p.t in departures)finish() else if(meters(start,p)<=100.000001)runLast=p}
            else if(p.t !in departures&&speed!=null&&speed*3.6<5){run=p;runLast=p}
            wasStopped=run!=null;last=p
        }
        finish();if(stopMinutes!=null){intervals.clear();intervals.addAll(stands)}
        for(i in 0 until manual.length()){val row=manual.getJSONObject(i);intervals.add(row.getLong("start") to if(row.isNull("end"))now else row.getLong("end"))}
        var total=0L;var end=Long.MIN_VALUE
        for((start,finish)in intervals.sortedBy { it.first })if(finish>start){total+=max(0L,finish-max(start,end));end=max(end,finish)}
        return JSONObject().put("elapsed_ms",if(departure==null)0 else max(0L,now-departure)).put("stopped_ms",total)
    }
}
