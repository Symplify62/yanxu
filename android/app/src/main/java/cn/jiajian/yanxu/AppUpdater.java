package cn.jiajian.yanxu;

import android.app.*;
import android.app.job.*;
import android.content.*;
import android.content.pm.*;
import android.os.*;
import java.io.*;
import java.net.*;
import java.security.MessageDigest;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.BooleanSupplier;
import org.json.*;

final class AppUpdater {
  static final Object GATE = new Object();
  static volatile boolean importing;
  static final int JOB = 7012;
  private static final AtomicBoolean working = new AtomicBoolean();

  static SharedPreferences prefs(Context c) {
    return c.getSharedPreferences("updates", 0);
  }

  static boolean automatic(Context c) {
    return prefs(c).getBoolean("automatic", true);
  }

  static File apk(Context c) {
    File d = new File(c.getFilesDir(), "updates");
    d.mkdirs();
    return new File(d, "ready.apk");
  }

  static long version(Context c) {
    try {
      PackageInfo p = c.getPackageManager().getPackageInfo(c.getPackageName(), 0);
      return Build.VERSION.SDK_INT >= 28 ? p.getLongVersionCode() : p.versionCode;
    } catch (Exception e) {
      throw new IllegalStateException(e);
    }
  }

  static String versionName(Context c) {
    try {
      return c.getPackageManager().getPackageInfo(c.getPackageName(), 0).versionName;
    } catch (Exception e) {
      return "未知";
    }
  }

  static String state(Context c) {
    return prefs(c).getString("state", "idle");
  }

  static String message(Context c) {
    return prefs(c).getString("message", "自动检查并下载，空闲时安装");
  }

  static boolean needsAction(Context c) {
    return java.util.Arrays.asList("permission", "confirm").contains(state(c))
        || ("failed".equals(state(c)) && release(c) != null);
  }

  static void recover(Context c) {
    if (working.get()) return;
    if (java.util.Arrays.asList("checking", "downloading").contains(state(c))) {
      prefs(c).edit().putLong("nextCheck", 0).apply();
      status(c, "idle", "更新中断，将自动重试");
    } else if ("installing".equals(state(c)) && !installing(c)) {
      prefs(c).edit().putBoolean("manualOnly", true).apply();
      status(c, "failed", "安装未完成，可稍后重试");
    }
  }

  static void status(Context c, String state, String message) {
    prefs(c).edit().putString("state", state).putString("message", message).apply();
  }

  static boolean installing(Context c) {
    if (!"installing".equals(state(c))) return false;
    int id = prefs(c).getInt("session", -1);
    return id >= 0 && c.getPackageManager().getPackageInstaller().getSessionInfo(id) != null;
  }

  static boolean pendingUploads(Context c) {
    if (importing) return true;
    for (File d : LocalStore.all(c)) {
      try {
        String s = LocalStore.read(d).optString("state");
        if (java.util.Arrays.asList("recording", "paused", "saved", "uploading", "retry")
            .contains(s)) return true;
      } catch (Exception e) {
        return true;
      }
    }
    return false;
  }

  static boolean idle(Context c) {
    return UpdatePolicy.idle(RecordingService.active, pendingUploads(c), installing(c));
  }

  static void schedule(Context c) {
    JobScheduler scheduler = c.getSystemService(JobScheduler.class);
    if (!automatic(c)) {
      scheduler.cancel(JOB);
      return;
    }
    if (scheduler.getPendingJob(JOB) == null)
      scheduler.schedule(
          new JobInfo.Builder(JOB, new ComponentName(c, UpdateJob.class))
              .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
              .setRequiresBatteryNotLow(true)
              .setBackoffCriteria(15 * 60 * 1000L, JobInfo.BACKOFF_POLICY_EXPONENTIAL)
              .setPeriodic(6 * 60 * 60 * 1000L)
              .setPersisted(true)
              .build());
  }

  static void kick(Context c, boolean manual) {
    Context app = c.getApplicationContext();
    new Thread(() -> run(app, manual, () -> false), "yanxu-updates").start();
  }

  static boolean run(Context c, boolean manual, BooleanSupplier cancelled) {
    if ((!manual && !automatic(c)) || !working.compareAndSet(false, true)) return true;
    try {
      if (installing(c)) return true;
      JSONObject cached = release(c);
      if (cached != null && cached.getLong("versionCode") <= version(c)) {
        prefs(c).edit().remove("release").remove("manualOnly").remove("session").apply();
        apk(c).delete();
        cached = null;
        status(c, "latest", "已是最新版本");
      }
      if (cached != null && !apk(c).isFile()) prefs(c).edit().putLong("nextCheck", 0).apply();
      boolean ready = cached != null && apk(c).isFile();
      boolean installRequested = manual && ready;
      if (!ready && (manual || System.currentTimeMillis() >= prefs(c).getLong("nextCheck", 0))) {
        status(c, "checking", "正在检查更新");
        JSONObject info =
            new JSONObject(
                new String(fetchManifest(cancelled), java.nio.charset.StandardCharsets.UTF_8));
        prefs(c)
            .edit()
            .putLong("nextCheck", System.currentTimeMillis() + 6 * 60 * 60 * 1000L)
            .apply();
        if (!info.optBoolean("available") || info.getLong("versionCode") <= version(c)) {
          status(c, "latest", "已是最新版本");
          return true;
        }
        validateRelease(info);
        if (info.getInt("minSdk") > Build.VERSION.SDK_INT) {
          status(c, "failed", "新版暂不支持当前安卓版本");
          return true;
        }
        if (cached == null || cached.getLong("versionCode") != info.getLong("versionCode"))
          prefs(c).edit().remove("manualOnly").apply();
        status(c, "downloading", "正在下载 " + info.getString("versionName"));
        download(c, info, cancelled);
        verifyPackage(c, info, apk(c));
        prefs(c).edit().putString("release", info.toString()).apply();
        cached = info;
        ready = true;
        status(c, "ready", "新版 " + info.getString("versionName") + " 已准备好");
      }
      if (cancelled.getAsBoolean()) return false;
      if (ready
          && (installRequested || (automatic(c) && !prefs(c).getBoolean("manualOnly", false))))
        UpdateInstaller.install(c, cached, installRequested);
      return true;
    } catch (Exception e) {
      if (e instanceof SecurityException) {
        apk(c).delete();
        prefs(c).edit().remove("release").apply();
      }
      prefs(c)
          .edit()
          .putBoolean("manualOnly", true)
          .putLong("nextCheck", System.currentTimeMillis() + 15 * 60 * 1000L)
          .apply();
      status(c, "failed", e instanceof SecurityException ? "安装包身份校验未通过" : "更新暂未完成，可稍后重试");
      android.util.Log.w("YanxuUpdate", "Update failed: " + e.getClass().getSimpleName());
      return false;
    } finally {
      working.set(false);
    }
  }

  static JSONObject release(Context c) {
    try {
      String value = prefs(c).getString("release", null);
      return value == null ? null : new JSONObject(value);
    } catch (Exception e) {
      return null;
    }
  }

  static void validateRelease(JSONObject m) throws Exception {
    long v = m.getLong("versionCode");
    String sha = m.getString("sha256");
    long size = m.getLong("size");
    if (!UpdatePolicy.allows(m.getString("url"), v, sha)
        || !"cn.jiajian.yanxu".equals(m.getString("packageName"))
        || size <= 0
        || size > UpdatePolicy.MAX_BYTES
        || m.getString("versionName").length() > 40
        || m.getInt("minSdk") < 26) throw new SecurityException("Invalid update manifest");
  }

  private static HttpURLConnection open(String url) throws IOException {
    HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
    conn.setInstanceFollowRedirects(false);
    conn.setConnectTimeout(15000);
    conn.setReadTimeout(30000);
    conn.setRequestProperty("Accept-Encoding", "identity");
    return conn;
  }

  private static byte[] fetchManifest(BooleanSupplier cancelled) throws Exception {
    HttpURLConnection conn = open(UpdatePolicy.ORIGIN + "/app/update.json");
    try {
      if (conn.getResponseCode() != 200) throw new IOException("Update unavailable");
      try (InputStream in = conn.getInputStream();
          ByteArrayOutputStream out = new ByteArrayOutputStream()) {
        byte[] b = new byte[4096];
        int n;
        while ((n = in.read(b)) != -1) {
          if (cancelled.getAsBoolean() || out.size() + n > 16384)
            throw new IOException("Invalid manifest");
          out.write(b, 0, n);
        }
        return out.toByteArray();
      }
    } finally {
      conn.disconnect();
    }
  }

  private static void download(Context c, JSONObject m, BooleanSupplier cancelled)
      throws Exception {
    File target = apk(c), temp = new File(target.getParentFile(), "download.part");
    HttpURLConnection conn = open(m.getString("url"));
    try {
      if (conn.getResponseCode() != 200) throw new IOException("Download unavailable");
      long count = 0;
      try (InputStream in = conn.getInputStream();
          FileOutputStream out = new FileOutputStream(temp)) {
        byte[] b = new byte[32768];
        int n;
        while ((n = in.read(b)) != -1) {
          count += n;
          if (cancelled.getAsBoolean() || count > m.getLong("size"))
            throw new IOException("Download interrupted");
          out.write(b, 0, n);
        }
        out.getFD().sync();
      }
      UpdatePolicy.verify(temp, m.getLong("size"), m.getString("sha256"));
      verifyPackage(c, m, temp);
      if (!temp.renameTo(target)) throw new IOException("Save failed");
    } finally {
      conn.disconnect();
      temp.delete();
    }
  }

  static void verifyPackage(Context c, JSONObject m, File f) throws Exception {
    validateRelease(m);
    UpdatePolicy.verify(f, m.getLong("size"), m.getString("sha256"));
    int flag =
        Build.VERSION.SDK_INT >= 28
            ? PackageManager.GET_SIGNING_CERTIFICATES
            : PackageManager.GET_SIGNATURES;
    PackageInfo offered = c.getPackageManager().getPackageArchiveInfo(f.getAbsolutePath(), flag);
    PackageInfo installed = c.getPackageManager().getPackageInfo(c.getPackageName(), flag);
    if (offered == null
        || !UpdatePolicy.identity(
            offered.packageName,
            Build.VERSION.SDK_INT >= 28 ? offered.getLongVersionCode() : offered.versionCode,
            signer(offered),
            signer(installed),
            m.getLong("versionCode"),
            version(c))
        || offered.applicationInfo.minSdkVersion > Build.VERSION.SDK_INT)
      throw new SecurityException("Package identity mismatch");
  }

  private static String signer(PackageInfo p) throws Exception {
    Signature[] signatures =
        Build.VERSION.SDK_INT >= 28 ? p.signingInfo.getApkContentsSigners() : p.signatures;
    if (signatures == null || signatures.length != 1)
      throw new SecurityException("Unexpected signer");
    return UpdatePolicy.hex(
        MessageDigest.getInstance("SHA-256").digest(signatures[0].toByteArray()));
  }

  static void notifyAction(Context c) {
    NotificationManager n = c.getSystemService(NotificationManager.class);
    n.createNotificationChannel(
        new NotificationChannel("updates", "应用更新", NotificationManager.IMPORTANCE_DEFAULT));
    Intent open = new Intent(c, MainActivity.class).putExtra("showUpdates", true);
    PendingIntent pi =
        PendingIntent.getActivity(
            c, 7021, open, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    try {
      n.notify(
          7021,
          new Notification.Builder(c, "updates")
              .setSmallIcon(android.R.drawable.stat_sys_download_done)
              .setContentTitle("言序更新")
              .setContentText(message(c))
              .setContentIntent(pi)
              .setAutoCancel(true)
              .build());
    } catch (SecurityException ignored) {
      /* Settings remains available when notifications are disabled. */
    }
  }
}
