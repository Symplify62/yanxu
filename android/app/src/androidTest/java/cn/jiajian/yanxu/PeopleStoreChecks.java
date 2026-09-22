package cn.jiajian.yanxu;

import android.content.Context;
import android.content.ContextWrapper;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import org.json.*;

/** Called by the test APK runner. All fixtures live under a fresh, isolated private directory. */
public final class PeopleStoreChecks {
  private interface ThrowingAction {
    void run() throws Exception;
  }

  public static String run(Context context) throws Exception {
    File testRoot = new File(context.getFilesDir(), "people-store-check-" + UUID.randomUUID());
    if (!testRoot.mkdirs()) throw new IOException("Unable to create isolated test directory");
    Context isolated =
        new ContextWrapper(context) {
          @Override
          public File getFilesDir() {
            return testRoot;
          }
        };
    try {
      PeopleStore first = new PeopleStore(isolated);
      PeopleStore second = new PeopleStore(isolated);
      check(first.all().isEmpty() && first.selected().isEmpty(), "Must start with no demo people");
      fails(() -> first.add("  ", "", false), "Blank names must fail");
      fails(
          () -> first.add(new String(new char[81]).replace('\0', '名'), "", false),
          "Names must be bounded");
      PeopleStore.Person member = first.add(" 王芳 ", "财务", false);
      check("王芳".equals(member.name), "Name must be normalized");
      fails(() -> second.add("王芳", "财务", false), "Duplicate identity must fail");
      PeopleStore.Person other = second.add("王芳", "采购", false);
      check(!member.id.equals(other.id), "Different departments may disambiguate equal names");
      first.setSelected(member.id, true);
      second.setSelected(other.id, true);
      first.setSelected(Collections.singletonList(member.id), false);
      check(
          second.selected().size() == 1 && second.isSelected(other.id),
          "Filtered deselection must preserve other selections across store instances");
      second.setSelected(other.id, true);
      check(first.selected().size() == 1, "Selection must be idempotent");
      fails(
          () -> first.setSelected(Arrays.asList(member.id, "missing"), true),
          "Unknown identity must reject the whole selection update");
      check(!first.isSelected(member.id), "Rejected update must not partly commit");

      File staged = sample(first);
      fails(
          () -> first.saveVoice(member.id, "王芳", staged, 1, false),
          "Persistent members require explicit consent");
      check(
          staged.exists() && !first.get(member.id).hasVoice(),
          "Rejected save must preserve the retryable draft");
      first.saveVoice(member.id, "王芳", staged, 1, true);
      File saved = second.voiceFile(member.id);
      check(
          saved != null && saved.exists() && !staged.exists(),
          "Completed save must survive another store instance and consume its draft");
      check(
          !saved.getAbsolutePath().contains("/recordings/"),
          "Voice sample must remain outside public recording storage");

      File replacement = sample(second);
      File blockedWrite = new File(testRoot, "people/people.json.new");
      check(blockedWrite.mkdir(), "Unable to simulate metadata write failure");
      File blocker = new File(blockedWrite, "blocker");
      check(blocker.createNewFile(), "Unable to protect failure fixture");
      try {
        fails(
            () -> second.saveVoice(member.id, "王芳更新", replacement, 1, true),
            "Metadata failure must reject replacement");
      } finally {
        blocker.delete();
        blockedWrite.delete();
      }
      check(
          saved.exists()
              && "王芳".equals(first.get(member.id).name)
              && saved.equals(first.voiceFile(member.id)),
          "Failed replacement must keep the original");
      check(replacement.exists(), "Failed commit must retain the staged recording for retry");
      second.saveVoice(member.id, "王芳更新", replacement, 1, true);
      File updated = first.voiceFile(member.id);
      check(
          updated != null && !updated.equals(saved) && !saved.exists(),
          "Replacement must use a new file and remove the old file only after commit");
      check("王芳更新".equals(second.get(member.id).name), "Confirmed name must persist");

      File active = sample(first);
      File abandoned = new File(active.getParentFile(), UUID.randomUUID() + ".wav");
      Files.copy(active.toPath(), abandoned.toPath());
      File orphan = new File(updated.getParentFile(), UUID.randomUUID() + ".wav");
      Files.copy(active.toPath(), orphan.toPath());
      second.recover();
      check(
          active.exists() && updated.exists() && !abandoned.exists() && !orphan.exists(),
          "Recovery must clean interrupted drafts/orphans and preserve active and saved samples");
      active.delete();
      first.recover();

      File external = new File(testRoot, UUID.randomUUID() + ".wav");
      Files.copy(updated.toPath(), external.toPath());
      fails(
          () -> first.saveVoice(member.id, "王芳更新", external, 1, true),
          "Files outside private staging must be rejected");
      check(external.exists() && updated.exists(), "Rejected source must not be consumed");
      first.setSelected(member.id, true);
      JSONObject snapshot = first.snapshot();
      check(
          snapshot.getJSONArray("participants").length() == 2,
          "Snapshot must contain selected people");
      snapshot.getJSONArray("participants").getJSONObject(0).put("name", "tampered");
      check(
          !first.snapshot().toString().contains("tampered"),
          "Snapshot must be detached from live data");
      check(
          !snapshot.toString().contains("voiceFilename"),
          "Roster must not expose private audio paths");

      PeopleStore.Person guest = first.add("来宾", "合作方", true);
      File guestDraft = sample(first);
      first.saveVoice(guest.id, "来宾", guestDraft, 1, false);
      File guestSample = first.voiceFile(guest.id);
      first.setSelected(guest.id, true);
      first.nextMeeting();
      check(
          second.get(guest.id) == null && !guestSample.exists() && second.selected().isEmpty(),
          "Next meeting must clear guests, their samples and selection");
      check(
          second.get(member.id).hasVoice() && updated.exists(),
          "Next meeting must retain permanent members and samples");
      second.clearVoice(member.id);
      check(
          !first.get(member.id).hasVoice()
              && first.voiceFile(member.id) == null
              && !updated.exists(),
          "Clearing a sample must persist and remove only its file");

      List<Throwable> failures = Collections.synchronizedList(new ArrayList<>());
      Thread a = concurrentWriter(first, "A", failures);
      Thread b = concurrentWriter(second, "B", failures);
      a.start();
      b.start();
      a.join();
      b.join();
      check(failures.isEmpty(), "Concurrent operations failed: " + failures);
      check(
          first.all().size() == 22 && second.selected().size() == 20,
          "Concurrent instances must not lose people or selections");

      File meta = new File(testRoot, "people/people.json");
      byte[] goodState = Files.readAllBytes(meta.toPath());
      JSONObject corrupt = new JSONObject(new String(goodState, StandardCharsets.UTF_8));
      corrupt
          .getJSONArray("people")
          .getJSONObject(0)
          .put("voiceFilename", "../../recordings/audio.wav");
      Files.write(meta.toPath(), corrupt.toString().getBytes(StandardCharsets.UTF_8));
      try {
        fails(first::all, "Corrupt file paths must fail closed");
      } finally {
        Files.write(meta.toPath(), goodState);
      }
      first.recover();
      check(
          !new File(testRoot, "recordings").exists(),
          "Store must never create the upload directory");
      return "PASS: empty/default validation, duplicate protection, selection isolation, private"
                 + " sample consent/persistence, failed-commit rollback, replacement, recovery,"
                 + " path bounds, detached roster, guest cleanup, sample removal and concurrent"
                 + " stores";
    } finally {
      remove(testRoot);
    }
  }

  private static Thread concurrentWriter(
      PeopleStore store, String prefix, List<Throwable> failures) {
    return new Thread(
        () -> {
          try {
            for (int i = 0; i < 10; i++) {
              PeopleStore.Person person = store.add(prefix + i, "并发验证", false);
              store.setSelected(person.id, true);
            }
          } catch (Throwable failure) {
            failures.add(failure);
          }
        });
  }

  private static File sample(PeopleStore store) throws Exception {
    File file = store.stagingFile();
    try (RandomAccessFile audio = new RandomAccessFile(file, "rw")) {
      audio.setLength(32044);
      LocalStore.header(audio, 32000);
      audio.seek(44);
      for (int i = 0; i < 16000; i++) LocalStore.le16(audio, (i % 100) * 100);
      audio.getFD().sync();
    }
    return file;
  }

  private static void fails(ThrowingAction action, String message) throws Exception {
    try {
      action.run();
    } catch (Exception expected) {
      return;
    }
    throw new AssertionError(message);
  }

  private static void check(boolean condition, String message) {
    if (!condition) throw new AssertionError(message);
  }

  private static void remove(File file) {
    File[] children = file.listFiles();
    if (children != null) for (File child : children) remove(child);
    file.delete();
  }
}
