package cn.jiajian.yanxu;

import android.app.Instrumentation;
import android.content.Context;
import android.os.Bundle;
import java.io.File;
import java.nio.file.Files;
import org.json.JSONObject;

/**
 * Runs only in the separate test APK; never enables a test endpoint in the installed application.
 */
public class UpdateInstrumentation extends Instrumentation {
  @Override
  public void onCreate(Bundle args) {
    super.onCreate(args);
    start();
  }

  @Override
  public void onStart() {
    Bundle result = new Bundle();
    try {
      Context c = getTargetContext();
      File d = new File(c.getFilesDir(), "updates/test");
      JSONObject good =
          new JSONObject(new String(Files.readAllBytes(new File(d, "good.json").toPath())));
      JSONObject wrong =
          new JSONObject(new String(Files.readAllBytes(new File(d, "wrong.json").toPath())));
      AppUpdater.verifyPackage(c, good, new File(d, "good.apk"));
      try {
        AppUpdater.verifyPackage(c, wrong, new File(d, "wrong.apk"));
        throw new AssertionError("Foreign signer accepted");
      } catch (SecurityException expected) {
      }
      JSONObject mismatch = new JSONObject(good.toString());
      mismatch.put("versionCode", good.getLong("versionCode") + 1);
      try {
        AppUpdater.verifyPackage(c, mismatch, new File(d, "good.apk"));
        throw new AssertionError("Wrong version accepted");
      } catch (SecurityException expected) {
      }
      boolean active = RecordingService.active;
      try {
        RecordingService.active = true;
        if (AppUpdater.idle(c)) throw new AssertionError("Recording was not protected");
      } finally {
        RecordingService.active = active;
      }
      try {
        AppUpdater.importing = true;
        if (AppUpdater.idle(c)) throw new AssertionError("Import was not protected");
      } finally {
        AppUpdater.importing = false;
      }
      String oldState = AppUpdater.state(c), oldMessage = AppUpdater.message(c);
      long oldNext = AppUpdater.prefs(c).getLong("nextCheck", 0);
      try {
        AppUpdater.status(c, "downloading", "interrupted-test");
        AppUpdater.prefs(c).edit().putLong("nextCheck", Long.MAX_VALUE).commit();
        AppUpdater.recover(c);
        if (!"idle".equals(AppUpdater.state(c))
            || AppUpdater.prefs(c).getLong("nextCheck", -1) != 0)
          throw new AssertionError("Interrupted download did not recover");
      } finally {
        AppUpdater.status(c, oldState, oldMessage);
        AppUpdater.prefs(c).edit().putLong("nextCheck", oldNext).commit();
      }
      result.putString(
          "result", "PASS: real APK signature/package/version checks and recording guard");
      finish(-1, result);
    } catch (Throwable e) {
      result.putString("failure", e.toString());
      finish(1, result);
    }
  }
}
