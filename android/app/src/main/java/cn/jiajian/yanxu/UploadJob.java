package cn.jiajian.yanxu;

import android.app.job.*;
import java.io.*;
import java.net.*;
import java.security.*;
import java.util.*;
import org.json.*;

public class UploadJob extends JobService {
  private volatile boolean stopped;

  private static class Rejected extends IOException {
    final int status;

    Rejected(int status) {
      super("HTTP " + status);
      this.status = status;
    }
  }

  @Override
  public boolean onStartJob(JobParameters params) {
    stopped = false;
    new Thread(
            () -> {
              boolean retry = false;
              for (File d : LocalStore.all(this)) {
                if (stopped) break;
                try {
                  JSONObject m = LocalStore.read(d);
                  if (!Arrays.asList("saved", "uploading", "retry").contains(m.optString("state")))
                    continue;
                  upload(d, m);
                } catch (Exception e) {
                  boolean permanent = e instanceof Rejected;
                  retry |= !permanent;
                  try {
                    JSONObject m = LocalStore.read(d);
                    String message =
                        permanent
                            ? (((Rejected) e).status == 413 ? "文件超过服务容量配置，录音已保留" : "服务拒绝此文件，录音已保留")
                            : "等待网络或服务恢复";
                    m.put("state", permanent ? "blocked" : "retry").put("message", message);
                    LocalStore.save(d, m);
                  } catch (Exception ignored) {
                  }
                }
              }
              jobFinished(params, retry);
            },
            "yanxu-upload")
        .start();
    return true;
  }

  @Override
  public boolean onStopJob(JobParameters p) {
    stopped = true;
    return true;
  }

  private void upload(File d, JSONObject m) throws Exception {
    File f = new File(d, m.getString("filename"));
    MessageDigest hash = MessageDigest.getInstance("SHA-256");
    byte[] buffer = new byte[1024 * 1024];
    try (InputStream in = new FileInputStream(f)) {
      int n;
      while ((n = in.read(buffer)) > 0) hash.update(buffer, 0, n);
    }
    StringBuilder sha = new StringBuilder();
    for (byte b : hash.digest()) sha.append(String.format("%02x", b & 255));
    JSONObject create =
        new JSONObject()
            .put("client_id", m.getString("client_id"))
            .put("title", m.getString("title"))
            .put("total_bytes", f.length())
            .put("sha256", sha.toString())
            .put(
                "extension",
                m.getString("filename").substring(m.getString("filename").lastIndexOf('.') + 1))
            .put("interrupted", m.optBoolean("interrupted"));
    JSONObject session =
        request(
            "POST",
            "/api/recordings",
            create.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8),
            null,
            true);
    String id = session.getString("id"), token = session.getString("uploadToken");
    int chunk = session.getInt("chunkSize");
    JSONArray parts =
        request("GET", "/api/uploads/" + id, null, token, false).getJSONArray("parts");
    Set<Integer> done = new HashSet<>();
    for (int i = 0; i < parts.length(); i++) done.add(parts.getJSONObject(i).getInt("part_no"));
    m.put("state", "uploading");
    LocalStore.save(d, m);
    try (RandomAccessFile in = new RandomAccessFile(f, "r")) {
      long total = f.length();
      for (int i = 0; (long) i * chunk < total; i++) {
        if (stopped) throw new IOException("stopped");
        if (done.contains(i)) continue;
        in.seek((long) i * chunk);
        byte[] data = new byte[(int) Math.min(chunk, total - (long) i * chunk)];
        in.readFully(data);
        request("PUT", "/api/uploads/" + id + "/parts/" + i, data, token, false);
        m.put("progress", (int) (((long) i * chunk + data.length) * 100 / total));
        LocalStore.save(d, m);
      }
    }
    JSONObject result =
        request("POST", "/api/uploads/" + id + "/complete", new byte[0], token, false);
    m.put("duration", result.optDouble("duration"));
    m.put("state", "uploaded").put("server_id", id).put("message", "已上传，自动处理中");
    LocalStore.save(d, m);
  }

  private JSONObject request(String method, String path, byte[] body, String token, boolean json)
      throws Exception {
    URL url = new URL(LocalStore.server(this) + path);
    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
    conn.setConnectTimeout(15000);
    conn.setReadTimeout(120000);
    conn.setRequestMethod(method);
    if (token != null) conn.setRequestProperty("X-Upload-Token", token);
    if (json) conn.setRequestProperty("Content-Type", "application/json");
    try {
      if (body != null) {
        conn.setDoOutput(true);
        conn.setFixedLengthStreamingMode(body.length);
        try (OutputStream out = conn.getOutputStream()) {
          out.write(body);
        }
      }
      int code = conn.getResponseCode();
      if (code >= 400 && code < 500 && code != 408 && code != 429) throw new Rejected(code);
      if (code / 100 != 2) throw new IOException("HTTP " + code);
      try (InputStream in = conn.getInputStream()) {
        return new JSONObject(
            new String(LocalStore.bytes(in), java.nio.charset.StandardCharsets.UTF_8));
      }
    } finally {
      conn.disconnect();
    }
  }
}
