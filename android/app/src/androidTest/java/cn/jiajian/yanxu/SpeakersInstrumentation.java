package cn.jiajian.yanxu;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import java.util.ArrayList;
import java.util.List;

/** Only packaged in the instrumentation APK. Never exposes a production test endpoint. */
public class SpeakersInstrumentation extends Instrumentation {
  private Bundle args;

  @Override
  public void onCreate(Bundle values) {
    super.onCreate(values);
    args = values == null ? new Bundle() : values;
    start();
  }

  @Override
  public void onStart() {
    Bundle out = new Bundle();
    Activity activity = null;
    int resultCode = -1;
    try {
      Context context = getTargetContext();
      if (!android.os.Build.FINGERPRINT.contains("generic")
          && !android.os.Build.MODEL.contains("sdk_gphone"))
        throw new IllegalStateException("This test runner is limited to the isolated emulator");
      String mode = args.getString("mode", "checks");
      if ("setup".equals(mode)) {
        context
            .getSharedPreferences("settings", 0)
            .edit()
            .putString("server", "http://10.0.2.2:5196")
            .commit();
        AppUpdater.prefs(context).edit().putBoolean("automatic", false).commit();
        AppUpdater.schedule(context);
        out.putString("result", "PASS: isolated local API and updates disabled for emulator tests");
      } else if ("cloudchecks".equals(mode)) {
        out.putString("result", CloudIdentityChecks.run(context));
      } else if ("guestchecks".equals(mode)) {
        out.putString("identity", GuestRecordingChecks.run(context));
        out.putString("result", GuestRecordingApiChecks.run(context));
      } else if ("cloudapi".equals(mode)) {
        out.putString("result", CloudApiIntegrationChecks.run(context, args));
      } else if ("cloudfixture".equals(mode)) {
        CloudSession session = CloudSession.current(context);
        if (session == null || !session.server.matches("http://(10\\.0\\.2\\.2|127\\.0\\.0\\.1):[0-9]+"))
          throw new IllegalArgumentException("UI fixture requires an actual login to the isolated local backend");
        PeopleStore store = new PeopleStore(context, session.scope());
        PeopleStore.Person candidate = null;
        for (PeopleStore.Person p : store.all()) if (p.name.startsWith("安卓接入测试-") && !p.hasVoice()) { candidate = p; break; }
        if (candidate == null) throw new IllegalStateException("No new disposable API person available");
        java.io.File wav = store.stagingFile();
        CloudIdentityChecks.writeWav(wav, 4);
        store.saveVoice(candidate.id, candidate.name, wav, 4, true);
        out.putString("result", "PASS: synthetic local UI consent fixture only; person=" + candidate.name);
      } else if ("checks".equals(mode)) {
        out.putString("store", PeopleStoreChecks.run(context));
        out.putInt("captureChecks", VoiceSampleRecorderChecks.run(context));
        boolean prior = VoiceEnrollmentDialog.busy;
        try {
          VoiceEnrollmentDialog.busy = true;
          if (AppUpdater.idle(context))
            throw new AssertionError("Voice enrollment must defer installation");
        } finally {
          VoiceEnrollmentDialog.busy = prior;
        }
        out.putString(
            "result", "PASS: private persistence, WAV/cancel/error, and update exclusion");
      } else if ("ui".equals(mode)) {
        activity =
            startActivitySync(
                new Intent(context, MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        out.putString("ui", VoiceEnrollmentUiChecks.run(this, activity));
        out.putString("result", "PASS: native enrollment UI with deterministic test input");
      } else if ("panel".equals(mode)) {
        activity =
            startActivitySync(
                new Intent(context, MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        out.putString("panel", PeoplePanelChecks.run(this, activity));
        out.putString("result", "PASS: native people picker visible and scoped selection");
      } else if ("seed".equals(mode)) {
        PeopleStore store = new PeopleStore(context);
        if (!store.all().isEmpty())
          throw new IllegalStateException("Test seed refuses to overwrite existing people");
        PeopleStore.Person a = store.add("测试林晓", "测试产品部", false);
        PeopleStore.Person b = store.add("测试周宁", "测试设计部", false);
        store.add("测试来宾", "测试合作方", true);
        List<String> ids = new ArrayList<>();
        ids.add(a.id);
        ids.add(b.id);
        store.setSelected(ids, true);
        out.putString("result", "PASS: isolated emulator test participants created");
      } else throw new IllegalArgumentException("Unknown test mode");

    } catch (Throwable e) {
      android.util.Log.e("YanxuSpeakerTests", "failed", e);
      out.putString("failure", e.toString());
      resultCode = 1;
    } finally {
      if (activity != null) {
        Activity last = activity;
        runOnMainSync(last::finish);
      }
    }
    finish(resultCode, out);
  }
}
