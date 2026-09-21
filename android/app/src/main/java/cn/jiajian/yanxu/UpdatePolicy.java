package cn.jiajian.yanxu;

import java.io.*;
import java.net.URI;
import java.security.MessageDigest;

final class UpdatePolicy {
  static final String ORIGIN = "https://yanxu.qjl666.xyz";
  static final long MAX_BYTES = 100L * 1024 * 1024;

  static boolean allows(String url, long version, String sha) {
    try {
      URI u = new URI(url);
      return version > 0
          && sha.matches("[a-f0-9]{64}")
          && "https".equals(u.getScheme())
          && "yanxu.qjl666.xyz".equals(u.getHost())
          && u.getPort() == -1
          && u.getRawUserInfo() == null
          && u.getRawQuery() == null
          && u.getRawFragment() == null
          && ("/app/releases/yanxu-" + version + "-" + sha.substring(0, 12) + ".apk")
              .equals(u.getRawPath());
    } catch (Exception e) {
      return false;
    }
  }

  static String hex(byte[] bytes) {
    StringBuilder out = new StringBuilder();
    for (byte b : bytes) out.append(String.format("%02x", b & 255));
    return out.toString();
  }

  static void verify(File file, long size, String hash) throws Exception {
    if (size <= 0 || size > MAX_BYTES || file.length() != size) throw new IOException("安装包大小不符");
    MessageDigest digest = MessageDigest.getInstance("SHA-256");
    try (InputStream in = new FileInputStream(file)) {
      byte[] buffer = new byte[32768];
      int n;
      while ((n = in.read(buffer)) != -1) digest.update(buffer, 0, n);
    }
    if (!hex(digest.digest()).equals(hash)) throw new IOException("安装包校验未通过");
  }

  static boolean identity(
      String name,
      long version,
      String signer,
      String installedSigner,
      long offered,
      long installed) {
    return "cn.jiajian.yanxu".equals(name)
        && version == offered
        && version > installed
        && signer != null
        && signer.equals(installedSigner);
  }

  static boolean idle(boolean recording, boolean pendingUploads, boolean installing) {
    return !recording && !pendingUploads && !installing;
  }
}
