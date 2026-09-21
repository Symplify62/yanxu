package cn.jiajian.yanxu;

import android.app.*;
import android.content.*;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.widget.*;

final class UpdateDialog {
  static void show(Activity a) {
    int pad = (int) (24 * a.getResources().getDisplayMetrics().density);
    LinearLayout box = new LinearLayout(a);
    box.setOrientation(1);
    box.setPadding(pad, pad / 2, pad, 0);
    TextView version = new TextView(a);
    version.setText("当前版本 " + AppUpdater.versionName(a));
    version.setTextSize(15);
    box.addView(version);
    Switch automatic = new Switch(a);
    automatic.setText("自动更新");
    automatic.setChecked(AppUpdater.automatic(a));
    automatic.setPadding(0, pad / 2, 0, pad / 2);
    box.addView(automatic);
    TextView state = new TextView(a);
    state.setTextSize(14);
    box.addView(state);
    TextView note = new TextView(a);
    note.setTextSize(12);
    note.setText("录音和上传期间暂缓安装");
    note.setPadding(0, pad / 2, 0, pad / 2);
    box.addView(note);
    AlertDialog dialog =
        new AlertDialog.Builder(a)
            .setTitle("应用更新")
            .setView(box)
            .setNegativeButton("关闭", null)
            .setPositiveButton("检查更新", null)
            .create();
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
  }
}
