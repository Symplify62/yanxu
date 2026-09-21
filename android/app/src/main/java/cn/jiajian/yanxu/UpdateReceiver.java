package cn.jiajian.yanxu;

import android.content.*;

public class UpdateReceiver extends BroadcastReceiver {
  @Override
  public void onReceive(Context c, Intent i) {
    if (UpdateInstaller.ACTION.equals(i.getAction())) UpdateInstaller.result(c, i);
    else if (Intent.ACTION_MY_PACKAGE_REPLACED.equals(i.getAction())) {
      AppUpdater.status(c, "latest", "更新已完成");
      AppUpdater.prefs(c)
          .edit()
          .remove("release")
          .remove("session")
          .remove("manualOnly")
          .putLong("nextCheck", 0)
          .apply();
      AppUpdater.apk(c).delete();
      LocalStore.recover(c);
      AppUpdater.schedule(c);
    } else if (Intent.ACTION_BOOT_COMPLETED.equals(i.getAction())) AppUpdater.schedule(c);
  }
}
