package cn.jiajian.yanxu;

import android.content.Context;
import java.io.IOException;
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
  static CloudSession requireOwner(Context context, JSONObject metadata) throws Exception {
    JSONObject identity = metadata.optJSONObject("cloudIdentity");
    if (identity == null) return null;
    CloudSession session = CloudSession.current(context);
    if (session == null || !session.valid() || !session.server.equals(identity.getString("server"))
        || !session.accountId.equals(identity.getString("ownerAccountId"))) throw new LoginRequired();
    return session;
  }
  static boolean visible(Context context, JSONObject metadata) {
    JSONObject identity = metadata.optJSONObject("cloudIdentity"); if (identity == null) return true;
    try { return requireOwner(context,metadata) != null; } catch(Exception e) { return false; }
  }
}
