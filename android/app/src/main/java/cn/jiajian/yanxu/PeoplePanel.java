package cn.jiajian.yanxu;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.text.Editable;
import android.text.InputFilter;
import android.text.TextUtils;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/** Device-local participant selection. This view never opens the microphone. */
public final class PeoplePanel {
  public interface Listener {
    void onEnroll(String personId);

    void onSelectionChanged();

    default boolean onAddRequested() {
      return false;
    }

    default boolean canAddPeople() {
      return true;
    }

    default boolean canSelectPeople() {
      return true;
    }
  }

  private static final int GREEN = AppUi.GREEN;
  private static final int INK = AppUi.INK;
  private static final int MUTED = AppUi.MUTED;
  private static final int LINE = AppUi.LINE;
  private static final int PALE = AppUi.PALE;
  private static final int BG = AppUi.BG;
  private final Activity activity;
  private final PeopleStore store;
  private final Listener listener;
  private LinearLayout home;
  private AppPage picker;
  private AlertDialog addDialog, feedback;
  private LinearLayout pickerResults;
  private ScrollView pickerScroll;
  private Spinner departmentPicker;
  private TextView pickerCount, pickerNotice;
  private Button pickerAll, pickerAdd;
  private String query = "", department = "";
  private final List<String> departmentValues = new ArrayList<>();
  private boolean updatingDepartments;
  private int pickerGridColumns;

  public PeoplePanel(Activity activity, PeopleStore store, Listener listener) {
    this.activity = activity;
    this.store = store;
    this.listener = listener;
  }

  /** Safe to call after a parent render; an open picker retains its filters and scroll. */
  public View build() {
    home = column();
    home.setPadding(0, dp(8), 0, dp(8));
    refreshHome();
    refreshPicker();
    return home;
  }

  /**
   * Refresh saved voices or recording locks without replacing the Activity or closing the picker.
   */
  public void refresh() {
    refreshHome();
    refreshPicker();
  }

  private static final class Snapshot {
    final List<PeopleStore.Person> people;
    final Set<String> selected = new HashSet<>();

    Snapshot(List<PeopleStore.Person> people, List<PeopleStore.Person> selectedPeople) {
      this.people = new ArrayList<>(people);
      for (PeopleStore.Person person : selectedPeople) selected.add(person.id);
    }
  }

  private Snapshot snapshot() throws Exception {
    return new Snapshot(store.all(), store.selected());
  }

  private void refreshHome() {
    if (home == null) return;
    home.removeAllViews();
    try {
      Snapshot data = snapshot();
      LinearLayout heading = row();
      TextView title =
          text(
              "参会者" + (data.selected.isEmpty() ? "" : " · " + data.selected.size() + " 人"),
              16,
              INK);
      title.setTypeface(null, Typeface.BOLD);
      heading.addView(title, new LinearLayout.LayoutParams(0, -2, 1));
      Button more = AppUi.quiet(activity, "更多人员", this::showPicker);
      heading.addView(more, new LinearLayout.LayoutParams(-2, dp(44)));
      home.addView(heading);
      if (RecordingService.active) home.addView(text("录音结束后可修改参会者和声音", 12, MUTED));
      if (data.people.isEmpty()) {
        TextView empty = text("还没有人员", 14, MUTED);
        empty.setPadding(dp(4), dp(14), 0, dp(10));
        home.addView(empty);
        Button add = button("＋ 添加人员", false, this::showAdd);
        enable(add, !RecordingService.active && listener.canAddPeople());
        home.addView(add, new LinearLayout.LayoutParams(-1, dp(48)));
        return;
      }
      List<PeopleStore.Person> ordered = new ArrayList<>(data.people);
      // Keep this meeting's attendees visible before filling remaining slots with directory entries.
      ordered.sort(java.util.Comparator.comparing(p -> !data.selected.contains(p.id)));
      int limit = activity.getResources().getConfiguration().screenWidthDp >= 600 ? 8 : 3;
      List<PeopleStore.Person> visible = new ArrayList<>(ordered.subList(0, Math.min(limit, ordered.size())));
      Button all =
          button(bulkLabel(visible, data.selected, false), false, () -> toggleAll(visible));
      enable(all, !RecordingService.active && listener.canSelectPeople());
      all.setBackgroundColor(Color.TRANSPARENT);
      all.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
      home.addView(all, new LinearLayout.LayoutParams(-1, dp(44)));
      int width = home.getWidth();
      if (width == 0) width = activity.getResources().getDisplayMetrics().widthPixels - dp(40);
      addCards(home, visible, data.selected, Math.max(2, Math.min(4, width / dp(112))));
    } catch (Exception error) {
      home.addView(text("人员未能读取，请重试", 14, INK));
      home.addView(button("重新读取", false, this::refreshHome));
    }
  }

  public void showPicker() {
    if (picker != null && picker.isShowing()) {
      refreshPicker();
      return;
    }
    picker = new AppPage(activity, "选择参会者", false);
    LinearLayout body = picker.body;
    EditText search = field("搜索姓名或部门", 80);
    search.setText(query);
    search.setContentDescription("搜索姓名或部门");
    body.addView(search, new LinearLayout.LayoutParams(-1, dp(48)));
    departmentPicker = new Spinner(activity);
    departmentValues.clear();
    departmentPicker.setContentDescription("部门筛选");
    LinearLayout.LayoutParams filterLayout = new LinearLayout.LayoutParams(-1, dp(48));
    filterLayout.topMargin = dp(8);
    body.addView(departmentPicker, filterLayout);
    pickerNotice = text("录音结束后可修改参会者和声音", 12, MUTED);
    body.addView(pickerNotice);
    pickerCount = text("", 12, MUTED);
    body.addView(pickerCount);
    pickerAll =
        button(
            "全选筛选结果",
            false,
            () -> {
              try {
                toggleAll(filtered(snapshot().people));
              } catch (Exception error) {
                showError("人员未能读取，请重试", error);
              }
            });
    pickerAll.setBackgroundColor(Color.TRANSPARENT);
    pickerAll.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
    body.addView(pickerAll, new LinearLayout.LayoutParams(-1, dp(44)));
    pickerScroll = new ScrollView(activity);
    pickerScroll.setFillViewport(false);
    pickerResults = column();
    pickerGridColumns = 0;
    pickerScroll.addView(pickerResults, new FrameLayout.LayoutParams(-1, -2));
    LinearLayout.LayoutParams scrollLayout = new LinearLayout.LayoutParams(-1, 0, 1);
    scrollLayout.topMargin = dp(8);
    body.addView(pickerScroll, scrollLayout);
    pickerAdd = button("＋ 添加人员", false, this::showAdd);
    picker.footer.addView(pickerAdd, new LinearLayout.LayoutParams(0, -2, 1));
    picker.action(-1, "完成", true, () -> picker.dismiss());
    picker.setOnDismissListener(
        dialog -> {
          picker = null;
          pickerResults = null;
          pickerScroll = null;
          departmentPicker = null;
        });
    picker.show();
    // Mutating children from onLayoutChange can leave the replacement rows unmeasured.
    // Reflow after this layout, and only if the available width changes the column count.
    LinearLayout results = pickerResults;
    results.addOnLayoutChangeListener(
        (v, l, t, r, b, oldL, oldT, oldR, oldB) -> {
          if (r > l && pickerColumns(r - l) != pickerGridColumns) {
            results.post(
                () -> {
                  if (pickerResults == results
                      && results.getWidth() > 0
                      && pickerColumns(results.getWidth()) != pickerGridColumns) refreshPicker();
                });
          }
        });
    search.addTextChangedListener(
        new TextWatcher() {
          @Override
          public void beforeTextChanged(CharSequence s, int start, int count, int after) {}

          @Override
          public void onTextChanged(CharSequence s, int start, int before, int count) {
            query = s.toString();
            if (pickerScroll != null) pickerScroll.scrollTo(0, 0);
            refreshPicker();
          }

          @Override
          public void afterTextChanged(Editable s) {}
        });
    departmentPicker.setOnItemSelectedListener(
        new AdapterView.OnItemSelectedListener() {
          @Override
          public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
            if (updatingDepartments || position >= departmentValues.size()) return;
            String next = departmentValues.get(position);
            if (next.equals(department)) return;
            department = next;
            if (pickerScroll != null) pickerScroll.scrollTo(0, 0);
            refreshPicker();
          }

          @Override
          public void onNothingSelected(AdapterView<?> parent) {}
        });
    refreshPicker();
  }

  private void refreshPicker() {
    if (picker == null || !picker.isShowing() || pickerResults == null) return;
    int scrollY = pickerScroll.getScrollY();
    try {
      Snapshot data = snapshot();
      updateDepartments(data.people);
      List<PeopleStore.Person> visible = filtered(data.people);
      int selectedHere = countSelected(visible, data.selected);
      pickerCount.setText(
          visible.size() + " 人 · 当前已选 " + selectedHere + " · 本场共 " + data.selected.size() + " 人");
      pickerNotice.setVisibility(RecordingService.active ? View.VISIBLE : View.GONE);
      pickerAll.setText(bulkLabel(visible, data.selected, true));
      enable(
          pickerAll, !RecordingService.active && listener.canSelectPeople() && !visible.isEmpty());
      enable(pickerAdd, !RecordingService.active && listener.canAddPeople());
      int width = pickerResults.getWidth();
      if (width == 0)
        width = Math.min(activity.getResources().getDisplayMetrics().widthPixels - dp(56), dp(628));
      pickerGridColumns = pickerColumns(width);
      pickerResults.removeAllViews();
      if (visible.isEmpty()) {
        TextView empty = text(data.people.isEmpty() ? "还没有人员，先添加一位" : "没有匹配的人员", 14, MUTED);
        empty.setGravity(Gravity.CENTER);
        empty.setPadding(dp(12), dp(28), dp(12), dp(28));
        pickerResults.addView(empty);
      } else {
        addCards(pickerResults, visible, data.selected, pickerGridColumns);
      }
      pickerScroll.post(
          () -> {
            if (pickerScroll != null) pickerScroll.scrollTo(0, scrollY);
          });
    } catch (Exception error) {
      pickerResults.removeAllViews();
      pickerResults.addView(text("人员未能读取，请重试", 14, INK));
      pickerResults.addView(button("重新读取", false, this::refreshPicker));
      enable(pickerAll, false);
      enable(pickerAdd, false);
    }
  }

  private int pickerColumns(int width) {
    return Math.max(2, Math.min(4, width / dp(112)));
  }

  private void addCards(
      LinearLayout destination,
      List<PeopleStore.Person> people,
      Set<String> selected,
      int columns) {
    for (int start = 0; start < people.size(); start += columns) {
      LinearLayout cards = row();
      cards.setGravity(Gravity.TOP);
      for (int offset = 0; offset < columns; offset++) {
        int index = start + offset;
        View card =
            index < people.size()
                ? personCard(people.get(index), selected.contains(people.get(index).id))
                : new View(activity);
        LinearLayout.LayoutParams item = new LinearLayout.LayoutParams(0, -2, 1);
        item.setMargins(dp(3), dp(4), dp(3), dp(8));
        cards.addView(card, item);
      }
      destination.addView(cards, new LinearLayout.LayoutParams(-1, -2));
    }
  }

  private void updateDepartments(List<PeopleStore.Person> people) {
    if (departmentPicker == null) return;
    LinkedHashSet<String> values = new LinkedHashSet<>();
    values.add("");
    for (PeopleStore.Person person : people) {
      if (person.department != null && !person.department.trim().isEmpty())
        values.add(person.department);
    }
    List<String> next = new ArrayList<>(values);
    if (next.equals(departmentValues)) return;
    updatingDepartments = true;
    departmentValues.clear();
    departmentValues.addAll(next);
    if (!departmentValues.contains(department)) department = "";
    List<String> labels = new ArrayList<>(next);
    labels.set(0, "全部部门／备注");
    ArrayAdapter<String> adapter =
        new ArrayAdapter<>(activity, android.R.layout.simple_spinner_item, labels);
    adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
    departmentPicker.setAdapter(adapter);
    departmentPicker.setSelection(departmentValues.indexOf(department), false);
    updatingDepartments = false;
  }

  private List<PeopleStore.Person> filtered(List<PeopleStore.Person> people) {
    String needle = query.trim().toLowerCase(Locale.ROOT);
    List<PeopleStore.Person> result = new ArrayList<>();
    for (PeopleStore.Person person : people) {
      String detail = person.department == null ? "" : person.department;
      if (!department.isEmpty() && !department.equals(detail)) continue;
      if (!needle.isEmpty()
          && !(person.name + " " + detail).toLowerCase(Locale.ROOT).contains(needle)) continue;
      result.add(person);
    }
    return result;
  }

  private LinearLayout personCard(PeopleStore.Person person, boolean selected) {
    LinearLayout card = column();
    card.setPadding(dp(8), dp(8), dp(8), 0);
    card.setBackground(shape(selected ? PALE : Color.WHITE, 16));
    LinearLayout choice = column();
    choice.setGravity(Gravity.CENTER);
    choice.setPadding(dp(4), dp(4), dp(4), 0);
    choice.setBackground(AppUi.ripple(activity, Color.TRANSPARENT, 12, false));
    choice.setSelected(selected);
    choice.setFocusable(true);
    choice.setContentDescription(
        person.name + (selected ? "，已选，点击取消" : "，未选，点击选择") + (person.guest ? "，本场来宾" : ""));
    FrameLayout portrait = new FrameLayout(activity);
    TextView avatar = text(initial(person.name), 20, selected ? Color.WHITE : GREEN);
    avatar.setPadding(0, 0, 0, 0);
    avatar.setGravity(Gravity.CENTER);
    avatar.setBackground(AppUi.shape(activity, selected ? GREEN : PALE, 26, false));
    FrameLayout.LayoutParams circle = new FrameLayout.LayoutParams(dp(40), dp(40), Gravity.CENTER);
    portrait.addView(avatar, circle);
    if (selected) {
      TextView tick = text("✓", 13, GREEN);
      tick.setPadding(0, 0, 0, 0);
      tick.setGravity(Gravity.CENTER);
      tick.setBackground(shape(Color.WHITE, 10));
      portrait.addView(
          tick, new FrameLayout.LayoutParams(dp(20), dp(20), Gravity.RIGHT | Gravity.BOTTOM));
    }
    choice.addView(portrait, new LinearLayout.LayoutParams(dp(54), dp(44)));
    TextView name = text(person.name, 13, INK);
    name.setGravity(Gravity.CENTER);
    name.setMaxLines(2);
    name.setMinLines(2);
    name.setPadding(0, dp(4), 0, 0);
    name.setEllipsize(TextUtils.TruncateAt.END);
    choice.addView(name, new LinearLayout.LayoutParams(-1, -2));
    choice.setOnClickListener(v -> toggle(person.id));
    enable(choice, !RecordingService.active && listener.canSelectPeople());
    card.addView(choice, new LinearLayout.LayoutParams(-1, -2));
    String info = person.guest ? "本场来宾" : person.department;
    if (info == null || info.isEmpty()) info = "";
    TextView detail = text(info, 11, MUTED);
    detail.setSingleLine(true);
    detail.setEllipsize(TextUtils.TruncateAt.END);
    detail.setGravity(Gravity.CENTER);
    card.addView(detail, new LinearLayout.LayoutParams(-1, -2));
    TextView voice =
        text(
            person.cloudPersonId.isEmpty()
                ? (person.hasVoice() ? "已存本机" : "未录声音")
                : CloudAccountUi.voiceLabel(person.cloudStatus)
                    .replace("云端声纹可用", "声纹可用")
                    .replace("云端未登记", "待录声音")
                    .replace("云端", ""),
            12,
            MUTED);
    voice.setGravity(Gravity.CENTER);
    voice.setSingleLine(true);
    voice.setEllipsize(TextUtils.TruncateAt.END);
    card.addView(voice, new LinearLayout.LayoutParams(-1, -2));
    Button enroll =
        button(
            RecordingService.active ? "会后录制" : (person.hasVoice() ? "重新录制" : "录制声音"),
            false,
            () -> {
              if (!canEdit()) return;
              listener.onEnroll(person.id);
            });
    enroll.setTextSize(13);
    enroll.setBackgroundColor(Color.TRANSPARENT);
    enroll.setPadding(dp(3), 0, dp(3), 0);
    enroll.setContentDescription(person.name + "，" + (person.hasVoice() ? "重新录制声音" : "录制声音"));
    enable(enroll, !RecordingService.active);
    card.addView(enroll, new LinearLayout.LayoutParams(-1, dp(44)));
    return card;
  }

  private void toggle(String id) {
    if (!canEdit() || !listener.canSelectPeople()) return;
    try {
      store.setSelected(id, !store.isSelected(id));
    } catch (Exception error) {
      showError("选择未能保存，请重试", error);
      return;
    }
    changed();
  }

  private void toggleAll(List<PeopleStore.Person> visible) {
    if (!canEdit() || !listener.canSelectPeople() || visible.isEmpty()) return;
    try {
      Snapshot current = snapshot();
      boolean select = countSelected(visible, current.selected) < visible.size();
      List<String> ids = new ArrayList<>();
      for (PeopleStore.Person person : visible) ids.add(person.id);
      store.setSelected(ids, select);
    } catch (Exception error) {
      showError("选择未能保存，请重试", error);
      return;
    }
    changed();
  }

  private String bulkLabel(
      List<PeopleStore.Person> people, Set<String> selected, boolean filtered) {
    int count = countSelected(people, selected);
    String scope = filtered ? "筛选结果" : "当前人员";
    if (!people.isEmpty() && count == people.size())
      return "✓ 取消全选" + scope + "（" + people.size() + "）";
    if (count > 0) return "－ 全选" + scope + "（" + count + "/" + people.size() + "）";
    return "全选" + scope + "（" + people.size() + "）";
  }

  private int countSelected(List<PeopleStore.Person> people, Set<String> selected) {
    int count = 0;
    for (PeopleStore.Person person : people) if (selected.contains(person.id)) count++;
    return count;
  }

  private void changed() {
    refreshHome();
    refreshPicker();
    listener.onSelectionChanged();
  }

  private boolean canEdit() {
    if (!RecordingService.active) return true;
    showError("录音结束后可修改参会者和声音", null);
    refreshHome();
    refreshPicker();
    return false;
  }

  private void showAdd() {
    if (!canEdit()) return;
    if (!listener.canAddPeople() || listener.onAddRequested()) return;
    if (addDialog != null && addDialog.isShowing()) return;
    LinearLayout form = column();
    form.setPadding(dp(20), dp(8), dp(20), dp(8));
    form.addView(text("姓名", 13, INK));
    EditText name = field("请输入真实姓名", 40);
    form.addView(name, new LinearLayout.LayoutParams(-1, dp(48)));
    form.addView(text("部门／备注（选填）", 13, INK));
    EditText detail = field("例如采购部、外部顾问", 80);
    form.addView(detail, new LinearLayout.LayoutParams(-1, dp(48)));
    RadioGroup types = new RadioGroup(activity);
    types.setOrientation(RadioGroup.VERTICAL);
    RadioButton member = new RadioButton(activity);
    member.setId(View.generateViewId());
    member.setText("本机成员 · 以后可复用");
    member.setMinHeight(dp(48));
    member.setTextColor(INK);
    types.addView(member);
    RadioButton guest = new RadioButton(activity);
    guest.setId(View.generateViewId());
    guest.setText("本场来宾");
    guest.setMinHeight(dp(48));
    guest.setTextColor(INK);
    types.addView(guest);
    types.check(member.getId());
    form.addView(types);
    TextView issue = text("", 13, Color.rgb(167, 70, 44));
    issue.setVisibility(View.GONE);
    form.addView(issue);
    ScrollView scroll = new ScrollView(activity);
    scroll.addView(form);
    addDialog =
        new AlertDialog.Builder(activity)
            .setTitle("添加人员")
            .setView(scroll)
            .setNegativeButton("取消", null)
            .setPositiveButton("添加", null)
            .create();
    addDialog.setOnDismissListener(dialog -> addDialog = null);
    addDialog.show();
    addDialog
        .getButton(AlertDialog.BUTTON_POSITIVE)
        .setOnClickListener(
            v -> {
              if (!canEdit()) return;
              String personName = name.getText().toString().trim();
              if (personName.isEmpty()) {
                name.setError("请填写姓名");
                name.requestFocus();
                return;
              }
              try {
                store.add(
                    personName,
                    detail.getText().toString().trim(),
                    types.getCheckedRadioButtonId() == guest.getId());
              } catch (Exception error) {
                issue.setText("人员未能保存，请重试" + detailMessage(error));
                issue.setVisibility(View.VISIBLE);
                return;
              }
              addDialog.dismiss();
              changed();
            });
  }

  /** Close only dialogs owned by this panel when the Activity is destroyed. */
  public void dismiss() {
    if (addDialog != null) addDialog.dismiss();
    if (picker != null) picker.dismiss();
    if (feedback != null) feedback.dismiss();
  }

  private void showError(String message, Exception error) {
    if (activity.isFinishing() || activity.isDestroyed()) return;
    if (feedback != null) feedback.dismiss();
    feedback =
        new AlertDialog.Builder(activity)
            .setTitle(message)
            .setMessage(error == null ? null : detailMessage(error).trim())
            .setPositiveButton("知道了", null)
            .create();
    feedback.setOnDismissListener(dialog -> feedback = null);
    feedback.show();
  }

  private String detailMessage(Exception error) {
    String value = error.getMessage();
    if (value == null || value.trim().isEmpty()) return "";
    return "\n" + value.substring(0, Math.min(value.length(), 160));
  }

  private String initial(String name) {
    if (name == null || name.isEmpty()) return "人";
    return name.substring(0, name.offsetByCodePoints(0, 1)).toUpperCase(Locale.ROOT);
  }

  private int dp(int value) {
    return Math.round(value * activity.getResources().getDisplayMetrics().density);
  }

  private LinearLayout column() {
    LinearLayout value = new LinearLayout(activity);
    value.setOrientation(LinearLayout.VERTICAL);
    return value;
  }

  private LinearLayout row() {
    LinearLayout value = new LinearLayout(activity);
    value.setOrientation(LinearLayout.HORIZONTAL);
    value.setGravity(Gravity.CENTER_VERTICAL);
    return value;
  }

  private TextView text(String value, int size, int color) {
    TextView result = new TextView(activity);
    result.setText(value);
    result.setTextSize(size);
    result.setTextColor(color);
    result.setPadding(0, dp(4), 0, dp(4));
    return result;
  }

  private Button button(String label, boolean primary, Runnable action) {
    Button result = AppUi.button(activity, label, primary, action);
    result.setTextSize(13);
    return result;
  }

  private EditText field(String hint, int maxLength) {
    EditText result = new EditText(activity);
    result.setSingleLine(true);
    result.setTextSize(15);
    result.setTextColor(INK);
    result.setHintTextColor(MUTED);
    result.setHint(hint);
    result.setBackground(shape(BG, 9));
    result.setPadding(dp(12), 0, dp(12), 0);
    result.setFilters(new InputFilter[] {new InputFilter.LengthFilter(maxLength)});
    return result;
  }

  private GradientDrawable shape(int color, int radius) {
    GradientDrawable result = new GradientDrawable();
    result.setColor(color);
    result.setCornerRadius(dp(radius));
    result.setStroke(dp(1), LINE);
    return result;
  }

  private RippleDrawable ripple(int color, int radius) {
    return new RippleDrawable(
        ColorStateList.valueOf(Color.argb(28, 70, 107, 79)), shape(color, radius), null);
  }

  private void enable(View view, boolean enabled) {
    view.setEnabled(enabled);
    view.setAlpha(enabled ? 1f : 0.5f);
  }
}
