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
  private TextView timer, status;
  private int tab = 0;
  private String lastLocalSignature = "";
  private boolean previousActive = false, previousPaused = false;
  private WebView web;
  private final Handler handler = new Handler(Looper.getMainLooper());
  private final Runnable tick =
      new Runnable() {
        public void run() {
          if (tab == 0) {
            if (timer != null) timer.setText(format(RecordingService.frames / 16000));
            if (status != null) status.setText(RecordingService.message);
            if (previousActive != RecordingService.active
                || previousPaused != RecordingService.paused) {
              render();
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
    render();
    handler.post(tick);
  }

  @Override
  protected void onResume() {
    super.onResume();
    LocalStore.enqueue(this);
    if (tab == 2) render();
  }

  @Override
  protected void onDestroy() {
    handler.removeCallbacks(tick);
    if (web != null) web.destroy();
    super.onDestroy();
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
    TextView settings = text("设置", 13, MUTED);
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
    np.topMargin = dp(24);
    np.bottomMargin = dp(tab == 1 ? 0 : 24);
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
    LinearLayout card = new LinearLayout(this);
    card.setOrientation(1);
    card.setGravity(Gravity.CENTER);
    card.setPadding(dp(22), dp(40), dp(22), dp(32));
    card.setBackground(bg(Color.WHITE, 18));
    status = text(RecordingService.message, 14, MUTED);
    status.setGravity(Gravity.CENTER);
    card.addView(status);
    timer = text(format(RecordingService.frames / 16000), 45, INK);
    timer.setGravity(Gravity.CENTER);
    timer.setTypeface(Typeface.MONOSPACE);
    LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(-1, -2);
    tp.topMargin = dp(28);
    tp.bottomMargin = dp(22);
    card.addView(timer, tp);
    if (!RecordingService.active) {
      card.addView(button("开始录音", true, this::startRecording));
    } else {
      card.addView(
          button(RecordingService.paused ? "继续录音" : "暂停录音", false, () -> command("pause")));
      card.addView(button("结束并保存", true, () -> command("stop")));
    }
    content.addView(card);
    TextView hint = text("本地保存 · 自动上传", 11, MUTED);
    hint.setGravity(Gravity.CENTER);
    hint.setPadding(0, dp(18), 0, 0);
    content.addView(hint);
  }

  private void command(String action) {
    Intent i = new Intent(this, RecordingService.class).setAction(action);
    if ("start".equals(action)) startForegroundService(i);
    else startService(i);
  }

  private void startRecording() {
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
    if (request == 100) {
      if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
          == PackageManager.PERMISSION_GRANTED) command("start");
      else {
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
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(1);
        row.setPadding(dp(17), dp(15), dp(17), dp(16));
        row.setBackground(bg(Color.WHITE, 12));
        row.addView(text(m.optString("title", "录音"), 16, INK));
        String state = m.optString("state");
        String label =
            switch (state) {
              case "recording" -> "录音中";
              case "paused" -> "已暂停";
              case "uploading" -> "上传中 " + m.optInt("progress") + "%";
              case "uploaded" -> "已上传";
              case "retry" -> "等待重试";
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
                    tab = 1;
                    render();
                    web.loadUrl(LocalStore.server(this) + "/?app=1#/records/" + id);
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
    content.addView(web, new LinearLayout.LayoutParams(-1, -1));
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
                  if (RecordingService.active) {
                    Toast.makeText(this, "请先结束录音", Toast.LENGTH_SHORT).show();
                    return;
                  }
                  Intent i =
                      new Intent(Intent.ACTION_OPEN_DOCUMENT)
                          .setType("audio/*")
                          .addCategory(Intent.CATEGORY_OPENABLE);
                  startActivityForResult(i, 201);
                })
            .create();
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
                          || u.getFragment() != null) {
                        edit.setError("请输入有效服务地址");
                        return;
                      }
                      getSharedPreferences("settings", 0).edit().putString("server", value).apply();
                      LocalStore.enqueue(this);
                      d.dismiss();
                      render();
                    }));
    d.show();
  }

  @Override
  protected void onActivityResult(int request, int result, Intent data) {
    super.onActivityResult(request, result, data);
    if (request != 201 || result != RESULT_OK || data == null) return;
    Uri uri = data.getData();
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
                LocalStore.save(dir, m);
                LocalStore.enqueue(this);
                runOnUiThread(
                    () -> {
                      tab = 2;
                      render();
                    });
              } catch (Exception e) {
                runOnUiThread(() -> Toast.makeText(this, "导入失败，请重新选择音频", Toast.LENGTH_LONG).show());
              }
            },
            "yanxu-import")
        .start();
  }

  private String format(long sec) {
    return String.format(Locale.ROOT, "%02d:%02d:%02d", sec / 3600, sec / 60 % 60, sec % 60);
  }
}
