package cn.jiajian.yanxu;

import android.app.Activity;
import android.app.Instrumentation;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.TextView;
import java.lang.reflect.Field;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Real guest navigation: avatar, contextual login and scoped settings; never opens a microphone.
 */
final class NavigationUiChecks {
  static String run(Instrumentation runner, Activity a) throws Exception {
    if (CloudSession.current(a) != null && CloudSession.current(a).valid())
      throw new IllegalStateException("Navigation checks require a signed-out test installation");
    String server = LocalStore.server(a);
    onMain(
        runner,
        () -> {
          View root = a.getWindow().getDecorView();
          View recorderCard = (View) find(root, "开始录音", false).getParent();
          View peopleItem = (View) ((View) find(root, "选择参会者", false).getParent()).getParent();
          View voicesItem = (View) ((View) find(root, "声音档案", false).getParent()).getParent();
          check(gap(recorderCard, peopleItem) >= AppUi.dp(a, 12),
              "recorder and people entry need a visible surface boundary");
          check(gap(peopleItem, voicesItem) >= AppUi.dp(a, 12),
              "sibling entries need the shared surface spacing");
          View avatar = find(a.getWindow().getDecorView(), "头像，登录", true);
          check(avatar != null && avatar.isClickable(), "guest avatar opens account");
          check(find(a.getWindow().getDecorView(), "设置", false) == null,
              "recorder header has no separate settings control");
          avatar.performClick();
        });
    runner.waitForIdleSync();
    CloudAccountUi cloud = field(a, "cloudUi");
    LoginPage login = field(cloud, "loginPage");
    onMain(
        runner,
        () -> {
          check(login.isShowing(), "avatar opens full-page login");
          check(find(login.getWindow().getDecorView(), "应用设置", false) != null,
              "guest can reach settings from login");
          click(login.getWindow().getDecorView(), "登录");
          check(
              find(login.getWindow().getDecorView(), "请输入账号和密码", false) != null,
              "empty login gives feedback");
          click(login.getWindow().getDecorView(), "返回");
          check(
              !RecordingService.active && !VoiceEnrollmentDialog.busy,
              "cancel login never starts capture");
          click(a.getWindow().getDecorView(), "选择参会者");
        });
    runner.waitForIdleSync();
    LoginPage contextual = field(cloud, "loginPage");
    onMain(
        runner,
        () -> {
          check(contextual.isShowing(), "people remain authenticated");
          contextual.dismiss();
          View avatar = find(a.getWindow().getDecorView(), "头像，登录", true);
          avatar.performClick();
          LoginPage reopened = field(cloud, "loginPage");
          click(reopened.getWindow().getDecorView(), "应用设置");
        });
    AppPage settings = field(a, "settingsDialog");
    onMain(
        runner,
        () -> {
          check(settings.isShowing(), "settings is a page");
          View update = (View) ((View) find(settings.body, "应用更新", false).getParent()).getParent();
          View advanced = (View) ((View) find(settings.body, "高级设置", false).getParent()).getParent();
          check(gap(update, advanced) >= AppUi.dp(a, 12),
              "settings rows follow the same surface spacing");
          check(
              find(settings.body, "服务地址", false) == null,
              "connection fields kept under advanced settings");
          check(find(settings.body, "导入音频", false) == null, "import belongs to recording");
          click(settings.body, "高级设置");
        });
    AppPage advanced = field(a, "settingsChild");
    onMain(
        runner,
        () -> {
          EditText address = (EditText) find(advanced.body, "服务地址", true);
          address.setText("not-a-server");
          advanced.getButton(-1).performClick();
          check(
              address.getError() != null && advanced.isShowing(),
              "invalid address keeps editable form");
          check(server.equals(LocalStore.server(a)), "invalid save cannot change server");
          advanced.onBackPressed();
          check(settings.isShowing(), "advanced back returns to settings");
          settings.onBackPressed();
          check(!RecordingService.active, "settings never starts capture");
        });
    return "PASS: avatar login, empty form, contextual login, cancellation, settings hierarchy,"
               + " invalid URL and back navigation";
  }

  private interface Work {
    void run() throws Exception;
  }

  private static void onMain(Instrumentation runner, Work work) throws Exception {
    AtomicReference<Throwable> failure = new AtomicReference<>();
    runner.runOnMainSync(
        () -> {
          try {
            work.run();
          } catch (Throwable e) {
            failure.set(e);
          }
        });
    if (failure.get() != null) throw new AssertionError(failure.get());
    runner.waitForIdleSync();
  }

  @SuppressWarnings("unchecked")
  private static <T> T field(Object target, String name) throws Exception {
    Field f = target.getClass().getDeclaredField(name);
    f.setAccessible(true);
    return (T) f.get(target);
  }

  private static View find(View root, String value, boolean description) {
    if (description
        ? value.contentEquals(
            root.getContentDescription() == null ? "" : root.getContentDescription())
        : root instanceof TextView && value.contentEquals(((TextView) root).getText())) return root;
    if (root instanceof ViewGroup group)
      for (int i = 0; i < group.getChildCount(); i++) {
        View found = find(group.getChildAt(i), value, description);
        if (found != null) return found;
      }
    return null;
  }

  private static void click(View root, String value) {
    View v = find(root, value, false);
    check(v != null, "visible entry: " + value);
    while (!v.isClickable() && v.getParent() instanceof View) v = (View) v.getParent();
    check(v.isEnabled() && v.isClickable(), "usable entry: " + value);
    v.performClick();
  }

  private static void check(boolean value, String message) {
    if (!value) throw new AssertionError(message);
  }

  private static int gap(View upper, View lower) {
    int[] first = new int[2];
    int[] second = new int[2];
    upper.getLocationOnScreen(first);
    lower.getLocationOnScreen(second);
    return second[1] - first[1] - upper.getHeight();
  }
}
