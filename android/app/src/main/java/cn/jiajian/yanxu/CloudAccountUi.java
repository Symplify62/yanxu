package cn.jiajian.yanxu;

import android.app.*;
import android.content.*;
import android.graphics.Color;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.widget.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import org.json.*;

/** Account, explicit local migration and private voice operations, separate from recording UI. */
final class CloudAccountUi {
  private final Activity activity;
  private final Runnable changed;
  private final Handler handler = new Handler(Looper.getMainLooper());
  private AlertDialog owned;
  private LoginPage loginPage;
  private boolean busy;
  CloudAccountUi(Activity activity, Runnable changed) { this.activity = activity; this.changed = changed; }
  interface Work { void run() throws Exception; }
  private boolean live() { return !activity.isFinishing() && !activity.isDestroyed(); }
  private int dp(int n) { return Math.round(n * activity.getResources().getDisplayMetrics().density); }
  private LinearLayout form() {
    LinearLayout box = new LinearLayout(activity); box.setOrientation(1); box.setPadding(dp(20),dp(8),dp(20),dp(8)); return box;
  }
  private TextView text(String value) { TextView t = new TextView(activity); t.setText(value); t.setTextSize(14); t.setPadding(0,dp(8),0,dp(8)); return t; }
  private Button button(String value, Runnable click) { Button b = new Button(activity); b.setText(value); b.setAllCaps(false); b.setOnClickListener(v -> click.run()); return b; }
  private void show(AlertDialog dialog) { if (owned != null) owned.dismiss(); owned = dialog; dialog.show(); }
  void dismissProtected() { if (owned != null) owned.dismiss(); }
  void close() { if (owned != null) owned.dismiss(); if (loginPage != null) loginPage.dismiss(); handler.removeCallbacksAndMessages(null); }
  private void error(Exception e) { if (live()) new AlertDialog.Builder(activity).setTitle("操作未完成")
      .setMessage(e instanceof CloudApi.Failure ? e.getMessage() : e.getMessage() == null ? "网络或存储不可用，请重试" : e.getMessage())
      .setPositiveButton("知道了", null).show(); }
  private void task(String title, Work work, Runnable done) {
    if (busy) return; busy = true;
    ProgressDialog progress = new ProgressDialog(activity); progress.setMessage(title); progress.setCancelable(false); progress.show();
    new Thread(() -> {
      Exception failure = null; try { work.run(); } catch (Exception e) { failure = e; }
      final Exception result = failure;
      activity.runOnUiThread(() -> { busy = false; if (live()) { progress.dismiss(); if (result != null) error(result); else { changed.run(); if (done != null) done.run(); } } });
    }, "yanxu-cloud").start();
  }
  private CloudSession require() throws Exception {
    CloudSession session = CloudSession.current(activity);
    if (session == null || !session.valid()) throw new CloudApi.Failure(401, "请先登录");
    return session;
  }
  private void ensure(CloudSession expected) throws Exception {
    if (!CloudSession.same(activity, expected)) throw new IOException("账号或服务已切换，请重新操作");
  }
  void login() { login(null); }
  void login(Runnable onReady) {
    if (owned != null) owned.dismiss();
    if (loginPage != null) loginPage.dismiss();
    final LoginPage[] page = new LoginPage[1];
    page[0] = new LoginPage(activity, (name, secret) -> {
      String server = LocalStore.server(activity);
      new Thread(() -> {
        CloudSession next = null; Exception failure = null;
        try {
          JSONObject reply = CloudApi.request(server, null, "POST", "/api/auth/login", new JSONObject().put("username",name).put("password",secret).toString().getBytes(StandardCharsets.UTF_8), "application/json");
          Object expires = reply.get("expiresAt"); long expiry;
          if (expires instanceof Number) { expiry = ((Number)expires).longValue(); if (expiry < 100000000000L) expiry *= 1000; }
          else expiry = Instant.parse(expires.toString()).toEpochMilli();
          next = new CloudSession(server,reply.getString("accessToken"),reply.getJSONObject("account"),expiry);
        } catch (Exception e) { failure = e; }
        CloudSession authenticated = next; Exception result = failure;
        activity.runOnUiThread(() -> {
          if (!live() || loginPage != page[0] || !page[0].isShowing()) { revokeUnused(authenticated); return; }
          if (result != null) { page[0].failed(result.getMessage() == null ? "登录未完成，请重试" : result.getMessage()); return; }
          try {
            if (!CloudSession.normalize(LocalStore.server(activity)).equals(authenticated.server)) throw new IOException("服务已切换，请重新登录");
            CloudSession.save(activity,authenticated);
            page[0].dismiss(); changed.run(); LocalStore.enqueue(activity);
            sync(onReady);
          } catch (Exception e) { revokeUnused(authenticated); page[0].failed(e.getMessage()); }
        });
      }, "yanxu-login").start();
    });
    loginPage = page[0]; loginPage.show();
  }
  private void revokeUnused(CloudSession session) {
    if (session == null) return;
    new Thread(() -> { try { CloudApi.request(session,"POST","/api/auth/logout",new JSONObject()); } catch (Exception ignored) {} }, "yanxu-cancelled-login").start();
  }
  void account() {
    CloudSession session = CloudSession.current(activity); if (session == null || !session.valid()) { login(); return; }
    LinearLayout box = form(); box.addView(text(session.account.optString("displayName",session.account.optString("username"))));
    box.addView(button("同步人员和声纹状态", this::sync));
    box.addView(button("迁移旧版本机声音", this::migrateLegacy));
    box.addView(button("重新登录", this::login));
    box.addView(button("退出登录", () -> {
      if (RecordingService.active || VoiceEnrollmentDialog.busy) { error(new IOException("请先结束录音或声音录入")); return; }
      final boolean[] revoked = {true};
      task("正在退出", () -> {
        try { CloudApi.request(session,"POST","/api/auth/logout",new JSONObject()); }
        catch (CloudApi.Failure failure) { revoked[0] = failure.status == 401; }
        catch (IOException unavailable) { revoked[0] = false; }
        ensure(session); CloudSession.clear(activity);
      }, () -> { if (owned != null) owned.dismiss();
        Toast.makeText(activity,revoked[0] ? "已退出登录" : "本机已退出，服务会话将在到期后失效",Toast.LENGTH_LONG).show(); });
    }));
    show(new AlertDialog.Builder(activity).setTitle("账号与云端资料").setView(box).setPositiveButton("完成",null).create());
  }
  void switchServer(String server) {
    CloudSession prior = CloudSession.current(activity);
    final boolean[] revoked = {true};
    task("正在切换服务", () -> {
      if (prior != null && prior.valid()) {
        try { CloudApi.request(prior,"POST","/api/auth/logout",new JSONObject()); }
        catch (CloudApi.Failure failure) { revoked[0] = failure.status == 401; }
        catch (IOException unavailable) { revoked[0] = false; }
      }
      // Freeze any pre-identity pending uploads before changing the mutable default endpoint.
      for (File dir : LocalStore.all(activity)) {
        JSONObject recording = LocalStore.read(dir);
        if (!recording.has("cloudIdentity") && !recording.has("uploadServer")) {
          recording.put("uploadServer",LocalStore.server(activity)); LocalStore.save(dir,recording);
        }
      }
      CloudSession.clear(activity);
      if (!activity.getSharedPreferences("settings",0).edit().putString("server",server).commit())
        throw new IOException("服务地址未能保存");
      LocalStore.enqueue(activity);
    }, () -> { if (owned != null) owned.dismiss();
      if (!revoked[0]) Toast.makeText(activity,"服务已切换，原服务会话将在到期后失效",Toast.LENGTH_LONG).show(); });
  }
  void sync() { sync(null); }
  private void sync(Runnable onReady) {
    task("正在同步", () -> {
      CloudSession session = require(); JSONObject me = CloudApi.request(session,"GET","/api/auth/me",null);
      ensure(session); CloudSession refreshed = new CloudSession(session.server,session.token,me,session.expiresAt);
      CloudSession.save(activity,refreshed);
      JSONObject directory = CloudApi.request(refreshed,"GET","/api/people",null);
      JSONObject profiles = CloudApi.request(refreshed,"GET","/api/voice-profiles",null);
      ensure(refreshed);
      new PeopleStore(activity,refreshed.scope()).syncCloud(directory.getJSONArray("items"),profiles.getJSONArray("items"));
    }, onReady);
  }
  void addPerson() {
    try {
      CloudSession session = require();
      if (!session.allows("record")) throw new CloudApi.Failure(403,"当前账号不能新增参会者");
      LinearLayout box = form();
      EditText name = new EditText(activity); name.setSingleLine(true); name.setHint("姓名"); name.setContentDescription("参会者姓名");
      EditText detail = new EditText(activity); detail.setSingleLine(true); detail.setHint("部门／备注（选填）"); detail.setContentDescription("参会者备注");
      name.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(80)});
      detail.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(120)});
      box.addView(name);box.addView(detail);
      AlertDialog dialog = new AlertDialog.Builder(activity).setTitle("添加参会者").setView(box).setNegativeButton("取消",null).setPositiveButton("添加",null).create();
      dialog.show();dialog.getButton(-1).setOnClickListener(v -> {
        String personName=name.getText().toString().trim(); if(personName.isEmpty()){name.setError("请填写姓名");return;}
        task("正在添加", () -> {
          ensure(session); CloudApi.request(session,"POST","/api/people",new JSONObject().put("name",personName).put("detail",detail.getText().toString().trim()));
        }, () -> {dialog.dismiss();sync();});
      });
    } catch(Exception e) {error(e);}
  }
  void voice(PeopleStore store, String localId, Runnable record) {
    try {
      CloudSession session = require(); PeopleStore.Person person = store.get(localId);
      if (person == null) throw new IOException("人员已变化，请刷新");
      LinearLayout box = form(); box.addView(text(person.name + " · " + voiceLabel(person.cloudStatus)));
      box.addView(button(person.hasVoice() ? "重新录制声音" : "录制声音", () -> { owned.dismiss(); record.run(); }));
      if (person.cloudPersonId.isEmpty()) box.addView(button("关联云端人员", () -> bind(store,localId)));
      else if (person.hasVoice()) box.addView(button("确认并上传此声音", () -> consent(store,localId)));
      if (!person.cloudPersonId.isEmpty()) box.addView(button("刷新云端状态", this::sync));
      if (!person.cloudPersonId.isEmpty() && !"none".equals(person.cloudStatus))
        box.addView(button("撤回云端声纹", () -> new AlertDialog.Builder(activity).setTitle("撤回声纹？")
            .setMessage("后续识别将不再使用此档案，本机声音仍保留。")
            .setNegativeButton("取消",null).setPositiveButton("撤回",(d,w) -> task("正在撤回", () -> {
              ensure(session); CloudApi.request(session,"POST","/api/people/"+CloudApi.id(person.cloudPersonId)+"/voice-profile/revoke",new JSONObject());
              ensure(session); store.cloudStatus(localId,"revoked");
            },null)).show()));
      show(new AlertDialog.Builder(activity).setTitle("声音档案").setView(box).setPositiveButton("完成",null).create());
    } catch (Exception e) { error(e); }
  }
  void voices(PeopleStore store, java.util.function.Consumer<String> record) {
    try {
      CloudSession session = require();
      List<PeopleStore.Person> people = store.all();
      LinearLayout box = form();
      if (people.isEmpty()) box.addView(text("还没有人员"));
      ScrollView scroll = new ScrollView(activity); scroll.addView(box);
      AlertDialog list = new AlertDialog.Builder(activity).setTitle("声音档案").setView(scroll).setPositiveButton("完成",null).create();
      for (PeopleStore.Person person : people) {
        if (!session.allows("record") && !session.allows("voices")
            && !person.cloudPersonId.equals(session.account.optString("personId"))) continue;
        // The directory API returns the current member only when they lack directory permissions.
        box.addView(button(person.name + " · " + voiceLabel(person.cloudStatus), () -> {
          if (!CloudSession.same(activity,session)) { list.dismiss(); login(() -> changed.run()); return; }
          list.dismiss(); voice(store,person.id,() -> record.accept(person.id));
        }));
      }
      if (session.allows("record")) box.addView(button("＋ 添加人员", () -> { list.dismiss(); addPerson(); }));
      box.addView(button("刷新", () -> { list.dismiss(); sync(() -> voices(new PeopleStore(activity,session.scope()),record)); }));
      show(list);
    } catch (Exception e) { error(e); }
  }
  static String voiceLabel(String status) {
    return switch(status) { case "ready", "available" -> "云端声纹可用"; case "pending", "uploaded", "processing", "queued" -> "云端生成中";
      case "failed", "rejected", "needs_recording" -> "云端需重录"; case "revoked" -> "云端已撤回"; default -> "云端未登记"; };
  }
  void bind(PeopleStore store, String localId) {
    try {
      CloudSession session = require(); PeopleStore.Person source = store.get(localId);
      List<PeopleStore.Person> candidates = new ArrayList<>();
      for (PeopleStore.Person p : store.all()) if (!p.cloudPersonId.isEmpty()) candidates.add(p);
      ArrayList<String> labels = new ArrayList<>(); for (PeopleStore.Person p : candidates) labels.add(p.name+" · "+p.department);
      if (session.allows("record")) labels.add("新建云端人员："+source.name);
      if (labels.isEmpty()) throw new IOException("暂无可关联人员，请联系管理员添加后同步");
      new AlertDialog.Builder(activity).setTitle("请选择同一位本人")
          .setItems(labels.toArray(new String[0]),(d,which) -> {
            if (which == candidates.size()) new AlertDialog.Builder(activity).setTitle("新建云端人员？").setMessage(source.name+" · "+source.department)
                .setNegativeButton("取消",null).setPositiveButton("创建",(x,w) -> task("正在创建", () -> {
                  ensure(session); JSONObject reply = CloudApi.request(session,"POST","/api/people",new JSONObject().put("name",source.name).put("detail",source.department));
                  JSONObject person = reply.optJSONObject("person"); if (person == null) person = reply;
                  ensure(session); store.bindCloud(localId,person.getString("id"));
                }, () -> { if (source.hasVoice()) consent(store,localId); })).show();
            else {
              PeopleStore.Person target = candidates.get(which);
              new AlertDialog.Builder(activity).setTitle("确认对应人员")
                  .setMessage(source.name+" 的本机样本对应云端 "+target.name+"（"+target.department+"）？")
                  .setNegativeButton("取消",null).setPositiveButton("确认",(x,w) -> task("正在关联", () -> {
                    ensure(session); if (source.hasVoice()) store.importVoice(store,localId,target.id);
                    store.setSelected(localId,false);
                  }, () -> { if (source.hasVoice()) consent(store,target.id); })).show();
            }
          }).show();
    } catch (Exception e) { error(e); }
  }
  void consent(PeopleStore store, String localId) {
    try {
      CloudSession session = require(); PeopleStore.Person person = store.get(localId);
      if (person.cloudPersonId.isEmpty()) { bind(store,localId); return; }
      if (!person.hasVoice()) throw new IOException("请先录制并试听声音");
      if (person.voiceSeconds < 3 || person.voiceSeconds > 120)
        throw new IOException("云端登记需要3至120秒的声音，请重新录制；本机原样本仍保留");
      LinearLayout box = form(); box.addView(text("姓名："+person.name));
      CheckBox name = new CheckBox(activity); name.setText("本人确认姓名正确，样本是我的声音");
      CheckBox agree = new CheckBox(activity); agree.setText("同意将声音保存到云端，用于会议发言识别");
      box.addView(name); box.addView(agree);
      AlertDialog dialog = new AlertDialog.Builder(activity).setTitle("云端声音登记").setView(box).setNegativeButton("取消",null).setPositiveButton("确认上传",null).create();
      dialog.show(); dialog.getButton(-1).setEnabled(false);
      android.widget.CompoundButton.OnCheckedChangeListener update = (b,c) -> dialog.getButton(-1).setEnabled(name.isChecked()&&agree.isChecked());
      name.setOnCheckedChangeListener(update); agree.setOnCheckedChangeListener(update);
      dialog.getButton(-1).setOnClickListener(v -> {
        if (!name.isChecked() || !agree.isChecked()) return;
        dialog.dismiss(); final String[] enrollment = {null};
        task("正在上传私有声音", () -> {
          ensure(session); File file = store.voiceFile(localId); if (file == null) throw new IOException("声音样本不可用");
          byte[] data; try (InputStream in = new FileInputStream(file)) { data = LocalStore.bytes(in); }
          MessageDigest digest = MessageDigest.getInstance("SHA-256"); StringBuilder sha = new StringBuilder();
          for (byte b : digest.digest(data)) sha.append(String.format("%02x",b&255));
          JSONObject pending = CloudApi.request(session,"POST","/api/people/"+CloudApi.id(person.cloudPersonId)+"/voice-enrollments",
              new JSONObject().put("clientId",store.enrollmentClient(localId,sha.toString())).put("sha256",sha.toString()).put("totalBytes",data.length)
                  .put("nameConfirmed",true).put("voiceConfirmed",true).put("cloudConsent",true).put("confirmedName",person.name));
          String id = CloudApi.id(pending.getString("id")); enrollment[0] = id; ensure(session);
          if ("uploading".equals(pending.optString("status")))
            CloudApi.request(session.server,session.token,"PUT","/api/voice-enrollments/"+id+"/audio",data,"audio/wav");
          ensure(session); JSONObject complete = CloudApi.request(session,"POST","/api/voice-enrollments/"+id+"/complete",new JSONObject());
          ensure(session); store.cloudStatus(localId,complete.optString("status","processing"));
        }, () -> { if (owned != null) owned.dismiss(); poll(session,store,localId,enrollment[0],0); });
      });
    } catch (Exception e) { error(e); }
  }
  private void poll(CloudSession session, PeopleStore store, String localId, String id, int attempt) {
    if (id == null || attempt >= 20 || !live() || !CloudSession.same(activity,session)) return;
    handler.postDelayed(() -> new Thread(() -> {
      try {
        ensure(session); JSONObject status = CloudApi.request(session,"GET","/api/voice-enrollments/"+CloudApi.id(id),null);
        ensure(session); String value = status.optString("status","processing"); store.cloudStatus(localId,value);
        activity.runOnUiThread(() -> { if (live() && CloudSession.same(activity,session)) {
          changed.run(); if (Arrays.asList("pending","processing","queued","uploaded").contains(value)) poll(session,store,localId,id,attempt+1);
        }});
      } catch (Exception ignored) { /* Keep durable sample; explicit status refresh can resume after network/login recovery. */ }
    },"yanxu-voice-status").start(),3000);
  }
  private void migrateLegacy() {
    try {
      CloudSession session = require();
      String owner = activity.getSharedPreferences("legacy-people-owner",0).getString("scope","");
      if (!owner.isEmpty() && !owner.equals(session.scope())) throw new IOException("旧版样本已归属于其他账号，请登录原账号");
      PeopleStore legacy = new PeopleStore(activity); List<PeopleStore.Person> entries = legacy.all();
      if (entries.isEmpty()) throw new IOException("没有旧版本机人员");
      String[] labels = new String[entries.size()]; for (int i=0;i<entries.size();i++) labels[i]=entries.get(i).name+" · "+entries.get(i).department;
      new AlertDialog.Builder(activity).setTitle("选择旧版本人样本").setItems(labels,(d,index) -> {
        try {
          ensure(session); PeopleStore scoped = new PeopleStore(activity,session.scope());
          List<PeopleStore.Person> targets = new ArrayList<>(); for (PeopleStore.Person p : scoped.all()) if (!p.cloudPersonId.isEmpty()) targets.add(p);
          if (targets.isEmpty()) throw new IOException("请先同步云端人员目录");
          String[] targetLabels = new String[targets.size()]; for(int i=0;i<targets.size();i++) targetLabels[i]=targets.get(i).name+" · "+targets.get(i).department;
          new AlertDialog.Builder(activity).setTitle("明确选择对应的云端人员").setItems(targetLabels,(x,target) -> {
            PeopleStore.Person from=entries.get(index), to=targets.get(target);
            new AlertDialog.Builder(activity).setTitle("确认样本对应本人")
                .setMessage(from.name+" 的旧版声音将关联到 "+to.name+"（"+to.department+"）。原件保留，上传前另行确认云端保存。")
                .setNegativeButton("取消",null).setPositiveButton("确认关联",(a,b) -> task("正在保存对应关系", () -> {
                  ensure(session);
                  if (!activity.getSharedPreferences("legacy-people-owner",0).edit().putString("scope",session.scope()).commit()) throw new IOException("未能保存归属");
                  scoped.importVoice(legacy,from.id,to.id);
                },()->consent(scoped,to.id))).show();
          }).show();
        } catch(Exception e) { error(e); }
      }).show();
    } catch(Exception e) { error(e); }
  }
}
