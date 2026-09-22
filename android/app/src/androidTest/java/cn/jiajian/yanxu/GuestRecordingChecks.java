package cn.jiajian.yanxu;

import android.content.Context;
import java.io.IOException;
import org.json.JSONArray;
import org.json.JSONObject;

/** Guest recording must never inherit a later account or silently discard selected people. */
public final class GuestRecordingChecks {
  private interface Action { void run() throws Exception; }

  private static void check(boolean value, String why) {
    if (!value) throw new AssertionError(why);
  }

  private static void rejected(Action action, String why) throws Exception {
    try { action.run(); }
    catch (Exception expected) { return; }
    throw new AssertionError(why);
  }

  private static void loginRequired(Action action, String why) throws Exception {
    try { action.run(); }
    catch (RecordingIdentity.LoginRequired expected) { return; }
    catch (IOException expected) { return; }
    throw new AssertionError(why);
  }

  private static JSONObject copy(JSONObject value) throws Exception {
    return new JSONObject(value.toString());
  }

  private static JSONObject roster(String... people) throws Exception {
    JSONArray participants = new JSONArray();
    for (String person : people) {
      participants.put(new JSONObject().put("personId", person).put("cloudPersonId", person)
          .put("name", "姓名-" + person).put("department", "测试部门")
          .put("guest", false).put("hasLocalSample", false));
    }
    return new JSONObject().put("version", 1).put("capturedAt", System.currentTimeMillis())
        .put("participants", participants);
  }

  private static void server(Context context, String server) {
    check(context.getSharedPreferences("settings", 0).edit().putString("server", server).commit(),
        "Test server setting must persist");
  }

  private static CloudSession session(String server, String account, boolean recorder, boolean expired)
      throws Exception {
    JSONArray permissions = new JSONArray();
    if (recorder) permissions.put("record");
    return new CloudSession(server, "guest-boundary-secret-" + account,
        new JSONObject().put("id", account).put("username", account).put("permissions", permissions),
        System.currentTimeMillis() + (expired ? -60000 : 600000));
  }

  private static void anonymous(JSONObject fragment, String server) throws Exception {
    check(fragment.getString("recordingMode").equals("anonymous"), "Expected explicit guest mode");
    check(fragment.getString("uploadServer").equals(server), "Guest destination must freeze at recording start");
    check(!fragment.has("cloudIdentity") && !fragment.has("participantsSnapshot"),
        "Guest metadata must not contain a private identity or roster");
    check(!fragment.toString().contains("guest-boundary-secret"), "Metadata must never contain a bearer token");
  }

  public static String run(Context context) throws Exception {
    CloudIdentityChecks.Sandbox box = new CloudIdentityChecks.Sandbox(context);
    String firstServer = "http://127.0.0.1:19131";
    String secondServer = "http://127.0.0.1:19132";
    try {
      server(box, firstServer);
      JSONObject guest = RecordingIdentity.captureForRecording(box, roster());
      anonymous(guest, firstServer);
      RecordingIdentity.validateStart(box, guest);
      check(RecordingIdentity.requireOwner(box, guest) == null, "A guest does not need a login to upload");
      check(RecordingIdentity.visible(box, guest), "Guest recordings remain visible without a login");
      loginRequired(() -> RecordingIdentity.captureForRecording(box, roster("p1")),
          "Selected people cannot be discarded just because there is no login");

      CloudSession owner = session(firstServer, "organizer-A", true, false);
      CloudSession.save(box, owner);
      check(RecordingIdentity.requireOwner(box, guest) == null,
          "Logging in must not adopt a pre-existing anonymous recording");
      anonymous(guest, firstServer);
      RecordingIdentity.validateStart(box, guest);
      JSONObject emptyManaged = RecordingIdentity.captureForRecording(box, roster());
      check(emptyManaged.getString("recordingMode").equals("managed"),
          "An authorized organizer's new recording remains managed even with an empty roster");
      RecordingIdentity.validateStart(box, emptyManaged);

      JSONObject originalRoster = roster("p1", "p2");
      JSONObject managed = RecordingIdentity.captureForRecording(box, originalRoster);
      JSONObject frozenIdentity = managed.getJSONObject("cloudIdentity");
      check(managed.getString("recordingMode").equals("managed"), "Selected people require managed mode");
      check(frozenIdentity.getString("ownerAccountId").equals(owner.accountId), "Managed owner must freeze");
      check(frozenIdentity.getString("server").equals(firstServer), "Managed destination must freeze");
      check(frozenIdentity.getJSONArray("participants").length() == 2,
          "Every selected cloud person must be included");
      check(frozenIdentity.getJSONArray("participants").getJSONObject(0).getString("personId").equals("p1"),
          "Upload must use the cloud person ID");
      check(!managed.toString().contains(owner.token), "Managed metadata must never persist the token");
      originalRoster.getJSONArray("participants").getJSONObject(0).put("name", "后续改名");
      originalRoster.getJSONArray("participants").put(new JSONObject().put("cloudPersonId", "p3"));
      check(managed.getJSONObject("participantsSnapshot").getJSONArray("participants").length() == 2,
          "Editing the current picker cannot change an already captured roster");
      check(managed.getJSONObject("participantsSnapshot").getJSONArray("participants")
          .getJSONObject(0).getString("name").equals("姓名-p1"), "Captured names must be detached");
      RecordingIdentity.validateStart(box, managed);

      CloudSession.clear(box);
      loginRequired(() -> RecordingIdentity.requireOwner(box, managed),
          "Logout must pause a managed upload, never downgrade it to guest");
      loginRequired(() -> RecordingIdentity.validateStart(box, managed),
          "Logout between capture and service start must prevent a managed start");
      check(!RecordingIdentity.visible(box, managed), "Signed-out users cannot view private participant names");
      CloudSession.save(box, session(firstServer, "organizer-B", true, false));
      loginRequired(() -> RecordingIdentity.requireOwner(box, managed), "Another account cannot upload the old meeting");
      loginRequired(() -> RecordingIdentity.validateStart(box, managed),
          "An account switch between capture and service start must be rejected");
      check(RecordingIdentity.requireOwner(box, guest) == null,
          "Switching to a second account must still leave guest uploads anonymous");

      CloudSession.save(box, session(firstServer, "organizer-A", true, true));
      anonymous(RecordingIdentity.captureForRecording(box, roster()), firstServer);
      loginRequired(() -> RecordingIdentity.captureForRecording(box, roster("p1")),
          "Expired login with selected people must request login instead of guest fallback");
      loginRequired(() -> RecordingIdentity.requireOwner(box, managed), "Expired owner cannot resume managed upload");
      loginRequired(() -> RecordingIdentity.validateStart(box, managed), "Expiry before service start must be rejected");

      CloudSession.save(box, session(firstServer, "member-A", false, false));
      anonymous(RecordingIdentity.captureForRecording(box, roster()), firstServer);
      loginRequired(() -> RecordingIdentity.captureForRecording(box, roster("p1")),
          "A member without recording permission can record audio, but cannot bind people");
      CloudSession.save(box, session(firstServer, "organizer-A", false, false));
      loginRequired(() -> RecordingIdentity.validateStart(box, managed),
          "Revoking record permission between capture and service start must be enforced");

      CloudSession.save(box, owner);
      check(RecordingIdentity.requireOwner(box, managed).accountId.equals(owner.accountId),
          "The original owner can resume the managed recording");
      server(box, secondServer);
      loginRequired(() -> RecordingIdentity.requireOwner(box, managed),
          "Changing server must not release a private upload to the new service");
      check(RecordingIdentity.requireOwner(box, guest) == null, "Guest identity remains anonymous after server changes");
      anonymous(guest, firstServer);
      rejected(() -> RecordingIdentity.validateStart(box, guest),
          "Changing server before service start must not create a recording with a stale destination");
      server(box, firstServer);
      RecordingIdentity.validateStart(box, managed);

      JSONObject mixedIdentity = copy(guest).put("cloudIdentity", copy(frozenIdentity));
      JSONObject mixedRoster = copy(guest).put("participantsSnapshot", roster("p1"));
      rejected(() -> RecordingIdentity.validateStart(box, mixedIdentity), "Anonymous start must reject private identity");
      rejected(() -> RecordingIdentity.requireOwner(box, mixedIdentity), "Anonymous upload must reject private identity instead of selecting managed transport");
      rejected(() -> RecordingIdentity.validateStart(box, mixedRoster), "Anonymous start must reject participant metadata");
      JSONObject emptyPrivateRoster = copy(guest).put("participantsSnapshot", roster());
      rejected(() -> RecordingIdentity.validateStart(box, emptyPrivateRoster), "Even an empty private roster must not be attached to guest mode");
      JSONObject unbound = roster("p1");
      unbound.getJSONArray("participants").getJSONObject(0).put("cloudPersonId", "");
      rejected(() -> RecordingIdentity.captureForRecording(box, unbound), "Unbound people must not be stripped silently");
      JSONObject mismatch = copy(managed);
      mismatch.getJSONObject("participantsSnapshot").getJSONArray("participants")
          .getJSONObject(0).put("personId", "different-person").put("cloudPersonId", "different-person");
      rejected(() -> RecordingIdentity.validateStart(box, mismatch), "Identity and visible participant snapshot must agree");
      JSONObject missingManagedIdentity = copy(managed); missingManagedIdentity.remove("cloudIdentity");
      rejected(() -> RecordingIdentity.validateStart(box, missingManagedIdentity), "Managed start requires a frozen identity");
      rejected(() -> RecordingIdentity.requireOwner(box, missingManagedIdentity), "Damaged managed upload must never silently downgrade to guest");
      JSONObject missingGuestServer = copy(guest); missingGuestServer.remove("uploadServer");
      rejected(() -> RecordingIdentity.requireOwner(box, missingGuestServer), "A new guest recording without its captured server cannot bind to a later server");
      JSONObject invalidMode = copy(guest).put("recordingMode", "surprise");
      rejected(() -> RecordingIdentity.validateStart(box, invalidMode), "Unknown recording mode cannot silently choose a protocol");
      rejected(() -> RecordingIdentity.validateStart(box, new JSONObject()), "A new service start requires explicit capture metadata");
      for (String invalid : new String[] {"file:///tmp/recordings", "http://", "https://user:secret@example.test",
          "https://example.test/path", "https://example.test?token=secret", "https://example.test#fragment"}) {
        JSONObject invalidServer = copy(guest).put("uploadServer", invalid);
        server(box, invalid);
        rejected(() -> RecordingIdentity.validateStart(box, invalidServer),
            "Even matching settings must reject a destination that is not an HTTP(S) origin");
      }
      server(box, firstServer);
      check(RecordingIdentity.requireOwner(box, new JSONObject()) == null,
          "Legacy anonymous files continue to use the legacy upload protocol");
      return "PASS: guest start/server freeze, no account adoption, managed owner/roster freeze, expiry/permission gates, "
          + "logout/account/server start races, and malformed/mixed metadata rejection";
    } finally { box.cleanup(); }
  }
}
