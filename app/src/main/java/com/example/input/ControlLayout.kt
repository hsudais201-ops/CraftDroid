package com.example.input

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.round

enum class LayoutOrientation {
    LANDSCAPE,
    PORTRAIT
}

data class ControlLayout(
    val orientation: LayoutOrientation,
    val controls: List<TouchControl>
) {
    fun findControl(id: String): TouchControl? = controls.firstOrNull { it.id == id }

    fun updateControl(updated: TouchControl): ControlLayout {
        val newControls = controls.map { if (it.id == updated.id) updated else it }
        return copy(controls = newControls)
    }

    fun addControl(control: TouchControl): ControlLayout {
        return copy(controls = controls + control)
    }

    fun removeControl(id: String): ControlLayout {
        return copy(controls = controls.filterNot { it.id == id })
    }

    fun duplicateControl(id: String): ControlLayout {
        val original = findControl(id) ?: return this
        val duplicated = original.copy(
            id = java.util.UUID.randomUUID().toString().take(8),
            name = "${original.name} (Copy)",
            xPercent = (original.xPercent + 0.04f).coerceIn(0.05f, 0.95f),
            yPercent = (original.yPercent + 0.04f).coerceIn(0.05f, 0.95f)
        )
        return copy(controls = controls + duplicated)
    }

    fun bringToFront(id: String): ControlLayout {
        val control = findControl(id) ?: return this
        return copy(controls = controls.filterNot { it.id == id } + control)
    }

    fun sendToBack(id: String): ControlLayout {
        val control = findControl(id) ?: return this
        return copy(controls = listOf(control) + controls.filterNot { it.id == id })
    }

    fun moveUp(id: String): ControlLayout {
        val index = controls.indexOfFirst { it.id == id }
        if (index < 0 || index >= controls.lastIndex) return this
        val list = controls.toMutableList()
        val tmp = list[index]
        list[index] = list[index + 1]
        list[index + 1] = tmp
        return copy(controls = list)
    }

    fun moveDown(id: String): ControlLayout {
        val index = controls.indexOfFirst { it.id == id }
        if (index <= 0) return this
        val list = controls.toMutableList()
        val tmp = list[index]
        list[index] = list[index - 1]
        list[index - 1] = tmp
        return copy(controls = list)
    }

    fun resetToSafeArea(horizontalMargin: Float = 0.04f, verticalMargin: Float = 0.05f): ControlLayout {
        val safeControls = controls.map { ctrl ->
            ctrl.copy(
                xPercent = ctrl.xPercent.coerceIn(horizontalMargin, 1.0f - horizontalMargin),
                yPercent = ctrl.yPercent.coerceIn(verticalMargin, 1.0f - verticalMargin)
            )
        }
        return copy(controls = safeControls)
    }

    fun snap(control: TouchControl, gridStepPercent: Float = 0.05f): TouchControl {
        val snappedX = (round(control.xPercent / gridStepPercent) * gridStepPercent).coerceIn(0.02f, 0.98f)
        val snappedY = (round(control.yPercent / gridStepPercent) * gridStepPercent).coerceIn(0.02f, 0.98f)
        return control.copy(xPercent = snappedX, yPercent = snappedY)
    }

    fun toJson(): JSONObject {
        val array = JSONArray()
        controls.forEach { array.put(it.toJson()) }
        return JSONObject().apply {
            put("orientation", orientation.name)
            put("controls", array)
        }
    }

    companion object {
        fun fromJson(json: JSONObject, defaultOrientation: LayoutOrientation = LayoutOrientation.LANDSCAPE): ControlLayout {
            val orient = try {
                LayoutOrientation.valueOf(json.optString("orientation", defaultOrientation.name))
            } catch (_: Exception) {
                defaultOrientation
            }
            val array = json.optJSONArray("controls") ?: JSONArray()
            val list = mutableListOf<TouchControl>()
            for (i in 0 until array.length()) {
                val item = array.optJSONObject(i) ?: continue
                try {
                    list.add(TouchControl.fromJson(item))
                } catch (_: Exception) {}
            }
            return ControlLayout(orientation = orient, controls = list)
        }
    }
}
