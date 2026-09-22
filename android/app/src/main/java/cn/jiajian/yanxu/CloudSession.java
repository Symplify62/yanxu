package cn.jiajian.yanxu;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.security.MessageDigest;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import org.json.*;

/** One active login. The token is encrypted with a non-exportable Android Keystore key. */
final class CloudSession {
  private static final String KEY = "yanxu.session.aes.v1";
  final String server, token, accountId;
  final JSONObject account;
  final long expiresAt;

  CloudSession(String server, String token, JSONObject account, long expiresAt) throws Exception {
    this.server = normalize(server);
    this.token = token;
    this.account = new JSONObject(account.toString());
    this.accountId = account.getString("id");
    this.expiresAt = expiresAt;
    if (token.isEmpty() || accountId.isEmpty()) throw new IllegalArgumentException("会话无效");
  }

  boolean allows(String permission) {
    JSONArray permissions = account.optJSONArray("permissions");
    if (permissions != null) for (int i = 0; i < permissions.length(); i++)
      if (permission.equals(permissions.optString(i))) return true;
    return false;
  }

  boolean valid() { return expiresAt > System.currentTimeMillis(); }
  String scope() { return scope(server, accountId); }
  static String scope(String server, String account) {
    try {
      byte[] hash = MessageDigest.getInstance("SHA-256").digest(
          (normalize(server) + "\n" + account).getBytes(StandardCharsets.UTF_8));
      StringBuilder out = new StringBuilder();
      for (byte b : hash) out.append(String.format("%02x", b & 255));
      return out.toString();
    } catch (Exception e) { throw new IllegalStateException(e); }
  }
  static String normalize(String server) { return server.trim().replaceAll("/+$", ""); }

  static synchronized CloudSession current(Context context) {
    try {
      String encrypted = context.getSharedPreferences("cloud-session", 0).getString("sealed", "");
      if (encrypted.isEmpty()) return null;
      JSONObject envelope = new JSONObject(encrypted);
      Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
      cipher.init(Cipher.DECRYPT_MODE, key(), new GCMParameterSpec(128,
          Base64.decode(envelope.getString("iv"), Base64.NO_WRAP)));
      byte[] plain = cipher.doFinal(Base64.decode(envelope.getString("ciphertext"), Base64.NO_WRAP));
      JSONObject data = new JSONObject(new String(plain, StandardCharsets.UTF_8));
      CloudSession session = new CloudSession(data.getString("server"), data.getString("token"),
          data.getJSONObject("account"), data.getLong("expiresAt"));
      return session.server.equals(normalize(LocalStore.server(context))) ? session : null;
    } catch (Exception unavailable) { return null; }
  }

  static synchronized void save(Context context, CloudSession session) throws Exception {
    JSONObject data = new JSONObject().put("server", session.server).put("token", session.token)
        .put("account", session.account).put("expiresAt", session.expiresAt);
    Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
    cipher.init(Cipher.ENCRYPT_MODE, key());
    byte[] sealed = cipher.doFinal(data.toString().getBytes(StandardCharsets.UTF_8));
    JSONObject envelope = new JSONObject().put("iv", Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP))
        .put("ciphertext", Base64.encodeToString(sealed, Base64.NO_WRAP));
    if (!context.getSharedPreferences("cloud-session", 0).edit()
        .putString("sealed", envelope.toString()).commit()) throw new IllegalStateException("登录状态未能保存");
  }
  static synchronized void clear(Context context) {
    context.getSharedPreferences("cloud-session", 0).edit().clear().commit();
  }
  static boolean same(Context context, CloudSession expected) {
    CloudSession now = current(context);
    return now != null && expected != null && now.scope().equals(expected.scope())
        && now.token.equals(expected.token);
  }
  private static SecretKey key() throws Exception {
    KeyStore store = KeyStore.getInstance("AndroidKeyStore"); store.load(null);
    if (store.containsAlias(KEY)) return (SecretKey) store.getKey(KEY, null);
    KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
    generator.init(new KeyGenParameterSpec.Builder(KEY, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
        .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());
    return generator.generateKey();
  }
}
