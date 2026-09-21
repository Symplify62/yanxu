package cn.jiajian.yanxu;

import android.app.job.*;

public class UpdateJob extends JobService {
  private volatile boolean stopped;

  @Override
  public boolean onStartJob(JobParameters params) {
    stopped = false;
    new Thread(
            () -> {
              boolean complete = AppUpdater.run(this, false, () -> stopped);
              if (!stopped) jobFinished(params, !complete);
            },
            "yanxu-update-job")
        .start();
    return true;
  }

  @Override
  public boolean onStopJob(JobParameters params) {
    stopped = true;
    return true;
  }
}
