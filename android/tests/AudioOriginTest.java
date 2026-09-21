package cn.jiajian.yanxu;

public class AudioOriginTest {
  public static void main(String[] args) {
    String path = "/recordings/a222afa8-93fd-4e7f-b63d-6235b19176b6/" + "f".repeat(64) + ".wav";
    String good = "https://audio.qjl666.xyz" + path;
    if (!AudioOrigin.allows(good) || !AudioOrigin.allows(good + "?attname=recording.wav"))
      throw new AssertionError("Valid audio rejected");
    for (String bad : new String[] {
      good.replace("https:", "http:"), good.replace("audio.qjl666.xyz", "audio.qjl666.xyz.evil.test"),
      good.replace("audio.qjl666.xyz", "evil@audio.qjl666.xyz"), good.replace(".xyz", ".xyz:8443"),
      good + "?redirect=https://evil.test", good + "#fragment", "file:///tmp/audio.wav",
      "https://audio.qjl666.xyz/anything.html", good.replace("/recordings/", "/recordings/../"), "invalid"
    }) {
      if (AudioOrigin.allows(bad)) throw new AssertionError("Unexpected origin accepted: " + bad);
    }
    System.out.println("Audio origin security checks passed");
  }
}
