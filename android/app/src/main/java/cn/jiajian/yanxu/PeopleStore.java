package cn.jiajian.yanxu;

import android.content.Context;
import android.util.AtomicFile;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.text.Normalizer;
import java.util.*;
import org.json.*;

/** Private, on-device people and voice samples. These files never enter the upload queue. */
public final class PeopleStore {
  private static final Object LOCK = new Object();
  private static final Set<String> ACTIVE_STAGING = new HashSet<>();
  private static final long MAX_SAMPLE_BYTES = 16L * 1024 * 1024;
  private static final int MAX_PEOPLE = 10000;
  private final File root;
  private final File voices;
  private final File staging;
  private final AtomicFile metadata;

  public static final class Person {
    public final String id, name, department, cloudPersonId, cloudStatus;
    public final boolean guest;
    public final String voiceFilename;
    public final long voiceRecordedAt;
    public final double voiceSeconds;

    private Person(
        String id,
        String name,
        String department,
        boolean guest,
        String voiceFilename,
        long voiceRecordedAt,
        double voiceSeconds, String cloudPersonId, String cloudStatus) {
      this.id = id;
      this.name = name;
      this.department = department;
      this.guest = guest;
      this.voiceFilename = voiceFilename;
      this.voiceRecordedAt = voiceRecordedAt;
      this.voiceSeconds = voiceSeconds;
      this.cloudPersonId = cloudPersonId;
      this.cloudStatus = cloudStatus;
    }

    public boolean hasVoice() {
      return !voiceFilename.isEmpty() && voiceRecordedAt > 0 && voiceSeconds > 0;
    }
  }

  public PeopleStore(Context context) { this(context, ""); }

  public PeopleStore(Context context, String scope) {
    if (!scope.isEmpty() && !scope.matches("[a-f0-9]{64}")) throw new IllegalArgumentException("人员目录范围无效");
    File privateFiles;
    try {
      privateFiles = Objects.requireNonNull(context).getFilesDir().getCanonicalFile();
    } catch (IOException unavailable) {
      throw new IllegalStateException("无法访问应用私有目录", unavailable);
    }
    root = new File(privateFiles, scope.isEmpty() ? "people" : "people-accounts/" + scope);
    voices = new File(root, "voices");
    staging = new File(root, "staging");
    metadata = new AtomicFile(new File(root, "people.json"));
  }

  public List<Person> all() throws Exception {
    synchronized (LOCK) {
      return people(readState(), false);
    }
  }

  public List<Person> selected() throws Exception {
    synchronized (LOCK) {
      return people(readState(), true);
    }
  }

  public boolean isSelected(String id) throws Exception {
    synchronized (LOCK) {
      return selection(readState()).contains(id);
    }
  }

  public void setSelected(String id, boolean selected) throws Exception {
    setSelected(Collections.singletonList(id), selected);
  }

  /** Changes only the supplied IDs, preserving selection outside the current UI filter. */
  public void setSelected(Collection<String> ids, boolean selected) throws Exception {
    synchronized (LOCK) {
      if (ids == null) throw new IllegalArgumentException("请选择人员");
      JSONObject state = readState();
      Set<String> chosen = selection(state);
      Set<String> before = new LinkedHashSet<>(chosen);
      for (String id : ids) {
        requirePerson(state, id);
        if (selected) chosen.add(id);
        else chosen.remove(id);
      }
      if (!before.equals(chosen)) {
        state.put("selected", new JSONArray(chosen));
        writeState(state);
      }
    }
  }

  public Person add(String name, String department, boolean guest) throws Exception {
    synchronized (LOCK) {
      name = text(name, "姓名", 80, true);
      department = text(department, "部门或备注", 120, false);
      JSONObject state = readState();
      JSONArray entries = state.getJSONArray("people");
      if (entries.length() >= MAX_PEOPLE) throw new IllegalStateException("本机人员数量已达上限");
      ensureUnique(state, name, department, null);
      JSONObject entry =
          new JSONObject()
              .put("id", UUID.randomUUID().toString())
              .put("name", name)
              .put("department", department)
              .put("guest", guest)
              .put("voiceFilename", "")
              .put("voiceRecordedAt", 0)
              .put("voiceSeconds", 0);
      entries.put(entry);
      writeState(state);
      return person(entry);
    }
  }

  public Person get(String id) throws Exception {
    synchronized (LOCK) {
      JSONObject entry = find(readState(), id);
      return entry == null ? null : person(entry);
    }
  }

  /** A detached local meeting roster: no sample paths, audio, or claim of voice recognition. */
  public JSONObject snapshot() throws Exception {
    synchronized (LOCK) {
      JSONArray participants = new JSONArray();
      for (Person p : people(readState(), true)) {
        participants.put(
            new JSONObject()
                .put("personId", p.cloudPersonId.isEmpty() ? p.id : p.cloudPersonId)
                .put("cloudPersonId", p.cloudPersonId)
                .put("name", p.name)
                .put("department", p.department)
                .put("guest", p.guest)
                .put("voiceRecordedAt", p.voiceRecordedAt)
                .put("hasLocalSample", p.hasVoice()));
      }
      return new JSONObject()
          .put("version", 1)
          .put("capturedAt", System.currentTimeMillis())
          .put("participants", participants);
    }
  }

  /** Commits metadata only after a separate, complete sample has been copied and synced. */
  public void saveVoice(
      String id, String confirmedName, File stagedWav, double seconds, boolean consent)
      throws Exception {
    synchronized (LOCK) {
      JSONObject state = readState();
      JSONObject entry = requirePerson(state, id);
      String name = text(confirmedName, "姓名", 80, true);
      if (entry.optString("cloudPersonId").isEmpty()) ensureUnique(state, name, entry.getString("department"), id);
      else if (!name.equals(entry.getString("name"))) throw new IllegalArgumentException("请在云端人员管理中修改姓名，再刷新目录");
      if (!entry.getBoolean("guest") && !consent)
        throw new IllegalArgumentException("请本人确认同意在本机保存声音样本");
      if (!Double.isFinite(seconds) || seconds <= 0 || seconds > 300)
        throw new IllegalArgumentException("声音样本应大于0秒且不超过5分钟");
      File source = ownedFile(staging, stagedWav);
      validateWav(source, seconds);
      String oldFilename = entry.optString("voiceFilename", "");
      String filename = UUID.randomUUID() + ".wav";
      File destination = child(voices, filename);
      boolean committed = false;
      try {
        try (InputStream in = new FileInputStream(source);
            FileOutputStream out = new FileOutputStream(destination)) {
          byte[] buffer = new byte[8192];
          int count;
          long total = 0;
          while ((count = in.read(buffer)) != -1) {
            total += count;
            if (total > MAX_SAMPLE_BYTES) throw new IOException("声音样本过大");
            out.write(buffer, 0, count);
          }
          out.getFD().sync();
        }
        validateWav(destination, seconds);
        entry
            .put("name", name)
            .put("voiceFilename", filename)
            .put("voiceRecordedAt", System.currentTimeMillis())
            .put("voiceSeconds", seconds)
            .put("voiceConsent", consent);
        writeState(state);
        committed = true;
      } finally {
        if (!committed) discardIfUnreferenced(destination);
      }
      // Deletion is after the commit. A failed cleanup is harmless and retried by recover().
      source.delete();
      ACTIVE_STAGING.remove(source.getCanonicalPath());
      if (!oldFilename.isEmpty()) child(voices, oldFilename).delete();
    }
  }

  public File voiceFile(String id) throws Exception {
    synchronized (LOCK) {
      JSONObject entry = requirePerson(readState(), id);
      String filename = entry.optString("voiceFilename", "");
      if (filename.isEmpty()) return null;
      File file = child(voices, filename);
      return file.isFile() && file.length() > 44 ? file : null;
    }
  }

  public void clearVoice(String id) throws Exception {
    synchronized (LOCK) {
      JSONObject state = readState();
      JSONObject entry = requirePerson(state, id);
      String filename = entry.optString("voiceFilename", "");
      if (filename.isEmpty()) return;
      entry
          .put("voiceFilename", "")
          .put("voiceRecordedAt", 0)
          .put("voiceSeconds", 0)
          .remove("voiceConsent");
      writeState(state);
      child(voices, filename).delete();
    }
  }

  public void nextMeeting() throws Exception {
    synchronized (LOCK) {
      JSONObject state = readState();
      JSONArray retained = new JSONArray();
      List<String> removeVoices = new ArrayList<>();
      JSONArray entries = state.getJSONArray("people");
      for (int i = 0; i < entries.length(); i++) {
        JSONObject entry = entries.getJSONObject(i);
        if (!entry.getBoolean("guest")) retained.put(entry);
        else if (!entry.optString("voiceFilename", "").isEmpty())
          removeVoices.add(entry.getString("voiceFilename"));
      }
      state.put("people", retained).put("selected", new JSONArray());
      writeState(state);
      for (String filename : removeVoices) child(voices, filename).delete();
    }
  }

  public File stagingFile() throws Exception {
    synchronized (LOCK) {
      prepareDirectories();
      File file = child(staging, UUID.randomUUID() + ".wav");
      if (!file.createNewFile()) throw new IOException("无法创建声音录制文件");
      ACTIVE_STAGING.add(file.getCanonicalPath());
      return file;
    }
  }

  /** Recover after process death without touching samples being recorded in this process. */
  public void recover() throws Exception {
    synchronized (LOCK) {
      JSONObject state = readState();
      Set<String> retained = new HashSet<>();
      JSONArray entries = state.getJSONArray("people");
      for (int i = 0; i < entries.length(); i++) {
        String filename = entries.getJSONObject(i).optString("voiceFilename", "");
        if (!filename.isEmpty()) retained.add(filename);
      }
      File[] pending = staging.listFiles();
      if (pending != null) {
        for (File file : pending) {
          if (isSampleName(file.getName()) && !ACTIVE_STAGING.contains(file.getCanonicalPath()))
            ownedFile(staging, file).delete();
        }
      }
      ACTIVE_STAGING.removeIf(path -> !new File(path).exists());
      File[] saved = voices.listFiles();
      if (saved != null) {
        for (File file : saved) {
          if (isSampleName(file.getName()) && !retained.contains(file.getName()))
            ownedFile(voices, file).delete();
        }
      }
    }
  }

  /** Directory is scoped by the caller's immutable server/account key. No name-based merges. */
  public void syncCloud(JSONArray directory, JSONArray profiles) throws Exception {
    synchronized (LOCK) {
      JSONObject state = readState(); JSONArray entries = state.getJSONArray("people");
      Map<String, JSONObject> byCloud = new HashMap<>();
      for (int i = 0; i < entries.length(); i++) {
        JSONObject entry = entries.getJSONObject(i);
        String cloudId = entry.optString("cloudPersonId");
        if (!cloudId.isEmpty()) { byCloud.put(cloudId, entry); entry.put("active", false); }
      }
      Map<String, String> statuses = new HashMap<>();
      for (int i = 0; i < profiles.length(); i++) {
        JSONObject profile = profiles.getJSONObject(i);
        statuses.put(profile.getString("personId"), profile.optString("status", "none"));
      }
      for (int i = 0; i < directory.length(); i++) {
        JSONObject remote = directory.getJSONObject(i); String cloudId = remote.getString("id");
        JSONObject entry = byCloud.get(cloudId);
        if (entry == null) {
          entry = new JSONObject().put("id", UUID.randomUUID().toString()).put("guest", false)
              .put("voiceFilename", "").put("voiceRecordedAt", 0).put("voiceSeconds", 0);
          entries.put(entry);
        }
        entry.put("cloudPersonId", cloudId).put("name", text(remote.getString("name"), "姓名", 80, true))
            .put("department", text(remote.isNull("departmentName") ? (remote.isNull("detail") ? "" : remote.optString("detail")) : remote.optString("departmentName"), "部门", 200, false))
            .put("active", remote.optBoolean("active", true)).put("cloudStatus", statuses.getOrDefault(cloudId, "none"));
      }
      Set<String> chosen = selection(state);
      for (int i = 0; i < entries.length(); i++) if (!entries.getJSONObject(i).optBoolean("active", true))
        chosen.remove(entries.getJSONObject(i).getString("id"));
      state.put("selected", new JSONArray(chosen)); writeState(state);
    }
  }

  public void bindCloud(String localId, String cloudId) throws Exception {
    synchronized (LOCK) {
      JSONObject state = readState();
      JSONArray entries = state.getJSONArray("people");
      for (int i = 0; i < entries.length(); i++) {
        JSONObject entry = entries.getJSONObject(i);
        if (cloudId.equals(entry.optString("cloudPersonId")) && !localId.equals(entry.getString("id")))
          throw new IllegalStateException("该云端人员已在目录中，请选择其头像录制，或使用迁移入口");
      }
      requirePerson(state, localId).put("cloudPersonId", CloudApi.id(cloudId)).put("cloudStatus", "none");
      writeState(state);
    }
  }

  public void cloudStatus(String id, String status) throws Exception {
    synchronized (LOCK) { JSONObject state = readState(); requirePerson(state, id).put("cloudStatus", status); writeState(state); }
  }

  public String enrollmentClient(String id, String sha) throws Exception {
    synchronized (LOCK) {
      JSONObject state = readState(), person = requirePerson(state,id);
      String client = person.optString("enrollmentClient");
      if (client.isEmpty() || !sha.equals(person.optString("enrollmentSha"))
          || Arrays.asList("failed","revoked","superseded","rejected").contains(person.optString("cloudStatus"))) {
        client = UUID.randomUUID().toString();
        person.put("enrollmentClient",client).put("enrollmentSha",sha);
        writeState(state);
      }
      return client;
    }
  }

  /** Explicitly copy a legacy sample to the selected cloud person; original remains untouched. */
  public void importVoice(PeopleStore source, String sourceId, String targetId) throws Exception {
    Person from = source.get(sourceId); File original = source.voiceFile(sourceId);
    if (from == null || original == null) throw new IOException("原本机样本不可用");
    Person target = get(targetId); if (target == null) throw new IOException("目标人员不可用");
    File stage = stagingFile();
    try {
      try (InputStream in = new FileInputStream(original); FileOutputStream out = new FileOutputStream(stage)) {
        byte[] b = new byte[8192]; int n; while ((n = in.read(b)) != -1) out.write(b, 0, n); out.getFD().sync();
      }
      saveVoice(targetId, target.name, stage, from.voiceSeconds, true);
    } finally { stage.delete(); }
  }

  private JSONObject readState() throws Exception {
    prepareDirectories();
    JSONObject state;
    try {
      byte[] bytes = metadata.readFully();
      if (bytes.length > 8 * 1024 * 1024) throw new IOException("本机人员数据过大");
      state = new JSONObject(new String(bytes, StandardCharsets.UTF_8));
    } catch (FileNotFoundException missing) {
      if (metadata.getBaseFile().exists() || new File(root, "people.json.bak").exists())
        throw missing;
      return new JSONObject()
          .put("version", 1)
          .put("people", new JSONArray())
          .put("selected", new JSONArray());
    }
    if (state.getInt("version") != 1) throw new IOException("本机人员数据版本不支持");
    JSONArray entries = state.getJSONArray("people");
    if (entries.length() > MAX_PEOPLE) throw new IOException("本机人员数量异常");
    Set<String> ids = new HashSet<>();
    for (int i = 0; i < entries.length(); i++) {
      Person p = person(entries.getJSONObject(i));
      if (!ids.add(p.id)) throw new IOException("本机人员编号重复");
    }
    for (String id : selection(state)) {
      if (!ids.contains(id)) throw new IOException("本场名单包含未知人员");
    }
    return state;
  }

  private void writeState(JSONObject state) throws Exception {
    byte[] expected = state.toString().getBytes(StandardCharsets.UTF_8);
    FileOutputStream out = null;
    try {
      out = metadata.startWrite();
      out.write(expected);
      out.getFD().sync();
      metadata.finishWrite(out);
      out = null;
      // AtomicFile reports rename errors through logging on some API levels; verify the commit.
      if (!Arrays.equals(expected, metadata.readFully())) throw new IOException("本机人员数据未能完整保存");
    } finally {
      if (out != null) metadata.failWrite(out);
    }
  }

  private void discardIfUnreferenced(File sample) {
    try {
      JSONArray entries = readState().getJSONArray("people");
      for (int i = 0; i < entries.length(); i++) {
        if (sample.getName().equals(entries.getJSONObject(i).optString("voiceFilename"))) return;
      }
      sample.delete();
    } catch (Exception uncertainCommit) {
      // Keep the file when commit verification is unavailable; recover() can safely retry later.
    }
  }

  private List<Person> people(JSONObject state, boolean selectedOnly) throws Exception {
    Set<String> chosen = selection(state);
    List<Person> result = new ArrayList<>();
    JSONArray entries = state.getJSONArray("people");
    for (int i = 0; i < entries.length(); i++) {
      Person p = person(entries.getJSONObject(i));
      if (entries.getJSONObject(i).optBoolean("active", true) && (!selectedOnly || chosen.contains(p.id))) result.add(p);
    }
    return Collections.unmodifiableList(result);
  }

  private Person person(JSONObject entry) throws Exception {
    String id = entry.getString("id");
    if (!isId(id)) throw new IOException("本机人员编号无效");
    String name = text(entry.getString("name"), "姓名", 80, true);
    String department = text(entry.getString("department"), "部门或备注", 200, false);
    boolean guest = entry.getBoolean("guest");
    String filename = entry.optString("voiceFilename", "");
    long recordedAt = entry.optLong("voiceRecordedAt", 0);
    double seconds = entry.optDouble("voiceSeconds", 0);
    if (!filename.isEmpty()) {
      File file = child(voices, filename);
      if (recordedAt <= 0 || !Double.isFinite(seconds) || seconds <= 0 || seconds > 300)
        throw new IOException("本机声音样本信息无效");
      if (!file.isFile() || file.length() <= 44) {
        filename = "";
        recordedAt = 0;
        seconds = 0;
      }
    }
    return new Person(id, name, department, guest, filename, recordedAt, seconds,
        entry.optString("cloudPersonId", ""), entry.optString("cloudStatus", "none"));
  }

  private static Set<String> selection(JSONObject state) throws JSONException {
    JSONArray array = state.getJSONArray("selected");
    Set<String> result = new LinkedHashSet<>();
    for (int i = 0; i < array.length(); i++) result.add(array.getString(i));
    return result;
  }

  private static JSONObject find(JSONObject state, String id) throws JSONException {
    JSONArray entries = state.getJSONArray("people");
    for (int i = 0; i < entries.length(); i++) {
      JSONObject entry = entries.getJSONObject(i);
      if (entry.getString("id").equals(id)) return entry;
    }
    return null;
  }

  private static JSONObject requirePerson(JSONObject state, String id) throws JSONException {
    JSONObject entry = find(state, id);
    if (entry == null) throw new IllegalArgumentException("未找到该人员，请刷新后重试");
    return entry;
  }

  private static void ensureUnique(
      JSONObject state, String name, String department, String exceptId) throws JSONException {
    JSONArray entries = state.getJSONArray("people");
    for (int i = 0; i < entries.length(); i++) {
      JSONObject entry = entries.getJSONObject(i);
      if (!entry.getString("id").equals(exceptId)
          && name.equalsIgnoreCase(entry.getString("name"))
          && department.equalsIgnoreCase(entry.getString("department")))
        throw new IllegalArgumentException("该姓名和部门的人员已存在，请选择已有人员");
    }
  }

  private static String text(String value, String label, int limit, boolean required) {
    String clean =
        Normalizer.normalize(value == null ? "" : value, Normalizer.Form.NFKC)
            .replaceAll("[\\p{Z}\\s]+", " ")
            .trim();
    if (required && clean.isEmpty()) throw new IllegalArgumentException("请填写" + label);
    if (clean.codePointCount(0, clean.length()) > limit)
      throw new IllegalArgumentException(label + "不能超过" + limit + "个字");
    for (int i = 0; i < clean.length(); i++) {
      if (Character.isISOControl(clean.charAt(i)))
        throw new IllegalArgumentException(label + "包含无效字符");
    }
    return clean;
  }

  private void prepareDirectories() throws IOException {
    for (File directory : Arrays.asList(root, voices, staging)) {
      if ((!directory.isDirectory() && !directory.mkdirs())
          || !directory.getAbsolutePath().equals(directory.getCanonicalPath()))
        throw new IOException("无法访问本机人员目录");
    }
  }

  private static boolean isId(String id) {
    if (id == null) return false;
    try {
      return UUID.fromString(id).toString().equals(id);
    } catch (IllegalArgumentException invalid) {
      return false;
    }
  }

  private static boolean isSampleName(String name) {
    return name != null && name.endsWith(".wav") && isId(name.substring(0, name.length() - 4));
  }

  private static File child(File directory, String name) throws IOException {
    if (!isSampleName(name)) throw new IOException("声音文件名无效");
    return ownedFile(directory, new File(directory, name));
  }

  private static File ownedFile(File directory, File file) throws IOException {
    if (file == null
        || !isSampleName(file.getName())
        || !directory.getCanonicalFile().equals(file.getCanonicalFile().getParentFile()))
      throw new IOException("声音文件不在本机专用目录");
    return file.getCanonicalFile();
  }

  private static void validateWav(File file, double seconds) throws IOException {
    if (!file.isFile() || file.length() <= 44 || file.length() > MAX_SAMPLE_BYTES)
      throw new IOException("声音文件为空或大小无效，请重新录制");
    try (RandomAccessFile in = new RandomAccessFile(file, "r")) {
      byte[] header = new byte[44];
      in.readFully(header);
      if (!"RIFF".equals(new String(header, 0, 4, StandardCharsets.US_ASCII))
          || !"WAVEfmt ".equals(new String(header, 8, 8, StandardCharsets.US_ASCII))
          || !"data".equals(new String(header, 36, 4, StandardCharsets.US_ASCII))
          || little(header, 16, 4) != 16
          || little(header, 20, 2) != 1
          || little(header, 22, 2) != 1
          || little(header, 24, 4) != 16000
          || little(header, 28, 4) != 32000
          || little(header, 32, 2) != 2
          || little(header, 34, 2) != 16
          || little(header, 4, 4) != file.length() - 8
          || little(header, 40, 4) != file.length() - 44
          || Math.abs(seconds - (file.length() - 44) / 32000.0) > 0.05)
        throw new IOException("声音文件未完整保存，请重新录制");
    }
  }

  private static long little(byte[] bytes, int start, int count) {
    long result = 0;
    for (int i = 0; i < count; i++) result |= (long) (bytes[start + i] & 255) << (8 * i);
    return result;
  }
}
