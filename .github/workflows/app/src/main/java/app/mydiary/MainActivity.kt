package app.mydiary

import android.annotation.SuppressLint
import android.app.Activity
import android.content.SharedPreferences
import android.graphics.Color
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import androidx.webkit.WebViewAssetLoader
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject
import kotlin.concurrent.thread

class MainActivity : Activity() {
    private lateinit var web: WebView
    private lateinit var vault: SharedPreferences
    private val host = "appassets.androidplatform.net"

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))
        window.statusBarColor = Color.parseColor("#111111")
        window.navigationBarColor = Color.parseColor("#111111")

        // Пароль хранится зашифрованным ключом из Android Keystore
        val key = MasterKey.Builder(this).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
        vault = EncryptedSharedPreferences.create(
            this, "secure_vault", key,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )

        val loader = WebViewAssetLoader.Builder()
            .setDomain(host)
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()

        web = WebView(this)
        setContentView(web)
        web.setBackgroundColor(Color.parseColor("#111111"))
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.settings.allowFileAccess = false
        web.settings.allowContentAccess = false
        web.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? =
                loader.shouldInterceptRequest(request.url)

            // Внешние ссылки в приложении не открываем: мост доступен только нашей странице
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                return request.url.host != host
            }
        }
        web.addJavascriptInterface(Bridge(), "Android")
        web.loadUrl("https://$host/assets/index.html")
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (web.canGoBack()) web.goBack() else super.onBackPressed()
    }

    inner class Bridge {
        // Вызов Python (netschoolpy) в фоне; результат возвращается в страницу
        @JavascriptInterface
        fun call(id: String, method: String, args: String) {
            thread {
                val out = try {
                    Python.getInstance().getModule("nsbridge").callAttr("handle", method, args).toString()
                } catch (e: Throwable) {
                    JSONObject().put("ok", false).put("error", e.message ?: e.toString()).toString()
                }
                web.post {
                    web.evaluateJavascript("window.__nsDone(${JSONObject.quote(id)},${JSONObject.quote(out)})", null)
                }
            }
        }

        @JavascriptInterface
        fun vaultGet(k: String): String = vault.getString(k, "") ?: ""

        @JavascriptInterface
        fun vaultSet(k: String, v: String): Boolean {
            vault.edit().putString(k, v).apply()
            return true
        }

        @JavascriptInterface
        fun vaultDel(k: String) {
            vault.edit().remove(k).apply()
        }
    }
}
