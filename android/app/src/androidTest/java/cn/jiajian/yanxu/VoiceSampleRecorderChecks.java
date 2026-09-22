package cn.jiajian.yanxu;

import android.content.Context;
import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Deterministic file/lifecycle checks. Synthetic PCM stays in the test APK; no microphone access. */
final class VoiceSampleRecorderChecks {
  static int run(Context context) throws Exception {
    int passed = 0;
    File directory = new File(context.getCacheDir(), "voice-recorder-checks-" + UUID.randomUUID());
    check(directory.mkdirs(), "test directory");
    try {
      FakeInput input = new FakeInput(64000, false, false);
      Capture capture = start(directory, "complete", input);
      awaitBytes(capture.recorder, 64000);
      capture.recorder.stop();
      capture.await();
      check(capture.error == null && capture.file != null, "complete sample");
      check(capture.seconds == 2.0, "duration follows PCM bytes");
      check(capture.target.length() == 64044, "WAV size");
      try (RandomAccessFile wav = new RandomAccessFile(capture.target, "r")) {
        byte[] riff = new byte[4];
        wav.readFully(riff);
        check(new String(riff, java.nio.charset.StandardCharsets.US_ASCII).equals("RIFF"), "RIFF");
        wav.seek(22);
        check(readLittle(wav, 2) == 1, "mono");
        check(readLittle(wav, 4) == 16000, "sample rate");
        wav.seek(40);
        check(readLittle(wav, 4) == 64000, "data header length");
      }
      check(input.releases == 1, "release after completion");
      passed++;

      input = new FakeInput(32000, false, false);
      capture = start(directory, "cancel", input);
      awaitBytes(capture.recorder, 32000);
      capture.recorder.cancel();
      capture.await();
      check(capture.file == null && capture.error == null, "cancel is not success/error");
      check(!capture.target.exists() && input.releases == 1, "cancel removes unconfirmed sample");
      passed++;

      input = new FakeInput(32000, false, true);
      capture = start(directory, "read-error", input);
      capture.await();
      check(capture.file == null && capture.error != null, "read failure reported");
      check(!capture.target.exists() && input.releases == 1, "partial failure removed");
      passed++;

      input = new FakeInput(32000, true, false);
      capture = start(directory, "zero-signal", input);
      awaitBytes(capture.recorder, 32000);
      capture.recorder.stop();
      capture.await();
      check(capture.file == null && capture.error != null, "zero signal rejected");
      check(!capture.target.exists(), "zero-signal sample removed");
      passed++;

      capture = start(directory, "empty", new FakeInput(0, false, false));
      capture.recorder.stop();
      capture.await();
      check(capture.error != null && !capture.target.exists(), "empty recording rejected");
      passed++;

      input = new FakeInput(VoiceSampleRecorder.MAX_BYTES + 6400, false, false);
      capture = start(directory, "limit", input);
      capture.await();
      check(capture.error == null && capture.seconds == 300.0, "limit stops at five minutes");
      check(capture.target.length() == VoiceSampleRecorder.MAX_BYTES + 44, "limit WAV length");
      check(input.releases == 1, "limit releases microphone");
      passed++;

      File failureTarget = new File(directory, "start-error.wav");
      FakeInput rejected =
          new FakeInput(0, false, false) {
            @Override
            public void start() throws IOException {
              throw new IOException("fixture start rejection");
            }
          };
      boolean failed = false;
      try {
        new VoiceSampleRecorder(() -> rejected).start(failureTarget, (f, seconds, error) -> {});
      } catch (IOException expected) {
        failed = true;
      }
      check(failed && rejected.releases == 1 && !failureTarget.exists(), "start failure cleanup");
      passed++;
      return passed;
    } finally {
      File[] files = directory.listFiles();
      if (files != null) for (File file : files) file.delete();
      directory.delete();
    }
  }

  private static Capture start(File directory, String name, FakeInput input) throws Exception {
    Capture capture = new Capture(new File(directory, name + ".wav"), input);
    capture.recorder.start(capture.target, capture);
    return capture;
  }

  private static void awaitBytes(VoiceSampleRecorder recorder, long bytes) throws Exception {
    long until = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
    while (recorder.seconds() * 32000 < bytes && System.nanoTime() < until) Thread.sleep(5);
    if (recorder.seconds() * 32000 < bytes) {
      recorder.cancel();
      throw new AssertionError("fixture did not supply PCM");
    }
  }

  private static long readLittle(RandomAccessFile file, int size) throws IOException {
    long value = 0;
    for (int i = 0; i < size; i++) value |= ((long) file.readUnsignedByte()) << (i * 8);
    return value;
  }

  private static void check(boolean condition, String message) {
    if (!condition) throw new AssertionError(message);
  }

  private static class FakeInput implements VoiceSampleRecorder.Input {
    private final long maximum;
    private final boolean zero, errorAtEnd;
    private long sent;
    private volatile boolean stopped;
    int releases;

    FakeInput(long maximum, boolean zero, boolean errorAtEnd) {
      this.maximum = maximum;
      this.zero = zero;
      this.errorAtEnd = errorAtEnd;
    }

    public void start() throws IOException {}

    public int read(byte[] buffer) {
      if (stopped) return -3;
      if (sent >= maximum) return errorAtEnd ? -3 : 0;
      int count = (int) Math.min(buffer.length, maximum - sent);
      for (int i = 0; i < count; i++) buffer[i] = zero ? 0 : (byte) (i % 119 + 1);
      sent += count;
      return count;
    }

    public void stop() {
      stopped = true;
    }

    public void release() {
      releases++;
    }
  }

  private static final class Capture implements VoiceSampleRecorder.Callback {
    final File target;
    final VoiceSampleRecorder recorder;
    final CountDownLatch done = new CountDownLatch(1);
    File file;
    double seconds;
    String error;

    Capture(File target, FakeInput input) {
      this.target = target;
      recorder = new VoiceSampleRecorder(() -> input);
    }

    public void onComplete(File file, double seconds, String error) {
      this.file = file;
      this.seconds = seconds;
      this.error = error;
      done.countDown();
    }

    void await() throws Exception {
      if (!done.await(15, TimeUnit.SECONDS)) {
        recorder.cancel();
        throw new AssertionError("capture callback timed out");
      }
    }
  }
}
