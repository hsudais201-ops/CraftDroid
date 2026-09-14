package com.example.launcher

import com.example.versions.LibraryRule
import com.example.versions.VersionJsonParser
import org.json.JSONArray
import org.json.JSONObject

/** Resolves Minecraft's modern rule-based arguments and legacy argument strings. */
class LaunchArgumentResolver(
    private val versionParser: VersionJsonParser
) {
    fun resolveJvmArguments(items: List<Any>, templates: Map<String, String>): List<String> =
        resolve(items, templates)

    fun resolveGameArguments(items: List<Any>, templates: Map<String, String>): List<String> =
        resolve(items, templates)

    fun resolveLegacyArguments(raw: String, templates: Map<String, String>): List<String> =
        tokenize(raw).map { substitute(it, templates) }

    /** JVM/user supplied args are tokenized without invoking a shell. */
    fun tokenize(raw: String): List<String> {
        val result = mutableListOf<String>()
        val current = StringBuilder()
        var quote: Char? = null
        var escaped = false
        for (ch in raw) {
            if (escaped) {
                current.append(ch)
                escaped = false
                continue
            }
            if (ch == '\\') {
                escaped = true
                continue
            }
            if (quote != null) {
                if (ch == quote) quote = null else current.append(ch)
            } else if (ch == '\'' || ch == '"') {
                quote = ch
            } else if (ch.isWhitespace()) {
                if (current.isNotEmpty()) { result += current.toString(); current.clear() }
            } else {
                current.append(ch)
            }
        }
        if (escaped) current.append('\\')
        check(quote == null) { "Unterminated quote in launch arguments" }
        if (current.isNotEmpty()) result += current.toString()
        return result
    }

    private fun resolve(items: List<Any>, templates: Map<String, String>): List<String> {
        val out = mutableListOf<String>()
        for (item in items) {
            when (item) {
                is String -> appendValue(out, item, templates)
                is JSONObject -> {
                    val rules = parseRules(item.optJSONArray("rules"))
                    if (versionParser.evaluateRules(rules)) {
                        when (val value = item.opt("value")) {
                            is String -> appendValue(out, value, templates)
                            is JSONArray -> for (i in 0 until value.length()) {
                                appendValue(out, value.optString(i), templates)
                            }
                        }
                    }
                }
            }
        }
        return out
    }

    private fun appendValue(out: MutableList<String>, value: String, templates: Map<String, String>) {
        if (value.isBlank() || value.contains("\${classpath}")) return
        out += substitute(value, templates)
    }

    private fun parseRules(array: JSONArray?): List<LibraryRule> {
        if (array == null) return emptyList()
        val result = mutableListOf<LibraryRule>()
        for (i in 0 until array.length()) {
            val rule = array.optJSONObject(i) ?: continue
            val os = rule.optJSONObject("os")
            result += LibraryRule(
                action = rule.optString("action", "disallow"),
                osName = os?.optString("name")?.takeIf { it.isNotBlank() },
                osVersion = os?.optString("version")?.takeIf { it.isNotBlank() },
                osArch = os?.optString("arch")?.takeIf { it.isNotBlank() }
            )
        }
        return result
    }

    private fun substitute(value: String, templates: Map<String, String>): String {
        var output = value
        for ((key, replacement) in templates) output = output.replace("\${$key}", replacement)
        return output
    }
}
