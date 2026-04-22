type TimeoutCallbacks = {
  onIdleTimeout: () => void;
  onHardTimeout: () => void;
};

type TimeoutOptions = TimeoutCallbacks & {
  idleTimeoutMs: number;
  hardTimeoutMs?: number | null;
};

export function createAnalysisTimeoutManager({
  idleTimeoutMs,
  hardTimeoutMs,
  onIdleTimeout,
  onHardTimeout,
}: TimeoutOptions) {
  let disposed = false;
  let completed = false;
  let lastEventAt = Date.now();
  let idleTimer: ReturnType<typeof setTimeout> | null = null;
  let hardTimer: ReturnType<typeof setTimeout> | null = null;

  const clearTimers = () => {
    if (idleTimer) {
      clearTimeout(idleTimer);
      idleTimer = null;
    }
    if (hardTimer) {
      clearTimeout(hardTimer);
      hardTimer = null;
    }
  };

  const armIdleTimer = () => {
    if (disposed || completed) {
      return;
    }
    if (idleTimer) {
      clearTimeout(idleTimer);
    }
    idleTimer = setTimeout(() => {
      if (!disposed && !completed) {
        onIdleTimeout();
      }
    }, idleTimeoutMs);
  };

  if (
    typeof hardTimeoutMs === 'number' &&
    Number.isFinite(hardTimeoutMs) &&
    hardTimeoutMs > 0
  ) {
    hardTimer = setTimeout(() => {
      if (!disposed && !completed) {
        onHardTimeout();
      }
    }, hardTimeoutMs);
  }

  armIdleTimer();

  return {
    touch() {
      if (disposed || completed) {
        return;
      }
      lastEventAt = Date.now();
      armIdleTimer();
    },
    complete() {
      completed = true;
      clearTimers();
    },
    dispose() {
      disposed = true;
      clearTimers();
    },
    getLastEventAt() {
      return lastEventAt;
    },
    isCompleted() {
      return completed;
    },
  };
}
