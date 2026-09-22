package cn.jiajian.yanxu;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import org.json.*;

/** Native authenticated HTTP only; redirects are rejected and tokens never enter a WebView. */
final class CloudApi {
  static final class Failure extends IOException {
    final int status;
    Failure(int status, String message) { super(message); this.status = status; }
  }
  static JSONObject request(CloudSession session, String method, String path, JSONObject data) throws Exception {
    if (!session.valid()) throw new Failure(401, "登录已到期，请重新登录");
    return request(session.server, session.token, method, path,
        data == null ? null : data.toString().getBytes(StandardCharsets.UTF_8), "application/json");
  }
  static JSONObject request(String server, String token, String method, String path, byte[] body, String type)
      throws Exception {
    if (!path.startsWith("/api/") || path.contains("..")) throw new IllegalArgumentException("接口路径无效");
    URL endpoint = new URL(CloudSession.normalize(server) + path);
    if (!endpoint.getProtocol().equals("https") && !endpoint.getProtocol().equals("http"))
      throw new IOException("服务地址无效");
    HttpURLConnection conn = (HttpURLConnection) endpoint.openConnection();
    conn.setInstanceFollowRedirects(false); conn.setConnectTimeout(15000); conn.setReadTimeout(60000);
    conn.setRequestMethod(method);
    if (token != null) conn.setRequestProperty("Authorization", "Bearer " + token);
    conn.setRequestProperty("Accept", "application/json");
    try {
      if (body != null) {
        conn.setDoOutput(true); conn.setRequestProperty("Content-Type", type);
        conn.setFixedLengthStreamingMode(body.length);
        try (OutputStream out = conn.getOutputStream()) { out.write(body); }
      }
      int code = conn.getResponseCode();
      if (code / 100 != 2) {
        String message = switch (code) {
          case 401 -> "账号或密码错误，或登录已到期";
          case 403 -> "当前账号没有此操作权限";
          case 404, 405, 501 -> "当前服务尚未支持此功能，请检查服务版本";
          case 409 -> "资料状态已变化，请刷新后重试";
          case 413 -> "文件超过服务容量限制，原件已保留";
          default -> "服务请求未成功（" + code + "），请重试";
        };
        throw new Failure(code, message);
      }
      try (InputStream in = conn.getInputStream()) {
        ByteArrayOutputStream out = new ByteArrayOutputStream(); byte[] buffer = new byte[8192]; int n;
        while ((n = in.read(buffer)) != -1) {
          if (out.size() + n > 8 * 1024 * 1024) throw new IOException("服务返回过大");
          out.write(buffer, 0, n);
        }
        return out.size() == 0 ? new JSONObject() : new JSONObject(out.toString("UTF-8"));
      }
    } finally { conn.disconnect(); }
  }
  static String id(String id) {
    if (id == null || !id.matches("[A-Za-z0-9_-]{1,128}")) throw new IllegalArgumentException("人员编号无效");
    return id;
  }
}
