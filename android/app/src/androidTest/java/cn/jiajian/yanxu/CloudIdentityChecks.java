package cn.jiajian.yanxu;

import android.content.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
import org.json.*;

/** Owned temporary data only. Keystore, ownership and real HTTP transport checks on emulator. */
public final class CloudIdentityChecks {
  interface Action { void run() throws Exception; }
  static void check(boolean value,String why) { if (!value) throw new AssertionError(why); }
  static void fails(Action action,String why) throws Exception {
    try { action.run(); } catch(Exception expected) { return; } throw new AssertionError(why);
  }
  static final class Sandbox extends ContextWrapper {
    final File dir; final String prefix = "cloud-check-"+UUID.randomUUID();
    final Set<String> preferences = new HashSet<>();
    Sandbox(Context context) { super(context); dir = new File(context.getFilesDir(),prefix); dir.mkdirs(); }
    @Override public File getFilesDir() { return dir; }
    @Override public SharedPreferences getSharedPreferences(String name,int mode) {
      preferences.add(prefix+name); return super.getSharedPreferences(prefix+name,mode);
    }
    void cleanup() { remove(dir); for(String name:preferences) super.deleteSharedPreferences(name); }
    static void remove(File file) { if(file.isDirectory()) for(File child:Objects.requireNonNull(file.listFiles())) remove(child); file.delete(); }
  }
  static CloudSession session(String server,String id,String token) throws Exception {
    return new CloudSession(server,token,new JSONObject().put("id",id).put("username",id)
        .put("permissions",new JSONArray().put("record").put("users")),System.currentTimeMillis()+600000);
  }
  public static String run(Context context) throws Exception {
    Sandbox box = new Sandbox(context);
    try {
      String server = "http://127.0.0.1:19101";
      box.getSharedPreferences("settings",0).edit().putString("server",server).commit();
      CloudSession first = session(server,"ownerA","token-never-plaintext-A");
      CloudSession.save(box,first);
      check(CloudSession.current(box).accountId.equals("ownerA"),"Encrypted session must round trip");
      String sealed = box.getSharedPreferences("cloud-session",0).getString("sealed","");
      check(!sealed.contains(first.token) && !sealed.contains("ownerA"),"Token and identity must not be plaintext preferences");
      PeopleStore a = new PeopleStore(box,first.scope()); PeopleStore legacy = new PeopleStore(box);
      PeopleStore.Person old=legacy.add("旧版成员","",false);
      File sample = legacy.stagingFile(); writeWav(sample); legacy.saveVoice(old.id,old.name,sample,1,true);
      JSONArray directory = new JSONArray().put(new JSONObject().put("id","cloud-person-A").put("name","同名同事").put("departmentName",JSONObject.NULL).put("detail","研发").put("active",true));
      a.syncCloud(directory,new JSONArray()); check(a.all().size()==1,"Remote directory must load");
      check(a.all().get(0).department.equals("研发"),"Null department must use detail, never literal null");
      check(!a.all().get(0).hasVoice(),"Sync must not silently import legacy samples by name");
      String localId = a.all().get(0).id; a.setSelected(localId,true);
      JSONObject roster = a.snapshot(); JSONObject identity = RecordingIdentity.capture(box,roster);
      check(identity.getJSONArray("participants").getJSONObject(0).getString("personId").equals("cloud-person-A"),"Roster must freeze cloud IDs");
      check(!identity.toString().contains("token")&&!identity.toString().contains("voiceFilename"),"Meeting identity must exclude token and voice file");
      JSONObject metadata = new JSONObject().put("cloudIdentity",identity);
      CloudSession second=session(server,"ownerB","token-B"); CloudSession.save(box,second);
      check(new PeopleStore(box,second.scope()).all().isEmpty(),"Other account must not see directory or samples");
      fails(()->RecordingIdentity.requireOwner(box,metadata),"Other account must never upload original recording");
      check(!RecordingIdentity.visible(box,metadata),"Other account must not see private recording names");
      CloudSession.clear(box); check(CloudSession.current(box)==null,"Logout must erase active token");
      check(a.all().size()==1 && legacy.voiceFile(old.id).exists(),"Logout must preserve private files and recording data");
      CloudSession.save(box,first); box.getSharedPreferences("settings",0).edit().putString("server","http://127.0.0.1:19102").commit();
      check(CloudSession.current(box)==null,"Changing server must not reuse bearer or directory");
      box.getSharedPreferences("settings",0).edit().putString("server",server).commit();
      check(RecordingIdentity.requireOwner(box,metadata).accountId.equals("ownerA"),"Original owner can resume same recording");
      a.importVoice(legacy,old.id,localId);
      check(a.get(localId).hasVoice() && legacy.voiceFile(old.id).exists(),"Explicit import copies, does not delete original");
      check(!"ready".equals(a.get(localId).cloudStatus),"A saved local file must not claim usable cloud voiceprint");
      String c1=a.enrollmentClient(localId,"abc");check(c1.equals(a.enrollmentClient(localId,"abc")),"Retry must preserve enrollment id");
      a.cloudStatus(localId,"revoked"); check(!c1.equals(a.enrollmentClient(localId,"abc")),"New consent after revoke must start a new enrollment");
      a.syncCloud(new JSONArray(),new JSONArray()); check(a.all().isEmpty()&&a.selected().isEmpty(),"Removed remote people cannot remain selectable");
      check(a.voiceFile(localId)!=null,"Directory removal must not delete local sample");
      PeopleStore.Person unbound=a.add("未关联","",false);a.setSelected(unbound.id,true);
      fails(()->RecordingIdentity.capture(box,a.snapshot()),"Unbound local roster must not silently fall back to anonymous upload");
      check(RecordingIdentity.requireOwner(box,new JSONObject())==null,"Old anonymous metadata keeps legacy protocol");
      check(MainActivity.speakerNotice("waiting").equals("正在识别发言人"),"Waiting attribution needs truthful visible notice");
      check(MainActivity.speakerNotice("failed").contains("逐字稿已保留"),"Attribution failure must not hide transcript");
      check(MainActivity.speakerNotice("complete").isEmpty()&&MainActivity.speakerNotice("none").isEmpty(),"Complete/none must not add unnecessary explanation");
      transport();
      return "PASS: encrypted session, logout/server/account isolation, frozen owner/roster, explicit legacy copy, retry identity and HTTP redirect boundary";
    } finally { box.cleanup(); }
  }
  private static void transport() throws Exception {
    try(ServerSocket server=new ServerSocket(0,2,InetAddress.getByName("127.0.0.1"))) {
      AtomicReference<String> request=new AtomicReference<>(); AtomicReference<Throwable> error=new AtomicReference<>();
      Thread responder = new Thread(()->{
        try(Socket conn=server.accept()) {
          BufferedReader in=new BufferedReader(new InputStreamReader(conn.getInputStream(),StandardCharsets.UTF_8));
          StringBuilder headers=new StringBuilder();String line;while((line=in.readLine())!=null&&!line.isEmpty())headers.append(line).append('\n');
          request.set(headers.toString()); byte[] body="{\"items\":[]}".getBytes(StandardCharsets.UTF_8);
          conn.getOutputStream().write(("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "+body.length+"\r\nConnection: close\r\n\r\n").getBytes(StandardCharsets.UTF_8));
          conn.getOutputStream().write(body);
        } catch(Throwable e){error.set(e);}
      }); responder.start();
      CloudSession login=session("http://127.0.0.1:"+server.getLocalPort(),"transport","transport-secret");
      check(CloudApi.request(login,"GET","/api/people",null).getJSONArray("items").length()==0,"Native HTTP must decode real API response");
      responder.join(3000);if(error.get()!=null)throw new AssertionError(error.get());
      check(request.get().contains("Authorization: Bearer transport-secret"),"Protected request must use Authorization header");
    }
    try(ServerSocket redirect=new ServerSocket(0,1,InetAddress.getByName("127.0.0.1"));
        ServerSocket destination=new ServerSocket(0,1,InetAddress.getByName("127.0.0.1"))) {
      destination.setSoTimeout(300);
      Thread responder=new Thread(()->{try(Socket conn=redirect.accept()){
        BufferedReader in=new BufferedReader(new InputStreamReader(conn.getInputStream()));String line;while((line=in.readLine())!=null&&!line.isEmpty()){}
        conn.getOutputStream().write(("HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1:"+destination.getLocalPort()+"/leak\r\nContent-Length: 0\r\nConnection: close\r\n\r\n").getBytes(StandardCharsets.UTF_8));
      }catch(Exception ignored){}});responder.start();
      fails(()->CloudApi.request(session("http://127.0.0.1:"+redirect.getLocalPort(),"redirect","secret"),"GET","/api/people",null),"Redirect must be rejected");
      try(Socket leaked=destination.accept()){throw new AssertionError("Bearer request followed redirect");}catch(SocketTimeoutException expected){}
      responder.join(3000);
    }
  }
  static void writeWav(File file) throws Exception {
    writeWav(file,1);
  }
  static void writeWav(File file,int seconds) throws Exception {
    try(RandomAccessFile out=new RandomAccessFile(file,"rw")) { LocalStore.header(out,32000L*seconds);out.seek(44);
      for(int i=0;i<16000*seconds;i++)LocalStore.le16(out,(int)(Math.sin(i*0.18)*6000));out.getFD().sync(); }
  }
}
