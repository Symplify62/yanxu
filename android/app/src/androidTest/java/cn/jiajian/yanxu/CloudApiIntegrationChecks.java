package cn.jiajian.yanxu;

import android.content.Context;
import android.os.Bundle;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.UUID;
import org.json.*;

/** Explicitly pointed at a disposable local backend, never the saved production endpoint. */
final class CloudApiIntegrationChecks {
  static String run(Context context, Bundle args) throws Exception {
    String endpoint=args.getString("apiServer","");
    if (!endpoint.matches("http://(10\\.0\\.2\\.2|127\\.0\\.0\\.1):[0-9]+"))
      throw new IllegalArgumentException("Integration tests require an explicit emulator-local server");
    String username=args.getString("apiUser",""),password=args.getString("apiPassword","");
    if(username.isEmpty()||password.isEmpty())throw new IllegalArgumentException("Disposable API account required");
    CloudIdentityChecks.Sandbox box=new CloudIdentityChecks.Sandbox(context);
    CloudSession session=null;String personId=null;
    try {
      box.getSharedPreferences("settings",0).edit().putString("server",endpoint).commit();
      JSONObject login=CloudApi.request(endpoint,null,"POST","/api/auth/login",new JSONObject().put("username",username).put("password",password).toString().getBytes(StandardCharsets.UTF_8),"application/json");
      session=new CloudSession(endpoint,login.getString("accessToken"),login.getJSONObject("account"),(long)(login.getDouble("expiresAt")*1000));
      CloudSession.save(box,session);
      CloudIdentityChecks.check(CloudApi.request(session,"GET","/api/auth/me",null).getString("id").equals(session.accountId),"Native login must resolve the same real account");
      JSONObject role = CloudApi.request(session,"POST","/api/admin/roles",new JSONObject().put("name","安卓只录音-"+UUID.randomUUID().toString().substring(0,8))
          .put("description","隔离record权限验证").put("permissions",new JSONArray().put("record")));
      String testUsername="rec-"+UUID.randomUUID().toString().substring(0,8),testPassword=UUID.randomUUID().toString();
      CloudApi.request(session,"POST","/api/admin/users",new JSONObject().put("name","安卓组织者测试").put("username",testUsername).put("password",testPassword).put("roleId",role.getString("id")));
      JSONObject organizerLogin=CloudApi.request(endpoint,null,"POST","/api/auth/login",new JSONObject().put("username",testUsername).put("password",testPassword).toString().getBytes(StandardCharsets.UTF_8),"application/json");
      CloudSession organizer=new CloudSession(endpoint,organizerLogin.getString("accessToken"),organizerLogin.getJSONObject("account"),(long)(organizerLogin.getDouble("expiresAt")*1000));
      JSONObject guest=CloudApi.request(organizer,"POST","/api/people",new JSONObject().put("name","安卓无账号来宾").put("detail","record-only路径"));
      CloudIdentityChecks.check(!guest.getString("id").isEmpty() && (guest.isNull("accountId") || guest.optString("accountId").isEmpty()),"record-only user may create a person without login account");
      boolean adminDenied=false;try{CloudApi.request(organizer,"GET","/api/admin/users",null);}catch(CloudApi.Failure e){adminDenied=e.status==403;}
      CloudIdentityChecks.check(adminDenied,"Adding a participant must not grant user administration");
      CloudApi.request(organizer,"POST","/api/auth/logout",new JSONObject());
      String name="安卓接入测试-"+UUID.randomUUID().toString().substring(0,8);
      JSONObject created=CloudApi.request(session,"POST","/api/admin/users",new JSONObject().put("name",name).put("detail","隔离联调样本"));
      personId=created.getString("id");
      PeopleStore store=new PeopleStore(box,session.scope());
      store.syncCloud(CloudApi.request(session,"GET","/api/people",null).getJSONArray("items"),CloudApi.request(session,"GET","/api/voice-profiles",null).getJSONArray("items"));
      PeopleStore.Person selected=null;for(PeopleStore.Person p:store.all())if(p.cloudPersonId.equals(personId))selected=p;
      CloudIdentityChecks.check(selected!=null,"Created real member must appear in native directory");
      File staged=store.stagingFile();CloudIdentityChecks.writeWav(staged,4);store.saveVoice(selected.id,selected.name,staged,4,true);
      byte[] audio;try(InputStream in=new FileInputStream(store.voiceFile(selected.id))){audio=LocalStore.bytes(in);}
      StringBuilder sha=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(audio))sha.append(String.format("%02x",b&255));
      JSONObject enrollment=new JSONObject().put("clientId",UUID.randomUUID().toString()).put("sha256",sha.toString()).put("totalBytes",audio.length)
          .put("nameConfirmed",true).put("voiceConfirmed",true).put("confirmedName",name).put("cloudConsent",false);
      boolean denied=false;try{CloudApi.request(session,"POST","/api/people/"+personId+"/voice-enrollments",enrollment);}catch(CloudApi.Failure e){denied=e.status==422;}
      CloudIdentityChecks.check(denied,"Local-only consent must never authorize private cloud upload");
      enrollment.put("cloudConsent",true);
      JSONObject pending=CloudApi.request(session,"POST","/api/people/"+personId+"/voice-enrollments",enrollment);
      String voiceId=pending.getString("id");
      CloudApi.request(endpoint,session.token,"PUT","/api/voice-enrollments/"+voiceId+"/audio",audio,"audio/wav");
      JSONObject completed=CloudApi.request(session,"POST","/api/voice-enrollments/"+voiceId+"/complete",new JSONObject());
      CloudIdentityChecks.check(!"ready".equals(completed.optString("status")),"Upload alone must not claim recognized voice profile");
      CloudApi.request(session,"GET","/api/voice-enrollments/"+voiceId,null);
      store.setSelected(selected.id,true);
      JSONObject identity=RecordingIdentity.capture(box,store.snapshot());
      JSONObject meeting=new JSONObject().put("client_id",UUID.randomUUID().toString()).put("title","Android isolated integration")
          .put("total_bytes",audio.length).put("sha256",sha.toString()).put("extension","wav").put("interrupted",false)
          .put("participants",identity.getJSONArray("participants")).put("rosterClientId",identity.getString("rosterClientId"));
      JSONObject upload=CloudApi.request(session,"POST","/api/managed/recordings",meeting);
      String recordingId=upload.getString("id"),uploadToken=upload.getString("uploadToken");
      part(endpoint,"PUT","/api/uploads/"+recordingId+"/parts/0",audio,uploadToken);
      part(endpoint,"POST","/api/uploads/"+recordingId+"/complete",new byte[0],uploadToken);
      CloudApi.request(session,"GET","/api/managed/recordings/"+recordingId,null);
      boolean privateDenied=false;try{CloudApi.request(endpoint,null,"GET","/api/managed/recordings/"+recordingId,null,"application/json");}catch(CloudApi.Failure e){privateDenied=e.status==401;}
      CloudIdentityChecks.check(privateDenied,"Private named recording must require bearer");
      CloudApi.request(session,"POST","/api/people/"+personId+"/voice-profile/revoke",new JSONObject());
      CloudApi.request(session,"POST","/api/auth/logout",new JSONObject());
      boolean logoutDenied=false;try{CloudApi.request(session,"GET","/api/auth/me",null);}catch(CloudApi.Failure e){logoutDenied=e.status==401;}
      CloudIdentityChecks.check(logoutDenied,"Server must revoke logout token");
      return "PASS: real login/me, record-only participant creation without admin, directory, cloud-consent rejection, private WAV upload/complete, managed roster/chunks, anonymous denial, revoke/logout; recording="+recordingId;
    } finally { box.cleanup(); }
  }
  private static void part(String endpoint,String method,String path,byte[] bytes,String token)throws Exception{
    HttpURLConnection connection=(HttpURLConnection)new URL(endpoint+path).openConnection();connection.setInstanceFollowRedirects(false);
    connection.setConnectTimeout(5000);connection.setReadTimeout(30000);connection.setRequestMethod(method);connection.setRequestProperty("X-Upload-Token",token);
    try{connection.setDoOutput(true);connection.setFixedLengthStreamingMode(bytes.length);try(OutputStream out=connection.getOutputStream()){out.write(bytes);}
      if(connection.getResponseCode()/100!=2)throw new IOException("Upload contract failed: "+connection.getResponseCode());
      try(InputStream in=connection.getInputStream()){LocalStore.bytes(in);}
    }finally{connection.disconnect();}
  }
}
