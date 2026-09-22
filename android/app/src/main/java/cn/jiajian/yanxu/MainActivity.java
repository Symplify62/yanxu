package cn.jiajian.yanxu;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.webkit.*;
import android.widget.*;
import java.io.*;
import java.text.*;
import java.util.*;
import org.json.*;

public class MainActivity extends Activity {
  private final int GREEN = Color.rgb(70, 107, 79),
      INK = Color.rgb(39, 61, 49),
      MUTED = Color.rgb(114, 128, 117),
      BG = Color.rgb(251, 252, 248);
  private LinearLayout shell, content, actions;
  private TextView timer, status, settingsLabel;
  private int tab = 0;
  private String lastLocalSignature = "";
  private boolean previousActive = false, previousPaused = false;
  private WebView web;
  private PeopleStore peopleStore;
  private CloudAccountUi cloudUi;
  private AlertDialog settingsDialog;
  private PeoplePanel peoplePanel;
  private VoiceEnrollmentDialog voiceDialog;
  private TextView participantCount;
  private String pendingVoiceId;
  private JSONObject pendingRecordingContext;
  private JSONObject pendingImportContext;
  private String displayedSession = "";
  private final Handler handler = new Handler(Looper.getMainLooper());
  private final Runnable tick =
      new Runnable() {
        public void run() {
          if (!sessionDisplayKey().equals(displayedSession)) {
            cloudUi.dismissProtected();
            if (voiceDialog != null) voiceDialog.dismiss();
            pendingVoiceId = null;
            useAccountStore(); render();
          }
          if (settingsLabel != null)
            settingsLabel.setText(AppUpdater.needsAction(MainActivity.this) ? "设置 · 更新" : "设置");
          if (tab == 0) {
            if (timer != null) timer.setText(format(RecordingService.frames / 16000));
            if (status != null) status.setText(RecordingService.message);
            if (previousActive != RecordingService.active
                || previousPaused != RecordingService.paused) {
              render();
              AppUpdater.kick(MainActivity.this, false);
            }
          } else if (tab == 2 && !localSignature().equals(lastLocalSignature)) {
            render();
          }
          handler.postDelayed(this, 500);
        }
      };

  @Override
  public void onCreate(Bundle state) {
    super.onCreate(state);
    getWindow().setStatusBarColor(BG);
    getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
    LocalStore.recover(this);
    cloudUi = new CloudAccountUi(this, () -> { useAccountStore(); render(); });
    useAccountStore();
    try {
      if (!VoiceEnrollmentDialog.busy) peopleStore.recover();
    } catch (Exception e) {
      Toast.makeText(this, "人员资料恢复异常，请保留应用数据", Toast.LENGTH_LONG).show();
    }
    render();
    handler.post(tick);
    AppUpdater.recover(this);
    AppUpdater.schedule(this);
    if (getIntent().getBooleanExtra("showUpdates", false))
      handler.post(() -> UpdateDialog.show(this));
  }

  @Override
  protected void onResume() {
    super.onResume();
    LocalStore.enqueue(this);
    UpdateInstaller.foreground = new java.lang.ref.WeakReference<>(this);
    boolean manual = AppUpdater.prefs(this).getBoolean("resumeInstall", false);
    AppUpdater.prefs(this).edit().remove("resumeInstall").apply();
    AppUpdater.kick(this, manual);
    if (tab == 2) render();
  }

  @Override
  protected void onPause() {
    if (voiceDialog != null) voiceDialog.onHostPause();
    UpdateInstaller.foreground.clear();
    super.onPause();
  }

  @Override
  protected void onDestroy() {
    if (cloudUi != null) cloudUi.close();
    if (settingsDialog != null) settingsDialog.dismiss();
    if (voiceDialog != null) voiceDialog.dismiss();
    if (peoplePanel != null) peoplePanel.dismiss();
    handler.removeCallbacks(tick);
    if (web != null) web.destroy();
    super.onDestroy();
  }

  @Override
  public void onConfigurationChanged(android.content.res.Configuration configuration) {
    super.onConfigurationChanged(configuration);
    if (voiceDialog != null) voiceDialog.onHostPause();
    render();
  }

  private int dp(int n) {
    return Math.round(n * getResources().getDisplayMetrics().density);
  }

  private GradientDrawable bg(int color, int radius) {
    GradientDrawable g = new GradientDrawable();
    g.setColor(color);
    g.setCornerRadius(dp(radius));
    g.setStroke(dp(1), Color.rgb(227, 232, 223));
    return g;
  }

  private TextView text(String value, int sp, int color) {
    TextView v = new TextView(this);
    v.setText(value);
    v.setTextSize(sp);
    v.setTextColor(color);
    v.setPadding(0, dp(5), 0, dp(5));
    return v;
  }

  private Button button(String label, boolean primary, Runnable action) {
    Button b = new Button(this);
    b.setText(label);
    b.setTextSize(14);
    b.setAllCaps(false);
    b.setTextColor(primary ? Color.WHITE : INK);
    b.setBackground(bg(primary ? GREEN : Color.WHITE, 10));
    b.setPadding(dp(16), 0, dp(16), 0);
    b.setMinHeight(dp(48));
    b.setOnClickListener(v -> action.run());
    LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, dp(50));
    p.topMargin = dp(12);
    b.setLayoutParams(p);
    return b;
  }

  private void render() {
    displayedSession = sessionDisplayKey();
    if (peoplePanel != null) {
      peoplePanel.dismiss();
      peoplePanel = null;
    }
    participantCount = null;
    if (web != null) {
      web.destroy();
      web = null;
    }
    shell = new LinearLayout(this);
    shell.setOrientation(1);
    shell.setBackgroundColor(BG);
    shell.setPadding(dp(20), dp(14), dp(20), dp(16));
    if (Build.VERSION.SDK_INT >= 21)
      shell.setOnApplyWindowInsetsListener(
          (v, insets) -> {
            v.setPadding(
                dp(20),
                dp(14) + insets.getSystemWindowInsetTop(),
                dp(20),
                dp(16) + insets.getSystemWindowInsetBottom());
            return insets;
          });
    LinearLayout top = new LinearLayout(this);
    top.setGravity(Gravity.CENTER_VERTICAL);
    TextView brand = text("言序", 25, GREEN);
    brand.setTypeface(null, Typeface.BOLD);
    top.addView(brand, new LinearLayout.LayoutParams(0, -2, 1));
    CloudSession headerSession = CloudSession.current(this);
    TextView account = text(headerSession != null && headerSession.valid() ? "账号" : "登录", 13, GREEN);
    account.setContentDescription(headerSession != null && headerSession.valid() ? "账号与云端资料" : "账号登录");
    account.setPadding(dp(12), dp(10), dp(12), dp(10));
    account.setOnClickListener(v -> cloudUi.account());
    top.addView(account);
    TextView settings = text("设置", 13, MUTED);
    settingsLabel = settings;
    settings.setPadding(dp(12), dp(10), dp(12), dp(10));
    settings.setOnClickListener(v -> settings());
    top.addView(settings);
    shell.addView(top);
    LinearLayout nav = new LinearLayout(this);
    String[] labels = {"快速录音", "公共记录", "本地录音"};
    for (int i = 0; i < 3; i++) {
      final int target = i;
      TextView item = text(labels[i], 13, tab == i ? GREEN : MUTED);
      item.setGravity(Gravity.CENTER);
      if (tab == i) item.setBackground(bg(Color.rgb(234, 240, 228), 8));
      item.setPadding(dp(6), dp(12), dp(6), dp(12));
      item.setOnClickListener(
          v -> {
            tab = target;
            render();
          });
      nav.addView(item, new LinearLayout.LayoutParams(0, -2, 1));
    }
    LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(-1, -2);
    np.topMargin = dp(16);
    np.bottomMargin = dp(tab == 1 ? 0 : 16);
    shell.addView(nav, np);
    content = new LinearLayout(this);
    content.setOrientation(1);
    shell.addView(content, new LinearLayout.LayoutParams(-1, 0, 1));
    setContentView(shell);
    shell.requestApplyInsets();
    if (tab == 0) recordView();
    else if (tab == 1) webView(null);
    else localView();
  }

  private void recordView() {
    previousActive = RecordingService.active;
    previousPaused = RecordingService.paused;
    ScrollView scroll = new ScrollView(this);
    scroll.setFillViewport(false);
    LinearLayout body = new LinearLayout(this);
    body.setOrientation(1);
    scroll.addView(body);
    content.addView(scroll, new LinearLayout.LayoutParams(-1, -1));
    LinearLayout card = new LinearLayout(this);
    card.setOrientation(1);
    card.setGravity(Gravity.CENTER);
    card.setPadding(dp(22), dp(22), dp(22), dp(24));
    card.setBackground(bg(Color.WHITE, 18));
    status = text(RecordingService.message, 14, MUTED);
    status.setGravity(Gravity.CENTER);
    card.addView(status);
    timer = text(format(RecordingService.frames / 16000), 38, INK);
    timer.setGravity(Gravity.CENTER);
    timer.setTypeface(Typeface.MONOSPACE);
    LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(-1, -2);
    tp.topMargin = dp(16);
    tp.bottomMargin = dp(12);
    card.addView(timer, tp);
    if (!RecordingService.active) {
      card.addView(button("开始录音", true, this::startRecording));
    } else {
      card.addView(
          button(RecordingService.paused ? "继续录音" : "暂停录音", false, () -> command("pause")));
      card.addView(button("结束并保存", true, () -> command("stop")));
    }
    body.addView(card);
    TextView hint = text("本地保存 · 自动上传", 11, MUTED);
    hint.setGravity(Gravity.CENTER);
    hint.setPadding(0, dp(18), 0, 0);
    body.addView(hint);
    participantCount = text("", 12, MUTED);
    participantCount.setGravity(Gravity.CENTER);
    body.addView(participantCount);
    updateParticipantCount();
    CloudSession activeSession = CloudSession.current(this);
    LinearLayout featureActions = new LinearLayout(this);
    Button participants = button("选择参会者", false, this::openParticipantPicker);
    Button voices = button("声音档案", false, this::openVoiceProfiles);
    LinearLayout.LayoutParams participantLayout = new LinearLayout.LayoutParams(0, dp(50), 1);
    participantLayout.topMargin = dp(12); participantLayout.rightMargin = dp(6);
    LinearLayout.LayoutParams voiceLayout = new LinearLayout.LayoutParams(0, dp(50), 1);
    voiceLayout.topMargin = dp(12); voiceLayout.leftMargin = dp(6);
    participants.setEnabled(!RecordingService.active); voices.setEnabled(!RecordingService.active);
    featureActions.addView(participants, participantLayout); featureActions.addView(voices, voiceLayout);
    body.addView(featureActions);
    if (activeSession == null || !activeSession.valid() || !activeSession.allows("record")) return;
    body.addView(button("同步人员与声纹", false, () -> cloudUi.sync()));
    peoplePanel =
        new PeoplePanel(
            this,
            peopleStore,
            new PeoplePanel.Listener() {
              @Override
              public void onEnroll(String personId) {
                if (!requirePeopleLogin(() -> openVoiceProfiles())) return;
                cloudUi.voice(peopleStore, personId, () -> requestVoiceRecording(personId));
              }

              @Override
              public void onSelectionChanged() {
                updateParticipantCount();
              }

              @Override public boolean onAddRequested() { cloudUi.addPerson(); return true; }
              @Override public boolean canAddPeople() { return canChoosePeople(); }
              @Override public boolean canSelectPeople() { return canChoosePeople(); }
            });
    body.addView(peoplePanel.build());
    if (!RecordingService.active) {
      body.addView(
          button(
              "准备下一场",
              false,
              () ->
                  new AlertDialog.Builder(this)
                      .setTitle("准备下一场会议？")
                      .setMessage("清空本场选择和临时来宾，保留本机成员及其声音。")
                      .setNegativeButton("取消", null)
                      .setPositiveButton(
                          "确认",
                          (d, which) -> {
                            if (RecordingService.active || VoiceEnrollmentDialog.busy) {
                              Toast.makeText(this, "请先结束当前录音或声音录入", Toast.LENGTH_SHORT).show();
                              return;
                            }
                            try {
                              peopleStore.nextMeeting();
                              peoplePanel.refresh();
                              updateParticipantCount();
                            } catch (Exception e) {
                              Toast.makeText(this, "无法保存本场名单，请重试", Toast.LENGTH_LONG).show();
                            }
                          })
                      .show()));
    }
  }

  private void updateParticipantCount() {
    if (participantCount == null) return;
    CloudSession session = CloudSession.current(this);
    if (session == null || !session.valid() || !session.allows("record")) { participantCount.setVisibility(View.GONE); return; }
    participantCount.setVisibility(View.VISIBLE);
    try {
      int count = peopleStore.selected().size();
      participantCount.setText(count == 0 ? "未选参会者" : "本场 " + count + " 人 · 录音开始后名单固定");
    } catch (Exception e) {
      participantCount.setText("名单读取失败，请保留应用数据");
    }
  }

  private void requestVoiceRecording(String personId) {
    if (!requirePeopleLogin(this::openVoiceProfiles)) return;
    if (RecordingService.active || VoiceEnrollmentDialog.busy) {
      Toast.makeText(this, "请先结束当前录音或声音录入", Toast.LENGTH_SHORT).show();
      return;
    }
    if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
        != PackageManager.PERMISSION_GRANTED) {
      pendingVoiceId = personId;
      requestPermissions(new String[] {Manifest.permission.RECORD_AUDIO}, 101);
      return;
    }
    voiceDialog =
        new VoiceEnrollmentDialog(
            this,
            peopleStore,
            personId,
            () -> {
              if (peoplePanel != null) peoplePanel.refresh();
              updateParticipantCount();
              CloudSession session = CloudSession.current(this);
              if (session != null && session.valid()) cloudUi.consent(peopleStore,personId);
            });
    voiceDialog.show();
  }

  private void command(String action) {
    Intent i = new Intent(this, RecordingService.class).setAction(action);
    if ("start".equals(action)) {
      if (VoiceEnrollmentDialog.busy) {
        Toast.makeText(this, "请先完成或取消声音录入", Toast.LENGTH_SHORT).show();
        return;
      }
      try {
        JSONObject context = pendingRecordingContext;
        pendingRecordingContext = null;
        if (context == null) context = RecordingIdentity.captureForRecording(this, peopleStore.snapshot());
        i.putExtra("recordingContext", context.toString());
      } catch (Exception e) {
        recordingBlocked(e);
        return;
      }
      startForegroundService(i);
    } else startService(i);
  }

  private void useAccountStore() {
    CloudSession session = CloudSession.current(this);
    peopleStore = session == null ? new PeopleStore(this,CloudSession.scope("signed-out","hidden")) : new PeopleStore(this,session.scope());
  }

  private String sessionDisplayKey() {
    CloudSession session = CloudSession.current(this);
    return session == null ? "guest" : session.scope() + ":" + session.valid() + ":" + session.account.optJSONArray("permissions");
  }

  private boolean canChoosePeople() {
    CloudSession session = CloudSession.current(this);
    return session != null && session.valid() && session.allows("record");
  }

  private boolean requirePeopleLogin(Runnable continuation) {
    CloudSession session = CloudSession.current(this);
    if (session == null || !session.valid()) { cloudUi.login(continuation); return false; }
    return true;
  }

  private void openParticipantPicker() {
    if (RecordingService.active || VoiceEnrollmentDialog.busy) {
      Toast.makeText(this, "请先结束录音或声音录入", Toast.LENGTH_SHORT).show(); return;
    }
    if (!requirePeopleLogin(this::openParticipantPicker)) return;
    if (!canChoosePeople()) { Toast.makeText(this,"当前账号没有选择参会者的权限",Toast.LENGTH_LONG).show(); return; }
    tab = 0; useAccountStore(); render();
    if (peoplePanel != null) peoplePanel.showPicker();
  }

  private void openVoiceProfiles() {
    if (RecordingService.active || VoiceEnrollmentDialog.busy) {
      Toast.makeText(this, "请先结束录音或声音录入", Toast.LENGTH_SHORT).show(); return;
    }
    if (!requirePeopleLogin(this::openVoiceProfiles)) return;
    useAccountStore();
    cloudUi.voices(peopleStore, this::requestVoiceRecording);
  }

  private void recordingBlocked(Exception error) {
    try {
      if (!peopleStore.selected().isEmpty() && !canChoosePeople()) {
        new AlertDialog.Builder(this).setTitle("本场名单需要登录")
            .setMessage("重新登录使用已选人员，或清空名单后普通录音。")
            .setNegativeButton("取消", null)
            .setNeutralButton("清空本场名单", (d, which) -> {
              try {
                ArrayList<String> ids = new ArrayList<>();
                for (PeopleStore.Person person : peopleStore.selected()) ids.add(person.id);
                peopleStore.setSelected(ids, false); render();
              } catch (Exception e) { Toast.makeText(this,"名单未能清空，请重试",Toast.LENGTH_LONG).show(); }
            })
            .setPositiveButton("登录", (d, which) -> cloudUi.login()).show();
        return;
      }
    } catch (Exception ignored) {}
    Toast.makeText(this,error.getMessage() == null ? "尚未开始录音，请重试" : error.getMessage(),Toast.LENGTH_LONG).show();
  }

  private void startRecording() {
    try { pendingRecordingContext = RecordingIdentity.captureForRecording(this, peopleStore.snapshot()); }
    catch (Exception e) { recordingBlocked(e); return; }
    if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
        != PackageManager.PERMISSION_GRANTED) {
      ArrayList<String> permissions = new ArrayList<>();
      permissions.add(Manifest.permission.RECORD_AUDIO);
      if (Build.VERSION.SDK_INT >= 33) permissions.add(Manifest.permission.POST_NOTIFICATIONS);
      requestPermissions(permissions.toArray(new String[0]), 100);
      return;
    }
    command("start");
  }

  @Override
  public void onRequestPermissionsResult(int request, String[] permissions, int[] grants) {
    super.onRequestPermissionsResult(request, permissions, grants);
    if (request == 101) {
      String personId = pendingVoiceId;
      pendingVoiceId = null;
      if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
          && personId != null) requestVoiceRecording(personId);
      else Toast.makeText(this, "未获得麦克风权限，声音尚未录制", Toast.LENGTH_LONG).show();
    } else if (request == 100) {
      if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
          == PackageManager.PERMISSION_GRANTED) command("start");
      else {
        pendingRecordingContext = null;
        RecordingService.message = "请允许麦克风权限";
        render();
      }
    }
  }

  private String localSignature() {
    StringBuilder b = new StringBuilder();
    for (File d : LocalStore.all(this)) {
      File m = new File(d, "meta.json");
      b.append(m.lastModified()).append(":").append(m.length()).append(";");
    }
    return b.toString();
  }

  private void localView() {
    lastLocalSignature = localSignature();
    ScrollView scroll = new ScrollView(this);
    LinearLayout list = new LinearLayout(this);
    list.setOrientation(1);
    scroll.addView(list);
    content.addView(scroll);
    for (File dir : LocalStore.all(this)) {
      try {
        JSONObject m = LocalStore.read(dir);
        if (!RecordingIdentity.visible(this,m)) continue;
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(1);
        row.setPadding(dp(17), dp(15), dp(17), dp(16));
        row.setBackground(bg(Color.WHITE, 12));
        row.addView(text(m.optString("title", "录音"), 16, INK));
        JSONObject roster = m.optJSONObject("participantsSnapshot");
        if (roster != null && m.has("cloudIdentity")) {
          JSONArray participants = roster.optJSONArray("participants");
          if (participants != null && participants.length() > 0) {
            ArrayList<String> names = new ArrayList<>();
            for (int p = 0; p < participants.length(); p++)
              names.add(participants.getJSONObject(p).optString("name"));
            row.addView(text("本场名单：" + String.join("、", names), 12, MUTED));
          }
        }
        String state = m.optString("state");
        String label =
            switch (state) {
              case "recording" -> "录音中";
              case "paused" -> "已暂停";
              case "uploading" -> "上传中 " + m.optInt("progress") + "%";
              case "uploaded" -> "已上传";
              case "retry" -> "等待重试";
              case "awaiting_login" -> "等待原账号登录";
              case "blocked" -> "上传受阻";
              case "saved" -> "已保存，等待上传";
              default -> "请检查录音";
            };
        row.addView(
            text(
                label
                    + " · "
                    + (m.has("duration") ? format((long) m.optDouble("duration")) : "时长待识别"),
                12,
                MUTED));
        if ("blocked".equals(state))
          row.addView(text(m.optString("message"), 11, Color.rgb(150, 107, 46)));
        if (m.optBoolean("interrupted"))
          row.addView(text("录音中断，已保留现有内容", 11, Color.rgb(150, 107, 46)));
        if ("uploaded".equals(state)) {
          String id = m.getString("server_id");
          row.addView(
              button(
                  "查看结果",
                  false,
                  () -> {
                    if (m.has("cloudIdentity")) { showPrivateTranscript(m,id); return; }
                    String base = m.optString("uploadServer",LocalStore.server(this));
                    if (!base.equals(LocalStore.server(this))) { Toast.makeText(this,"请切回原服务查看此录音",Toast.LENGTH_LONG).show(); return; }
                    tab = 1;
                    render();
                    web.loadUrl(base + "/?app=1#/records/" + id);
                  }));
        } else if (!RecordingService.active)
          row.addView(
              button(
                  "重试上传",
                  false,
                  () -> {
                    try {
                      JSONObject latest = LocalStore.read(dir);
                      latest.put("state", "saved");
                      LocalStore.save(dir, latest);
                    } catch (Exception ignored) {
                    }
                    LocalStore.enqueue(this);
                    Toast.makeText(this, "已安排上传", Toast.LENGTH_SHORT).show();
                  }));
        LinearLayout.LayoutParams rp = new LinearLayout.LayoutParams(-1, -2);
        rp.bottomMargin = dp(13);
        list.addView(row, rp);
      } catch (Exception ignored) {
      }
    }
    if (list.getChildCount() == 0) list.addView(text("暂无本地录音", 15, MUTED));
    list.addView(
        button(
            "刷新",
            false,
            () -> {
              LocalStore.enqueue(this);
              render();
            }));
  }

  private void webView(String id) {
    web = new WebView(this);
    try {
      int version = getPackageManager().getPackageInfo(getPackageName(), 0).versionCode;
      SharedPreferences preferences = getSharedPreferences("settings", 0);
      if (preferences.getInt("webCacheVersion", -1) != version) {
        web.clearCache(true);
        preferences.edit().putInt("webCacheVersion", version).apply();
      }
    } catch (PackageManager.NameNotFoundException ignored) {
    }
    web.setBackgroundColor(BG);
    web.getSettings().setJavaScriptEnabled(true);
    web.getSettings().setDomStorageEnabled(true);
    web.getSettings().setAllowFileAccess(false);
    web.getSettings().setAllowContentAccess(false);
    web.setWebViewClient(
        new WebViewClient() {
          @Override
          public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest r) {
            return !sameServer(r.getUrl()) && !AudioOrigin.allows(r.getUrl().toString());
          }
        });
    web.setDownloadListener(
        (url, ua, cd, mime, len) -> {
          Uri uri = Uri.parse(url);
          if (sameServer(uri) || AudioOrigin.allows(url)) {
            DownloadManager.Request request =
                new DownloadManager.Request(uri)
                    .setNotificationVisibility(
                        DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                    .setTitle("言序录音");
            if (Build.VERSION.SDK_INT >= 29) {
              request.setDestinationInExternalPublicDir(
                  Environment.DIRECTORY_DOWNLOADS, URLUtil.guessFileName(url, cd, mime));
            }
            getSystemService(DownloadManager.class).enqueue(request);
            Toast.makeText(this, "已开始下载", Toast.LENGTH_SHORT).show();
          }
        });
    CloudSession login = CloudSession.current(this);
    if (login != null && login.valid()) content.addView(button("我的会议 · 具名逐字稿", false, () -> showMyMeetings(0)));
    content.addView(web, new LinearLayout.LayoutParams(-1, 0, 1));
    web.loadUrl(LocalStore.server(this) + (id == null ? "/?app=1" : "/?app=1#/records/" + id));
  }

  private boolean sameServer(Uri uri) {
    Uri base = Uri.parse(LocalStore.server(this));
    return Objects.equals(uri.getScheme(), base.getScheme())
        && Objects.equals(uri.getHost(), base.getHost())
        && uri.getPort() == base.getPort();
  }

  private void settings() {
    LinearLayout box = new LinearLayout(this);
    box.setOrientation(1);
    box.setPadding(dp(22), dp(10), dp(22), 0);
    CloudSession session = CloudSession.current(this);
    box.addView(button(session == null || !session.valid() ? "账号登录" : "账号 · " + session.account.optString("displayName",session.account.optString("username")),false,() -> {
      if (settingsDialog != null) settingsDialog.dismiss();
      cloudUi.account();
    }));
    box.addView(text("服务地址", 13, MUTED));
    EditText edit = new EditText(this);
    edit.setSingleLine(true);
    edit.setInputType(
        android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_URI);
    edit.setText(LocalStore.server(this));
    box.addView(edit);
    AlertDialog d =
        new AlertDialog.Builder(this)
            .setTitle("连接设置")
            .setView(box)
            .setNegativeButton("取消", null)
            .setPositiveButton("保存", null)
            .setNeutralButton(
                "导入音频",
                (v, w) -> {
                  if (RecordingService.active || VoiceEnrollmentDialog.busy) {
                    Toast.makeText(this, "请先结束录音", Toast.LENGTH_SHORT).show();
                    return;
                  }
                  try { pendingImportContext = RecordingIdentity.captureForRecording(this,new JSONObject().put("participants",new JSONArray())); }
                  catch (Exception e) { recordingBlocked(e); return; }
                  Intent i =
                      new Intent(Intent.ACTION_OPEN_DOCUMENT)
                          .setType("audio/*")
                          .addCategory(Intent.CATEGORY_OPENABLE);
                  startActivityForResult(i, 201);
                })
            .create();
    box.addView(
        button(
            "应用更新 · " + AppUpdater.versionName(this),
            false,
            () -> {
              d.dismiss();
              UpdateDialog.show(this);
            }));
    d.setOnShowListener(
        v ->
            d.getButton(AlertDialog.BUTTON_POSITIVE)
                .setOnClickListener(
                    b -> {
                      String value = edit.getText().toString().trim().replaceAll("/+$", "");
                      Uri u = Uri.parse(value);
                      if (u.getHost() == null
                          || !("http".equals(u.getScheme()) || "https".equals(u.getScheme()))
                          || u.getQuery() != null
                          || u.getFragment() != null || u.getUserInfo() != null
                          || (u.getPath() != null && !u.getPath().isEmpty() && !"/".equals(u.getPath()))) {
                        edit.setError("请输入有效服务地址");
                        return;
                      }
                      if (RecordingService.active || VoiceEnrollmentDialog.busy) { edit.setError("请先结束录音或声音录入"); return; }
                      if (value.equals(LocalStore.server(this))) { d.dismiss(); return; }
                      d.dismiss();
                      cloudUi.switchServer(value);
                    }));
    settingsDialog = d;
    d.show();
  }

  @Override
  protected void onActivityResult(int request, int result, Intent data) {
    super.onActivityResult(request, result, data);
    if (request != 201) return;
    final JSONObject recordingContext = pendingImportContext;
    pendingImportContext = null;
    if (result != RESULT_OK || data == null) return;
    Uri uri = data.getData();
    if (recordingContext == null) { Toast.makeText(this,"导入已中断，请重新选择音频",Toast.LENGTH_LONG).show(); return; }
    synchronized (AppUpdater.GATE) {
      if (AppUpdater.installing(this)) {
        Toast.makeText(this, "正在更新，请稍后导入", Toast.LENGTH_SHORT).show();
        return;
      }
      AppUpdater.importing = true;
    }
    new Thread(
            () -> {
              try {
                String mime = getContentResolver().getType(uri);
                String ext =
                    "audio/mpeg".equals(mime)
                        ? "mp3"
                        : mime != null && mime.contains("wav")
                            ? "wav"
                            : mime != null && mime.contains("webm") ? "webm" : "m4a";
                File dir = new File(LocalStore.root(this), UUID.randomUUID().toString());
                dir.mkdirs();
                String name = "import." + ext;
                try (InputStream in = getContentResolver().openInputStream(uri);
                    FileOutputStream out = new FileOutputStream(new File(dir, name))) {
                  byte[] buf = new byte[65536];
                  int n;
                  while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
                  out.getFD().sync();
                }
                JSONObject m =
                    new JSONObject()
                        .put("client_id", dir.getName())
                        .put(
                            "title",
                            "导入录音 · "
                                + new SimpleDateFormat("MM月dd日 HH:mm", Locale.CHINA)
                                    .format(new Date()))
                        .put("filename", name)
                        .put("state", "saved")
                        .put("createdAt", System.currentTimeMillis());
                for (Iterator<String> keys = recordingContext.keys(); keys.hasNext();) {
                  String key = keys.next(); m.put(key,recordingContext.get(key));
                }
                LocalStore.save(dir, m);
                LocalStore.enqueue(this);
                runOnUiThread(
                    () -> {
                      tab = 2;
                      render();
                    });
              } catch (Exception e) {
                runOnUiThread(() -> Toast.makeText(this, "导入失败，请重新选择音频", Toast.LENGTH_LONG).show());
              } finally {
                AppUpdater.importing = false;
                AppUpdater.kick(this, false);
              }
            },
            "yanxu-import")
        .start();
  }

  private void showPrivateTranscript(JSONObject metadata, String id) {
    try {
      CloudSession owner = RecordingIdentity.requireOwner(this,metadata);
      if (owner == null) throw new IOException("请登录原账号查看");
      showPrivateTranscript(owner,id);
    } catch(Exception e) { Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show(); }
  }

  private void showMyMeetings(int offset) {
    CloudSession session = CloudSession.current(this);
    if (session == null || !session.valid()) { cloudUi.login(() -> showMyMeetings(offset)); return; }
    new Thread(() -> {
      try {
        JSONObject result = CloudApi.request(session,"GET","/api/managed/recordings?limit=30&offset="+offset,null);
        JSONArray records = result.getJSONArray("items");
        runOnUiThread(() -> {
          if (isFinishing() || isDestroyed() || !CloudSession.same(this,session)) return;
          LinearLayout body = new LinearLayout(this); body.setOrientation(1); body.setPadding(dp(18),dp(8),dp(18),dp(8));
          ScrollView scroll = new ScrollView(this);scroll.addView(body);
          AlertDialog list = new AlertDialog.Builder(this).setTitle("我的会议").setView(scroll).setPositiveButton("完成",null).create();
          if (records.length()==0) body.addView(text("暂无可查看的会议",14,MUTED));
          for(int i=0;i<records.length();i++) {
            JSONObject row=records.optJSONObject(i);if(row==null)continue;
            String id=row.optString("id");
            body.addView(button(row.optString("title","会议"),false,()->{list.dismiss();showPrivateTranscript(session,id);}));
          }
          if (offset>0) body.addView(button("上一页",false,()->{list.dismiss();showMyMeetings(Math.max(0,offset-30));}));
          if(offset+records.length()<result.optInt("total"))body.addView(button("下一页",false,()->{list.dismiss();showMyMeetings(offset+30);}));
          list.show();
        });
      }catch(Exception e){runOnUiThread(()->Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show());}
    },"yanxu-my-meetings").start();
  }

  private void showPrivateTranscript(CloudSession owner, String id) {
    new Thread(() -> {
      try {
        JSONObject result = CloudApi.request(owner,"GET","/api/managed/recordings/"+CloudApi.id(id),null);
        runOnUiThread(() -> {
          if (isFinishing() || isDestroyed() || !CloudSession.same(this,owner)) return;
          LinearLayout body = new LinearLayout(this); body.setOrientation(1); body.setPadding(dp(18),dp(8),dp(18),dp(8));
          String speakerNotice = speakerNotice(result.optString("speakerStatus"));
          if (!speakerNotice.isEmpty()) body.addView(text(speakerNotice,13,MUTED));
          JSONObject transcript = result.optJSONObject("transcript");
          JSONArray segments = transcript == null ? null : transcript.optJSONArray("segments");
          if (segments == null || segments.length() == 0) body.addView(text("正在处理，稍后重新查看",14,MUTED));
          else for (int i=0;i<segments.length();i++) {
            JSONObject segment = segments.optJSONObject(i); if (segment == null) continue;
            Object speaker = segment.opt("speaker"); String label = speaker instanceof JSONObject
                ? ((JSONObject)speaker).optString("displayName",((JSONObject)speaker).optString("name","未识别"))
                : speaker == null || speaker == JSONObject.NULL || speaker.toString().isEmpty() ? "未识别" : speaker.toString();
            body.addView(text(label+" · "+format((long)segment.optDouble("start")),13,GREEN));
            body.addView(text(segment.optString("text"),16,INK));
          }
          ScrollView scroll=new ScrollView(this);scroll.addView(body);
          new AlertDialog.Builder(this).setTitle("会议逐字稿").setView(scroll).setPositiveButton("完成",null).show();
        });
      } catch(Exception e) { runOnUiThread(() -> Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show()); }
    },"yanxu-private-transcript").start();
  }

  static String speakerNotice(String status) {
    return switch(status) {
      case "waiting" -> "正在识别发言人";
      case "failed" -> "发言人识别未完成，逐字稿已保留";
      default -> "";
    };
  }

  private String format(long sec) {
    return String.format(Locale.ROOT, "%02d:%02d:%02d", sec / 3600, sec / 60 % 60, sec % 60);
  }
}
