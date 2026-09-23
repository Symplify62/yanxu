package cn.jiajian.yanxu;

import android.app.Activity;
import android.app.Dialog;
import android.graphics.Typeface;
import android.os.Build;
import android.view.*;
import android.widget.*;
import java.util.HashMap;
import java.util.Map;

/** Full-page mobile task: stable navigation, independently scrolling body and reachable actions. */
final class AppPage extends Dialog {
  final LinearLayout body, footer;
  private final LinearLayout page, stage;
  private final Button back;
  private Runnable backAction = this::dismiss;
  private final Map<Integer, Button> buttons = new HashMap<>();

  AppPage(Activity a, String title, boolean scrollable) {
    super(a, android.R.style.Theme_Material_Light_NoActionBar);
    page = AppUi.column(a);
    page.setBackgroundColor(AppUi.BG);
    LinearLayout nav = AppUi.row(a);
    nav.setPadding(AppUi.dp(a, 8), 0, AppUi.dp(a, 16), 0);
    back = AppUi.quiet(a, "‹", () -> backAction.run());
    back.setTextSize(30);
    back.setContentDescription("返回");
    nav.addView(back, new LinearLayout.LayoutParams(AppUi.dp(a, 48), AppUi.dp(a, 52)));
    TextView name = AppUi.text(a, title, 18, AppUi.INK);
    name.setTypeface(null, Typeface.BOLD);
    nav.addView(name, new LinearLayout.LayoutParams(0, -2, 1));
    page.addView(nav, new LinearLayout.LayoutParams(-1, AppUi.dp(a, 56)));
    stage = AppUi.column(a);
    stage.setGravity(Gravity.CENTER_HORIZONTAL);
    body = AppUi.column(a);
    body.setPadding(AppUi.dp(a, 20), AppUi.dp(a, 12), AppUi.dp(a, 20), AppUi.dp(a, 24));
    if (scrollable) {
      ScrollView scroll = new ScrollView(a);
      scroll.setFillViewport(true);
      scroll.setClipToPadding(false);
      scroll.addView(body);
      stage.addView(scroll, new LinearLayout.LayoutParams(-1, -1));
    } else stage.addView(body, new LinearLayout.LayoutParams(-1, -1));
    page.addView(stage, new LinearLayout.LayoutParams(-1, 0, 1));
    footer = AppUi.row(a);
    footer.setPadding(AppUi.dp(a, 20), AppUi.dp(a, 10), AppUi.dp(a, 20), AppUi.dp(a, 12));
    footer.setVisibility(View.GONE);
    page.addView(footer);
    page.setOnApplyWindowInsetsListener(
        (v, i) -> {
          int l, t, r, b;
          if (Build.VERSION.SDK_INT >= 30) {
            android.graphics.Insets s =
                i.getInsets(
                    WindowInsets.Type.systemBars()
                        | WindowInsets.Type.displayCutout()
                        | WindowInsets.Type.ime());
            l = s.left;
            t = s.top;
            r = s.right;
            b = s.bottom;
          } else {
            l = i.getSystemWindowInsetLeft();
            t = i.getSystemWindowInsetTop();
            r = i.getSystemWindowInsetRight();
            b = i.getSystemWindowInsetBottom();
          }
          int gutter =
              Math.max(
                  0, (a.getResources().getDisplayMetrics().widthPixels - AppUi.dp(a, 680)) / 2);
          v.setPadding(l + gutter, t, r + gutter, b);
          return i;
        });
    setContentView(page);
    Window w = getWindow();
    if (w != null) {
      if (Build.VERSION.SDK_INT >= 30) w.setDecorFitsSystemWindows(false);
      w.setStatusBarColor(AppUi.BG);
      w.setNavigationBarColor(AppUi.BG);
      w.getDecorView()
          .setSystemUiVisibility(
              View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
      w.setSoftInputMode(
          WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE
              | WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN);
    }
  }

  void onBack(Runnable action) {
    backAction = action;
  }

  @Override
  public void onBackPressed() {
    backAction.run();
  }

  Button action(int which, String title, boolean primary, Runnable run) {
    Button b = AppUi.button(getContext(), title, primary, run);
    LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, -2, 1);
    if (footer.getChildCount() > 0) p.leftMargin = AppUi.dp(getContext(), 10);
    footer.addView(b, p);
    footer.setVisibility(View.VISIBLE);
    buttons.put(which, b);
    return b;
  }

  Button getButton(int which) {
    return buttons.get(which);
  }

  @Override
  public void show() {
    super.show();
    getWindow().setLayout(-1, -1);
    page.requestApplyInsets();
  }
}
