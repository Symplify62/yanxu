package cn.jiajian.yanxu;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.Instrumentation;
import android.content.Context;
import android.content.ContextWrapper;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.media.MediaPlayer;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.TextView;
import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/** Real dialog controls with test-only PCM, private isolated data, and no microphone access. */
public final class VoiceEnrollmentUiChecks {
  private VoiceEnrollmentUiChecks() {}

  /** Invoke on the instrumentation thread, with a resumed Activity and RECORD_AUDIO granted. */
  public static String run(Instrumentation instrumentation, Activity activity) throws Exception {
    check(
        activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO)
            == PackageManager.PERMISSION_GRANTED,
        "Grant RECORD_AUDIO for UI guard coverage before running this test; input stays synthetic");
    check(!RecordingService.active && !VoiceEnrollmentDialog.busy, "recorders must be idle");
    File isolated = new File(activity.getCacheDir(), "voice-ui-check-" + UUID.randomUUID());
    check(isolated.mkdirs(), "isolated test folder");
    Context context =
        new ContextWrapper(activity) {
          @Override
          public File getFilesDir() {
            return isolated;
          }
        };
    PeopleStore store = new PeopleStore(context);
    PeopleStore.Person person = store.add("张伟", "研发测试", false);
    AtomicReference<VoiceEnrollmentDialog> current = new AtomicReference<>();
    AtomicReference<TestInput> input = new AtomicReference<>();
    AtomicInteger sourcesCreated = new AtomicInteger();
    AtomicInteger saves = new AtomicInteger();
    int passed = 0;
    try {
      open(instrumentation, activity, store, person.id, current, input, sourcesCreated, saves);
      check(VoiceEnrollmentDialog.busy, "opening holds enrollment gate");
      onMain(
          instrumentation,
          () -> {
            check(!save(current.get()).isEnabled(), "no-save before audio");
            check(!checkBox(current.get(), "已核对姓名，录音为本人声音").isEnabled(), "no-confirm before audio");
            return null;
          });
      check(sourcesCreated.get() == 0, "showing dialog does not create an audio source");
      screenshot(instrumentation, activity, current.get(), "voice-enrollment-initial.png");
      passed++;

      onMain(
          instrumentation,
          () -> {
            name(current.get()).setText("");
            click(current.get(), "开始录制");
            checkVisible(current.get(), "请填写本人姓名");
            return null;
          });
      check(sourcesCreated.get() == 0, "empty name blocks recording");
      passed++;

      onMain(
          instrumentation,
          () -> {
            name(current.get()).setText("张伟");
            click(current.get(), "开始录制");
            return null;
          });
      awaitInput(input);
      onMain(instrumentation, () -> { click(current.get(), "结束录制"); return null; });
      await(
          "sample becomes reviewable",
          () -> onMain(instrumentation, () -> save(current.get()).isEnabled()));
      check(!store.get(person.id).hasVoice(), "unconfirmed audio is not committed");
      onMain(
          instrumentation,
          () -> {
            save(current.get()).performClick();
            checkVisible(current.get(), "请核对姓名，并确认这是本人的声音");
            return null;
          });
      check(!store.get(person.id).hasVoice() && saves.get() == 0, "confirmation blocks save");
      passed++;

      onMain(
          instrumentation,
          () -> {
            checkBox(current.get(), "已核对姓名，录音为本人声音").performClick();
            name(current.get()).setText("张炜");
            check(!checkBox(current.get(), "已核对姓名，录音为本人声音").isChecked(), "name change resets confirmation");
            save(current.get()).performClick();
            checkVisible(current.get(), "请核对姓名，并确认这是本人的声音");
            return null;
          });
      check(store.get(person.id).name.equals("张伟"), "name remains unchanged until confirmed save");
      passed++;

      onMain(
          instrumentation,
          () -> {
            checkBox(current.get(), "已核对姓名，录音为本人声音").performClick();
            save(current.get()).performClick();
            checkVisible(current.get(), "保存前需本人同意在本机保留声音");
            return null;
          });
      check(!store.get(person.id).hasVoice(), "long-term consent blocks save");
      passed++;

      onMain(instrumentation, () -> { click(current.get(), "试听本次录音"); return null; });
      await(
          "actual MediaPlayer starts staged WAV",
          () ->
              onMain(
                  instrumentation,
                  () -> {
                    MediaPlayer player = field(current.get(), "player");
                    return player != null && player.isPlaying();
                  }));
      onMain(
          instrumentation,
          () -> {
            click(current.get(), "停止试听");
            check(field(current.get(), "player") == null, "stop playback releases player");
            return null;
          });
      screenshot(instrumentation, activity, current.get(), "voice-enrollment-confirm.png");
      passed++;

      onMain(
          instrumentation,
          () -> {
            checkBox(current.get(), "同意在本机保留声音，供后续会议使用").performClick();
            save(current.get()).performClick();
            return null;
          });
      await("confirmed save completes and releases busy", () -> saves.get() == 1 && !VoiceEnrollmentDialog.busy);
      PeopleStore.Person saved = store.get(person.id);
      check(saved.hasVoice() && saved.name.equals("张炜") && saved.voiceSeconds == 2.0, "confirmed metadata");
      File savedFile = store.voiceFile(person.id);
      byte[] original = Files.readAllBytes(savedFile.toPath());
      check(original.length == 64044, "actual WAV persisted");
      check(store.selected().isEmpty(), "enrollment does not change meeting selection");
      check(isEmpty(new File(isolated, "people/staging")), "save consumes staging");
      passed++;

      open(instrumentation, activity, store, person.id, current, input, sourcesCreated, saves);
      screenshot(instrumentation, activity, current.get(), "voice-enrollment-saved.png");
      onMain(instrumentation, () -> { click(current.get(), "开始录制"); return null; });
      awaitInput(input);
      onMain(instrumentation, () -> { click(current.get(), "结束录制"); return null; });
      await("replacement ready", () -> onMain(instrumentation, () -> save(current.get()).isEnabled()));
      check(store.get(person.id).voiceFilename.equals(saved.voiceFilename), "reviewing replacement preserves old metadata");
      check(Arrays.equals(original, Files.readAllBytes(savedFile.toPath())), "reviewing replacement preserves old WAV");
      onMain(
          instrumentation,
          () -> {
            dialog(current.get()).getButton(AlertDialog.BUTTON_NEGATIVE).performClick();
            AlertDialog discard = field(current.get(), "discardDialog");
            check(discard != null && discard.isShowing(), "cancel asks before discarding");
            discard.getButton(AlertDialog.BUTTON_NEGATIVE).performClick();
            check(dialog(current.get()).isShowing() && VoiceEnrollmentDialog.busy, "continue preserves active enrollment");
            dialog(current.get()).getButton(AlertDialog.BUTTON_NEGATIVE).performClick();
            discard = field(current.get(), "discardDialog");
            discard.getButton(AlertDialog.BUTTON_POSITIVE).performClick();
            return null;
          });
      await("cancel releases busy", () -> !VoiceEnrollmentDialog.busy);
      check(store.get(person.id).voiceFilename.equals(saved.voiceFilename), "cancel keeps old voice link");
      check(Arrays.equals(original, Files.readAllBytes(savedFile.toPath())), "cancel keeps old WAV");
      check(isEmpty(new File(isolated, "people/staging")) && saves.get() == 1, "cancel discards new sample only");
      passed++;

      open(instrumentation, activity, store, person.id, current, input, sourcesCreated, saves);
      onMain(instrumentation, () -> { click(current.get(), "开始录制"); return null; });
      awaitInput(input);
      TestInput interrupted = input.get();
      onMain(instrumentation, () -> { current.get().onHostPause(); return null; });
      await("host pause stops capture and gate", () -> !VoiceEnrollmentDialog.busy && interrupted.released);
      check(onMain(instrumentation, () -> !dialog(current.get()).isShowing()), "host pause dismisses dialog");
      check(isEmpty(new File(isolated, "people/staging")), "host pause discards unconfirmed sample");
      check(store.get(person.id).voiceFilename.equals(saved.voiceFilename), "host pause preserves saved voice");
      check(Arrays.equals(original, Files.readAllBytes(savedFile.toPath())) && saves.get() == 1, "host pause does not save");
      passed++;
      return "Voice enrollment UI: " + passed + " checks passed; deterministic test PCM, no microphone";
    } finally {
      if (current.get() != null) onMain(instrumentation, () -> { current.get().dismiss(); return null; });
      await("final enrollment cleanup", () -> !VoiceEnrollmentDialog.busy);
      deleteTree(isolated);
    }
  }

  private static void open(
      Instrumentation instrumentation,
      Activity activity,
      PeopleStore store,
      String id,
      AtomicReference<VoiceEnrollmentDialog> current,
      AtomicReference<TestInput> input,
      AtomicInteger created,
      AtomicInteger saves)
      throws Exception {
    input.set(null);
    onMain(
        instrumentation,
        () -> {
          VoiceEnrollmentDialog enrollment =
              new VoiceEnrollmentDialog(
                  activity,
                  store,
                  id,
                  () -> saves.incrementAndGet(),
                  () -> {
                    TestInput fixture = new TestInput();
                    input.set(fixture);
                    created.incrementAndGet();
                    return new VoiceSampleRecorder(() -> fixture);
                  });
          current.set(enrollment);
          enrollment.show();
          check(dialog(enrollment) != null && dialog(enrollment).isShowing(), "dialog opened");
          return null;
        });
  }

  private static void awaitInput(AtomicReference<TestInput> input) throws Exception {
    check(input.get() != null, "test source created by start button");
    check(input.get().supplied.await(5, TimeUnit.SECONDS), "PCM supplied");
  }

  private static void screenshot(
      Instrumentation instrumentation,
      Activity activity,
      VoiceEnrollmentDialog enrollment,
      String filename)
      throws Exception {
    instrumentation.waitForIdleSync();
    CountDownLatch rendered = new CountDownLatch(1);
    onMain(
        instrumentation,
        () -> {
          View decor = dialog(enrollment).getWindow().getDecorView();
          decor.postOnAnimation(() -> decor.postOnAnimation(rendered::countDown));
          return null;
        });
    check(rendered.await(5, TimeUnit.SECONDS), "dialog rendered before screenshot");
    Bitmap bitmap = instrumentation.getUiAutomation().takeScreenshot();
    check(bitmap != null, "real display screenshot available");
    File evidence = new File(activity.getFilesDir(), "speaker-test-evidence");
    check(evidence.isDirectory() || evidence.mkdirs(), "screenshot evidence folder");
    try (FileOutputStream output = new FileOutputStream(new File(evidence, filename))) {
      check(bitmap.compress(Bitmap.CompressFormat.PNG, 100, output), "screenshot encoded");
      output.getFD().sync();
    } finally {
      bitmap.recycle();
    }
  }

  private static AlertDialog dialog(VoiceEnrollmentDialog enrollment) throws Exception {
    return field(enrollment, "dialog");
  }

  private static Button save(VoiceEnrollmentDialog enrollment) throws Exception {
    return dialog(enrollment).getButton(AlertDialog.BUTTON_POSITIVE);
  }

  private static EditText name(VoiceEnrollmentDialog enrollment) throws Exception {
    return field(enrollment, "name");
  }

  private static CheckBox checkBox(VoiceEnrollmentDialog enrollment, String text) throws Exception {
    View view = find(dialog(enrollment).getWindow().getDecorView(), text);
    check(view instanceof CheckBox, "checkbox exists: " + text);
    return (CheckBox) view;
  }

  private static void click(VoiceEnrollmentDialog enrollment, String text) throws Exception {
    View view = find(dialog(enrollment).getWindow().getDecorView(), text);
    check(view instanceof Button && view.isEnabled(), "button enabled: " + text);
    view.performClick();
  }

  private static void checkVisible(VoiceEnrollmentDialog enrollment, String text) throws Exception {
    View view = find(dialog(enrollment).getWindow().getDecorView(), text);
    check(view != null && view.getVisibility() == View.VISIBLE, "visible error: " + text);
  }

  private static View find(View view, String text) {
    if (view instanceof TextView && ((TextView) view).getText().toString().equals(text)) return view;
    if (view instanceof ViewGroup) {
      ViewGroup group = (ViewGroup) view;
      for (int i = 0; i < group.getChildCount(); i++) {
        View found = find(group.getChildAt(i), text);
        if (found != null) return found;
      }
    }
    return null;
  }

  @SuppressWarnings("unchecked")
  private static <T> T field(Object object, String name) throws Exception {
    Field field = object.getClass().getDeclaredField(name);
    field.setAccessible(true);
    return (T) field.get(object);
  }

  private interface CheckedSupplier<T> {
    T get() throws Exception;
  }

  private static <T> T onMain(Instrumentation instrumentation, CheckedSupplier<T> action)
      throws Exception {
    AtomicReference<T> result = new AtomicReference<>();
    AtomicReference<Throwable> failure = new AtomicReference<>();
    instrumentation.runOnMainSync(
        () -> {
          try {
            result.set(action.get());
          } catch (Throwable error) {
            failure.set(error);
          }
        });
    if (failure.get() != null) {
      if (failure.get() instanceof Exception) throw (Exception) failure.get();
      if (failure.get() instanceof Error) throw (Error) failure.get();
      throw new IllegalStateException(failure.get());
    }
    return result.get();
  }

  private static void await(String label, CheckedSupplier<Boolean> ready) throws Exception {
    long until = System.nanoTime() + TimeUnit.SECONDS.toNanos(8);
    while (!ready.get()) {
      if (System.nanoTime() >= until) throw new AssertionError("Timed out: " + label);
      Thread.sleep(20);
    }
  }

  private static boolean isEmpty(File directory) {
    File[] files = directory.listFiles();
    return files == null || files.length == 0;
  }

  private static void deleteTree(File file) {
    File[] children = file.listFiles();
    if (children != null) for (File child : children) deleteTree(child);
    file.delete();
  }

  private static void check(boolean condition, String message) {
    if (!condition) throw new AssertionError(message);
  }

  private static final class TestInput implements VoiceSampleRecorder.Input {
    final CountDownLatch supplied = new CountDownLatch(1);
    private int bytes;
    private volatile boolean stopped;
    volatile boolean released;

    public void start() {}

    public int read(byte[] buffer) {
      if (stopped) return -3;
      if (bytes >= 64000) {
        supplied.countDown();
        return 0;
      }
      int count = Math.min(buffer.length, 64000 - bytes);
      for (int i = 0; i < count; i += 2) {
        int sample = (int) (Math.sin((bytes + i) / 2.0 * Math.PI * 2 * 220 / 16000) * 96);
        buffer[i] = (byte) sample;
        buffer[i + 1] = (byte) (sample >> 8);
      }
      bytes += count;
      return count;
    }

    public void stop() {
      stopped = true;
    }

    public void release() {
      released = true;
    }
  }
}
