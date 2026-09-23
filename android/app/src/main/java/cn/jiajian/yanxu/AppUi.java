package cn.jiajian.yanxu;

import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.*;

/** Shared mobile appearance. Business permissions and callbacks remain with the calling screen. */
final class AppUi {
  static final int BG = 0xfff7f8f4,
      SURFACE = Color.WHITE,
      INK = 0xff243b30,
      MUTED = 0xff68786e,
      GREEN = 0xff466b4f,
      PALE = 0xffe9efe6,
      LINE = 0xffe1e7df,
      DANGER = 0xffac463a;

  static int dp(Context c, int n) {
    return Math.round(n * c.getResources().getDisplayMetrics().density);
  }

  static GradientDrawable shape(Context c, int color, int radius, boolean border) {
    GradientDrawable d = new GradientDrawable();
    d.setColor(color);
    d.setCornerRadius(dp(c, radius));
    if (border) d.setStroke(dp(c, 1), LINE);
    return d;
  }

  static RippleDrawable ripple(Context c, int color, int radius, boolean border) {
    return new RippleDrawable(
        ColorStateList.valueOf(0x18466b4f), shape(c, color, radius, border), null);
  }

  static TextView text(Context c, String s, int sp, int color) {
    TextView t = new TextView(c);
    t.setText(s);
    t.setTextSize(sp);
    t.setTextColor(color);
    t.setIncludeFontPadding(false);
    return t;
  }

  static LinearLayout column(Context c) {
    LinearLayout b = new LinearLayout(c);
    b.setOrientation(1);
    return b;
  }

  static LinearLayout row(Context c) {
    LinearLayout b = new LinearLayout(c);
    b.setGravity(Gravity.CENTER_VERTICAL);
    return b;
  }

  static void buttonStyle(Button b, boolean primary) {
    Context c = b.getContext();
    b.setAllCaps(false);
    b.setTextSize(15);
    b.setTypeface(null, Typeface.NORMAL);
    b.setTextColor(
        new ColorStateList(
            new int[][] {new int[] {-android.R.attr.state_enabled}, new int[] {}},
            new int[] {0xff8e9d91, primary ? Color.WHITE : GREEN}));
    android.graphics.drawable.StateListDrawable backgrounds =
        new android.graphics.drawable.StateListDrawable();
    backgrounds.addState(
        new int[] {-android.R.attr.state_enabled}, shape(c, 0xffe4e9e1, 14, false));
    backgrounds.addState(new int[] {}, ripple(c, primary ? GREEN : PALE, 14, false));
    b.setBackground(backgrounds);
    b.setStateListAnimator(null);
    b.setElevation(0);
    b.setMinWidth(0);
    b.setMinimumWidth(0);
    b.setMinHeight(dp(c, 48));
    b.setMinimumHeight(dp(c, 48));
    b.setPadding(dp(c, 16), dp(c, 8), dp(c, 16), dp(c, 8));
  }

  static Button button(Context c, String s, boolean primary, Runnable action) {
    Button b = new Button(c);
    b.setText(s);
    buttonStyle(b, primary);
    b.setOnClickListener(v -> action.run());
    return b;
  }

  static Button quiet(Context c, String s, Runnable action) {
    Button b = button(c, s, false, action);
    b.setTextSize(14);
    b.setBackground(ripple(c, Color.TRANSPARENT, 10, false));
    return b;
  }

  static void input(EditText e) {
    Context c = e.getContext();
    e.setTextSize(16);
    e.setTextColor(INK);
    e.setHintTextColor(MUTED);
    e.setBackground(shape(c, SURFACE, 12, true));
    e.setPadding(dp(c, 14), dp(c, 12), dp(c, 14), dp(c, 12));
    e.setMinHeight(dp(c, 52));
  }

  static TextView section(Context c, String value) {
    TextView t = text(c, value, 13, MUTED);
    t.setPadding(dp(c, 4), dp(c, 24), dp(c, 4), dp(c, 10));
    return t;
  }

  static View item(Context c, String title, String detail, Runnable action) {
    LinearLayout r = row(c);
    r.setPadding(dp(c, 16), dp(c, 16), dp(c, 14), dp(c, 16));
    r.setMinimumHeight(dp(c, 64));
    r.setBackground(ripple(c, SURFACE, 14, false));
    LinearLayout copy = column(c);
    copy.addView(text(c, title, 16, INK));
    if (detail != null && !detail.isEmpty()) {
      TextView sub = text(c, detail, 13, MUTED);
      sub.setPadding(0, dp(c, 6), dp(c, 8), 0);
      copy.addView(sub);
    }
    r.addView(copy, new LinearLayout.LayoutParams(0, -2, 1));
    if (action != null) {
      TextView arrow = text(c, "›", 24, MUTED);
      r.addView(arrow);
      r.setOnClickListener(v -> action.run());
      r.setFocusable(true);
    }
    LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
    p.bottomMargin = dp(c, 6);
    r.setLayoutParams(p);
    return r;
  }

  static TextView avatar(Context c, String name, int size) {
    String initial = name.isEmpty() ? "人" : name.substring(0, name.offsetByCodePoints(0, 1));
    TextView t = text(c, initial, 24, GREEN);
    t.setGravity(Gravity.CENTER);
    t.setBackground(shape(c, PALE, size / 2, false));
    return t;
  }
}
