const queuedTaskRegistry = new Map<string, Promise<unknown>>();

export function getOrCreateQueuedTask<T>(
  contractId: string,
  factory: () => Promise<T>
): Promise<T> {
  const existing = queuedTaskRegistry.get(contractId) as Promise<T> | undefined;
  if (existing) {
    return existing;
  }

  const created = factory().catch((error) => {
    queuedTaskRegistry.delete(contractId);
    throw error;
  });

  queuedTaskRegistry.set(contractId, created);
  return created;
}

export function releaseQueuedTask(contractId: string): void {
  queuedTaskRegistry.delete(contractId);
}

export function clearQueuedTaskRegistry(): void {
  queuedTaskRegistry.clear();
}
