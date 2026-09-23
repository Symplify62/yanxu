package cn.jiajian.yanxu;

import java.net.URI;

/** The sole external origin used for verified recording playback and downloads. */
final class AudioOrigin {
  static boolean allows(String value) {
    return allows(value, "https://audio.qjl666.xyz");
  }

  static boolean allows(String value, String expectedOrigin) {
    try {
      URI uri = URI.create(value);
      URI expected = URI.create(expectedOrigin);
      String query = uri.getRawQuery();
      return "https".equalsIgnoreCase(uri.getScheme())
          && "https".equalsIgnoreCase(expected.getScheme())
          && expected.getHost() != null
          && expected.getHost().equalsIgnoreCase(uri.getHost())
          && expected.getRawPath().isEmpty()
          && expected.getRawQuery() == null
          && expected.getRawFragment() == null
          && expected.getPort() == -1
          && uri.getUserInfo() == null
          && (uri.getPort() == -1 || uri.getPort() == 443)
          && uri.getFragment() == null
          && uri.getRawPath().matches("/recordings/[0-9a-f-]{36}/[0-9a-f]{64}\\.(wav|m4a|mp3|webm)")
          && (query == null || query.matches("attname=[A-Za-z0-9._%-]+"));
    } catch (IllegalArgumentException | NullPointerException ignored) {
      return false;
    }
  }
}
