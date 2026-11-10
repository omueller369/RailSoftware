package de.lokzeitleiste.app.portal

import java.net.URLDecoder

/** Preserve the server's UTF-8 attachment name instead of WebView's download.bin fallback. */
object DownloadMetadata {
    fun name(disposition: String, fallback: String): String {
        val extended = Regex("filename\\*\\s*=\\s*(?:\"([^\"]+)\"|([^;]+))", RegexOption.IGNORE_CASE).find(disposition)
        val value = extended?.let { it.groupValues[1].ifEmpty { it.groupValues[2] }.trim() }
        val encoded = value?.let { Regex("UTF-8'[^']*'(.*)", RegexOption.IGNORE_CASE).matchEntire(it)?.groupValues?.get(1) }
        val decoded = encoded?.let { runCatching { URLDecoder.decode(it.replace("+", "%2B"), "UTF-8") }.getOrNull() }
        val plain = Regex("filename\\s*=\\s*(?:\"([^\"]+)\"|([^;]+))", RegexOption.IGNORE_CASE).find(disposition)
            ?.let { it.groupValues[1].ifEmpty { it.groupValues[2] } }
        return (decoded?.takeIf { it.isNotBlank() } ?: plain?.takeIf { it.isNotBlank() } ?: fallback)
            .replace(Regex("[/\\\\\\x00-\\x1f]"), "_").trim().ifEmpty { "download.bin" }
    }

    fun mime(name: String, supplied: String?): String {
        if (name.endsWith(".pdf", ignoreCase = true)) return "application/pdf"
        return supplied?.substringBefore(';')?.trim()?.takeIf { it.contains('/') } ?: "application/octet-stream"
    }
}
