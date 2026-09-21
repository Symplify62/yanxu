package cn.jiajian.yanxu;

import java.io.*;
import java.nio.file.*;
import java.security.*;

public class UpdatePolicyTest {
  public static void main(String[] args) throws Exception {
    byte[] data = "signed-apk-fixture".getBytes();
    String sha = UpdatePolicy.hex(MessageDigest.getInstance("SHA-256").digest(data));
    String good = "https://yanxu.qjl666.xyz/app/releases/yanxu-8-" + sha.substring(0, 12) + ".apk";
    if (!UpdatePolicy.allows(good, 8, sha)) throw new AssertionError("Rejected trusted release");
    for (String bad :
        new String[] {
          good.replace("https:", "http:"),
          good.replace(".xyz", ".xyz.evil.test"),
          good.replace(".xyz", ".xyz:443"),
          good + "?redirect=x",
          good + "#x",
          good.replace("/app/", "/app/../app/"),
          good.replace("yanxu.qjl", "user@yanxu.qjl"),
          good.replace("/releases/", "/releases/%2e%2e/"),
          "file:///update.apk"
        })
      if (UpdatePolicy.allows(bad, 8, sha))
        throw new AssertionError("Accepted untrusted URL: " + bad);
    File f = File.createTempFile("yanxu-update-", ".apk");
    try {
      Files.write(f.toPath(), data);
      UpdatePolicy.verify(f, data.length, sha);
      for (int mode = 0; mode < 2; mode++) {
        try {
          UpdatePolicy.verify(f, data.length + mode, mode == 0 ? "0".repeat(64) : sha);
          throw new AssertionError("Accepted bad package");
        } catch (IOException expected) {
        }
      }
    } finally {
      f.delete();
    }
    if (!UpdatePolicy.identity("cn.jiajian.yanxu", 8, "sig", "sig", 8, 7))
      throw new AssertionError();
    if (UpdatePolicy.identity("cn.jiajian.yanxu", 8, "evil", "sig", 8, 7)
        || UpdatePolicy.identity("evil.app", 8, "sig", "sig", 8, 7)
        || UpdatePolicy.identity("cn.jiajian.yanxu", 7, "sig", "sig", 7, 8)
        || UpdatePolicy.identity("cn.jiajian.yanxu", 8, "sig", "sig", 9, 7))
      throw new AssertionError("Invalid release identity accepted");
    for (int mask = 0; mask < 8; mask++)
      if (UpdatePolicy.idle((mask & 1) != 0, (mask & 2) != 0, (mask & 4) != 0) != (mask == 0))
        throw new AssertionError("Recording/upload/install guard failed");
    System.out.println("PASS: update origin, integrity, identity, downgrade and busy guards");
  }
}
