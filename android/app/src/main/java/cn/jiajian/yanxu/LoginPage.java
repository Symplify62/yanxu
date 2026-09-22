package cn.jiajian.yanxu;

import android.app.Activity;
import android.app.Dialog;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.view.WindowInsets;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Full-page, cancellable login. Opening or completing this page never starts audio capture. */
final class LoginPage extends Dialog {
  interface Submit { void login(String username, String password); }
  private static final int BG = Color.rgb(251, 252, 248);
  private static final int GREEN = Color.rgb(70, 107, 79);
  private static final int INK = Color.rgb(39, 61, 49);
  private final EditText username, password;
  private final TextView error;
  private final Button submit;
  private final LinearLayout page;
  private final Submit listener;
  private boolean submitting;

  LoginPage(Activity activity, Submit listener) {
    super(activity, android.R.style.Theme_Material_Light_NoActionBar);
    this.listener = listener;
    page = new LinearLayout(activity);
    page.setOrientation(LinearLayout.VERTICAL);
    page.setBackgroundColor(BG);
    page.setPadding(dp(24), dp(12), dp(24), dp(20));
    page.setOnApplyWindowInsetsListener((view, insets) -> {
      int left, top, right, bottom;
      if (Build.VERSION.SDK_INT >= 30) {
        android.graphics.Insets safe = insets.getInsets(WindowInsets.Type.systemBars()
            | WindowInsets.Type.displayCutout() | WindowInsets.Type.ime());
        left = safe.left; top = safe.top; right = safe.right; bottom = safe.bottom;
      } else {
        left = insets.getSystemWindowInsetLeft(); top = insets.getSystemWindowInsetTop();
        right = insets.getSystemWindowInsetRight(); bottom = insets.getSystemWindowInsetBottom();
      }
      view.setPadding(dp(24) + left, dp(12) + top, dp(24) + right, dp(20) + bottom);
      return insets;
    });
    Button back = new Button(activity);
    back.setText("返回"); back.setContentDescription("返回录音");
    back.setAllCaps(false); back.setTextColor(GREEN); back.setBackgroundColor(Color.TRANSPARENT);
    back.setOnClickListener(v -> dismiss());
    LinearLayout.LayoutParams backLayout = new LinearLayout.LayoutParams(dp(76), dp(48));
    backLayout.gravity = Gravity.START;
    page.addView(back, backLayout);
    ScrollView scroll = new ScrollView(activity);
    scroll.setFillViewport(true);
    LinearLayout content = new LinearLayout(activity);
    content.setOrientation(LinearLayout.VERTICAL);
    int width = Math.min(activity.getResources().getDisplayMetrics().widthPixels - dp(48), dp(440));
    LinearLayout.LayoutParams contentLayout = new LinearLayout.LayoutParams(width, -2);
    contentLayout.gravity = Gravity.CENTER_HORIZONTAL;
    LinearLayout centered = new LinearLayout(activity);
    centered.setOrientation(LinearLayout.VERTICAL);
    centered.setGravity(Gravity.CENTER_HORIZONTAL);
    centered.setPadding(0, dp(30), 0, dp(24));
    centered.addView(content, contentLayout);
    centered.addOnLayoutChangeListener((v, l, t, r, b, oldL, oldT, oldR, oldB) -> {
      int wanted = Math.min(r - l, dp(440));
      if (wanted > 0 && content.getLayoutParams().width != wanted) {
        content.getLayoutParams().width = wanted; content.requestLayout();
      }
    });
    scroll.addView(centered);
    page.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
    TextView brand = label(activity, "言序", 28, GREEN);
    brand.setTypeface(null, Typeface.BOLD);
    content.addView(brand);
    TextView title = label(activity, "账号登录", 22, INK);
    title.setTypeface(null, Typeface.BOLD);
    title.setPadding(0, dp(22), 0, dp(18));
    content.addView(title);
    content.addView(label(activity, "账号", 14, INK));
    username = new EditText(activity);
    username.setSingleLine(true); username.setContentDescription("账号");
    username.setInputType(InputType.TYPE_CLASS_TEXT);
    username.setImeOptions(EditorInfo.IME_ACTION_NEXT);
    content.addView(username, new LinearLayout.LayoutParams(-1, dp(52)));
    TextView passwordLabel = label(activity, "密码", 14, INK);
    passwordLabel.setPadding(0, dp(18), 0, 0);
    content.addView(passwordLabel);
    password = new EditText(activity);
    password.setSingleLine(true); password.setContentDescription("密码");
    password.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
    password.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO);
    password.setImeOptions(EditorInfo.IME_ACTION_DONE);
    password.setOnEditorActionListener((v, action, event) -> {
      if (action == EditorInfo.IME_ACTION_DONE) { send(); return true; }
      return false;
    });
    content.addView(password, new LinearLayout.LayoutParams(-1, dp(52)));
    error = label(activity, "", 13, Color.rgb(165, 69, 53));
    error.setPadding(0, dp(12), 0, 0); error.setVisibility(View.GONE);
    error.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
    content.addView(error);
    submit = new Button(activity);
    submit.setText("登录"); submit.setAllCaps(false); submit.setTextColor(Color.WHITE);
    GradientDrawable background = new GradientDrawable(); background.setColor(GREEN); background.setCornerRadius(dp(10));
    submit.setBackground(background); submit.setOnClickListener(v -> send());
    LinearLayout.LayoutParams action = new LinearLayout.LayoutParams(-1, dp(52));
    action.topMargin = dp(26); content.addView(submit, action);
    setContentView(page);
    setOnDismissListener(d -> password.setText(""));
    Window window = getWindow();
    if (window != null) {
      if (Build.VERSION.SDK_INT >= 30) window.setDecorFitsSystemWindows(false);
      window.setStatusBarColor(BG); window.setNavigationBarColor(BG);
      window.getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
      window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE | WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN);
    }
  }

  @Override public void show() {
    super.show();
    Window window = getWindow();
    if (window != null) window.setLayout(-1, -1);
    page.requestApplyInsets();
  }

  private void send() {
    if (submitting) return;
    String name = username.getText().toString().trim(), secret = password.getText().toString();
    if (name.isEmpty() || secret.isEmpty()) { failed("请输入账号和密码"); return; }
    submitting = true; error.setVisibility(View.GONE);
    submit.setEnabled(false); submit.setText("正在登录…");
    username.setEnabled(false); password.setEnabled(false);
    listener.login(name, secret);
  }

  void failed(String message) {
    submitting = false; submit.setEnabled(true); submit.setText("登录");
    username.setEnabled(true); password.setEnabled(true);
    error.setText(message); error.setVisibility(View.VISIBLE);
  }

  private int dp(int value) { return Math.round(value * getContext().getResources().getDisplayMetrics().density); }
  private TextView label(Activity activity, String value, int size, int color) {
    TextView text = new TextView(activity); text.setText(value); text.setTextSize(size); text.setTextColor(color); return text;
  }
}
