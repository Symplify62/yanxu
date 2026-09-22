package cn.jiajian.yanxu;

import android.content.Context;
import java.io.IOException;
import java.net.URI;
import org.json.*;

/** Immutable recording ownership. No token or sample path is serialized into meeting metadata. */
final class RecordingIdentity {
  static final class LoginRequired extends IOException {
    LoginRequired() { super("请登录录制时的账号后继续上传，录音已保留"); }
  }
  static JSONObject capture(Context context, JSONObject roster) throws Exception {
    CloudSession session = CloudSession.current(context);
    if (session == null || !session.valid() || !session.allows("record")) throw new LoginRequired();
    JSONArray selected = roster.getJSONArray("participants"), ids = new JSONArray();
    for (int i = 0; i < selected.length(); i++) {
      String id = selected.getJSONObject(i).optString("cloudPersonId");
      if (id.isEmpty()) throw new IOException("请先将已选人员关联到云端，或取消选择后录音");
      ids.put(new JSONObject().put("personId",id));
    }
    return new JSONObject().put("version",1).put("ownerAccountId",session.accountId)
        .put("server",session.server).put("participants",ids).put("rosterClientId",java.util.UUID.randomUUID().toString());
  }

  /** Freeze the upload mode before recording/import; later login never adopts guest audio. */
  static JSONObject captureForRecording(Context context, JSONObject roster) throws Exception {
    JSONArray selected = roster.getJSONArray("participants");
    CloudSession session = CloudSession.current(context);
    if (session != null && session.valid() && session.allows("record")) {
      return new JSONObject().put("recordingMode", "managed")
          .put("cloudIdentity", capture(context, roster))
          .put("participantsSnapshot", new JSONObject(roster.toString()));
    }
    if (selected.length() > 0) {
      if (session == null || !session.valid()) throw new LoginRequired();
      throw new IOException("当前账号不能使用参会名单，请取消选择后普通录音");
    }
    return new JSONObject().put("recordingMode", "anonymous")
        .put("uploadServer", serverOrigin(LocalStore.server(context)));
  }

  /** Recheck at service start, before microphone allocation or recording-file creation. */
  static JSONObject validateStart(Context context, JSONObject fragment) throws Exception {
    String mode = fragment.optString("recordingMode");
    if ("anonymous".equals(mode)) {
      if (fragment.has("cloudIdentity") || fragment.has("participantsSnapshot"))
        throw new IOException("普通录音不能携带参会名单");
      String server = serverOrigin(fragment.getString("uploadServer"));
      if (!server.equals(serverOrigin(LocalStore.server(context))))
        throw new IOException("服务已切换，请重新开始录音");
      return new JSONObject().put("recordingMode", "anonymous").put("uploadServer", server);
    }
    if (!"managed".equals(mode)) throw new IOException("录音方式无效，请重新开始");
    CloudSession owner = requireOwner(context, fragment);
    if (owner == null || !owner.allows("record")) throw new LoginRequired();
    JSONObject identity = fragment.getJSONObject("cloudIdentity");
    serverOrigin(identity.getString("server"));
    JSONObject roster = fragment.getJSONObject("participantsSnapshot");
    JSONArray ids = identity.getJSONArray("participants"), people = roster.getJSONArray("participants");
    if (ids.length() != people.length()) throw new IOException("参会名单已变化，请重新选择");
    java.util.HashSet<String> seen = new java.util.HashSet<>();
    for (int i = 0; i < ids.length(); i++) {
      String id = ids.getJSONObject(i).getString("personId");
      if (id.isEmpty() || !seen.add(id) || !id.equals(people.getJSONObject(i).getString("cloudPersonId")))
        throw new IOException("参会名单不一致，请重新选择");
    }
    return new JSONObject().put("recordingMode", "managed")
        .put("cloudIdentity", new JSONObject(identity.toString()))
        .put("participantsSnapshot", new JSONObject(roster.toString()));
  }

  static String serverOrigin(String value) throws IOException {
    try {
      String normalized = CloudSession.normalize(value);
      URI uri = new URI(normalized);
      if (!("https".equals(uri.getScheme()) || "http".equals(uri.getScheme()))
          || uri.getHost() == null || uri.getRawUserInfo() != null
          || uri.getRawQuery() != null || uri.getRawFragment() != null
          || (uri.getRawPath() != null && !uri.getRawPath().isEmpty())
          || uri.getPort() == 0 || uri.getPort() > 65535) throw new IOException();
      return normalized;
    } catch (Exception error) { throw new IOException("录音服务地址无效"); }
  }

  static CloudSession requireOwner(Context context, JSONObject metadata) throws Exception {
    JSONObject identity = metadata.optJSONObject("cloudIdentity");
    String mode = metadata.optString("recordingMode");
    if (identity == null) {
      if ("managed".equals(mode) || metadata.has("cloudIdentity")) throw new LoginRequired();
      if ("anonymous".equals(mode)) {
        if (metadata.has("participantsSnapshot")) throw new IOException("普通录音包含无效的参会信息");
        serverOrigin(metadata.getString("uploadServer"));
      } else if (!mode.isEmpty()) throw new IOException("录音方式无效，原件已保留");
      return null;
    }
    if (!mode.isEmpty() && !"managed".equals(mode)) throw new IOException("录音身份不一致，原件已保留");
    serverOrigin(identity.getString("server"));
    CloudSession session = CloudSession.current(context);
    if (session == null || !session.valid() || !session.server.equals(identity.getString("server"))
        || !session.accountId.equals(identity.getString("ownerAccountId"))) throw new LoginRequired();
    return session;
  }
  static boolean visible(Context context, JSONObject metadata) {
    try {
      CloudSession owner = requireOwner(context,metadata);
      return metadata.optJSONObject("cloudIdentity") == null || owner != null;
    } catch(Exception e) { return false; }
  }
}
