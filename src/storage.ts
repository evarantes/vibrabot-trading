import { initialItems, initialMovements } from "./data";
import { DailyMovement, LinenItem } from "./types";

const ITEMS_KEY = "codexiaauditor:items";
const MOVEMENTS_KEY = "codexiaauditor:movements";

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function loadItems(): LinenItem[] {
  if (!canUseStorage()) {
    return initialItems;
  }

  const raw = window.localStorage.getItem(ITEMS_KEY);

  if (!raw) {
    return initialItems;
  }

  try {
    return JSON.parse(raw) as LinenItem[];
  } catch {
    return initialItems;
  }
}

export function loadMovements(): DailyMovement[] {
  if (!canUseStorage()) {
    return initialMovements;
  }

  const raw = window.localStorage.getItem(MOVEMENTS_KEY);

  if (!raw) {
    return initialMovements;
  }

  try {
    return JSON.parse(raw) as DailyMovement[];
  } catch {
    return initialMovements;
  }
}

export function persistState(items: LinenItem[], movements: DailyMovement[]): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(ITEMS_KEY, JSON.stringify(items));
  window.localStorage.setItem(MOVEMENTS_KEY, JSON.stringify(movements));
}

export function resetDemoState(): { items: LinenItem[]; movements: DailyMovement[] } {
  if (canUseStorage()) {
    window.localStorage.removeItem(ITEMS_KEY);
    window.localStorage.removeItem(MOVEMENTS_KEY);
  }

  return {
    items: initialItems,
    movements: initialMovements
  };
}
