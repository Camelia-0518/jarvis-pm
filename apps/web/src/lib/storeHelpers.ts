// Zustand store helpers — eliminate repeated loading/error boilerplate.
// Usage:
//   setLoading(set);
//   try { ... set({ ...data, isLoading: false }); }
//   catch (err) { setError(set, err, 'Failed to ...'); }

type SetFn<T> = (partial: T | Partial<T> | ((state: T) => T | Partial<T>)) => void;

export function setLoading<T extends Record<string, any>>(set: SetFn<T>): void {
  set({ isLoading: true, error: null } as unknown as Partial<T>);
}

export function setError<T extends Record<string, any>>(
  set: SetFn<T>,
  error: unknown,
  fallback: string,
): void {
  set({
    error: error instanceof Error ? error.message : fallback,
    isLoading: false,
  } as unknown as Partial<T>);
}
