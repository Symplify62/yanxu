import { inject, type Component, type InjectionKey } from "vue";
export interface Kit {
  Button: Component;
  Select: Component;
  Dialog: Component;
  Input: Component;
  Checkbox: Component;
  Table: Component;
}
export const kitKey: InjectionKey<Kit> = Symbol("design-kit");
export function useKit() {
  const kit = inject(kitKey);
  if (!kit) throw new Error("Missing component kit");
  return kit;
}
export interface Column {
  key: string;
  label: string;
  width?: number;
}
