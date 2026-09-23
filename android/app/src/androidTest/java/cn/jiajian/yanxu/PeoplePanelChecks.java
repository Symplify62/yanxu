package cn.jiajian.yanxu;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.Instrumentation;
import android.content.Context;
import android.content.ContextWrapper;
import android.graphics.Bitmap;
import android.graphics.Rect;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Spinner;
import android.widget.TextView;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.lang.reflect.Field;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/** Exercises measured, attached native views with an isolated directory and no microphone. */
public final class PeoplePanelChecks {
  private PeoplePanelChecks() {}

  /** Run off the main thread using a resumed test Activity; the caller owns Activity cleanup. */
  public static String run(Instrumentation instrumentation, Activity activity) throws Exception {
    check(!RecordingService.active, "meeting recorder must be idle");
    File isolated = new File(activity.getCacheDir(), "people-panel-check-" + UUID.randomUUID());
    check(isolated.mkdirs(), "create isolated people directory");
    Context context =
        new ContextWrapper(activity) {
          @Override
          public File getFilesDir() {
            return isolated;
          }
        };
    PeopleStore store = new PeopleStore(context);
    PeopleStore.Person alice = store.add("Alice", "研发", false);
    PeopleStore.Person bob = store.add("Bob", "产品", false);
    store.add("来宾", "合作方", true);
    store.setSelected(bob.id, true);
    AtomicReference<PeoplePanel> panel = new AtomicReference<>();
    AtomicReference<View> home = new AtomicReference<>();
    AtomicInteger selections = new AtomicInteger();
    AtomicInteger enrollments = new AtomicInteger();
    int passed = 0;
    try {
      onMain(
          instrumentation,
          () -> {
            PeoplePanel value =
                new PeoplePanel(
                    activity,
                    store,
                    new PeoplePanel.Listener() {
                      @Override
                      public void onEnroll(String id) {
                        check(alice.id.equals(id), "enrollment belongs to Alice");
                        enrollments.incrementAndGet();
                      }

                      @Override
                      public void onSelectionChanged() {
                        selections.incrementAndGet();
                      }
                    });
            panel.set(value);
            home.set(value.build());
            activity.setContentView(home.get());
            return null;
          });
      rendered(instrumentation, home.get());
      onMain(
          instrumentation,
          () -> {
            visible(home.get(), "Alice");
            return null;
          });
      screenshot(instrumentation, activity, "people-home-visible.png");
      passed++;

      onMain(
          instrumentation,
          () -> {
            panel.get().showPicker();
            return null;
          });
      rendered(instrumentation, decor(panel.get()));
      onMain(
          instrumentation,
          () -> {
            visible(decor(panel.get()), "Alice");
            visibleDescription(decor(panel.get()), "Alice，录制声音");
            check(findText(decor(panel.get()), "未录声音") == null,
                "person cards do not expose explanatory voice copy");
            return null;
          });
      screenshot(instrumentation, activity, "people-picker-visible.png");
      passed++;

      onMain(
          instrumentation,
          () -> {
            search(panel.get()).setText("Ali");
            return null;
          });
      rendered(instrumentation, decor(panel.get()));
      onMain(
          instrumentation,
          () -> {
            visible(decor(panel.get()), "Alice");
            check(findText(decor(panel.get()), "Bob") == null, "search removes Bob from results");
            visibleDescription(decor(panel.get()), "全选筛选结果，共1人");
            clickPrefix(decor(panel.get()), "全选");
            return null;
          });
      rendered(instrumentation, decor(panel.get()));
      check(
          store.isSelected(alice.id) && store.isSelected(bob.id),
          "filtered select preserves Bob outside search");
      onMain(
          instrumentation,
          () -> {
            visible(decor(panel.get()), "Alice");
            return null;
          });
      check(selections.get() == 1, "select emits exactly one callback");
      passed++;

      onMain(
          instrumentation,
          () -> {
            visibleDescription(decor(panel.get()), "取消全选筛选结果，共1人");
            clickPrefix(decor(panel.get()), "取消全选");
            return null;
          });
      rendered(instrumentation, decor(panel.get()));
      check(
          !store.isSelected(alice.id) && store.isSelected(bob.id),
          "filtered deselect preserves Bob");
      onMain(
          instrumentation,
          () -> {
            visible(decor(panel.get()), "Alice");
            View enroll = visibleDescription(decor(panel.get()), "Alice，录制声音");
            enroll.performClick();
            return null;
          });
      check(
          enrollments.get() == 1 && !store.isSelected(alice.id),
          "unselected person can enroll without selection");
      passed++;

      onMain(
          instrumentation,
          () -> {
            search(panel.get()).setText("");
            Spinner departments = field(panel.get(), "departmentPicker");
            int index = -1;
            for (int i = 0; i < departments.getCount(); i++) {
              if ("研发".equals(departments.getItemAtPosition(i))) index = i;
            }
            check(index >= 0, "department option exists");
            departments.setSelection(index);
            return null;
          });
      rendered(instrumentation, decor(panel.get()));
      onMain(
          instrumentation,
          () -> {
            visible(decor(panel.get()), "Alice");
            check(findText(decor(panel.get()), "Bob") == null, "department filter removes Bob");
            panel.get().refresh();
            return null;
          });
      rendered(instrumentation, decor(panel.get()));
      AppPage closingPicker =
          onMain(
              instrumentation,
              () -> {
                visible(decor(panel.get()), "Alice");
                Spinner departments = field(panel.get(), "departmentPicker");
                check(
                    "研发".equals(departments.getSelectedItem()),
                    "refresh preserves selected department");
                AppPage current = dialog(panel.get());
                current.getButton(AlertDialog.BUTTON_POSITIVE).performClick();
                return current;
              });
      // AlertDialog dispatches the button dismissal asynchronously; observe that boundary
      // before reopening, so this exercises a new picker rather than the closing window.
      instrumentation.waitForIdleSync();
      onMain(
          instrumentation,
          () -> {
            check(!closingPicker.isShowing(), "completed picker is dismissed before reopening");
            check(dialog(panel.get()) == null, "dismiss callback has cleared the old picker");
            return null;
          });
      onMain(
          instrumentation,
          () -> {
            panel.get().showPicker();
            check(dialog(panel.get()) != closingPicker, "reopening creates a new picker");
            return null;
          });
      rendered(instrumentation, decor(panel.get()));
      onMain(
          instrumentation,
          () -> {
            visible(decor(panel.get()), "Alice");
            Spinner departments = field(panel.get(), "departmentPicker");
            check(
                "研发".equals(departments.getSelectedItem()),
                "reopen retains a populated department picker");
            return null;
          });
      passed++;
      return "PeoplePanel: "
          + passed
          + " native layout/interaction checks passed; private fixtures, no microphone";
    } finally {
      if (panel.get() != null)
        onMain(
            instrumentation,
            () -> {
              panel.get().dismiss();
              return null;
            });
      deleteTree(isolated);
    }
  }

  private static View visible(View root, String label) {
    View found = findText(root, label);
    assertVisible(found, label);
    return found;
  }

  private static View visibleDescription(View root, String label) {
    View found = findDescription(root, label);
    assertVisible(found, label);
    return found;
  }

  private static void assertVisible(View view, String label) {
    check(view != null, "view exists: " + label);
    Rect bounds = new Rect();
    check(
        view.isAttachedToWindow()
            && view.isShown()
            && view.getGlobalVisibleRect(bounds)
            && bounds.width() > 8
            && bounds.height() > 8,
        "nonempty visible bounds for "
            + label
            + ": "
            + bounds
            + ", measured="
            + view.getMeasuredWidth()
            + "x"
            + view.getMeasuredHeight());
  }

  private static View findText(View view, String label) {
    if (view instanceof TextView && label.contentEquals(((TextView) view).getText())) return view;
    if (view instanceof ViewGroup) {
      ViewGroup group = (ViewGroup) view;
      for (int i = 0; i < group.getChildCount(); i++) {
        View found = findText(group.getChildAt(i), label);
        if (found != null) return found;
      }
    }
    return null;
  }

  private static View findDescription(View view, String label) {
    if (label.contentEquals(
        view.getContentDescription() == null ? "" : view.getContentDescription())) return view;
    if (view instanceof ViewGroup) {
      ViewGroup group = (ViewGroup) view;
      for (int i = 0; i < group.getChildCount(); i++) {
        View found = findDescription(group.getChildAt(i), label);
        if (found != null) return found;
      }
    }
    return null;
  }

  private static void clickPrefix(View root, String prefix) {
    Button target = buttonPrefix(root, prefix);
    check(target != null && target.isEnabled(), "enabled button: " + prefix);
    assertVisible(target, prefix);
    target.performClick();
  }

  private static Button buttonPrefix(View view, String prefix) {
    if (view instanceof Button && ((Button) view).getText().toString().startsWith(prefix))
      return (Button) view;
    if (view instanceof ViewGroup) {
      ViewGroup group = (ViewGroup) view;
      for (int i = 0; i < group.getChildCount(); i++) {
        Button found = buttonPrefix(group.getChildAt(i), prefix);
        if (found != null) return found;
      }
    }
    return null;
  }

  private static EditText search(PeoplePanel panel) throws Exception {
    return (EditText) findDescription(decor(panel), "搜索姓名或部门");
  }

  private static AppPage dialog(PeoplePanel panel) throws Exception {
    return field(panel, "picker");
  }

  private static View decor(PeoplePanel panel) throws Exception {
    return dialog(panel).getWindow().getDecorView();
  }

  @SuppressWarnings("unchecked")
  private static <T> T field(Object object, String name) throws Exception {
    Field value = object.getClass().getDeclaredField(name);
    value.setAccessible(true);
    return (T) value.get(object);
  }

  private static void rendered(Instrumentation instrumentation, View root) throws Exception {
    instrumentation.waitForIdleSync();
    CountDownLatch frames = new CountDownLatch(1);
    onMain(
        instrumentation,
        () -> {
          root.postOnAnimation(() -> root.postOnAnimation(frames::countDown));
          return null;
        });
    check(frames.await(5, TimeUnit.SECONDS), "native view frames rendered");
    instrumentation.waitForIdleSync();
  }

  private static void screenshot(Instrumentation instrumentation, Activity activity, String name)
      throws IOException {
    Bitmap image = instrumentation.getUiAutomation().takeScreenshot();
    check(image != null, "capture rendered picker screenshot");
    File output = new File(activity.getFilesDir(), "speaker-test-evidence");
    if (!output.isDirectory() && !output.mkdirs())
      throw new IOException("Cannot create screenshot directory");
    try (FileOutputStream stream = new FileOutputStream(new File(output, name))) {
      check(image.compress(Bitmap.CompressFormat.PNG, 100, stream), "write picker screenshot");
    } finally {
      image.recycle();
    }
  }

  private interface CheckedSupplier<T> {
    T get() throws Exception;
  }

  private static <T> T onMain(Instrumentation instrumentation, CheckedSupplier<T> action)
      throws Exception {
    AtomicReference<T> result = new AtomicReference<>();
    AtomicReference<Throwable> failure = new AtomicReference<>();
    instrumentation.runOnMainSync(
        () -> {
          try {
            result.set(action.get());
          } catch (Throwable error) {
            failure.set(error);
          }
        });
    if (failure.get() instanceof Exception) throw (Exception) failure.get();
    if (failure.get() instanceof Error) throw (Error) failure.get();
    if (failure.get() != null) throw new IllegalStateException(failure.get());
    return result.get();
  }

  private static void deleteTree(File entry) throws IOException {
    File[] children = entry.listFiles();
    if (children != null) for (File child : children) deleteTree(child);
    if (entry.exists() && !entry.delete())
      throw new IOException("Unable to remove test fixture: " + entry);
  }

  private static void check(boolean condition, String message) {
    if (!condition) throw new AssertionError(message);
  }
}
