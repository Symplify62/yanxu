package cn.jiajian.yanxu;

import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.Handler;
import android.os.Looper;
import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;

/** Foreground-only capture into a private, unconfirmed WAV. Never enters the upload queue. */
public final class VoiceSampleRecorder {
  static final int SAMPLE_RATE = 16000;
  static final long MAX_BYTES = 300L * SAMPLE_RATE * 2;

  public interface Callback {
    /** A null file and error means cancellation; only a non-null file is ready for confirmation. */
    void onComplete(File file, double seconds, String error);
  }

  // Package-private audio seam lets instrumentation verify file/lifecycle behavior without a mic.
  interface Input {
    void start() throws Exception;

    int read(byte[] buffer) throws Exception;

    void stop();

    void release();
  }

  interface InputFactory {
    Input create() throws Exception;
  }

  private final InputFactory factory;
  private final Handler main = new Handler(Looper.getMainLooper());
  private final Object inputLock = new Object();
  private volatile boolean running, cancelled, finished = true;
  private volatile long bytes;
  private boolean started;
  private Input input;

  public VoiceSampleRecorder() {
    this(Microphone::new);
  }

  VoiceSampleRecorder(InputFactory factory) {
    this.factory = factory;
  }

  /** Called only after the user presses Start and the host grants RECORD_AUDIO permission. */
  public synchronized void start(File target, Callback callback) throws Exception {
    if (started) throw new IllegalStateException("请重新创建录音");
    started = true;
    RandomAccessFile output = null;
    try {
      output = new RandomAccessFile(target, "rw");
      output.setLength(0);
      LocalStore.header(output, 0);
      output.getFD().sync();
      synchronized (inputLock) {
        input = factory.create();
        input.start();
      }
      bytes = 0;
      cancelled = false;
      running = true;
      finished = false;
      final RandomAccessFile stream = output;
      new Thread(() -> capture(target, stream, callback), "yanxu-voice-sample").start();
    } catch (Exception error) {
      running = false;
      releaseInput();
      if (output != null) {
        try {
          output.close();
        } catch (IOException ignored) {
        }
      }
      target.delete();
      finished = true;
      throw error;
    }
  }

  public double seconds() {
    return bytes / (SAMPLE_RATE * 2.0);
  }

  public boolean isFinished() {
    return finished;
  }

  public void stop() {
    running = false;
    synchronized (inputLock) {
      if (input != null) input.stop();
    }
  }

  public void cancel() {
    cancelled = true;
    stop();
  }

  private void capture(File target, RandomAccessFile output, Callback callback) {
    String error = null;
    boolean signal = false;
    long lastSync = 0;
    try (RandomAccessFile out = output) {
      byte[] buffer = new byte[6400];
      while (running) {
        Input current = input;
        int count = current.read(buffer);
        if (count < 0) {
          if (!running) break;
          throw new IOException("麦克风采集已中断，请重新录制");
        }
        if (count == 0) {
          Thread.sleep(10);
          continue;
        }
        if (count > buffer.length || count % 2 != 0) throw new IOException("录音格式异常，请重新录制");
        int accepted = (int) Math.min(count, MAX_BYTES - bytes);
        out.write(buffer, 0, accepted);
        for (int i = 0; i < accepted; i++) {
          if (buffer[i] != 0) signal = true;
        }
        bytes += accepted;
        if (bytes - lastSync >= SAMPLE_RATE * 2) {
          LocalStore.header(out, bytes);
          out.getFD().sync();
          lastSync = bytes;
        }
        if (bytes >= MAX_BYTES) running = false;
      }
      if (!cancelled && (bytes == 0 || !signal)) throw new IOException("未收到有效声音，请检查麦克风后重录");
      LocalStore.header(out, bytes);
      out.getFD().sync();
    } catch (Exception failure) {
      error = failure instanceof IOException ? failure.getMessage() : "录音未完成，请重新录制";
    } finally {
      running = false;
      releaseInput();
      finished = true;
    }
    final boolean discarded = cancelled || error != null;
    if (discarded) target.delete();
    final String reportedError = cancelled ? null : error;
    main.post(() -> callback.onComplete(discarded ? null : target, seconds(), reportedError));
  }

  private void releaseInput() {
    synchronized (inputLock) {
      if (input == null) return;
      try {
        input.stop();
      } finally {
        input.release();
        input = null;
      }
    }
  }

  private static final class Microphone implements Input {
    private final AudioRecord recorder;

    Microphone() throws IOException {
      int minimum =
          AudioRecord.getMinBufferSize(
              SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
      if (minimum <= 0) throw new IOException("当前设备不支持声音录制");
      recorder =
          new AudioRecord(
              MediaRecorder.AudioSource.MIC,
              SAMPLE_RATE,
              AudioFormat.CHANNEL_IN_MONO,
              AudioFormat.ENCODING_PCM_16BIT,
              Math.max(minimum, 6400) * 2);
      if (recorder.getState() != AudioRecord.STATE_INITIALIZED) {
        recorder.release();
        throw new IOException("无法打开麦克风");
      }
    }

    @Override
    public void start() throws IOException {
      recorder.startRecording();
      if (recorder.getRecordingState() != AudioRecord.RECORDSTATE_RECORDING)
        throw new IOException("无法开始录音，请检查麦克风");
    }

    @Override
    public int read(byte[] buffer) {
      return recorder.read(buffer, 0, buffer.length, AudioRecord.READ_BLOCKING);
    }

    @Override
    public void stop() {
      try {
        if (recorder.getRecordingState() == AudioRecord.RECORDSTATE_RECORDING) recorder.stop();
      } catch (IllegalStateException ignored) {
      }
    }

    @Override
    public void release() {
      recorder.release();
    }
  }
}
