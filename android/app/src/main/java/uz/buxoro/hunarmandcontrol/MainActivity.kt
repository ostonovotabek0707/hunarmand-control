package uz.buxoro.hunarmandcontrol

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.*
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class MainActivity : Activity() {

    private val apiUrl = "http://127.0.0.1:8000"

    private val dark = Color.rgb(30, 38, 48)
    private val gold = Color.rgb(184, 143, 70)
    private val bg = Color.rgb(246, 246, 243)
    private val white = Color.WHITE
    private val gray = Color.rgb(105, 112, 122)
    private val green = Color.rgb(55, 125, 75)
    private val red = Color.rgb(150, 60, 60)

    private lateinit var phone: EditText
    private lateinit var password: EditText
    private lateinit var message: TextView
    private lateinit var loginButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        showLoginScreen()
    }

    private fun root(): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(bg)
            setPadding(24, 24, 24, 24)
        }

    private fun label(
        value: String,
        size: Float = 16f,
        color: Int = dark,
        bold: Boolean = false
    ): TextView =
        TextView(this).apply {
            text = value
            textSize = size
            setTextColor(color)
            if (bold) typeface = Typeface.DEFAULT_BOLD
        }

    private fun centerLabel(
        value: String,
        size: Float = 16f,
        color: Int = dark,
        bold: Boolean = false
    ): TextView =
        label(value, size, color, bold).apply {
            gravity = Gravity.CENTER
        }

    private fun logo(sizeW: Int = 90, sizeH: Int = 70): TextView =
        centerLabel("BHB", 26f, white, true).apply {
            setBackgroundColor(gold)
            setPadding(10, 10, 10, 10)
            layoutParams = LinearLayout.LayoutParams(sizeW, sizeH)
        }

    private fun button(
        title: String,
        color: Int = dark,
        action: () -> Unit
    ): Button =
        Button(this).apply {
            text = title
            textSize = 18f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(white)
            setBackgroundColor(color)
            setOnClickListener { action() }
        }

    private fun showLoginScreen() {

        val main = root()

        val scroll = ScrollView(this)
        val content = LinearLayout(this)

        content.orientation = LinearLayout.VERTICAL
        content.gravity = Gravity.CENTER_HORIZONTAL
        content.setPadding( 16, 0, 16, 0)

        content.addView(
            logo(120, 90),
            LinearLayout.LayoutParams(120, 90)
        )

        content.addView(
            centerLabel(
                "HUNARMAND CONTROL",
                27f,
                dark,
                true
            ).apply {
                setPadding(0, 25, 0, 5)
            }
        )

        content.addView(
            centerLabel(
                "Ҳунармандлар бошқарув тизими",
                16f,
                gray
            ).apply {
                setPadding(0, 0, 0, 35)
            }
        )

        phone = EditText(this).apply {
            hint = "Телефон рақами"
            textSize = 17f
            inputType = InputType.TYPE_CLASS_PHONE
            setSingleLine(true)
            setPadding(20, 15, 20, 15)
            setBackgroundColor(white)
        }

        password = EditText(this).apply {
            hint = "Пароль"
            textSize = 17f
            inputType =
                InputType.TYPE_CLASS_TEXT or
                InputType.TYPE_TEXT_VARIATION_PASSWORD
            setSingleLine(true)
            setPadding(20, 15, 20, 15)
            setBackgroundColor(white)
        }

        content.addView(
            phone,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                65
            ).apply {
                setMargins(0, 0, 0, 12)
            }
        )

        content.addView(
            password,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                65
            ).apply {
                setMargins(0, 0, 0, 20)
            }
        )

        loginButton = button("КИРИШ") {
            login()
        }

        content.addView(
            loginButton,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                62
            )
        )

        message = centerLabel("", 15f, gray)

        content.addView(
            message,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                setMargins(0, 20, 0, 0)
            }
        )

        content.addView(
            centerLabel(
                "Buxoro viloyati Hunarmand uyushmasi",
                13f,
                gray
            ).apply {
                setPadding(0, 55, 0, 0)
            }
        )

        scroll.addView(content)
        main.addView(
            scroll,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.MATCH_PARENT
            )
        )

        setContentView(main)
    }

    private fun login() {

        val p = phone.text.toString().trim()
        val pass = password.text.toString()

        if (p.isEmpty() || pass.isEmpty()) {
            message.text = "Телефон ва парольни киритинг"
            return
        }

        loginButton.isEnabled = false
        message.text = "Кириш текширилмоқда..."

        Thread {

            try {

                val connection =
                    URL("$apiUrl/api/v1/auth/login")
                        .openConnection() as HttpURLConnection

                connection.requestMethod = "POST"

                connection.setRequestProperty(
                    "Content-Type",
                    "application/json"
                )

                connection.connectTimeout = 10000
                connection.readTimeout = 10000
                connection.doOutput = true

                val body =
                    JSONObject().apply {
                        put("phone", p)
                        put("password", pass)
                    }.toString()

                connection.outputStream.use {
                    it.write(body.toByteArray(Charsets.UTF_8))
                }

                val code = connection.responseCode

                val stream =
                    if (code in 200..299)
                        connection.inputStream
                    else
                        connection.errorStream

                val response =
                    stream?.bufferedReader()?.use {
                        it.readText()
                    } ?: ""

                if (code in 200..299) {

                    val json = JSONObject(response)

                    val token =
                        json.optString("access_token", "")

                    val user =
                        json.optJSONObject("user")

                    val role =
                        user?.optString("role", "") ?: ""

                    getSharedPreferences(
                        "auth",
                        MODE_PRIVATE
                    ).edit()
                        .putString("access_token", token)
                        .putString("role", role)
                        .apply()

                    runOnUiThread {
                        showHome(role)
                    }

                } else {

                    val error =
                        try {
                            JSONObject(response)
                                .optString(
                                    "detail",
                                    "Номаълум хато"
                                )
                        } catch (_: Exception) {
                            "HTTP $code"
                        }

                    runOnUiThread {
                        loginButton.isEnabled = true
                        message.text = error
                    }
                }

                connection.disconnect()

            } catch (e: Exception) {

                runOnUiThread {
                    loginButton.isEnabled = true
                    message.text =
                        "Серверга уланиб бўлмади:\n${e.message}"
                }
            }

        }.start()
    }

    private fun showHome(role: String) {

        val main = root()

        val scroll = ScrollView(this)

        val content = LinearLayout(this)
        content.orientation = LinearLayout.VERTICAL
        content.setPadding( 16, 0, 16, 0)

        val header = LinearLayout(this)
        header.orientation = LinearLayout.HORIZONTAL
        header.gravity = Gravity.CENTER_VERTICAL
        header.setPadding( 16, 0, 16, 0)

        header.addView(logo(75, 65))

        val headerText = LinearLayout(this)
        headerText.orientation = LinearLayout.VERTICAL
        headerText.setPadding( 16, 0, 16, 0)

        headerText.addView(
            label(
                "HUNARMAND",
                22f,
                dark,
                true
            )
        )

        headerText.addView(
            label(
                "CONTROL",
                18f,
                gold,
                true
            )
        )

        header.addView(
            headerText,
            LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1f
            )
        )

        content.addView(header)

        content.addView(
            centerLabel(
                roleName(role),
                18f,
                white,
                true
            ).apply {
                setBackgroundColor(dark)
                setPadding(10, 16, 10, 16)
            },
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                60
            ).apply {
                setMargins(0, 0, 0, 25)
            }
        )

        content.addView(
            label(
                "АСОСИЙ БЎЛИМЛАР",
                15f,
                gray,
                true
            ).apply {
                setPadding(5, 0, 0, 12)
            }
        )

        when (role) {

            "SUPER_ADMIN" -> {

                menu(
                    content,
                    "👤",
                    "ХОДИМЛАР",
                    "Тизим ходимларини бошқариш"
                ) {
                    showEmployees()
                }

                menu(
                    content,
                    "🧑‍🎨",
                    "ҲУНАРМАНДЛАР",
                    "Барча ҳунармандлар"
                ) {
                    showSection(
                        "ҲУНАРМАНДЛАР",
                        "Ҳунармандлар бошқаруви"
                    )
                }

                menu(
                    content,
                    "🗺",
                    "ҲУДУДЛАР",
                    "Вилоят ва туманлар"
                ) {
                    showSection(
                        "ҲУДУДЛАР",
                        "Ҳудудлар бошқаруви"
                    )
                }

                menu(
                    content,
                    "📊",
                    "ҲИСОБОТЛАР",
                    "Тизим статистикаси"
                ) {
                    showSection(
                        "ҲИСОБОТЛАР",
                        "Тизим ҳисоботлари"
                    )
                }

                menu(
                    content,
                    "⚙️",
                    "ТИЗИМ СОЗЛАМАЛАРИ",
                    "Асосий тизим параметрлари"
                ) {
                    showSection(
                        "ТИЗИМ СОЗЛАМАЛАРИ",
                        "Тизим созламалари"
                    )
                }
            }

            "REGIONAL_MANAGER" -> {

                menu(
                    content,
                    "👤",
                    "ХОДИМЛАР",
                    "Вилоят бошқаруви ходимлари"
                ) {
                    showEmployees()
                }

                menu(
                    content,
                    "🧑‍🎨",
                    "ҲУНАРМАНДЛАР",
                    "Бухоро вилояти ҳунармандлари"
                ) {
                    showSection(
                        "ҲУНАРМАНДЛАР",
                        "Вилоят ҳунармандлари"
                    )
                }

                menu(
                    content,
                    "🗺",
                    "ТУМАНЛАР",
                    "Бухоро вилояти туманлари"
                ) {
                    showSection(
                        "ТУМАНЛАР",
                        "Вилоят туманлари"
                    )
                }

                menu(
                    content,
                    "📊",
                    "ҲИСОБОТЛАР",
                    "Вилоят ҳисоботлари"
                ) {
                    showSection(
                        "ҲИСОБОТЛАР",
                        "Вилоят ҳисоботлари"
                    )
                }
            }

            "REGIONAL_HEAD" -> {

                menu(
                    content,
                    "🧑‍🎨",
                    "ҲУНАРМАНДЛАР",
                    "Вилоят ҳунармандлари"
                ) {
                    showSection(
                        "ҲУНАРМАНДЛАР",
                        "Вилоят ҳунармандлари"
                    )
                }

                menu(
                    content,
                    "🗺",
                    "ТУМАНЛАР",
                    "Вилоят туманлари"
                ) {
                    showSection(
                        "ТУМАНЛАР",
                        "Вилоят туманлари"
                    )
                }

                menu(
                    content,
                    "📊",
                    "ҲИСОБОТЛАР",
                    "Вилоят ҳисоботлари"
                ) {
                    showSection(
                        "ҲИСОБОТЛАР",
                        "Вилоят ҳисоботлари"
                    )
                }
            }

            "DISTRICT_HEAD" -> {

                menu(
                    content,
                    "🧑‍🎨",
                    "ҲУНАРМАНДЛАР",
                    "Туман ҳунармандлари"
                ) {
                    showSection(
                        "ҲУНАРМАНДЛАР",
                        "Туман ҳунармандлари"
                    )
                }

                menu(
                    content,
                    "📊",
                    "ҲИСОБОТЛАР",
                    "Туман ҳисоботлари"
                ) {
                    showSection(
                        "ҲИСОБОТЛАР",
                        "Туман ҳисоботлари"
                    )
                }
            }

            "ARTISAN" -> {

                menu(
                    content,
                    "👤",
                    "ПРОФИЛИМ",
                    "Шахсий маълумотлар"
                ) {
                    showSection(
                        "ПРОФИЛИМ",
                        "Менинг профилим"
                    )
                }

                menu(
                    content,
                    "🧑‍🎨",
                    "МАҲСУЛОТЛАРИМ",
                    "Менинг маҳсулотларим"
                ) {
                    showSection(
                        "МАҲСУЛОТЛАРИМ",
                        "Менинг маҳсулотларим"
                    )
                }
            }
        }

        content.addView(
            button("ЧИҚИШ", red) {
                logout()
            },
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                58
            ).apply {
                setMargins(0, 25, 0, 10)
            }
        )

        scroll.addView(content)

        main.addView(
            scroll,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.MATCH_PARENT
            )
        )

        setContentView(main)
    }

    private fun menu(
    parent: LinearLayout,
    icon: String,
    title: String,
    description: String,
    action: () -> Unit
) {
    val card = LinearLayout(this)
    card.orientation = LinearLayout.HORIZONTAL
    card.gravity = Gravity.CENTER_VERTICAL
    card.setPadding(22, 12, 22, 12)
    card.setBackgroundColor(white)

    card.setOnClickListener {
        action()
    }

    val iconView = centerLabel(icon, 34f, gold)

    card.addView(
        iconView,
        LinearLayout.LayoutParams(
            76,
            86
        )
    )

    val info = LinearLayout(this)
    info.orientation = LinearLayout.VERTICAL
    info.gravity = Gravity.CENTER_VERTICAL
    info.setPadding(18, 0, 10, 0)

    info.addView(
        label(title, 20f, dark, true),
        LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        )
    )

    info.addView(
        label(description, 14f, gray),
        LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply {
            topMargin = 5
        }
    )

    card.addView(
        info,
        LinearLayout.LayoutParams(
            0,
            LinearLayout.LayoutParams.MATCH_PARENT,
            1f
        )
    )

    parent.addView(
        card,
        LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            108
        ).apply {
            setMargins(0, 0, 0, 16)
        }
    )
}

    private fun showEmployees() {

        val main = root()

        val scroll = ScrollView(this)

        val content = LinearLayout(this)
        content.orientation = LinearLayout.VERTICAL
        content.setPadding( 16, 0, 16, 0)

        content.addView(
            centerLabel(
                "👤  ХОДИМЛАР",
                25f,
                dark,
                true
            ).apply {
                setPadding(0, 10, 0, 20)
            }
        )

        val status = centerLabel(
            "Маълумотлар юкланмоқда...",
            16f,
            gray
        )

        content.addView(
            status,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                setMargins(0, 15, 0, 20)
            }
        )

        val back = button("← БОШ САҲИФАГА") {

            val role =
                getSharedPreferences(
                    "auth",
                    MODE_PRIVATE
                ).getString("role", "") ?: ""

            showHome(role)
        }

        content.addView(
            back,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                58
            ).apply {
                setMargins(0, 25, 0, 0)
            }
        )

        scroll.addView(content)

        main.addView(
            scroll,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.MATCH_PARENT
            )
        )

        setContentView(main)

        loadEmployees(content, status)
    }

    private fun loadEmployees(
        content: LinearLayout,
        status: TextView
    ) {

        Thread {

            try {

                val token =
                    getSharedPreferences(
                        "auth",
                        MODE_PRIVATE
                    ).getString(
                        "access_token",
                        ""
                    ) ?: ""

                val connection =
                    URL(
                        "$apiUrl/api/v1/admin/employees"
                    ).openConnection()
                            as HttpURLConnection

                connection.requestMethod = "GET"

                connection.setRequestProperty(
                    "Authorization",
                    "Bearer $token"
                )

                connection.connectTimeout = 10000
                connection.readTimeout = 10000

                val code = connection.responseCode

                val stream =
                    if (code in 200..299)
                        connection.inputStream
                    else
                        connection.errorStream

                val response =
                    stream?.bufferedReader()?.use {
                        it.readText()
                    } ?: ""

                if (code !in 200..299) {

                    runOnUiThread {
                        status.text =
                            "Маълумот олишда хатолик: HTTP $code"
                    }

                    return@Thread
                }

                runOnUiThread {

                    status.visibility = View.GONE

                    try {

                        val json = JSONObject(response)

                        val array =
                            when {
                                json.has("items") ->
                                    json.optJSONArray("items")

                                json.has("employees") ->
                                    json.optJSONArray("employees")

                                else -> null
                            }

                        if (array == null) {

                            val box = TextView(this)

                            box.text = response
                            box.textSize = 18f
                            box.setTextColor(gray)
                            box.setPadding( 16, 0, 16, 0)

                            content.addView(box, 1)

                            return@runOnUiThread
                        }

                        for (i in 0 until array.length()) {

                            val employee =
                                array.getJSONObject(i)

                            val name =
                                employee.optString(
                                    "full_name",
                                    employee.optString(
                                        "name",
                                        "Номи кўрсатилмаган"
                                    )
                                )

                            val phone =
                                employee.optString(
                                    "phone",
                                    "—"
                                )

                            val role =
                                employee.optString(
                                    "role",
                                    "—"
                                )

                            val active =
                                employee.optBoolean(
                                    "is_active",
                                    true
                                )

                            val card =
                                LinearLayout(this)

                            card.orientation =
                                LinearLayout.VERTICAL

                            card.setPadding( 16, 0, 16, 0)

                            card.setBackgroundColor(
                                white
                            )

                            val title =
                                label(
                                    name,
                                    17f,
                                    dark,
                                    true
                                )

                            val details =
                                label(
                                    "$phone\n$role",
                                    14f,
                                    gray
                                )

                            val state =
                                label(
                                    if (active)
                                        "● ACTIVE"
                                    else
                                        "● INACTIVE",
                                    14f,
                                    if (active)
                                        green
                                    else
                                        red,
                                    true
                                )

                            card.addView(title)
                            card.addView(details)
                            card.addView(state)

                            content.addView(
                                card,
                                1 + i
                            )

                            val params = LinearLayout.LayoutParams(
                                LinearLayout.LayoutParams.MATCH_PARENT,
                                105
                            )
                            params.setMargins(0, 0, 0, 10)
                            card.layoutParams = params
                        }

                        if (array.length() == 0) {

                            status.visibility =
                                View.VISIBLE

                            status.text =
                                "Ҳозирча ходимлар мавжуд эмас"
                        }

                    } catch (e: Exception) {

                        status.visibility =
                            View.VISIBLE

                        status.text =
                            "Маълумот формати: ${e.message}"
                    }
                }

                connection.disconnect()

            } catch (e: Exception) {

                runOnUiThread {
                    status.text =
                        "Серверга уланиб бўлмади:\n${e.message}"
                }
            }

        }.start()
    }

    private fun showSection(
        titleText: String,
        description: String
    ) {

        val main = root()

        val content = LinearLayout(this)

        content.orientation = LinearLayout.VERTICAL
        content.gravity = Gravity.CENTER_HORIZONTAL
        content.setPadding( 16, 0, 16, 0)

        content.addView(logo(100, 75))

        content.addView(
            centerLabel(
                titleText,
                25f,
                dark,
                true
            ).apply {
                setPadding(0, 30, 0, 10)
            }
        )

        content.addView(
            centerLabel(
                description,
                17f,
                gray
            ).apply {
                setPadding(10, 10, 10, 30)
            }
        )

        content.addView(
            centerLabel(
                "Backend маълумотлари билан ишлаш қисми",
                15f,
                gray
            )
        )

        val backButton = button("← БОШ САҲИФАГА") {

                val role =
                    getSharedPreferences(
                        "auth",
                        MODE_PRIVATE
                    ).getString(
                        "role",
                        ""
                    ) ?: ""

                showHome(role)
            }
        content.addView(
            backButton,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                58
            ).apply {
                leftMargin = 0
                topMargin = 45
                rightMargin = 0
                bottomMargin = 0
            }
        )

        main.addView(
            content,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.MATCH_PARENT
            )
        )

        setContentView(main)
    }

    private fun roleName(role: String): String =
        when (role) {
            "SUPER_ADMIN" -> "SUPER ADMIN"
            "REGIONAL_HEAD" -> "ВИЛОЯТ РАҲБАРИ"
            "REGIONAL_MANAGER" -> "ВИЛОЯТ БОШҚАРУВИ"
            "DISTRICT_HEAD" -> "ТУМАН РАҲБАРИ"
            "ARTISAN" -> "ҲУНАРМАНД"
            else -> role
        }

    private fun logout() {

        getSharedPreferences(
            "auth",
            MODE_PRIVATE
        )
            .edit()
            .clear()
            .commit()

        finishAndRemoveTask()
    }
}






