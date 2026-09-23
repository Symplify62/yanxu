package cn.jiajian.yanxu;

import android.app.job.*;
import android.content.*;
import java.io.*;
import java.util.*;
import org.json.*;

final class LocalStore {
  static final int JOB = 7011;

  static File root(Context c) {
    File d = new File(c.getFilesDir(), "recordings");
    d.mkdirs();
    return d;
  }

  static String server(Context c) {
    if (!"development".equals(BuildConfig.YANXU_ENVIRONMENT)) return BuildConfig.YANXU_SERVER_ORIGIN;
    return c.getSharedPreferences("settings", 0).getString("server", BuildConfig.YANXU_SERVER_ORIGIN);
  }

  static synchronized JSONObject read(File dir) throws Exception {
    try (InputStream in = new FileInputStream(new File(dir, "meta.json"))) {
      return new JSONObject(new String(bytes(in), java.nio.charset.StandardCharsets.UTF_8));
    }
  }

  static synchronized void save(File dir, JSONObject data) throws Exception {
    dir.mkdirs();
    File tmp = new File(dir, "meta.tmp");
    try (FileOutputStream out = new FileOutputStream(tmp)) {
      out.write(data.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
      out.getFD().sync();
    }
    if (!tmp.renameTo(new File(dir, "meta.json"))) throw new IOException("无法保存录音状态");
  }

  static List<File> all(Context c) {
    File[] a = root(c).listFiles(File::isDirectory);
    if (a == null) return new ArrayList<>();
    Arrays.sort(a, (x, y) -> Long.compare(y.lastModified(), x.lastModified()));
    return Arrays.asList(a);
  }

  static void enqueue(Context c) {
    JobInfo info =
        new JobInfo.Builder(JOB, new ComponentName(c, UploadJob.class))
            .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
            .setPersisted(true)
            .setBackoffCriteria(30000, JobInfo.BACKOFF_POLICY_EXPONENTIAL)
            .build();
    c.getSystemService(JobScheduler.class).schedule(info);
  }

  static void recover(Context c) {
    if (RecordingService.active) return;
    for (File d : all(c)) {
      try {
        JSONObject m = read(d);
        if ("recording".equals(m.optString("state")) || "paused".equals(m.optString("state"))) {
          File audio = new File(d, m.optString("filename", "audio.wav"));
          if (audio.length() > 44) {
            try (RandomAccessFile f = new RandomAccessFile(audio, "rw")) {
              header(f, audio.length() - 44);
              f.getFD().sync();
            }
            m.put("state", "saved");
            m.put("interrupted", true);
            m.put("duration", (audio.length() - 44) / 32000.0);
            m.put("message", "已恢复中断录音");
            save(d, m);
          }
        } else if ("uploading".equals(m.optString("state"))) {
          m.put("state", "saved");
          save(d, m);
        }
      } catch (Exception ignored) {
      }
    }
    enqueue(c);
  }

  static void header(RandomAccessFile f, long bytes) throws IOException {
    if (bytes > 0xffffffffL - 36) throw new IOException("WAV容量已到达当前格式上限");
    long pos = f.getFilePointer();
    f.seek(0);
    f.writeBytes("RIFF");
    le32(f, bytes + 36);
    f.writeBytes("WAVEfmt ");
    le32(f, 16);
    le16(f, 1);
    le16(f, 1);
    le32(f, 16000);
    le32(f, 32000);
    le16(f, 2);
    le16(f, 16);
    f.writeBytes("data");
    le32(f, bytes);
    f.seek(Math.max(44, pos));
  }

  static byte[] bytes(InputStream in) throws IOException {
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    byte[] b = new byte[8192];
    int n;
    while ((n = in.read(b)) > 0) out.write(b, 0, n);
    return out.toByteArray();
  }

  static void le32(RandomAccessFile f, long v) throws IOException {
    for (int i = 0; i < 4; i++) f.write((int) (v >> (8 * i)) & 255);
  }

  static void le16(RandomAccessFile f, int v) throws IOException {
    f.write(v & 255);
    f.write((v >> 8) & 255);
  }
}
