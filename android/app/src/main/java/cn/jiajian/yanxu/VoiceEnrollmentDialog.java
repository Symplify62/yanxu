package cn.jiajian.yanxu;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.media.MediaPlayer;
import android.os.Handler;
import android.os.Looper;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import java.io.File;
import java.util.Locale;
import java.util.function.Supplier;

/** Local voice confirmation UI. The host owns permission requests and its Activity lifecycle. */
public final class VoiceEnrollmentDialog {
  public static volatile boolean busy;
  private static VoiceEnrollmentDialog owner;
  private static final int GREEN = AppUi.GREEN;
  private static final int INK = AppUi.INK;
  private static final int MUTED = AppUi.MUTED;
  private static final int BG = AppUi.BG;
  private final Activity activity;
  private final PeopleStore store;
  private final String personId;
  private final Runnable onChanged;
  private final Supplier<VoiceSampleRecorder> recorderFactory;
  private final Handler main = new Handler(Looper.getMainLooper());
  private PeopleStore.Person person;
  private AppPage dialog;
  private AlertDialog discardDialog;
  private LinearLayout confirmations;
  private EditText name;
  private TextView status, clock, error;
  private CheckBox confirmed, consent;
  private Button capture, playback, save;
  private VoiceSampleRecorder recorder;
  private MediaPlayer player;
  private File staged;
  private double stagedSeconds;
  private boolean closed, recording, stopping, saving, ownsGate;
  private final Runnable tick =
      new Runnable() {
        @Override
        public void run() {
          if (closed || !recording || recorder == null) return;
          clock.setText(duration(recorder.seconds()));
          main.postDelayed(this, 200);
        }
      };

  public VoiceEnrollmentDialog(
      Activity activity, PeopleStore store, String personId, Runnable onChanged) {
    this(activity, store, personId, onChanged, VoiceSampleRecorder::new);
  }

  VoiceEnrollmentDialog(
      Activity activity,
      PeopleStore store,
      String personId,
      Runnable onChanged,
      Supplier<VoiceSampleRecorder> recorderFactory) {
    this.activity = activity;
    this.store = store;
    this.personId = personId;
    this.onChanged = onChanged;
    this.recorderFactory = recorderFactory;
  }

  public void show() {
    if (closed || activity.isFinishing() || activity.isDestroyed()) return;
    synchronized (AppUpdater.GATE) {
      if (busy || RecordingService.active || AppUpdater.installing(activity)) {
        Toast.makeText(activity, "请先结束当前录音或等待更新完成", Toast.LENGTH_SHORT).show();
        return;
      }
      busy = true;
      owner = this;
      ownsGate = true;
    }
    try {
      person = store.get(personId);
      if (person == null) throw new IllegalStateException("此人员已不存在");
      build();
    } catch (Exception failure) {
      releaseGate();
      Toast.makeText(activity, "无法读取人员资料，请稍后重试", Toast.LENGTH_SHORT).show();
    }
  }

  private void build() {
    dialog = new AppPage(activity, "录制本人声音", true);
    LinearLayout body = dialog.body;
    body.addView(label("姓名", 13, MUTED));
    name = new EditText(activity);
    AppUi.input(name);
    name.setSingleLine(true);
    name.setTextSize(16);
    name.setTextColor(INK);
    name.setSelectAllOnFocus(true);
    name.setText(person.name);
    name.setEnabled(person.cloudPersonId.isEmpty());
    name.setContentDescription("确认姓名");
    body.addView(name, new LinearLayout.LayoutParams(-1, dp(52)));
    TextView instruction = label("请本人说出姓名，并说一句完整的介绍。", 14, INK);
    instruction.setPadding(0, dp(14), 0, dp(10));
    body.addView(instruction);
    status = label(person.hasVoice() ? "已有本机声音，可试听或重录" : "准备录制", 13, MUTED);
    status.setGravity(Gravity.CENTER);
    body.addView(status);
    clock = label("00:00", 36, INK);
    clock.setTypeface(Typeface.create("sans-serif-light", Typeface.NORMAL));
    clock.setPadding(0, dp(20), 0, dp(20));
    clock.setGravity(Gravity.CENTER);
    body.addView(clock);
    capture = action("开始录制", true, this::captureClicked);
    body.addView(capture);
    playback = action(person.hasVoice() ? "试听已保存声音" : "试听本次录音", false, this::play);
    playback.setVisibility(person.hasVoice() ? View.VISIBLE : View.GONE);
    body.addView(playback);
    confirmations = AppUi.column(activity);
    confirmations.setVisibility(View.GONE);
    body.addView(confirmations);
    confirmed = new CheckBox(activity);
    confirmed.setText("已核对姓名，录音为本人声音");
    confirmed.setTextColor(INK);
    confirmed.setTextSize(13);
    confirmed.setEnabled(false);
    confirmations.addView(confirmed);
    if (!person.guest) {
      consent = new CheckBox(activity);
      consent.setText("同意在本机保留声音，供后续会议使用");
      consent.setTextColor(INK);
      consent.setTextSize(13);
      consent.setEnabled(false);
      confirmations.addView(consent);
    } else {
      body.addView(label("临时来宾：声音仅保留本场。", 12, MUTED));
    }
    error = label("", 13, Color.rgb(165, 62, 48));
    error.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
    error.setVisibility(View.GONE);
    body.addView(error);
    confirmations.addView(
        label(
            person.cloudPersonId.isEmpty() ? "声音先保存在本机，关联人员后可登记云端。" : "姓名来自云端目录，保存后另行确认云端登记。",
            12,
            MUTED));
    name.addTextChangedListener(
        new TextWatcher() {
          public void beforeTextChanged(CharSequence s, int start, int count, int after) {}

          public void onTextChanged(CharSequence s, int start, int before, int count) {
            confirmed.setChecked(false);
          }

          public void afterTextChanged(Editable value) {}
        });
    dialog.action(AlertDialog.BUTTON_NEGATIVE, "取消", false, this::requestDismiss);
    save = dialog.action(AlertDialog.BUTTON_POSITIVE, "确认保存", true, this::save);
    dialog.onBack(this::requestDismiss);
    dialog.setCanceledOnTouchOutside(false);
    dialog.setCancelable(false);
    dialog.setOnKeyListener(
        (d, keyCode, event) -> {
          if (keyCode == KeyEvent.KEYCODE_BACK && event.getAction() == KeyEvent.ACTION_UP) {
            requestDismiss();
            return true;
          }
          return false;
        });
    dialog.setOnDismissListener(d -> cleanup());
    dialog.show();
    dialog.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
    dialog.getButton(AlertDialog.BUTTON_NEGATIVE).setOnClickListener(v -> requestDismiss());
    save = dialog.getButton(AlertDialog.BUTTON_POSITIVE);

    save.setEnabled(false);
    save.setOnClickListener(v -> save());
  }

  private void captureClicked() {
    if (closed || saving || stopping) return;
    if (recording) {
      stopping = true;
      capture.setEnabled(false);
      status.setText("正在整理录音…");
      recorder.stop();
      return;
    }
    stopPlayback();
    clearError();
    if (name.getText().toString().trim().isEmpty()) {
      showError("请填写本人姓名");
      name.requestFocus();
      return;
    }
    synchronized (AppUpdater.GATE) {
      if (RecordingService.active || AppUpdater.installing(activity)) {
        showError("请先结束会议录音或等待更新完成");
        return;
      }
      if (activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO)
          != PackageManager.PERMISSION_GRANTED) {
        showError("请先在系统设置中允许麦克风权限");
        return;
      }
      try {
        discardStaged();
        confirmations.setVisibility(View.GONE);
        confirmed.setChecked(false);
        confirmed.setEnabled(false);
        if (consent != null) {
          consent.setChecked(false);
          consent.setEnabled(false);
        }
        save.setEnabled(false);
        clock.setText("00:00");
        playback.setText("试听已保存声音");
        playback.setVisibility(person.hasVoice() ? View.VISIBLE : View.GONE);
        File target = store.stagingFile();
        recorder = recorderFactory.get();
        recorder.start(target, this::captureFinished);
        recording = true;
        stopping = false;
        name.setEnabled(false);
        save.setEnabled(false);
        playback.setVisibility(View.GONE);
        capture.setText("结束录制");
        status.setText("正在录制 · 最长 5 分钟");
        clock.setText("00:00");
        dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        main.post(tick);
      } catch (Exception failure) {
        recorder = null;
        showError(failure instanceof SecurityException ? "请允许麦克风权限后重试" : "无法开始录制，请检查麦克风和存储空间");
      }
    }
  }

  private void captureFinished(File file, double seconds, String failure) {
    recorder = null;
    recording = false;
    stopping = false;
    main.removeCallbacks(tick);
    if (dialog != null && dialog.getWindow() != null)
      dialog.getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    if (closed) {
      if (file != null) file.delete();
      releaseGate();
      return;
    }
    name.setEnabled(person.cloudPersonId.isEmpty());
    capture.setEnabled(true);
    if (file == null) {
      clock.setText("00:00");
      status.setText("未保存本次录音");
      capture.setText("重新录制");
      showError(failure == null ? "本次录音已取消" : failure);
      playback.setText("试听已保存声音");
      playback.setVisibility(person.hasVoice() ? View.VISIBLE : View.GONE);
      return;
    }
    staged = file;
    stagedSeconds = seconds;
    clock.setText(duration(seconds));
    status.setText("录制完成，请试听并确认");
    capture.setText("重新录制");
    playback.setText("试听本次录音");
    playback.setVisibility(View.VISIBLE);
    confirmations.setVisibility(View.VISIBLE);
    confirmed.setEnabled(true);
    if (consent != null) consent.setEnabled(true);
    save.setEnabled(true);
  }

  private void play() {
    if (recording || saving || closed) return;
    if (player != null) {
      stopPlayback();
      return;
    }
    clearError();
    try {
      File audio = staged != null ? staged : store.voiceFile(personId);
      if (audio == null || !audio.isFile()) throw new IllegalStateException();
      MediaPlayer next = new MediaPlayer();
      player = next;
      next.setDataSource(audio.getAbsolutePath());
      next.setOnPreparedListener(
          p -> {
            if (closed || player != p) return;
            p.start();
            playback.setText("停止试听");
          });
      next.setOnCompletionListener(p -> stopPlayback());
      next.setOnErrorListener(
          (p, what, extra) -> {
            stopPlayback();
            if (!closed) showError("无法试听，请重新录制");
            return true;
          });
      next.prepareAsync();
      playback.setText("停止试听");
    } catch (Exception failure) {
      stopPlayback();
      showError("无法读取声音，请重新录制");
    }
  }

  private void save() {
    if (recording || stopping || saving || closed) return;
    clearError();
    String confirmedName = name.getText().toString().trim();
    if (confirmedName.isEmpty() || confirmedName.length() > 80) {
      showError("姓名请填写 1–80 个字");
      return;
    }
    if (staged == null || !staged.isFile()) {
      showError("请先录制本人声音");
      return;
    }
    if (!confirmed.isChecked()) {
      showError("请核对姓名，并确认这是本人的声音");
      return;
    }
    if (consent != null && !consent.isChecked()) {
      showError("保存前需本人同意在本机保留声音");
      return;
    }
    stopPlayback();
    saving = true;
    name.setEnabled(false);
    capture.setEnabled(false);
    playback.setEnabled(false);
    confirmed.setEnabled(false);
    if (consent != null) consent.setEnabled(false);
    save.setEnabled(false);
    dialog.getButton(AlertDialog.BUTTON_NEGATIVE).setEnabled(false);
    status.setText("正在保存…");
    File toSave = staged;
    double seconds = stagedSeconds;
    boolean agreed = consent != null && consent.isChecked();
    new Thread(
            () -> {
              Exception failure = null;
              try {
                store.saveVoice(personId, confirmedName, toSave, seconds, agreed);
              } catch (Exception e) {
                failure = e;
              }
              final Exception result = failure;
              main.post(
                  () -> {
                    saving = false;
                    if (result == null) {
                      staged = null;
                      toSave.delete();
                      if (!closed) Toast.makeText(activity, "声音已保存到本机", Toast.LENGTH_SHORT).show();
                      dismiss();
                      releaseGate();
                      if (!activity.isDestroyed() && !activity.isFinishing()) onChanged.run();
                    } else if (closed) {
                      discardStaged();
                      releaseGate();
                    } else {
                      name.setEnabled(person.cloudPersonId.isEmpty());
                      capture.setEnabled(true);
                      playback.setEnabled(true);
                      confirmed.setEnabled(true);
                      if (consent != null) consent.setEnabled(true);
                      save.setEnabled(true);
                      dialog.getButton(AlertDialog.BUTTON_NEGATIVE).setEnabled(true);
                      status.setText("保存未完成");
                      showError(
                          result instanceof IllegalArgumentException
                              ? result.getMessage()
                              : "未能保存，请重试；原来的声音仍然保留");
                    }
                  });
            },
            "yanxu-save-voice")
        .start();
  }

  private void requestDismiss() {
    if (saving || closed) return;
    if (!recording && staged == null && person.name.equals(name.getText().toString().trim())) {
      dismiss();
      return;
    }
    if (discardDialog != null && discardDialog.isShowing()) return;
    discardDialog =
        new AlertDialog.Builder(activity)
            .setTitle("放弃本次录入？")
            .setMessage("未保存的录音和修改将丢弃，原来的声音不受影响。")
            .setNegativeButton("继续录入", null)
            .setPositiveButton("放弃", (d, which) -> dismiss())
            .show();
  }

  /** Leaving, locking or rotating cannot retain an unconfirmed microphone recording. */
  public void onHostPause() {
    dismiss();
  }

  public void dismiss() {
    cleanup();
    if (dialog != null && dialog.isShowing()) dialog.dismiss();
  }

  private void cleanup() {
    if (closed) return;
    closed = true;
    main.removeCallbacks(tick);
    if (discardDialog != null && discardDialog.isShowing()) discardDialog.dismiss();
    if (dialog != null && dialog.getWindow() != null)
      dialog.getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    stopPlayback();
    if (recorder != null) recorder.cancel();
    if (!saving) discardStaged();
    if (recorder == null && !saving) releaseGate();
  }

  private void stopPlayback() {
    if (player != null) {
      player.release();
      player = null;
    }
    if (playback != null) playback.setText(staged != null ? "试听本次录音" : "试听已保存声音");
  }

  private void discardStaged() {
    if (staged != null) staged.delete();
    staged = null;
    stagedSeconds = 0;
  }

  private void releaseGate() {
    synchronized (AppUpdater.GATE) {
      if (ownsGate && owner == this) {
        busy = false;
        owner = null;
        ownsGate = false;
      }
    }
  }

  private void showError(String message) {
    error.setText(message);
    error.setVisibility(View.VISIBLE);
  }

  private void clearError() {
    error.setVisibility(View.GONE);
  }

  private int dp(int value) {
    return Math.round(value * activity.getResources().getDisplayMetrics().density);
  }

  private TextView label(String value, int size, int color) {
    TextView view = new TextView(activity);
    view.setText(value);
    view.setTextSize(size);
    view.setTextColor(color);
    view.setPadding(0, dp(4), 0, dp(4));
    return view;
  }

  private Button action(String title, boolean primary, Runnable run) {
    Button view = AppUi.button(activity, title, primary, run);
    LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, dp(48));
    params.topMargin = dp(8);
    params.bottomMargin = dp(8);
    view.setLayoutParams(params);
    view.setOnClickListener(v -> run.run());
    return view;
  }

  private static String duration(double seconds) {
    long total = Math.max(0, (long) seconds);
    return String.format(Locale.ROOT, "%02d:%02d", total / 60, total % 60);
  }
}
