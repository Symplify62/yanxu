package cn.jiajian.yanxu;

import android.app.*;
import android.content.*;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.widget.*;

final class UpdateDialog {
  static AppPage show(Activity a) {
    int pad = (int) (24 * a.getResources().getDisplayMetrics().density);
    AppPage dialog = new AppPage(a, "应用更新", true);
    LinearLayout box = dialog.body;
    TextView version = new TextView(a);
    version.setText("当前版本 " + AppUpdater.versionName(a));
    version.setTextSize(22);
    version.setTextColor(AppUi.INK);
    version.setPadding(0, pad, 0, pad);
    box.addView(version);
    Switch automatic = new Switch(a);
    automatic.setText("自动更新");
    automatic.setChecked(AppUpdater.automatic(a));
    automatic.setPadding(0, pad / 2, 0, pad / 2);
    box.addView(automatic);
    TextView state = new TextView(a);
    state.setTextSize(14);
    state.setTextColor(AppUi.GREEN);
    state.setPadding(0, pad / 2, 0, 0);
    box.addView(state);
    TextView note = new TextView(a);
    note.setTextSize(13);
    note.setTextColor(AppUi.MUTED);
    note.setText("录音和上传期间暂缓安装");
    note.setPadding(0, pad / 2, 0, pad / 2);
    box.addView(note);
    dialog.action(-1, "检查更新", true, () -> {});
    automatic.setOnCheckedChangeListener(
        (b, on) -> {
          AppUpdater.prefs(a).edit().putBoolean("automatic", on).apply();
          AppUpdater.schedule(a);
          if (on) {
            AppUpdater.prefs(a).edit().putLong("nextCheck", 0).apply();
            AppUpdater.kick(a, false);
          }
        });
    Handler handler = new Handler(Looper.getMainLooper());
    Runnable refresh =
        new Runnable() {
          public void run() {
            if (!dialog.isShowing()) return;
            state.setText(AppUpdater.message(a));
            String s = AppUpdater.state(a);
            automatic.setEnabled(!"installing".equals(s));
            Button button = dialog.getButton(AlertDialog.BUTTON_POSITIVE);
            button.setEnabled(
                !java.util.Arrays.asList("checking", "downloading", "installing").contains(s));
            button.setText(
                "permission".equals(s)
                    ? "允许安装更新"
                    : "confirm".equals(s)
                        ? "确认安装"
                        : AppUpdater.release(a) != null ? "安装更新" : "检查更新");
            handler.postDelayed(this, 500);
          }
        };
    dialog.setOnShowListener(
        v -> {
          dialog
              .getButton(AlertDialog.BUTTON_POSITIVE)
              .setOnClickListener(
                  b -> {
                    String s = AppUpdater.state(a);
                    if ("permission".equals(s)) {
                      AppUpdater.prefs(a).edit().putBoolean("resumeInstall", true).apply();
                      a.startActivity(
                          new Intent(
                              Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                              Uri.parse("package:" + a.getPackageName())));
                    } else if ("confirm".equals(s)) UpdateInstaller.confirm(a);
                    else AppUpdater.kick(a, true);
                  });
          handler.post(refresh);
        });
    dialog.setOnDismissListener(v -> handler.removeCallbacks(refresh));
    dialog.show();
    return dialog;
  }
}
