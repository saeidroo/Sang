package com.tekar.tradingsignalai;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.HttpAuthHandler;
import android.webkit.SafeBrowsingResponse;
import android.webkit.SslErrorHandler;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.net.http.SslError;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;

public class MainActivity extends Activity {
    private static final String PREFS = "tsai_mobile";
    private static final String KEY_URL = "server_url";
    private LinearLayout root;
    private ProgressBar progress;
    private WebView web;
    private TextView status;
    private String serverUrl = "";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        getWindow().setStatusBarColor(Color.TRANSPARENT);
        getWindow().setNavigationBarColor(Color.TRANSPARENT);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            getWindow().setStatusBarContrastEnforced(false);
            getWindow().setNavigationBarContrastEnforced(false);
        }
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        serverUrl = getPreferences(MODE_PRIVATE).getString(KEY_URL, "");
        buildUi();
        if (serverUrl.isEmpty()) showServerDialog(); else loadServer();
    }

    private int dp(float v) {
        return (int)(v * getResources().getDisplayMetrics().density + 0.5f);
    }

    private GradientDrawable bg(int color, int radius) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color);
        d.setCornerRadius(dp(radius));
        return d;
    }

    private void buildUi() {
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(13,14,17));

        LinearLayout bar = new LinearLayout(this);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding(dp(14), dp(8), dp(10), dp(8));
        bar.setBackgroundColor(Color.rgb(20,21,25));

        TextView brand = new TextView(this);
        brand.setText("TradingSignalAI Pro");
        brand.setTextColor(Color.WHITE);
        brand.setTextSize(17);
        brand.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        bar.addView(brand, new LinearLayout.LayoutParams(0, dp(44), 1));

        Button reload = smallButton("↻");
        reload.setOnClickListener(v -> { if (web != null) web.reload(); });
        bar.addView(reload);

        Button settings = smallButton("⚙");
        settings.setOnClickListener(v -> showServerDialog());
        bar.addView(settings);
        root.addView(bar, new LinearLayout.LayoutParams(-1, dp(60)));

        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100);
        progress.setProgressTintList(android.content.res.ColorStateList.valueOf(Color.rgb(214,177,94)));
        progress.setIndeterminate(false);
        root.addView(progress, new LinearLayout.LayoutParams(-1, dp(3)));

        web = new WebView(this);
        web.setBackgroundColor(Color.rgb(13,14,17));
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setJavaScriptCanOpenWindowsAutomatically(false);
        s.setSupportMultipleWindows(false);
        s.setMediaPlaybackRequiresUserGesture(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) s.setSafeBrowsingEnabled(true);

        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, false);

        web.setWebChromeClient(new WebChromeClient() {
            @Override public void onProgressChanged(WebView view, int p) {
                progress.setProgress(p);
                progress.setVisibility(p >= 100 ? View.GONE : View.VISIBLE);
            }
            @Override public boolean onCreateWindow(WebView view, boolean dialog, boolean userGesture, android.os.Message resultMsg) {
                return false;
            }
        });

        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (sameOrigin(uri.toString())) return false;
                try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); }
                catch (Exception ignored) { Toast.makeText(MainActivity.this, "امکان بازکردن پیوند وجود ندارد", Toast.LENGTH_SHORT).show(); }
                return true;
            }

            @Override public void onReceivedHttpAuthRequest(WebView view, HttpAuthHandler handler, String host, String realm) {
                showAuthDialog(handler, host, realm);
            }

            @Override public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                handler.cancel();
                setStatus("گواهی امنیتی سرور معتبر نیست؛ اتصال مسدود شد");
            }

            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) setStatus("ارتباط برقرار نشد؛ آدرس سرور و اینترنت را بررسی کنید");
            }

            @Override public void onPageFinished(WebView view, String url) {
                setStatus("متصل به سرور");
            }
        });

        root.addView(web, new LinearLayout.LayoutParams(-1, 0, 1));
        status = new TextView(this);
        status.setText("آماده اتصال");
        status.setTextColor(Color.LTGRAY);
        status.setTextSize(11);
        status.setPadding(dp(12), dp(7), dp(12), dp(7));
        status.setBackgroundColor(Color.rgb(20,21,25));
        root.addView(status, new LinearLayout.LayoutParams(-1, -2));
        setContentView(root);
        ViewCompat.setOnApplyWindowInsetsListener(root, (view, insets) -> {
            Insets bars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            return insets;
        });
        ViewCompat.requestApplyInsets(root);
    }

    private Button smallButton(String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextColor(Color.rgb(214,177,94));
        b.setTextSize(18);
        b.setAllCaps(false);
        b.setMinWidth(dp(44));
        b.setMinHeight(dp(44));
        b.setBackground(bg(Color.rgb(39,39,43), 12));
        return b;
    }

    private void setStatus(String value) {
        if (status != null) status.setText(value);
    }

    private boolean sameOrigin(String candidate) {
        try {
            Uri a = Uri.parse(serverUrl), b = Uri.parse(candidate);
            return TextUtils.equals(a.getScheme(), b.getScheme())
                && TextUtils.equals(a.getHost(), b.getHost())
                && effectivePort(a) == effectivePort(b);
        } catch (Exception e) {
            return false;
        }
    }

    private int effectivePort(Uri uri) {
        if (uri.getPort() != -1) return uri.getPort();
        return "https".equalsIgnoreCase(uri.getScheme()) ? 443 : 80;
    }

    private void showServerDialog() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(20), dp(8), dp(20), 0);

        TextView help = new TextView(this);
        help.setText("آدرس امن سرور را وارد کنید. نمونه: https://trade.example.com");
        help.setTextColor(Color.DKGRAY);
        help.setTextSize(14);
        box.addView(help);

        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setHint("https://your-domain.com");
        input.setInputType(InputType.TYPE_TEXT_VARIATION_URI);
        input.setText(serverUrl);
        box.addView(input);

        new AlertDialog.Builder(this).setTitle("اتصال به موتور اصلی").setView(box)
            .setPositiveButton("اتصال", (d,w) -> {
                String value = input.getText().toString().trim();
                if (!value.matches("(?i)^https://[a-z0-9.-]+(:[0-9]{1,5})?(/.*)?$")) {
                    Toast.makeText(this, "فقط آدرس HTTPS معتبر مجاز است", Toast.LENGTH_LONG).show();
                    return;
                }
                serverUrl = value.replaceAll("/+$", "");
                getPreferences(MODE_PRIVATE).edit().putString(KEY_URL, serverUrl).apply();
                loadServer();
            }).setNegativeButton("انصراف", null).show();
    }

    private void showAuthDialog(HttpAuthHandler handler, String host, String realm) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(20), dp(4), dp(20), 0);

        EditText user = new EditText(this);
        user.setSingleLine(true);
        user.setHint("نام کاربری");
        box.addView(user);

        EditText pass = new EditText(this);
        pass.setSingleLine(true);
        pass.setHint("رمز عبور");
        pass.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        box.addView(pass);

        AlertDialog dialog = new AlertDialog.Builder(this).setTitle("ورود امن به سرور")
            .setMessage("اطلاعات ورود در تنظیمات برنامه ذخیره نمی‌شود.")
            .setView(box)
            .setPositiveButton("ورود", (d,w) -> handler.proceed(user.getText().toString(), pass.getText().toString()))
            .setNegativeButton("لغو", (d,w) -> handler.cancel()).create();
        dialog.setOnCancelListener(d -> handler.cancel());
        dialog.show();
    }

    private void loadServer() {
        if (web == null || serverUrl.isEmpty()) return;
        setStatus("در حال اتصال به موتور اصلی…");
        web.loadUrl(serverUrl + "/");
    }

    @Override public void onBackPressed() {
        if (web != null && web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }

    @Override protected void onDestroy() {
        if (web != null) {
            web.stopLoading();
            web.loadUrl("about:blank");
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }
}
