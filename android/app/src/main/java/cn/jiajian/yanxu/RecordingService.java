package cn.jiajian.yanxu;

import android.app.*;
import android.content.*;
import android.content.pm.ServiceInfo;
import android.media.*;
import android.os.*;
import java.io.*;
import java.text.*;
import java.util.*;
import org.json.*;

public class RecordingService extends Service {
  public static volatile boolean active = false, paused = false;
  public static volatile long frames = 0;
  public static volatile String message = "准备就绪";
  private volatile boolean running = false;
  private Thread thread;
  private AudioRecord recorder;
  private File dir;
  private JSONObject meta;
  private PowerManager.WakeLock wake;

  @Override
  public android.os.IBinder onBind(Intent i) {
    return null;
  }

  @Override
  public int onStartCommand(Intent intent, int flags, int startId) {
    String action = intent == null ? "" : intent.getAction();
    if ("start".equals(action) && !active) start();
    else if ("pause".equals(action) && active && running) {
      paused = !paused;
      message = paused ? "录音已暂停" : "正在录音";
      try {
        meta.put("state", paused ? "paused" : "recording");
        LocalStore.save(dir, meta);
      } catch (Exception e) {
        message = "录音中，状态保存异常";
      }
      notifyState();
    } else if ("stop".equals(action)) running = false;
    return START_NOT_STICKY;
  }

  private void start() {
    try {
      if (new StatFs(getFilesDir().getAbsolutePath()).getAvailableBytes() < 64L * 1024 * 1024)
        throw new IOException("设备存储空间不足");
      getSystemService(NotificationManager.class)
          .createNotificationChannel(
              new NotificationChannel("recording", "录音状态", NotificationManager.IMPORTANCE_LOW));
      Notification n = notification("正在录音");
      if (Build.VERSION.SDK_INT >= 29)
        startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
      else startForeground(1, n);
      dir = new File(LocalStore.root(this), UUID.randomUUID().toString());
      meta =
          new JSONObject()
              .put("client_id", dir.getName())
              .put(
                  "title",
                  "录音 · " + new SimpleDateFormat("MM月dd日 HH:mm", Locale.CHINA).format(new Date()))
              .put("filename", "audio.wav")
              .put("state", "recording")
              .put("createdAt", System.currentTimeMillis())
              .put("interrupted", false);
      LocalStore.save(dir, meta);
      int size =
          Math.max(
              AudioRecord.getMinBufferSize(
                  16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT),
              32000);
      recorder =
          new AudioRecord(
              MediaRecorder.AudioSource.MIC,
              16000,
              AudioFormat.CHANNEL_IN_MONO,
              AudioFormat.ENCODING_PCM_16BIT,
              size * 2);
      if (recorder.getState() != AudioRecord.STATE_INITIALIZED) throw new IOException("无法打开麦克风");
      frames = 0;
      paused = false;
      active = true;
      running = true;
      message = "正在录音";
      wake =
          ((PowerManager) getSystemService(POWER_SERVICE))
              .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "yanxu:recording");
      wake.acquire();
      recorder.startRecording();
      thread = new Thread(() -> capture(size), "yanxu-capture");
      thread.start();
    } catch (Exception e) {
      message = e instanceof SecurityException ? "请允许麦克风权限" : "无法开始录音，请检查麦克风或存储";
      cleanup();
    }
  }

  private void capture(int size) {
    boolean interrupted = false;
    long flush = 0;
    try (RandomAccessFile out = new RandomAccessFile(new File(dir, "audio.wav"), "rw")) {
      LocalStore.header(out, 0);
      byte[] buf = new byte[size];
      while (running) {
        int count = recorder.read(buf, 0, buf.length);
        if (count < 0) throw new IOException("采集已中断");
        if (count > 0 && !paused) {
          out.write(buf, 0, count);
          frames += count / 2;
        }
        if (SystemClock.elapsedRealtime() - flush > 1000) {
          LocalStore.header(out, frames * 2);
          out.getFD().sync();
          flush = SystemClock.elapsedRealtime();
        }
        if (frames * 2 > 0xffffffffL - 64000) throw new IOException("已到文件格式容量上限");
      }
      LocalStore.header(out, frames * 2);
      out.getFD().sync();
    } catch (Exception e) {
      interrupted = true;
      running = false;
      message = "录音中断，保留已录内容";
    }
    try {
      File f = new File(dir, "audio.wav");
      if (f.length() > 44) {
        try (RandomAccessFile out = new RandomAccessFile(f, "rw")) {
          LocalStore.header(out, f.length() - 44);
          out.getFD().sync();
        }
        meta.put("duration", (f.length() - 44) / 32000.0)
            .put("state", "saved")
            .put("interrupted", interrupted);
        LocalStore.save(dir, meta);
        if (!interrupted) message = "录音已保存，自动上传";
        LocalStore.enqueue(this);
      } else {
        meta.put("state", "failed").put("message", "未采集到音频");
        LocalStore.save(dir, meta);
        message = "未采集到音频";
      }
    } catch (Exception e) {
      message = "保存异常，请保留应用数据";
    }
    cleanup();
  }

  private Notification notification(String text) {
    PendingIntent open =
        PendingIntent.getActivity(
            this,
            0,
            new Intent(this, MainActivity.class),
            PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    PendingIntent stop =
        PendingIntent.getService(
            this,
            1,
            new Intent(this, RecordingService.class).setAction("stop"),
            PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    return new Notification.Builder(this, "recording")
        .setSmallIcon(android.R.drawable.ic_btn_speak_now)
        .setContentTitle("言序")
        .setContentText(text)
        .setOngoing(true)
        .setContentIntent(open)
        .addAction(new Notification.Action.Builder(null, "结束并保存", stop).build())
        .build();
  }

  private void notifyState() {
    getSystemService(NotificationManager.class).notify(1, notification(message));
  }

  private void cleanup() {
    running = false;
    active = false;
    paused = false;
    if (recorder != null) {
      try {
        recorder.stop();
      } catch (Exception ignored) {
      }
      recorder.release();
      recorder = null;
    }
    if (wake != null && wake.isHeld()) wake.release();
    stopForeground(STOP_FOREGROUND_REMOVE);
    stopSelf();
  }

  @Override
  public void onDestroy() {
    running = false;
    super.onDestroy();
  }
}
