package cn.jiajian.yanxu;

import android.content.Context;
import java.io.*;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
import org.json.*;

/** Exercises the real upload method using owned sandbox files and loopback HTTP only. */
public final class GuestRecordingApiChecks {
  private static void check(boolean value, String why) {
    if (!value) throw new AssertionError(why);
  }

  private static final class TestUploadJob extends UploadJob {
    TestUploadJob(Context context) { attachBaseContext(context); }
  }

  private static final class Request {
    final String method, path;
    final Map<String, String> headers = new HashMap<>();
    final byte[] body;
    Request(InputStream stream) throws Exception {
      String[] line = readLine(stream).split(" ");
      check(line.length == 3, "An HTTP request line is required");
      method = line[0]; path = line[1];
      String header;
      while (!(header = readLine(stream)).isEmpty()) {
        int colon = header.indexOf(':');
        check(colon > 0, "Malformed HTTP header");
        headers.put(header.substring(0, colon).toLowerCase(Locale.ROOT), header.substring(colon + 1).trim());
      }
      int size = Integer.parseInt(headers.getOrDefault("content-length", "0"));
      check(size >= 0 && size <= 1024 * 1024, "Unexpected test request body size");
      body = new byte[size]; new DataInputStream(stream).readFully(body);
    }
  }

  private static String readLine(InputStream stream) throws Exception {
    ByteArrayOutputStream bytes = new ByteArrayOutputStream();
    while (bytes.size() < 16384) {
      int value = stream.read();
      if (value < 0) throw new EOFException("Incomplete HTTP request");
      if (value == '\n') return bytes.toString("US-ASCII").replaceFirst("\\r$", "");
      bytes.write(value);
    }
    throw new IOException("HTTP header line too long");
  }

  private static void respond(Socket connection, String body) throws Exception {
    byte[] data = body.getBytes(StandardCharsets.UTF_8);
    connection.getOutputStream().write(("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
        + data.length + "\r\nConnection: close\r\n\r\n").getBytes(StandardCharsets.US_ASCII));
    connection.getOutputStream().write(data); connection.getOutputStream().flush();
  }

  private static void upload(Context context, File directory, JSONObject metadata) throws Exception {
    Method method = UploadJob.class.getDeclaredMethod("upload", File.class, JSONObject.class);
    method.setAccessible(true);
    try { method.invoke(new TestUploadJob(context), directory, metadata); }
    catch (InvocationTargetException wrapped) {
      Throwable failure = wrapped.getCause();
      if (failure instanceof Exception) throw (Exception) failure;
      throw new AssertionError(failure);
    }
  }

  public static String run(Context context) throws Exception {
    CloudIdentityChecks.Sandbox box = new CloudIdentityChecks.Sandbox(context);
    try (ServerSocket destination = new ServerSocket(0, 4, InetAddress.getByName("127.0.0.1"));
        ServerSocket laterServer = new ServerSocket(0, 1, InetAddress.getByName("127.0.0.1"))) {
      destination.setSoTimeout(5000); laterServer.setSoTimeout(300);
      String original = "http://127.0.0.1:" + destination.getLocalPort();
      String changed = "http://127.0.0.1:" + laterServer.getLocalPort();
      box.getSharedPreferences("settings", 0).edit().putString("server", original).commit();
      JSONObject metadata = RecordingIdentity.captureForRecording(box,
          new JSONObject().put("version", 1).put("participants", new JSONArray()));
      RecordingIdentity.validateStart(box, metadata);
      metadata.put("client_id", UUID.randomUUID().toString()).put("filename", "audio.wav")
          .put("title", "匿名上传验证").put("state", "saved").put("interrupted", false);
      File recording = new File(LocalStore.root(box), UUID.randomUUID().toString());
      check(recording.mkdirs(), "An isolated recording directory is required");
      File audio = new File(recording, "audio.wav"); CloudIdentityChecks.writeWav(audio);
      byte[] originalAudio;
      try (InputStream input = new FileInputStream(audio)) { originalAudio = LocalStore.bytes(input); }
      LocalStore.save(recording, metadata);
      // Login after recording: upload must still choose the anonymous endpoint without a bearer.
      CloudSession.save(box, CloudIdentityChecks.session(original, "later-owner-A", "guest-http-token-A"));
      List<Request> requests = Collections.synchronizedList(new ArrayList<>());
      AtomicReference<Throwable> responderFailure = new AtomicReference<>();
      Thread responder = new Thread(() -> {
        try {
          for (int i = 0; i < 4; i++) {
            try (Socket connection = destination.accept()) {
              connection.setSoTimeout(5000);
              requests.add(new Request(connection.getInputStream()));
              if (i == 0) {
                // Switch both account and server before chunks. Neither may adopt or redirect this file.
                box.getSharedPreferences("settings", 0).edit().putString("server", changed).commit();
                CloudSession.save(box, CloudIdentityChecks.session(changed, "later-owner-B", "guest-http-token-B"));
                respond(connection, "{\"id\":\"guest-upload\",\"uploadToken\":\"recording-only-token\",\"chunkSize\":65536}");
              } else if (i == 1) respond(connection, "{\"parts\":[]}");
              else if (i == 2) respond(connection, "{}");
              else respond(connection, "{\"duration\":1}");
            }
          }
        } catch (Throwable error) { responderFailure.set(error); }
      }, "guest-http-fixture");
      responder.setDaemon(true); responder.start();
      try { upload(box, recording, metadata); }
      finally { responder.join(5500); }
      check(!responder.isAlive(), "The complete upload exchange must finish");
      if (responderFailure.get() != null) throw new AssertionError(responderFailure.get());
      check(requests.size() == 4, "Create, status, audio part, and completion must all execute");
      String[] methods = {"POST", "GET", "PUT", "POST"};
      String[] paths = {"/api/recordings", "/api/uploads/guest-upload", "/api/uploads/guest-upload/parts/0",
          "/api/uploads/guest-upload/complete"};
      for (int i = 0; i < requests.size(); i++) {
        Request request = requests.get(i);
        check(request.method.equals(methods[i]) && request.path.equals(paths[i]), "Unexpected upload protocol step " + i);
        check(!request.headers.containsKey("authorization"), "Guest HTTP must never send a login bearer");
        if (i > 0) check("recording-only-token".equals(request.headers.get("x-upload-token")),
            "Chunk protocol must retain the original upload token");
      }
      JSONObject created = new JSONObject(new String(requests.get(0).body, StandardCharsets.UTF_8));
      Set<String> fields = new HashSet<>(); Iterator<String> keys = created.keys(); while (keys.hasNext()) fields.add(keys.next());
      check(fields.equals(new HashSet<>(Arrays.asList("client_id", "title", "total_bytes", "sha256", "extension", "interrupted"))),
          "Anonymous create must only contain legacy public recording fields");
      check(!created.toString().contains("later-owner") && !created.toString().contains("guest-http-token"),
          "No identity or bearer may leak into the create body");
      check(Arrays.equals(originalAudio, requests.get(2).body), "Every uploaded audio byte must match the saved guest recording");
      JSONObject saved = LocalStore.read(recording);
      check(saved.getString("state").equals("uploaded") && saved.getString("server_id").equals("guest-upload"),
          "Successful anonymous upload must persist normal uploaded state");
      check(saved.getString("uploadServer").equals(original), "Upload must retain the server captured before the account switch");
      check(!saved.has("cloudIdentity") && !saved.has("participantsSnapshot"), "Uploading cannot add private account data");
      check(RecordingIdentity.requireOwner(box, saved) == null, "Completed guest recording must remain guest after login changes");
      try (Socket unexpected = laterServer.accept()) { throw new AssertionError("Guest upload contacted the later server"); }
      catch (SocketTimeoutException expected) { /* No request was sent to the new account's server. */ }
      return "PASS: real anonymous create/status/part/complete HTTP, no bearer/roster leakage, byte-identical audio, "
          + "and frozen anonymous destination across login/account/server changes";
    } finally { box.cleanup(); }
  }
}
