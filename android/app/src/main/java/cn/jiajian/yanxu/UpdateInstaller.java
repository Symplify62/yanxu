package cn.jiajian.yanxu;

import android.app.*;
import android.content.*;
import android.content.pm.PackageInstaller;
import android.os.Build;
import java.io.*;
import java.lang.ref.WeakReference;
import org.json.JSONObject;

final class UpdateInstaller {
  static final String ACTION = "cn.jiajian.yanxu.UPDATE_RESULT";
  static WeakReference<Activity> foreground = new WeakReference<>(null);
  private static Intent confirmation;

  static void install(Context c, JSONObject release, boolean manual) throws Exception {
    synchronized (AppUpdater.GATE) {
      if (!AppUpdater.idle(c)) {
        if (!AppUpdater.installing(c)) AppUpdater.status(c, "deferred", "录音或上传结束后更新");
        return;
      }
      if (!c.getPackageManager().canRequestPackageInstalls()) {
        AppUpdater.status(c, "permission", "需允许言序安装更新");
        AppUpdater.notifyAction(c);
        return;
      }
      if (!manual && AppUpdater.prefs(c).getBoolean("manualOnly", false)) return;
      try {
        AppUpdater.verifyPackage(c, release, AppUpdater.apk(c));
      } catch (Exception e) {
        AppUpdater.apk(c).delete();
        AppUpdater.prefs(c).edit().remove("release").apply();
        throw e;
      }
      PackageInstaller installer = c.getPackageManager().getPackageInstaller();
      int prior = AppUpdater.prefs(c).getInt("session", -1);
      if (prior >= 0) {
        try {
          installer.abandonSession(prior);
        } catch (Exception ignored) {
        }
      }
      PackageInstaller.SessionParams params =
          new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
      params.setAppPackageName(c.getPackageName());
      params.setSize(release.getLong("size"));
      if (Build.VERSION.SDK_INT >= 31)
        params.setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_NOT_REQUIRED);
      int id = installer.createSession(params);
      AppUpdater.prefs(c).edit().putInt("session", id).putBoolean("manualOnly", false).commit();
      AppUpdater.status(c, "installing", "正在安装更新");
      try (PackageInstaller.Session session = installer.openSession(id);
          InputStream in = new FileInputStream(AppUpdater.apk(c))) {
        try (OutputStream out = session.openWrite("base.apk", 0, release.getLong("size"))) {
          byte[] b = new byte[32768];
          int n;
          while ((n = in.read(b)) != -1) out.write(b, 0, n);
          session.fsync(out);
        }
        Intent callback = new Intent(c, UpdateReceiver.class).setAction(ACTION);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 31) flags |= PendingIntent.FLAG_MUTABLE;
        PendingIntent receiver = PendingIntent.getBroadcast(c, id, callback, flags);
        session.commit(receiver.getIntentSender());
      } catch (Exception e) {
        try {
          installer.abandonSession(id);
        } catch (Exception ignored) {
        }
        AppUpdater.prefs(c).edit().remove("session").apply();
        throw e;
      }
    }
  }

  static void result(Context c, Intent intent) {
    int id = intent.getIntExtra(PackageInstaller.EXTRA_SESSION_ID, -1);
    if (id != AppUpdater.prefs(c).getInt("session", -2)) return;
    int status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE);
    if (status == PackageInstaller.STATUS_PENDING_USER_ACTION) {
      confirmation = intent.getParcelableExtra(Intent.EXTRA_INTENT);
      AppUpdater.prefs(c).edit().putBoolean("manualOnly", true).apply();
      AppUpdater.status(c, "confirm", "系统需要确认安装");
      Activity activity = foreground.get();
      if (activity != null && !activity.isFinishing() && AppUpdater.idle(c)) confirm(activity);
      else AppUpdater.notifyAction(c);
    } else {
      confirmation = null;
      AppUpdater.prefs(c)
          .edit()
          .remove("session")
          .putBoolean("manualOnly", status != PackageInstaller.STATUS_SUCCESS)
          .apply();
      if (status == PackageInstaller.STATUS_SUCCESS) {
        AppUpdater.prefs(c).edit().remove("release").apply();
        AppUpdater.apk(c).delete();
        AppUpdater.status(c, "latest", "更新已完成");
      } else {
        AppUpdater.status(
            c,
            "failed",
            status == PackageInstaller.STATUS_FAILURE_ABORTED ? "已取消更新，可稍后重试" : "安装未完成，可稍后重试");
        AppUpdater.notifyAction(c);
      }
    }
  }

  static void confirm(Activity a) {
    synchronized (AppUpdater.GATE) {
      if (!AppUpdater.idle(a)) {
        AppUpdater.status(a, "confirm", "录音或上传结束后确认安装");
        return;
      }
      if (confirmation != null) {
        try {
          AppUpdater.status(a, "installing", "等待系统完成安装");
          a.startActivity(confirmation);
        } catch (Exception e) {
          AppUpdater.status(a, "confirm", "请重新确认安装");
        }
      } else {
        // A killed process loses the system Intent; recreate our own validated session on user
        // action.
        AppUpdater.kick(a, true);
      }
    }
  }
}
