/**
 * Minimal className combiner — joins truthy strings with a space.
 * Dependency-free (no clsx/tailwind-merge) to keep the bundle lean; callers
 * are responsible for not passing conflicting Tailwind classes.
 */
export type ClassValue = string | number | false | null | undefined;

export function cn(...classes: ClassValue[]): string {
  return classes.filter(Boolean).join(" ");
}
